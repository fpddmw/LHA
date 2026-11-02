"""Offline experience authority, discovery, curation and observation checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from planner_harness.common import load, save, sha
from planner_harness.creative_knowledge import CreativeKnowledge
from planner_harness import training_experience as tx, maintenance as m
from planner_harness.experience_contributions import curate, navigation_documents
from planner_harness.experience_usage import snapshot_index


class ContributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.seed_path = self.folder/'seed.json'
        CreativeKnowledge(ROOT).freeze(self.seed_path)
        self.seed = load(self.seed_path)
        self.entry = self.seed['curated_catalog']['entries'][0]
        self.source = {'sha256':'software-fixture-source', 'split':'train'}

    def tearDown(self):
        self.tmp.cleanup()

    def comment(self, op='clarify'):
        return {'op':op, 'id':self.entry['id'], 'summary':'Synthetic prism boundary for testing.',
                'text':'A synthetic prism condition changes this fixture recommendation; no empirical claim.'}

    def add(self):
        return tx.changeset(ROOT, self.seed, [self.comment()], self.source,
                            {'request':{'text':'Software test'}, 'events':[{'prompt':'Actual fixture prompt'}]})

    def decision(self, identity):
        return {'contribution_ids':[identity], 'disposition':'merge', 'reason':'Authorized software test.',
                'expected_entry_sha256':self.entry['sha256'],
                'entry':{'id':self.entry['id'], 'title':'Synthetic revised judgment',
                         'text':'Revised fixture account.', 'summary':'Prefer the synthetic prism construction.',
                         'questions':['Which prism?'], 'renderers':['bernini']}}

    def test_contribution_keeps_canonical_text_summary_and_manuals(self):
        result, ids = self.add()
        self.assertEqual(result['curated_catalog'], self.seed['curated_catalog'])
        for path, doc in self.seed['documents'].items():
            self.assertEqual(result['documents'][path], doc)
        self.assertEqual(len(ids), 1)
        self.assertEqual(result['experience_contributions']['items'][0]['target_version']['sha256'], self.entry['sha256'])

    def test_task_cannot_replace_or_target_manuals(self):
        for change in [self.comment('replace'), {k:v for k,v in self.comment().items() if k!='op'},
                       {**self.comment(), 'id':'manual'}, {**self.comment(), 'id':'planning-resources'}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                tx.changeset(ROOT, self.seed, [change], self.source)

    def test_first_page_search_and_source_case_are_linked(self):
        result, ids = self.add(); k = CreativeKnowledge(ROOT, result)
        first = k.read(self.entry['id'], max_chars=256)
        self.assertEqual(first['related_contributions'][0]['id'], ids[0])
        account = k.read(ids[0]); case = k.read(account['source_case']['id'])
        self.assertIn('Actual fixture prompt', case['text'])
        self.assertIn(ids[0], [r['id'] for r in k.search('synthetic prism')['matches']])
        self.assertIn(ids[0], snapshot_index(result)); self.assertIn(ids[0], k.usage_index()['items'])

    def test_freeze_and_none_isolation(self):
        result, ids = self.add(); k = CreativeKnowledge(ROOT, result)
        frozen = self.folder/'roundtrip.json'; k.freeze(frozen)
        again = CreativeKnowledge(ROOT, frozen)
        self.assertEqual(k.read(ids[0]), again.read(ids[0]))
        none = CreativeKnowledge(ROOT, experience_mode='none')
        with self.assertRaises(ValueError):none.read(ids[0])
        with self.assertRaises(ValueError):none.browse('contributions')
        nf = self.folder/'none.json'; none.freeze(nf); bad = load(nf)
        bad['experience_contributions'] = result['experience_contributions']
        with self.assertRaises(ValueError):CreativeKnowledge(ROOT, bad)

    def test_create_followed_by_comment_never_alters_first_contribution(self):
        created, _ = tx.changeset(ROOT, self.seed, [{'op':'create','id':'proposal-prism','title':'Prism',
            'text':'Use prism construction under the fixture condition.','summary':'Prefer prism.'}], self.source)
        old = CreativeKnowledge(ROOT, created).read('proposal-prism')['text']
        second, ids = tx.changeset(ROOT, created, [{'op':'comment','id':'proposal-prism','text':'Boundary correction.'}], {'sha256':'second'})
        k = CreativeKnowledge(ROOT, second)
        self.assertEqual(k.read('proposal-prism')['text'], old)
        self.assertEqual(k.read('proposal-prism')['related_contributions'][0]['id'], ids[0])
        self.assertEqual(second['experience_contributions']['items'][1]['case_id'], k.read(ids[0])['source_case']['id'])

    def test_duplicate_same_contribution_is_idempotent(self):
        first, ids = tx.changeset(ROOT, self.seed, [self.comment()], self.source)
        again, new = tx.changeset(ROOT, first, [self.comment()], self.source)
        self.assertFalse(new)
        self.assertEqual(first, again)

    def test_explicit_curation_updates_discovery_and_keeps_original_evidence(self):
        result, ids = self.add(); before = copy.deepcopy(result['experience_contributions']['items'])
        revised = curate(result, [self.decision(ids[0])], authorization='software-fixture-review')
        k = CreativeKnowledge(ROOT, revised)
        self.assertIn('Revised fixture', k.read(self.entry['id'])['text'])
        self.assertIn('Prefer the synthetic prism', k.read('experience-map', max_chars=8000)['text'])
        self.assertIn('Prefer the synthetic prism', k.read('EX-renderer-profiles', max_chars=8000)['text'])
        self.assertEqual(revised['experience_contributions']['items'], before)
        self.assertEqual(revised['experience_entry_history'][0]['document'], self.seed['documents'][self.entry['path']])
        self.assertEqual(k.read(ids[0])['curation']['disposition'], 'merge')
        self.assertEqual(k.read(self.entry['id'])['recommendation'], 'Prefer the synthetic prism construction.')
        target = self.folder/'curated.json'; k.freeze(target)
        self.assertEqual(load(target)['experience_entry_history'], revised['experience_entry_history'])

    def test_stale_entry_or_manual_curation_rejected(self):
        result, ids = self.add(); decision = self.decision(ids[0])
        with self.assertRaises(ValueError):curate(result, [decision], authorization='')
        with self.assertRaises(ValueError):curate(result, [{**decision, 'expected_entry_sha256':'stale'}], authorization='review')
        decision['entry']['id'] = 'manual'
        with self.assertRaises(ValueError):curate(result, [decision], authorization='review')

    def test_decline_and_supersede_are_visible_without_erasing_text(self):
        result, ids = tx.changeset(ROOT, self.seed, [self.comment(), {**self.comment('comment'),'text':'New competing explanation.'}], self.source)
        revised = curate(result, [{'contribution_ids':[ids[0]], 'disposition':'supersede',
                                  'successor_ids':[ids[1]], 'reason':'Prefer the sharper condition.'}], authorization='review')
        k = CreativeKnowledge(ROOT, revised)
        self.assertEqual(k.read(ids[0])['curation']['successor_ids'], [ids[1]])
        self.assertEqual(revised['curated_catalog']['entries'], self.seed['curated_catalog']['entries'])

    def test_curator_pointer_recovery_and_stale_parent(self):
        result, ids = self.add(); source = self.folder/'contributed.json'; save(source, result)
        initial = tx.initialize(ROOT, self.folder, source)
        decisions = [self.decision(ids[0])]
        receipt = tx.curate_library(ROOT, self.folder, decisions, authorization='review', expected_snapshot_sha256=initial['snapshot_sha256'])
        self.assertEqual(tx.current(ROOT, self.folder), receipt['after'])
        save(self.folder/'training-experience/current.json', initial)
        same = tx.curate_library(ROOT, self.folder, decisions, authorization='review', expected_snapshot_sha256=initial['snapshot_sha256'])
        self.assertEqual(same, receipt); self.assertEqual(tx.current(ROOT, self.folder), receipt['after'])
        with self.assertRaises(ValueError):
            tx.curate_library(ROOT, self.folder, decisions, authorization='different review', expected_snapshot_sha256=initial['snapshot_sha256'])

    def test_tampered_contribution_rejected(self):
        result, _ = self.add(); row = result['experience_contributions']['items'][0]
        result['documents'][row['path']]['text'] += ' altered'
        with self.assertRaises(ValueError):CreativeKnowledge(ROOT, result)

    def test_generated_navigation_matches_catalog(self):
        for path, text in navigation_documents(self.seed['curated_catalog']).items():
            self.assertEqual((ROOT/path).read_text(), text)

    def video(self):
        import cv2
        import numpy as np
        path = self.folder/'synthetic.mp4'
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 8, (64,64))
        for i in range(8):writer.write(np.full((64,64,3), i*20, dtype=np.uint8))
        writer.release()
        return path

    def test_new_interval_observation_is_bound_and_bounded(self):
        path = self.video(); videos = {'v1':{'path':str(path),'sha256':sha(path)}}
        result = m.observe_saved(videos, self.folder/'review', {'video_id':'v1','start':.5,'end':.875,'count':3}, 'fixture')
        self.assertEqual(result['evidence_phase'], 'post_task')
        self.assertGreaterEqual(result['frames'][0]['timestamp_seconds'], .5)
        with self.assertRaises(ValueError):m.observe_saved(videos, self.folder, {'video_id':'v1','count':9}, 'bad')
        videos['v1']['sha256'] = 'changed'
        with self.assertRaises(ValueError):m.observe_saved(videos, self.folder, {'video_id':'v1'}, 'bad')

    def test_opened_case_exposes_only_bound_videos(self):
        path = self.video()
        result, ids = tx.changeset(ROOT,self.seed,[self.comment()],self.source,
            {'videos':{'v2':{'path':str(path),'sha256':sha(path)}}})
        k = CreativeKnowledge(ROOT,result); case_id = k.read(ids[0])['case_id']
        opened = m.case_videos(k,case_id)
        self.assertEqual(list(opened),[case_id+':v2'])
        observed = m.observe_saved(opened,self.folder,{'video_id':case_id+':v2','count':2},'case-fixture')
        self.assertEqual(observed['video_sha256'],sha(path))
        self.assertEqual(m.case_videos(k,self.entry['id']),{})

    def test_post_task_model_can_observe_new_frames_and_contribute(self):
        from test_loop_protocol_upgrade import IntegrationTests
        run = IntegrationTests().run_record(self.folder)
        path = self.video(); state = load(run/'state.json')
        state['videos'] = {'v1':{'path':str(path), 'sha256':sha(path)}}; save(run/'state.json', state)
        library = tx.initialize(ROOT, self.folder)
        jid = m.enqueue(ROOT,self.folder,run,split='train',topic='fixture',method='none',batch_sha256='fixture',maintenance_snapshot=library)
        seen = []
        class Model:
            model = 'software-fixture'; reasoning_effort = 'high'
            def predict_text(inner, **kw):
                seen.append(kw)
                if len(seen)==1:return json.dumps({'action':'observe','arguments':{'video_id':'v1','start':.5,'end':.875,'count':2}})
                return json.dumps({'action':'contribute','arguments':{'text':'Software-only observation fixture.', 'changes':[
                    {'op':'create','id':'proposal-observation','title':'Fixture','summary':'A fixture judgment.','text':'A fixture observation.'}]}})
        status = tx.maintain(ROOT,self.folder,run,jid,{'model_calls':3,'attempts':1,'wall_seconds':30},model_factory=Model)
        self.assertEqual(status['status'],'activated',status)
        self.assertTrue(seen[1]['image_paths'])
        k=CreativeKnowledge(ROOT,tx.current(ROOT,self.folder)['snapshot'])
        case=k.read(k.read('proposal-observation')['case_id'],max_chars=8000)
        self.assertIn('post_task',case['text'])
        self.assertEqual(load(run/'knowledge-snapshot.json')['experience_mode'],'none')
        self.assertFalse(status['canonical_entries_changed'])


if __name__ == '__main__':unittest.main()
