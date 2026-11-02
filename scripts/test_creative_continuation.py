"""Offline continuation gating, factual spending and hidden-policy projection checks."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import test_planner_harness as legacy
import test_creative_loop as fixtures
from planner_harness import PlannerHarness
from planner_harness.common import load,save
from planner_harness.execution import collect
from planner_harness.continuation import view,usage,phase
from planner_harness.delivery import verify_delivery
from critic_harness.adapter import critique

action=fixtures.action


class ContinuationTests(unittest.TestCase):
    setUp,tearDown=legacy.Tests.setUp,legacy.Tests.tearDown
    respond=fixtures.CreativeTests.respond

    def start(self,mode='full',cap=None):
        self.model=fixtures.Scripted([action('generate',input_video='source',prompt='Blue.')])
        self.h=PlannerHarness(self.root/'run',self.model)
        self.h.start(self.source,'Make the scene blue.',mode='loop',workflow='creative_loop_v1',execution={
            'mode':'replay','experience_mode':mode,'seed_sequence':{'start':42,'step':1},
            'continuation_policy':{'hard_generation_limit':cap}})

    def collect_render(self,seconds=None):
        self.h.checkpoint()
        self.respond(review=False)
        if seconds is not None:
            path=self.h.output/'jobs'/self.h.state['pending_tool']/'response.json';data=load(path)
            data['payload']['execution']['generation_seconds']=seconds;save(path,data)
        collect(self.h)
        fixtures.drain_review(self.h)

    def test_two_successes_then_generation_without_an_explanation(self):
        self.start();self.collect_render(1.5)
        self.h.operate(action('generate',input_video='source',prompt='Second.'),'second');self.collect_render(2.5)
        result=self.h.operate(action('generate',input_video='source',prompt='Third.'),'third')
        self.assertEqual(result['status'],'pending')
        job=self.h.state['jobs'][result['job_id']]
        self.assertEqual(job['payload']['renderer']['seed'],44)
        self.assertNotIn('justification',json.dumps(job))
        record=load(self.h.output/'jobs'/job['id']/'continuation.json')
        self.assertIsNone(record['justification']);self.assertEqual(record['prompt'],'Third.')
        self.assertEqual(usage(self.h.state)['known_rendering_elapsed_seconds'],4.0)

    def test_compliant_prompt_and_justification_use_one_model_response_and_stable_recovery(self):
        self.start();self.collect_render();self.h.operate(action('generate',input_video='source',prompt='Second.'),'second');self.collect_render()
        self.h.checkpoint()
        model=fixtures.Scripted([action('generate',input_video='v1',prompt='Actual revised prompt.',justification='x')])
        self.h=PlannerHarness(self.h.output,model);self.h.resume()
        self.assertEqual(len(model.inputs),1)
        job_id=self.h.state['pending_tool'];before=self.h.state['generation_requests']
        request=load(self.h.output/'jobs'/job_id/'request.json')
        self.h=PlannerHarness(self.h.output,fixtures.Scripted([]));self.h.resume()
        self.assertEqual(self.h.state['pending_tool'],job_id);self.assertEqual(self.h.state['generation_requests'],before)
        self.assertEqual(load(self.h.output/'jobs'/job_id/'request.json'),request)
        self.assertEqual(self.h.model.inputs,[])

    def test_four_request_budget_hints_and_locks_without_semantic_judging(self):
        self.start()
        notices=[]
        for n,expected in enumerate(('exploration','continuation','deliberate'),1):
            self.collect_render()
            self.assertEqual(phase(self.h.state),expected)
            visible=view(self.h.state);notices.append(visible['budget_awareness'])
            self.assertFalse(visible['justification_required'])
            self.h.operate(action('generate',input_video='source',prompt='Blue again.',justification='x'),'repeat-'+str(n))
        self.collect_render()
        self.assertEqual(self.h.state['generation_requests'],4)
        self.assertEqual(len(set(notices)),3)
        self.assertEqual(phase(self.h.state),'frozen')
        result=self.h.operate(action('generate',input_video='source',prompt='Fifth.',justification='x'),'refused-fifth')
        self.assertEqual(result['status'],'generation_unavailable')
        self.assertEqual(self.h.state['generation_requests'],4)
        self.assertFalse(view(self.h.state)['justification_required'])
        self.assertEqual(view(self.h.state)['continuation_questions'],[])
        for notice in notices+[view(self.h.state)['budget_awareness']]:
            for leak in ('five','six','half','remaining','last attempt','%'):
                self.assertNotIn(leak,notice.lower())
        self.assertEqual(sum(j['kind']=='critique' for j in self.h.state['jobs'].values()),4)
        self.assertEqual({r['justification'] for r in self.h.state['generation_decisions'].values() if r['justification'] is not None},{'x'})

    def test_actual_cap_locks_only_generate_and_keeps_full_confirmation_available(self):
        self.start(cap=1);self.collect_render();self.h.checkpoint()
        model=fixtures.Scripted([action('generate',input_video='source',prompt='Another.',justification='x'),
            action('observe',video='v1',count=2),action('note',text='Retain the candidate with its visible limitations.'),
            action('observe',video='source',count=2),action('finish',video='v1',message='Propose the retained candidate.'),
            action('finish',video='v1',message='Confirm the retained result with the reported limitations.')])
        self.h=PlannerHarness(self.h.output,model);state=self.h.resume()
        self.assertEqual(state['status'],'complete');self.assertEqual(state['generation_requests'],1)
        self.assertTrue(any(e.get('result',{}).get('status')=='generation_unavailable' for e in state['events']))
        self.assertEqual(sum(j['kind']=='critique' for j in state['jobs'].values()),1)
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')

    def test_failures_count_for_the_cap_and_request_based_reminders_without_advancing_seed(self):
        self.start();job=self.h.state['jobs'][self.h.state['pending_tool']]
        save(self.h.output/'jobs'/job['id']/'response.json',{'request_sha256':job['sha256'],'mode':'replay','status':'failed','error':'Definite synthetic failure.'})
        self.h.state['submitted_generation_ids']=[job['id']];self.h.state['generation_requests']=1
        collect(self.h)
        self.assertEqual(usage(self.h.state)['failed_render_attempts'],1)
        self.assertFalse(view(self.h.state)['justification_required'])
        self.h.operate(action('generate',input_video='source',prompt='Retry a new definite attempt.'),'after-failure')
        self.assertEqual(self.h.state['jobs'][self.h.state['pending_tool']]['payload']['renderer']['seed'],42)
        self.collect_render()
        self.assertTrue(view(self.h.state)['generation_available'])
        self.assertFalse(view(self.h.state)['justification_required'])
        self.assertEqual(phase(self.h.state),'continuation')
        self.assertEqual(usage(self.h.state)['generated_candidates'],1)
        self.assertEqual(usage(self.h.state)['submitted_render_requests'],2)

    def test_uncertain_outcome_is_unavailable_and_no_replacement_is_submitted(self):
        self.start();job=self.h.state['jobs'][self.h.state['pending_tool']]
        save(self.h.output/'jobs'/job['id']/'response.json',{'request_sha256':job['sha256'],'mode':'replay','status':'failed',
                                                          'outcome_unknown':True,'error':'Synthetic uncertain dispatch.'})
        self.h.state['submitted_generation_ids']=[job['id']];self.h.state['generation_requests']=1
        self.assertFalse(collect(self.h));self.assertFalse(view(self.h.state)['generation_available'])
        self.assertEqual(usage(self.h.state)['uncertain_render_attempts'],1)
        self.assertEqual(usage(self.h.state)['failed_render_attempts'],0)
        with self.assertRaises(ValueError):self.h.operate(action('generate',input_video='source',prompt='Replacement.'),'replacement')
        self.assertEqual(self.h.state['generation_requests'],1)

    def test_visible_manual_context_errors_and_receipts_hide_operator_policy(self):
        forbidden=['max_generations','generation_limit','hard_generation_limit','free_successes','deliberate_after_successes',
                   'free_requests','deliberate_after_requests','strong_after_requests',
                   'limit_meaning','near exhaustion','last attempt','half consumed','remaining budget','unlimited generation']
        for mode in ['full','none']:
            with self.subTest(mode=mode):
                self.root=self.root/mode;self.root.mkdir();self.start(mode)
                initial=self.model.inputs[0]
                for token in forbidden:self.assertNotIn(token,initial['system_prompt']+'\n'+initial['user_text'])
                context=json.loads(initial['user_text'])
                self.assertNotIn('resource_status',context)
                self.assertNotIn('continuation_policy',context['execution_profile'])
                audit=load(self.h.output/'calls/event-0001/continuation-policy.json')
                self.assertEqual(audit['policy']['hard_generation_limit'],4)
                self.h.state['config']['context_version']=1
                self.assertNotIn('generation_limit',self.h.context()[0])
                self.h.state['config']['context_version']=2
                self.collect_render();self.h.operate(action('generate',input_video='source',prompt='Second.'),'second');self.collect_render()
                result=self.h.operate(action('generate',input_video='source',prompt='Third.'),'missing')
                visible=self.h.system+'\n'+self.h.context()[0]+'\n'+json.dumps(result)
                for token in forbidden:self.assertNotIn(token,visible)
                self.assertFalse(result['continuation']['justification_required'])

    def test_model_resource_recovery_keeps_generation_frozen(self):
        from planner_harness.delivery import continue_budget_stop
        self.start(cap=1);self.collect_render()
        self.h.state['status']='budget_exhausted'
        self.h.state['final']={'stop_reason':'budget'}
        turns=self.h.state['config']['resource_policy']['max_turns']
        continue_budget_stop(self.h.state)
        self.assertEqual(self.h.state['config']['resource_policy']['max_turns'],turns)
        self.assertEqual(self.h.state['config']['resource_policy']['max_generations'],1)
        self.assertEqual(self.h.state['config']['continuation_policy']['hard_generation_limit'],1)
        self.assertFalse(view(self.h.state)['generation_available'])
        self.assertEqual(self.h.operate(action('generate',input_video='source',prompt='More.'),'after-recovery')['status'],'generation_unavailable')

    def test_operator_configuration_cannot_raise_the_approved_cap(self):
        from planner_harness.resources import configure
        from planner_harness.continuation import configure as continuation_configure
        state={'config':{}}
        self.assertEqual(configure(state,{'max_generations':6})['max_generations'],6)
        self.assertEqual(continuation_configure(state,{'hard_generation_limit':6})['hard_generation_limit'],6)

    def test_server_configuration_uses_the_same_private_policy_without_rendering(self):
        from server_runtime.queue import Queue
        from server_runtime.service import Service
        from planner_harness.common import sha
        directory=self.root/'service';queue=Queue(directory/'queue.sqlite3')
        model=fixtures.Scripted([action('generate',input_video='source',prompt='Blue.')])
        service=Service(queue,directory,ROOT,{'workflow':'creative_loop_v1','continuation_policy':{'hard_generation_limit':1}},
                        model_factory=lambda role:model,renderer=object())
        service.submit({'id':'policy-fixture','source':str(self.source),'source_sha256':sha(self.source),'request':'Make it blue.',
                        'execution':{'mode':'live','renderer':{'backend':'fixture'}}})
        job=queue.claim('llm','software-fixture')
        result=service(job,directory/'job-result')
        self.assertEqual(result['state']['config']['continuation_policy']['hard_generation_limit'],1)
        self.assertNotIn('continuation_policy',result['state']['config']['execution'])
        self.assertNotIn('hard_generation_limit',model.inputs[0]['user_text'])


if __name__=='__main__':unittest.main()
