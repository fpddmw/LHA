"""Offline campaign counts, ordered phases, and real no-knowledge maintenance."""
import copy
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from contextlib import ExitStack
from experiments import campaign, unified_benchmark as u
from planner_harness import PlannerHarness, training_experience as tx, maintenance
from planner_harness.creative_knowledge import CreativeKnowledge
from planner_harness.common import load, save, sha
from planner_harness.execution import immutable
import test_unified_results as base
import test_creative_loop as loop


class CampaignTests(base.Fixture):
    def setUp(self):
        super().setUp()
        self.config = campaign.configuration(ROOT / 'configs/experiment-campaign.json')
        self.config['rsi_partition']={'train_count':1,'test_count':1}
        # Distinct fixture source hashes keep the RSI partition independent.
        second=self.repo/'source-two.mp4';second.write_bytes(self.source.read_bytes()+b'fixture-two')
        self.rows[1].update(source_video='source-two.mp4',source_video_sha256=sha(second))
        save(self.repo/'benchmark_data/benchmark.json',self.rows)

    def test_counts_and_ablation_not_part_of_main(self):
        result = campaign.plan(self.repo, self.config)
        stages = {r['stage']: r for r in result['batches']}
        self.assertEqual([stages[k]['max_generations'] for k in campaign.STAGES], [16, 16, 4, 16, 16, 16])
        self.assertEqual(result['main_max_generations'], 52)
        self.assertEqual(result['main_trajectories'], 16)
        self.assertEqual(result['validation_conditions_scheduled'], 0)
        self.assertNotIn('self-review', campaign.MAIN)
        self.assertEqual(stages['self-review-zero']['methods'], ['none'])
        self.assertEqual(stages['self-review-knowledge']['methods'], ['full'])
        self.assertEqual(stages['self-review-zero']['review_mode'], 'planner')
        self.assertEqual(stages['self-review-zero']['post_task_maintenance'], 2)
        self.assertEqual(stages['self-review-knowledge']['post_task_maintenance'], 0)

    def test_plan_does_not_prepare_run_or_touch_benchmark(self):
        before = sha(self.repo / 'benchmark_data/benchmark.json')
        with patch.object(u, 'prepare', side_effect=AssertionError('No preparation')):
            campaign.plan(self.repo, self.config)
        self.assertEqual(before, sha(self.repo / 'benchmark_data/benchmark.json'))
        self.assertFalse((self.output / 'campaign.json').exists())

    def test_no_execution_without_explicit_flag(self):
        with self.assertRaisesRegex(ValueError, '--execute'):
            campaign.execute(self.repo, self.output, self.config, {}, 'main')

    def test_online_budget_reuses_existing_normalizer_and_equal_loop_allocations(self):
        methods = ['direct', 'pe-loop', 'none', 'full']
        batch = {'arms': methods, 'max_generations': 4, 'best_of_n': None,
                 'resource_policy': {'max_wall_seconds': 3600}}
        policy = u.policy(batch, campaign.online_budget(self.config, methods, 50))
        self.assertEqual(policy['allocations']['none'], policy['allocations']['full'])
        self.assertIsNone(policy['allocations']['pe-loop']['model_calls'])
        from planner_harness.accounting import validate_policy
        validate_policy(campaign.evaluation_budget(self.config, 50), require_live=True)

    def test_default_training_and_ordered_queue(self):
        batch = self.prepare(methods=None, best_of_n=None)
        train = next(t for t in batch['topics'] if t['split'] == 'train')
        self.assertEqual(train['methods'], ['none'])
        from experiments.device_scheduler import work_units
        units = work_units(batch, {})
        training = [t for t in units if t['split'] == 'train']
        self.assertEqual(training[1]['dependency'], training[0]['claim_id'])
        self.assertTrue(all(t['dependency'] == training[-1]['claim_id'] for t in units if t['split'] == 'test'))

    def test_main_stage_order_reuses_zero_training_in_the_same_registry(self):
        self.config['reuse_direct_results'] = None
        calls = []
        batches = {}
        def prepare(root, output, **options):
            batches[str(output)] = {'topics': [{'id': 'fixture'}], 'arms': options['methods'], 'profile_sha256':'fixture',
                'review': options['review'], 'max_generations': options['max_generations'],
                'seed_sequence': {'start': options['seed_start'], 'step': options['seed_step']},
                'requested_splits': options['splits'], 'requested_prompt_forms': options['prompt_forms'],
                'training_maintenance':options['training_maintenance'],
                'experience_seed_sha256':sha(options['experience_snapshot']), 'experience_owner':options['experience_owner'],
                'results_root': str(options['results_root'])}
            save(Path(output) / 'batch.json', batches[str(output)])
            calls.append(('prepare', Path(output).name, options))
        def run(root, output, host):
            calls.append(('run', Path(output).name))
            return {'status': 'settled', 'positions': [{'status': 'ready'}]}
        def freeze(root, output):
            path = Path(output) / 'trained-experience.json'
            save(path, {'fixture': True})
            save(path.with_name(path.stem+'-receipt.json'),{'revision':{'owner':{'fixture':'critic'}}})
            return path
        save(self.root/'seed.json',{'fixture':'seed'})
        with ExitStack() as stack:
            stack.enter_context(patch.object(campaign, 'seed_library', return_value=self.root/'seed.json'))
            for name, fn in [('prepare', prepare), ('verify', lambda r, o: batches[str(o)]),
                             ('preflight', lambda *a: None), ('policy', lambda *a: {}), ('run', run)]:
                stack.enter_context(patch.object(u, name, side_effect=fn))
            stack.enter_context(patch('planner_harness.accounting.install'))
            stack.enter_context(patch.object(campaign, 'freeze_training', side_effect=freeze))
            stack.enter_context(patch.object(tx, 'validate_snapshot'))
            stack.enter_context(patch('experiments.results.current_evaluation', return_value=None))
            stack.enter_context(patch('experiments.results.prepare_evaluation'))
            score = stack.enter_context(patch('experiments.results.score_evaluation'))
            campaign.execute(self.repo, self.output, self.config, {'renderer': {'backend': 'bernini'}}, 'main', execute_paid=True)
        self.assertEqual([v[1] for v in calls if v[0] == 'run'], ['zero', 'knowledge', 'direct', 'pe-loop'])
        preparations = {v[1]: v[2] for v in calls if v[0] == 'prepare'}
        self.assertEqual(preparations['zero']['methods'], ['none'])
        self.assertEqual(preparations['zero']['review'], {'mode': 'critic'})
        self.assertEqual({str(p['results_root']) for p in preparations.values()}, {str(self.output/'results')})
        self.assertEqual({key:p['training_maintenance'] for key,p in preparations.items()},
                         {'zero':True,'knowledge':False,'direct':False,'pe-loop':False})
        self.assertEqual(preparations['pe-loop']['max_generations'],4)
        self.assertEqual(preparations['knowledge']['max_generations'],4)
        score.assert_called_once()

    def test_pending_generation_does_not_start_training(self):
        self.config['reuse_direct_results'] = None
        batch = {'topics': [{}], 'profile_sha256':'fixture', 'arms': ['none'], 'review': {'mode': 'critic'}, 'training_maintenance':True,
                 'max_generations': 4, 'seed_sequence': {'start': 42, 'step': 1},
                 'requested_splits': ['train','test'], 'requested_prompt_forms': ['short', 'long'],
                 'results_root': str(self.output / 'results')}
        save(self.root/'seed.json',{'fixture':'seed'})
        batch['experience_seed_sha256']=sha(self.root/'seed.json')
        with patch.object(campaign, 'seed_library', return_value=self.root/'seed.json'), \
             patch.object(u, 'prepare'), patch.object(u, 'verify', return_value=batch), \
             patch.object(u, 'preflight'), patch.object(u, 'policy', return_value={}), \
             patch('planner_harness.accounting.install'), \
             patch.object(u, 'run', return_value={'status': 'partial', 'positions': [{'status': 'execution_unknown'}]}) as run:
            with self.assertRaisesRegex(RuntimeError, 'dependent stage'):
                campaign.execute(self.repo, self.output, self.config, {'renderer': {'backend': 'bernini'}}, 'main', execute_paid=True)
        run.assert_called_once()

    def test_direct_reuse_checks_original_conditions_and_omits_scores(self):
        from experiments import results
        source_registry = self.root / 'old-results'
        old = results.import_video(self.repo, source_registry, self.row())
        batch = self.prepare(methods=['direct'], best_of_n=None, splits=['train'], prompt_forms=['short'])
        rows = campaign.reuse_direct(self.repo, self.output, batch, {'renderer': {}}, str(source_registry))
        self.assertEqual(rows[0]['status'], 'reused')
        new = results.find(self.registry, '001', 'short', 'direct', 42)
        self.assertEqual(new['video_sha256'], old['video_sha256'])
        self.assertEqual(new['evaluation_status'], 'pending')
        self.assertFalse((self.registry / 'current-evaluation.json').exists())
        repeated = campaign.reuse_direct(self.repo, self.output, batch, {'renderer': {}}, str(source_registry))
        self.assertEqual(repeated[0]['status'], 'already_registered')

    def test_self_review_missing_rows_appear_only_after_ablation_is_planned(self):
        from experiments import results
        self.prepare(methods=['none'], best_of_n=None, splits=['test'], prompt_forms=['short'])
        results.prepare_evaluation(self.repo, self.registry, evaluation_id='optional-mode')
        records = results.compare_evaluation(self.repo, self.registry, models={})
        self.assertTrue(records)
        self.assertNotIn('critic-vs-planner', {r['review_mode'] for r in records})
        self.output = self.output / 'additional'
        self.prepare(methods=['none'], best_of_n=None, splits=['test'], prompt_forms=['short'], review={'mode': 'planner'})
        records = results.compare_evaluation(self.repo, self.registry, models={})
        cross = [r for r in records if r['review_mode'] == 'critic-vs-planner']
        self.assertTrue(cross)
        self.assertTrue(all(r['result']['judgments'] is None for r in cross))

    def test_readonly_full_population_does_not_initialize_training_or_schedule_maintenance(self):
        from experiments.device_scheduler import work_units
        batch=self.prepare(methods=['full','none'],best_of_n=None,training_maintenance=False)
        self.assertFalse(batch['training_maintenance'])
        self.assertFalse((self.output/'training-experience').exists())
        self.assertTrue(all(not u.training_topic(t,batch) for t in batch['topics']))
        units=work_units(batch,{})
        self.assertTrue(all('dependency' not in t for t in units))
        source=self.root/'frozen-full.json';save(source,{'fixture':'same frozen library'})
        batch.update(experience_snapshot=str(source),experience_seed_sha256=sha(source))
        with patch('planner_harness.training_experience.current',side_effect=AssertionError('Read-only even for RSI train rows')):
            bound=u.task_conditions(self.repo,self.output,batch['topics'][0],'full',batch)
        self.assertEqual(bound['experience_snapshot'],str(source))
        self.assertFalse(bound['training_method'])

    def test_report_all_population_and_rsi_subset_share_scores_without_overwriting(self):
        from experiments import results
        self.prepare(methods=['none','full'],best_of_n=None,training_maintenance=False,prompt_forms=['short'])
        save(self.registry/'analysis-population.json',campaign.population(self.repo,self.config))
        results.prepare_evaluation(self.repo,self.registry,evaluation_id='all-and-rsi')
        results.compare_evaluation(self.repo,self.registry,models={})
        all_rows=results.report(self.repo,self.registry)
        self.assertEqual({r['sample_id'] for r in all_rows['results']},{'001','002'})
        self.assertIn('main_analysis',all_rows)
        before=sha(self.registry/'results.json')
        heldout=results.report(self.repo,self.registry,splits=['test'],methods=['none','full'],
                               review_modes=['critic'],analysis_population='rsi',output_name='rsi')
        self.assertEqual({r['sample_id'] for r in heldout['results']},{'002'})
        self.assertIn('rsi_analysis',heldout)
        self.assertEqual(sha(self.registry/'results.json'),before)
        self.assertTrue((self.registry/'rsi.html').exists())
        main=all_rows['main_analysis']['by_review_mode']['critic']
        rsi=heldout['rsi_analysis']['by_review_mode']['critic']
        self.assertEqual(rsi['plan']['primary']['comparison'],'none_final__to__full_final')
        for comparisons in main['by_judge'].values():
            for endpoints in comparisons.values():
                self.assertTrue(all(m['planned_positions']==2 for m in endpoints.values()))
        for comparisons in rsi['by_judge'].values():
            for endpoints in comparisons.values():
                self.assertTrue(all(m['planned_positions']==1 for m in endpoints.values()))

    def test_new_entry_comment_and_invalid_operation_are_private(self):
        path = self.root / 'seed.json'
        CreativeKnowledge(ROOT, experience_mode='full').freeze(path)
        seed = load(path)
        created, ids = tx.changeset(ROOT, seed, [{'op': 'create', 'id': 'training-fixture',
            'title': 'Fixture condition', 'summary': 'A conditional observation.', 'text': 'Fixture content.'}], {'sha256': 'fixture'})
        self.assertEqual(ids, ['training-fixture'])
        self.assertNotIn('training-fixture', CreativeKnowledge(ROOT, seed).items)
        self.assertIn('training-fixture', CreativeKnowledge(ROOT, created).items)
        commented, _ = tx.changeset(ROOT, created, [{'op': 'comment', 'id': 'training-fixture', 'text': 'Observed boundary.'}], {'sha256': 'evidence'})
        self.assertEqual(CreativeKnowledge(ROOT, commented).read('training-fixture')['text'], CreativeKnowledge(ROOT, created).read('training-fixture')['text'])
        related = CreativeKnowledge(ROOT, commented).read('training-fixture')['related_contributions']
        self.assertIn('Observed boundary.', CreativeKnowledge(ROOT, commented).read(related[0]['id'])['text'])
        self.assertNotIn('Observed boundary.', CreativeKnowledge(ROOT, created).read('training-fixture')['text'])
        with self.assertRaises(ValueError):
            tx.changeset(ROOT, seed, [{'op': 'create', 'id': '../escape', 'text': 'x', 'summary': 'x', 'title': 'x'}], {'sha256': 'fixture'})

    def test_none_task_maintenance_reads_full_library_without_changing_online_exposure(self):
        seed = self.root / 'seed.json'; none = self.root / 'none.json'
        CreativeKnowledge(ROOT, experience_mode='full').freeze(seed)
        CreativeKnowledge(ROOT, experience_mode='none').freeze(none)
        snapshot = load(seed)
        for name in [*snapshot['asset_hashes'], 'knowledge/source-map.json', 'src/planner_harness/CREATIVE_LOOP.md',
                     'docs/experience-authoring-standard.md', 'docs/experience-usage-interface.md', 'docs/online-event-observation.md',
                     *[f'.agents/skills/{name}/SKILL.md' for name in maintenance.SKILLS]]:
            target = self.repo / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        before = tx.initialize(self.repo, self.output, seed)
        execution = {'mode': 'replay', 'experience_mode': 'none', 'renderer': {'seed': 42},
            'experience_snapshot': str(none), 'experience_snapshot_sha256': sha(none),
            'benchmark_metadata': {'split': 'train', 'sample_id': '001'}}
        self.h = PlannerHarness(self.root / 'training-task', loop.Scripted([loop.action('generate', input_video='source', prompt='Blue.')]), root=self.repo)
        self.h.start(self.source, self.rows[0]['prompt_short'], mode='loop', workflow='creative_loop_v1', execution=execution)
        loop.CreativeTests.respond(self)
        self.h.model = loop.Scripted([loop.action('finish', video='v1', stop_reason='budget', message='Fixture stop')]); self.h.resume()
        state_hash = sha(self.h.output / 'state.json'); online_hash = sha(self.h.output / 'knowledge-snapshot.json')
        job = maintenance.enqueue(self.repo, self.output, self.h.output, split='train', topic='001-short', method='none',
                                  batch_sha256='fixture', maintenance_snapshot=before)
        entry = snapshot['curated_catalog']['entries'][0]
        inputs = []
        class Contributor:
            model = 'fixture'; reasoning_effort = 'high'
            def predict_text(inner, **kw):
                inputs.append(kw)
                if len(inputs) == 1:
                    return json.dumps({'action': 'read', 'arguments': {'source': 'knowledge', 'id': entry['id']}})
                return json.dumps({'action': 'contribute', 'arguments': {'text': 'Private fixture increment.', 'changes': [
                    {'op': 'comment', 'id': entry['id'], 'text': 'A post-task fixture boundary.'},
                    {'op': 'create', 'id': 'fixture-new', 'title': 'New insight', 'summary': 'A fixture condition.', 'text': 'New conditional guidance.'}]}})
        result = tx.maintain(self.repo, self.output, self.h.output, job, {'model_calls': 3, 'attempts': 1, 'wall_seconds': 30}, model_factory=Contributor)
        self.assertEqual(result['status'], 'activated', result)
        after = tx.current(self.repo, self.output)
        self.assertIn('fixture-new', CreativeKnowledge(self.repo, after['snapshot']).items)
        self.assertEqual(sha(self.h.output / 'state.json'), state_hash)
        self.assertEqual(sha(self.h.output / 'knowledge-snapshot.json'), online_hash)
        self.assertEqual(load(self.h.output / 'knowledge-snapshot.json')['curated_catalog']['entries'], [])
        self.assertIn(entry['id'], json.dumps(inputs))
        self.assertNotIn('fixture-new', CreativeKnowledge(ROOT, none).items)
        # Replay is idempotent, and test membership cannot authorize activation.
        self.assertEqual(tx.maintain(self.repo, self.output, self.h.output, job), result)
        with self.assertRaises(ValueError):
            maintenance.provenance(self.repo, self.h.output, 'test')


if __name__ == '__main__':
    unittest.main()
