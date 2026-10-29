"""Evidence, isolation and integration checks; synthetic fixtures are not benchmark results."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from critic_harness.runner import CriticHarness, load_feedback
from critic_harness.evidence import Evidence, metadata, validate_assessment
from planner_harness.common import load, save, sha
from planner_harness import PlannerHarness
from planner_harness.execution import signature
from planner_harness.execution import request_job, collect
from critic_harness.adapter import critique
from test_planner_harness import Tests, ScriptedModel


def call(action, **arguments):
    return {"action": action, "arguments": arguments}


class CriticTests(unittest.TestCase):
    setUp = Tests.setUp
    tearDown = Tests.tearDown

    def spec(self):
        return {"request": "Make it blue.", "candidate": "candidate", "duration_seconds": 2,
                "videos": {"source": {"path": str(self.source)}, "candidate": {"path": str(self.source), "parent": "source", "prompt": "SECRET_EXECUTION_PROMPT"}}}

    def assessment(self):
        return {"summary": "Synthetic test judgment, not a measured video result.", "findings": [
            {"id": "color", "dimension": "edit", "origin": "user_requirement", "importance": "core", "verdict": "fail", "claim": "Test fixture remains gray.",
             "evidence": [{"observation_id": "overview", "video": "candidate"}]}]}

    def test_prompt_isolation_and_durable_feedback(self):
        model = ScriptedModel([call("process_context"), call("guide", id="judgment"), call("assess", **self.assessment()), call("process_context"), call("finish", summary="Fixture completed.", process_diagnostics="The actual prompt is available.")])
        h = CriticHarness(self.root / "review", model)
        state = h.start(self.spec())
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["events"][0]["status"], "operation_error")
        for inp in model.inputs[:4]:
            self.assertNotIn("SECRET_EXECUTION_PROMPT", inp["user_text"])
        self.assertIn("SECRET_EXECUTION_PROMPT", model.inputs[4]["user_text"])
        self.assertTrue((h.output / "report.html").exists())
        self.assertEqual(load(h.output / "outcome.json"), self.assessment())

    def evidence(self):
        videos = {k: {**v, "sha256": sha(v["path"]), **metadata(v["path"])} for k,v in self.spec()["videos"].items()}
        return videos, Evidence(videos, self.root / "evidence")

    def test_dense_coverage_crop_and_no_tail_padding(self):
        videos, ev = self.evidence()
        observation = ev.observe("dense", ["source", "candidate"], start=.2, end=.6, dense=True, crop=[0,0,.5,.5])
        self.assertEqual(len(observation["frames"]), 8)
        self.assertTrue(observation["videos"]["candidate"]["continuous"])
        self.assertEqual(observation["videos"]["candidate"]["actual_interval"], [.2,.6])
        with self.assertRaises(ValueError):
            ev.observe("bad", ["source"], end=2.5)
        from PIL import Image
        with Image.open(observation["frames"][0]["path"]) as image:
            self.assertEqual(image.size, (40,30))

    def test_sequence_claim_requires_matching_video_and_interval(self):
        videos, ev = self.evidence()
        observations = {"overview": ev.observe("overview", list(videos)), "dense": ev.observe("dense", list(videos), end=.5, dense=True)}
        report = self.assessment()
        finding = report["findings"][0]
        finding.update(dimension="preservation", origin="preservation", verdict="pass", requires_sequence=True, interval_seconds=[0,2], sequence_videos=["source","candidate"], scope="whole frame", evidence=[{"observation_id":"dense","video":v} for v in videos])
        with self.assertRaisesRegex(ValueError, "exceeds"):
            validate_assessment(report, observations, videos, "candidate", 2)
        finding["interval_seconds"]=[0,.5]
        validate_assessment(report, observations, videos, "candidate", 2)
        finding["evidence"][0]["observation_id"]="invented"
        with self.assertRaisesRegex(ValueError,"not observed"):
            validate_assessment(report, observations, videos, "candidate", 2)

    def test_partial_boundary_and_global_temporal_rating(self):
        videos, ev = self.evidence()
        observations = {"overview": ev.observe("overview", list(videos))}
        report = self.assessment(); report["findings"][0]["verdict"]="partial"
        with self.assertRaisesRegex(ValueError,"partial boundary"):
            validate_assessment(report, observations, videos, "candidate", 2)
        report["findings"][0]["partial_boundary"]="Only one requested component is present."
        report["ratings"]={"temporal":{"score":3.5,"reason":"Fixture test.","evidence":[{"observation_id":"overview","video":"candidate"}]}}
        with self.assertRaisesRegex(ValueError,"continuous coverage"):
            validate_assessment(report, observations, videos, "candidate", 2)
        report = self.assessment()
        report["findings"][0]["dimension"] = "temporal"
        with self.assertRaisesRegex(ValueError,"explicit continuous"):
            validate_assessment(report, observations, videos, "candidate", 2)

    def test_observation_accepts_purpose_inside_arguments(self):
        videos, evidence = self.evidence()
        harness = CriticHarness(self.root / "purpose", ScriptedModel([]))
        harness.state = {"observations":{}}
        harness.evidence = evidence
        result = harness.operate(call("observe", videos=["candidate"], count=2, purpose="Inspect the requested region."),"test-purpose")
        self.assertEqual(result["purpose"],"Inspect the requested region.")
        self.assertEqual(len(harness.state["observations"]["test-purpose"]["frames"]),2)

    def test_visual_memory_keeps_overviews_and_attributed_notes(self):
        actions=[call("observe",videos=["candidate"],count=2,crop=[0,0,.5,.5]),
                 {"observation_note":"Synthetic local observation with unresolved motion.","action":"observe","arguments":{"videos":["source"],"count":2}},
                 call("assess",**self.assessment())]
        model=ScriptedModel(actions)
        h=CriticHarness(self.root / "memory",model)
        h.start(self.spec(),max_turns=3)
        payload=json.loads(model.inputs[2]["user_text"])
        self.assertEqual(payload["notes"][0]["observation_id"],"event-0001")
        self.assertIn("Synthetic local observation",payload["notes"][0]["text"])
        attached=payload["attached_images"]
        self.assertEqual({f["video"] for f in attached if f["observation_id"]=="overview"},{"source","candidate"})
        self.assertIn("event-0002",{f["observation_id"] for f in attached})

    def test_resume_reuses_saved_pending_call_and_checks_material(self):
        h=CriticHarness(self.root / "resume", ScriptedModel([RuntimeError("test interruption")]))
        with self.assertRaises(RuntimeError): h.start(self.spec())
        before=load(h.output / "calls/event-0001/input.json")
        model=ScriptedModel([call("assess",**self.assessment()),call("finish",summary="Fixture complete.")])
        CriticHarness(h.output,model).resume()
        self.assertEqual(before["user_text"],model.inputs[0]["user_text"])
        (h.output / "instructions.json").write_text("{}",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"Frozen"):
            CriticHarness(h.output,model).resume()

    def test_planner_opt_in_uses_actual_ancestry_and_separate_comparison(self):
        model=ScriptedModel([call("critique",video="prior2",compare_to="prior1",question="Check placement.")])
        h=PlannerHarness(self.root / "planner",model)
        imports=[{"path":str(self.source),"parent":"source","provenance":"Synthetic parent"}, {"path":str(self.source),"parent":"prior1","provenance":"Synthetic child"}]
        state=h.start(self.source,"Make it blue.",mode="loop",execution={"critic":{"max_turns":3}}, imported=imports)
        job=state["jobs"][state["pending_tool"]]
        self.assertEqual(job["kind"],"critique")
        self.assertEqual(job["payload"]["videos"]["prior2"]["parent"],"prior1")
        self.assertEqual(job["payload"]["question"],"Check placement.")
        self.assertEqual(state["generation_requests"],0)
        self.assertNotIn("card_data",job["payload"])

    def test_feedback_import_rejects_wrong_task_and_tampering(self):
        h=CriticHarness(self.root / "import-review", ScriptedModel([call("assess",**self.assessment()),call("finish",summary="Fixture complete.")]))
        state=h.start(self.spec())
        path=h.output / "feedback.json"
        valid=load_feedback(path,"Make it blue.",state["spec"]["videos"])
        self.assertEqual(valid["identity_map"],{"source":"source","candidate":"candidate"})
        with self.assertRaisesRegex(ValueError,"original task"):
            load_feedback(path,"Another task",state["spec"]["videos"])
        data=load(path); data["feedback"]["summary"]="Tampered"
        save(path,data)
        with self.assertRaisesRegex(ValueError,"signature"):
            load_feedback(path,"Make it blue.",state["spec"]["videos"])

    def test_worker_feedback_returns_to_same_planner(self):
        h=PlannerHarness(self.root / "worker-planner",ScriptedModel([call("critique",video="prior1")]))
        state=h.start(self.source,"Make it blue.",mode="loop",execution={"critic":{"duration_seconds":2}},
                      imported=[{"path":str(self.source),"parent":"source","provenance":"Synthetic fixture"}])
        job=state["jobs"][state["pending_tool"]]; directory=h.output / "jobs" / job["id"]
        assessment=self.assessment();assessment["findings"][0]["evidence"][0]["video"]="prior1"
        model=ScriptedModel([call("assess",**assessment),call("finish",summary="Fixture feedback.")])
        result=critique(job,directory,ROOT,model=model)
        save(directory / "response.json",{"request_sha256":job["sha256"],"mode":job["mode"],"status":"complete","payload":result})
        after=ScriptedModel([call("finish",video="prior1",message="Fixture selection.")])
        final=PlannerHarness(h.output,after).resume()
        self.assertEqual(final["status"],"complete")
        self.assertIn("Fixture feedback.",after.inputs[0]["user_text"])
        self.assertEqual(final["generation_requests"],0)

    def test_deep_branch_review_keeps_direct_input_not_all_ancestors(self):
        from types import SimpleNamespace
        videos={"source":{"path":str(self.source),"sha256":sha(self.source),"duration_seconds":2}}
        for i in range(1,7):
            videos[f"v{i}"]={**videos["source"],"parent":"source" if i==1 else f"v{i-1}"}
        h=SimpleNamespace(output=self.root / "branch",state={"config":{"mode":"loop","execution":{"critic":{}}},"videos":videos,"request":{"text":"Test"},"jobs":{},"generation_requests":0})
        # An enabled profile has actual options; an empty dictionary is unavailable.
        h.state["config"]["execution"]["critic"]={"max_turns":3}
        request_job(h,"critique",{"video":"v6","compare_to":"v2"},"review")
        payload=h.state["jobs"][h.state["pending_tool"]]["payload"]
        self.assertEqual(set(payload["videos"]),{"source","v6","v5","v2"})
        self.assertEqual(payload["videos"]["v6"]["parent"],"v5")
        self.assertEqual(payload["videos"]["v5"]["recorded_parent_not_in_review"],"v4")


if __name__ == "__main__": unittest.main(verbosity=2)
