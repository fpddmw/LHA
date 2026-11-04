"""PE Loop budgets, phase recovery and result reuse. No API/GPU execution."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from test_unified_results import Fixture
from experiments import pe_loop, results, unified_benchmark as u
from planner_harness import accounting
from planner_harness.common import save, load, sha
from planner_harness.integrity import IntegrityError
from planner_harness.resources import ResourceExhausted
from planner_harness.video import Video


class PELoopTests(Fixture):
    def setup_loop(self, n=3, **options):
        batch = self.prepare(methods=['pe-loop'], best_of_n=None, max_generations=n, **options)
        accounting.install(self.output / 'accounting')
        fixture = self

        class Runtime:
            def __init__(self):
                self.calls = []
                self.fail_review = False
                self.fail_choose = False
                self.stop_round = None
                self.last_history = None

            def refine(self, topic, directory, scope, history):
                self.calls.append(('refine', len(history)))
                self.last_history = copy.deepcopy(history)
                if self.stop_round == len(history) + 1:
                    raise ResourceExhausted('Task time exhausted')
                return 'A blue painted scene. Round ' + str(len(history) + 1)

            def render(self, topic, method, prompt, seed, number, scope):
                self.calls.append(('render', seed))
                receipt = fixture.root / ('render-' + str(number) + '.json')
                save(receipt, {'seed': seed, 'prompt': prompt})
                return {'video': Video(fixture.source, fixture.root / 'video').info,
                        'response': str(receipt), 'seed': seed}

            def review(self, topic, candidate, directory, scope):
                self.calls.append(('review', candidate['id'], topic['prompt_form'], candidate['prompt']))
                if self.fail_review:
                    self.fail_review = False
                    raise RuntimeError('Interrupted Critic')
                return {'report': {'summary': 'The blue treatment is visible.', 'findings': []},
                        'evidence': []}

            def choose(self, topic, candidates, reviews, directory, scope):
                self.calls.append(('choose', len(candidates)))
                if self.fail_choose:
                    self.fail_choose = False
                    raise RuntimeError('Interrupted selection')
                return 0, {'policy': u.SELECTOR, 'selected_index': 0,
                           'reason': 'The first candidate retains clearer silhouettes.', 'model_called': True}

            def close(self):
                pass

        return batch, Runtime()

    def run_loop(self, batch, runtime, topic=None):
        return u.execute_method(self.repo, self.output, topic or batch['topics'][0], 'pe-loop', batch, runtime)

    def test_test_default_is_four_groups_and_old_methods_remain_explicit(self):
        batch = self.prepare(splits=['test'], methods=None, best_of_n=None)
        self.assertEqual(batch['arms'], ['direct', 'pe-loop', 'none', 'full'])
        self.assertEqual(sum(1 if m == 'direct' else batch['max_generations'] for m in batch['arms']), 13)
        self.assertIn('pe', results.RUN_METHODS)
        self.assertIn('direct-best-of-n', results.RUN_METHODS)
        self.assertFalse(batch['pe_loop']['knowledge_access'])

    def test_three_rounds_reuse_feedback_and_register_first_last_selected(self):
        batch, runtime = self.setup_loop()
        result = self.run_loop(batch, runtime)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual([v[1] for v in runtime.calls if v[0] == 'render'], [42, 43, 44])
        self.assertEqual([v[1] for v in runtime.calls if v[0] == 'refine'], [0, 1, 2])
        self.assertEqual(len(runtime.last_history), 2)
        row = results.find(self.registry, '001', 'short', 'pe-loop', 42)
        self.assertEqual(row['evidence']['actual_generations'], 3)
        self.assertEqual(row['candidates'][0]['roles'], ['first', 'selected'])
        self.assertEqual(row['candidates'][2]['roles'], ['last'])
        self.assertEqual(row['evidence']['selection']['reviewed'], 3)
        self.assertEqual(row['evidence']['method_identity']['max_generations'], 3)
        before = list(runtime.calls)
        self.run_loop(batch, runtime)
        self.assertEqual(runtime.calls, before)
        plan = results.prepare_evaluation(self.repo, self.registry, evaluation_id='pe-test')
        self.assertEqual({p['position'] for p in plan['positions']}, {'first', 'last', 'final'})
        self.assertEqual(len({results._score_key(p, 'judge') for p in plan['positions']}), 1)
        view = results.report(self.repo, self.registry)
        ready = next(r for r in view['results'] if r['method'] == 'pe-loop' and r['status'] == 'ready')
        self.assertEqual(ready['first']['id'], 'v1')
        self.assertEqual(ready['last']['id'], 'v3')

    def test_n_one_needs_one_enhancement_render_review_and_no_selection_call(self):
        batch, runtime = self.setup_loop(n=1)
        self.run_loop(batch, runtime)
        self.assertEqual([v[0] for v in runtime.calls], ['refine', 'render', 'review'])
        row = results.find(self.registry, '001', 'short', 'pe-loop', 42)
        self.assertEqual(set(row['candidates'][0]['roles']), {'first', 'last', 'selected'})

    def test_resume_review_failure_does_not_rewrite_or_render_again(self):
        batch, runtime = self.setup_loop(n=2)
        runtime.fail_review = True
        with self.assertRaisesRegex(RuntimeError, 'Interrupted Critic'):
            self.run_loop(batch, runtime)
        folder = self.output / 'methods' / batch['topics'][0]['id'] / 'pe-loop'
        self.assertEqual(load(folder / 'progress.json')['phase'], 'review')
        self.assertIsNone(results.find(self.registry, '001', 'short', 'pe-loop', 42))
        self.run_loop(batch, runtime)
        self.assertEqual(sum(v[0] == 'render' for v in runtime.calls), 2)
        self.assertEqual(sum(v[0] == 'refine' for v in runtime.calls), 2)
        self.assertEqual(sum(v[0] == 'review' for v in runtime.calls), 3)

    def test_resume_selection_failure_reuses_completed_reviews(self):
        batch, runtime = self.setup_loop(n=2)
        runtime.fail_choose = True
        with self.assertRaisesRegex(RuntimeError, 'Interrupted selection'):
            self.run_loop(batch, runtime)
        self.run_loop(batch, runtime)
        self.assertEqual(sum(v[0] == 'render' for v in runtime.calls), 2)
        self.assertEqual(sum(v[0] == 'review' for v in runtime.calls), 2)

    def test_budget_stop_keeps_committed_choice_and_separate_last_candidate(self):
        batch, runtime = self.setup_loop()
        runtime.stop_round = 3
        result = self.run_loop(batch, runtime)
        self.assertTrue(result['partial'])
        row = results.find(self.registry, '001', 'short', 'pe-loop', 42)
        self.assertEqual(row['evidence']['delivery_kind'], 'deadline_delivery')
        self.assertEqual(row['evidence']['actual_generations'], 2)
        self.assertEqual(row['candidates'][-1]['roles'], ['last'])

    def test_unknown_selection_keeps_original_phase_for_recovery(self):
        batch, runtime = self.setup_loop(n=4)
        def choose(topic, candidates, reviews, directory, scope):
            if len(candidates) == 2:
                return 1, {'policy': u.SELECTOR, 'selected_index': 1,
                           'reason': 'Second candidate has the preferred design.', 'model_called': True}
            raise accounting.ExternalExecutionUnknown('Interrupted selection stream')
        runtime.choose = choose
        with self.assertRaises(accounting.ExternalExecutionUnknown):
            self.run_loop(batch, runtime)
        folder=self.output/'methods'/batch['topics'][0]['id']/'pe-loop'
        self.assertFalse((folder/'complete.json').exists())
        self.assertEqual(load(folder/'progress.json')['phase'],'select')
        runtime.choose=lambda *args: (1, {'policy':u.SELECTOR,'selected_index':1,'reason':'Original choice after recovery'})
        self.run_loop(batch, runtime)
        self.assertEqual(sum(v[0]=='render' for v in runtime.calls),4)
        self.assertEqual(sum(v[0]=='review' for v in runtime.calls),4)

    def test_unknown_review_remains_recoverable(self):
        batch, runtime = self.setup_loop(n=2)
        def review(*args):
            raise accounting.ExternalExecutionUnknown('Interrupted review')
        runtime.review = review
        with self.assertRaises(accounting.ExternalExecutionUnknown):
            self.run_loop(batch, runtime)
        directory = self.output / 'methods' / batch['topics'][0]['id'] / 'pe-loop'
        self.assertEqual(load(directory / 'progress.json')['phase'], 'review')
        self.assertFalse((directory / 'complete.json').exists())

    def test_changed_default_budget_reuses_original_pe_result(self):
        batch, runtime = self.setup_loop(n=1)
        self.run_loop(batch, runtime)
        changed = {**batch, 'max_generations': 3}
        before=list(runtime.calls)
        self.run_loop(changed, runtime)
        self.assertEqual(runtime.calls,before)

    def test_long_task_routes_to_the_same_critic_with_long_track(self):
        batch, runtime = self.setup_loop(n=1)
        topic = next(t for t in batch['topics'] if t['prompt_form'] == 'long')
        self.run_loop(batch, runtime, topic)
        self.assertEqual(next(v for v in runtime.calls if v[0] == 'review')[2], 'long')

    def test_pe_stays_shared_critic_when_planner_loop_uses_self_review(self):
        batch, runtime = self.setup_loop(n=1, review={'mode': 'planner'})
        self.run_loop(batch, runtime)
        row = results.find(self.registry, '001', 'short', 'pe-loop', 42)
        self.assertEqual(row['review_mode'], 'shared')
        self.assertEqual(row['evidence']['method_identity']['pe_loop']['review_mode'], 'critic')
        self.assertEqual(sum(v[0] == 'review' for v in runtime.calls), 1)

    def test_other_model_requires_a_different_experiment_contract(self):
        with self.assertRaisesRegex(ValueError, 'GPT-6.1-sol high'):
            self.prepare(methods=['pe-loop'], best_of_n=None, planner={'model': 'other', 'reasoning_effort': 'high'})

    def test_model_receives_online_diagnostics_and_actual_images_without_scores(self):
        batch, runtime = self.setup_loop(n=2)
        topic = batch['topics'][0]
        seen = []
        class Model:
            model = 'gpt-6.1-sol'
            reasoning_effort = 'high'
            def predict_text(self, **kwargs):
                seen.append(kwargs)
                return json.dumps({'prompt': 'A detailed blue painted scene with clear silhouettes.'})
        scope = accounting.topic_scope(self.output, topic['id'], lane='pe-loop')
        model = accounting.attach(Model(), scope)
        frames = Video(self.source, self.root / 'critic-evidence').observe('critic', count=4)['frames']
        evidence = [{**frame, 'id': 'candidate:' + str(frame['frame_index']), 'video_id': 'candidate'} for frame in frames]
        history = [{'candidate': {'id': 'v1'}, 'prompt': 'First prompt',
                    'feedback': {'report': {'summary': 'The colors fit.', 'main_scores': {'bad': 4}}, 'evidence': evidence}}]
        path = self.root / 'rewrite'
        pe_loop.rewrite(topic, path, model, history)
        pe_loop.rewrite(topic, path, model, history)
        self.assertEqual(len(seen), 1)
        self.assertNotIn('main_scores', seen[0]['user_text'])
        self.assertEqual(json.loads(seen[0]['user_text'])['history'][0]['prompt'], 'First prompt')
        self.assertGreater(len(seen[0]['image_paths']), 8)
        self.assertEqual(json.loads(seen[0]['user_text'])['latest_feedback_candidate_id'], 'v1')

    def test_runtime_review_gets_actual_enhanced_prompt(self):
        batch, runtime = self.setup_loop(n=1)
        host = u.Runtime.__new__(u.Runtime)
        model = SimpleNamespace(model='gpt-6.1-sol', reasoning_effort='high')
        host.service = SimpleNamespace(model_factory=lambda role: model)
        scope = accounting.topic_scope(self.output, batch['topics'][0]['id'], lane='pe-loop')
        candidate = {'video': Video(self.source, self.root / 'video').info, 'prompt': 'Actual enhanced prompt'}
        with patch('critic_harness.one_shot.run_review', return_value={'report': {'summary': 'ok'}}) as review:
            host.review(batch['topics'][0], candidate, self.root / 'review', scope)
        self.assertEqual(review.call_args.args[0]['actual_prompt'], 'Actual enhanced prompt')

    def test_scoring_reuses_same_video_and_includes_new_primary_contrast(self):
        from evaluation.low_high import PROTOCOL, profile
        from evaluation.creative import JUDGES
        from evaluation.pairwise import QUESTIONS
        from evaluation.statistics import PLAN
        batch, runtime = self.setup_loop(n=2, splits=['test'])
        topic = batch['topics'][0]
        self.run_loop(batch, runtime, topic)
        for method in ('direct', 'full', 'none'):
            results.import_video(self.repo, self.registry, self.row(sample_id=topic['sample_id'],
                request=topic['request'], method=method, review_mode='critic' if method in ('full','none') else 'shared'))
        results.prepare_evaluation(self.repo, self.registry, evaluation_id='pe-score')
        models = {name: SimpleNamespace(model=name, reasoning_effort=None, requires_live_budget=False) for name in JUDGES}
        absolute, blind = [], []
        def score(request, source, candidate, directory, *, model, plan):
            absolute.append(model.model)
            return {'source_sha256': source['sha256'], 'output_sha256': candidate['sha256'],
                    'model': model.model, 'profile_sha256': profile()['sha256'],
                    'report': {'protocol_id': PROTOCOL, 'main_scores': {}}}
        def compare(request, source, left, right, directory, *, model, plan, seed):
            blind.append(model.model)
            answer = {'status': 'scored', 'judge': model.model, 'final_profile_sha256': profile()['sha256'],
                      'judgments': {q: {'outcome': 'tie', 'mapped_orders': ['tie','tie']} for q in QUESTIONS}}
            save(Path(directory) / 'result.json', answer)
            return answer
        with patch('evaluation.creative.judge_candidate', side_effect=score), \
             patch('evaluation.final_suite.automatic', return_value={'metrics': {}}), \
             patch('evaluation.pairwise.compare', side_effect=compare):
            view = results.score_evaluation(self.repo, self.registry, models=models)
            results.score_evaluation(self.repo, self.registry, models=models)
        self.assertEqual(len(absolute), len(JUDGES))
        self.assertEqual(len(blind), len(JUDGES))
        label = 'pe-loop_final__to__none_final'
        self.assertIn(label + '/review-critic', view['blind_comparisons'])
        self.assertEqual(PLAN['primary']['comparison'], label)
        metric = view['test_analysis']['by_review_mode']['critic']['by_judge'][next(iter(JUDGES))][label]['task_completion']
        self.assertEqual(metric['role'], 'primary')
        self.assertEqual(metric['planned_source_groups'], 1)

    def test_corrupt_completed_phase_is_rejected_before_more_generation(self):
        batch, runtime = self.setup_loop(n=2)
        runtime.fail_review = True
        with self.assertRaises(RuntimeError):
            self.run_loop(batch, runtime)
        phase = self.output / 'methods' / batch['topics'][0]['id'] / 'pe-loop/rounds/0001/prompt.json'
        record = load(phase)
        record['value'] = 'Different prompt'
        save(phase, record)
        with self.assertRaises(IntegrityError):
            self.run_loop(batch, runtime)
        self.assertEqual(sum(v[0] == 'render' for v in runtime.calls), 1)

    def test_explicit_recovery_reopens_settlement_and_queue_without_repeating_render(self):
        from experiments.recovery import recover_pe_loop
        from experiments.device_scheduler import Claims
        from planner_harness.execution import signature
        batch, runtime = self.setup_loop(n=2, splits=['test'])
        batch = {k:v for k,v in batch.items() if k != 'sha256'}
        batch['topics'] = batch['topics'][:1]
        batch['sha256'] = signature(batch)
        save(self.output / 'batch.json', batch)
        limits = {**accounting.LIMITS, 'amount': None, 'wall_seconds': 60}
        policy = accounting.validate_policy({'version': accounting.VERSION, 'mode': 'live',
            'cost_control': 'count_limits_only', 'lanes': ['pe-loop'], 'batch': limits,
            'topic': limits, 'allocations': {'pe-loop': limits}, 'max_call_seconds': 20})
        # This fixture installed an offline ledger before calling the real batch
        # driver. Give the driver a separate ledger, preserving its phase reuse.
        host = {'devices': ['0'], 'budget': policy}
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as storage:
            old_accounting = self.output / 'accounting'
            old_accounting.rename(Path(storage) / 'offline-accounting')
            runtime.fail_review = True
            with patch.object(u, 'verify', return_value=batch), patch.object(u, 'policy', return_value=policy), \
                 patch.object(u, 'preflight', return_value={}):
                u.run_serial(self.repo, self.output, host, runtime_factory=lambda *args: runtime)
                topic = batch['topics'][0]['id']
                folder = self.output / 'methods' / topic / 'pe-loop'
                self.assertEqual(load(folder / 'settlement.json')['status'], 'recovery_required')
                queue = Claims(self.output / 'device-queue.sqlite3', batch['topics'], batch['sha256'], 'fixture')
                with queue.connect() as db:
                    db.execute('UPDATE tasks SET status="settled"')
                record = recover_pe_loop(self.output, topic, 'Original failure inspected')
                self.assertEqual(record['model_calls'], 0)
                self.assertEqual(queue.rows()[0]['status'], 'pending')
                u.run_serial(self.repo, self.output, host, runtime_factory=lambda *args: runtime)
                self.assertEqual(load(folder / 'settlement.json')['status'], 'ready')
                self.assertTrue(list((folder / 'settlement-history').glob('*.json')))
                self.assertEqual(sum(v[0] == 'render' for v in runtime.calls), 2)

    def test_recovery_refuses_unresolved_external_work(self):
        from experiments.recovery import recover_pe_loop
        batch, runtime = self.setup_loop(n=2)
        runtime.fail_review = True
        with self.assertRaises(RuntimeError):
            self.run_loop(batch, runtime)
        topic = batch['topics'][0]['id']
        ledger_path = self.output / 'accounting/ledger.json'
        ledger = load(ledger_path)
        ledger['operations']['unknown'] = {'id': 'unknown', 'topic': topic, 'status': 'reserved'}
        save(ledger_path, ledger)
        with self.assertRaisesRegex(ValueError, 'Reconcile original external operations'):
            recover_pe_loop(self.output, topic, 'Try recovery')
        self.assertFalse((self.output / 'methods' / topic / 'pe-loop/recovery.json').exists())

    def test_pe_budget_uses_shared_online_count_limit_without_deadline(self):
        batch, runtime = self.setup_loop(n=3)
        limits = {**accounting.LIMITS, 'amount': None}
        supplied = {'version': accounting.VERSION, 'mode': 'live', 'cost_control': 'count_limits_only',
                    'lanes': ['pe-loop'], 'batch': limits, 'topic': limits,
                    'allocations': {'pe-loop': limits}, 'max_call_seconds': 60}
        policy = u.policy(batch, supplied)
        self.assertEqual(policy['online_task_budget']['lanes'], ['pe-loop'])
        self.assertEqual(policy['online_task_budget']['max_generations'], 3)
        self.assertEqual(policy['online_task_budget']['wall_seconds'], None)

    def test_prompt_compaction_is_cached_and_uses_original_scope(self):
        batch, _ = self.setup_loop(n=2)
        topic = batch['topics'][0]
        scope = accounting.topic_scope(self.output, topic['id'], lane='pe-loop')
        seen = []
        class Model:
            model = 'openai/gpt-6.1-sol'
            reasoning_effort = 'high'
            def predict_text(self, **kwargs):
                seen.append(kwargs)
                return json.dumps({'prompt': 'Blue light across the stone surface.'})
        model = accounting.attach(Model(), scope)
        path = self.root / 'compact'
        args = (topic, 'A detailed blue scene. ' * 80, {'token_count': 533, 'token_limit': 512}, path, model, scope)
        answer = pe_loop.compact_prompt(*args)
        with patch.object(accounting, 'check_task', side_effect=ResourceExhausted('deadline')):
            self.assertEqual(pe_loop.compact_prompt(*args), answer)
            with self.assertRaises(ResourceExhausted):
                pe_loop.compact_prompt(*args[:3], self.root / 'new-compact', model, scope)
        self.assertEqual(len(seen), 1)
        packet = json.loads(seen[0]['user_text'])
        self.assertEqual(packet['original_request'], topic['request'])
        self.assertEqual(packet['refusal']['token_count'], 533)
        self.assertLess(packet['target_words'], len(packet['prompt'].split()))
        calls = list(accounting.load_ledger(scope['root'])['operations'].values())
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]['topic'], calls[0]['lane']), (topic['id'], 'pe-loop'))

    def test_runtime_bounds_prompt_revisions_and_leaves_direct_unchanged(self):
        batch, _ = self.setup_loop(n=2)
        topic = batch['topics'][0]
        scope = accounting.topic_scope(self.output, topic['id'], lane='pe-loop')
        host = u.Runtime.__new__(u.Runtime)
        host.directory, host.batch = self.root / 'worker', batch
        host.service = SimpleNamespace(model_factory=lambda role: SimpleNamespace())
        refused = pe_loop.PromptLengthRefused({'token_count': 533, 'token_limit': 512})
        with patch.object(host, '_render', side_effect=refused) as render, \
             patch.object(pe_loop, 'compact_prompt', side_effect=['Shorter first.', 'Shorter second.']) as compact:
            with self.assertRaises(pe_loop.PromptLengthRefused):
                host.render(topic, 'pe-loop', 'Original prompt.', 43, 1, scope)
            self.assertEqual(compact.call_count, 2)
            self.assertEqual([c.kwargs['revision'] for c in render.call_args_list], [0, 1, 2])
            self.assertEqual([c.args[2] for c in render.call_args_list], ['Original prompt.', 'Shorter first.', 'Shorter second.'])
            render.reset_mock(); compact.reset_mock()
            with self.assertRaises(pe_loop.PromptLengthRefused):
                host.render(topic, 'direct', 'Original prompt.', 43, 1, scope)
            self.assertEqual(render.call_count, 1)
            compact.assert_not_called()

    def test_only_definite_unsubmitted_length_refusal_can_be_compacted(self):
        batch, _ = self.setup_loop(n=2)
        topic = batch['topics'][0]
        scope = accounting.topic_scope(self.output, topic['id'], lane='pe-loop')
        host = u.Runtime.__new__(u.Runtime)
        host.directory, host.batch = self.output / 'workers/0', batch
        from experiments.render_profiles import renderer_spec
        body = {'id': topic['id'] + '__pe-loop__0', 'kind': 'generate', 'mode': 'live',
                'accounting_scope': scope, 'payload': {'input_id': 'source', 'input': topic['source_info'],
                'prompt': 'Original prompt.', 'renderer': renderer_spec(topic, batch, 42)}}
        request = {**body, 'sha256': u.signature(body)}
        folder = host.directory / 'baselines' / topic['id'] / 'pe-loop/0'
        save(folder / 'request.json', request)
        response = {'request_sha256': request['sha256'], 'status': 'failed', 'mode': 'live',
                    'error': 'ValueError: Prompt exceeds tokenizer limit; automatic truncation is disabled'}
        save(folder / 'response.json', response)
        before = (folder / 'response.json').read_bytes()
        with self.assertRaises(pe_loop.PromptLengthRefused):
            host._render(topic, 'pe-loop', 'Original prompt.', 42, 0, scope)
        self.assertEqual((folder / 'response.json').read_bytes(), before)
        save(folder / 'render-started.json', {'request_sha256': request['sha256']})
        with self.assertRaisesRegex(RuntimeError, 'Baseline render failed'):
            host._render(topic, 'pe-loop', 'Original prompt.', 42, 0, scope)
        save(folder / 'response.json', {**response, 'task_deadline': True, 'error': 'TaskDeadline: original deadline'})
        with self.assertRaises(ResourceExhausted):
            host._render(topic, 'pe-loop', 'Original prompt.', 42, 0, scope)
        save(folder / 'response.json', {**response, 'outcome_unknown': True})
        with self.assertRaises(accounting.ExternalExecutionUnknown):
            host._render(topic, 'pe-loop', 'Original prompt.', 42, 0, scope)

    def test_effective_prompt_reaches_critic_history_and_length_stop_retains_choice(self):
        batch, runtime = self.setup_loop(n=3)
        original = runtime.render
        def render(topic, method, prompt, seed, number, scope):
            if number == 2:
                raise pe_loop.PromptLengthRefused({'token_count': 520, 'token_limit': 512})
            return {**original(topic, method, prompt, seed, number, scope),
                    'prompt': 'The actual compact blue scene.', 'prompt_revisions': 1}
        runtime.render = render
        result = self.run_loop(batch, runtime)
        self.assertTrue(result['partial'])
        self.assertEqual(result['delivery_kind'], 'prompt_limit_delivery')
        self.assertEqual(runtime.last_history[0]['prompt'], 'The actual compact blue scene.')
        self.assertTrue(all(c[3] == 'The actual compact blue scene.' for c in runtime.calls if c[0] == 'review'))
        row = results.find(self.registry, '001', 'short', 'pe-loop', 42)
        self.assertEqual(row['evidence']['actual_generations'], 2)
        self.assertEqual(row['candidates'][0]['roles'], ['first', 'selected'])
        directory = self.output / 'methods' / batch['topics'][0]['id'] / 'pe-loop'
        self.assertEqual(load(directory / 'rounds/0001/prompt.json')['value'], 'A blue painted scene. Round 1')
        self.assertTrue((directory / 'prompt-limit-stop.json').exists())


if __name__ == '__main__':
    unittest.main()
