"""Resume the same Planner/Critic decision after relay 502; scripted, no GPU/API."""
from pathlib import Path
import json
import sqlite3
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import recover_interrupted_model as recovery
import test_planner_harness as fixtures
from test_loop_engineering import APIPlanner, Renderer
from test_review_modes import Reviewer, action
from planner_harness import accounting as a
from planner_harness.common import load, save, sha
from planner_harness.delivery import verify_delivery
from server_runtime.service import Service
from server_runtime.queue import Queue
from server_runtime.engine import Engine
from vlm.responses_stream import StreamAudit


def interrupted(model):
    metadata = {'request_id': 'a' * 32, 'http_status': 502,
                'outcome': 'execution_unknown', 'relay_error': {'code': 'relay_execution_unknown',
                'stage': 'upstream_connect', 'upstream_error': {'type': 'URLError',
                'message': 'SSL UNEXPECTED_EOF_WHILE_READING'}}}
    audit = StreamAudit(model.lha_audit_directory, metadata)
    audit.received(json.dumps({'error': metadata['relay_error']}).encode())
    audit.close(stage='connect')
    model.last_client_audit = metadata
    raise a.ExternalExecutionUnknown('Scripted relay 502')


class Planner(APIPlanner):
    def predict_text(self, **kwargs):
        if self.actions[0] == 'interrupt':
            self.actions.pop(0)
            self.inputs.append(kwargs)
            interrupted(self)
        return super().predict_text(**kwargs)


class Critic(Reviewer):
    def predict_text(self, **kwargs):
        if self.actions[0] == 'interrupt':
            self.actions.pop(0)
            self.inputs.append(kwargs)
            interrupted(self)
        return super().predict_text(**kwargs)


class RecoveryTests(unittest.TestCase):
    setUp, tearDown = fixtures.Tests.setUp, fixtures.Tests.tearDown

    def setup_run(self, role):
        output = self.root / 'batch'
        worker = output / 'workers/0'
        policy = a.default_online_policy(max_generations=4, wall_seconds=9000)
        ar = a.install(output / 'accounting', policy)
        planner = Planner([action('generate', input_video='source', prompt='Make blue.'),
                           *([action('generate', input_video='v1', prompt='Soften the blue.'),
                              'interrupt'] if role == 'planner' else []),
                           action('finish', video='v2' if role == 'planner' else 'v1',
                                  message='The reviewed candidate is ready.')])
        critic = Critic([action('note', text='Inspect the existing output.'),
                         action('observe', video='v1', count=2),
                         action('note', text='The detail view is recorded.'),
                         'interrupt', *Reviewer().actions] if role == 'critic'
                        else Reviewer().actions + Reviewer().actions)
        renderer = Renderer(self.source)
        queue = Queue(worker / 'queue.sqlite3')
        config = {'workflow': 'creative_loop_v1', 'review': {'mode': 'critic'},
                  'planner': {'model': planner.model, 'reasoning_effort': planner.reasoning_effort},
                  'critic': {'model': critic.model, 'reasoning_effort': critic.reasoning_effort},
                  'accounting_root': str(ar), 'budget': policy}
        service = Service(queue, worker, ROOT, config,
                          model_factory=lambda role: planner if role == 'planner' else critic, renderer=renderer)
        service.submit({'id': '001__short__full', 'source': str(self.source), 'source_sha256': sha(self.source),
                        'request': 'Make the scene blue.', 'max_generations': 4, 'budget_topic': '001__short',
                        'budget_lane': 'full', 'execution': {'mode': 'live',
                        'resource_policy': {'max_wall_seconds': 9000},
                        'renderer': {'backend': 'bernini', 'seed': 42, 'generation': {}}}})
        # Materialize an old release's unresolved state for migration coverage.
        # Current text calls recover automatically; the operator CLI must still
        # understand the historical records produced before that change.
        from planner_harness import model_call
        current_call=model_call.call_text
        def historical_call(*args,**kwargs):
            kwargs.update(attempts=1,retry_delay=0)
            try:return current_call(*args,**kwargs)
            except model_call.ModelTransportError:
                if list(Path(args[0]).glob('attempts/*/unknown.json')):
                    raise a.ExternalExecutionUnknown('Historical unresolved model call')
                raise
        with patch.object(model_call,'call_text',historical_call):
            Engine(queue, worker, service, service.expand, interval=.005).run(once=True)
        run = worker / 'tasks/001__short__full/run'
        self.assertTrue((run / 'state.json').exists(), queue.summary())
        state = load(run / 'state.json')
        self.assertEqual(state['status'], 'needs_reconciliation')
        call = recovery._call(run, state)[0]
        digest = sha(call / 'attempts/01/client-audit/summary.json')
        save(output / 'topics/001__short/full.json', {'outcome': 'execution_unknown'})
        save(output / 'methods/001__short/full/settlement.json', {'status': 'execution_unknown'})
        with sqlite3.connect(output / 'device-queue.sqlite3') as db:
            db.execute('CREATE TABLE tasks(id TEXT, status TEXT, owner TEXT)')
            db.execute('INSERT INTO tasks VALUES (?,?,?)', ('001__short__training_full', 'recovery_required', None))
        return output, worker, run, call, digest, service, queue, renderer, planner, critic

    def check_resume(self, role):
        output, worker, run, call, digest, service, queue, renderer, planner, critic = self.setup_run(role)
        before = load(run / 'state.json')
        ledger_before = sha(output / 'accounting/ledger.json')
        input_before = sha(call / 'input.json')
        request_bytes = {str(p): p.read_bytes() for p in (run / 'jobs').glob('*/request.json')}
        renders = list(renderer.calls)
        models = len(planner.inputs) + len(critic.inputs)
        preview = recovery.recover(run, digest, 'Resume the original interrupted text request')
        self.assertEqual(preview['submission'], 'possibly_submitted')
        self.assertEqual(load(run / 'state.json'), before)
        result = recovery.recover(run, digest, 'Resume the original interrupted text request',
                                  execute=True, abandon_response=True)
        self.assertEqual(result['status'], 'prepared_not_executed')
        self.assertEqual(len(planner.inputs) + len(critic.inputs), models)
        self.assertEqual(sha(output / 'accounting/ledger.json'), ledger_before)
        self.assertEqual(sha(call / 'input.json'), input_before)
        self.assertEqual(load(run / 'state.json')['online_clock'], before['online_clock'])
        self.assertEqual(load(run / 'state.json')['videos'], before['videos'])
        self.assertEqual(load(call / 'allowance.json'), {'first': 2, 'last': 2})
        self.assertEqual(recovery.recover(run, digest, 'Same recovery', execute=True, abandon_response=True), result)
        self.assertFalse((output / 'topics/001__short/full.json').exists())
        self.assertTrue((Path(result['history']) / 'original-operation.json').exists())
        Engine(queue, worker, service, service.expand, interval=.005).run(once=True)
        self.assertEqual(verify_delivery(run)['selected'], 'v2' if role == 'planner' else 'v1')
        self.assertEqual(renderer.calls, renders)
        self.assertEqual(request_bytes, {str(p): p.read_bytes() for p in (run / 'jobs').glob('*/request.json')})
        self.assertEqual(load(run / 'state.json')['online_clock'], before['online_clock'])
        self.assertEqual(load(call / 'returned.json')['attempt'], 2)
        old = a.operation(load(run / 'budget-scope.json'), str(call / 'attempts/01'))
        self.assertEqual(old, load(Path(result['history']) / 'original-operation.json'))

    def test_planner_resumes_same_event_and_keeps_video(self):
        self.check_resume('planner')

    def test_critic_resumes_same_review_without_rendering_again(self):
        self.check_resume('critic')

    def test_expired_task_and_changed_evidence_are_unchanged(self):
        output, worker, run, call, digest, *_ = self.setup_run('planner')
        before = sha(run / 'state.json')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            recovery.recover(run, '0' * 64, 'Inspect')
        self.assertEqual(sha(run / 'state.json'), before)
        state = load(run / 'state.json')
        state['online_clock']['deadline_unix'] = time.time() - 1
        save(run / 'state.json', state)
        before = sha(run / 'state.json')
        with self.assertRaisesRegex(ValueError, 'expired'):
            recovery.recover(run, digest, 'Inspect', execute=True, abandon_response=True)
        self.assertEqual(sha(run / 'state.json'), before)
        self.assertTrue((call / 'attempts/01/unknown.json').exists())

    def test_interrupted_preparation_replays_one_journal(self):
        output, worker, run, call, digest, service, queue, renderer, *_ = self.setup_run('planner')
        original = recovery.save
        def fail_state(path, value):
            if Path(path) == run / 'state.json':
                raise OSError('Scripted interruption after backups')
            return original(path, value)
        with patch.object(recovery, 'save', side_effect=fail_state):
            with self.assertRaises(OSError):
                recovery.recover(run, digest, 'Resume relay call', execute=True, abandon_response=True)
        result = recovery.recover(run, digest, 'Resume relay call', execute=True, abandon_response=True)
        self.assertEqual(result['next_attempt'], 2)
        count = len(renderer.calls)
        Engine(queue, worker, service, service.expand, interval=.005).run(once=True)
        self.assertEqual(verify_delivery(run)['selected'], 'v2')
        self.assertEqual(len(renderer.calls), count)


if __name__ == '__main__':
    unittest.main()
