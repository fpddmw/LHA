"""Stream assembly, empty-answer stopping and zero-API original-call recovery."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from vlm.responses_stream import ResponseOutput, events, replay_answer
from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel
from planner_harness.common import load, save, sha
from planner_harness.resumption import planner_ready
from planner_harness.subscription_recovery import recover_answer
from planner_harness.delivery import verify_delivery
from server_runtime.service import Service
from server_runtime.queue import Queue
from server_runtime.engine import Engine
from test_loop_engineering import APIPlanner, Renderer
from test_review_modes import Reviewer, action
import test_planner_harness as fixture


def message(identity, phase, text=''):
    return {'id': identity, 'type': 'message', 'role': 'assistant', 'phase': phase,
            'content': [{'type': 'output_text', 'text': text}]}


def body(text, commentary=''):
    sequence = []
    if commentary:
        sequence.append({'type': 'response.output_item.done', 'output_index': 0,
                         'item': message('comment', 'commentary', commentary)})
    sequence += [
        {'type': 'response.output_item.added', 'output_index': 1, 'item': message('final', 'final_answer')},
        {'type': 'response.output_text.delta', 'output_index': 1, 'content_index': 0, 'item_id': 'final', 'delta': text[:4]},
        {'type': 'response.output_text.delta', 'output_index': 1, 'content_index': 0, 'item_id': 'final', 'delta': text[4:]},
        {'type': 'response.output_text.done', 'output_index': 1, 'content_index': 0, 'item_id': 'final', 'text': ''},
        {'type': 'response.output_item.done', 'output_index': 1, 'item': message('final', 'final_answer')},
        {'type': 'response.completed', 'response': {'id': 'response-fixture', 'status': 'completed',
            'model': 'gpt-6.1-sol', 'output': [], 'usage': {'total_tokens': 12}}},
    ]
    return b''.join(b'data: ' + json.dumps(e).encode() + b'\n\n' for e in sequence)


class AssemblyTests(unittest.TestCase):
    def test_empty_tail_preserves_final_delta_and_does_not_join_commentary(self):
        raw = body('{"ok":true}', '{"action":"generate","prompt":"Unselected commentary"}')
        output = ResponseOutput()
        for event in events(io.BytesIO(raw)):
            output.feed(event)
        answer, receipt = output.answer(event['response'])
        self.assertEqual(answer, '{"ok":true}')
        self.assertEqual(receipt['selected_message_id'], 'final')

    def test_empty_final_stays_empty_despite_nonempty_commentary(self):
        raw = body('', '{"action":"generate"}')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'stream.bin'
            path.write_bytes(raw)
            self.assertEqual(replay_answer(path)['text'], '')

    def test_completed_item_text_is_not_duplicated(self):
        output = ResponseOutput()
        for event in events(io.BytesIO(body('{"ok":true}'))):
            output.feed(event)
        response = {'output': [message('final', 'final_answer', '{"ok":true}')]}
        self.assertEqual(output.answer(response)[0], '{"ok":true}')

    def test_new_empty_final_does_not_inherit_text_from_another_message_id(self):
        output = ResponseOutput()
        output.feed({'type': 'response.output_item.done', 'output_index': 0,
                     'item': message('comment', 'commentary', '{"action":"generate"}')})
        self.assertEqual(output.answer({'output': [message('another-final', 'final_answer')]})[0], '')

    def test_live_client_uses_the_same_assembled_final(self):
        model = ChatGPTSubscriptionVisionModel(relay_url='http://127.0.0.1:18767')
        response = io.BytesIO(body('{"action":"observe"}'))
        response.status = 200
        response.headers = {'Content-Type': 'text/event-stream'}
        with patch.object(model, '_open', return_value=response):
            answer = model.predict_text(system_prompt='s', user_text='u', image_paths=[])
        self.assertEqual(answer, '{"action":"observe"}')
        self.assertEqual(model.last_provider_response['output'], [])
        self.assertEqual(model.last_usage['total_tokens'], 12)


class OriginalCallTests(unittest.TestCase):
    setUp, tearDown = fixture.Tests.setUp, fixture.Tests.tearDown

    def stopped(self):
        generate = json.dumps(action('generate', input_video='source', prompt='Make the visible scene blue.'))
        class EmptyStoredPlanner(APIPlanner):
            def predict_text(inner, **kwargs):
                if inner.inputs:
                    return super().predict_text(**kwargs)
                inner.inputs.append(kwargs)
                stream = Path(inner.lha_audit_directory) / 'stream.bin'
                stream.parent.mkdir(parents=True, exist_ok=True)
                stream.write_bytes(body(generate))
                inner.last_usage = {'total_tokens': 12}
                inner.last_client_audit = {'request_id': 'request-fixture', 'response_id': 'response-fixture',
                                           'stream_sha256': sha(stream), 'selection': 'no_answer'}
                return ''
        planner = EmptyStoredPlanner([action('finish', video='v1', message='The reviewed result is ready.')])
        reviewer = Reviewer()
        renderer = Renderer(self.source)
        worker = self.root / 'service'
        queue = Queue(worker / 'queue.sqlite3')
        config = {'workflow': 'creative_loop_v1', 'review': {'mode': 'critic'},
                  'planner': {'model': planner.model, 'reasoning_effort': planner.reasoning_effort},
                  'critic': {'model': reviewer.model, 'reasoning_effort': reviewer.reasoning_effort}}
        service = Service(queue, worker, ROOT, config,
                          model_factory=lambda role: planner if role == 'planner' else reviewer, renderer=renderer)
        service.submit({'id': 'topic', 'source': str(self.source), 'source_sha256': sha(self.source),
                        'request': 'Make the scene blue.', 'max_generations': 1,
                        'execution': {'mode': 'live', 'renderer': {'backend': 'bernini', 'seed': 42, 'generation': {}}}})
        Engine(queue, worker, service, service.expand, interval=.001).run(once=True)
        run = worker / 'tasks/topic/run'
        return service, queue, planner, renderer, run

    def test_empty_answer_stops_same_event_across_restarts(self):
        service, queue, planner, renderer, run = self.stopped()
        state = load(run / 'state.json')
        self.assertEqual(state['status'], 'needs_reconciliation')
        self.assertEqual(state['pending_event'], 'event-0001')
        self.assertEqual(state['events'], [])
        self.assertFalse(planner_ready(run))
        for _ in range(2):
            Engine(queue, service.directory, service, service.expand, interval=.001).run(once=True)
        self.assertEqual(len(planner.inputs), 1)
        self.assertEqual(len(renderer.calls), 0)
        self.assertEqual(load(run / 'state.json')['attempts'], 1)

    def test_replay_restores_original_call_without_ledger_clock_or_api_change(self):
        service, queue, planner, renderer, run = self.stopped()
        call = run / 'calls/event-0001'
        stream = call / 'transport/attempts/01/client-audit/stream.bin'
        before = copy.deepcopy(load(run / 'state.json'))
        ledger = Path(load(run / 'budget-scope.json')['root']) / 'ledger.json'
        ledger_hash = sha(ledger)
        request_hash = sha(call / 'transport/input.json')
        plan = recover_answer(run, 'event-0001', stream)
        self.assertEqual(plan['status'], 'recoverable')
        result = recover_answer(run, 'event-0001', stream, execute=True)
        self.assertEqual((result['model_calls'], result['renders']), (0, 0))
        self.assertEqual(result['answer_sha256'], sha(call / 'response.txt'))
        self.assertEqual(sha(ledger), ledger_hash)
        self.assertEqual(sha(call / 'transport/input.json'), request_hash)
        after = load(run / 'state.json')
        self.assertEqual(after['online_clock'], before['online_clock'])
        self.assertEqual(after['attempts'], before['attempts'])
        self.assertEqual(len(planner.inputs), 1)
        archived = Path(result['history']) / 'original/calls/event-0001/response.txt'
        self.assertEqual(archived.read_bytes(), b'')
        self.assertTrue(planner_ready(run))
        self.assertEqual(recover_answer(run, 'event-0001', stream, execute=True), result)
        Engine(queue, service.directory, service, service.expand, interval=.001).run(once=True)
        self.assertEqual(verify_delivery(run)['selected'], 'v1')
        self.assertEqual(len(renderer.calls), 1)
        self.assertEqual(len(planner.inputs), 2)

    def test_supervisor_settlement_and_old_error_events_are_archived_without_budget_reset(self):
        service, queue, planner, renderer, run = self.stopped()
        state = load(run / 'state.json')
        state.update(status='budget_exhausted', pending_event=None, attempts=2,
                     final={'outcome': 'incomplete', 'stop_reason': 'execution_failure'})
        state['events'] = [{'event_id': f'event-{i:04d}', 'status': 'response_error'} for i in (1, 2)]
        save(run / 'state.json', state)
        save(run / 'final.json', state['final'])
        save(run / 'events/event-0001.json', state['events'][0])
        save(self.root / 'batch.json', {'fixture': True})
        scope = load(run / 'budget-scope.json')
        settlement = self.root / 'methods' / scope['topic'] / scope['lane'] / 'settlement.json'
        save(settlement, {'status': 'budget_exhausted'})
        stop = Path(scope['root']) / 'stop-submissions.json'
        save(stop, {'reason': 'Supervised admission pause'})
        before = sha(stop)
        stream = run / 'calls/event-0001/transport/attempts/01/client-audit/stream.bin'
        result = recover_answer(run, 'event-0001', stream, execute=True)
        after = load(run / 'state.json')
        self.assertEqual(after['attempts'], 2)
        self.assertEqual(after['online_clock'], state['online_clock'])
        self.assertEqual(after['events'], [state['events'][1]])
        self.assertEqual(after['pending_event'], 'event-0001')
        self.assertEqual(sha(stop), before)
        self.assertFalse(settlement.exists())
        self.assertTrue((Path(result['history']) / 'original/batch/methods' / scope['topic'] / scope['lane'] / 'settlement.json').exists())
        self.assertEqual((len(planner.inputs), len(renderer.calls)), (1, 0))

    def test_unrelated_stream_is_not_published(self):
        _, _, planner, renderer, run = self.stopped()
        stream = self.root / 'unrelated.bin'
        stream.write_bytes(body('{"action":"generate"}').replace(b'response-fixture', b'another-response'))
        before = sha(run / 'state.json')
        with self.assertRaisesRegex(ValueError, 'different model response'):
            recover_answer(run, 'event-0001', stream, execute=True)
        self.assertEqual(sha(run / 'state.json'), before)
        self.assertEqual((len(planner.inputs), len(renderer.calls)), (1, 0))


if __name__ == '__main__': unittest.main()
