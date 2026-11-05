"""Offline legacy frame selection and cancelled Direct continuation."""
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT / 'scripts/deploy')]
from experiments import render_profiles, recovery, resumption, video_contract as vc
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from planner_harness import accounting
from server_runtime.renderers import PersistentRenderer
from test_fixed117 import write_video
from test_unified_results import Fixture


class NativeConditioning(unittest.TestCase):
    def test_legacy_native_and_explicit_uniform_requests_select_different_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.mp4'
            write_video(source, 120, 24)
            info = {'frames': 120, 'fps': 24, 'width': 32, 'height': 32}
            renderer = PersistentRenderer(ROOT, {'backend': 'bernini', 'generation': render_profiles.BERNINI}, root)
            renderer.ready, renderer.pipeline = True, object()
            renderer.prefix, renderer.clean = '', lambda text: text
            renderer.tokenizer = lambda *args, **kw: {'input_ids': [1]}
            readers = []
            def reader(path):
                readers.append(path)
                return SimpleNamespace(length=120, fps=24)
            renderer.reader = reader
            # Official same-fps smart_video_nframes truncates to the leading 117.
            renderer.indices = lambda *args, **kw: list(range(117))
            payload = {'input_id': 'source', 'input': {'path': str(source), 'sha256': sha(source)},
                       'prompt': 'Mineral-pigment animation.',
                       'renderer': {'backend': 'bernini', 'generation': render_profiles.BERNINI,
                                    'seed': 42, 'output': {'frames': 117, 'fps': 24}}}
            before = copy.deepcopy(payload)
            with patch('run_prompt_probe.inspect_video', return_value=info):
                renderer.prepare({'payload': payload}, root / 'legacy')
                old = load(root / 'legacy/renderer-input.json')
                self.assertEqual(old['conditioning_path'], str(source))
                self.assertEqual(old['conditioning_source_indices'], list(range(117)))
                self.assertFalse((root / 'legacy/conditioning-upgrade.json').exists())
                self.assertEqual(payload, before)
                payload['renderer']['conditioning_policy'] = vc.POLICY
                renderer.prepare({'payload': payload}, root / 'uniform')
            normalized = load(root / 'uniform/conditioning-upgrade.json')
            self.assertEqual(normalized['normalization']['source_indices'], vc.sample_indices(120))
            self.assertEqual(normalized['normalization']['source_indices'][-1], 119)
            self.assertNotEqual(readers[0], readers[1])
            self.assertEqual(sha(source), before['input']['sha256'])

    def test_legacy_other_native_axes_are_not_normalized(self):
        for frames, fps in ((117, 24), (149, 30), (101, 20)):
            payload = {'input': {'path': '/original.mp4'}, 'renderer': {'output': {'frames': frames, 'fps': fps}}}
            info = {'frames': frames + 3, 'fps': fps}
            with patch.object(vc, 'normalize', side_effect=AssertionError('Historical input changed')):
                self.assertEqual(vc.conditioning_input(payload, '.', info), (Path('/original.mp4'), info))

    def test_new_policy_reaches_both_renderer_and_planner_requests(self):
        from experiments.creative_benchmark import direct_request, task_spec
        topic = {'id': 'sample', 'request': 'Blue.', 'source': 'source.mp4', 'source_sha256': 'source',
                 'source_info': {'path': '/source.mp4'}, 'native_output': {'frames': 117, 'fps': 24},
                 'prompt_form': 'short', 'normalization': {'policy': vc.POLICY}}
        batch = {'backend': 'bernini', 'seed_sequence': {'start': 42}, 'generation': render_profiles.BERNINI,
                 'max_generations': 4, 'max_turns': None, 'profile_sha256': 'fixture'}
        self.assertEqual(direct_request(ROOT, topic, batch)['payload']['renderer']['conditioning_policy'], vc.POLICY)
        self.assertEqual(task_spec(topic, 'none', batch, 'profile')['execution']['renderer']['conditioning_policy'], vc.POLICY)
        topic.pop('normalization')
        self.assertNotIn('conditioning_policy', render_profiles.renderer_spec(topic, batch))


class CancelledDirect(Fixture):
    def cancelled(self):
        self.prepare(methods=['direct'], prompt_forms=['short'])
        batch = load(self.output / 'batch.json')
        topic = batch['topics'][0]['id']
        folder = self.output / 'workers/0/baselines' / topic / 'direct/0'
        accounting.install(self.output / 'accounting', accounting.default_online_policy(max_generations=1, lanes=['direct']))
        scope = accounting.scope(self.output / 'accounting', topic, 'direct')
        accounting.start_task(scope)
        body = {'id': topic + '__direct__0', 'kind': 'generate', 'mode': 'live', 'payload': {}, 'accounting_scope': scope}
        request = {**body, 'sha256': signature(body)}
        key = request['sha256']
        save(folder / 'request.json', request)
        save(folder / 'render-started.json', {'request_sha256': key})
        response = {'request_sha256': key, 'status': 'failed', 'task_deadline': True,
                    'outcome_unknown': False, 'resource_ownership_unknown': False,
                    'deadline_cleanup': {'cancellations': [{'operation': key, 'identity_verified': True,
                                                          'local_stopped': True, 'resource_released': True}]}}
        save(folder / 'response.json', response)
        def cancelled():
            raise RuntimeError('Synthetic confirmed cancellation')
        with self.assertRaisesRegex(RuntimeError, 'confirmed cancellation'):
            accounting.invoke(scope, key, 'render', 'render:bernini', cancelled)
        save(self.output / 'methods' / topic / 'direct/settlement.json',
             {'topic': topic, 'method': 'direct', 'batch_sha256': batch['sha256'], 'status': 'budget_exhausted'})
        return batch, topic, folder

    def test_read_only_inspection_preserves_consumed_slot_and_pending_claim(self):
        from experiments.device_scheduler import Claims, work_units
        batch, topic, folder = self.cancelled()
        hashes = {p: sha(p) for p in self.output.rglob('*') if p.is_file()}
        report = recovery.recover_direct(self.output, '0', topic, '')
        self.assertEqual(report['status'], 'cancelled_without_output')
        self.assertEqual((report['submitted_renders'], report['remaining_generation_slots']), (1, 0))
        self.assertEqual((report['extra_generation_allowance'], report['gpu_jobs']), (0, 0))
        self.assertEqual({p: sha(p) for p in self.output.rglob('*') if p.is_file()}, hashes)
        self.assertFalse(resumption.method_recoverable(self.output, topic, 'direct'))
        queue = Claims(self.output / 'device-queue.sqlite3', work_units(batch, {}), batch['sha256'], 'old:0:dead')
        self.assertEqual(queue.next()['id'], topic)
        queue.finish(topic, 'settled')
        queue.recover(self.output)
        self.assertNotEqual(queue.next()['id'], topic)
        self.assertEqual(sha(folder / 'response.json'), hashes[folder / 'response.json'])

    def test_incomplete_cleanup_unknown_and_existing_video_need_reconciliation(self):
        _, topic, folder = self.cancelled()
        original = load(folder / 'response.json')
        for key in ('identity_verified', 'local_stopped', 'resource_released'):
            response = copy.deepcopy(original)
            response['deadline_cleanup']['cancellations'][0][key] = False
            save(folder / 'response.json', response)
            self.assertEqual(recovery.direct_recovery_plan(self.output, '0', topic)['status'], 'reconciliation_required')
        response = copy.deepcopy(original)
        response['outcome_unknown'] = True
        save(folder / 'response.json', response)
        self.assertEqual(recovery.direct_recovery_plan(self.output, '0', topic)['status'], 'reconciliation_required')
        save(folder / 'response.json', original)
        (folder / 'native.mp4').write_bytes(b'Partial video')
        self.assertEqual(recovery.direct_recovery_plan(self.output, '0', topic)['status'], 'reconciliation_required')

    def test_completion_hash_is_checked(self):
        _, topic, _ = self.cancelled()
        completion = next((self.output / 'accounting/operations').glob('*/completion.json'))
        save(completion, {'status': 'failed', 'result': 'changed'})
        with self.assertRaisesRegex(ValueError, 'completion changed'):
            recovery.direct_recovery_plan(self.output, '0', topic)


if __name__ == '__main__': unittest.main()
