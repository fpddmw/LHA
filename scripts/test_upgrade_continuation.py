"""Cross-version recovery: historical record projections plus offline execution."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from planner_harness.common import load, save, sha
from planner_harness import accounting as a, PlannerHarness
from planner_harness.execution import signature
from planner_harness.resumption import reopen_interrupted_state
from planner_harness.model_call import call_text
from planner_harness.delivery import verify_delivery
from experiments import unified_benchmark as u, resumption
from test_loop_engineering import APIPlanner, Renderer
from test_review_modes import Reviewer, action
from server_runtime.service import Service
from server_runtime.queue import Queue
from server_runtime.engine import Engine
import test_planner_harness as fixture
from test_unified_results import Fixture

HISTORY = load(ROOT/'scripts/fixtures/upgrade-records-20261104.json')


class SavedRecords(unittest.TestCase):
    def test_real_direct_records_survive_uniform117_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(len(HISTORY['direct']),71)
            old_axes=set()
            for entry in HISTORY['direct']:
                topic={'id':entry['sample_id']+'__'+entry['prompt_form'],
                       'sample_id':entry['sample_id'],'prompt_form':entry['prompt_form'],
                       'source_sha256':'new-normalized-input','request':'Current inventory text',
                       'native_output':{'frames':117,'fps':24}}
                batch={'results_root':tmp,'backend':'bernini','generation':{'updated_default':True}}
                before=copy.deepcopy(entry)
                u.check_entry(topic,'direct',batch,entry)
                self.assertEqual(entry,before)
                old_axes.add((entry['generation']['output']['frames'],entry['generation']['output']['fps']))
            self.assertGreater(len(old_axes),1)
            self.assertEqual(len(list((Path(tmp)/'reuse/upgrade-history').glob('*.json'))),71)

    def test_real_three_of_four_state_reopens_without_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);state=copy.deepcopy(HISTORY['planner'])
            state['notes']=['Keep the original task memory.']
            save(path/'state.json',state);save(path/'final.json',state['final'])
            recovered=reopen_interrupted_state(path,state)
            self.assertEqual(recovered['status'],'running')
            for key in ('submitted_generation_ids','videos','event_ids','notes','config'):
                self.assertEqual(recovered[key],load(path/'state.json')[key])
            self.assertEqual(len(recovered['submitted_generation_ids']),3)
            self.assertEqual(recovered['config']['resource_policy']['max_generations'],4)
            self.assertEqual(recovered['config']['continuation_policy']['hard_generation_limit'],4)
            self.assertEqual(recovered['videos'],HISTORY['planner']['videos'])
            self.assertEqual(recovered['event_ids'],HISTORY['planner']['event_ids'])
            self.assertFalse((path/'final.json').exists())
            self.assertEqual(len(list((path/'recovery-history').glob('*.json'))),1)

    def test_unknown_original_call_is_not_reopened(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);state=copy.deepcopy(HISTORY['planner']);state['pending_event']='event-old'
            save(path/'state.json',state)
            call=path/'calls/event-old/transport'
            save(call/'allowance.json',{'first':1,'last':1})
            save(call/'attempts/01/submitted.json',{'at':'old'})
            self.assertEqual(reopen_interrupted_state(path,state),state)
            self.assertEqual(state['status'],'execution_failed')

    def test_time_upgrade_keeps_ledger_operations_and_allowance(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=a.default_online_policy(max_generations=4,wall_seconds=30)
            root=a.install(tmp,old);scope=a.scope(root,'topic','full');a.start_task(scope)
            a.invoke(scope,'render-1','render','render:bernini',lambda:{'done':True})
            before=a.load_ledger(root);digest=sha(root/'policy.json')
            a.install(root,a.default_online_policy(max_generations=9))
            after=a.load_ledger(root)
            self.assertEqual(after['operations'],before['operations'])
            self.assertEqual(sha(root/'policy.json'),digest)
            self.assertEqual(a.checked(scope)[1]['online_task_budget']['max_generations'],4)
            self.assertIsNone(a.start_task(scope)['deadline_unix'])


class PlannerUpgrade(unittest.TestCase):
    setUp,tearDown=fixture.Tests.setUp,fixture.Tests.tearDown

    def test_interrupted_fourth_generation_uses_original_answer_and_budget(self):
        worker=self.root/'service';policy=a.default_online_policy(max_generations=4)
        ar=a.install(self.root/'accounting',policy)
        planner=APIPlanner([action('note',text='Preserve this interpretation.'),
            *[action('generate',input_video='source' if n==0 else 'v1',prompt='Blue plan '+str(n)) for n in range(4)],
            action('finish',video='v1',message='Select the original successful candidate.')])
        critic=Reviewer();critic.actions*=4;renderer=Renderer(self.source)
        config={'workflow':'creative_loop_v1','review':{'mode':'critic'},
                'planner':{'model':planner.model,'reasoning_effort':planner.reasoning_effort},
                'critic':{'model':critic.model,'reasoning_effort':critic.reasoning_effort},
                'accounting_root':str(ar),'budget':policy}
        queue=Queue(worker/'queue.sqlite3')
        service=Service(queue,worker,ROOT,config,model_factory=lambda role:planner if role=='planner' else critic,renderer=renderer)
        task={'id':'upgrade','source':str(self.source),'source_sha256':sha(self.source),'request':'Turn the scene blue.',
              'max_generations':4,'budget_topic':'upgrade','budget_lane':'full',
              'execution':{'mode':'live','resource_policy':{'max_generations':4},
                           'continuation_policy':{'completion_policy':'fixed_generation_budget'},
                           'renderer':{'backend':'bernini','seed':42,'generation':{}}}}
        service.submit(task)
        operate=PlannerHarness.operate
        def interrupt(h,op,event):
            if op['action']=='generate' and len(renderer.calls)==3:raise KeyboardInterrupt()
            return operate(h,op,event)
        with patch.object(PlannerHarness,'operate',interrupt),self.assertRaises(KeyboardInterrupt):
            Engine(queue,worker,service,service.expand,interval=.001).run(once=True)
        run=worker/'tasks/upgrade/run';before=load(run/'state.json')
        pending=run/'calls'/before['pending_event']/'input.json';pending_hash=sha(pending)
        old_notes=copy.deepcopy(before['notes']);old_ids=list(before['submitted_generation_ids'])
        before['config']['continuation_policy']['version']='creative-continuation-v4'
        before['config']['delivery_review_protocol']='historical-delivery'
        save(run/'state.json',before)
        changed=copy.deepcopy(config);changed['budget']=a.default_online_policy(max_generations=9)
        with patch.object(Service,'source_inventory',return_value={'new_code.py':'new-version'}):
            upgraded=Service(queue,worker,ROOT,changed,model_factory=service.model_factory,renderer=renderer)
        upgraded.submit({**task,'max_generations':9,'request':'Changed defaults must not replace the original task.'})
        Engine(queue,worker,upgraded,upgraded.expand,interval=.001).run(once=True)
        state=load(run/'state.json')
        self.assertEqual(len(renderer.calls),4, [(r['key'],r['state'],r.get('error')) for r in queue.rows()])
        self.assertEqual(state['submitted_generation_ids'][:3],old_ids)
        self.assertEqual(state['notes'],old_notes)
        self.assertEqual(sha(pending),pending_hash)
        self.assertEqual(state['config']['resource_policy']['max_generations'],4)
        self.assertEqual(verify_delivery(run)['selected'],'v1')
        state['final']['delivery_review']['protocol']='creative-delivery-v5-historical'
        save(run/'state.json',state);save(run/'final.json',state['final'])
        self.assertEqual(verify_delivery(run)['selected'],'v1')
        count=(len(planner.inputs),len(critic.inputs),len(renderer.calls))
        Engine(queue,worker,upgraded,upgraded.expand,interval=.001).run(once=True)
        self.assertEqual((len(planner.inputs),len(critic.inputs),len(renderer.calls)),count)


class BatchUpgrade(Fixture):
    def test_prepare_preserves_task_population_and_defaults(self):
        saved=self.prepare(methods=['direct','pe-loop','pre-experience'],max_generations=4)
        before=sha(self.output/'batch.json')
        self.rows[0]['prompt_short']='Updated prompt';save(self.repo/'benchmark_data/benchmark.json',self.rows)
        with patch('planner_harness.creative.verify_experiment',return_value={'sha256':'fixture'}):
            restored=u.prepare(self.repo,self.output,methods=['full'],max_generations=9,splits=['test'],prompt_forms=['long'])
        self.assertEqual({k:restored[k] for k in saved},saved)
        self.assertEqual(sha(self.output/'batch.json'),before)
        self.assertEqual(resumption.preview(self.output)['saved_method_positions'],12)

    def test_cached_model_answer_uses_original_input_after_upgrade(self):
        class Model:
            model='fixture';reasoning_effort='high';calls=0
            def predict_text(self,**kwargs):
                Model.calls+=1;return 'Original answer'
        call=self.output/'call'
        self.assertEqual(call_text(call,Model(),'old manual','old task',[]),'Original answer')
        before=sha(call/'input.json')
        self.assertEqual(call_text(call,Model(),'new manual','new task',[]),'Original answer')
        self.assertEqual(Model.calls,1)
        self.assertEqual(sha(call/'input.json'),before)


    def test_partial_scoring_reuses_accepted_main_projection_after_upgrade(self):
        from evaluation import low_high, creative, final_projection, task_metrics
        from test_low_high import Judge
        from planner_harness.video import Video
        source=Video(self.source,self.root/'info').info
        request='Change the scene color.'
        plan=low_high.freeze_plan({'track':'long'},request,source,self.root/'plan')
        model=Judge();directory=self.output/'score'
        with patch.object(task_metrics,'evaluate',side_effect=KeyboardInterrupt('After accepted main judgment')):
            with self.assertRaises(KeyboardInterrupt):
                creative.judge_candidate(request,source,source,directory,model=model,plan=plan)
        before=len(model.calls);projection=load(directory/'final-main-projection.json')
        with patch.object(final_projection,'VERSION','new-validator-version'),patch.object(task_metrics,'evaluate',return_value={'metrics':{}}):
            result=creative.judge_candidate(request,source,source,directory,model=model,plan=plan)
            final_projection.verify(directory,result,load(directory/'evidence/request.json'),model)
        self.assertEqual(len(model.calls),before)
        self.assertEqual(result['main_projection'],projection)

    def test_frozen_judge_keeps_original_provider_model_and_effort(self):
        from evaluation import creative, providers
        from types import SimpleNamespace
        original={'model':'old-judge','provider':'openrouter','provider_model':'old/model','reasoning_effort':'medium'}
        with patch.object(providers,'OpenRouterJudge',return_value=SimpleNamespace()) as ctor:
            model=creative.frozen_judge(original)
        self.assertEqual(ctor.call_args.kwargs['frozen_spec'],original)
        self.assertEqual(model.frozen_identity,original)


if __name__=='__main__':unittest.main()
