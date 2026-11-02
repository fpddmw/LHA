"""Offline reused/new review and real post-proposal Planner confirmation checks."""
import copy
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
from planner_harness.delivery import verify_delivery
from planner_harness.execution import collect
from critic_harness.adapter import critique

action=fixtures.action


class LowCritic(fixtures.ScriptedCritic):
    def predict_text(self,**kwargs):
        self.inputs.append(kwargs)
        report=fixtures.review_fixture(kwargs['user_text'])
        if json.loads(kwargs['user_text']).get('stage') != 'report':
            return json.dumps(report)
        if 'main_scores' not in report:return json.dumps(report)
        for row in report['main_scores'].values():
            if row['status']=='scored':row['score']=0
        report['main_scores']['temporal_consistency'].update(status='unknown',score=None,evidence_refs=[])
        return json.dumps(report)


class DeliveryReviewTests(unittest.TestCase):
    setUp,tearDown=legacy.Tests.setUp,legacy.Tests.tearDown
    respond=fixtures.CreativeTests.respond
    resume=fixtures.CreativeTests.resume

    def start(self,mode='full'):
        self.h=PlannerHarness(self.root/'run',fixtures.Scripted([action('generate',input_video='source',prompt='Make it blue.')]))
        self.h.start(self.source,'Make it blue.',mode='loop',workflow='creative_loop_v1',
                     execution={'mode':'replay','experience_mode':mode})
        self.respond(review=False)
        collect(self.h)

    def finish(self,video='v1'):
        count=1 if self.h.state.get('active_delivery_proposal') else 2
        self.h.model=fixtures.Scripted([action('finish',video=video,message='The visible tradeoffs are acceptable for this task.',stop_reason='satisfied') for _ in range(count)])
        return self.h.resume(additional_turns=8 if self.h.state['status']=='budget_exhausted' else 0)

    def propose(self,video='v1'):
        # A direct local action has no returned model input proving exposure.
        self.h.operate(action('finish',video=video,message='Manual fixture proposal.'),'manual-proposal-'+str(len(self.h.state.get('delivery_reviews',{}))))
        self.assertNotEqual(self.h.state['status'],'complete')
        self.h.checkpoint()


    def review(self,critic=None):
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        folder=self.h.output/'jobs'/job['id'];critic=critic or fixtures.ScriptedCritic()
        result=critique(job,folder,ROOT,model=critic)
        save(folder/'response.json',{'status':'complete','mode':job['mode'],'request_sha256':job['sha256'],'payload':result})
        collect(self.h)
        return job,critic

    def test_ordinary_full_review_reused_with_one_real_finish(self):
        self.start();ordinary,critic=self.review()
        calls_before_delivery = len(critic.inputs)
        self.assertEqual(sum(json.loads(c['user_text']).get('stage') == 'report' for c in critic.inputs), 1)
        state=self.resume([action('finish',video='v1',message='Propose the retained candidate.'),
                           action('finish',video='v1',message='The complete report supports this choice with stated tradeoffs.')])
        self.assertEqual(state['status'],'complete');self.assertEqual(len(critic.inputs),calls_before_delivery)
        self.assertEqual(sum(j['kind']=='critique' for j in state['jobs'].values()),1)
        proof=state['final']['delivery_review'];self.assertEqual(proof['review_origin'],'reused')
        self.assertEqual(proof['review_job'],ordinary['id'])
        first=next(e for e in state['events'] if e['event_id']==proof['proposal_event_id'])
        self.assertEqual(first['result']['outcome'],'selected_video')
        self.assertEqual(proof['proposal_event_id'],proof['planner_event_id'])
        self.assertEqual(len(self.model.inputs),1)
        before=json.loads(load(self.h.output/'calls'/proof['proposal_event_id']/'input.json')['user_text'])
        after=json.loads(load(self.h.output/'calls'/proof['planner_event_id']/'input.json')['user_text'])
        self.assertIn(ordinary['id'],before['evaluations'])
        self.assertEqual(before['delivery_review']['status'],'no_active_proposal')
        self.assertEqual(after['evaluations'][ordinary['id']]['report'],state['evaluations'][ordinary['id']]['report'])
        verify_delivery(self.h.output)

    def test_report_alone_or_direct_finish_cannot_confirm(self):
        self.start();self.review();self.propose()
        self.assertEqual(self.h.state['status'],'running');self.assertNotIn('final',self.h.state)
        with self.assertRaises(ValueError):verify_delivery(self.h.output)
        with self.assertRaisesRegex(ValueError,'new Planner response'):
            self.h.operate(action('finish',video='v1',message='Manually asserted acceptance.'),'fake-confirmation')

    def test_real_post_report_finish_accepts_low_scores_unknowns_and_full_report(self):
        self.start();job,critic=self.review(LowCritic());state=self.finish()
        self.assertEqual(state['status'],'complete')
        proof=state['final']['delivery_review'];self.assertEqual(proof['proposal_event_id'],proof['planner_event_id'])
        actual=load(self.h.output/'calls'/proof['planner_event_id']/'input.json')
        report=json.loads(actual['user_text'])['evaluations'][job['id']]['report']
        self.assertEqual(report,state['evaluations'][job['id']]['report'])
        self.assertEqual(report['main_scores']['instruction_adherence']['score'],0)
        self.assertIsNone(report['main_scores']['temporal_consistency']['score'])
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')
        self.assertIn('tradeoffs',state['final']['message'])

    def test_same_proposal_recovery_has_no_extra_call_and_initial_finish_is_not_confirmation(self):
        self.start();job_id=self.h.state['pending_tool']
        waiting=self.resume([])
        self.assertEqual(waiting['pending_tool'],job_id);self.assertEqual(self.model.inputs,[])
        self.assertEqual(sum(j['kind']=='critique' for j in waiting['jobs'].values()),1)
        self.review();self.propose();proposal_id=self.h.state['active_delivery_proposal']
        original_event=self.h.state['delivery_reviews'][proposal_id]['event_id']
        with self.assertRaisesRegex(ValueError,'new Planner response'):
            self.h.operate(action('finish',video='v1',message='Cached initial finish.'),original_event)
        self.h.checkpoint();self.finish();self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')

    def test_new_generation_invalidates_proposal_and_later_finish_reuses_valid_report(self):
        self.start();self.review();self.propose()
        self.resume([action('note',text='A useful observation.'),action('generate',input_video='v1',prompt='Another blue treatment.')])
        first=next(iter(self.h.state['delivery_reviews'].values()))
        self.assertEqual(first['status'],'superseded');self.assertIsNone(self.h.state['active_delivery_proposal'])
        self.respond();self.resume([action('finish',video='v1',message='Propose v1 again.'),action('finish',video='v1',message='Confirm after reviewing this proposal.')])
        self.assertEqual(len(self.h.state['delivery_reviews']),2)
        self.assertEqual(first['review_job'],self.h.state['final']['delivery_review']['review_job'])
        verify_delivery(self.h.output)

    def test_changed_candidate_invalidates_even_when_selecting_back(self):
        self.start();self.review();self.resume([action('generate',input_video='source',prompt='Second candidate.')]);self.respond()
        self.propose()
        self.resume([action('delivery_candidate',video='v2'),action('delivery_candidate',video='v1'),
                     action('finish',video='v1',message='Reconsidered the earlier candidate.'),
                     action('finish',video='v1',message='Confirm the retained result after this report.')])
        self.assertEqual(len(self.h.state['delivery_reviews']),2)
        self.assertEqual(next(iter(self.h.state['delivery_reviews'].values()))['status'],'superseded')

    def test_comparison_focus_and_supplemental_checks_are_reused_unchanged(self):
        self.start();self.review()
        self.resume([action('generate',input_video='source',prompt='Second candidate.',review_focus={
            'compare_to':'v1','focus':'Inspect visible geometry.','extra_checks':['Is the rim visibly blue?']})])
        self.respond(review=False);collect(self.h)
        job,critic=self.review()
        calls_before_delivery = len(critic.inputs)
        self.assertEqual(sum(json.loads(c['user_text']).get('stage') == 'report' for c in critic.inputs), 1)
        self.resume([action('finish',video='v2',message='Propose v2.'),action('finish',video='v2',message='The comparison and uncertainty are acceptable.')])
        proof=self.h.state['final']['delivery_review']
        self.assertEqual(proof['review_job'],job['id']);self.assertEqual(len(critic.inputs),calls_before_delivery)
        visible=json.loads(load(self.h.output/'calls'/proof['planner_event_id']/'input.json')['user_text'])
        self.assertTrue(visible['evaluations'][job['id']]['report']['comparisons'])
        self.assertTrue(visible['evaluations'][job['id']]['report']['extra_checks'])
        verify_delivery(self.h.output)

    def test_failed_or_tampered_review_stays_incomplete(self):
        self.start();job=self.h.state['jobs'][self.h.state['pending_tool']]
        folder=self.h.output/'jobs'/job['id']
        save(folder/'response.json',{'status':'failed','mode':'replay','request_sha256':job['sha256'],'error':'Retained invalid report.'})
        collect(self.h);self.h.checkpoint()
        self.assertEqual(self.h.state['status'],'running');self.assertNotIn('final',self.h.state)
        state=self.resume([action('finish',video='v1',stop_reason='no_promising_attempt',message='No reviewed candidate is available.')])
        self.assertEqual(state['status'],'delivery_blocked');self.assertIn('final',state)
        self.assertIsNone(state['pending_tool'])
        with self.assertRaises(ValueError):verify_delivery(self.h.output)

    def test_invalid_cached_profile_blocks_replacement_review(self):
        self.start();old,critic=self.review()
        self.h.state['evaluations'][old['id']]['profile_sha256']='wrong-profile'
        path=self.h.output/'jobs'/old['id']/'response.json';response=load(path)
        response['payload']['profile_sha256']='wrong-profile';save(path,response)
        save(path.with_name('collected.json'),response);self.h.checkpoint()
        from planner_harness.integrity import IntegrityError
        with self.assertRaises(IntegrityError):
            self.finish()
        self.assertEqual(sum(j['kind']=='critique' for j in self.h.state['jobs'].values()),1)
        self.assertEqual(self.h.state['status'],'transport_or_runtime_error')

    def test_invalid_ordinary_answer_cannot_be_retried_through_delivery(self):
        class InvalidCritic(fixtures.ScriptedCritic):
            def predict_text(self, **kwargs):
                self.inputs.append(kwargs)
                if json.loads(kwargs['user_text']).get('stage') == 'report':
                    return '{}'
                return json.dumps(fixtures.review_fixture(kwargs['user_text']))
        self.start()
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        folder=self.h.output/'jobs'/job['id']; critic=InvalidCritic()
        with self.assertRaises(ValueError):
            critique(job,folder,ROOT,model=critic)
        calls_before_delivery = len(critic.inputs)
        self.assertEqual(sum(json.loads(c['user_text']).get('stage') == 'report' for c in critic.inputs), 2)
        raw=(folder/'one-shot-critic/call/response.txt').read_bytes()
        save(folder/'response.json',{'status':'failed','mode':job['mode'],
            'request_sha256':job['sha256'],'error':'Invalid ordinary report; retain the answer.'})
        collect(self.h); self.h.checkpoint()
        state=self.resume([action('finish',video='v1',message='Try the original candidate.'),action('finish',video='v1',stop_reason='no_promising_attempt',message='The original report is unavailable; stop explicitly.')])
        self.assertEqual(state['status'],'delivery_blocked')
        self.assertEqual(len(critic.inputs),calls_before_delivery)
        self.assertEqual(sum(j['kind']=='critique' for j in state['jobs'].values()),1)
        self.assertEqual((folder/'one-shot-critic/call/response.txt').read_bytes(),raw)
        self.assertIn('final',state)

    def test_both_experience_modes_and_tampered_confirmation(self):
        for mode in ['full','none']:
            with self.subTest(mode=mode):
                if (self.root/'run').exists():
                    self.h=PlannerHarness(self.root/('run-'+mode),fixtures.Scripted([action('generate',input_video='source',prompt='Blue.')]))
                    self.h.start(self.source,'Make it blue.',mode='loop',workflow='creative_loop_v1',execution={'mode':'replay','experience_mode':mode});self.respond()
                else:self.start(mode)
                if self.h.state.get('pending_tool'):self.review()
                self.finish();verify_delivery(self.h.output)
                state=load(self.h.output/'state.json');state['final']['delivery_review']['candidate_sha256']='tampered'
                save(self.h.output/'state.json',state)
                with self.assertRaises(ValueError):verify_delivery(self.h.output)

    def test_resume_cannot_return_manually_assembled_complete_flag(self):
        self.start();self.review();self.finish()
        state=load(self.h.output/'state.json');state['final'].pop('delivery_review')
        save(self.h.output/'state.json',state)
        with self.assertRaisesRegex(ValueError,'lacks proposal|Settled final record changed'):
            self.h.resume()


if __name__=='__main__':unittest.main()
