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
        for row in report['main_scores'].values():row['score']=0
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
        self.respond()

    def finish(self,video='v1'):
        return self.resume([action('finish',video=video,message='The visible tradeoffs are acceptable for this task.',stop_reason='satisfied')])

    def review(self,critic=None):
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        folder=self.h.output/'jobs'/job['id'];critic=critic or fixtures.ScriptedCritic()
        result=critique(job,folder,ROOT,model=critic)
        save(folder/'response.json',{'status':'complete','mode':job['mode'],'request_sha256':job['sha256'],'payload':result})
        return job,critic

    def test_ordinary_review_reused_with_new_proposal_input_and_real_confirmation(self):
        self.start();self.resume([action('critique',video='v1')]);ordinary,critic=self.review()
        state=self.resume([action('finish',video='v1',message='Propose the retained candidate.'),
                           action('finish',video='v1',message='The complete report supports this choice with stated tradeoffs.')])
        self.assertEqual(state['status'],'complete');self.assertEqual(len(critic.inputs),1)
        self.assertEqual(sum(j['kind']=='critique' for j in state['jobs'].values()),1)
        proof=state['final']['delivery_review'];self.assertEqual(proof['review_origin'],'reused')
        self.assertEqual(proof['review_job'],ordinary['id'])
        first=next(e for e in state['events'] if e['event_id']==proof['proposal_event_id'])
        self.assertEqual(first['result']['delivery_status'],'proposed_not_confirmed')
        before=json.loads(load(self.h.output/'calls'/proof['proposal_event_id']/'input.json')['user_text'])
        after=json.loads(load(self.h.output/'calls'/proof['planner_event_id']/'input.json')['user_text'])
        self.assertIn(ordinary['id'],before['evaluations'])
        self.assertEqual(before['delivery_review']['status'],'no_active_proposal')
        self.assertEqual(after['delivery_review']['report'],state['evaluations'][ordinary['id']]['report'])
        verify_delivery(self.h.output)

    def test_report_alone_or_direct_finish_cannot_confirm(self):
        self.start();self.finish();self.review();collect(self.h)
        self.assertEqual(self.h.state['status'],'running');self.assertNotIn('final',self.h.state)
        with self.assertRaises(ValueError):verify_delivery(self.h.output)
        with self.assertRaisesRegex(ValueError,'new Planner response'):
            self.h.operate(action('finish',video='v1',message='Manually asserted acceptance.'),'fake-confirmation')

    def test_real_post_report_finish_accepts_low_scores_unknowns_and_full_report(self):
        self.start();self.finish();job,critic=self.review(LowCritic());state=self.finish()
        self.assertEqual(state['status'],'complete')
        proof=state['final']['delivery_review'];self.assertNotEqual(proof['proposal_event_id'],proof['planner_event_id'])
        actual=load(self.h.output/'calls'/proof['planner_event_id']/'input.json')
        report=json.loads(actual['user_text'])['delivery_review']['report']
        self.assertEqual(report,state['evaluations'][job['id']]['report'])
        self.assertEqual(report['main_scores']['instruction_adherence']['score'],0)
        self.assertIsNone(report['main_scores']['temporal_consistency']['score'])
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')
        self.assertIn('tradeoffs',state['final']['message'])

    def test_same_proposal_recovery_has_no_extra_call_and_initial_finish_is_not_confirmation(self):
        self.start();state=self.finish();job_id=state['pending_tool'];proposal_id=state['active_delivery_proposal']
        waiting=self.resume([])
        self.assertEqual(waiting['pending_tool'],job_id);self.assertEqual(self.model.inputs,[])
        self.assertEqual(len([j for j in waiting['jobs'].values() if j['payload'].get('delivery_review')]),1)
        self.review();collect(self.h)
        original_event=self.h.state['delivery_reviews'][proposal_id]['event_id']
        with self.assertRaisesRegex(ValueError,'new Planner response'):
            self.h.operate(action('finish',video='v1',message='Cached initial finish.'),original_event)
        self.h.checkpoint();self.finish();self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')

    def test_new_generation_invalidates_proposal_and_later_finish_reuses_valid_report(self):
        self.start();self.finish();self.review()
        self.resume([action('note',text='A useful observation.'),action('generate',input_video='v1',prompt='Another blue treatment.')])
        first=next(iter(self.h.state['delivery_reviews'].values()))
        self.assertEqual(first['status'],'superseded');self.assertIsNone(self.h.state['active_delivery_proposal'])
        self.respond();self.resume([action('finish',video='v1',message='Propose v1 again.'),action('finish',video='v1',message='Confirm after reviewing this proposal.')])
        self.assertEqual(len(self.h.state['delivery_reviews']),2)
        self.assertEqual(first['review_job'],self.h.state['final']['delivery_review']['review_job'])
        verify_delivery(self.h.output)

    def test_changed_candidate_invalidates_even_when_selecting_back(self):
        self.start();self.resume([action('generate',input_video='source',prompt='Second candidate.')]);self.respond()
        self.finish();self.review()
        self.resume([action('delivery_candidate',video='v2'),action('delivery_candidate',video='v1'),
                     action('finish',video='v1',message='Reconsidered the earlier candidate.'),
                     action('finish',video='v1',message='Confirm the retained result after this report.')])
        self.assertEqual(len(self.h.state['delivery_reviews']),2)
        self.assertEqual(next(iter(self.h.state['delivery_reviews'].values()))['status'],'superseded')

    def test_comparison_focus_and_supplemental_checks_are_reused_unchanged(self):
        self.start();self.resume([action('generate',input_video='source',prompt='Second candidate.')]);self.respond()
        self.resume([action('critique',video='v1',compare_to='v2',focus='Inspect visible geometry.',extra_checks=['Is the rim visibly blue?'])])
        job,critic=self.review()
        self.resume([action('finish',video='v1',message='Propose v1.'),action('finish',video='v1',message='The comparison and uncertainty are acceptable.')])
        proof=self.h.state['final']['delivery_review']
        self.assertEqual(proof['review_job'],job['id']);self.assertEqual(len(critic.inputs),1)
        visible=json.loads(load(self.h.output/'calls'/proof['planner_event_id']/'input.json')['user_text'])
        self.assertTrue(visible['delivery_review']['report']['comparisons'])
        self.assertTrue(visible['delivery_review']['report']['extra_checks'])
        verify_delivery(self.h.output)

    def test_failed_or_tampered_review_stays_incomplete(self):
        self.start();self.finish();job=self.h.state['jobs'][self.h.state['pending_tool']]
        folder=self.h.output/'jobs'/job['id']
        save(folder/'response.json',{'status':'failed','mode':'replay','request_sha256':job['sha256'],'error':'Retained invalid report.'})
        state=self.resume([])
        self.assertEqual(state['status'],'needs_reconciliation');self.assertNotIn('final',state)
        self.assertEqual(state['pending_tool'],job['id'])
        with self.assertRaises(ValueError):verify_delivery(self.h.output)

    def test_invalid_cached_profile_is_not_reused_and_new_request_is_bound_neutrally(self):
        self.start();self.resume([action('critique',video='v1')]);old,critic=self.review()
        collect(self.h)
        self.h.state['evaluations'][old['id']]['profile_sha256']='wrong-profile'
        path=self.h.output/'jobs'/old['id']/'response.json';response=load(path)
        response['payload']['profile_sha256']='wrong-profile';save(path,response)
        save(path.with_name('collected.json'),response);self.h.checkpoint()
        state=self.finish();new=state['jobs'][state['pending_tool']]
        self.assertNotEqual(new['id'],old['id'])
        self.assertEqual(set(new['payload']['videos']),{'source','v1'})
        self.assertEqual(new['payload']['focus'],'');self.assertEqual(new['payload']['extra_checks'],[])
        self.assertNotIn('tradeoffs',json.dumps(new['payload']))
        self.assertNotIn('final',state)

    def test_both_experience_modes_and_tampered_confirmation(self):
        for mode in ['full','none']:
            with self.subTest(mode=mode):
                if (self.root/'run').exists():
                    self.h=PlannerHarness(self.root/('run-'+mode),fixtures.Scripted([action('generate',input_video='source',prompt='Blue.')]))
                    self.h.start(self.source,'Make it blue.',mode='loop',workflow='creative_loop_v1',execution={'mode':'replay','experience_mode':mode});self.respond()
                else:self.start(mode)
                self.finish();self.review();self.finish();verify_delivery(self.h.output)
                state=load(self.h.output/'state.json');state['final']['delivery_review']['candidate_sha256']='tampered'
                save(self.h.output/'state.json',state)
                with self.assertRaises(ValueError):verify_delivery(self.h.output)

    def test_resume_cannot_return_manually_assembled_complete_flag(self):
        self.start();self.finish();self.review();self.finish()
        state=load(self.h.output/'state.json');state['final'].pop('delivery_review')
        save(self.h.output/'state.json',state)
        with self.assertRaisesRegex(ValueError,'lacks proposal'):
            self.h.resume()


if __name__=='__main__':unittest.main()
