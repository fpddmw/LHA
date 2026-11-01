"""Offline versioned migration preserves an active/completed prefix without rerendering."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import test_creative_delivery_review as fixtures
import test_creative_loop as common
from planner_harness.common import load,save,sha
from planner_harness.protocol_migration import plan,apply,prepare_batch
from planner_harness.execution import signature
from planner_harness.delivery import verify_delivery
from planner_harness import PlannerHarness


class MigrationTests(unittest.TestCase):
    setUp,tearDown=fixtures.DeliveryReviewTests.setUp,fixtures.DeliveryReviewTests.tearDown
    start=fixtures.DeliveryReviewTests.start
    respond=fixtures.DeliveryReviewTests.respond
    resume=fixtures.DeliveryReviewTests.resume
    finish=fixtures.DeliveryReviewTests.finish
    review=fixtures.DeliveryReviewTests.review

    def legacy(self):
        state=load(self.h.output/'state.json')
        state['config'].pop('continuation_policy',None);state['config'].pop('delivery_review_protocol',None)
        state['final'].pop('delivery_review',None) if 'final' in state else None
        state.pop('delivery_reviews',None);state.pop('active_delivery_proposal',None)
        save(self.h.output/'state.json',state)
        if 'final' in state:save(self.h.output/'final.json',state['final'])
        return state

    def test_completed_loop_reopens_proposal_reuses_report_and_retains_old_final(self):
        self.start();self.finish();self.review();self.finish();old=self.legacy()
        run=self.h.output;knowledge=sha(run/'knowledge-snapshot.json');old_state=sha(run/'state.json')
        with self.assertRaisesRegex(ValueError,'explicit creative protocol migration'):
            self.h.resume()
        proposed=plan(run,ROOT,'Offline fixture: approved replacement protocol')
        self.assertEqual(sha(run/'state.json'),old_state)
        with self.assertRaises(ValueError):apply(run,ROOT,proposed,'')
        receipt=apply(run,ROOT,proposed,'Offline fixture authorization only')
        migrated=load(run/'state.json')
        self.assertNotIn('final',migrated);self.assertEqual(migrated['status'],'running')
        self.assertEqual(migrated['generation_requests'],old['generation_requests'])
        self.assertEqual(migrated['videos'],old['videos']);self.assertEqual(sha(run/'knowledge-snapshot.json'),knowledge)
        self.assertEqual(load(Path(receipt['before_snapshot'])/'final.json'),old['final'])
        self.assertEqual(load(Path(receipt['before_snapshot'])/'state.json'),old)
        with self.assertRaises(ValueError):verify_delivery(run)
        self.h=PlannerHarness(run,common.Scripted([common.action('finish',video='v1',message='Confirm this proposal after its complete retained report.')]))
        self.h.resume();self.assertEqual(verify_delivery(run)['selected'],'v1')
        self.assertEqual(self.h.state['final']['delivery_review']['review_origin'],'reused')
        self.assertEqual(self.h.state['generation_requests'],old['generation_requests'])

    def test_active_settled_render_keeps_signed_request_and_collects_without_rerender(self):
        self.start();old=self.legacy();run=self.h.output
        pending=old['pending_tool'];request_hash=sha(run/'jobs'/pending/'request.json')
        response_hash=sha(run/'jobs'/pending/'response.json')
        proposed=plan(run,ROOT,'Offline settled-render transition')
        apply(run,ROOT,proposed,'Offline fixture authorization only')
        self.assertEqual(sha(run/'jobs'/pending/'request.json'),request_hash)
        self.assertEqual(sha(run/'jobs'/pending/'response.json'),response_hash)
        self.h=PlannerHarness(run,common.Scripted([common.action('finish',video='v1',message='Propose the preserved render.')]))
        self.h.resume();self.assertEqual(self.h.state['generation_requests'],1)
        self.assertEqual(self.h.state['videos']['v1']['job_id'],pending)
        self.review();self.finish();verify_delivery(run)

    def test_unsettled_call_or_changed_prefix_cannot_apply(self):
        self.start();run=self.h.output;old=self.legacy()
        proposed=plan(run,ROOT,'Offline prefix check')
        path=run/'jobs'/old['pending_tool']/'response.json';path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'prefix changed'):apply(run,ROOT,proposed,'Offline fixture authorization only')
        state=load(run/'state.json');state['pending_event']='unsettled';save(run/'state.json',state)
        pending_plan=plan(run,ROOT,'Offline pending call')
        self.assertTrue(pending_plan['blocked_requirements'])
        with self.assertRaises(ValueError):apply(run,ROOT,pending_plan,'Offline fixture authorization only')

    def test_extra_local_scope_is_only_a_blocked_preview_not_a_silent_expansion(self):
        from planner_harness.creative import experiment_profile
        target=experiment_profile(ROOT);previous=copy.deepcopy(target)
        removed=next(iter(previous['knowledge_scopes']['full']))
        previous['knowledge_scopes']['full'].pop(removed)
        previous['sha256']=signature({k:v for k,v in previous.items() if k!='sha256'})
        batch={'profile_sha256':previous['sha256']};batch['sha256']=signature(batch)
        save(self.root/'baseline-profile.json',previous);save(self.root/'baseline-batch.json',batch)
        result=prepare_batch(ROOT,self.root/'baseline-batch.json',self.root/'baseline-profile.json',self.root/'preview')
        self.assertEqual(result['status'],'prepared_requires_environment_reconciliation')
        self.assertTrue(result['local_preview_only']);self.assertIn(removed,result['scope_presence_differences']['full'])
        self.assertFalse(result['modifies_live_state'])


if __name__=='__main__':unittest.main()
