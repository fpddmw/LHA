"""Offline end-to-end v2 contracts: raw metrics, partial evidence, automatic review."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from planner_harness import PlannerHarness
from planner_harness.common import load,save,sha
from planner_harness.execution import collect
from evaluation import low_high,task_metrics,task_spec,final_suite,low_high_summary
from evaluation.creative import judge_candidate
from test_low_high import video,Judge
from test_creative_loop import action,Scripted,ScriptedCritic,CreativeTests,drain_review,review_fixture
from planner_harness.video import Video


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.path=self.root/'source.avi';video(self.path,frames=20)
        self.source=Video(self.path,self.root/'info').info
        self.request='Adapt the scene to the new world. Keep two protagonists; give the left one a blue coat.'
    def tearDown(self):self.tmp.cleanup()
    def plan(self,track='long'):
        return low_high.freeze_plan({'track':track},self.request,self.source,self.root/track)

    def test_original_spans_without_hidden_requirements_and_task_specific_ratings(self):
        self.assertEqual(len(task_spec.clauses(self.request)),3)
        for track in ('short','long'):
            plan=self.plan(track);judge=Judge()
            result=judge_candidate(self.request,self.source,self.source,self.root/('score-'+track),model=judge,plan=plan)
            metrics=result['task_metrics']['metrics']
            self.assertNotIn('core_conversion',metrics)
            self.assertEqual(metrics['edit_completion']['score'],1)
            self.assertEqual(metrics['binding_accuracy']['status'],'scored' if track=='long' else 'not_applicable')
            self.assertEqual(metrics['style_realization']['status'],'not_applicable' if track=='long' else 'scored')
            self.assertEqual(metrics['joint_satisfaction']['status'],'scored' if track=='long' else 'not_applicable')
            self.assertEqual(metrics['aesthetic_mean']['score'],3)
            task_metrics.verify(self.root/('score-'+track)/'task-metrics',judge)
            packet=load(self.root/('score-'+track)/'task-metrics/request.json')
            self.assertNotIn('core_conversion',json.dumps(packet))
            self.assertNotIn('calibration_status',result)
            if track=='long': self.assertEqual(metrics['joint_satisfaction']['score'],1)
            bad=copy.deepcopy(result['task_metrics']['report']);bad['aesthetics']['color_texture']['score']=3.1
            task_metrics.validate(bad,packet)
            bad['aesthetics']['color_texture']['score']=3.11
            with self.assertRaises(ValueError):task_metrics.validate(bad,packet)
            bad=copy.deepcopy(result['task_metrics']['report']);bad['items'][0]['completion']['label']='unknown'
            calculated=task_metrics.calculate(bad,track)['edit_completion']
            self.assertIsNone(calculated['score']);self.assertEqual(calculated['valid'],2)
            self.assertAlmostEqual(calculated['lower'],2/3);self.assertEqual(calculated['upper'],1)

    def test_rejects_hidden_task_answers_without_waiting(self):
        for body in ({'core_conversion':{'status':'pending','text':None}},
                     {'core_conversion':{'status':'approved','text':'Replace the activity.'}},
                     {'intent':'invented goal'}):
            with self.assertRaises(ValueError):
                low_high.freeze_plan(body,self.request,self.source,self.root/'invalid')
        plan=self.plan()
        self.assertEqual(set(plan['task']),{'original_request','track','requirements','events','motion_preservation'})

    def test_default_features_flow_cache_missing_and_pair_direction(self):
        plan=self.plan()
        with patch.object(final_suite.features,'compute',return_value={'clip_f':.9,'dino_f':.8,'encoders':{}}) as compute:
            first=final_suite.automatic(self.source,self.source,plan,self.root/'automatic')
            second=final_suite.automatic(self.source,self.source,plan,self.root/'automatic')
            self.assertEqual(first,second);self.assertEqual(compute.call_count,1)
            self.assertEqual(compute.call_args.kwargs['sample_fps'],4)
            self.assertEqual(len(compute.call_args.kwargs['clip_revision']),40)
        self.assertEqual(first['metrics']['clip_f']['score'],.9)
        self.assertEqual(first['details']['temporal']['planned_pairs'],19)
        self.assertEqual(first['metrics']['flow_velocity_error']['status'],'not_applicable')
        with patch.object(final_suite.features,'compute',side_effect=ImportError('fixture')):
            missing=final_suite.automatic(self.source,self.source,plan,self.root/'missing')
        self.assertEqual(missing['metrics']['clip_f']['status'],'not_measured')
        self.assertIsNone(missing['metrics']['clip_f']['score'])
        self.assertEqual(missing['metrics']['flow_warp_l1']['status'],'scored')
        a={'automatic':{'metrics':{'flow_warp_l1':{'status':'scored','score':.2}}}}
        b={'automatic':{'metrics':{'flow_warp_l1':{'status':'scored','score':.1}}}}
        self.assertEqual(final_suite.metric_pairs([(a,b),(a,None)])['flow_warp_l1']['improved'],1)
        rows=[{'source_id':'s','sample_id':'s','length':'long','judge':'glm5.3flash','variant':'x','result':a}]
        summary=low_high_summary.summarize(rows)['groups'][0]['dimensions']
        self.assertEqual(summary['flow_warp_l1']['mean_source_macro'],.2)
        self.assertEqual(summary['style_realization']['statuses']['not_applicable'],1)
        path=Path(first['directory'])/'result.json';saved=load(path);saved['metrics']['clip_f']['score']=0;save(path,saved)
        with self.assertRaises(ValueError):final_suite.automatic(self.source,self.source,plan,self.root/'automatic')

    def test_paired_automatic_metrics_survive_missing_vlm_and_missing_candidates(self):
        def result(value):
            return {'report':None,'source_sha256':'source','plan_sha256':'plan','profile_sha256':'profile',
                    'automatic':{'metrics':{'flow_warp_l1':{'status':'scored','score':value}}}}
        base={'source_id':'source','length':'long','judge':'glm5.3flash'}
        rows=[{**base,'sample_id':'one','before':result(.2),'after':result(.1)},
              {**base,'sample_id':'two','before':result(.2),'after':{'report':None,'status':'missing'}}]
        group=next(g for g in low_high_summary.paired(rows) if g['length']=='all')['dimensions']
        self.assertEqual(group['flow_warp_l1']['planned'],2)
        self.assertEqual(group['flow_warp_l1']['valid'],1)
        self.assertEqual(group['flow_warp_l1']['improved'],1)
        self.assertEqual(group['instruction_adherence']['valid'],0)
        changed=copy.deepcopy(rows);changed[0]['after']['plan_sha256']='other-plan'
        with self.assertRaises(ValueError):low_high_summary.paired(changed)

    def test_full_timeline_is_fixed_and_missing_output_is_not_padded(self):
        plan=self.plan();path=self.root/'short.avi';video(path,frames=8)
        info=Video(path,self.root/'short-info').info
        _,segments,coverage=low_high.collect_evidence(self.request,self.source,{'candidate':info},self.root/'frames',plan)
        self.assertEqual({r['frame_index'] for segment in segments for r in segment['rows'] if r['video_id']=='source'},set(range(20)))
        self.assertGreater(coverage['candidate']['missing_targets'],0)


class AutomaticReviewTests(unittest.TestCase):
    setUp=CreativeTests.setUp
    tearDown=CreativeTests.tearDown
    respond=CreativeTests.respond

    def start(self,focus=None,track="long"):
        args={'input_video':'source','prompt':'Make the scene blue.'}
        if focus is not None:args['review_focus']=focus
        self.h=PlannerHarness(self.root/'run',Scripted([action('generate',**args)]))
        self.h.start(self.source,'Make the scene blue.',workflow='creative_loop_v1',mode='loop',execution={'mode':'replay','task_track':track})

    def test_automatic_after_generation_focus_separate_resume_and_no_manual_trigger(self):
        self.start({'focus':'Inspect the contact.', 'events':[{'start':0,'end':1,'question':'Is contact continuous?'}]})
        generation=self.h.state['jobs'][self.h.state['pending_tool']]
        self.assertNotIn('review_focus',generation['payload'])
        self.respond(review=False)
        model=Scripted([]);self.h=PlannerHarness(self.h.output,model);state=self.h.resume()
        self.assertEqual(model.inputs,[]);self.assertEqual(state['status'],'waiting_tool')
        job=state['jobs'][state['pending_tool']]
        self.assertEqual(job['kind'],'critique');self.assertEqual(job['payload']['focus'],'Inspect the contact.')
        self.assertNotIn('core_conversion',json.dumps(job))
        for _ in range(2):
            self.h=PlannerHarness(self.h.output,Scripted([]));self.h.resume()
            self.assertEqual(len(self.h.state['jobs']),2)
        critic=ScriptedCritic();drain_review(self.h,critic)
        self.assertEqual(len([v for v in self.h.state['evaluations'].values()]),1)
        self.assertNotIn('core_conversion',json.dumps(critic.inputs))
        with self.assertRaises(ValueError):self.h.operate(action('critique',video='v1'),'manual')
        self.h.model=Scripted([action('finish',video='v1',message='Propose fixture.'),action('finish',video='v1',message='Accept the reviewed fixture.')])
        state=self.h.resume()
        self.assertEqual(state['status'],'complete');self.assertEqual(len(state['jobs']),2)
        self.assertEqual(state['reviews']['v1']['job_id'],job['id'])
        from planner_harness.delivery import verify_delivery
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')

    def test_automatic_critic_routes_short_specialties_and_exposes_them_to_planner(self):
        self.start(track='short');self.respond(review=False);collect(self.h)
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        self.assertEqual(job['payload']['track'],'short')
        critic=ScriptedCritic();drain_review(self.h,critic)
        feedback=self.h.state['evaluations'][job['id']]
        self.assertIn('summary',feedback['report'])
        self.assertNotIn('task_metrics',feedback)
        from planner_harness.context import feedback_summary
        self.assertEqual(feedback_summary(job['id'],feedback)['summary'],feedback['report']['summary'])
        self.h.model=Scripted([action('finish',video='v1',message='Review short task.'),action('finish',video='v1',message='Accept the reviewed fixture.')])
        self.h.resume()
        from planner_harness.delivery import verify_delivery
        self.assertEqual(verify_delivery(self.h.output)['selected'],'v1')
        # Every review stage receives the actual track; no prompt-length heuristic.
        self.assertTrue(all(json.loads(x['user_text'])['track']=='short' for x in critic.inputs))

    def test_crash_before_auto_checkpoint_replays_same_jobs(self):
        self.start();self.respond(review=False)
        with patch('planner_harness.automatic_review.enqueue',side_effect=RuntimeError('fixture crash')):
            with self.assertRaises(RuntimeError):collect(self.h)
        self.h=PlannerHarness(self.h.output,Scripted([]));self.h.resume()
        self.assertEqual(set(self.h.state['videos']),{'source','v1'})
        self.assertEqual(len(self.h.state['jobs']),2)
        self.assertEqual(len([e for e in self.h.state['events'] if e['request']['action']=='tool_result']),1)

    def test_failed_render_does_not_trigger_review_and_failed_review_cannot_deliver(self):
        self.start();job=self.h.state['jobs'][self.h.state['pending_tool']]
        save(self.h.output/'jobs'/job['id']/'response.json',{'request_sha256':job['sha256'],'mode':'replay','status':'failed','error':'fixture'})
        collect(self.h);self.assertEqual(len(self.h.state['jobs']),1)
        self.h.model=Scripted([action('generate',input_video='source',prompt='Retry blue.')]);self.h.resume()
        self.respond(review=False);collect(self.h)
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        save(self.h.output/'jobs'/job['id']/'response.json',{'request_sha256':job['sha256'],'mode':'replay','status':'failed','error':'fixture'})
        collect(self.h);self.assertEqual(self.h.state['status'],'running')
        self.assertNotIn('final',self.h.state)
        self.h.model=Scripted([action('finish',video='v1',message='I choose from my observations after the explicit review failure.')])
        state=self.h.resume()
        self.assertEqual(state['status'],'complete')
        self.assertEqual(state['reviews']['v1']['status'],'failed')
        self.assertEqual(sum(j['kind']=='critique' for j in state['jobs'].values()),1)


import test_unified_results as registered_fixtures


class RegistryIntegrationTests(registered_fixtures.Fixture):
    def test_current_registry_scores_short_long_and_reuses_full_suite(self):
        from experiments import results as registry
        registry.import_video(self.repo,self.registry,self.row())
        registry.import_video(self.repo,self.registry,self.row(prompt_form='long',request=self.rows[0]['prompt_long']))
        registry.prepare_evaluation(self.repo,self.registry,evaluation_id='offline-v2')
        glm=Judge();sonnet=Judge();sonnet.model='sonnet-5.5high';sonnet.reasoning_effort='high'
        models={'glm5.3flash':glm,'sonnet-5.5high':sonnet}
        with patch.object(final_suite.features,'compute',return_value={'clip_f':.9,'dino_f':.8}) as features:
            view=registry.score_evaluation(self.repo,self.registry,None,models=models)
            counts=(len(glm.calls),len(sonnet.calls),features.call_count)
            repeated=registry.score_evaluation(self.repo,self.registry,None,models=models)
            self.assertEqual((len(glm.calls),len(sonnet.calls),features.call_count),counts)
        ready=[r for r in view['results'] if r['status']=='ready']
        self.assertEqual({r['prompt_form'] for r in ready},{'short','long'})
        for row in ready:
            m=row['judges']['glm5.3flash']['metrics']
            self.assertNotIn('core_conversion',m)
            self.assertEqual(m['clip_f']['score'],.9)
            self.assertEqual(m['binding_accuracy']['status'],'scored' if row['prompt_form']=='long' else 'not_applicable')
        self.assertTrue(view['metrics']['groups'])
        self.assertEqual(view,repeated)


class ReportIdentityTests(unittest.TestCase):
    def test_live_and_offline_transport_validation_preserves_input_binding(self):
        from types import SimpleNamespace
        from planner_harness.report_call import call_report,verify_answer,verify_inputs
        from planner_harness.integrity import IntegrityError
        class Client:
            model='scripted';reasoning_effort='high';requires_live_budget=False
            def __init__(self,answers):self.answers=answers
            def runtime_identity(self):return {'backend':'offline-fixture','version':'1'}
            def predict_text(self,**kwargs):return self.answers.pop(0)
        def validate(report,packet):
            if report!={'ok':True}:raise ValueError('Invalid scripted answer')
        packet={'system_prompt':'Read the evidence.','user_text':'Review this candidate.'}
        for answers in [['{"ok":true}'],['{}','{"ok":true}']]:
            with self.subTest(attempts=len(answers)),tempfile.TemporaryDirectory() as temp:
                folder=Path(temp);client=Client(answers.copy())
                report,binding=call_report(folder,client,packet,[],validate)
                call=verify_answer(folder,report)
                offline=SimpleNamespace(model=client.model,reasoning_effort=client.reasoning_effort)
                verify_inputs(call,client,packet,[]);verify_inputs(call,offline,packet,[])
                self.assertEqual(binding['input_sha256'],sha(call/'input.json'))
                self.assertEqual(call_report(folder,client,packet,[],validate)[0],report)
                sent=load(call/'input.json');sent['transport']['version']='changed';save(call/'input.json',sent)
                with self.assertRaises(IntegrityError):verify_inputs(call,offline,packet,[])
                with self.assertRaises(IntegrityError):verify_answer(folder,report)

    def test_failed_attempt_transport_is_checked_during_offline_recovery(self):
        from types import SimpleNamespace
        from planner_harness.report_call import call_report,verify_inputs,ReportUnavailable
        from planner_harness.integrity import IntegrityError
        class Client:
            model='scripted';reasoning_effort='high';requires_live_budget=False
            def runtime_identity(self):return {'backend':'offline-fixture'}
            def predict_text(self,**kwargs):return '{}'
        def validate(report,packet):raise ValueError('Incomplete answer')
        packet={'system_prompt':'Rubric','user_text':'Evidence'}
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);client=Client()
            with self.assertRaises(ReportUnavailable):call_report(folder,client,packet,[],validate)
            offline=SimpleNamespace(model=client.model,reasoning_effort=client.reasoning_effort)
            for failure in load(folder/'unavailable.json')['failures']:
                call=Path(failure['call_path']);verify_inputs(call,offline,packet,[])
                sent=load(call/'input.json');original=__import__('copy').deepcopy(sent);sent['transport']['backend']='changed';save(call/'input.json',sent)
                with self.assertRaises(IntegrityError):verify_inputs(call,offline,packet,[])
                save(call/'input.json',original)


if __name__=='__main__':unittest.main()
