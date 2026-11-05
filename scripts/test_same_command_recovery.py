"""Offline command restart, durable Planner recovery and device reassignment."""
import contextlib
import copy
import io
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from planner_harness.common import load, save, sha
from planner_harness import accounting as a, PlannerHarness
from planner_harness.delivery import verify_delivery
from planner_harness.lock import RunLock
from experiments import campaign, unified_benchmark as u, resumption as resume
from server_runtime.service import Service
from server_runtime.queue import Queue
from server_runtime.engine import Engine
from test_unified_results import Fixture
from test_loop_engineering import APIPlanner, Renderer
from test_review_modes import Reviewer, action
import test_planner_harness as fixture


def lock_child(path, ready, release):
    with RunLock(path):
        ready.set()
        release.wait(20)


class PlannerRecovery(unittest.TestCase):
    setUp, tearDown = fixture.Tests.setUp, fixture.Tests.tearDown

    def test_four_renders_then_interrupted_finish_resumes_original_answer(self):
        worker = self.root/'service'
        policy = a.default_online_policy(max_generations=4)
        ar = a.install(self.root/'accounting', policy)
        planner = APIPlanner([*[action('generate', input_video='source' if n==0 else 'v1',
                                  prompt='Blue realization '+str(n)) for n in range(4)],
                              action('finish', video='v1', message='The first candidate is preferred.')])
        critic = Reviewer(); critic.actions = critic.actions * 4
        renderer = Renderer(self.source)
        queue = Queue(worker/'queue.sqlite3')
        config = {'workflow':'creative_loop_v1','review':{'mode':'critic'},
                  'planner':{'model':planner.model,'reasoning_effort':planner.reasoning_effort},
                  'critic':{'model':critic.model,'reasoning_effort':critic.reasoning_effort},
                  'accounting_root':str(ar),'budget':policy}
        service = Service(queue,worker,ROOT,config,
                          model_factory=lambda role:planner if role=='planner' else critic,renderer=renderer)
        service.submit({'id':'same-task','source':str(self.source),'source_sha256':sha(self.source),
                        'request':'Make the scene blue.','max_generations':4,
                        'budget_topic':'same-task','budget_lane':'full',
                        'execution':{'mode':'live','resource_policy':{'max_generations':4},
                                     'continuation_policy':{'completion_policy':'fixed_generation_budget'},
                                     'renderer':{'backend':'bernini','seed':42,'generation':{}}}})
        original = PlannerHarness.operate
        def interrupt(harness, operation, event):
            if operation['action']=='finish':raise KeyboardInterrupt('After saved model answer')
            return original(harness,operation,event)
        with patch.object(PlannerHarness,'operate',interrupt), self.assertRaises(KeyboardInterrupt):
            Engine(queue,worker,service,service.expand,interval=.001).run(once=True)
        run = worker/'tasks/same-task/run'
        before = load(run/'state.json')
        self.assertEqual(len(renderer.calls),4)
        self.assertEqual(len(before['submitted_generation_ids']),4)
        self.assertIsNone(before['online_clock']['deadline_unix'])
        request_hashes = {str(p):sha(p) for p in (run/'jobs').glob('*/request.json')}
        counts = (len(planner.inputs),len(critic.inputs),len(renderer.calls))
        Engine(queue,worker,service,service.expand,interval=.001).run(once=True)
        self.assertEqual(verify_delivery(run)['selected'],'v1')
        self.assertEqual((len(planner.inputs),len(critic.inputs),len(renderer.calls)),counts)
        state = load(run/'state.json')
        self.assertEqual(state['submitted_generation_ids'],before['submitted_generation_ids'])
        self.assertEqual(state['online_clock'],before['online_clock'])
        self.assertEqual({str(p):sha(p) for p in (run/'jobs').glob('*/request.json')},request_hashes)
        Engine(queue,worker,service,service.expand,interval=.001).run(once=True)
        self.assertEqual((len(planner.inputs),len(critic.inputs),len(renderer.calls)),counts)

    def test_saved_render_completion_survives_missing_tool_response(self):
        from test_loop_engineering import Engineering
        service,queue,renderer,planner = Engineering.service(self,[
            action('generate',input_video='source',prompt='Blue.'),
            action('finish',video='v1',message='The reviewed result is ready.')])
        service.submit(Engineering.task(self,n=1))
        import server_runtime.service as module
        original=module.save
        def fail_response(path,value):
            if Path(path).name=='response.json' and value.get('payload',{}).get('video'):
                raise KeyboardInterrupt('After durable renderer completion')
            return original(path,value)
        with patch.object(module,'save',side_effect=fail_response),self.assertRaises(KeyboardInterrupt):
            Engine(queue,service.directory,service,service.expand,interval=.001).run(once=True)
        self.assertEqual(len(renderer.calls),1)
        Engine(queue,service.directory,service,service.expand,interval=.001).run(once=True)
        self.assertEqual(verify_delivery(service.directory/'tasks/topic/run')['selected'],'v1')
        self.assertEqual(len(renderer.calls),1)

    def test_uncertain_planner_call_stays_original_without_repeated_calls(self):
        from test_interrupted_model_recovery import RecoveryTests
        output,worker,run,call,digest,service,queue,renderer,planner,critic=RecoveryTests.setup_run(self,'planner')
        before=(len(renderer.calls),len(planner.inputs),len(critic.inputs))
        for _ in range(2):Engine(queue,worker,service,service.expand,interval=.001).run(once=True)
        self.assertEqual((len(renderer.calls),len(planner.inputs),len(critic.inputs)),before)
        self.assertEqual(load(run/'state.json')['status'],'needs_reconciliation')
        # The explicit recovery preview accepts the new no-deadline clock.
        state=load(run/'state.json');state['online_clock']['deadline_unix']=None;save(run/'state.json',state)
        import recover_interrupted_model
        plan=recover_interrupted_model.recover(run,digest,'Inspect the original uncertain call')
        self.assertEqual(plan['role'],'planner')

    def test_physical_device_change_keeps_the_task_queue_and_run(self):
        from test_loop_engineering import Engineering
        from experiments import creative_benchmark as cb
        old_worker=cb._WORKER
        self.addCleanup(setattr,cb,'_WORKER',old_worker)
        shared=[action('generate',input_video='source',prompt='Blue.'),
                action('finish',video='v1',message='Choose the inspected candidate.')]
        resident,_,renderer,planner=Engineering.service(self,shared,config={'renderer':{'backend':'bernini','gpu_lock':'gpu-0'}})
        def make(current):
            runtime=u.Runtime.__new__(u.Runtime)
            runtime.root,runtime.output=ROOT,self.root/'batch'
            runtime.resident_service=current;runtime.task_services={}
            runtime.bind_task('topic','full')
            return runtime
        first=make(resident)
        task=Engineering.task(self,identity='topic__full',n=1)
        task.update(budget_topic='topic',budget_lane='full')
        first.service.submit(task)
        original=PlannerHarness.operate
        def stop(h,op,event):
            if op['action']=='finish':raise KeyboardInterrupt()
            return original(h,op,event)
        with patch.object(PlannerHarness,'operate',stop),self.assertRaises(KeyboardInterrupt):
            Engine(first.queue,first.directory,first.service,first.service.expand,interval=.001).run(once=True)
        cfg=copy.deepcopy(resident.config);cfg['renderer']['gpu_lock']='gpu-3'
        replacement=Service(Queue(self.root/'other/queue.sqlite3'),self.root/'other',ROOT,cfg,
                            model_factory=resident.model_factory,renderer=renderer)
        second=make(replacement)
        self.assertEqual(first.directory,second.directory)
        count=len(planner.inputs)
        Engine(second.queue,second.directory,second.service,second.service.expand,interval=.001).run(once=True)
        self.assertEqual(verify_delivery(second.directory/'tasks/topic__full/run')['selected'],'v1')
        self.assertEqual((len(renderer.calls),len(planner.inputs)),(1,count))


class Commands(Fixture):
    def test_transport_recovery_keeps_original_or_explicit_allowance(self):
        from planner_harness.resumption import call_ready
        call = self.root/'transport'
        save(call/'input.json', {'model': 'fixture'})
        save(call/'allowance.json', {'first':1, 'last':1})
        save(call/'attempts/01/failed.json', {'retryable':False})
        self.assertFalse(call_ready(call))
        before = sha(call/'allowance.json')
        self.assertFalse(call_ready(call))
        self.assertEqual(sha(call/'allowance.json'),before)
        # Only explicit recovery advances past a permanent provider rejection.
        from planner_harness.model_call import reopen_call
        reopen_call(call, 'Provider access restored.', 1)
        self.assertTrue(call_ready(call))
        save(call/'attempts/02/submitted.json', {'attempt':2})
        self.assertFalse(call_ready(call))

    def test_original_pe_command_recovers_and_reuses_completed_direct(self):
        import run_experiment_campaign as entry
        from planner_harness.video import Video
        from planner_harness.execution import immutable
        config = campaign.configuration(ROOT/'configs/experiment-campaign.json')
        config['rsi_partition']={'train_count':1,'test_count':1}
        config['prompt_forms']=['short']
        config['reuse_direct_results']=None
        second = self.repo/'second.mp4'; second.write_bytes(self.source.read_bytes()+b'fixture')
        self.rows[1].update(source_video='second.mp4',source_video_sha256=sha(second))
        save(self.repo/'benchmark_data/benchmark.json',self.rows)
        cfg,host = self.root/'campaign.json',self.root/'host.json'
        save(cfg,config); save(host,{'devices':['0'],'renderer':{'backend':'bernini'}})
        calls=[]; failure=[True]
        class Runtime:
            def __init__(inner, root, output, host, batch):inner.batch=batch
            def ready(inner):pass
            def close(inner):pass
            def refine(inner, topic, directory, scope, history):
                calls.append(('refine',topic['id'],len(history)))
                return 'Synthetic blue scene '+str(len(history))
            def render(inner, topic, method, prompt, seed, number, scope):
                directory=Path(scope['root']).parent/'fake-render'/topic['id']/method/str(number)
                path=directory/'response.json'
                if path.exists():return load(path)
                def produce():
                    calls.append(('render',topic['id'],method,seed))
                    return {'video':Video(self.repo/topic['source'],directory).info,
                            'response':str(path),'seed':seed}
                value=a.invoke(scope,str(path),'render','renderer:bernini',produce)
                immutable(path,value)
                return value
            def review(inner,topic,candidate,directory,scope):
                if failure[0] and candidate['id']=='v2':
                    failure[0]=False
                    raise RuntimeError('Synthetic interruption before review dispatch')
                calls.append(('review',topic['id'],candidate['id']))
                return {'report':{'summary':'Synthetic review','findings':[]},'evidence':[]}
            def choose(inner,topic,candidates,reviews,directory,scope):
                calls.append(('choose',topic['id'],len(candidates)))
                return 0,{'policy':u.SELECTOR,'selected_index':0,'reason':'Synthetic first choice'}
        def serial(root,output,host):
            return u.run_serial(root,output,host,runtime_factory=Runtime)
        def command(stage):
            argv=['run_experiment_campaign.py','run','--backend','bernini','--stage',stage,
                  '--config',str(cfg),'--host-config',str(host),'--output',str(self.output),'--execute']
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
                return entry.main()
        with patch.object(entry,'ROOT',self.repo), \
             patch('planner_harness.creative.experiment_profile',return_value={'sha256':'fixture'}), \
             patch('planner_harness.creative.verify_experiment',return_value={'sha256':'fixture'}), \
             patch.object(u,'preflight'),patch.object(u,'run',side_effect=serial):
            command('direct'); count=len(calls); command('direct'); self.assertEqual(len(calls),count)
            with self.assertRaises(RuntimeError):command('pe-loop')
            command('pe-loop')
            count=len(calls); command('pe-loop'); self.assertEqual(len(calls),count)
            # Deployment changes preserve the same completed tasks and original allowance.
            save(host,{'devices':['1','3'],'renderer':{'backend':'bernini'}})
            command('pe-loop'); self.assertEqual(len(calls),count)
        renders=[r for r in calls if r[0]=='render']
        self.assertEqual(len([r for r in renders if r[2]=='direct']),2)
        for topic in ('001__short','002__short'):
            self.assertEqual([r[3] for r in renders if r[1]==topic and r[2]=='pe-loop'],[42,43,44,45])
        self.assertEqual(len([r for r in calls if r[0]=='refine']),8)

    def test_standardized_source_verified_against_original_and_changed_source_rejected(self):
        from test_fixed117 import write_video
        write_video(self.source,9,10)
        for row in self.rows:row['source_video_sha256']=sha(self.source)
        save(self.repo/'benchmark_data/benchmark.json',self.rows)
        self.prepare(methods=['direct'])
        with patch('planner_harness.creative.verify_experiment',return_value={'sha256':'fixture'}):
            u.verify(self.repo,self.output)
            self.source.write_bytes(self.source.read_bytes()+b'changed')
            # The saved normalized source remains usable after the original is updated.
            recovered=u.verify(self.repo,self.output)
            self.assertEqual(recovered['sha256'],load(self.output/'batch.json')['sha256'])
            saved_source=self.repo/recovered['topics'][0]['source']
            saved_source.write_bytes(saved_source.read_bytes()+b'corrupt')
            with self.assertRaises(Exception):u.verify(self.repo,self.output)

    def test_deployment_and_legacy_task_location_preserve_identity(self):
        p=self.output/'host.json'
        resume.bind_deployment(p,{'devices':['0'],'renderer':{'backend':'bernini'}})
        resume.bind_deployment(p,{'devices':['2','4'],'renderer':{'backend':'bernini'}})
        effective=resume.bind_deployment(p,{'devices':['2'],'renderer':{'backend':'ditto'}})
        self.assertEqual(effective['renderer']['backend'],'bernini')
        self.assertEqual(effective['devices'],['2'])
        old=self.output/'workers/7';save(old/'tasks/topic__full/task.json',{'id':'topic__full'})
        self.assertEqual(resume.task_directory(self.output,'topic','full'),old)
        self.assertEqual(resume.task_directory(self.output,'topic','full'),old)
        self.assertEqual(resume.task_directory(self.output,'fresh','full'),self.output/'executions/fresh/full')

    def test_concurrent_start_has_only_one_owner(self):
        ctx=multiprocessing.get_context('spawn');ready=ctx.Event();release=ctx.Event()
        path=self.output/'campaign-owner'
        child=ctx.Process(target=lock_child,args=(path,ready,release));child.start()
        try:
            self.assertTrue(ready.wait(10))
            with self.assertRaisesRegex(RuntimeError,'owned by another process'):
                with RunLock(path):self.fail('A duplicate command acquired ownership')
        finally:
            release.set();child.join(10)
        self.assertEqual(child.exitcode,0)
        with RunLock(path):pass

    def test_scoring_restart_only_calls_the_missing_judge(self):
        from experiments import results
        from evaluation.creative import JUDGES
        from evaluation.low_high import PROTOCOL,profile
        from types import SimpleNamespace
        results.import_video(self.repo,self.registry,self.row())
        results.prepare_evaluation(self.repo,self.registry,evaluation_id='original')
        models={j:SimpleNamespace(model=j,reasoning_effort=None,requires_live_budget=False) for j in JUDGES}
        calls=[]; interrupted=[False]
        def judge(request,source,candidate,directory,*,model,plan):
            if model.model==JUDGES[1] and not interrupted[0]:
                interrupted[0]=True
                raise KeyboardInterrupt('Between independent judges')
            calls.append(model.model)
            return {'source_sha256':source['sha256'],'output_sha256':candidate['sha256'],
                    'model':model.model,'profile_sha256':profile()['sha256'],
                    'report':{'protocol_id':PROTOCOL,'main_scores':{}}}
        with patch('evaluation.creative.judge_candidate',side_effect=judge), \
             patch('evaluation.final_suite.automatic',return_value={'metrics':{}}):
            with self.assertRaises(KeyboardInterrupt):results.score_evaluation(self.repo,self.registry,models=models)
            identity=sha(self.registry/'current-evaluation.json')
            results.score_evaluation(self.repo,self.registry,models=models)
            results.score_evaluation(self.repo,self.registry,models=models)
            self.assertEqual(calls,list(JUDGES))
            self.assertEqual(sha(self.registry/'current-evaluation.json'),identity)
        (self.registry/'current-evaluation.json').unlink()
        restored, _ = results.ensure_evaluation(self.repo,self.registry,evaluation_id='original')
        self.assertEqual(restored,self.registry/'evaluations/original')
        self.assertEqual(len(list((self.registry/'evaluations').iterdir())),1)
        self.assertEqual(calls,list(JUDGES))

    def test_claim_recovery_reopens_only_the_original_task(self):
        import socket
        from experiments.device_scheduler import Claims,work_units
        self.prepare(methods=['direct'],prompt_forms=['short'])
        batch=load(self.output/'batch.json')
        units=work_units(batch,{})
        owner=socket.gethostname()+':999999999:dead:0:fixture'
        queue=Claims(self.output/'device-queue.sqlite3',units,batch['sha256'],owner)
        first=queue.next()
        queue.recover(self.output)
        again=queue.next()
        self.assertEqual(first['id'],again['id'])
        queue.finish(again['id'],'settled')
        save(self.output/'methods'/again['id']/'direct/settlement.json',
             {'batch_sha256':batch['sha256'],'status':'ready'})
        queue.recover(self.output)
        self.assertNotEqual(queue.next()['id'],first['id'])
        before=queue.rows()
        changed=[*units,{'id':'unapproved'}]
        with self.assertRaisesRegex(ValueError,'Queue differs'):
            Claims(self.output/'device-queue.sqlite3',changed,batch['sha256'],'other')
        self.assertEqual(queue.rows(),before)


if __name__=='__main__':unittest.main()
