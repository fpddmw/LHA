"""Offline acceptance for the approved creative loop; no model/network/GPU calls."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import test_planner_harness as legacy
from planner_harness import PlannerHarness
from planner_harness.common import load, save, sha
from planner_harness.creative_knowledge import CreativeKnowledge
from planner_harness.execution import collect
from planner_harness.model_call import call_text
from critic_harness.adapter import critique
from critic_harness.one_shot import DIMENSIONS, frozen_profile, validate_report, prepare_request
from evaluation.creative import ParateraJudge, prepare_final_request, judge_candidate, paired_summary


def action(name, **args):
    return {"action": name, "arguments": args}


class Scripted(legacy.ScriptedModel):
    model = "gpt-6.1-sol"
    reasoning_effort = "high"
    attempts = 5


def review_fixture(user_text):
    """A scripted score, not an assessment of image quality."""
    p = json.loads(user_text)
    candidate = p["candidate_id"]
    source_ref = next(e["id"] for e in p["evidence"] if e["video_id"] == "source")
    refs = [e["id"] for e in p["evidence"] if e["video_id"] == candidate and e["kind"] == "consecutive_frames"]
    scores = {key: {"status": "scored", "score": 3, "reason": "Scripted software fixture; no visual finding is asserted.",
                   "evidence_refs": [source_ref, *refs[:2]], "limitations": ["Not a real evaluation."]}
              for key in DIMENSIONS}
    comparisons = []
    if p.get("compare_to"):
        reference = next(e["id"] for e in p["evidence"] if e["video_id"] == p["compare_to"])
        comparisons = [{"against": p["compare_to"], "dimension": "visual_integrity", "change": "same",
                        "reason": "Scripted comparison only.", "evidence_refs": [reference, refs[0]]}]
    return {"protocol_id": p["protocol_id"], "candidate_id": candidate, "main_scores": scores,
            "comparisons": comparisons, "extra_checks": [{"id": c["id"], "status": "unknown", "reason": "Scripted unknown.",
              "evidence_refs": [], "limitations": []} for c in p["extra_checks"]], "unassessed": ["Software fixture only."]}


class ScriptedCritic:
    model = "gpt-6.1-sol"
    reasoning_effort = "high"
    attempts = 5

    def __init__(self, invalid=False):
        self.inputs = []
        self.invalid = invalid

    def predict_text(self, **kwargs):
        self.inputs.append(kwargs)
        if self.invalid:
            return "This is not a JSON report."
        return json.dumps(review_fixture(kwargs["user_text"]))


class CreativeTests(unittest.TestCase):
    setUp = legacy.Tests.setUp
    tearDown = legacy.Tests.tearDown

    def start(self, actions=None, **kwargs):
        self.model = Scripted(actions or [action("generate", input_video="source", prompt="Make the scene blue.")])
        self.h = PlannerHarness(self.root / "run", self.model)
        return self.h.start(self.source, "Make the scene blue.", mode="loop", workflow="creative_loop_v1",
                            execution={"mode": "replay"}, **kwargs)

    def respond(self):
        s = load(self.h.output / "state.json")
        job = s["jobs"][s["pending_tool"]]
        p = job["payload"]
        save(self.h.output / "jobs" / job["id"] / "response.json", {
            "request_sha256": job["sha256"], "mode": "replay", "status": "complete",
            "payload": {"video": {"path": str(self.source), "sha256": sha(self.source)},
                        "replay_provenance": "Synthetic test media; no rendering occurred.",
                        "execution": {"requested_prompt": p["prompt"], "effective_prompt": p["prompt"],
                                      "input_sha256": p["input"]["sha256"]}}})

    def resume(self, actions):
        self.model = Scripted(actions)
        self.h = PlannerHarness(self.h.output, self.model)
        return self.h.resume()

    def review_job(self):
        self.start()
        self.respond()
        self.resume([action("critique", video="v1", focus="Inspect visible geometry.", extra_checks=["Is the rim visibly blue?"])])
        return self.h.state["jobs"][self.h.state["pending_tool"]]

    def complete_delivery(self):
        proposal=self.h.state['delivery_reviews'][self.h.state['active_delivery_proposal']]
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        folder=self.h.output/'jobs'/job['id']
        feedback=critique(job,folder,ROOT,model=ScriptedCritic())
        save(folder/'response.json',{'status':'complete','mode':job['mode'],'request_sha256':job['sha256'],'payload':feedback})
        self.model=Scripted([action('finish',video=proposal['binding']['candidate_id'],message='Confirm this fixture after the complete report.')])
        self.h=PlannerHarness(self.h.output,self.model)
        return self.h.resume()

    def test_four_classes_complete_material_and_no_excluded_sources(self):
        k = CreativeKnowledge(ROOT)
        k.freeze(self.root / "knowledge.json")
        k = CreativeKnowledge(ROOT, self.root / "knowledge.json")
        self.assertEqual(len(k.overview()["classes"]), 4)
        self.assertEqual(k.manifest["totals"]["complete_entries"], 111)
        self.assertEqual(k.manifest["totals"]["domain_cards"], 5)
        original_assets = {p: h for p, h in k.snapshot["asset_hashes"].items() if not p.startswith("knowledge/experience/curated/")}
        self.assertEqual(len(original_assets), 98)
        approved_images = {r["path"] for r in k.curated_catalog["resources"] if Path(r["path"]).suffix in {".png", ".jpg", ".jpeg", ".webp"}}
        self.assertEqual(set(k.snapshot["asset_hashes"]) - set(original_assets), approved_images)
        for identity in ("manual", "meaning", "opuscar-053", "choose-editing-input"):
            self.assertIn("text", k.read(identity))
        for identity in ("wiki-map", "wiki-scene-identity", "case-bernini-027-after-v1",
                         "knowledge/INTEGRATION.md", "knowledge/staged/e1-20261030/README.md", "../../.env"):
            with self.assertRaises(ValueError): k.read(identity)
            with self.assertRaises(ValueError): k.references(identity)
        self.assertEqual(k.search("evidencecarduniquenonsense")["matches"], [])
        for path, document in k.snapshot["documents"].items():
            # Approved source extracts retain historical words verbatim; they do
            # not grant access to the excluded historical workflow or Wiki IDs.
            if not path.startswith("knowledge/experience/curated/evidence/"):
                self.assertNotRegex(document["text"], r"\bRSI\b|\[\[wiki-|rsi_|evidence cards")
            if path.startswith(("knowledge/entries/", "knowledge/domain", "knowledge/guides/", "knowledge/experience/")):
                self.assertEqual(document["sha256"], sha(ROOT / path))
        self.assertTrue(k.read("map")["links"])
        self.assertEqual(k.read("knowledge/README.md")["id"], "map")

    def test_no_forms_no_automatic_work_review_four_generations_and_earlier_delivery(self):
        self.start([action("read", targets=[{"id": "meaning"}, {"id": "opuscar-053"}]),
                    action("workspace", summary="A visual direction remains open."),
                    action("generate", input_video="source", prompt="Make the scene blue.")])
        for number in range(1, 4):
            self.respond()
            commands = [action("generate", input_video="v1" if number > 1 else "source", prompt=f"Blue treatment {number}.",justification='A software-fixture continuation.')]
            if number == 1:
                commands.insert(0, action("delivery_candidate", video="v1"))
            self.resume(commands)
        self.assertEqual(self.h.state["generation_requests"], 4)
        self.assertFalse(any(j["kind"] == "critique" for j in self.h.state["jobs"].values()))
        self.respond()
        state = self.resume([action("finish", video="v1", message="Retain the earlier candidate in this scripted test.")])
        self.assertEqual(state['status'],'waiting_tool')
        state = self.complete_delivery()
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["final"]["video"], "v1")
        self.assertEqual(state["videos"]["v4"]["parent"], "v1")
        self.assertEqual(json.loads(self.model.inputs[0]["user_text"])["delivery_candidate"], "v1")
        for name in ("requirements", "task_memory", "intent", "rsi"):
            self.assertNotIn(name, state)
        self.assertNotIn("Frozen task card", (self.h.output / "system-prompt.txt").read_text())

    def test_waiting_resume_does_not_duplicate_job_or_call_model(self):
        self.start()
        job = self.h.state["pending_tool"]
        state = self.resume([])
        self.assertEqual(state["pending_tool"], job)
        self.assertEqual(len(state["jobs"]), 1)
        self.assertEqual(self.model.inputs, [])

    def test_multiple_requested_style_references_are_all_attached(self):
        self.start()
        result = self.h.operate(action("view_reference", id=["zyx/img/opuscar98/01.jpg", "zyx/img/opuscar98/02.jpg"]), "references")
        _, images, mapping = self.h.context()
        self.assertTrue(all(r["path"] in images for r in result["images"]))
        self.assertEqual(sum(m.get("kind") == "knowledge reference, not source-video evidence" for m in mapping), 2)

    def test_mixed_profile_and_legacy_tools_rejected(self):
        with self.assertRaisesRegex(ValueError, "RSI"):
            self.start(rsi={})
        self.start()
        for name in ("requirements", "criteria_objection", "evaluate", "lesson"):
            with self.assertRaises(ValueError): self.h.operate(action(name), "invalid")
        with self.assertRaises(ValueError):
            self.h.operate(action("generate", input_video="source", prompt="Blue.", intent={}), "invalid")
        from planner_harness.creative import configure
        for profile in ({"rsi": {}}, {"evaluation": None}, {"critic": {"protocol": "legacy"}}):
            with self.assertRaises(ValueError): configure(self.h, profile)

    def test_single_review_cache_and_no_advice_or_intent_in_request(self):
        job = self.review_job()
        critic = ScriptedCritic()
        folder = self.h.output / "jobs" / job["id"]
        result = critique(job, folder, ROOT, model=critic)
        self.assertEqual(len(critic.inputs), 1)
        self.assertEqual(critic.attempts, 5)
        visible = json.loads(critic.inputs[0]["user_text"])
        self.assertEqual(visible["focus"], "Inspect visible geometry.")
        self.assertNotIn("prompt", json.dumps(visible["videos"]))
        self.assertNotIn("intent", visible)
        self.assertEqual(result, critique(job, folder, ROOT, model=critic))
        self.assertEqual(len(critic.inputs), 1)
        save(folder / "response.json", {"status": "complete", "mode": "replay", "request_sha256": job["sha256"], "payload": result})
        state = self.resume([action("critique", video="v1", focus="A different question."),
                             action("finish", video="v1", message="Scripted delivery proposal."),
                             action("finish", video="v1", message="Confirm after the reused complete report.")])
        self.assertEqual(sum(j["kind"] == "critique" for j in state["jobs"].values()), 1)
        self.assertTrue(any(e.get('result',{}).get('cached') for e in state['events']))
        context = json.loads(self.model.inputs[0]["user_text"])
        self.assertNotIn("rubric", context["execution_profile"]["critic"])
        self.assertIn("main_scores", next(iter(context["evaluations"].values()))["report"])

    def test_invalid_report_is_not_repaired_or_recalled(self):
        job = self.review_job()
        critic = ScriptedCritic(invalid=True)
        folder = self.h.output / "jobs" / job["id"]
        for _ in range(2):
            with self.assertRaises(ValueError): critique(job, folder, ROOT, model=critic)
        self.assertEqual(len(critic.inputs), 1)
        self.assertTrue((folder / "one-shot-critic/invalid-report.json").exists())

    def test_fixed_scores_references_unknown_and_advice_guard(self):
        job = self.review_job()
        packet, _ = prepare_request(job["payload"]["request"], "v1", job["payload"]["videos"],
                                    self.root / "packet", frozen_profile())
        report = review_fixture(packet["user_text"])
        row = report["main_scores"]["temporal_consistency"]
        row.update(status="unknown", score=None, evidence_refs=[])
        self.assertEqual(validate_report(report, packet)["main_scores"]["temporal_consistency"]["score"], None)
        for update in ({"score": 0}, {"status": "scored", "score": 4.1},
                       {"reason": "You should regenerate from the source."}, {"evidence_refs": ["not-real"]}):
            bad = copy.deepcopy(report)
            bad["main_scores"]["temporal_consistency"].update(update)
            with self.assertRaises(ValueError): validate_report(bad, packet)
        report["main_scores"]["new_main_metric"] = row
        with self.assertRaises(ValueError): validate_report(report, packet)

    def test_profile_freeze_and_resource_stop_remain_incomplete(self):
        self.start(max_generations=1)
        self.respond()
        state = self.resume([action("generate", input_video="v1", prompt="Blue again."),
                             action('finish',video='v1',stop_reason='budget',message='Explicit fixture resource pause.')])
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertEqual(state['final']['stop_reason'],'budget')
        self.h.state["config"]["execution"]["critic"]["frozen_profile"]["rubric"] += "changed"
        self.h.checkpoint()
        with self.assertRaises(ValueError): self.resume([])

    def test_blocked_choice_is_not_delivery(self):
        self.start()
        self.respond()
        state = self.resume([action("finish", video="v1", stop_reason="no_promising_attempt", message="Scripted blockage.")])
        self.assertEqual(state["status"], "delivery_blocked")

    def test_transport_retry_is_bounded_recorded_and_does_not_mutate_model(self):
        model = Scripted([ConnectionError("temporary"), action("note", text="Recovered.")])
        text = call_text(self.root / "retry", model, "system", "user", [], retry_delay=0)
        self.assertIn("Recovered", text)
        self.assertEqual(len(model.inputs), 2)
        self.assertEqual(model.attempts, 5)
        self.assertTrue((self.root / "retry/attempts/01/failed.json").exists())
        self.assertEqual(text, call_text(self.root / "retry", model, "system", "user", [], retry_delay=0))
        self.assertEqual(len(model.inputs), 2)

    def test_independent_judge_anonymity_model_and_missing_values(self):
        self.start()
        self.respond()
        self.resume([action("finish", video="v1", message="Scripted delivery.")])
        source, video = self.h.state["videos"]["source"], self.h.state["videos"]["v1"]
        packet, images = prepare_final_request("Make the scene blue.", source, video, self.root / "final")
        p = json.loads(packet["user_text"])
        self.assertEqual(set(p["videos"]), {"source", "candidate"})
        self.assertEqual(p["extra_checks"], [])
        self.assertNotIn("prompt", json.dumps(p["videos"]))
        body = ParateraJudge.build_payload(packet["system_prompt"], packet["user_text"], images[:1])
        self.assertEqual(body["model"], "GLM-5.3-Flash")
        self.assertNotIn("reasoning_effort", body)
        self.assertNotIn("max_completion_tokens", body)
        model = ScriptedCritic()
        model.model, model.reasoning_effort = "glm5.3flash", None
        judgment = judge_candidate("Make the scene blue.", source, video, self.root / "final", model=model)
        self.assertEqual(judgment["usage"], "independent_final")
        a = copy.deepcopy(judgment["report"])
        b = copy.deepcopy(a)
        b["main_scores"]["temporal_consistency"].update(status="unknown", score=None)
        result = paired_summary([(a, b)])
        self.assertEqual(result["temporal_consistency"]["missing"], 1)
        self.assertIsNone(result["temporal_consistency"]["mean_delta"])
        self.assertEqual(self.h.state["evaluations"], {})

    def test_server_entry_preserves_explicit_workflow_without_starting_renderer(self):
        from server_runtime.queue import Queue
        from server_runtime.service import Service
        q = Queue(self.root / "service/queue.sqlite3")
        model = Scripted([action("generate", input_video="source", prompt="Blue.")])
        service = Service(q, self.root / "service", ROOT, {"workflow": "creative_loop_v1"},
                          model_factory=lambda role: model, renderer=object())
        task = {"id": "fixture", "source": str(self.source), "source_sha256": sha(self.source),
                "request": "Make it blue.", "max_generations": 1,
                "execution": {"mode": "live", "renderer": {"backend": "fixture"}}}
        service.submit(task)
        job = q.claim("llm", "fixture-owner")
        result = service(job, self.root / "service/job-test")
        self.assertEqual(result["state"]["config"]["workflow"], "creative_loop_v1")
        self.assertEqual(result["state"]["config"]["completion_mode"], "delivery")
        self.assertEqual(result["state"]["status"], "waiting_tool")

    def test_paratera_wire_contract_has_no_model_fallback_or_gpt_options(self):
        with patch.dict("os.environ", {"LHA_PARATERA_API_KEY": "fixture-credential", "LHA_EVAL_MODEL": "another-model"}):
            client = ParateraJudge(base_url="https://llmapi.paratera.com/v1")
        with patch("evaluation.creative.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = io.BytesIO(json.dumps({
                "model": "GLM-5.3-Flash",
                "choices": [{"message": {"content": "{\"fixture\": true}"}}], "usage": {"total_tokens": 7}}).encode())
            self.assertEqual(client.predict_text(system_prompt="fixture", user_text="fixture", image_paths=[]), '{"fixture": true}')
            request = opener.return_value.open.call_args.args[0]
            body = json.loads(request.data)
            self.assertEqual(request.full_url, "https://llmapi.paratera.com/v1/chat/completions")
            self.assertEqual(body["model"], "GLM-5.3-Flash")
            self.assertEqual(set(body), {"model", "messages", "max_tokens"})
            self.assertNotIn("fixture-credential", request.data.decode())


if __name__ == "__main__":
    unittest.main()
