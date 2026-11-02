"""Offline dual-backend dispatch, registry identity and seeded-library checks."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from experiments import campaign, render_profiles as profiles, unified_benchmark as runner, pe_loop
from experiments.creative_benchmark import task_spec, direct_request
from planner_harness.common import load, save, sha
from planner_harness.integrity import IntegrityError
from test_unified_results import Fixture
from run_experiment_campaign import load_hosts


class BackendTests(Fixture):
    def test_ditto_prepare_planner_direct_and_cached_identity(self):
        batch = self.prepare(methods=['direct','pe-loop','none','full'], training_maintenance=False, backend='ditto')
        topic = batch['topics'][0]
        self.assertEqual(batch['generation'], profiles.DITTO)
        self.assertEqual(topic['native_output'], {'frames':9,'fps':10.0,'width':32,'height':32})
        self.assertEqual(topic['conditioning_source_indices'], list(range(9)))
        for spec in (direct_request(self.repo,topic,batch)['payload']['renderer'],
                     task_spec(topic,'none',batch,'profile.json')['execution']['renderer']):
            self.assertEqual(spec['backend'],'ditto')
            self.assertEqual(spec['conditioning_source_indices'],list(range(9)))
        with self.assertRaises(IntegrityError):
            runner.check_entry(topic,'direct',batch,self.row(request_sha256=__import__('planner_harness.execution',fromlist=['signature']).signature({'text':topic['request']})))
        with self.assertRaises(ValueError):
            profiles.check_host(batch,{'renderer':{'backend':'bernini'}})
        profiles.check_host(batch,{'renderer':{'backend':'ditto','generation':profiles.DITTO}})

    def test_registered_ditto_result_and_roundtrip(self):
        batch=self.prepare(methods=['direct'],training_maintenance=False,backend='ditto')
        topic=batch['topics'][0]
        receipt=self.root/'receipt.json';save(receipt,{'fixture':True})
        from planner_harness.video import Video
        candidate={'video':Video(self.source,self.root/'video').info,'response':str(receipt),'seed':42}
        entry=runner._register(self.repo,batch,topic,'direct',42,candidate,self.root,[candidate])
        self.assertEqual(entry['generation']['backend'],'ditto')
        runner.check_entry(topic,'direct',batch,entry)
        other={**batch,'backend':'bernini','generation':profiles.BERNINI}
        with self.assertRaises(IntegrityError):runner.check_entry(topic,'direct',other,entry)

    def test_host_dimensions_and_model_specific_prompt(self):
        with self.assertRaises(ValueError):self.prepare(backend='ditto',output_dimensions={'width':845,'height':480})
        self.assertIn('Bernini',pe_loop.system_prompt('bernini'))
        text=pe_loop.system_prompt('ditto')
        self.assertIn('Ditto V2V',text)
        self.assertNotIn('Bernini accepts',text)
        self.assertNotEqual(pe_loop.configuration('bernini'),pe_loop.configuration('ditto'))

    def test_both_command_resolves_host_files_relative_to_config(self):
        folder=self.root/'host-configs';folder.mkdir()
        for name in ('bernini','ditto'):save(folder/(name+'.json'),{'renderer':{'backend':name}})
        path=folder/'hosts.json';save(path,{'hosts':{'bernini':'bernini.json','ditto':'ditto.json'}})
        self.assertEqual(set(load_hosts(path,'both')),{'bernini','ditto'})
        with self.assertRaises(ValueError):load_hosts(folder/'bernini.json','ditto')


class LibraryAndProcessTests(unittest.TestCase):
    def test_seed_contains_preexisting_entries_and_is_immutable(self):
        with tempfile.TemporaryDirectory() as d:
            target=campaign.seed_library(ROOT,Path(d))
            snapshot=load(target)
            self.assertEqual(snapshot['experience_mode'],'full')
            self.assertGreater(len(snapshot['curated_catalog']['entries']),0)
            self.assertEqual(campaign.seed_library(ROOT,Path(d)),target)
            bad=copy.deepcopy(snapshot);bad['curated_catalog']['entries']=[]
            p=Path(d)/'empty.json';save(p,bad)
            with self.assertRaises(ValueError):campaign.seed_library(ROOT,Path(d)/'empty',p)

    def test_two_models_share_seed_but_not_output_or_experience(self):
        with tempfile.TemporaryDirectory() as d:
            hosts={n:{'renderer':{'backend':n}} for n in ('bernini','ditto')}
            calls=[]
            def run(root,output,config,host,stage,**kw):
                calls.append((Path(output),sha(kw['initial_snapshot'])))
                return {'status':'fixture'}
            with patch.object(campaign,'execute',side_effect=run):
                result=campaign.execute_models(ROOT,d,{},hosts,'main',execute_paid=True)
            self.assertEqual(set(result),set(hosts))
            self.assertEqual([p.name for p,_ in calls],['bernini','ditto'])
            self.assertEqual(calls[0][1],calls[1][1])

    def test_process_dispatches_ditto_prepare_render_and_close(self):
        from server_runtime import renderers, ditto
        events=[]
        class Renderer:
            def __init__(self,*a):events.append('construct')
            def initialize(self):events.append('initialize')
            def load_pipeline(self):events.append('load')
            def prepare(self,*a):events.append('prepare')
            def __call__(self,*a):events.append('render');return {'video':'fixture'}
            def close(self):events.append('close')
        class Connection:
            def __init__(self):self.actions=iter([('prepare',{},'.'),('render',{},'.'),('close',None,None)]);self.messages=[]
            def recv(self):return next(self.actions)
            def send(self,v):self.messages.append(v)
            def close(self):pass
        conn=Connection()
        with tempfile.TemporaryDirectory() as d, patch('os.setsid'), patch.object(ditto,'PersistentDittoRenderer',Renderer):
            renderers._renderer_process(ROOT,{'backend':'ditto','asset_manifest_sha256':'fixture'},d,conn)
        self.assertEqual(events,['construct','initialize','load','prepare','render','close'])
        self.assertEqual(conn.messages[-1]['payload'],{'video':'fixture'})


if __name__=='__main__':unittest.main()
