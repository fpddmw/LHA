"""Fixed-seed parallel claims and private contribution commits; CPU/scripted only."""
import contextlib
import io
import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from experiments import campaign, device_scheduler as scheduler, results
from planner_harness import maintenance, training_experience as tx
from planner_harness.common import load, save
from planner_harness.creative_knowledge import CreativeKnowledge
from planner_harness.lock import RunLock
from test_loop_protocol_upgrade import IntegrationTests
from test_unified_results import Fixture


def claim_worker(path, units, barrier, owner):
    queue = scheduler.Claims(path, units, 'fixed-seed', owner)
    task = queue.next()
    # All three independent tasks must be claimed before any can settle.
    barrier.wait(timeout=10)
    if task is None:
        raise AssertionError('A card was blocked by an unrelated task')
    queue.finish(task['claim_id'], 'settled')


class ParallelClaims(unittest.TestCase):
    def test_three_processes_claim_independent_tasks_in_every_main_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            for method in ('pre-experience', 'full', 'direct', 'pe-loop'):
                batch = {'arms': [method], 'training_maintenance': method == 'pre-experience',
                         'topics': [{'id': str(i), 'split': 'train' if i < 2 else 'test',
                                     'claim_id': str(i)} for i in range(3)]}
                units = scheduler.work_units(batch, {})
                self.assertTrue(all(t.get('dependency') is None for t in units))
                path = Path(tmp) / (method + '.sqlite3')
                scheduler.Claims(path, units, 'fixed-seed', 'coordinator')
                ctx = multiprocessing.get_context('spawn')
                barrier = ctx.Barrier(3)
                workers = [ctx.Process(target=claim_worker, args=(path, units, barrier, str(i))) for i in range(3)]
                for worker in workers:
                    worker.start()
                try:
                    for worker in workers:
                        worker.join(timeout=15)
                    self.assertTrue(all(not w.is_alive() and w.exitcode == 0 for w in workers))
                    rows = scheduler.Claims(path, units, 'fixed-seed', 'check').rows()
                    self.assertEqual({r['status'] for r in rows}, {'settled'})
                    self.assertEqual(len({r['owner'] for r in rows}), 3)
                finally:
                    for worker in workers:
                        if worker.is_alive():
                            worker.terminate(); worker.join()

    def test_resume_rejects_changed_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'queue.db'
            tasks = [{'id': 'a'}, {'id': 'b', 'dependency': 'a'}]
            scheduler.Claims(path, tasks, 'same-batch', 'old')
            with self.assertRaisesRegex(ValueError, 'dependencies'):
                scheduler.Claims(path, [{'id': 'a'}, {'id': 'b'}], 'same-batch', 'new')


class ParallelMaintenance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'pre-experience'
        self.seed = tx.initialize(ROOT, self.output)
        self.snapshot = load(self.seed['snapshot'])

    def job(self, number):
        folder = self.root / ('task-' + str(number)); folder.mkdir()
        run = IntegrationTests.run_record(self, folder)
        save(run / 'knowledge-snapshot.json', self.snapshot)
        state = load(run / 'state.json')
        state['config']['execution'].update(experience_mode='full', experience_condition='pre-experience',
            experience_snapshot_sha256=self.seed['snapshot_sha256'], review={'mode': 'critic'}, renderer={'backend': 'bernini'})
        save(run / 'state.json', state)
        identity = maintenance.enqueue(ROOT, self.output, run, split='train', topic=str(number),
            method='pre-experience', batch_sha256='fixture', maintenance_snapshot=tx.base_snapshot(ROOT, self.output))
        return run, identity

    def contributor(self, barrier=None):
        expected = self.seed['snapshot_sha256']
        target = self.snapshot['curated_catalog']['entries'][0]['id']
        class Contributor:
            model = 'offline-fixture'
            reasoning_effort = 'high'
            def predict_text(inner, **kwargs):
                packet = json.loads(kwargs['user_text'])
                if packet['maintenance_snapshot']['snapshot_sha256'] != expected:
                    raise AssertionError('Maintainer saw accumulated knowledge')
                if barrier:
                    barrier.wait(timeout=10)
                return json.dumps({'action': 'contribute', 'arguments': {'text': 'Scripted contribution.',
                    'changes': [{'op': 'create', 'id': 'shared-proposed-id', 'title': 'Parallel fixture',
                                 'summary': 'Inspect the transition.', 'text': 'Inspect the transition.'},
                                {'op': 'comment', 'id': 'shared-proposed-id', 'text': 'A comment on this task account.'},
                                {'op': 'comment', 'id': target, 'text': 'Record the observed transition.'}]}})
        return Contributor

    def test_concurrent_maintenance_merges_without_exposing_increments(self):
        jobs = [self.job(i) for i in range(3)]
        barrier = threading.Barrier(3)
        def run(job):
            folder, identity = job
            return tx.maintain(ROOT, self.output, folder, identity,
                {'model_calls': 1, 'attempts': 1, 'wall_seconds': 60}, model_factory=self.contributor(barrier))
        # Force contention rather than depending on coincidental scheduling.
        entered = threading.Event(); release = threading.Event()
        def hold():
            with RunLock(self.output / 'training-experience/owner'):
                entered.set(); release.wait(timeout=10)
        holder = threading.Thread(target=hold); holder.start(); self.assertTrue(entered.wait(5))
        with ThreadPoolExecutor(max_workers=3) as executor:
            pending = [executor.submit(run, job) for job in jobs]
            time.sleep(.15); release.set(); holder.join()
            outcomes = [p.result(timeout=30) for p in pending]
        self.assertEqual([r['status'] for r in outcomes], ['activated'] * 3, outcomes)
        pointer = tx.current(ROOT, self.output)
        self.assertEqual(pointer['version'], 3)
        self.assertEqual(len(pointer['training_sources']), 3)
        library = load(pointer['snapshot'])
        created = [r for r in library['experience_contributions']['items'] if r['operation'] == 'create']
        self.assertEqual(len(created), 3)
        self.assertEqual(len({r['id'] for r in created}), 3)
        for row in created:
            linked = [item for item in library['experience_contributions']['items']
                      if item.get('target_id') == row['id']]
            self.assertEqual(len(linked), 1)
            self.assertEqual(linked[0]['case_id'], row['case_id'])
        self.assertNotIn('shared-proposed-id', CreativeKnowledge(ROOT, tx.base_snapshot(ROOT, self.output)['snapshot']).items)
        before = pointer['snapshot_sha256']
        for folder, identity in jobs:
            tx.maintain(ROOT, self.output, folder, identity, model_factory=lambda: self.fail('Duplicate model call'))
        self.assertEqual(tx.current(ROOT, self.output)['snapshot_sha256'], before)

    def test_interrupted_append_is_recovered_before_another_commit(self):
        run, identity = self.job(0)
        def crash(path, value):
            if Path(path) == self.output / 'training-experience/current.json':
                raise OSError('Injected crash after durable journal')
            return save(path, value)
        with patch.object(tx, 'save', side_effect=crash):
            first = tx.maintain(ROOT, self.output, run, identity,
                {'model_calls': 1, 'attempts': 1}, model_factory=self.contributor())
        self.assertEqual(first['status'], 'failed')
        other_run, other_id = self.job(1)
        second = tx.maintain(ROOT, self.output, other_run, other_id,
            {'model_calls': 1, 'attempts': 1}, model_factory=self.contributor())
        self.assertEqual(second['status'], 'activated', second)
        self.assertEqual(tx.current(ROOT, self.output)['version'], 2)
        contribution = self.output / 'maintenance/jobs' / identity / 'training-attempt-1/contribution.json'
        self.assertEqual(tx.activate(ROOT, self.output, contribution)['status'], 'activated')
        self.assertEqual(tx.current(ROOT, self.output)['version'], 2)
        recovered = tx.maintain(ROOT, self.output, run, identity,
                               model_factory=lambda: self.fail('Recovered contribution called model again'))
        self.assertEqual(recovered['status'], 'activated')
        recovery = load(contribution.parents[1] / 'activation-recovery.json')
        self.assertEqual(recovery['previous_result']['status'], 'failed')


class EntryAndRegistry(Fixture):
    def test_registry_waits_for_other_gpu_commit(self):
        entered = threading.Event(); release = threading.Event()
        def hold():
            with RunLock(self.registry / 'registry-owner'):
                entered.set(); release.wait(timeout=10)
        holder = threading.Thread(target=hold); holder.start(); self.assertTrue(entered.wait(5))
        with ThreadPoolExecutor(max_workers=3) as executor:
            pending = [executor.submit(results.import_video, self.repo, self.registry, self.row(seed=seed))
                       for seed in (41, 42, 43)]
            time.sleep(.1); release.set(); holder.join()
            rows = [future.result(timeout=15) for future in pending]
        self.assertEqual({r['seed'] for r in rows}, {41, 42, 43})
        self.assertEqual(len(results.entry_files(self.registry)), 3)

    def test_public_and_lower_level_device_overrides_and_default_method(self):
        import run_experiment_campaign as entry
        import run_creative_benchmark as lower
        host = self.root / 'host.json'; save(host, {'renderer': {'backend': 'bernini'}, 'devices': [0]})
        for command, extra, receiver in [('check', [], 'check'), ('run', ['--execute'], 'execute')]:
            with patch.object(sys, 'argv', ['campaign', command, '--host-config', str(host), '--devices', '0', '1', '2', *extra]), \
                 patch('experiments.readiness.check', return_value={'status': 'offline_checks_passed'}) as check, \
                 patch.object(campaign, 'execute', return_value={}) as execute, \
                 contextlib.redirect_stdout(io.StringIO()):
                entry.main()
            actual = check.call_args.args[2]['bernini'] if receiver == 'check' else execute.call_args.args[3]
            self.assertEqual(actual['devices'], ['0', '1', '2'])
        with patch.object(sys, 'argv', ['lower', 'prepare', '--output', str(self.output)]), \
             patch('experiments.creative_benchmark.prepare', return_value={'topics': [], 'arms': ['pre-experience']}) as prepare, \
             contextlib.redirect_stdout(io.StringIO()):
            lower.main()
        self.assertEqual(prepare.call_args.kwargs['methods'], ['pre-experience'])
        with patch.object(sys, 'argv', ['lower', 'preflight', '--output', str(self.output), '--host-config', str(host), '--devices', '0', '1']), \
             patch('experiments.creative_benchmark.verify_batch', return_value={'schema': 'lha-unified-benchmark-v1'}), \
             patch('experiments.unified_benchmark.preflight', return_value={}) as check, \
             contextlib.redirect_stdout(io.StringIO()):
            lower.main()
        self.assertEqual(check.call_args.args[2]['devices'], ['0', '1'])

    def test_offline_check_accepts_auto_without_querying_hardware(self):
        from test_public_campaign import PublicChecks
        from experiments import readiness
        config = campaign.configuration(ROOT / 'configs/experiment-campaign.json')
        config['rsi_partition'] = {'train_count': 1, 'test_count': 1}
        host = PublicChecks.host(self); host['devices'] = 'auto'
        with patch.object(scheduler.subprocess, 'check_output', side_effect=AssertionError('GPU inventory query')):
            report = readiness.check(self.repo, config, {'bernini': host})
        declaration = next(r for r in report['checks'] if r['name'] == 'bernini_host')
        self.assertEqual(declaration['status'], 'passed', declaration)
        self.assertEqual(scheduler.device_selection([0, 1, 2]), ['0', '1', '2'])
        with self.assertRaises(ValueError):
            scheduler.device_selection(['auto', '0'])


if __name__ == '__main__':
    unittest.main()
