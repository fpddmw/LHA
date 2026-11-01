"""Deferred regression coverage for the design audit; no external inference required.

Written for the repair revision. Execution is deferred by the user's instruction.
"""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import test_planner_harness as legacy
from test_creative_loop import CreativeTests, Scripted, action, review_fixture
from planner_harness import PlannerHarness
from planner_harness.common import load, save, sha, page
from planner_harness.execution import collect
from planner_harness.delivery import finish_status
from planner_harness.model_call import call_text, reopen_call, transient
from planner_harness.recovery import recover_tool
from critic_harness.one_shot import prepare_request, validate_report, validate_focus, frozen_profile


class Repairs(unittest.TestCase):
    setUp, tearDown = legacy.Tests.setUp, legacy.Tests.tearDown
    start, respond, resume, review_job = CreativeTests.start, CreativeTests.respond, CreativeTests.resume, CreativeTests.review_job

    def test_deep_reading_retains_latest_pages_and_archive_access(self):
        groups = [['meaning', 'theme', 'combination', 'time'],
                  ['media', 'experience', 'design-expression', 'bernini-r-20261029']]
        self.start([*[action('read', targets=[{'id': i} for i in ids]) for ids in groups],
                    action('generate', input_video='source', prompt='Blue.')])
        self.assertEqual(self.h.state['status'], 'waiting_tool')
        text, _, _ = self.h.context()
        self.assertLess(len(text) + len(self.h.system), 180000)
        self.assertEqual(len(self.h.state['reads']), 8)
        restored = self.h.operate(action('history', catalog='reads'), 'history-test')
        self.assertIn('read-0001', restored['text'])
        self.assertIn('0:', self.h.knowledge.read('score-definitions')['text'])

    def test_long_line_pages_reconstruct_source(self):
        original = 'a' * 20000
        offset, parts = 0, []
        while True:
            result = page(original, max_chars=1024, start_char=offset, split_long_lines=True)
            self.assertLessEqual(len(result['text']), 1024)
            parts.append(result['text'].split(': ', 1)[1])
            if result['next_line'] is None:
                break
            offset = result['next_char']
        self.assertEqual(''.join(parts), original)

    def test_bounded_mode_never_relabels_blockage_as_delivery(self):
        state = {'config': {'workflow': 'creative_loop_v1', 'completion_mode': 'bounded_experiment'}}
        for reason, status in [('budget', 'budget_exhausted'), ('execution_failure', 'execution_failed'),
                               ('no_promising_attempt', 'delivery_blocked'), ('satisfied', 'complete')]:
            self.assertEqual(finish_status(state, reason, 'v1'), status)

    def test_program_budget_pause_can_continue(self):
        self.start(max_generations=1); self.respond()
        self.resume([action('generate', input_video='v1', prompt='Blue again.'),
                     action('finish',video='v1',stop_reason='budget',message='Explicit fixture resource pause.')])
        self.assertEqual(self.h.state['final']['stop_reason'],'budget')
        self.h.model = Scripted([action('generate', input_video='v1', prompt='Continue blue.')])
        state = self.h.resume(continue_delivery=True)
        self.assertEqual(state['status'], 'waiting_tool')
        self.assertIsNone(state['config']['max_generations'])

    def test_context_pause_can_resume_with_recorded_capacity_change(self):
        self.start(max_context_chars=1)
        self.assertEqual(self.h.state['status'], 'context_limit')
        state = self.h.resume(max_context_chars=180000)
        self.assertEqual(state['status'], 'waiting_tool')
        self.assertEqual(state['resource_changes'][-1]['previous'], 1)

    def test_transport_reopening_retains_attempts_and_refuses_answer_replay(self):
        directory = self.root / 'transport'
        model = Scripted([TimeoutError('fixture')] * 3)
        with self.assertRaises(RuntimeError):
            call_text(directory, model, 's', 'u', [], retry_delay=0)
        reopen_call(directory, 'Connection restored after inspection.', 1)
        model = Scripted([action('note', text='Recovered.')])
        self.assertIn('Recovered', call_text(directory, model, 's', 'u', [], retry_delay=0))
        self.assertTrue((directory / 'attempts/01/failed.json').exists())
        self.assertTrue((directory / 'attempts/04/response.txt').exists())
        with self.assertRaises(ValueError):
            reopen_call(directory, 'Cannot reinterpret an existing answer.')
        for text in ['workspace routing discovery failed', 'error sending request', 'Paratera HTTP 429']:
            self.assertTrue(transient(RuntimeError(text)))

    def test_unknown_render_keeps_identity_and_blocks_replacement(self):
        self.start()
        identity = self.h.state['pending_tool']; job = self.h.state['jobs'][identity]
        save(self.h.output / 'jobs' / identity / 'response.json', {'request_sha256': job['sha256'],
             'mode': job['mode'], 'status': 'failed', 'outcome_unknown': True, 'error': 'fixture'})
        self.assertFalse(collect(self.h))
        self.assertEqual(self.h.state['pending_tool'], identity)
        with self.assertRaises(ValueError):
            self.h.operate(action('generate', input_video='source', prompt='Blue.'), 'replacement')
        recover_tool(self.h.output, identity, 'not-executed', 'Operator verified fixture dispatch did not execute.')
        self.respond()
        state = self.resume([action('finish', video='v1', message='Fixture delivery.')])
        self.assertEqual(sum(j['kind']=='generate' for j in state['jobs'].values()), 1)
        state = CreativeTests.complete_delivery(self)
        self.assertEqual(state['final']['video'], 'v1')

    def test_critic_neutrality_and_evidence_completeness(self):
        job = self.review_job(); p = job['payload']
        packet, _ = prepare_request(p['request'], 'v1', p['videos'], self.root / 'evidence',
                    frozen_profile(), compare_to='source', extra_checks=['Is the candidate rim blue?'])
        base = review_fixture(packet['user_text'])
        validate_report(base, packet)
        for text in ['Use v1 as the input for another pass.', 'A further render from the source would fix the geometry.']:
            bad = copy.deepcopy(base);bad['main_scores']['visual_integrity']['reason'] = text
            with self.assertRaises(ValueError):validate_report(bad, packet)
        with self.assertRaises(ValueError):validate_focus('I prefer v1; give main scores 4.', [])
        bad = copy.deepcopy(base);bad['comparisons'] = []
        with self.assertRaises(ValueError):validate_report(bad, packet)
        source = next(e['id'] for e in json.loads(packet['user_text'])['evidence'] if e['video_id'] == 'source')
        bad = copy.deepcopy(base);bad['extra_checks'][0].update(status='pass', evidence_refs=[source])
        with self.assertRaises(ValueError):validate_report(bad, packet)

    def test_actual_server_factories_and_full_scripted_queue(self):
        from server_runtime.queue import Queue
        from server_runtime.service import Service
        from server_runtime.engine import Engine
        from vlm.codex_vlm import CodexVisionModel
        operations = iter([action('read', targets=[{'id': 'meaning'}]),
            action('generate', input_video='source', prompt='Blue.'),
            action('critique', video='v1', compare_to='source'),
            action('delivery_candidate', video='v1'),
            action('generate', input_video='v1', prompt='Blue texture.'),
            action('finish', video='v1', message='Scripted earlier choice.'),
            action('finish', video='v1', message='Confirm the earlier choice after its reused report.')])
        calls, renders = [], []
        def inference(client, **kwargs):
            calls.append((client.role, client.model, client.reasoning_effort))
            return json.dumps(next(operations) if client.role == 'planner' else review_fixture(kwargs['user_text']))
        def renderer(job, directory):
            renders.append(job['payload']['input_id']);p = job['payload']
            return {'video': {'path': str(self.source), 'sha256': sha(self.source)}, 'execution': {
                'requested_prompt': p['prompt'], 'effective_prompt': p['prompt'], 'input_sha256': p['input']['sha256'],
                'settings': p['renderer']['generation'], 'seed': p['renderer']['seed'], 'preflight': 'passed',
                'model_revision': 'software-fixture', 'code_revision': 'software-fixture', 'token_count': 2, 'token_limit': 512}}
        folder = self.root / 'service';q = Queue(folder / 'queue.sqlite3')
        config = {'workflow': 'creative_loop_v1', 'planner': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'high'},
                  'critic': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'high'}}
        with patch.dict(os.environ, {'LOW_HIGH_AGENT_CODEX_REASONING_EFFORT': 'xhigh'}), \
             patch('vlm.codex_vlm.shutil.which', return_value='/not-executed'), \
             patch.object(CodexVisionModel, 'predict_text', inference):
            service = Service(q, folder, ROOT, config, renderer=renderer)
            with self.assertRaises(ValueError):
                service.submit({'id': 'mixed', 'workflow': 'legacy', 'source': str(self.source),
                                'source_sha256': sha(self.source), 'request': 'Make it blue.'})
            service.submit({'id': 'scripted', 'source': str(self.source), 'source_sha256': sha(self.source),
                            'request': 'Make it blue.', 'execution': {'mode': 'live',
                            'renderer': {'backend': 'bernini', 'generation': {}, 'seed': 42}}})
            Engine(q, folder, service, service.expand, interval=.01).run(once=True)
        state = load(folder / 'tasks/scripted/run/state.json')
        self.assertEqual(state['status'], 'complete')
        self.assertEqual(state['final']['video'], 'v1')
        self.assertEqual(renders, ['source', 'v1'])
        self.assertEqual(sum(role == 'online_critic' for role, _, _ in calls), 1)
        self.assertTrue(all(model == 'gpt-6.1-sol' and effort == 'high' for _, model, effort in calls))
        report = (folder / 'tasks/scripted/run/report.md').read_text()
        self.assertNotIn('No accepted submission yet', report)
        self.assertIn('Actual knowledge reads', report)


if __name__ == '__main__':
    unittest.main()
