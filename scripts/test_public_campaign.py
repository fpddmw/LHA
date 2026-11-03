"""Public entry contracts and a synthetic delivery/maintenance/scoring handoff."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from experiments import campaign, readiness, results
from planner_harness import PlannerHarness, maintenance, training_experience as tx
from planner_harness.common import load, save, sha
from planner_harness.creative_knowledge import CreativeKnowledge
from planner_harness.delivery import verify_delivery
from planner_harness.execution import collect
from test_unified_results import Fixture
import test_creative_loop as scripted


class PublicChecks(Fixture):
    def setUp(self):
        super().setUp()
        self.config = campaign.configuration(ROOT / 'configs/experiment-campaign.json')
        self.config['rsi_partition'] = {'train_count': 1, 'test_count': 1}
        source = self.repo / 'source-two.mp4'
        source.write_bytes(self.source.read_bytes() + b'offline-fixture')
        self.rows[1].update(source_video='source-two.mp4', source_video_sha256=sha(source))
        save(self.repo / 'benchmark_data/benchmark.json', self.rows)

    def host(self):
        host = load(ROOT / 'configs/bernini-campaign-host.example.json')
        manifest = self.repo / 'assets.json'
        save(manifest, {'files': [{'path': 'source.mp4', 'bytes': self.source.stat().st_size,
                                   'sha256': sha(self.source)}]})
        host['renderer'].update(asset_manifest='assets.json', asset_manifest_sha256=sha(manifest))
        return host

    def test_check_validates_files_without_clients_or_gpu(self):
        with patch('vlm.settings.create_client', side_effect=AssertionError('No model construction')):
            report = readiness.check(self.repo, self.config, {'bernini': self.host()}, verify_assets=True)
        self.assertEqual(report['status'], 'offline_checks_passed', report)
        self.assertEqual(report['live_model_calls'], 0)
        self.assertIn('GPU/CUDA compatibility and memory', report['not_checked'])

    def test_missing_inputs_are_actionable_and_private_values_are_not_printed(self):
        host = self.host()
        host['renderer']['asset_manifest_sha256'] = 'PRIVATE_TEST_VALUE'
        (self.repo / self.rows[0]['prompt_file']).unlink()
        report = readiness.check(self.repo, self.config, {'bernini': host})
        failed = {row['name'] for row in report['checks'] if row['status'] != 'passed'}
        self.assertIn('dataset_files', failed)
        self.assertIn('bernini_assets', failed)
        self.assertNotIn('PRIVATE_TEST_VALUE', json.dumps(report))

    def test_cli_check_reports_missing_host_without_preparing_a_batch(self):
        import run_experiment_campaign as entry
        path = self.root / 'config.json'
        save(path, self.config)
        with patch.object(entry, 'ROOT', self.repo), patch.object(sys, 'argv',
             ['run_experiment_campaign.py', 'check', '--config', str(path), '--output', str(self.output)]), \
             patch.object(campaign, 'execute', side_effect=AssertionError('No launch')), \
             contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(entry.main(), 2)
        self.assertEqual(json.loads(stream.getvalue())['status'], 'needs_configuration')
        self.assertFalse(self.output.exists())


class SyntheticHandoff(Fixture):
    def test_deliver_maintain_freeze_read_score_and_reuse(self):
        from evaluation import creative, final_suite, providers
        from test_low_high import Judge

        # All output stays in an isolated repository. Use the published corpus,
        # while renderer responses and model judgments are explicitly synthetic.
        for name in ['src/planner_harness/CREATIVE_LOOP.md', 'docs/experience-authoring-standard.md',
                     'docs/experience-usage-interface.md', 'docs/online-event-observation.md',
                     *[f'.agents/skills/{name}/SKILL.md' for name in maintenance.SKILLS]]:
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        seed = self.root / 'seed.json'
        CreativeKnowledge(ROOT, experience_mode='full').freeze(seed)
        none_snapshot = self.root / 'none.json'
        CreativeKnowledge(ROOT, experience_mode='none').freeze(none_snapshot)
        initial = load(seed)
        entry_id = initial['curated_catalog']['entries'][0]['id']
        self.registry = self.root / 'example/results'
        traces = []
        for mode in ('critic', 'planner'):
            campaign_root = self.root / 'example' / mode
            family = campaign_root / ('zero' if mode == 'critic' else 'self-review-zero')
            before = tx.initialize(self.repo, family, seed, review_mode=mode)
            save(family / 'batch.json', {'sha256': 'synthetic', 'review': {'mode': mode},
                'training_maintenance': True, 'arms': ['none'], 'backend': 'bernini',
                'experience_owner': before['owner'], 'topics': [{'id': '001-short', 'split': 'train'}]})
            for arm in ('none', 'full'):
                snapshot = none_snapshot if arm == 'none' else frozen
                run = campaign_root / ('online-' + arm)
                self.h = PlannerHarness(run, scripted.Scripted([
                    scripted.action('generate', input_video='source', prompt='Synthetic blue treatment.')]), root=self.repo)
                self.h.start(self.source, self.rows[0]['prompt_short'], mode='loop', workflow='creative_loop_v1',
                    execution={'mode': 'replay', 'experience_mode': arm,
                        'experience_snapshot': str(snapshot), 'experience_snapshot_sha256': sha(snapshot),
                        'review': {'mode': mode}, 'renderer': {'backend': 'bernini', 'seed': 42},
                        'resource_policy': {'max_generations': 4},
                        'continuation_policy': {'completion_policy': 'fixed_generation_budget'},
                        'benchmark_metadata': {'split': 'train', 'sample_id': '001'}})
                for n in range(1, 5):
                    scripted.CreativeTests.respond(self, review=mode == 'critic')
                    if mode == 'planner':
                        collect(self.h)
                    action = (scripted.action('generate', input_video='v1', prompt=f'Synthetic alternative {n+1}.')
                              if n < 4 else scripted.action('finish', video='v1', message='Synthetic earlier-version choice.'))
                    if mode == 'planner':
                        action['review'] = {'video_id': f'v{n}', 'summary': 'Scripted self-review; no quality claim.', 'findings': []}
                    self.h.checkpoint()
                    self.h.model = scripted.Scripted([action])
                    self.h.resume()
                delivery = verify_delivery(run)
                self.assertEqual(delivery['selected'], 'v1')
                self.assertEqual(len(self.h.state['submitted_generation_ids']), 4)
                critic_jobs = [j for j in self.h.state['jobs'].values() if j['kind'] == 'critique']
                self.assertEqual(len(critic_jobs), 4 if mode == 'critic' else 0)
                candidates = [{'id': f'v{n}', 'video': str(self.source), 'video_sha256': sha(self.source),
                               'seed': 41+n, 'roles': (['first', 'selected'] if n == 1 else ['last'] if n == 4 else [])}
                              for n in range(1, 5)]
                results.import_video(self.repo, self.registry, self.row(method=arm, review_mode=mode,
                    candidates=candidates, evidence={'synthetic': True, 'delivery_sha256': sha(run / 'state.json')}))
                online_hash = sha(run / 'knowledge-snapshot.json')
                if arm == 'none':
                    self.assertEqual(load(run / 'knowledge-snapshot.json')['curated_catalog']['entries'], [])
                    job = maintenance.enqueue(self.repo, family, run, split='train', topic='001-short', method='none',
                        batch_sha256='synthetic', maintenance_snapshot=before)
                    class Contributor:
                        model = 'scripted-maintainer'; reasoning_effort = 'high'
                        def predict_text(inner, **kwargs):
                            return json.dumps({'action': 'contribute', 'arguments': {
                                'text': 'Synthetic contribution for interface testing only.', 'changes': [{
                                    'op': 'comment', 'id': entry_id, 'text': 'Synthetic boundary; no empirical claim.'}]}})
                    result = tx.maintain(self.repo, family, run, job,
                        {'model_calls': 2, 'attempts': 1, 'wall_seconds': 60}, model_factory=Contributor)
                    self.assertEqual(result['status'], 'activated', result)
                    after = tx.current(self.repo, family)
                    self.assertNotEqual(before['snapshot_sha256'], after['snapshot_sha256'])
                    save(family / 'methods/001-short/none/settlement.json', {'status': 'ready'})
                    frozen = campaign.freeze_training(self.repo, campaign_root, review_mode=mode)
                    self.assertEqual(sha(frozen), after['snapshot_sha256'])
                else:
                    self.assertEqual(tx.current(self.repo, family)['snapshot_sha256'], after['snapshot_sha256'])
                    related = self.h.knowledge.read(entry_id)['related_contributions']
                    self.assertTrue(related)
                self.assertEqual(sha(run / 'knowledge-snapshot.json'), online_hash)
                traces.append({'mode': mode, 'arm': arm, 'submitted': 4, 'selected': 'v1',
                               'online_critic_jobs': len(critic_jobs), 'run': str(run)})
        results.import_video(self.repo, self.registry, self.row())
        models = {}
        for name in providers.JUDGES:
            model = Judge(); model.model = name
            model.reasoning_effort = providers.judge_identity(name)['reasoning_effort']
            models[name] = model
        with patch.object(creative, 'make_judge', side_effect=lambda name: models[name]), \
             patch.object(final_suite.features, 'compute', return_value={'clip_f': .9, 'dino_f': .8}):
            results.score_evaluation(self.repo, self.registry, None)
            calls = sum(len(m.calls) for m in models.values())
            results.score_evaluation(self.repo, self.registry, None)
            self.assertEqual(sum(len(m.calls) for m in models.values()), calls)
        view = load(self.registry / 'results.json')
        self.assertEqual(view['ready'], 5)
        self.assertTrue(view['evaluation_coverage']['blind_comparisons_finished'])
        self.assertTrue((self.registry / 'index.html').exists())
        save(self.root / 'example/trace-summary.json', {'synthetic': True, 'trajectories': traces,
             'live_model_calls': 0, 'gpu_generations': 0, 'scripted_judge_calls': calls})
        (self.root / 'example/README.md').write_text(
            '# Synthetic software smoke example\n\nAll videos, decisions, contributions and scores are fixtures.\n'
            'Four Planner trajectories each submit four synthetic renders and select v1.\n'
            'Critic and self-review maintain separate private libraries; full reads its own revision.\n'
            'Results include Direct, first/last/selected, two scripted judges and blind comparisons.\n'
            'Run paths in copied receipts refer to the temporary test workspace.\n'
            'Use results/index.html and trace-summary.json for the retained portable view.\n', encoding='utf-8')
        if os.environ.get('LHA_SMOKE_ARTIFACTS'):
            shutil.copytree(self.root / 'example', os.environ['LHA_SMOKE_ARTIFACTS'])


if __name__ == '__main__':
    unittest.main()
