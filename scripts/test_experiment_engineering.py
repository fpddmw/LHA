"""Offline entry/configuration, settlement and scheduling regressions."""
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from test_unified_results import Fixture
from experiments import campaign,creative_benchmark as public,device_scheduler as scheduler,unified_benchmark as u
from planner_harness.common import load,save,sha


class Engineering(Fixture):
    def test_selected_samples_freeze_only_the_requested_long_task(self):
        batch=self.prepare(sample_ids=['002'],prompt_forms=['long'],methods=['direct','full','pe-loop'],training_maintenance=False)
        self.assertEqual([t['id'] for t in batch['topics']],['002__long'])
        self.assertEqual(batch['requested_sample_ids'],['002'])
        inputs=load(self.output/'inputs/plan.json')
        self.assertEqual(inputs['sample_count'],1)
        self.assertEqual(inputs['inventory_count'],2)
        self.assertEqual(inputs['requested_sample_ids'],['002'])

    def test_sample_selector_rejects_unknown_or_out_of_split_ids_before_video_decode(self):
        for ids in (['missing'],['001'],['002','002'],[]):
            with self.subTest(ids=ids),patch('run_bernini_benchmark.inspect_video') as inspect:
                with self.assertRaises(ValueError):
                    self.prepare(sample_ids=ids,splits=['test'],prompt_forms=['long'],methods=['direct'])
                inspect.assert_not_called()

    def test_public_prepare_uses_current_unified_defaults_without_a_40_train_branch(self):
        with patch('experiments.unified_benchmark.prepare',return_value={'prepared':True}) as prepare:
            self.assertEqual(public.prepare(self.repo,self.output),{'prepared':True})
        self.assertEqual(prepare.call_args.kwargs,{'splits':['test'],'prompt_forms':['short','long']})

    def test_campaign_and_host_example_resolve_the_same_api_configuration(self):
        config=campaign.configuration(ROOT/'configs/experiment-campaign.json')
        host=load(ROOT/'configs/creative-fewshot-host.example.json')
        expected={'model':config['model'],'reasoning_effort':config['reasoning_effort']}
        planner,critic,roles=u.model_configuration(expected,host['models'])
        self.assertEqual(planner,expected);self.assertEqual(critic,expected)
        self.assertEqual(roles['planner']['factory'],'vlm.openrouter:OpenRouterVisionModel')
        self.assertEqual(config['model'],'openai/gpt-6.1-sol')

    def test_maintenance_factory_uses_the_frozen_planner_api_options(self):
        calls=[]
        def client(**kwargs):calls.append(kwargs);return object()
        batch={'models':{'planner':{'factory':'fixture_api:Client','options':{'model':'fixture/model','reasoning_effort':'medium','credential_file':'external.env'}}}}
        with patch.dict(sys.modules,{'fixture_api':SimpleNamespace(Client=client)}):u.maintenance_model(batch)
        self.assertEqual(calls,[{'role':'post_task_planner','model':'fixture/model','reasoning_effort':'medium','credential_file':'external.env'}])

    def test_freeze_keeps_known_failed_training_and_maintenance_coverage(self):
        topic={'id':'train-task','split':'train'}
        from planner_harness.training_experience import initialize
        revision=initialize(self.repo,self.output/'zero')
        save(self.output/'zero/batch.json',{'sha256':'batch','topics':[topic],
            'review':{'mode':'critic'},'arms':['none'],'backend':'bernini','training_maintenance':True,'experience_owner':revision['owner']})
        save(self.output/'zero/methods/train-task/none/settlement.json',{'status':'failed'})
        save(self.output/'zero/maintenance/training-errors/train-task.json',{'status':'failed','error_type':'FixtureKnownFailure','current_version_retained':True})
        target=campaign.freeze_training(self.repo,self.output)
        self.assertEqual(load(target),load(revision['snapshot']))
        receipt=load(self.output/'trained-experience-receipt.json')
        self.assertEqual(receipt['online_mode'],'none')
        self.assertEqual(receipt['conditions'],1)
        self.assertEqual(receipt['full_run_conditions'],1)
        self.assertEqual(receipt['coverage'][0]['online_status'],'failed')
        self.assertEqual(receipt['coverage'][0]['maintenance']['status'],'failed')

    def test_unknown_training_maintenance_is_not_frozen_or_marked_complete(self):
        save(self.output/'zero/batch.json',{'sha256':'batch','topics':[{'id':'one','split':'train'}],
            'review':{'mode':'critic'},'arms':['none'],'training_maintenance':True})
        save(self.output/'zero/methods/one/none/settlement.json',{'status':'ready'})
        save(self.output/'zero/maintenance/training-errors/one.json',{'status':'execution_unknown'})
        self.assertFalse(scheduler.training_maintenance_settled(self.output/'zero',{'id':'one'}))
        with self.assertRaisesRegex(ValueError,'maintenance needs recovery'):campaign.freeze_training(self.repo,self.output)
        self.assertFalse((self.output/'trained-experience.json').exists())

    def test_dead_claim_with_unknown_receipt_retains_original_recovery_requirement(self):
        topic={'id':'one','methods':['direct']}
        queue=scheduler.Claims(self.output/'queue.db',[topic],'batch','foreign-host:1:old')
        queue.next()
        save(self.output/'batch.json',{'sha256':'batch','arms':['direct']})
        save(self.output/'methods/one/direct/settlement.json',{'batch_sha256':'batch','status':'execution_unknown'})
        queue.recover(self.output)
        self.assertEqual(queue.rows()[0]['status'],'recovery_required')
        self.assertIsNone(queue.next())

    def test_explicit_device_selection_is_checked_against_physical_inventory(self):
        inventory=lambda:'0, GPU-a\n1, GPU-b\n'
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(scheduler.devices({'devices':['GPU-b',0]},query=inventory),['1','0'])
            with self.assertRaisesRegex(ValueError,'absent'):scheduler.devices({'devices':[7]},query=inventory)

    def test_ready_videos_do_not_hide_unresolved_training_or_device_claims(self):
        self.assertEqual(scheduler.dispatch_status([{'status':'ready'}],[{'status':'recovery_required'}]),'partial')
        self.assertEqual(scheduler.dispatch_status([{'status':'failed'}],[{'status':'settled_from_receipts'}]),'settled')

    def test_direct_reuse_shares_content_addressed_bytes_on_the_same_filesystem(self):
        from experiments import results
        source=self.root/'previous'
        old=results.import_video(self.repo,source,self.row())
        batch=self.prepare(methods=['direct'],best_of_n=None,splits=['train'],prompt_forms=['short'])
        campaign.reuse_direct(self.repo,self.output,batch,{'renderer':{}},str(source))
        new=results.find(self.registry,'001','short','direct',42)
        self.assertEqual((source/old['video']).stat().st_ino,(self.registry/new['video']).stat().st_ino)

    def test_modern_direct_recovery_binds_completed_receipt_to_failed_settlement(self):
        from experiments.recovery import recover_direct
        from server_runtime.queue import Queue
        from planner_harness.execution import signature
        from planner_harness.video import Video
        batch=self.prepare(methods=['direct'],best_of_n=None,splits=['train'],prompt_forms=['short'])
        batch=load(self.output/'batch.json');topic=batch['topics'][0]
        worker=self.output/'workers/0';folder=worker/'baselines'/topic['id']/'direct/0'
        body={'id':topic['id']+'__direct__0','kind':'generate','mode':'live','payload':{}}
        request={**body,'sha256':signature(body)};save(folder/'request.json',request)
        queue=Queue(worker/'queue.sqlite3',{'gpu':1,'llm':1,'cpu':1})
        queue.enqueue(body['id'],'tool','gpu',{'request':str(folder/'request.json'),'request_sha256':request['sha256']})
        job=queue.claim('gpu','fixture');queue.finish(job,state='needs_review',error='Original uncertain result')
        settlement=self.output/'methods'/topic['id']/'direct/settlement.json'
        save(settlement,{'batch_sha256':batch['sha256'],'status':'failed'})
        prior=sha(settlement)
        receipt=self.root/'completed.json'
        save(receipt,{'request_sha256':request['sha256'],'mode':'live','status':'complete',
            'payload':{'video':Video(self.source,self.root/'info').info}})
        recover_direct(self.output,0,topic['id'],'Collect the original completed result',receipt=receipt)
        recovery=load(settlement.parent/'recovery.json')
        self.assertEqual(recovery['previous_settlement_sha256'],prior)
        self.assertEqual(recovery['model_calls'],0);self.assertEqual(recovery['gpu_jobs'],0)
        self.assertEqual(load(folder/'request.json'),request)


if __name__=='__main__':unittest.main()
