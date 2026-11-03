"""Fixed experimental generation budget; scripted models and synthetic videos only."""
import copy
import sys
import time
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from planner_harness import PlannerHarness, continuation as c, resources
from planner_harness.common import load
from planner_harness.delivery import verify_delivery
from planner_harness.execution import collect
import test_creative_loop as f
import test_planner_harness as legacy
import test_unified_results as batch_fixture
from experiments import creative_benchmark as benchmark, unified_benchmark as unified


class RuntimeTests(unittest.TestCase):
    setUp,tearDown=legacy.Tests.setUp,legacy.Tests.tearDown
    respond=f.CreativeTests.respond

    def start(self,cap=4,review='critic'):
        model=f.Scripted([f.action('generate',input_video='source',prompt='A blue scene.')])
        self.h=PlannerHarness(self.root/'run',model)
        self.h.start(self.source,'Make the scene blue.',mode='loop',workflow='creative_loop_v1',
            execution={'mode':'replay','review':{'mode':review},
                       'resource_policy':{'max_generations':cap},
                       'continuation_policy':{'completion_policy':c.FIXED_BUDGET}})

    def test_every_model_stop_reason_is_blocked_before_budget_use(self):
        self.start();self.respond()
        for reason in ('satisfied','budget','no_promising_attempt','execution_failure'):
            with self.subTest(reason=reason):
                result=self.h.operate(f.action('finish',video='v1',stop_reason=reason,message='Stop now.'),'early-'+reason)
                self.assertEqual(result['status'],'generation_budget_remaining')
                self.assertFalse(self.h.state.get('final'))
                self.assertFalse((self.h.output/'final.json').exists())
        self.assertEqual(c.usage(self.h.state)['submitted_render_requests'],1)

    def test_budget_used_then_deliver_earlier_candidate_and_verify(self):
        self.start();self.respond()
        for number in range(2,5):
            self.h.operate(f.action('generate',input_video='v1',prompt='Blue alternative '+str(number)),'generate-'+str(number))
            self.h.checkpoint()
            self.respond()
        self.assertFalse(c.completion_pending(self.h.state))
        self.assertFalse(c.view(self.h.state)['generation_available'])
        self.assertEqual(self.h.operate(f.action('generate',input_video='source',prompt='Extra'),'extra')['status'],'generation_unavailable')
        self.h.checkpoint()
        self.h=PlannerHarness(self.h.output,f.Scripted([
            f.action('observe',video='v1',count=2),
            f.action('finish',video='v1',message='The first candidate is the preferred result.')]))
        state=self.h.resume()
        self.assertEqual(state['status'],'complete')
        self.assertEqual(state['final']['video'],'v1')
        self.assertEqual(len(state['submitted_generation_ids']),4)
        self.assertEqual(len([j for j in state['jobs'].values() if j['kind']=='critique']),4)
        verify_delivery(self.h.output)

    def test_resume_keeps_fixed_policy_and_rejected_finish_can_continue(self):
        self.start(cap=2);self.respond();self.h.checkpoint()
        self.h=PlannerHarness(self.h.output,f.Scripted([
            f.action('finish',video='v1',message='Try early delivery.'),
            f.action('generate',input_video='source',prompt='Another implementation.')]))
        self.h.resume()
        events=self.h.state['events']
        self.assertTrue(any(e.get('result',{}).get('status')=='generation_budget_remaining' for e in events))
        self.assertEqual(self.h.state['jobs'][self.h.state['pending_tool']]['kind'],'generate')
        self.assertEqual(self.h.state['config']['continuation_policy']['completion_policy'],c.FIXED_BUDGET)
        self.assertEqual(len(self.h.state['submitted_generation_ids']),1)

    def test_planner_review_still_precedes_final_selection(self):
        self.start(cap=1,review='planner');self.respond(review=False);collect(self.h)
        self.assertEqual(self.h.state['pending_review']['video_id'],'v1')
        self.h.checkpoint()
        response=f.action('finish',video='v1',message='Select the reviewed result.')
        response['review']={'video_id':'v1','summary':'Scripted final candidate inspection.','findings':[]}
        self.h=PlannerHarness(self.h.output,f.Scripted([response]));state=self.h.resume()
        self.assertEqual(state['status'],'complete')
        self.assertEqual(state['reviews']['v1']['status'],'complete')
        self.assertFalse(any(j['kind']=='critique' for j in state['jobs'].values()))
        verify_delivery(self.h.output)

    def test_attempt_accounting_and_runtime_deadline_are_unchanged(self):
        self.start(cap=2);self.respond()
        state=copy.deepcopy(self.h.state)
        state['jobs']['failed']={'kind':'generate'}
        self.assertTrue(c.completion_pending(state))
        state['submitted_generation_ids'].append('failed')
        state['render_outcomes']={'failed':{'status':'failed','uncertain':False}}
        self.assertFalse(c.completion_pending(state))
        self.assertEqual(c.usage(state)['failed_render_attempts'],1)
        actual=self.h.state
        with patch('planner_harness.resources.time.time',return_value=actual['online_clock']['deadline_unix']+1):
            resources.settle(actual,'Real task deadline reached')
        self.assertEqual(actual['status'],'budget_exhausted')
        self.assertTrue(c.completion_pending(actual))
        self.assertNotEqual(actual['final']['outcome'],'selected_video')

    def test_legacy_policy_has_no_new_finish_gate(self):
        self.start();self.respond()
        del self.h.state['config']['continuation_policy']['completion_policy']
        self.assertIsNone(c.authorize_finish(self.h.state))

    def test_visible_policy_hides_exact_allowance(self):
        self.start()
        view=c.view(self.h.state)
        self.assertIn('complete generation allowance',view['budget_awareness'])
        self.assertNotIn('4',str(view))
        self.assertNotIn('hard_generation_limit',str(view))
        self.assertFalse(view['justification_required'])


class EntryTests(batch_fixture.Fixture):
    def test_new_batches_bind_both_loop_arms_and_review_modes_to_fixed_budget(self):
        for review in ('critic','planner'):
            self.output=self.root/review
            batch=self.prepare(methods=['full','none'],training_maintenance=False,review={'mode':review})
            self.assertEqual(batch['planner_completion_policy'],c.FIXED_BUDGET)
            for arm in ('full','none'):
                spec=benchmark.task_spec(batch['topics'][0],arm,batch,self.output/'profile.json')
                self.assertEqual(spec['execution']['continuation_policy']['completion_policy'],c.FIXED_BUDGET)
                self.assertEqual(spec['execution']['review']['mode'],review)
                self.assertIn('before finishing',spec['run_instructions'])
                old=copy.deepcopy(batch);old.pop('planner_completion_policy')
                self.assertNotEqual(unified.method_identity(arm,batch),unified.method_identity(arm,old))
            self.assertEqual(unified.method_identity('direct',batch),unified.method_identity('direct',old))


if __name__=='__main__':unittest.main()
