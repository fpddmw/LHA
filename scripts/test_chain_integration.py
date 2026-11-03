"""Offline cross-entry contracts: clients, completion, navigation and progress."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from planner_harness.common import load, save, sha
from experiments import campaign, unified_benchmark
from server_runtime.service import Service
import run_planner_harness as single
import run_experiment_campaign as campaign_cli
import run_creative_benchmark as batch_cli


class FixtureClient:
    instances = []

    def __init__(self, **options):
        self.options = options
        self.model = options['model']
        self.reasoning_effort = options['reasoning_effort']
        self.instances.append(self)

    def predict_text(self, **_):
        raise AssertionError('No model calls in launch resolution tests')

    predict_json = predict_text


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.calls = []
        FixtureClient.instances = []
        fixture = types.ModuleType('lha_fixture_client')
        fixture.Client = FixtureClient
        self.module = patch.dict(sys.modules, {'lha_fixture_client': fixture})
        self.module.start()
        self.environment = patch.dict(os.environ, {'LHA_API_ENV_FILE': str(self.folder / 'absent')}, clear=True)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.module.stop()
        self.tmp.cleanup()

    def profile(self):
        value = load(ROOT / 'configs/creative-loop-v1.json')
        value['models']['planner'] = {'factory': 'lha_fixture_client:Client', 'options': {
            'model': 'fixture/planner', 'reasoning_effort': None, 'endpoint': 'fixture://private-route'}}
        path = self.folder / 'profile.json'
        save(path, value)
        return path

    def invoke(self, args):
        calls = self.calls

        class Harness:
            def __init__(self, output, model):
                calls.append({'output': str(output), 'client': model})

            def start(self, *_, **kw):
                calls.append({'start': kw})
                return {'status': 'complete'}

            def resume(self, **kw):
                calls.append({'resume': kw})
                return {'status': 'complete'}

        with patch('planner_harness.PlannerHarness', Harness), patch.object(sys, 'argv', [single.__file__, *args]), contextlib.redirect_stdout(io.StringIO()):
            return single.main()

    def new_args(self):
        return ['--source', 'unused.mp4', '--request', 'Recast the scene.', '--output', str(self.folder / 'run')]

    def test_profile_and_service_use_the_same_factory_options_and_cli_overrides(self):
        path = self.profile()
        self.invoke([*self.new_args(), '--profile', str(path), '--model', 'fixture/override', '--reasoning', 'medium'])
        started = self.calls[-1]['start']
        single_client = self.calls[0]['client']
        self.assertEqual(started['workflow'], 'creative_loop_v1')
        self.assertEqual(started['mode'], 'loop')
        service = object.__new__(Service)
        service.config = {**started['execution'], 'workflow': 'creative_loop_v1'}
        service.directory = self.folder
        service_client = service.client('planner')
        self.assertEqual(single_client.options, service_client.options)
        self.assertEqual(single_client.options['endpoint'], 'fixture://private-route')
        self.assertEqual(single_client.model, 'fixture/override')
        self.assertEqual(single_client.reasoning_effort, 'medium')
        # The campaign freezes these same role options before the service uses them.
        resolved, _, roles = unified_benchmark.model_configuration(started['execution']['planner'], started['execution']['models'])
        self.assertEqual(resolved, started['execution']['planner'])
        self.assertEqual(roles['planner'], started['execution']['models']['planner'])

    def test_new_default_is_current_loop_and_legacy_is_explicit(self):
        with patch('vlm.openrouter.OpenRouterVisionModel', FixtureClient):
            self.invoke(self.new_args())
            current = self.calls[-1]['start']
            self.assertEqual((current['workflow'], current['mode']), ('creative_loop_v1', 'loop'))
            self.assertEqual(current['max_generations'], 4)
            self.assertEqual(current['execution']['continuation_policy']['completion_policy'], 'fixed_generation_budget')
            self.invoke([*self.new_args(), '--workflow', 'legacy'])
            old = self.calls[-1]['start']
            self.assertEqual((old['workflow'], old['mode']), ('legacy', 'plan'))

    def test_execution_factory_and_resource_profile_reach_the_runtime(self):
        path = self.profile()
        value = load(path)
        value['resource_policy'] = {'max_wall_seconds': 1234}
        save(path, value)
        self.invoke([*self.new_args(), '--profile', str(path), '--max-generations', '3'])
        started = self.calls[-1]['start']
        from planner_harness import resources, continuation
        state = {'config': {'max_generations': started['max_generations']}}
        execution = started['execution']
        resources.configure(state, execution['resource_policy'], continuation=execution['continuation_policy'])
        continuation.configure(state, execution['continuation_policy'])
        self.assertEqual(state['config']['resource_policy']['max_generations'], 3)
        self.assertEqual(state['config']['continuation_policy']['hard_generation_limit'], 3)
        self.assertEqual(state['config']['resource_policy']['max_wall_seconds'], 1234)
        self.assertEqual(load(path), value)
        # An execution file can supply the client without a separate role profile.
        execution_path = self.folder / 'execution.json'
        save(execution_path, {'models': value['models']})
        self.invoke([*self.new_args(), '--execution-config', str(execution_path)])
        self.assertEqual(self.calls[-2]['client'].options['endpoint'], 'fixture://private-route')

    def test_resume_retains_saved_factory_effort_and_budget(self):
        profile = load(self.profile())
        config = {'workflow': 'creative_loop_v1', 'model': 'fixture/planner', 'reasoning_effort': None,
                  'backend': 'FixtureClient', 'resource_policy': {'max_generations': 3},
                  'execution': {'models': profile['models'], 'review': {'mode': 'planner'}}}
        run = self.folder / 'resume'
        save(run / 'state.json', {'config': config})
        before = sha(run / 'state.json')
        self.invoke(['--output', str(run), '--resume'])
        self.assertIsNone(self.calls[0]['client'].reasoning_effort)
        self.assertEqual(self.calls[0]['client'].options['endpoint'], 'fixture://private-route')
        self.assertIsNone(self.calls[-1]['resume']['execution'])
        self.assertEqual(sha(run / 'state.json'), before)
        count = len(FixtureClient.instances)
        for override in (['--max-generations', '4'], ['--backend', 'openrouter'], ['--reasoning', 'high']):
            with self.subTest(override=override), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.invoke(['--output', str(run), '--resume', *override])
        self.assertEqual(len(FixtureClient.instances), count)

    def test_historical_resume_does_not_load_the_new_default_profile(self):
        run = self.folder / 'old'
        save(run / 'state.json', {'config': {'workflow': 'legacy', 'model': 'fixture/old',
                                           'reasoning_effort': 'xhigh', 'backend': 'OpenRouterVisionModel'}})
        with patch('vlm.openrouter.OpenRouterVisionModel', FixtureClient):
            self.invoke(['--output', str(run), '--resume'])
        self.assertEqual(self.calls[0]['client'].model, 'fixture/old')
        self.assertIsNone(self.calls[-1]['resume']['execution'])

    def test_full_and_none_share_completion_contract(self):
        from planner_harness.creative_knowledge import CreativeKnowledge
        texts = []
        for mode in ('full', 'none'):
            knowledge = CreativeKnowledge(ROOT, experience_mode=mode)
            path = (ROOT / 'src/planner_harness/CREATIVE_LOOP.md' if mode == 'full'
                    else ROOT / knowledge.allowlist['operations_manual'])
            text = path.read_text()
            texts.append(text[text.index('Choose the render input explicitly.'):text.index('Read pages stay in working memory')])
        self.assertEqual(texts[0], texts[1])
        self.assertIn('no `stop_reason` bypasses', texts[0])


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.batch = self.folder / 'zero'
        save(self.batch / 'batch.json', {'schema': 'lha-unified-benchmark-v1', 'arms': ['none'],
                                      'topics': [{'id': '001'}, {'id': '002'}]})

    def tearDown(self):
        self.tmp.cleanup()

    def dispatch(self):
        save(self.batch / 'dispatch-status.json', {'claims': [
            {'topic': '001', 'status': 'settled', 'owner': 'fixture'},
            {'topic': '002', 'status': 'claimed', 'owner': 'fixture'}], 'workers': {'0': None}})
        save(self.batch / 'methods/001/none/settlement.json', {'topic': '001', 'method': 'none', 'status': 'ready'})

    def cli_status(self, cli, args):
        stream = io.StringIO()
        with patch.object(sys, 'argv', [cli.__file__, *args]), contextlib.redirect_stdout(stream):
            cli.main()
        return json.loads(stream.getvalue())

    def test_live_dispatch_counts_are_identical_in_both_status_entries(self):
        self.dispatch()
        one = self.cli_status(campaign_cli, ['status', '--output', str(self.folder)])['zero']
        two = self.cli_status(batch_cli, ['status', '--output', str(self.batch)])
        self.assertEqual(one, two)
        self.assertEqual((one['status'], one['ready'], one['planned']), ('running', 1, 2))
        self.assertEqual(one['claim_counts']['claimed'], 1)

    def test_serial_checkpoint_and_durable_receipts_are_deduplicated(self):
        row = {'topic': '001', 'method': 'none', 'status': 'ready'}
        save(self.batch / 'checkpoint.json', {'status': 'running', 'settled': [row]})
        save(self.batch / 'methods/001/none/settlement.json', row)
        save(self.batch / 'methods/002/none/settlement.json', {'topic': '002', 'method': 'none', 'status': 'execution_unknown'})
        result = campaign.batch_status(self.batch)
        self.assertEqual((result['ready'], result['recorded']), (1, 2))
        self.assertEqual(result['unresolved'][0]['topic'], '002')

    def test_final_checkpoint_wins_until_a_new_dispatch_record(self):
        self.dispatch()
        checkpoint = self.batch / 'checkpoint.json'
        save(checkpoint, {'status': 'settled', 'positions': [{'topic': '001', 'method': 'none', 'status': 'ready'}]})
        os.utime(self.batch / 'dispatch-status.json', ns=(1000000000, 1000000000))
        self.assertEqual(campaign.batch_status(self.batch)['status'], 'settled')
        os.utime(checkpoint, ns=(500000000, 500000000))
        self.assertEqual(campaign.batch_status(self.batch)['status'], 'running')

    def test_prepared_and_multi_model_roots_are_discovered_without_launching(self):
        self.assertEqual(campaign.batch_status(self.batch)['status'], 'prepared')
        save(self.folder / 'bernini/campaign.json', {'fixture': True})
        result = self.cli_status(campaign_cli, ['status', '--output', str(self.folder)])
        self.assertIn('bernini', result)
        self.assertEqual(result['bernini']['pre-experience']['status'], 'not_started')
        self.assertNotIn('zero', result['bernini'])

    def test_current_pre_experience_status_does_not_claim_a_no_knowledge_run(self):
        save(self.folder / 'pre-experience/batch.json',
             {'arms': ['pre-experience'], 'topics': [{'id': 'fixture'}]})
        report = self.cli_status(campaign_cli, ['status', '--output', str(self.folder)])
        self.assertEqual(report['pre-experience']['planned'], 1)
        self.assertEqual(report['zero']['planned'], 2)


if __name__ == '__main__':
    unittest.main()
