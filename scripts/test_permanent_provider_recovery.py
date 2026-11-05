"""Two-device permanent rejection recovery using fake APIs and real receipts."""
import copy
import multiprocessing
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from experiments.device_scheduler import Claims, work_units
from experiments.resumption import task_directory
from planner_harness import accounting as a
from planner_harness.common import load, save, sha
from planner_harness.model_call import call_text, reopen_call, ModelTransportError
from planner_harness.owned_process import birth
from planner_harness.resumption import call_ready
from test_unified_results import Fixture


class RegionalAPIError(RuntimeError):
    retryable = False
    safe_diagnostic = {'status': 403, 'code': 403, 'message': 'This model is not available in your region.'}


class RejectedAPI:
    model = 'offline-regional-api'
    reasoning_effort = 'high'
    requires_live_budget = False
    def predict_text(self, **kwargs):
        raise RegionalAPIError('Explicit synthetic HTTP 403')


class AvailableAPI(RejectedAPI):
    def predict_text(self, **kwargs):
        return 'Saved answer after explicitly restoring provider access.'


def device_worker(output, device, recover=False):
    import os
    output = Path(output)
    batch = load(output / 'batch.json')
    owner = f'{socket.gethostname()}:{os.getpid()}:{birth(os.getpid())}:{device}'
    queue = Claims(output / 'device-queue.sqlite3', work_units(batch, {}), batch['sha256'], owner)
    processed = []
    def execute(topic):
        identity = topic['id']
        directory = task_directory(output, identity, 'full')
        run = directory / 'tasks' / (identity + '__full') / 'run'
        call = run / 'calls/event-0001/transport'
        save(run / 'state.json', {'status': 'model_unavailable', 'pending_event': 'event-0001'})
        scope = a.scope(output / 'accounting', identity, 'full')
        a.start_task(scope)
        try:
            call_text(call, a.attach(RejectedAPI(), scope), 'Planner', identity, [], retry_delay=0)
        except ModelTransportError as exc:
            if exc.retryable:
                raise AssertionError('An explicit 403 must remain permanent')
        else:
            raise AssertionError('Synthetic rejection unexpectedly returned an answer')
        save(output / 'methods' / identity / 'full/settlement.json',
             {'topic': identity, 'method': 'full', 'batch_sha256': batch['sha256'], 'status': 'model_unavailable'})
        queue.finish(identity, 'settled')
        processed.append(identity)
    first = queue.next()
    if first is None:
        raise AssertionError('An independent task was not dispatched')
    execute(first)
    if recover:
        queue.recover(output)
        extra = queue.next()
        if extra is not None:
            execute(extra)
    save(output / ('device-' + str(device) + '.json'), {'processed': processed})


class DeviceRecovery(Fixture):
    def test_other_device_does_not_reopen_permanent_failure_and_explicit_resume_works(self):
        self.prepare(methods=['full'], prompt_forms=['long'], training_maintenance=False)
        batch = load(self.output / 'batch.json')
        a.install(self.output / 'accounting', a.default_online_policy(lanes=['full']))
        # The first owner exits. Another card finishes its task and runs the same
        # claim-recovery path which previously submitted the first event again.
        ctx = multiprocessing.get_context('fork')
        for device in (0, 1):
            process = ctx.Process(target=device_worker, args=(self.output, device, device == 1))
            process.start()
            process.join(30)
            if process.is_alive():
                process.terminate()
                process.join(5)
                self.fail('Offline device worker did not finish')
            self.assertEqual(process.exitcode, 0)
        topics = [t['id'] for t in batch['topics']]
        calls = [task_directory(self.output, topic, 'full') / 'tasks' / (topic + '__full') /
                 'run/calls/event-0001/transport' for topic in topics]
        for call in calls:
            self.assertEqual(len(list((call / 'attempts').glob('*/submitted.json'))), 1)
            self.assertFalse(call_ready(call))
        self.assertEqual(load(self.output / 'device-1.json')['processed'], [topics[1]])
        queue = Claims(self.output / 'device-queue.sqlite3', work_units(batch, {}), batch['sha256'], 'coordinator')
        queue.recover(self.output)
        self.assertIsNone(queue.next())
        self.assertEqual({r['status'] for r in queue.rows()}, {'recovery_required'})
        original = copy.deepcopy(a.load_ledger(self.output / 'accounting')['operations'])
        self.assertEqual(len(original), 2)
        self.assertEqual(len({r['owner_pid'] for r in original.values()}), 2)
        hashes = {p: sha(p) for p in calls[0].rglob('*') if p.is_file()}
        scope = a.scope(self.output / 'accounting', topics[0], 'full')
        # A different worker or restored endpoint alone cannot submit this call.
        with self.assertRaisesRegex(ModelTransportError, 'permanent provider failure'):
            call_text(calls[0], a.attach(AvailableAPI(), scope), 'Planner', topics[0], [])
        self.assertEqual({p: sha(p) for p in calls[0].rglob('*') if p.is_file()}, hashes)
        policy = reopen_call(calls[0], 'Provider access restored after operator verification.', 1)
        self.assertEqual(policy, {'first': 2, 'last': 2})
        self.assertTrue(call_ready(calls[0]))
        queue.recover(self.output)
        self.assertEqual(queue.next()['id'], topics[0])
        result = call_text(calls[0], a.attach(AvailableAPI(), scope), 'Planner', topics[0], [])
        self.assertIn('explicitly restoring', result)
        self.assertEqual(load(calls[0] / 'allowance.json'), policy)
        after = a.load_ledger(self.output / 'accounting')['operations']
        self.assertEqual({key: after[key] for key in original}, original)
        self.assertEqual(len(after), 3)


class TransportDecisions(unittest.TestCase):
    def test_old_automatic_window_does_not_authorize_past_permanent_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            call = Path(tmp)
            save(call / 'input.json', {'model': 'fixture'})
            save(call / 'attempts/01/failed.json', {'retryable': False, 'provider_error': {'status': 403}})
            save(call / 'allowance.json', {'first': 2, 'last': 13})
            save(call / 'retry-window.json', {'first': 2, 'last': 13, 'closed': False})
            save(call / 'recoveries/runtime-2.json', {'first': 1, 'last': 12, 'closed': True,
                                                    'reason': 'permanent_provider_failure'})
            self.assertFalse(call_ready(call))
            reopen_call(call, 'Provider access restored.', 1)
            self.assertTrue(call_ready(call))

    def test_retryable_transient_failure_still_retries_within_the_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            class API(AvailableAPI):
                calls = []
                def predict_text(self, **kwargs):
                    self.calls.append(1)
                    if len(self.calls) == 1:
                        raise ConnectionError('Synthetic temporary connection error')
                    return 'Returned after a transient failure.'
            with patch.dict('os.environ', {'LHA_MODEL_TRANSPORT_ATTEMPTS': '2'}):
                result = call_text(tmp, API(), 's', 'u', [], retry_delay=0)
            self.assertIn('transient', result)
            self.assertEqual(len(API.calls), 2)


if __name__ == '__main__': unittest.main()
