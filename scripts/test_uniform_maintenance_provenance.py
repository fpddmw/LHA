"""Real uniform preparation through Planner settlement and private maintenance."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from experiments import creative_benchmark as cb, unified_benchmark as u, video_contract as vc
from planner_harness import maintenance as m, training_experience as tx
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from planner_harness.video import Video
from server_runtime.service import Service
from server_runtime.queue import Queue
from server_runtime.engine import Engine
from test_fixed117 import write_video
from test_unified_results import Fixture
from test_loop_engineering import APIPlanner, Renderer
from test_review_modes import Reviewer, action


class UniformMaintenance(Fixture):
    def prepared(self, split='train'):
        write_video(self.source, 120, 24)
        for row in self.rows:
            row['source_video_sha256'] = sha(self.source)
        save(self.repo / 'benchmark_data/benchmark.json', self.rows)
        self.prepare(methods=['pre-experience'], splits=[split], max_generations=1)
        batch = load(self.output / 'batch.json')
        topic = batch['topics'][0]
        spec = cb.task_spec(topic, 'pre-experience', batch, self.output / 'profile.json')
        normalized = Video(self.repo / topic['source'], self.output).info
        self.assertNotEqual(normalized['sha256'], sha(self.source))
        state = {'config': {'execution': spec['execution']}, 'videos': {'source': normalized},
                 'request': {'text': spec['request'], 'source': normalized}}
        run = self.output / 'provenance-run'
        save(run / 'state.json', state)
        return batch, topic, run, state

    def test_real_prepare_task_loop_enqueue_and_activation_for_both_prompt_forms(self):
        batch, _, _, _ = self.prepared()
        target = load(batch['experience_snapshot'])['curated_catalog']['entries'][0]['id']
        for topic in batch['topics']:
            task = cb.task_spec(topic, 'pre-experience', batch, self.output / 'profile.json')
            task['source'] = str((self.repo / topic['source']).resolve())
            conditions = u.task_conditions(self.repo, self.output, topic, 'pre-experience', batch)
            task['execution'].update(experience_snapshot=conditions['experience_snapshot'],
                                     experience_snapshot_sha256=conditions['actual_knowledge_sha256'])
            planner = APIPlanner([action('generate', input_video='source', prompt='Blue painted scene.'),
                                  action('finish', video='v1', message='Select the reviewed scene.')])
            critic = Reviewer()
            renderer = Renderer(self.repo / topic['source'])
            worker = self.output / topic['prompt_form']
            queue = Queue(worker / 'queue.sqlite3')
            config = {'workflow': 'creative_loop_v1', 'review': {'mode': 'critic'},
                      'planner': {'model': planner.model, 'reasoning_effort': planner.reasoning_effort},
                      'critic': {'model': critic.model, 'reasoning_effort': critic.reasoning_effort}}
            with patch('planner_harness.creative.verify_experiment', return_value={'sha256': 'fixture'}):
                service = Service(queue, worker, ROOT, config,
                                  model_factory=lambda role: planner if role == 'planner' else critic,
                                  renderer=renderer)
                service.submit(task)
                Engine(queue, worker, service, service.expand, interval=.001).run(once=True)
            run = worker / 'tasks' / task['id'] / 'run'
            settled = load(run / 'state.json')
            self.assertEqual(settled['status'], 'complete')
            self.assertEqual(len(renderer.calls), 1)
            self.assertTrue(critic.inputs)
            profile = m.stage_profile(ROOT, self.output)
            identity = m.enqueue(self.repo, self.output, run, split='train', topic=topic['id'],
                                 method='pre-experience', batch_sha256=batch['sha256'], maintenance_profile=profile,
                                 maintenance_snapshot=tx.base_snapshot(self.repo, self.output))
            job = load(self.output / 'maintenance/jobs' / identity / 'job.json')
            proof = job['provenance']['normalized_source']
            self.assertEqual(job['provenance']['source_sha256'], sha(self.source))
            self.assertEqual(proof['source_sha256'], settled['videos']['source']['sha256'])
            self.assertEqual(proof['input_plan_sha256'], batch['input_plan_sha256'])
            self.assertEqual(proof['normalization']['source_indices'], vc.sample_indices(120))
            class Contributor:
                model = 'offline-maintenance'
                reasoning_effort = 'high'
                def predict_text(self, **kwargs):
                    return json.dumps({'action': 'contribute', 'arguments': {'text': 'Synthetic review.',
                        'changes': [{'op': 'comment', 'id': target, 'text': 'Synthetic conditional observation.'}]}})
            result = tx.maintain(self.repo, self.output, run, identity,
                                 {'model_calls': 1, 'attempts': 1}, model_factory=Contributor)
            self.assertEqual(result['status'], 'activated', result)

    def test_request_case_and_original_normalized_identities_are_bound(self):
        _, _, run, state = self.prepared()
        baseline = m.provenance(self.repo, run, 'train')
        self.assertEqual(baseline['source_sha256'], sha(self.source))
        for field, value in [('original_source_sha256', 'wrong'), ('source_sha256', 'wrong')]:
            changed = copy.deepcopy(state)
            changed['config']['execution']['benchmark_source'][field] = value
            save(run / 'state.json', changed)
            with self.assertRaises(ValueError):
                m.provenance(self.repo, run, 'train')
        changed = copy.deepcopy(state)
        changed['request']['text'] = self.rows[0]['prompt_long']
        save(run / 'state.json', changed)
        with self.assertRaisesRegex(ValueError, 'source/request'):
            m.provenance(self.repo, run, 'train')
        changed = copy.deepcopy(state)
        changed['config']['execution'].pop('benchmark_source')
        save(run / 'state.json', changed)
        with self.assertRaisesRegex(ValueError, 'attested benchmark source'):
            m.provenance(self.repo, run, 'train')

    def test_resigned_plan_and_receipt_cannot_change_frame_mapping(self):
        _, _, run, state = self.prepared()
        binding = state['config']['execution']['benchmark_source']
        plan_path = Path(binding['input_plan']['path'])
        plan = load(plan_path)
        case = next(c for c in plan['cases'] if c['case_id'] == binding['input_plan']['case_id'])
        binding['normalization']['source_indices'][-1] = 118
        case['normalization'] = copy.deepcopy(binding['normalization'])
        plan['sha256'] = signature({k: v for k, v in plan.items() if k != 'sha256'})
        binding['input_plan']['sha256'] = plan['sha256']
        save(plan_path, plan)
        save((self.repo / binding['source']).with_name('normalization.json'), binding['normalization'])
        save(run / 'state.json', state)
        with self.assertRaisesRegex(ValueError, 'frame indices'):
            m.provenance(self.repo, run, 'train')

    def test_changed_input_plan_is_rejected(self):
        _, _, run, state = self.prepared()
        path = state['config']['execution']['benchmark_source']['input_plan']['path']
        plan = load(path)
        plan['cases'][0]['prompt'] = 'A different task.'
        save(path, plan)
        with self.assertRaisesRegex(ValueError, 'input plan changed'):
            m.provenance(self.repo, run, 'train')

    def test_historical_native_source_retains_original_provenance_shape(self):
        _, _, run, state = self.prepared()
        state['config']['execution'].pop('benchmark_source')
        original = Video(self.source, self.output).info
        state['videos']['source'] = original
        state['request']['source'] = original
        save(run / 'state.json', state)
        result = m.provenance(self.repo, run, 'train')
        self.assertEqual(result['source_sha256'], sha(self.source))
        self.assertNotIn('normalized_source', result)

    def test_modified_source_files_and_receipt_are_rejected(self):
        _, _, run, state = self.prepared()
        normalized = self.repo / state['config']['execution']['benchmark_source']['source']
        for path in (self.source, normalized, normalized.with_name('normalization.json')):
            original = path.read_bytes()
            try:
                if path.suffix == '.json':
                    record = load(path)
                    record['source_indices'][-1] = 118
                    save(path, record)
                else:
                    path.write_bytes(original + b'changed')
                with self.assertRaises(ValueError):
                    m.provenance(self.repo, run, 'train')
            finally:
                path.write_bytes(original)

    def test_heldout_pre_experience_retains_deferred_scope(self):
        _, _, run, _ = self.prepared(split='test')
        self.assertEqual(m.provenance(self.repo, run, 'test', deferred=True)['split'], 'test')
        with self.assertRaisesRegex(ValueError, 'attested training task'):
            m.provenance(self.repo, run, 'test')


if __name__ == '__main__': unittest.main()
