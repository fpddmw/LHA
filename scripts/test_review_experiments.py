"""Review-mode experiment identities and score-free selection. No network/GPU."""
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from test_unified_results import Fixture
from experiments import results,unified_benchmark as u
from planner_harness.common import load,save,sha
from planner_harness import accounting
from planner_harness.execution import signature


class ReviewExperiments(Fixture):
    def test_cross_mode_filter_keeps_the_main_contrast_when_both_modes_are_selected(self):
        for mode in ('critic','planner'):
            results.import_video(self.repo,self.registry,self.row(method='full',review_mode=mode))
        evaluation=results.prepare_evaluation(self.repo,self.registry,evaluation_id='mode-filter')
        directory=self.registry/'evaluations/mode-filter'
        label='full_final@critic__to__full_final@planner'
        record={'sample_id':'001__short__42__review-critic-vs-planner','source_id':sha(self.source),
            'source_group':'001','split':'train','length':'short','seed':42,'judge':'glm5.3flash',
            'comparison':label,'review_mode':'critic-vs-planner','positions':{},'path':None,'sha256':None,
            'result':{'status':'missing','judgments':None}}
        body={'evaluation_sha256':evaluation['sha256'],'records':[record]}
        save(directory/'comparison-index.json',{**body,'sha256':signature(body)})
        key=label+'/review-critic-vs-planner'
        for modes in (None,['critic','planner']):
            view=results.report(self.repo,self.registry,review_modes=modes)
            self.assertIn(key,view['blind_comparisons'])
            self.assertIn(key,view['paired_differences'])
        for modes in (['critic'],['planner']):
            self.assertNotIn(key,results.report(self.repo,self.registry,review_modes=modes)['blind_comparisons'])

    def test_same_seed_full_none_modes_coexist_and_share_one_media_object(self):
        for method in ('full','none'):
            for mode in ('critic','planner'):
                results.import_video(self.repo,self.registry,self.row(method=method,review_mode=mode,
                    evidence={'method_identity':{'review_mode':mode},'receipt':'fixture'}))
        results.import_video(self.repo,self.registry,self.row())
        self.assertEqual(len(list((self.registry/'media').glob('*.mp4'))),1)
        for method in ('full','none'):
            critic=results.find(self.registry,'001','short',method,42,'critic')
            planner=results.find(self.registry,'001','short',method,42,'planner')
            self.assertNotEqual(critic['sha256'],planner['sha256'])
            self.assertEqual(critic['video'],planner['video'])
        view=results.report(self.repo,self.registry)
        ready=[r for r in view['results'] if r['status']=='ready']
        self.assertEqual(len(ready),5)
        self.assertEqual({r['review_mode'] for r in ready},{'critic','planner','shared'})
        positions=results.prepare_evaluation(self.repo,self.registry,evaluation_id='modes')['positions']
        self.assertEqual(len(positions),5)
        results.append_evaluation(self.repo,self.registry)
        self.assertEqual(len(results.current_evaluation(self.registry)[1]['positions']),5)

    def test_old_loop_identity_is_retained_without_treating_it_as_the_new_critic_mode(self):
        entry=results.import_video(self.repo,self.registry,self.row(method='full'))
        self.assertEqual(entry['review_mode'],'legacy')
        self.assertIsNone(results.find(self.registry,'001','short','full',42,'critic'))
        self.assertEqual(results.find(self.registry,'001','short','full',42)['sha256'],entry['sha256'])

    def test_prepare_freezes_review_and_api_roles_and_default_formula_time_policy(self):
        batch=self.prepare(methods=['none'],best_of_n=None,splits=['train'],review={'mode':'planner'})
        self.assertEqual(batch['review'],{'mode':'planner'})
        self.assertEqual(batch['resource_policy']['max_wall_seconds'],None)
        self.assertEqual(batch['max_generations'],4)
        self.assertEqual(batch['models']['planner']['factory'],'vlm.openrouter:OpenRouterVisionModel')
        from experiments.creative_benchmark import task_spec
        task=task_spec(batch['topics'][0],'none',batch,self.output/'profile.json')
        self.assertEqual(task['execution']['review'],{'mode':'planner'})
        self.assertEqual(task['execution']['experience_mode'],'none')
        identity=u.method_identity('none',batch)
        self.assertEqual(identity['review_mode'],'planner')
        self.assertEqual(u.selection_config(),batch['selection'])
        with patch('planner_harness.creative.verify_experiment',return_value={'sha256':'fixture'}):
            restored=self.prepare(methods=['full'],best_of_n=None,splits=['train'])
        self.assertEqual(restored['arms'],batch['arms'])
        self.assertEqual(restored['review'],batch['review'])

    def test_qualitative_selector_cannot_read_formal_review_scores(self):
        batch=self.prepare(methods=['direct-best-of-n'],best_of_n=2)
        topic=batch['topics'][0]
        accounting.install(self.output/'accounting')
        scope=accounting.scope(self.output/'accounting','select','direct-best-of-n')
        from planner_harness.video import Video
        candidates=[{'video':Video(self.source,self.root/'info').info},{'video':Video(self.source,self.root/'info').info}]
        seen=[]
        class Model:
            model='fixture/api';reasoning_effort='high'
            def predict_text(inner,**kwargs):
                seen.append(kwargs)
                packet=json.loads(kwargs['user_text'])
                refs=[r['id'] for r in packet['evidence'] if r['video_id']=='candidate-2']
                return json.dumps({'selected':'candidate-2','reason':'Its visible color treatment better follows the request.','evidence_refs':refs[:1]})
        model=accounting.attach(Model(),scope)
        reviews=[{'report':{'summary':'Candidate one.','limitations':['Legacy field.'],'main_scores':{'instruction_adherence':{'score':4}}}},
                 {'report':{'summary':'Candidate two.','main_scores':{'instruction_adherence':{'score':0}}}}]
        index,decision=u.qualitative_select(self.repo,topic,candidates,reviews,self.root/'select',model)
        self.assertEqual(index,1)
        self.assertNotIn('main_scores',seen[0]['user_text'])
        self.assertNotIn('limitations',seen[0]['user_text'])
        self.assertNotIn('score_definitions',seen[0]['system_prompt'].lower())
        self.assertEqual(decision['policy'],u.SELECTOR)
        u.qualitative_select(self.repo,topic,candidates,reviews,self.root/'select',model)
        self.assertEqual(len(accounting.load_ledger(self.output/'accounting')['operations']),1)

    def test_blind_groups_keep_review_modes_separate_and_do_not_repeat_shared_baseline_calls(self):
        from evaluation.low_high import PROTOCOL,profile
        from evaluation.creative import JUDGES
        from evaluation.pairwise import QUESTIONS
        rows=copy.deepcopy(self.rows);rows[0]['split']='test';save(self.repo/'benchmark_data/benchmark.json',rows)
        for mode in ('critic','planner'):
            for method in ('full','none'):
                results.import_video(self.repo,self.registry,self.row(method=method,review_mode=mode))
        results.import_video(self.repo,self.registry,self.row())
        results.prepare_evaluation(self.repo,self.registry,evaluation_id='mode-blind')
        models={name:SimpleNamespace(model=name,reasoning_effort=None,requires_live_budget=False) for name in JUDGES}
        comparisons=[]
        def score(request,source,candidate,directory,*,model,plan):
            return {'source_sha256':source['sha256'],'output_sha256':candidate['sha256'],'model':model.model,
                'profile_sha256':profile()['sha256'],'report':{'protocol_id':PROTOCOL,'main_scores':{}}}
        def compare(request,source,left,right,directory,*,model,plan,seed):
            comparisons.append(1)
            result={'status':'scored','judge':model.model,'final_profile_sha256':profile()['sha256'],
                'judgments':{q:{'outcome':'tie','mapped_orders':['tie','tie']} for q in QUESTIONS}}
            save(Path(directory)/'result.json',result);return result
        with patch('evaluation.creative.judge_candidate',side_effect=score),patch('evaluation.final_suite.automatic',return_value={'metrics':{}}),patch('evaluation.pairwise.compare',side_effect=compare):
            view=results.score_evaluation(self.repo,self.registry,models=models)
            self.assertIn('none_final__to__full_final/review-critic',view['blind_comparisons'])
            self.assertIn('none_final__to__full_final/review-planner',view['blind_comparisons'])
            self.assertIn('full_final@critic__to__full_final@planner/review-critic-vs-planner',view['blind_comparisons'])
            self.assertIn('none_final@critic__to__none_final@planner/review-critic-vs-planner',view['paired_differences'])
            cross=view['blind_comparisons']['full_final@critic__to__full_final@planner/review-critic-vs-planner']['glm5.3flash']['short']['task_completion']
            self.assertEqual(cross['planned_sources'],1)
            self.assertEqual(len(comparisons),2) # identical video pair, one comparison per judge
            results.score_evaluation(self.repo,self.registry,models=models)
            self.assertEqual(len(comparisons),2)

    def test_api_preflight_never_probes_codex_or_calls_a_provider(self):
        from experiments.preflight import api_model_preflight
        with patch('experiments.preflight.subprocess.run',side_effect=AssertionError('no external command')):
            result=api_model_preflight({},require_credentials=False)
        self.assertEqual(result['planner']['factory'],'vlm.openrouter:OpenRouterVisionModel')
        self.assertFalse(result['planner']['network_checked'])
        with self.assertRaises(ValueError):api_model_preflight({'models':{'planner':{'factory':'vlm.codex_vlm:CodexVisionModel'}}})

    def test_api_preflight_reads_the_same_external_credential_file_as_the_client(self):
        from experiments.preflight import api_model_preflight,provider_identity
        credentials=self.root/'api.env';credentials.write_text('OPENROUTER_API_KEY=offline-test-key\n')
        with patch.dict(os.environ,{'LHA_API_ENV_FILE':str(credentials)},clear=True):
            result=api_model_preflight({},require_credentials=True)
            self.assertTrue(result['planner']['credential_configured'])
        from evaluation.low_high import profile
        with patch('critic_harness.one_shot.frozen_profile',side_effect=AssertionError('online review must not identify final evaluation')):
            self.assertEqual(provider_identity()['rubric_sha256'],profile()['sha256'])

    def test_mode_shard_export_import_preserves_mode_and_shared_media(self):
        self.prepare(methods=['full'],best_of_n=None,splits=['test'],prompt_forms=['short'],review={'mode':'critic'})
        batch=load(self.output/'batch.json');topic=batch['topics'][0]
        for mode in ('critic','planner'):
            results.import_video(self.repo,self.registry,self.row(sample_id=topic['sample_id'],request=topic['request'],method='full',review_mode=mode))
        save(self.output/'host.json',{'shard_rank':0,'shard_count':1})
        export=self.root/'export';target=self.root/'imported'
        manifest=results.export_shard(self.repo,self.registry,self.output,export)
        imported=results.import_manifest(self.repo,target,manifest)
        self.assertEqual(len(imported),1)
        self.assertEqual(imported[0]['review_mode'],'critic')
        self.assertIsNotNone(results.find(target,topic['sample_id'],'short','full',42,'critic'))
        self.assertIsNone(results.find(target,topic['sample_id'],'short','full',42,'planner'))


if __name__=='__main__':unittest.main()
