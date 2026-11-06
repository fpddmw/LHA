"""Resume stale maintenance eligibility through the existing public command."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from experiments import unified_benchmark as benchmark
from planner_harness import maintenance, training_experience as experience
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from planner_harness.delivery import verify_delivery
from server_runtime.engine import Engine
from test_unified_results import Fixture
from test_loop_engineering import Engineering
from test_review_modes import action
import run_creative_benchmark as cli


class MaintenanceEligibilityRecovery(unittest.TestCase):
    setUp = Fixture.setUp
    prepare = Fixture.prepare

    def setup_batch(self):
        self.batch = self.prepare(splits=['train'], prompt_forms=['short'],
                                  methods=['pre-experience'], max_generations=1)
        self.topic = self.batch['topics'][0]
        self.profile = maintenance.stage_profile(ROOT,self.output,{'model_calls':1,'attempts':1})
        self.marker = self.output/'maintenance/training-errors'/(self.topic['id']+'.json')
        self.old = {'status':'not_eligible','reason':'Online task produced no settled Planner trace',
                    'current_version_retained':True,'online_result_changed':False}
        save(self.marker,self.old)
        self.marker_hash = sha(self.marker)
        self.sent = []

    def deliver(self):
        service,queue,renderer,planner = Engineering.service(self,[
            action('generate',input_video='source',prompt='Give the scene a blue treatment.'),
            action('finish',video='v1',message='Select the reviewed blue candidate.')])
        task = Engineering.task(self,n=1,execution={
            'experience_mode':'full','experience_condition':'pre-experience',
            'experience_snapshot':self.batch['experience_snapshot'],
            'experience_snapshot_sha256':self.batch['experience_seed_sha256'],
            'benchmark_metadata':{'sample_id':self.topic['sample_id'],'split':'train'}})
        task.update(source=str(self.repo/self.topic['source']),source_sha256=self.topic['source_sha256'],
                    request=self.topic['request'])
        service.submit(task)
        Engine(queue,service.directory,service,service.expand,interval=.001).run(once=True)
        self.run = service.directory/'tasks/topic/run'
        self.assertEqual(verify_delivery(self.run)['selected'],'v1')
        self.assertEqual(len(renderer.calls),1)
        state = load(self.run/'state.json')
        arm = {'arm':'pre-experience','outcome':'delivered','selected':'v1','first':'v1',
               'record_directory':str(self.run),'videos':{'v1':state['videos']['v1']},
               'delivery_review':state['final'].get('delivery_review'),
               'binding':{'topic':self.topic['id'],'source':self.topic['source_sha256'],
                          'request':signature({'text':self.topic['request']}),'profile':self.batch['profile_sha256']},
               'completion_record':{'path':str(self.run/'state.json'),'sha256':sha(self.run/'state.json')}}
        self.arm_path = self.output/'topics'/self.topic['id']/'pre-experience.json'
        save(self.arm_path,{**arm,'sha256':signature(arm)})
        self.online = {p:sha(p) for p in self.run.rglob('*') if p.is_file()}
        self.online[self.source] = sha(self.source)

    def contributor(self):
        target = load(self.batch['experience_snapshot'])['curated_catalog']['entries'][0]['id']
        sent = self.sent
        class Model:
            model = 'offline-fixture'
            reasoning_effort = 'high'
            def predict_text(self,**kwargs):
                sent.append(kwargs)
                return json.dumps({'contribute':{'text':'The blue treatment retained the source composition.',
                    'changes':[{'op':'comment','id':target,'text':'Inspect color placement against the retained composition.'}]}})
        return Model()

    def recover(self):
        stdout = io.StringIO()
        with patch.object(cli,'ROOT',self.repo), \
             patch('planner_harness.creative.verify_experiment',return_value={'sha256':'fixture'}), \
             patch('experiments.unified_benchmark.maintenance_model',side_effect=lambda _:self.contributor()), \
             patch.object(sys,'argv',['run_creative_benchmark.py','recover-maintenance',
                        '--output',str(self.output),'--topic',self.topic['id']]), \
             contextlib.redirect_stdout(stdout):
            cli.main()
        return json.loads(stdout.getvalue())

    def test_original_command_activates_after_delivery_and_preserves_online_files(self):
        self.setup_batch()
        self.assertEqual(self.recover()['status'],'not_eligible')
        self.assertEqual(sha(self.marker),self.marker_hash)
        self.assertEqual(self.sent,[])
        self.deliver()
        result = self.recover()
        self.assertEqual(result['status'],'activated',result)
        self.assertEqual(len(self.sent),1)
        self.assertFalse(self.marker.exists())
        history = list((self.marker.parent/'recovery-history'/self.topic['id']).glob('*.json'))
        self.assertEqual(len(history),1)
        self.assertEqual(sha(history[0]),self.marker_hash)
        self.assertTrue(all(sha(p)==digest for p,digest in self.online.items()))
        pointer = experience.current(self.repo,self.output)
        self.assertEqual(pointer['version'],1)
        self.assertEqual(self.recover()['status'],'activated')
        self.assertEqual(len(self.sent),1)
        self.assertEqual(experience.current(self.repo,self.output),pointer)
        self.assertTrue(all(sha(p)==digest for p,digest in self.online.items()))

    def test_changed_original_binding_keeps_marker_and_calls_no_model(self):
        self.setup_batch();self.deliver()
        arm = load(self.arm_path)
        arm['binding']['profile'] = 'another-batch-profile'
        arm['sha256'] = signature({k:v for k,v in arm.items() if k!='sha256'})
        save(self.arm_path,arm)
        with self.assertRaisesRegex(ValueError,'frozen topic'):
            self.recover()
        self.assertEqual(sha(self.marker),self.marker_hash)
        self.assertEqual(self.sent,[])
        self.assertFalse((self.output/'maintenance/jobs').exists())

    def test_unsettled_state_or_failed_arm_does_not_start_maintenance(self):
        self.setup_batch();self.deliver()
        state = load(self.run/'state.json');state['status']='interrupted'
        save(self.run/'state.json',state)
        arm = load(self.arm_path)
        arm['completion_record']['sha256'] = sha(self.run/'state.json')
        arm['sha256'] = signature({k:v for k,v in arm.items() if k!='sha256'})
        save(self.arm_path,arm)
        with self.assertRaisesRegex(ValueError,'actual settled delivery'):
            self.recover()
        self.assertEqual(sha(self.marker),self.marker_hash)
        arm['outcome']='model_unavailable'
        save(self.arm_path,arm)
        self.assertEqual(self.recover()['status'],'not_eligible')
        self.assertEqual(self.sent,[])
        self.assertFalse((self.output/'maintenance/jobs').exists())


if __name__=='__main__':unittest.main()
