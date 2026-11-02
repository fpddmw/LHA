"""Focused offline integration for the request-path simplification."""
import copy
import json
import multiprocessing
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import test_planner_harness as legacy
import test_creative_loop as fixtures
import test_creative_delivery_review as delivery_fixtures
import test_unified_results as registry_fixtures
from planner_harness.common import load,save,sha
from planner_harness import PlannerHarness
from planner_harness.execution import collect
from planner_harness.delivery import verify_delivery
from experiments.device_scheduler import Claims,work_units


def claim_worker(path,units,barrier,results,owner):
    queue=Claims(path,units,'frozen-plan',owner)
    barrier.wait(timeout=5)
    while (topic:=queue.next(wait=True)) is not None:
        started=time.monotonic()
        time.sleep(.15 if topic['split']=='train' else .2)
        # Real training hooks finish the claim only after maintenance settles.
        queue.finish(topic.get('claim_id',topic['id']),'settled')
        results.put((topic['id'],owner,started,time.monotonic()))


class Cleanup(unittest.TestCase):
    setUp,tearDown=legacy.Tests.setUp,legacy.Tests.tearDown
    start=delivery_fixtures.DeliveryReviewTests.start
    review=delivery_fixtures.DeliveryReviewTests.review
    respond=fixtures.CreativeTests.respond
    resume=fixtures.CreativeTests.resume

    def test_current_complete_report_delivers_in_single_actual_finish(self):
        self.start();job,critic=self.review()
        with patch('planner_harness.resources.reserve',side_effect=AssertionError('duplicate reservation')):
            state=self.resume([fixtures.action('finish',video='v1',message='Accept the complete report and its stated limitations.')])
        self.assertEqual(state['status'],'complete')
        self.assertEqual(len(self.model.inputs),1)
        proof=state['final']['delivery_review']
        from planner_harness.delivery_review import PROTOCOL
        self.assertEqual(proof['protocol'],PROTOCOL)
        self.assertEqual(proof['review_mode'],'critic')
        self.assertEqual(proof['candidate_id'],'v1')
        actual=load(self.h.output/'calls'/proof['planner_event_id']/'transport/input.json')
        visible=json.loads(actual['user_text'])
        self.assertEqual(visible['evaluations'][job['id']]['report'],state['evaluations'][job['id']]['report'])
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')
        self.assertFalse((self.h.output/'resource-ledger.json').exists())
        self.assertEqual(len(critic.inputs),1)
        call=Path(state['evaluations'][job['id']]['review_call'])
        packet=load(call.parent/'request.json')
        sent=load(call/'input.json')
        self.assertEqual(sent['user_text'],packet['user_text'])
        self.assertNotIn('decoder',sent['user_text'])
        before=(self.h.output/'state.json').read_bytes()
        self.h.resume(continue_delivery=True,additional_turns=20,max_context_chars=9000)
        self.assertEqual(before,(self.h.output/'state.json').read_bytes())

    def test_known_second_critic_failure_returns_to_planner_then_delivers_v1(self):
        self.start();first,critic=self.review()
        self.resume([fixtures.action('generate',input_video='source',prompt='Try a second blue treatment.')])
        self.respond(review=False);collect(self.h)
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        folder=self.h.output/'jobs'/job['id']
        failed={'status':'failed','mode':job['mode'],'request_sha256':job['sha256'],'error':'Known invalid report; no external execution remains.'}
        save(folder/'response.json',failed);collect(self.h);self.h.checkpoint()
        self.assertEqual(self.h.state['status'],'running')
        self.assertIsNone(self.h.state['pending_tool'])
        self.assertNotIn(job['id'],self.h.state['evaluations'])
        state=self.resume([fixtures.action('delivery_candidate',video='v1'),
            fixtures.action('finish',video='v1',message='The first valid report supports the retained result.'),
            fixtures.action('finish',video='v1',message='Read the restored first report and accept its limitations.')])
        self.assertEqual(state['status'],'complete');self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')
        self.assertEqual(state['final']['delivery_review']['candidate_id'],'v1')
        from planner_harness.delivery_review import validated_feedback
        self.assertEqual(validated_feedback(self.h.output,state,'v1',first['id'])['video_id'],'v1')
        self.assertEqual(load(folder/'response.json'),failed)
        self.assertEqual(sum(j['kind']=='critique' for j in state['jobs'].values()),2)
        self.assertTrue(any(e.get('result',{}).get('status')=='failed' for e in state['events']))

    def test_three_real_workers_wait_for_training_then_share_heldout(self):
        ctx=multiprocessing.get_context('spawn')
        batch={'arms':['none','full'],'training_maintenance':True,
            'topics':[{'id':f'train{i}','split':'train','methods':['none']} for i in range(2)]
                +[{'id':f'test{i}','split':'test','methods':['full']} for i in range(6)]}
        units=work_units(batch,{})
        self.assertTrue(all(t['methods']==['none'] for t in units if t['split']=='train'))
        last_training=next(t['claim_id'] for t in units if t['id']=='train1')
        self.assertTrue(all(t['dependency']==last_training for t in units if t['split']=='test'))
        path=self.root/'queue.sqlite3';Claims(path,units,'frozen-plan','init')
        barrier=ctx.Barrier(3);results=ctx.Queue()
        workers=[ctx.Process(target=claim_worker,args=(path,units,barrier,results,f'worker{i}')) for i in range(3)]
        for worker in workers:worker.start()
        try:
            for worker in workers:worker.join(timeout=8)
            self.assertTrue(all(not w.is_alive() and w.exitcode==0 for w in workers))
            rows=[results.get(timeout=1) for _ in units]
            train_end=max(r[3] for r in rows if r[0].startswith('train'))
            heldout=[r for r in rows if r[0].startswith('test')]
            self.assertEqual(len({r[1] for r in heldout}),3)
            self.assertGreaterEqual(min(r[2] for r in heldout),train_end-.01)
            self.assertEqual({r['status'] for r in Claims(path,units,'frozen-plan','check').rows()},{'settled'})
        finally:
            for worker in workers:
                if worker.is_alive():worker.terminate();worker.join()

    def test_projection_is_compact_on_first_and_repair_calls_with_exact_raw_binding(self):
        from planner_harness.report_call import call_report,verify_inputs,retry_packet
        from critic_harness.evidence import model_packet
        visible={'stage':'fixture','evidence':[{'id':'source:0','video_id':'source','kind':'overview','frame_index':0,'timestamp_seconds':0,'attachment':1,'sha256':'a'*64,'decoder':'native','pts_origin_seconds':0,'crop':None}],
            'event_observations':[{'report':{'findings':['Verbatim finding.'],'limitations':['Verbatim uncertainty.']}}]}
        packet={'system_prompt':'Return JSON.','user_text':json.dumps(visible,indent=2),'images':[],'input_projection':'evidence-v1'}
        model=fixtures.Scripted([{'bad':True},{'ok':True}])
        def validate(value,raw):
            self.assertEqual(raw,packet)
            if value!={'ok':True}:raise ValueError('Missing ok field')
        report,selected=call_report(self.root/'projection',model,packet,[],validate)
        self.assertEqual(report,{'ok':True});self.assertEqual(selected['attempt'],2)
        self.assertEqual(len(model.inputs),2)
        self.assertEqual(json.loads(model.inputs[0]['user_text'])['event_observations'],visible['event_observations'])
        for sent in model.inputs:
            self.assertNotIn('\n',sent['user_text']);self.assertNotIn('sha256',json.loads(sent['user_text'])['evidence'][0])
        verify_inputs(self.root/'projection/call',model,packet,[])
        verify_inputs(self.root/'projection/report-attempts/02/call',model,packet,[])
        from planner_harness.working_memory import estimate
        self.assertEqual(load(self.root/'projection/context-budget.json')['text_tokens_estimated'],estimate(packet['system_prompt'],model_packet(packet)['user_text'],0)['text_tokens_estimated'])


class RegistryCleanup(registry_fixtures.Fixture):
    def test_missing_planned_report_and_split_filter_include_matching_comparisons_only(self):
        from experiments import results
        frozen=self.root/'main-frozen.json';save(frozen,{'revision':'frozen-main'})
        with patch('planner_harness.training_experience.validate_snapshot') as validate:
            batch=self.prepare(methods=['full','direct-best-of-n'],best_of_n=2,prompt_forms=['short'],
                training_maintenance=False,experience_snapshot=frozen)
        validate.assert_called_once()
        self.assertFalse(batch['training_maintenance'])
        self.assertEqual(load(batch['experience_snapshot']),{'revision':'frozen-main'})
        self.assertFalse((self.output/'training-experience').exists())
        results.prepare_evaluation(self.repo,self.registry,evaluation_id='missing-plan')
        records=results.compare_evaluation(self.repo,self.registry)
        self.assertTrue(records);self.assertEqual({r['split'] for r in records},{'train','test'})
        self.assertTrue(all(r['result']['judgments'] is None for r in records))
        view=results.report(self.repo,self.registry,splits=['test'])
        self.assertTrue(view['results']);self.assertEqual({r['split'] for r in view['results']},{'test'})
        for judges in view['blind_comparisons'].values():
            for judge in judges.values():
                for metric in judge['short'].values():self.assertEqual(metric['planned'],1)
        self.assertEqual(set(view['test_analysis']['by_review_mode']),{'critic'})
        for comparisons in view['test_analysis']['by_review_mode']['critic']['by_judge'].values():
            for endpoints in comparisons.values():
                for metric in endpoints.values():self.assertEqual(metric['planned_positions'],1)

    def test_zero_accumulates_privately_and_full_reads_only_the_frozen_revision(self):
        from experiments.unified_benchmark import task_conditions,method_identity
        seed=self.root/'seed.json';learned=self.root/'learned.json';none=self.root/'none.json'
        save(seed,{'revision':'base'});save(learned,{'revision':'learned'});save(none,{'enabled':False})
        batch=self.prepare(methods=['none'],best_of_n=None,prompt_forms=['short'],training_maintenance=True)
        batch={**batch,'experience_snapshot':str(seed),'experience_seed_sha256':sha(seed),'experience_none_snapshot':str(none)}
        training=next(t for t in batch['topics'] if t['split']=='train')
        topic=next(t for t in batch['topics'] if t['split']=='test')
        current={'snapshot':str(learned),'snapshot_sha256':sha(learned)}
        with patch('planner_harness.training_experience.current',return_value=current):
            online=task_conditions(self.repo,self.output,training,'none',batch)
            empty=task_conditions(self.repo,self.output,topic,'none',batch)
        self.assertTrue(online['training_method'])
        self.assertEqual(online['actual_knowledge_sha256'],sha(none))
        self.assertFalse(empty['training_method'])
        self.assertEqual(empty['actual_knowledge_sha256'],sha(none))
        self.assertEqual(empty['experience_seed_sha256'],sha(learned))
        zero_output=self.output
        with patch('planner_harness.training_experience.current',side_effect=AssertionError('Original task is already bound')):
            self.assertEqual(task_conditions(self.repo,zero_output,training,'none',batch),online)
            self.assertEqual(task_conditions(self.repo,zero_output,topic,'none',batch),empty)
        self.output=self.root/'full-read-only'
        with patch('planner_harness.training_experience.validate_snapshot'):
            frozen_batch=self.prepare(methods=['full'],best_of_n=None,prompt_forms=['short'],
                training_maintenance=False,experience_snapshot=zero_output/'heldout-full.json')
        with patch('planner_harness.training_experience.current',side_effect=AssertionError('Full evaluation must not follow the private current pointer')):
            bound=[task_conditions(self.repo,self.output,t,'full',frozen_batch) for t in frozen_batch['topics']]
            self.assertEqual(task_conditions(self.repo,self.output,frozen_batch['topics'][0],'full',frozen_batch),bound[0])
        self.assertTrue(all(not state['training_method'] for state in bound))
        self.assertTrue(all(load(state['experience_snapshot'])=={'revision':'learned'} for state in bound))
        full=bound[0]
        variants=[{**frozen_batch,'max_generations':1},{**frozen_batch,'resource_policy':{'max_wall_seconds':2}},
            {**frozen_batch,'seed_sequence':{'start':42,'step':7}},{**full,'actual_knowledge_sha256':'other'}]
        self.assertTrue(all(method_identity('full',v)!=method_identity('full',full) for v in variants))

    def test_maintenance_stage_identity_uses_actual_code_and_same_config(self):
        import shutil
        from planner_harness import maintenance
        for name in [*maintenance.REFERENCES,*['.agents/skills/'+s+'/SKILL.md' for s in maintenance.SKILLS]]:
            target=self.repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        frozen=maintenance.stage_profile(self.repo,self.output,{'model_calls':7})
        self.assertEqual(frozen['configuration']['model_calls'],7)
        self.assertEqual(frozen['implementation']['src/planner_harness/maintenance.py'],sha(ROOT/'src/planner_harness/maintenance.py'))
        self.assertEqual(frozen['implementation']['src/planner_harness/training_experience.py'],sha(ROOT/'src/planner_harness/training_experience.py'))
        self.assertEqual(len(frozen['skills']),3);self.assertEqual(len(frozen['references']),3)


if __name__=='__main__':unittest.main()
