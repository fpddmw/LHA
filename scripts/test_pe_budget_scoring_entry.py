"""Actual PE inputs, formula clocks and complete one-command scoring offline."""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from experiments import bernini_pe, campaign, pe_loop, results, unified_benchmark
from planner_harness import accounting, resources
from planner_harness.common import load, save, sha
from test_unified_results import Fixture
from test_low_high import Judge


class FormulaTests(unittest.TestCase):
    def test_renderer_and_count_determine_time_and_token_estimates(self):
        for backend, seconds in [('bernini', 1200), ('ditto', 2400)]:
            for count in (1, 4, 8):
                estimate = resources.estimate_budget(backend, count)
                self.assertEqual(estimate['estimated_wall_seconds'], seconds * (count + .5))
                self.assertEqual(estimate['estimated_total_tokens'], 1000000 * (count + .5))
                state = {'config': {'max_generations': count}}
                policy = resources.configure(state, backend=backend)
                self.assertEqual(policy['max_wall_seconds'], estimate['max_wall_seconds'])
                self.assertIsNone(policy['max_total_tokens'])
        config = campaign.configuration(ROOT / 'configs/experiment-campaign.json')
        self.assertIsNone(campaign.stage_config(config, 'direct', 'ditto')['task_wall_seconds'])
        self.assertIsNone(campaign.stage_config(config, 'pe-loop', 'bernini')['task_wall_seconds'])

    def test_unlimited_ditto_clock_resumes_and_tokens_do_not_block_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = accounting.default_online_policy(backend='ditto')
            root = accounting.install(Path(tmp) / 'accounting', policy)
            scope = accounting.scope(root, 'topic', 'full')
            first = accounting.start_task(scope)
            self.assertIsNone(first['deadline_unix'])
            self.assertEqual(accounting.start_task(scope), first)
            record = accounting.reserve(scope, 'large-model-call', 'model', 'fixture', tokens=10000000)
            self.assertEqual(record['reserved_tokens'], 10000000)
            self.assertIsNone(load(root / 'policy.json')['allocations']['full']['tokens'])


class OfficialPETests(Fixture):
    def test_official_template_and_actual_runtime_input(self):
        tree = ast.parse((ROOT / 'third_party/Bernini/bernini/prompt_enhancer.py').read_text())
        original = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == 'V2V_TEMPLATE' for t in n.targets))
        self.assertEqual(bernini_pe.OFFICIAL_V2V_TEMPLATE, original)
        prompt = pe_loop.system_prompt('bernini')
        for category in range(1, 16):
            self.assertIn(str(category) + '. ', prompt)
        self.assertIn('thin matte-black rectangular frame', prompt)
        self.assertIn('Concretization:', prompt)
        self.assertIn('Camera Movement', prompt)
        self.assertIn('Return exactly JSON', prompt)
        self.assertNotIn('Output ONLY the final enhanced English prompt.', prompt)
        batch = self.prepare(methods=['pe-loop'], backend='bernini', training_maintenance=False)
        topic = batch['topics'][0]
        accounting.install(self.output / 'accounting')
        seen = []
        class Model:
            model = 'gpt-6.1-sol'
            reasoning_effort = 'high'
            def predict_text(self, **kw):
                seen.append(kw)
                return json.dumps({'prompt': 'Convert the video to blue ceramic: glazed figures and tiled surfaces.'})
        runtime = unified_benchmark.Runtime.__new__(unified_benchmark.Runtime)
        runtime.batch = batch
        runtime.service = SimpleNamespace(model_factory=lambda role: Model())
        history = [{'candidate': {'id': 'v1'}, 'prompt': 'Convert the video to blue ceramic.',
                    'feedback': {'report': {'summary': 'The garments retain their fabric surface.'}, 'evidence': []}}]
        runtime.refine(topic, self.root / 'rewrite', accounting.topic_scope(self.output, topic['id'], lane='pe-loop'), history)
        self.assertEqual(seen[0]['system_prompt'], prompt)
        self.assertEqual(json.loads(seen[0]['user_text'])['original_request'], topic['request'])
        self.assertEqual(len(seen[0]['image_paths']), 8)
        self.assertIn('garments retain', seen[0]['user_text'])


class ScoringEntryTests(Fixture):
    def test_one_command_prepares_scores_every_family_and_resumes(self):
        import benchmark_results as entry
        from evaluation import creative, final_suite, low_high, pairwise, providers, temporal
        for form in ('short', 'long'):
            for method in ('direct', 'pe'):
                results.import_video(self.repo, self.registry,
                    self.row(prompt_form=form, request=self.rows[0]['prompt_' + form], method=method))
        models = {}
        for name in providers.JUDGES:
            model = Judge()
            model.model = name
            model.reasoning_effort = providers.judge_identity(name)['reasoning_effort']
            models[name] = model
        arguments = ['benchmark_results.py', 'score-evaluation', '--root', str(self.registry), '--execute']
        with patch.object(entry, 'ROOT', self.repo), patch.object(sys, 'argv', arguments), \
             patch('planner_harness.supervisor.maybe_supervise_cli', return_value=False), \
             patch.object(creative, 'make_judge', side_effect=lambda name: models[name]), \
             patch.object(final_suite.features, 'compute', return_value={'clip_f': .9, 'dino_f': .8}) as features, \
             patch.object(temporal, 'compute', wraps=temporal.compute) as motion, \
             contextlib.redirect_stdout(io.StringIO()):
            entry.main()
            directory, evaluation = results.current_evaluation(self.registry)
            original = sha(directory / 'evaluation.json')
            calls = sum(len(m.calls) for m in models.values())
            feature_calls, motion_calls = features.call_count, motion.call_count
            entry.main()
            self.assertEqual(sum(len(m.calls) for m in models.values()), calls)
            self.assertEqual((features.call_count, motion.call_count), (feature_calls, motion_calls))
        self.assertEqual(sha(directory / 'evaluation.json'), original)
        self.assertGreater(feature_calls, 0)
        self.assertGreater(motion_calls, 0)
        visible = [v for model in models.values() for v in model.calls]
        self.assertEqual({v['task_spec']['track'] for v in visible}, {'short', 'long'})
        self.assertTrue(any(v.get('stage') == 'task_metrics' for v in visible))
        self.assertTrue(any(v.get('protocol_id') == low_high.PROTOCOL for v in visible))
        self.assertTrue(any(v.get('protocol_id') == pairwise.PROTOCOL for v in visible))
        self.assertTrue(any('scope' in v for v in visible))
        view = load(self.registry / 'results.json')
        coverage = view['evaluation_coverage']
        self.assertTrue(coverage['blind_comparisons_finished'])
        self.assertGreater(coverage['continuous_event_reviews'], 0)
        self.assertGreater(coverage['blind_question_outcomes']['tie'], 0)
        for family in coverage['metric_families'].values():
            for states in family.values():
                self.assertNotIn('pending', states)
        self.assertIn('scored', coverage['metric_families']['objective_and_motion']['clip_f'])
        self.assertIn('not_applicable', coverage['metric_families']['objective_and_motion']['flow_velocity_error'])
        page = (self.registry / 'index.html').read_text()
        for label in ('五维主表', '必要内容保留', '短任务专项', '长任务专项', '美学明细', '客观指标与运动诊断', '独立盲评'):
            self.assertIn(label, page)

    def test_dual_campaign_score_needs_no_generation_host_or_library(self):
        import run_experiment_campaign as entry
        config = self.root / 'campaign-config.json'
        save(config, campaign.configuration(ROOT / 'configs/experiment-campaign.json'))
        original = {}
        for name in ('bernini', 'ditto'):
            output = self.root / name
            save(output / 'campaign.json', {'old_generation_configuration': name})
            original[name] = sha(output / 'campaign.json')
            results.import_video(self.repo, output / 'results', self.row())
        args = ['run_experiment_campaign.py', 'run', '--backend', 'both', '--stage', 'score',
                '--output', str(self.root), '--config', str(config), '--execute']
        with patch.object(entry, 'ROOT', self.repo), patch.object(sys, 'argv', args), \
             patch.object(campaign, 'seed_library', side_effect=AssertionError('Scoring needs no generation library')), \
             patch.object(campaign, 'plan', return_value={'batches': [{'stage': 'pre-experience', 'conditions': 4}]}), \
             patch.object(results, 'score_evaluation', return_value={}) as score, \
             patch.object(results, 'report', return_value={}), contextlib.redirect_stdout(io.StringIO()):
            entry.main()
        self.assertEqual([c.args[1] for c in score.call_args_list],
                         [self.root / name / 'results' for name in ('bernini', 'ditto')])
        for name in original:
            self.assertEqual(sha(self.root / name / 'campaign.json'), original[name])
            self.assertFalse((self.root / name / 'host-input.json').exists())
            self.assertIsNotNone(results.current_evaluation(self.root / name / 'results'))

    def test_old_scoring_namespace_is_preserved_and_replaced_automatically(self):
        from evaluation import low_high
        results.import_video(self.repo, self.registry, self.row())
        old = {**low_high.profile(), 'sha256': 'old-protocol'}
        with patch.object(low_high, 'profile', return_value=old):
            results.prepare_evaluation(self.repo, self.registry, evaluation_id='old')
        original = sha(self.registry / 'evaluations/old/evaluation.json')
        directory, current = results.ensure_evaluation(self.repo, self.registry, evaluation_id='old')
        self.assertNotEqual(current['evaluation_id'], 'old')
        self.assertEqual(results.ensure_evaluation(self.repo, self.registry, evaluation_id='old')[0], directory)
        self.assertEqual(sha(self.registry / 'evaluations/old/evaluation.json'), original)


if __name__ == '__main__':
    unittest.main()
