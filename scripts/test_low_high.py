"""Offline contract tests using synthetic videos and scripted model responses."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT / "src"),str(ROOT / "scripts")]
import cv2
import numpy as np
from planner_harness.video import Video
from planner_harness.common import load
from evaluation import low_high as lh
from evaluation import pairwise,temporal,low_high_summary
from evaluation.creative import judge_candidate
from critic_harness.one_shot import validate_report, frozen_profile
from test_creative_loop import review_fixture


def video(path,frames=60,mode="moving",fps=10):
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),fps,(96,64))
    if not writer.isOpened(): raise RuntimeError("Synthetic test video writer unavailable")
    rng=np.random.default_rng(7)
    texture=rng.integers(0,256,(64,96,3),dtype=np.uint8)
    for i in range(frames):
        if mode=="static": frame=texture.copy()
        elif mode=="flash": frame=np.full((64,96,3),255*(i%2),dtype=np.uint8)
        else: frame=np.roll(texture,i,axis=1)
        writer.write(frame)
    writer.release()


def body(events=True):
    return {"track":"long",
        "events":[{"id":"event1","start":1.0,"end":2.0,"reason":"One complete observed interaction"}] if events else [],
        "motion_preservation":{"required":True,"reason":"Appearance-only task retains motion","regions":[[0,0,1,1]]}}



class Judge:
    model="glm5.3flash"
    reasoning_effort=None
    def __init__(self): self.calls=[]
    def predict_text(self,**kwargs):
        visible=json.loads(kwargs["user_text"]);self.calls.append(visible)
        if "source_duration_seconds" in visible: return json.dumps(body())
        if "scope" in visible:
            return json.dumps({"status":"observed","observations":[{"finding":"Scripted event observation, not empirical evidence.",
                 "evidence_refs":[e["id"] for e in visible["evidence"]]}],"limitations":["Synthetic test"]})
        if visible.get("protocol_id")==pairwise.PROTOCOL:
            refs=[next(e["id"] for e in visible["evidence"] if e["video_id"]==v) for v in ("source","A","B")]
            return json.dumps({"protocol_id":pairwise.PROTOCOL,"judgments":{q:{"winner":"tie","reason":"Scripted tie", "evidence_refs":refs,"limitations":[]} for q in pairwise.QUESTIONS}})
        return json.dumps(review_fixture(kwargs["user_text"]))


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source_path=self.root / "source.avi";video(self.source_path)
        self.source=Video(self.source_path,self.root / "info").info
        self.request="Change the scene color to blue."
        self.plan=lh.freeze_plan(body(),self.request,self.source,self.root / "plan")
    def tearDown(self):self.tmp.cleanup()

    def test_source_plan_local_original_only(self):
        judge=Judge()
        with self.assertRaisesRegex(ValueError,'retired'):
            lh.generate_plan(self.request,self.source,self.root/'generated-plan',judge)
        self.assertEqual(judge.calls,[])
        plan=lh.freeze_plan({},self.request,self.source,self.root/'local-plan')
        self.assertNotIn('core_conversion',plan['task'])
        self.assertEqual(plan['task']['original_request'],self.request)
        with self.assertRaises(ValueError):lh.freeze_plan({'targets':['invention']},self.request,self.source,self.root/'bad')
        with self.assertRaises(ValueError):lh.check_plan(plan,'different',self.source)

    def test_request_character_spans_never_become_judge_time_ranges(self):
        request = "Preserve this scene with " + "careful detail " * 16 + ". Keep the people together. Add warm light."
        plan = lh.freeze_plan(body(), request, self.source, self.root / "long-request-plan")
        before = json.dumps(plan, sort_keys=True)
        self.assertGreater(plan["task"]["requirements"][1]["start"], self.source["frames"])
        judge = Judge()
        judge_candidate(request, self.source, self.source, self.root / "long-request-score", model=judge, plan=plan)
        pairwise.compare(request, self.source, self.source, self.source, self.root / "long-request-pair", plan=plan, seed=1, model=judge)
        for visible in judge.calls:
            task = visible["task_spec"]
            self.assertEqual(task["requirements"], [{"id":r["id"],"text":r["text"]} for r in plan["task"]["requirements"]])
            for event in task["events"]:
                self.assertEqual((event["start_seconds"], event["end_seconds"]), (1.0, 2.0))
                self.assertNotIn("start", event)
            scopes = ([visible["scope"]] if "scope" in visible else []) + [r["scope"] for r in visible.get("event_observations", [])]
            for scope in scopes:
                self.assertIn("requested_interval_seconds", scope)
                self.assertNotIn("start", scope["event"])
                self.assertTrue(all("interval_seconds" in r for r in scope["coverage"].values()))
        self.assertEqual(json.dumps(plan, sort_keys=True), before)
        lh.check_plan(plan, request, self.source)

    def test_final_overview_and_events_are_independent_from_online(self):
        self.assertNotEqual(lh.profile()["sha256"],frozen_profile()["sha256"])
        overview,segments,coverage=lh.collect_evidence(self.request,self.source,{"candidate":self.source},self.root / "evidence",self.plan)
        self.assertEqual(coverage["source"]["observed_overview"],20)
        self.assertEqual(coverage["source"]["overview_mapping"],coverage["candidate"]["overview_mapping"])
        for segment in segments:
            for identity in ("source","candidate"):
                rows=[e for e in segment["rows"] if e["video_id"]==identity]
                self.assertEqual([e["frame_index"] for e in rows],list(range(rows[0]["frame_index"],rows[-1]["frame_index"]+1)))
        judge=Judge();result=judge_candidate(self.request,self.source,self.source,self.root / "final",model=judge,plan=self.plan)
        self.assertEqual(result["event_reviews"],1)
        self.assertEqual(len(judge.calls),3)
        self.assertEqual(result["report"]["main_scores"]["temporal_consistency"]["score"],3)
        packet=load(self.root / "final/evidence/request.json")
        self.assertTrue(all(e["kind"]=="overview" for e in packet["images"]))
        self.assertNotIn("source_sha256",packet["user_text"])
        lh.verify_event_records(self.root / "final",packet,judge)
        event_path=self.root / "final/events/event1p0/observation.json"
        modified=load(event_path);modified["report"]["observations"][0]["finding"]="changed"
        event_path.write_text(json.dumps(modified))
        with self.assertRaises(ValueError):lh.verify_event_records(self.root / "final",packet,judge)

    def test_sparse_evidence_requires_unknown_and_rejects_fractional_scores(self):
        packet,_=lh.prepare_final(self.request,self.source,self.source,self.root / "preview",plan=self.plan)
        report=review_fixture(packet["user_text"])
        self.assertEqual(report["main_scores"]["temporal_consistency"]["status"],"unknown")
        validate_report(report,packet)
        report["main_scores"]["temporal_consistency"].update(status="scored",score=3,evidence_refs=[e["id"] for e in packet["images"]])
        with self.assertRaises(ValueError):validate_report(report,packet)
        report=review_fixture(packet["user_text"])
        report["main_scores"]["instruction_adherence"]["score"]=3.1
        with self.assertRaises(ValueError):validate_report(report,packet)
        with self.assertRaisesRegex(ValueError,"shared frozen"):judge_candidate(self.request,self.source,self.source,self.root / "invalid",model=Judge())

    def test_short_output_records_missing_coverage_without_padding(self):
        path=self.root / "short.avi";video(path,frames=20)
        info=Video(path,self.root / "short-info").info
        overview,_,coverage=lh.collect_evidence(self.request,self.source,{"candidate":info},self.root / "short-evidence",self.plan)
        self.assertGreater(coverage["candidate"]["missing_targets"],0)
        times=[r["timestamp_seconds"] for r in overview if r["video_id"]=="candidate"]
        self.assertEqual(len(times),len(set(times)))
        self.assertLessEqual(max(times),1.9+1e-6)

    def test_failed_event_keeps_visual_scores_and_unknown_temporal(self):
        class FailingEvent(Judge):
            def predict_text(self,**kwargs):
                if "scope" in json.loads(kwargs["user_text"]):return "invalid json"
                return super().predict_text(**kwargs)
        judge=FailingEvent()
        result=judge_candidate(self.request,self.source,self.source,self.root / "event-failed",model=judge,plan=self.plan)
        self.assertEqual(result["report"]["main_scores"]["temporal_consistency"]["status"],"unknown")
        self.assertEqual(result["report"]["main_scores"]["visual_integrity"]["score"],3)
        lh.verify_event_records(self.root / "event-failed",load(self.root / "event-failed/evidence/request.json"),judge)

    def test_blind_swap_mapping_and_order_instability(self):
        def report(a,b=None):return {"judgments":{q:{"winner":a if i==0 else b or a} for i,q in enumerate(pairwise.QUESTIONS)}}
        stable=pairwise.reconcile(report("A"),report("B"),["left","right"])
        self.assertEqual(stable["task_completion"]["outcome"],"left")
        unstable=pairwise.reconcile(report("A"),report("A"),["left","right"])
        self.assertEqual(unstable["task_completion"]["outcome"],"order_unstable")
        self.assertEqual(pairwise.reconcile(report("tie"),report("A"),["left","right"])["task_completion"]["outcome"],"order_unstable")
        self.assertEqual(pairwise.reconcile(report("unknown"),report("B"),["left","right"])["task_completion"]["outcome"],"unknown")
        result=pairwise.compare(self.request,self.source,self.source,self.source,self.root / "blind",plan=self.plan,seed=17,model=Judge())
        self.assertEqual(result["judgments"]["task_completion"]["outcome"],"tie")
        for n in (1,2):
            packet=load(self.root / f"blind/order-{n}/request.json")
            for term in ('first_order','left_sha256','right_sha256','source_sha256','final_profile_sha256'):
                self.assertNotIn(term,packet["user_text"])
        rows=[{"source_id":"s1","length":"short","judge":"glm5.3flash","result":result},
              {"source_id":"s2","length":"long","judge":"glm5.3flash","result":None}]
        aggregate=pairwise.summary(rows)["glm5.3flash"]["all"]["task_completion"]
        self.assertEqual((aggregate["planned"],aggregate["valid"],aggregate["missing"]),(2,1,1))
        self.assertEqual(aggregate["left_preference_source_macro"],.5)

    def test_temporal_freeze_does_not_hide_motion_loss(self):
        static=self.root / "static.avi";flash=self.root / "flash.avi"
        video(static,mode="static");video(flash,mode="flash")
        stable=temporal.compute(static,source=self.source_path,motion_scope=self.plan["task"]["motion_preservation"],geometry_aligned=True)
        flicker=temporal.compute(flash)
        moving=temporal.compute(self.source_path)
        self.assertLess(stable["flow_warp_l1"],.001)
        self.assertEqual(stable["low_motion_duration_fraction"],1)
        self.assertGreater(flicker["flow_warp_l1"],.9)
        self.assertGreater(moving["motion_diagonals_per_second"],stable["motion_diagonals_per_second"])
        self.assertGreater(stable["source_motion"]["flow_velocity_error"],.01)
        scoped=temporal.compute(static,source=self.source_path,motion_scope={"required":False,"reason":"Authorized new action","regions":[]})
        self.assertEqual(scoped["source_motion"]["status"],"not_applicable")
        missing=temporal.compute(static,motion_scope=self.plan["task"]["motion_preservation"])
        self.assertEqual(missing["source_motion"]["status"],"unknown")

    def test_source_macro_missing_and_judge_separation(self):
        packet,_=lh.prepare_final(self.request,self.source,self.source,self.root / "summary-preview")
        def result(score):
            report=review_fixture(packet["user_text"])
            for row in report["main_scores"].values():
                if row["status"]=="scored":row["score"]=score
            return {"model":"glm5.3flash","profile_sha256":"test-profile","source_sha256":"source-fixture","plan_sha256":"plan-fixture","report":report}
        rows=[{"source_id":"s1","sample_id":str(i),"length":"short","judge":"glm5.3flash","variant":"knowledge","result":result(4)} for i in range(3)]
        rows += [{"source_id":"s2","sample_id":"0","length":"long","judge":"glm5.3flash","variant":"knowledge","result":result(0)},
                 {"source_id":"s3","sample_id":"0","length":"long","judge":"glm5.3flash","variant":"knowledge","result":None}]
        out=low_high_summary.summarize(rows)
        group=next(g for g in out["groups"] if g["length"]=="all")["dimensions"]
        self.assertEqual(group["instruction_adherence"]["mean_source_macro"],2)
        self.assertEqual(group["instruction_adherence"]["mean_micro"],3)
        self.assertEqual(group["instruction_adherence"]["valid_sources"],2)
        self.assertEqual(group["instruction_adherence"]["statuses"]["missing"],1)
        self.assertIsNone(group["temporal_consistency"]["mean_source_macro"])
        with self.assertRaises(ValueError):low_high_summary.summarize(rows+[rows[0]])
        paired=low_high_summary.paired([{"source_id":"s1","sample_id":"0","length":"short","judge":"glm5.3flash","before":result(2),"after":result(4)},
            {"source_id":"s2","sample_id":"0","length":"long","judge":"glm5.3flash","before":result(3),"after":None}])
        self.assertEqual(next(g for g in paired if g["length"]=="all")["dimensions"]["instruction_adherence"]["mean_delta_source_macro"],2)

    def test_event_subdivision_is_independent_of_candidate_frame_rate(self):
        high=self.root / "high-fps.avi";video(high,frames=120,fps=20)
        info=Video(high,self.root / "high-info").info
        plan_body=body();plan_body["events"][0].update(start=.2,end=4.8)
        plan=lh.freeze_plan(plan_body,self.request,self.source,self.root / "long-event-plan")
        _,a,_=lh.collect_evidence(self.request,self.source,{"candidate":self.source},self.root / "normal",plan)
        _,b,_=lh.collect_evidence(self.request,self.source,{"candidate":info},self.root / "high",plan)
        self.assertEqual([s["requested_interval"] for s in a],[s["requested_interval"] for s in b])
        indices={r["frame_index"] for s in b for r in s["rows"] if r["video_id"]=="candidate"}
        self.assertEqual(indices,set(range(4,97)))

    def test_blind_failed_order_is_unknown_and_keeps_other_order(self):
        class FailedOrder(Judge):
            def predict_text(self,**kwargs):
                visible=json.loads(kwargs["user_text"])
                if visible.get("protocol_id")==pairwise.PROTOCOL and len([x for x in self.calls if x.get("protocol_id")==pairwise.PROTOCOL])<2:
                    self.calls.append(visible);return "not json"
                return super().predict_text(**kwargs)
        result=pairwise.compare(self.request,self.source,self.source,self.source,self.root / "partial-blind",plan=self.plan,seed=2,model=FailedOrder())
        self.assertEqual(result["status"],"partial")
        self.assertEqual(result["judgments"]["task_completion"]["outcome"],"unknown")
        self.assertTrue((self.root / "partial-blind/order-1/unavailable.json").exists())
        self.assertIsNotNone(load(self.root / "partial-blind/order-2/comparison.json")["report"])

    def test_supplied_tracks_coverage(self):
        src=[{"id":"hand","time":0,"x":.2,"y":.2,"confidence":1}, {"id":"hand","time":1,"x":.8,"y":.2,"confidence":1}]
        out=[{**src[0],"x":.3}]
        report=temporal.trajectory_error(src,out,required=True)
        self.assertEqual((report["planned_points"],report["valid_points"]),(2,1))
        self.assertGreater(report["mean_position_error_diagonals"],0)
        self.assertEqual(temporal.trajectory_error(src,out)["status"],"not_applicable")


if __name__=="__main__":unittest.main()
