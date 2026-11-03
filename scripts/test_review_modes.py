"""Offline end-to-end tests for qualitative Critic and contextual Planner checks."""
import copy,json,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import test_planner_harness as legacy
from planner_harness import PlannerHarness
from planner_harness.common import load,save,sha
from planner_harness.execution import collect
from planner_harness.delivery import verify_delivery,verify_settlement
from critic_harness.adapter import critique
from vlm.openrouter import DEFAULT_MODEL


def action(name,**args):return {'action':name,'arguments':args}


class Planner(legacy.ScriptedModel):
    model='configured/custom-planner';reasoning_effort=None


class Reviewer:
    model=DEFAULT_MODEL;reasoning_effort='high'
    def __init__(self,actions=None):self.actions=list(actions or [{'action':'review','arguments':{'summary':'The actual visible result serves the requested blue treatment.','findings':['The supplied frames show the requested color.']}}]);self.inputs=[]
    def predict_text(self,**kwargs):
        self.inputs.append(kwargs)
        value=self.actions.pop(0)
        if isinstance(value,Exception):raise value
        return json.dumps(value(kwargs) if callable(value) else value)


class ReviewModes(unittest.TestCase):
    setUp,tearDown=legacy.Tests.setUp,legacy.Tests.tearDown
    def start(self,mode='critic',n=5,resource=None):
        self.model=Planner([action('generate',input_video='source',prompt='Actually make the scene blue.')])
        self.h=PlannerHarness(self.root/'run',self.model)
        return self.h.start(self.source,'Make the scene blue.',workflow='creative_loop_v1',mode='loop',max_generations=n,
            execution={'mode':'replay','review':{'mode':mode},**({'resource_policy':resource} if resource else {})})
    def render(self):
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        ids=self.h.state.setdefault('submitted_generation_ids',[])
        if job['id'] not in ids:ids.append(job['id'])
        self.h.state['generation_requests']=len(ids)
        save(self.h.output/'jobs'/job['id']/'response.json',{'status':'complete','mode':'replay','request_sha256':job['sha256'],
            'payload':{'video':{'path':str(self.source),'sha256':sha(self.source)},'replay_provenance':'Software fixture, no GPU.',
                'execution':{'requested_prompt':job['payload']['prompt'],'effective_prompt':job['payload']['prompt'],'input_sha256':job['payload']['input']['sha256']}}})
        collect(self.h);self.h.checkpoint()
    def review(self,model=None):
        model=model or Reviewer();job=self.h.state['jobs'][self.h.state['pending_tool']];folder=self.h.output/'jobs'/job['id']
        feedback=critique(job,folder,ROOT,model=model)
        save(folder/'response.json',{'status':'complete','mode':job['mode'],'request_sha256':job['sha256'],'payload':feedback})
        collect(self.h);self.h.checkpoint();return job,model,feedback
    def resume(self,responses):
        self.model=Planner(responses);self.h=PlannerHarness(self.h.output,self.model);return self.h.resume()
    def check(self,video='v1',summary='I inspected this generated result in the current task context.'):
        return {'video_id':video,'summary':summary}

    def test_default_critic_reviews_last_generation_and_finish_adds_no_review(self):
        self.start(n=1);self.render();job,reviewer,feedback=self.review()
        self.assertEqual(len(reviewer.inputs),1)
        visible=json.loads(reviewer.inputs[0]['user_text'])
        self.assertEqual(visible['actual_prompt'],'Actually make the scene blue.')
        self.assertEqual(visible['submitted_prompt'],'Actually make the scene blue.')
        self.assertEqual(visible['original_request'],'Make the scene blue.')
        self.assertNotIn('main_scores',feedback['report']);self.assertNotIn('task_metrics',feedback)
        state=self.resume([action('finish',video='v1',message='The checked result is suitable.')])
        self.assertEqual(state['status'],'complete');self.assertEqual(len(self.model.inputs),1)
        self.assertEqual(state['reviews']['v1']['status'],'complete')
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')
        original=(self.h.output/'state.json').read_bytes();self.h.resume(continue_delivery=True)
        self.assertEqual((self.h.output/'state.json').read_bytes(),original)
        self.assertEqual(sum(j['kind']=='critique' for j in state['jobs'].values()),1)
        self.assertFalse((self.h.output/'resource-ledger.json').exists())
        again=critique(job,self.h.output/'jobs'/job['id'],ROOT,model=reviewer)
        self.assertEqual(again,feedback);self.assertEqual(len(reviewer.inputs),1)

    def test_planner_checks_and_next_actions_share_context_and_last_is_required(self):
        self.start(mode='planner',n=2);self.render()
        self.assertIsNone(self.h.state['pending_tool']);self.assertEqual(self.h.state['pending_review']['video_id'],'v1')
        next_action=action('generate',input_video='v1',prompt='Coordinate the blue lighting.',justification='Use the checked result to coordinate this treatment.')
        next_action['review']=self.check()
        self.resume([next_action]);self.assertEqual(self.h.state['reviews']['v1']['mode'],'planner')
        self.render();finish=action('finish',video='v2',message='Both generated results were checked.')
        checked={**finish,'review':self.check('v2')}
        state=self.resume([finish,checked])
        self.assertEqual(len(self.model.inputs),2)
        self.assertTrue(any(e.get('result',{}).get('status')=='review_required' for e in state['events']))
        self.assertEqual(set(state['reviews']),{'v1','v2'});self.assertTrue(all(r['status']=='complete' for r in state['reviews'].values()))
        self.assertEqual(sum(j['kind']=='critique' for j in state['jobs'].values()),0)
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v2')
        self.assertEqual(json.loads(self.model.inputs[0]['user_text'])['task']['text'],'Make the scene blue.')

    def test_critic_uses_same_native_observer_pages_crop_and_reopen(self):
        self.start();self.render()
        def next_page(kwargs):
            payload=json.loads(kwargs['user_text']);args=payload['last_result']['next_arguments'];self.assertIsNotNone(args)
            return action('observe',**args)
        reviewer=Reviewer([action('observe',video='v1',mode='continuous',start=0,end=1,count=2,crop=[0,0,.5,.5]),next_page,
            action('observe',observation='review-0001'),action('review',summary='The inspected native-frame pages show local temporal continuity.')])
        job,reviewer,feedback=self.review(reviewer)
        self.assertEqual(len(reviewer.inputs),4)
        observations=feedback['observations'];continuous=[o for o in observations if o.get('mode')=='continuous']
        self.assertEqual(len(continuous),2)
        self.assertEqual(continuous[0]['frames'][0]['crop'],[0,0,.5,.5])
        self.assertEqual(set(f['frame_index'] for f in continuous[0]['frames']) & set(f['frame_index'] for f in continuous[1]['frames']),{continuous[0]['frames'][-1]['frame_index']})
        reopened=json.loads(reviewer.inputs[-1]['user_text'])['evidence']
        self.assertTrue(any(e['observation_id']=='review-0001' for e in reopened))
        self.assertNotIn('task_diagnostics',reviewer.inputs[-1]['system_prompt'])

    def test_tool_error_returns_to_reviewer_without_faking_observation(self):
        self.start();self.render()
        reviewer=Reviewer([action('observe',video='absent'),action('review',summary='The supplied overview supports a limited color judgment.')])
        _,reviewer,feedback=self.review(reviewer)
        self.assertIn('error',json.loads(reviewer.inputs[1]['user_text'])['last_result'])
        self.assertEqual(len(feedback['observations']),2)

    def test_failed_critic_is_explicit_and_does_not_gate_planner_delivery(self):
        self.start();self.render();job=self.h.state['jobs'][self.h.state['pending_tool']]
        save(self.h.output/'jobs'/job['id']/'response.json',{'status':'failed','mode':job['mode'],'request_sha256':job['sha256'],'error':'Known provider rejection.'})
        collect(self.h);self.h.checkpoint()
        self.assertEqual(self.h.state['status'],'running');self.assertEqual(self.h.state['reviews']['v1']['status'],'failed')
        self.assertIsNone(self.h.state.get('pending_review'))
        self.resume([action('finish',video='v1',message='I choose the candidate using my current observations; external review failed.')])
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')
        self.assertEqual(sum(j['kind']=='critique' for j in self.h.state['jobs'].values()),1)

    def test_deadline_keeps_unreviewed_fallback_without_claiming_review_or_confirmation(self):
        self.start(resource={'max_wall_seconds':1});self.render();time.sleep(1.03)
        state=self.resume([]);settlement=verify_settlement(self.h.output)
        self.assertEqual(state['status'],'budget_exhausted');self.assertEqual(settlement['selected'],'v1')
        self.assertEqual(settlement['selection']['origin'],'latest_generated_fallback')
        self.assertFalse(settlement['selection']['review_completed']);self.assertFalse(settlement['planner_confirmed'])
        self.assertEqual(state['reviews']['v1']['status'],'pending')

    def test_both_knowledge_scopes_have_review_skill_without_scoring_manual(self):
        from planner_harness.creative_knowledge import CreativeKnowledge
        for mode in ('full','none'):
            knowledge=CreativeKnowledge(ROOT,experience_mode=mode)
            self.assertIn('original task',knowledge.read('review')['text'])
            with self.assertRaises(ValueError):knowledge.read('score-definitions')
            if mode=='none':
                with self.assertRaises(ValueError):knowledge.read('EX-P-moment')

    def test_standalone_api_fixture_uses_live_whole_task_metering_without_old_count_caps(self):
        class APIPlanner(Planner):
            is_live_api=True;requires_live_budget=False
            def predict_text(self,**kwargs):
                self.last_usage={'input_tokens':12,'output_tokens':4,'cost':'0.001'}
                return super().predict_text(**kwargs)
        model=APIPlanner([action('finish',stop_reason='no_promising_attempt',message='No generation in this software fixture.')])
        h=PlannerHarness(self.root/'api-run',model)
        h.start(self.source,'Make blue.',workflow='creative_loop_v1',mode='loop',execution={'mode':'replay','review':{'mode':'planner'}})
        binding=load(h.output/'budget-scope.json');policy=load(Path(binding['root'])/'policy.json')
        self.assertEqual(policy['mode'],'live');self.assertNotEqual(binding['topic'],'offline-fixture')
        self.assertIsNone(policy['topic']['model_calls']);self.assertIsNone(policy['topic']['tokens'])
        ledger=load(Path(binding['root'])/'ledger.json');self.assertEqual(len(ledger['operations']),1)
        record=next(iter(ledger['operations'].values()));self.assertEqual(record['actual_usage']['cost'],'0.001')

    def test_api_environment_and_explicit_role_settings_match_frozen_review(self):
        from planner_harness.creative import role_settings
        from critic_harness.one_shot import frozen_profile
        from vlm.openrouter import OpenRouterVisionModel
        with patch.dict('os.environ',{'OPENROUTER_API_KEY':'software-fixture','LHA_API_ONLINE_CRITIC_MODEL':'fixture/role-model','LHA_API_ONLINE_CRITIC_REASONING_EFFORT':'medium'}):
            settings=role_settings({},'online_critic');client=OpenRouterVisionModel(role='online_critic')
            self.assertEqual(settings,{'model':client.model,'reasoning_effort':client.reasoning_effort})
            frozen=frozen_profile();self.assertEqual(frozen['model'],client.model);self.assertEqual(frozen['reasoning_effort'],client.reasoning_effort)
            explicit=role_settings({'critic':{'model':'fixture/explicit','reasoning_effort':None}},'online_critic')
            exact=OpenRouterVisionModel(role='online_critic',**explicit)
            self.assertEqual(exact.model,'fixture/explicit');self.assertIsNone(exact.reasoning_effort)

    def test_qualitative_transport_recovery_reopens_original_current_call(self):
        from planner_harness.model_call import ModelTransportError
        from planner_harness.recovery import recover_tool
        self.start();self.render();job=self.h.state['jobs'][self.h.state['pending_tool']];folder=self.h.output/'jobs'/job['id']
        reviewer=Reviewer([ConnectionError('Temporary software-fixture transport failure'),action('review',summary='Original review resumed on the same evidence.')])
        with self.assertRaises(ModelTransportError):critique(job,folder,ROOT,model=reviewer)
        save(folder/'response.json',{'status':'failed','mode':job['mode'],'request_sha256':job['sha256'],'failure_kind':'model_transport','error':'Known fixture transport failure.'})
        recover_tool(self.h.output,job['id'],'retry-review','Retry the known failed original software-fixture request.')
        self.h.state=load(self.h.output/'state.json');self.review(reviewer)
        self.assertEqual(len(reviewer.inputs),2);self.assertEqual(reviewer.inputs[0]['user_text'],reviewer.inputs[1]['user_text'])
        self.assertEqual(self.h.state['reviews']['v1']['status'],'complete')
        self.assertEqual(sum(j['kind']=='critique' for j in self.h.state['jobs'].values()),1)

    def test_planner_summary_is_available_to_post_task_maintenance(self):
        from planner_harness.experience_usage import project_run
        self.start(mode='planner');self.render()
        finish={**action('finish',video='v1',message='Deliver after the contextual check.'),'review':self.check(summary='Specific checked outcome for maintenance.')}
        self.resume([finish]);joined=project_run(self.h.output)
        reports=[r['report'] for r in joined['online_feedback'] if r['video_id']=='v1']
        self.assertIn({'summary':'Specific checked outcome for maintenance.'},reports)


if __name__=='__main__':unittest.main()
