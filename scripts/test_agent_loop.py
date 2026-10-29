"""Local integration checks; scripted models and replay videos are test fixtures."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import cv2
import numpy as np
from agent_loop import AgentLoop
from agent_loop.core import digest, publish_response
from planner_harness import PlannerHarness
from planner_harness.common import load, save, sha
from test_planner_harness import ScriptedModel, final


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "input.avi"
        writer = cv2.VideoWriter(str(self.source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (80, 60))
        for index in range(20):
            writer.write(np.full((60, 80, 3), index * 10, dtype=np.uint8))
        writer.release()
        self.initial = self.root / "initial"
        PlannerHarness(self.initial, ScriptedModel([final()])).start(self.source, "Make it blue")
        self.loop = AgentLoop(self.root / "loop")
        self.loop.initialize(self.initial, {"backend": "fixture", "settings": {"seed": 42},
                                          "output": {"frames": 20, "fps": 10}}, mode="replay", max_candidates=3, max_render_jobs=4)

    def tearDown(self):
        self.temp.cleanup()

    def respond(self, payload, **extra):
        state = load(self.loop.output / "state.json")
        response = {"request_sha256": state["job"]["sha256"], "mode": state["mode"], "status": "complete", "payload": payload, **extra}
        publish_response(self.loop.output, response)
        return self.loop.advance()

    def render_payload(self):
        request = load(self.loop.output / "state.json")["job"]["payload"]
        return {"video": {"path": str(self.source), "sha256": sha(self.source)},
                "execution": {"backend": "fixture", "settings": {"seed": 42},
                              "requested_prompt": request["prompt"], "effective_prompt": request["prompt"],
                              "prompt_transforms": [], "input_sha256": request["input_video"]["sha256"],
                              "preflight": "not_run"},
                "replay_provenance": "Synthetic source video reused for state-machine testing; no rendering occurred."}

    def render(self):
        return self.respond(self.render_payload())

    def evaluate(self):
        return self.respond({"protocol": {"id": "fixture-only", "version": "1"},
                             "findings": [{"item": "example", "judgment": "unknown", "evidence": []}],
                             "metrics": {"future_metric": {"value": None, "unit": "undefined"}},
                             "uncertainties": ["Synthetic replay has no measured visual outcome."]})

    def decide(self, selection="accept", action="revise", input_id="original", mode="full"):
        state = load(self.loop.output / "state.json")
        return self.respond({"policy": {"id": "scripted-test", "version": "1"}, "selection": selection,
                             "next_action": action, "input": input_id, "instruction_mode": mode,
                             "reason": "Exercise the transition; this is not a quality finding.",
                             "evaluation_sha256": digest(state["candidates"][-1]["evaluation"])})

    def test_pending_jobs_are_stable_and_missing_evaluation_waits(self):
        job = self.loop.state["job"]
        for _ in range(3):
            self.assertEqual(AgentLoop(self.loop.output).advance()["job"], job)
        self.assertEqual(self.render()["status"], "awaiting_evaluation")
        state = self.loop.advance()
        self.assertEqual(state["status"], "awaiting_evaluation")
        self.assertIsNone(state["incumbent"])
        self.assertNotIn("evaluation", state["candidates"][0])

    def test_unknown_metrics_and_separate_selection(self):
        self.render()
        state = self.evaluate()
        self.assertEqual(state["status"], "awaiting_decision")
        self.assertIsNone(state["candidates"][0]["evaluation"]["metrics"]["future_metric"]["value"])
        self.assertIsNone(state["incumbent"])
        state = self.decide(selection="undecided", action="stop")
        self.assertEqual(state["status"], "stopped")
        self.assertIsNone(state["incumbent"])

    def test_accept_parent_reject_rollback_and_source_restart(self):
        self.render(); self.evaluate()
        self.decide(input_id="incumbent", mode="incremental")
        model = ScriptedModel([
            {"action": "observe", "arguments": {"video_id": "candidate", "count": 2}},
            {"action": "read", "arguments": {"targets": [{"id": "media"}]}},
            final([{"read_id": "read-0001", "use": "Read the media guide during this child run."}])])
        state = self.loop.revise(model)
        self.assertEqual(state["status"], "awaiting_render")
        self.assertEqual(state["job"]["payload"]["input_id"], "candidate-001")
        self.assertEqual(state["job"]["payload"]["instruction_mode"], "incremental")
        context = json.loads(model.inputs[0]["user_text"])
        self.assertEqual(context["revision_context"]["next_input"]["id"], "candidate-001")
        self.assertEqual({i.get("video_id") for i in context["attached_images_in_order"]}, {"original", "candidate"})
        self.render(); self.evaluate()
        state = self.decide(selection="reject", input_id="original")
        self.assertEqual(state["incumbent"], "candidate-001")
        model2 = ScriptedModel([final()])
        state = self.loop.revise(model2)
        self.assertEqual(state["job"]["payload"]["input_id"], "original")
        context2 = json.loads(model2.inputs[0]["user_text"])["revision_context"]
        self.assertEqual(set(context2["videos"]), {"candidate", "incumbent"})
        self.assertEqual(context2["incumbent"]["id"], "candidate-001")
        self.render(); self.evaluate()
        state = self.decide(selection="reject", action="revise")
        self.assertEqual(state["status"], "stopped")
        self.assertEqual(state["stop_reason"], "candidate_or_render_budget")
        self.assertEqual(state["incumbent"], "candidate-001")

    def test_reject_cannot_create_an_incumbent(self):
        self.render(); self.evaluate()
        with self.assertRaisesRegex(ValueError, "No accepted incumbent"):
            self.decide(selection="reject", input_id="incumbent")
        self.assertIsNone(load(self.loop.output / "state.json")["incumbent"])

    def test_stale_response_and_replay_mode_rejected(self):
        response = {"request_sha256": "stale", "mode": "replay", "status": "complete", "payload": {}}
        with self.assertRaises(ValueError):
            publish_response(self.loop.output, response)
        response["request_sha256"] = self.loop.state["job"]["sha256"]
        response["mode"] = "live"
        with self.assertRaises(ValueError):
            publish_response(self.loop.output, response)

    def test_exact_prompt_and_configuration_are_required(self):
        bad = self.render_payload()
        bad["execution"]["requested_prompt"] += " Unrequested template text."
        with self.assertRaisesRegex(ValueError, "requested prompt/input"):
            self.respond(bad)
        self.assertEqual(load(self.loop.output / "state.json")["status"], "failed")
        self.assertEqual(self.loop.retry("Repair the adapter receipt")["status"], "awaiting_render")

    def test_output_contract_and_decode_checked(self):
        short = self.root / "short.avi"
        writer = cv2.VideoWriter(str(short), cv2.VideoWriter_fourcc(*"MJPG"), 10, (80, 60))
        writer.write(np.zeros((60, 80, 3), dtype=np.uint8))
        writer.release()
        payload = self.render_payload()
        payload["video"] = {"path": str(short), "sha256": sha(short)}
        with self.assertRaisesRegex(ValueError, "frame count/FPS"):
            self.respond(payload)
        self.assertFalse((self.loop.output / "candidates/candidate-001/video.avi").exists())
        self.loop.retry("A valid full-length fixture is now available")
        self.assertEqual(self.render()["status"], "awaiting_evaluation")

    def test_failed_job_retry_has_new_identity_without_automatic_retry(self):
        before = self.loop.state["job"]["id"]
        state = self.respond({}, status="failed", error="Fixture transport failed")
        self.assertEqual(state["status"], "failed")
        self.assertEqual(self.loop.advance()["job"]["id"], before)
        state = self.loop.retry("Transport restored; explicit fixture retry")
        self.assertNotEqual(state["job"]["id"], before)
        self.assertEqual(state["render_jobs"], 2)

    def test_missing_outbox_recreated_after_checkpoint(self):
        request = self.loop.state["job"]
        path = self.loop.output / "jobs" / request["id"] / "request.json"
        path.unlink()
        self.loop.advance()
        self.assertEqual(load(path), request)
        self.assertEqual(self.loop.state["render_jobs"], 1)

    def test_revision_recovers_pending_call_without_replaying_generation(self):
        self.render(); self.evaluate(); self.decide()
        broken = ScriptedModel([RuntimeError("Interrupted model transport")])
        with self.assertRaisesRegex(RuntimeError, "Interrupted"):
            self.loop.revise(broken)
        resumed = ScriptedModel([final()])
        state = AgentLoop(self.loop.output).revise(resumed)
        self.assertEqual(broken.inputs[0]["user_text"], resumed.inputs[0]["user_text"])
        self.assertEqual(state["render_jobs"], 2)
        self.assertEqual(state["status"], "awaiting_render")
        self.assertEqual(load(self.initial / "state.json")["attempts"], 1)

    def test_collected_video_tampering_is_detected(self):
        self.render()
        video = Path(self.loop.state["candidates"][0]["video"]["path"])
        video.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "candidate video changed"):
            self.loop.advance()

    def test_live_preflight_requires_actual_tokenizer_receipt(self):
        live = AgentLoop(self.root / "live")
        live.initialize(self.initial, {"backend": "fixture", "settings": {"seed": 42},
                                      "output": {"frames": 20, "fps": 10}})
        self.loop = live
        with self.assertRaisesRegex(ValueError, "successful renderer preflight"):
            self.render()


if __name__ == "__main__":
    unittest.main(verbosity=2)
