"""Offline checks of questions -> actions -> outcomes -> maintenance reading."""
import copy
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import test_creative_delivery_review as fixtures
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from planner_harness.experience_usage import project_run, export_batch

action = fixtures.action


class MaintenanceTests(unittest.TestCase):
    setUp, tearDown = fixtures.DeliveryReviewTests.setUp, fixtures.DeliveryReviewTests.tearDown
    start = fixtures.DeliveryReviewTests.start
    respond = fixtures.DeliveryReviewTests.respond
    resume = fixtures.DeliveryReviewTests.resume
    finish = fixtures.DeliveryReviewTests.finish
    review = fixtures.DeliveryReviewTests.review

    def complete(self):
        self.start()
        self.resume([action('generate', input_video='source', prompt='Second blue treatment.')]); self.respond()
        self.resume([action('read', targets=[{'id': 'EX-input-conditioning'}]),
            action('generate', input_video='v2', prompt='Blue contours around the retained arrangement.',
                   justification='EX-input-conditioning favors v2: retain its arrangement while developing the contours.')])
        self.respond(); self.finish(); self.review(); self.finish()
        return self.h.output

    def test_join_and_export_preserve_exposure_reason_actual_action_and_delivery(self):
        run = self.complete(); report = project_run(run)
        generation = next(d for d in report['decisions'] if d['arguments'].get('justification'))
        self.assertEqual(generation['submission']['input_id'], 'v2')
        self.assertEqual(generation['submission']['prompt'], generation['arguments']['prompt'])
        self.assertEqual(generation['candidate_ids'], ['v3'])
        self.assertTrue(generation['continuation_audit']['visible']['justification_required'])
        self.assertEqual(generation['call_status'], 'response_recorded')
        self.assertTrue(any(s['id'] == 'EX-input-conditioning' and s['surface'] == 'text_page' for s in generation['experience_exposure']))
        self.assertEqual(generation['literal_references'][0]['pointer'], '/request/arguments/justification')
        self.assertEqual([d['disposition'] for d in report['decisions'] if d['operation'] == 'finish'],
                         ['delivery_proposed', 'delivery_confirmed'])
        self.assertTrue(report['delivery_proposals'])
        self.assertIsNone(report['independent_outcomes'])
        manifest = self.root / 'manifest.json'
        save(manifest, {'purpose': 'development_maintenance', 'runs': [{'id': 'full', 'path': str(run), 'data_role': 'development'}]})
        summary = export_batch(manifest, self.root / 'export')
        entry = next(r for r in summary['experience_usage'] if r['id'] == 'EX-input-conditioning')
        self.assertEqual(entry['literal_reference_events'], 1)
        self.assertTrue((self.root / 'export/runs/full.md').is_file())
        readable = (self.root / 'export/runs/full.md').read_text()
        self.assertIn('Selected candidate: v1.', readable)
        self.assertIn('Online report:', readable)
        self.assertIn('instruction_adherence:', readable)
        self.assertEqual(summary['runs'][0]['decision_dispositions']['delivery_confirmed'], 1)

    def test_refused_generation_is_not_projected_as_a_render(self):
        self.start(); self.resume([action('generate', input_video='source', prompt='Second.')]); self.respond()
        self.resume([action('generate', input_video='v2', prompt='Third without an explanation.'),
                     action('finish', video='v2', message='Retain a provisional result.', stop_reason='no_promising_attempt')])
        report = project_run(self.h.output)
        refusal = next(d for d in report['decisions'] if d['disposition'] == 'justification_required')
        self.assertIsNone(refusal['submission'])
        self.assertIsNone(refusal['generation_decision'])
        self.assertTrue(refusal['continuation_audit']['visible']['justification_required'])
        self.assertEqual(report['counts']['accepted_generation_requests'], 2)

    def test_historical_missing_records_and_default_judge_isolation(self):
        self.start()
        state = load(self.h.output / 'state.json')
        state.pop('generation_decisions'); state['config'].pop('continuation_policy')
        save(self.h.output / 'state.json', state)
        (self.h.output / 'calls/event-0001/continuation-policy.json').unlink()
        with patch('planner_harness.experience_usage.topic_evidence', side_effect=AssertionError('Unauthorized final evidence read')):
            report = project_run(self.h.output)
        self.assertIsNone(report['decisions'][0]['continuation_audit'])
        self.assertIsNone(report['cohort']['continuation_policy'])
        self.assertIsNone(report['independent_outcomes'])

    def archive(self, run):
        archive = self.root / 'topic/archive'; copied = archive / 'runs/full'
        shutil.copytree(run, copied)
        state = load(copied / 'state.json')
        arms = {}
        for arm in ('direct', 'full', 'none'):
            arms[arm] = {'first': 'v1', 'selected': 'v1', 'videos': {k: v for k, v in state['videos'].items() if k != 'source'}}
            save(archive / (arm + '-record.json'), arms[arm])
        summary = {'topic': 'software-example', 'request': state['request']['text'], 'data_role': 'development_regression',
                   'judges': {}, 'judge_disagreement': {'fixture': 'preserved separately'}}
        for name, score in [('glm5.3flash', 1), ('sonnet-5.5high', 3)]:
            binding = {'request': state['request']['text'], 'source': state['videos']['source']['sha256'],
                       'candidate': state['videos']['v1']['sha256'], 'protocol': 'fixture-protocol',
                       'model': name, 'provider_model': name, 'reasoning_effort': None, 'adapter': 'fixture'}
            key = signature(binding); folder = archive / 'judgments' / key
            result = {'usage': 'independent_final', 'model': name, 'provider_model': name, 'reasoning_effort': None,
                      'source_sha256': binding['source'], 'output_sha256': binding['candidate'],
                      'profile_sha256': binding['protocol'], 'report': {'main_scores': {'fixture': {'score': score}}}}
            save(folder / 'identity.json', binding); save(folder / 'judgment.json', result)
            item = {'key': key, 'result': result, 'sha256': sha(folder / 'judgment.json')}
            summary['judges'][name] = {'positions': {p: copy.deepcopy(item) for p in ['direct', 'full_first', 'full_final', 'none_first', 'none_final']}}
        save(archive / 'summary.json', summary)
        files = {p.relative_to(archive).as_posix(): sha(p) for p in archive.rglob('*') if p.is_file()}
        save(archive.parent / 'archive-manifest.json', {'files': files, 'sha256': signature(files)})
        return archive, copied

    def test_moved_archive_resolves_media_and_keeps_independent_judges_separate(self):
        run = self.complete(); archive, copied = self.archive(run)
        # Original run removal simulates offline retrieval; all input bytes remain archived.
        shutil.rmtree(run)
        report = project_run(copied, topic_archive=archive)
        self.assertTrue(report['videos']['v1']['media']['available'])
        self.assertTrue(Path(report['videos']['v1']['media']['path']).is_relative_to(copied))
        self.assertTrue(report['videos']['v1']['media']['original_path'].startswith(str(run)))
        judges = report['independent_outcomes']['judges']
        self.assertEqual(judges['glm5.3flash']['positions']['direct']['result']['report']['main_scores']['fixture']['score'], 1)
        self.assertEqual(judges['sonnet-5.5high']['positions']['direct']['result']['report']['main_scores']['fixture']['score'], 3)
        self.assertTrue(report['videos']['v1']['independent_positions'])
        self.assertTrue(report['online_feedback'][0]['request']['available'])
        self.assertTrue(all(f['artifact']['available'] for f in report['online_feedback'][0]['evidence']))
        # Missing final scoring is explicit for a distinct unscored candidate hash.
        state = load(copied / 'state.json'); state['videos']['v3']['sha256'] = 'f' * 64
        save(copied / 'state.json', state)
        rejected = project_run(copied, topic_archive=archive)
        self.assertIsNone(rejected['independent_outcomes'])
        self.assertIn('candidate identities', rejected['independent_evidence_error'])
        self.assertTrue(rejected['decisions'])

    def test_changed_independent_artifact_is_rejected(self):
        archive, copied = self.archive(self.complete())
        file = next((archive / 'judgments').glob('*/judgment.json'))
        file.write_text(file.read_text() + '\n')
        rejected = project_run(copied, topic_archive=archive)
        self.assertIsNone(rejected['independent_outcomes'])
        self.assertIn('artifact is missing or changed', rejected['independent_evidence_error'])
        self.assertTrue(rejected['decisions'])


if __name__ == '__main__':
    unittest.main()
