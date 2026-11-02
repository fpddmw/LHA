"""Seed, family isolation and self-review campaign regressions; no paid calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from planner_harness import training_experience as tx, maintenance as m
from planner_harness.common import load, save, sha
from planner_harness.creative_knowledge import CreativeKnowledge
from experiments import campaign, unified_benchmark as u
import test_loop_protocol_upgrade as protocol_tests
from test_unified_results import Fixture


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seed = self.root / 'seed.json'
        CreativeKnowledge(ROOT, experience_mode='full').freeze(self.seed)

    def run_record(self, mode='planner', renderer='bernini'):
        run = protocol_tests.IntegrationTests.run_record(self, self.root)
        state = load(run / 'state.json')
        state['config']['execution'].update(review={'mode':mode},renderer={'backend':renderer})
        save(run/'state.json',state)
        return run

    def test_same_nonempty_seed_independent_ownership_and_resume(self):
        libraries = [tx.initialize(ROOT,self.root/name,self.seed,review_mode=mode,renderer_backend=backend)
                     for name,mode,backend in [('critic','critic','bernini'),('self','planner','bernini'),('ditto','planner','ditto')]]
        self.assertEqual(len({r['snapshot_sha256'] for r in libraries}),1)
        self.assertEqual(len({r['owner']['id'] for r in libraries}),3)
        self.assertTrue(tx.validate_snapshot(ROOT,load(libraries[0]['snapshot'])).curated_catalog['entries'])
        self.assertEqual(tx.initialize(ROOT,self.root/'self',self.seed,review_mode='planner'),libraries[1])
        with self.assertRaisesRegex(ValueError,'review family'):
            tx.initialize(ROOT,self.root/'self',self.seed,review_mode='critic')
        with self.assertRaisesRegex(ValueError,'renderer'):
            tx.initialize(ROOT,self.root/'self',self.seed,review_mode='planner',renderer_backend='ditto')

    def test_empty_seed_rejected_by_lower_level_initialization(self):
        value=load(self.seed);value['curated_catalog']['entries']=[]
        save(self.seed,value)
        with self.assertRaisesRegex(ValueError,'nonempty'):
            tx.initialize(ROOT,self.root/'empty',self.seed)
        self.assertFalse((self.root/'empty/training-experience/current.json').exists())

    def test_foreign_increment_cannot_be_relabelled_as_owned_frozen_copy(self):
        own=tx.initialize(ROOT,self.root/'self',self.seed,review_mode='planner')
        value,_=tx.changeset(ROOT,load(self.seed),[{'op':'create','id':'foreign-entry',
            'title':'Foreign fixture','summary':'Foreign condition.','text':'Foreign increment.'}],{'sha256':'fixture'})
        foreign=self.root/'foreign.json';save(foreign,value)
        with self.assertRaises((ValueError,FileNotFoundError)):
            tx.owned_copy(ROOT,foreign,own['owner'])

    def test_none_enqueue_binds_seed_and_never_falls_back_to_online_snapshot(self):
        run=self.run_record(); online=sha(run/'knowledge-snapshot.json')
        identity=m.enqueue(ROOT,self.root/'self',run,split='train',topic='fixture',method='none',batch_sha256='fixture')
        job=load(self.root/'self/maintenance/jobs'/identity/'job.json')
        self.assertEqual(job['maintenance_snapshot']['owner']['review_mode'],'planner')
        self.assertTrue(tx.bound_snapshot(ROOT,job['maintenance_snapshot']).curated_catalog['entries'])
        self.assertEqual(sha(run/'knowledge-snapshot.json'),online)
        self.assertEqual(load(run/'knowledge-snapshot.json')['curated_catalog']['entries'],[])
        broken=copy.deepcopy(job);broken['maintenance_snapshot']=None
        with self.assertRaisesRegex(ValueError,'bound full library'):
            m._execute(ROOT,self.root/'never-called',broken,m.configuration(),None)
        self.assertEqual(m.enqueue(ROOT,self.root/'self',run,split='train',topic='fixture',method='none',batch_sha256='fixture'),identity)

    def test_cross_family_enqueue_rejected_even_when_seed_hash_matches(self):
        run=self.run_record()
        critic=tx.initialize(ROOT,self.root/'critic',self.seed)
        own=tx.initialize(ROOT,self.root/'self',self.seed,review_mode='planner')
        self.assertEqual(critic['snapshot_sha256'],own['snapshot_sha256'])
        for destination in (self.root/'critic', self.root/'self'):
            with self.assertRaisesRegex(ValueError,'another (review family|batch)'):
                m.enqueue(ROOT,destination,run,split='train',topic='fixture',method='none',batch_sha256='fixture',maintenance_snapshot=critic)

    def test_readonly_batch_cannot_enqueue_maintenance_even_on_a_training_task(self):
        run=self.run_record();output=self.root/'readonly'
        save(output/'batch.json',{'training_maintenance':False})
        self.assertIsNone(m.enqueue(ROOT,output,run,split='train',topic='fixture',method='full',batch_sha256='fixture'))
        self.assertFalse((output/'training-experience').exists())

    def test_self_review_contribution_updates_only_own_library_and_rejects_cross_activation(self):
        run=self.run_record(); own=self.root/'self'; other=self.root/'critic'
        before=tx.initialize(ROOT,other,self.seed)
        tx.initialize(ROOT,own,self.seed,review_mode='planner')
        identity=m.enqueue(ROOT,own,run,split='train',topic='fixture',method='none',batch_sha256='fixture')
        class Contributor:
            model='offline-fixture';reasoning_effort='high'
            def predict_text(self,**kwargs):
                return json.dumps({'action':'contribute','arguments':{'text':'Fixture conditional finding.',
                    'changes':[{'op':'create','id':'self-only','title':'Self-review fixture',
                                'summary':'When this fixture applies, inspect the transition.',
                                'text':'A simulated post-task finding for isolation verification.'}]}})
        result=tx.maintain(ROOT,own,run,identity,{'model_calls':2,'attempts':1,'wall_seconds':30},model_factory=Contributor)
        self.assertEqual(result['status'],'activated',result)
        after=tx.current(ROOT,own)
        self.assertIn('self-only',CreativeKnowledge(ROOT,after['snapshot']).items)
        self.assertEqual(load(after['snapshot'])['training_revision']['owner'],after['owner'])
        tx.owned_copy(ROOT,after['snapshot'],after['owner'])
        self.assertEqual(tx.current(ROOT,other),before)
        self.assertNotIn('self-only',CreativeKnowledge(ROOT,before['snapshot']).items)
        contribution=own/'maintenance/jobs'/identity/'training-attempt-1/contribution.json'
        with self.assertRaisesRegex(ValueError,'another batch'):
            tx.activate(ROOT,other,contribution)
        self.assertEqual(tx.maintain(ROOT,own,run,identity),result)
        self.assertEqual(tx.activate(ROOT,own,contribution),result)


class CampaignFamilyTests(Fixture):
    def test_self_review_alias_runs_own_accumulation_then_own_frozen_library(self):
        from contextlib import ExitStack
        seed=self.root/'seed.json';CreativeKnowledge(ROOT,experience_mode='full').freeze(seed)
        config=campaign.configuration(ROOT/'configs/experiment-campaign.json')
        calls=[];batches={};prepared={}
        config['reuse_direct_results']=None
        def prepare(root,output,**kw):
            prepared[output.name]=kw
            batch={'topics':[{'id':'fixture'}],'arms':kw['methods'],'review':kw['review'],
                'profile_sha256':'fixture','max_generations':kw['max_generations'],
                'training_maintenance':kw['training_maintenance'],'results_root':str(kw['results_root']),
                'seed_sequence':{'start':kw['seed_start'],'step':kw['seed_step']},
                'requested_splits':kw['splits'],'requested_prompt_forms':kw['prompt_forms'],
                'experience_seed_sha256':sha(kw['experience_snapshot']),'experience_owner':kw['experience_owner']}
            batches[str(output)]=batch;save(output/'batch.json',batch)
        def freeze(root,output,*,review_mode='critic'):
            self.assertEqual(review_mode,'planner')
            path=output/'self-review-trained-experience.json'
            save(path,{'offline':'self-review increment'})
            save(path.with_name(path.stem+'-receipt.json'),{'revision':{'owner':{'offline':'planner'}}})
            return path
        def run(root,output,host):
            calls.append(output.name);return {'status':'settled','positions':[]}
        with ExitStack() as stack:
            stack.enter_context(patch.object(campaign,'plan',return_value={'population':{}}))
            stack.enter_context(patch.object(campaign,'seed_library',return_value=seed))
            stack.enter_context(patch.object(campaign,'freeze_training',side_effect=freeze))
            stack.enter_context(patch.object(tx,'validate_snapshot'))
            for name,fn in [('prepare',prepare),('verify',lambda r,o:batches[str(o)]),
                            ('preflight',lambda *a:None),('policy',lambda *a:{}),('run',run)]:
                stack.enter_context(patch.object(u,name,side_effect=fn))
            stack.enter_context(patch('planner_harness.accounting.install'))
            campaign.execute(self.repo,self.output,config,{'renderer':{'backend':'bernini'}},'self-review',execute_paid=True)
        self.assertEqual(calls,['self-review-zero','self-review-knowledge'])
        zero,full=prepared['self-review-zero'],prepared['self-review-knowledge']
        self.assertEqual(zero['experience_snapshot'],seed)
        self.assertTrue(zero['training_maintenance'])
        self.assertEqual(full['experience_snapshot'],self.output/'self-review-trained-experience.json')
        self.assertFalse(full['training_maintenance'])
        self.assertTrue(all(p['review']=={'mode':'planner'} for p in prepared.values()))
        self.assertFalse((self.output/'zero').exists())

    def test_readonly_batch_rejects_empty_experience_snapshot(self):
        path=self.root/'empty.json';CreativeKnowledge(ROOT,experience_mode='full').freeze(path)
        value=load(path);value['curated_catalog']['entries']=[];save(path,value)
        with self.assertRaisesRegex(ValueError,'nonempty'):
            self.prepare(methods=['full'],training_maintenance=False,experience_snapshot=path)

    def test_self_review_none_accumulates_training_only_and_full_is_readonly(self):
        from experiments.device_scheduler import work_units
        batch=self.prepare(methods=['none'],review={'mode':'planner'},training_maintenance=True)
        self.assertEqual(batch['experience_owner']['review_mode'],'planner')
        units=work_units(batch,{})
        train=[r for r in units if r['split']=='train']
        self.assertEqual(len(train),2)
        self.assertEqual(train[1]['dependency'],train[0]['claim_id'])
        self.assertTrue(all(r['dependency']==train[-1]['claim_id'] for r in units if r['split']=='test'))
        self.assertTrue(all(u.training_topic(t,batch)==(t['split']=='train') for t in batch['topics']))
        own=tx.current(self.repo,self.output)
        self.output=self.root/'self-review-full'
        readonly=self.prepare(methods=['full'],review={'mode':'planner'},training_maintenance=False,
                              experience_snapshot=own['snapshot'],experience_owner=own['owner'])
        self.assertTrue(all(not u.training_topic(t,readonly) for t in readonly['topics']))
        self.assertEqual(readonly['experience_seed_sha256'],own['snapshot_sha256'])
        self.assertEqual(readonly['experience_owner'],own['owner'])
        self.assertFalse((self.output/'training-experience').exists())

    def test_readonly_self_review_cannot_import_critic_owner(self):
        critic=tx.initialize(self.repo,self.root/'critic')
        with self.assertRaisesRegex(ValueError,'review family'):
            self.prepare(methods=['full'],training_maintenance=False,review={'mode':'planner'},
                         experience_snapshot=critic['snapshot'],experience_owner=critic['owner'])

    def test_accumulated_snapshot_without_explicit_owner_still_cannot_cross_family(self):
        critic=tx.initialize(self.repo,self.root/'critic')
        value=load(critic['snapshot'])
        value['training_revision']={'owner':critic['owner'],'change_scope':'fixture'}
        path=self.root/'critic-increment.json';save(path,value)
        with self.assertRaisesRegex(ValueError,'review family'):
            self.prepare(methods=['full'],training_maintenance=False,review={'mode':'planner'},experience_snapshot=path)

    def test_real_family_freeze_uses_self_review_batch(self):
        parent=self.output
        self.output=parent/'self-review-zero'
        batch=self.prepare(methods=['none'],review={'mode':'planner'},training_maintenance=True)
        for t in batch['topics']:
            save(self.output/'methods'/t['id']/'none/settlement.json',{'status':'ready'})
            if t['split']=='train':
                save(self.output/'maintenance/training-errors'/(t['id']+'.json'),{'status':'not_eligible','reason':'Offline fixture'})
        frozen=campaign.freeze_training(self.repo,parent,review_mode='planner')
        self.assertEqual(frozen,parent/'self-review-trained-experience.json')
        self.assertEqual(sha(frozen),batch['experience_seed_sha256'])
        receipt=load(parent/'self-review-trained-experience-receipt.json')
        self.assertEqual(receipt['revision']['owner']['review_mode'],'planner')
        self.assertEqual(receipt['conditions'],2)
        self.assertFalse((parent/'trained-experience.json').exists())


if __name__=='__main__':unittest.main()
