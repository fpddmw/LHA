"""Offline checks for context projection, compatible tools and usage accounting."""
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
from planner_harness import tool_interface, working_memory
from planner_harness.candidate_view import select
from planner_harness.common import load, save
from planner_harness.context import observation_view
from planner_harness.json_output import decode_object
from planner_harness.maintenance import model_view
from planner_harness.model_call import call_text
from planner_harness.usage_report import summarize
from vlm.litellm_vlm import LiteLLMVisionModel
import test_creative_loop as creative_tests
from test_unified_results import Fixture


class InterfaceTests(unittest.TestCase):
    def test_equivalent_arguments_and_conflicts(self):
        original = {'tool': 'generate', 'arguments': {'input_id': 'v2', 'prompt': 'Blue.',
                    'review_focus': {'focus': ['face', 'hands'], 'extra_checks': 'One person?'}},
                    'note': 'Keep this hypothesis.', 'workspace': {'summary': 'My direction'}}
        before = copy.deepcopy(original)
        normalized = tool_interface.normalize(original)
        self.assertEqual(original, before)
        self.assertEqual(normalized['arguments']['input_video'], 'v2')
        self.assertEqual(normalized['arguments']['review_focus'], {'focus': 'face\nhands', 'extra_checks': ['One person?']})
        self.assertEqual(normalized['note'], original['note'])
        self.assertEqual(normalized['workspace'], original['workspace'])
        for args in ('style-map', ['style-map', 'experience-map'], {'id': 'style-map'}):
            self.assertIsInstance(tool_interface.normalize({'action': 'read', 'arguments': args})['arguments']['targets'], list)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            tool_interface.normalize({'action': 'generate', 'arguments': {'input_id': 'v1', 'input_video': 'source'}})
        with self.assertRaisesRegex(ValueError, 'missing input_video'):
            tool_interface.normalize({'action': 'generate', 'arguments': {'prompt': 'Blue.'}})

    def test_candidate_batch_contains_actual_prompt_parent_review(self):
        state = {'videos': {'v1': {'parent': 'source', 'prompt': 'Blue.'}, 'v2': {'parent': 'v1', 'prompt': 'Warm blue.'}},
                 'reviews': {'v1': {'mode': 'critic', 'status': 'complete', 'report': {'summary': 'Unknown motion.'}}}}
        before = copy.deepcopy(state)
        rows = select(state, {'ids': ['v1', 'v2'], 'compare_prompts': True})
        self.assertEqual(rows['candidates'][0]['review']['report']['summary'], 'Unknown motion.')
        self.assertEqual(rows['candidates'][1]['parent'], 'v1')
        self.assertIn('+Warm blue.', rows['prompt_diff'])
        self.assertEqual(select(state, {'id': 'v1', 'raw': True}), state['videos']['v1'])
        self.assertIn('error', select(state, {'ids': ['v1', 'missing']})['candidates'][1])
        self.assertEqual(state, before)

    def test_one_surrounded_operation_is_accepted_only_when_enabled(self):
        raw = 'I will inspect it.\n```json\n{"action":"observe","arguments":{"video":"v1"}}\n```'
        self.assertEqual(decode_object(raw, allow_prose=True)['action'], 'observe')
        with self.assertRaises(ValueError):
            decode_object(raw)
        for raw in ('{} {}', 'Here {broken: {"action":"finish"}}'):
            with self.assertRaises(ValueError):
                decode_object(raw, allow_prose=True)


class ProjectionTests(unittest.TestCase):
    def test_full_current_read_archived_old_page_and_unmodified_state(self):
        state = {'events': [{'event_id': 'now'}]}
        def material(identity, text):
            return {'id': identity, 'sha256': identity, 'read_id': 'r-' + identity, 'text': text,
                    'title': identity, 'summary': 'Approved conditional summary.', 'start_line': 1, 'end_line': 9}
        working_memory.retain(state, [material('old', 'x' * 28000)], 'old-event')
        working_memory.retain(state, [material('new', '1: Current condition and conclusion.\n')], 'now')
        before = copy.deepcopy(state)
        payload = {'recent_operations': [{'event_id': 'now', 'result': {'materials': [material('new', '1: Current condition and conclusion.\n')]}}]}
        working_memory.visible(payload, state)
        memory = payload['working_memory']
        self.assertEqual(memory['retained_reads'][0]['material']['text'], '1: Current condition and conclusion.\n')
        self.assertEqual(memory['archived_reads'][0]['summary'], 'Approved conditional summary.')
        self.assertEqual(memory['archived_reads'][0]['open']['arguments']['id'], 'old')
        self.assertNotIn('text', payload['recent_operations'][0]['result']['materials'][0])
        self.assertEqual(state, before)

    def test_overlapping_complete_lines_are_present_once(self):
        state = {'events': [{'event_id': 'new'}]}
        for event, text in [('old', '1: A\n2: B\n'), ('new', '2: B\n3: C\n')]:
            working_memory.retain(state, [{'id': 'x', 'sha256': 'hash', 'read_id': event, 'text': text,
                                          'start_line': 1 if event == 'old' else 2, 'end_line': 2 if event == 'old' else 3}], event)
        payload = {}
        working_memory.visible(payload, state)
        text = ''.join(r['material']['text'] for r in payload['working_memory']['retained_reads'])
        self.assertEqual(text.count('2: B'), 1)
        self.assertIn('1: A', text)
        self.assertIn('3: C', text)

    def test_observation_projection_keeps_coverage_and_coordinates(self):
        raw = {'observation_id': 'o', 'video_id': 'v1', 'coverage': {'fraction': .5}, 'next_arguments': {'page': 2},
               'frames': [{'path': 'disk.png', 'sha256': 'hash', 'frame_index': 5, 'timestamp_seconds': .2, 'crop': [0,0,1,1]}]}
        shown = observation_view(raw)
        self.assertEqual(shown['coverage'], raw['coverage'])
        self.assertEqual(shown['frames'][0]['frame_index'], 5)
        self.assertEqual(shown['next_arguments'], raw['next_arguments'])
        self.assertNotIn('path', shown['frames'][0])
        self.assertIn('path', raw['frames'][0])

    def test_maintenance_deduplicates_without_losing_current_read(self):
        page = {'text': 'One complete useful page.'}
        image = {'sha256': 'x', 'path': 'local.png', 'video_id': 'v1', 'timestamp_seconds': 0}
        raw = {'image_catalog': {'first': image, 'later': image}, 'current_result': page,
               'retained_reading': [{'result': page}], 'run_sources': {'state': {'sha256': 's', 'characters': 42}}}
        shown = model_view(raw)
        self.assertEqual(len(shown['image_catalog']), 1)
        self.assertEqual(shown['current_result'], page)
        self.assertEqual(shown['retained_reading'][0]['result'], {'text_location': 'current_result'})
        self.assertEqual(len(raw['image_catalog']), 2)


class UsageTests(unittest.TestCase):
    def test_http_retry_is_counted_once_usage_unknown_is_preserved(self):
        model = LiteLLMVisionModel(api_key='offline-placeholder', base_url='https://invalid.example', model='test-luna', retries=2)
        returned = {'id': 'test', 'model': 'test-luna', 'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120,
                              'prompt_tokens_details': {'cached_tokens': 30}, 'completion_tokens_details': {'reasoning_tokens': 10}}}
        with tempfile.TemporaryDirectory() as tmp, patch('urllib.request.urlopen', side_effect=[TimeoutError('offline fixture'), io.BytesIO(json.dumps(returned).encode())]) as request, patch('vlm.litellm_vlm.time.sleep'):
            folder = Path(tmp) / 'call'
            self.assertEqual(call_text(folder, model, 'System.', 'Input.', [], attempts=3), '{}')
            self.assertEqual(request.call_count, 2)
            self.assertEqual(load(folder/'allowance.json')['last'], 1)
            records = list((folder/'attempts/01/client-audit/http-attempts').glob('*.json'))
            self.assertEqual(len(records), 2)
            report = summarize(tmp)['roles']['planner']
            self.assertEqual(report['logical_calls'], 1)
            self.assertEqual(report['instrumented_http_attempts'], 2)
            self.assertEqual(report['usage']['total_tokens']['known_sum'], 120)
            self.assertFalse(report['usage']['total_tokens']['complete'])
            self.assertIsNone(report['usage']['cost']['known_sum'])
            self.assertEqual(report['usage']['cached_input_tokens']['known_sum'], 30)
            # Recovery uses the durable answer, with no extra HTTP request.
            self.assertEqual(call_text(folder, model, 'System.', 'Input.', [], attempts=3), '{}')
            self.assertEqual(request.call_count, 2)

    def test_empty_response_usage_retained_and_nested_null_details(self):
        model = LiteLLMVisionModel(api_key='offline-placeholder', model='test-luna', retries=2)
        model._attempt_usage = []
        model._returned_usage({'prompt_tokens': 10, 'completion_tokens': 4, 'completion_tokens_details': None})
        model._returned_usage({'prompt_tokens': 15, 'completion_tokens': 6})
        self.assertEqual(model.last_usage['prompt_tokens'], 25)
        self.assertEqual(model.last_usage['completion_tokens'], 10)
        self.assertNotIn('cost', model.last_usage)


class RuntimeTests(unittest.TestCase):
    setUp = creative_tests.CreativeTests.setUp
    tearDown = creative_tests.CreativeTests.tearDown
    start = creative_tests.CreativeTests.start

    def test_normalized_actions_execute_and_keep_original_receipts(self):
        read = {'tool': 'read', 'arguments': 'experience-map', 'note': 'A concrete optional observation.'}
        generate = {'action': 'generate', 'arguments': {'input_id': 'source', 'prompt': 'Make it blue.',
                    'review_focus': {'focus': ['surface', 'movement'], 'extra_checks': 'Does the face remain recognizable?'}}}
        state = self.start([read, generate])
        self.assertEqual(state['status'], 'waiting_tool')
        self.assertEqual([e['request']['action'] for e in state['events']], ['read', 'generate'])
        self.assertEqual(load(self.h.output/'calls/event-0001/normalization.json')['original'], read)
        self.assertIn('optional observation', state['notes'])
        self.assertTrue((self.h.output/'calls/event-0002/context-components.json').exists())
        self.assertEqual(len(state['jobs']), 1)


class PilotConfigurationTests(Fixture):
    def test_pe_and_pre_experience_freeze_explicit_models_and_seeded_library(self):
        from experiments.unified_benchmark import maintenance_model
        from planner_harness.training_experience import base_snapshot
        models = {role: {'factory': 'vlm.litellm_vlm:LiteLLMVisionModel',
                        'options': {'model': 'offline-luna-fixture', 'reasoning_effort': 'high', 'api_key': 'offline-placeholder'}}
                  for role in ('planner', 'online_critic')}
        batch = self.prepare(methods=['pe-loop', 'pre-experience'], models=models,
                             max_generations=4, sample_ids=['001'], splits=['train'], prompt_forms=['long'])
        self.assertEqual(batch['arms'], ['pe-loop', 'pre-experience'])
        self.assertEqual(batch['planner']['model'], 'offline-luna-fixture')
        self.assertEqual(batch['critic']['model'], 'offline-luna-fixture')
        self.assertEqual(batch['max_generations'], 4)
        self.assertEqual(maintenance_model(batch).model, 'offline-luna-fixture')
        seed = base_snapshot(self.repo, self.output)
        snapshot = load(seed['snapshot'])
        self.assertTrue(snapshot['curated_catalog']['entries'])
        self.assertTrue(batch['training_maintenance'])


if __name__ == '__main__':
    unittest.main()
