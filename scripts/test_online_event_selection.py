"""Offline continuous-event observation and online Critic contracts."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from planner_harness.video import Video
from planner_harness.event_observation import observe_event,segments,coverage
from planner_harness.common import load,sha
from planner_harness import PlannerHarness
from critic_harness import one_shot,event_review
from test_creative_loop import Scripted,ScriptedCritic,action,review_fixture
from test_low_high import video,body
from evaluation.low_high import freeze_plan,prepare_final,collect_evidence


class FocusJudge(ScriptedCritic):
    def predict_text(self,**kwargs):
        self.inputs.append(kwargs)
        visible=json.loads(kwargs["user_text"])
        if visible.get("stage")=="select_events":
            start,end=(2,3.2) if "late" in visible["focus"] else (0,1)
            return json.dumps({"events":[{"start":start,"end":end,"question":visible["focus"] or "Inspect event"}],"limitations":[]})
        return json.dumps(review_fixture(kwargs["user_text"]))


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.path=self.root/'source.avi';video(self.path)
        self.source=Video(self.path,self.root/'source-info').info
    def tearDown(self):self.tmp.cleanup()
    def payload(self,*,focus="late contact",candidate=None,events=None):
        return {"request":"Reconstruct the scene while preserving required correspondence", "video_id":"candidate",
            "videos":{"source":self.source,"candidate":candidate or self.source},"compare_to":None,
            "focus":focus,"extra_checks":[],"events":events or [],
            "critic":{"frozen_profile":one_shot.frozen_profile()}}

    def test_planner_views_complete_event_across_actual_model_calls(self):
        commands=[action('observe',video='source',mode='continuous',start=0,end=4,count=8,page=i) for i in range(1,7)]
        commands.append(action('finish',stop_reason='no_promising_attempt',message='Observation-only software fixture.'))
        model=Scripted(commands)
        harness=PlannerHarness(self.root/'planner',model)
        harness.start(self.path,'Inspect the full event.',mode='loop',workflow='creative_loop_v1',execution={'mode':'replay'})
        observations=[o for o in harness.state['observations'] if o.get('mode')=='continuous']
        self.assertEqual(len(observations),6)
        self.assertFalse(observations[0]['coverage']['complete'])
        self.assertTrue(observations[-1]['coverage']['complete'])
        self.assertEqual(observations[-1]['coverage']['observed_frame_indices'],list(range(41)))
        for before,after in zip(observations,observations[1:]):
            self.assertEqual(before['frames'][-1]['frame_index'],after['frames'][0]['frame_index'])
        for observation,input_record in zip(observations,model.inputs[1:]):
            visible=json.loads(input_record['user_text'])
            attached={f['sha256'] for f in visible['attached_images_in_order']}
            self.assertTrue({f['sha256'] for f in observation['frames']}<=attached)
        self.assertIsNone(observations[-1]['next_arguments'])

    def test_page_distinguishes_missing_tail_from_unread_frames(self):
        clip=Video(self.path,self.root/'pages')
        first=observe_event(clip,'page1',start=4,end=7,count=8)
        self.assertEqual(first['coverage']['media_missing_intervals'],[[6.0,7.0]])
        self.assertTrue(first['coverage']['unreviewed_intervals'])
        previous=[first];args=first['next_arguments']
        while args:
            args={k:v for k,v in args.items() if k!='mode'}
            result=observe_event(clip,'page'+str(len(previous)+1),previous=previous,**args)
            previous.append(result);args=result['next_arguments']
        self.assertEqual(result['coverage']['unreviewed_intervals'],[])
        self.assertFalse(result['coverage']['complete'])
        absent=observe_event(clip,'absent',start=7,end=8)
        self.assertEqual(absent['frames'],[])
        self.assertEqual(absent['coverage']['media_missing_intervals'],[[7.0,8.0]])

    def test_mixed_fps_continuous_segments_do_not_drop_ordinals(self):
        other=self.root/'fast.avi';video(other,frames=120,fps=20)
        videos={'source':Video(self.path,self.root/'a'),'candidate':Video(other,self.root/'b')}
        pieces,unread=segments(videos,1,3,size=16,limit=20)
        self.assertIsNone(unread)
        for identity,expected in [('source',set(range(10,31))),('candidate',set(range(20,61)))]:
            actual=set()
            for piece in pieces:
                ids=piece['indices'][identity]
                self.assertLessEqual(len(ids),16)
                self.assertEqual(ids,list(range(ids[0],ids[-1]+1)))
                actual.update(ids)
            self.assertEqual(actual,expected)

    def test_focus_changes_event_selection_and_records_scope(self):
        early=one_shot.run_review(self.payload(focus='early transition'),self.root/'early',FocusJudge())
        late=one_shot.run_review(self.payload(),self.root/'late',FocusJudge())
        self.assertEqual(early['coverage']['events'][0]['event']['start'],0)
        self.assertEqual(late['coverage']['events'][0]['event']['start'],2)
        self.assertGreaterEqual(late['coverage']['events'][0]['event']['end']-2,1)
        packet=load(late['request_path'])
        self.assertTrue(all(row['kind']=='overview' for row in packet['images']))
        dense=[r for r in late['evidence'] if r['kind']=='consecutive_frames' and r['video_id']=='candidate']
        self.assertEqual([r['frame_index'] for r in dense],list(range(20,33)))
        self.assertTrue(late['coverage']['whole_timeline']['candidate']['unreviewed_intervals'])
        self.assertNotIn('dense_windows',one_shot.POLICY)
        event_review.verify_records(Path(late['request_path']).parent,packet,FocusJudge())

    def test_localized_requested_event_is_retained_and_expanded(self):
        requested=[{'start':4,'end':4.2,'question':'Check the ending contact.'}]
        result=one_shot.run_review(self.payload(events=requested),self.root/'explicit',FocusJudge())
        event=result['coverage']['events'][0]['event']
        self.assertLessEqual(event['start'],4)
        self.assertGreaterEqual(event['end'],4.2)
        self.assertGreaterEqual(event['end']-event['start'],1)
        self.assertTrue(result['coverage']['selection_adjustments'])

    def test_short_candidate_retains_absent_interval_and_unknown_tc(self):
        short=self.root/'short.avi';video(short,frames=10)
        candidate=Video(short,self.root/'short-info').info
        result=one_shot.run_review(self.payload(candidate=candidate),self.root/'missing',FocusJudge())
        self.assertEqual(result['coverage']['events'][0]['videos']['candidate']['media_missing_intervals'],[[2.0,3.2]])
        self.assertEqual(result['report']['main_scores']['temporal_consistency']['status'],'unknown')
        self.assertEqual(result['report']['main_scores']['visual_integrity']['score'],3)

    def test_full_event_budget_reports_unreviewed_remainder(self):
        class FullJudge(FocusJudge):
            def predict_text(self,**kwargs):
                p=json.loads(kwargs['user_text'])
                if p.get('stage')=='select_events':
                    self.inputs.append(kwargs)
                    return json.dumps({'events':[{'start':0,'end':6,'question':'Inspect the complete sequence.'}],'limitations':[]})
                return super().predict_text(**kwargs)
        with patch.dict(event_review.POLICY,{'max_event_parts':1}):
            result=one_shot.run_review(self.payload(),self.root/'bounded',FullJudge())
        scoped=result['coverage']['events'][0]
        self.assertEqual(result['coverage']['event_parts_used'],1)
        self.assertIsNotNone(scoped['budget_unreviewed_interval'])
        self.assertFalse(scoped['videos']['candidate']['complete'])
        self.assertTrue(scoped['videos']['candidate']['unreviewed_intervals'])

    def test_failed_event_keeps_visual_scores_and_uncertain_coverage(self):
        class Broken(FocusJudge):
            def predict_text(self,**kwargs):
                if json.loads(kwargs['user_text']).get('stage')=='observe_event':return '{}'
                return super().predict_text(**kwargs)
        result=one_shot.run_review(self.payload(),self.root/'broken',Broken())
        self.assertEqual(result['report']['main_scores']['temporal_consistency']['score'],None)
        scope=result['coverage']['events'][0]
        self.assertTrue(scope['unavailable_or_uncertain_intervals'])
        self.assertTrue(scope['videos']['candidate']['supplied_intervals'])
        self.assertEqual(scope['videos']['candidate']['observed_intervals'],[])

    def test_original_event_answer_tampering_is_rejected_and_resume_reuses(self):
        model=FocusJudge();result=one_shot.run_review(self.payload(),self.root/'resume',model)
        calls=len(model.inputs)
        self.assertEqual(result,one_shot.run_review(self.payload(),self.root/'resume',model))
        self.assertEqual(len(model.inputs),calls)
        packet=load(result['request_path']);directory=Path(result['request_path']).parent
        record=next(r for r in packet['online_event_records'] if r['path'].startswith('events/'))
        raw=Path(record['answer_binding']['call_path'])/'response.txt'
        raw.write_text(raw.read_text()+' changed')
        with self.assertRaises(ValueError):event_review.verify_records(directory,packet,model)

    def test_final_sampling_is_independent_of_online_focus_and_requested_events(self):
        request='Change the scene color to blue.'
        plan=freeze_plan(body(),request,self.source,self.root/'final-plan')
        before=prepare_final(request,self.source,self.source,self.root/'final-before',plan=plan)[0]
        one_shot.run_review(self.payload(events=[{'start':4,'end':5,'question':'Observe the later event.'}]),self.root/'online',FocusJudge())
        after=prepare_final(request,self.source,self.source,self.root/'final-after',plan=plan)[0]
        self.assertEqual(before['user_text'],after['user_text'])
        self.assertEqual(before['profile_sha256'],after['profile_sha256'])
        self.assertEqual(sum(e['video_id']=='candidate' for e in after['images']),20)
        _,events,_=collect_evidence(request,self.source,{'candidate':self.source},self.root/'fixed-events',plan)
        self.assertEqual(events[0]['event']['start'],1.0)
        self.assertEqual(events[0]['event']['end'],2.0)


if __name__=='__main__':unittest.main()
