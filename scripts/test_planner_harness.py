"""Focused reliability checks; scripted responses are not live Planner evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import cv2
import numpy as np
from planner_harness import PlannerHarness
from planner_harness.common import load, save
from planner_harness.knowledge import Knowledge
from planner_harness.lock import RunLock
from planner_harness.video import Video


def final(sources=None):
    return {"action": "submit", "purpose": "Finish this test proposal", "arguments": {
        "understanding": "A synthetic test sequence.", "proposal": "A blue visual treatment.",
        "prompt": "Render the scene in blue.", "self_review": "The proposed color matches the test request.",
        "sources": sources or [], "unresolved": []}}


class ScriptedModel:
    model = "scripted-test-only"
    reasoning_effort = "none"

    def __init__(self, actions):
        self.actions, self.inputs = list(actions), []

    def predict_text(self, **kwargs):
        self.inputs.append(kwargs)
        action = self.actions.pop(0)
        if isinstance(action, Exception):
            raise action
        return json.dumps(action)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "input.avi"
        writer = cv2.VideoWriter(str(self.source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (80, 60))
        for index in range(20):
            writer.write(np.full((60, 80, 3), index * 10, dtype=np.uint8))
        writer.release()

    def tearDown(self):
        self.temp.cleanup()

    def harness(self, actions):
        self.model = ScriptedModel(actions)
        return PlannerHarness(self.root / "run", self.model)

    def test_complete_conversation_and_exact_handoff(self):
        h = self.harness([
            {"action": "read", "arguments": {"targets": [{"id": "opuscar-053"}]}, "workspace": {"summary": "Compare transparent pigment and paper."}},
            final([{"read_id": "read-0001", "use": "Use paper as the light region."}])])
        state = h.start(self.source, "Make it blue")
        self.assertEqual(state["status"], "complete")
        payload = json.loads(self.model.inputs[1]["user_text"])
        self.assertEqual(payload["workspace"]["summary"], "Compare transparent pigment and paper.")
        self.assertIn("Paper white", json.dumps(payload["recent_operations"]))
        self.assertEqual((h.output / "prompt.txt").read_text(), state["proposal"]["prompt"])
        self.assertEqual(load(h.output / "handoff.json")["prompt"], state["proposal"]["prompt"])
        self.assertEqual(state["renderer_submission"]["status"], "not_requested")

    def test_invalid_citation_is_returned_for_correction(self):
        h = self.harness([final([{"read_id": "invented", "use": "Unseen source"}]), final()])
        state = h.start(self.source, "Make it blue")
        self.assertFalse(state["submission_attempts"][0]["accepted"])
        self.assertTrue(state["submission_attempts"][1]["accepted"])

    def test_transport_resume_reuses_pending_turn(self):
        h = self.harness([RuntimeError("temporary transport failure")])
        with self.assertRaises(RuntimeError):
            h.start(self.source, "Make it blue")
        self.assertEqual(load(h.output / "state.json")["pending_event"], "event-0001")
        next_model = ScriptedModel([final()])
        resumed = PlannerHarness(h.output, next_model).resume()
        self.assertEqual(resumed["attempts"], 1)
        self.assertEqual(resumed["status"], "complete")
        self.assertEqual(self.model.inputs[0]["user_text"], next_model.inputs[0]["user_text"])

    def test_saved_response_recovered_without_second_model_call(self):
        h = self.harness([RuntimeError("interrupted after response")])
        with self.assertRaises(RuntimeError):
            h.start(self.source, "Make it blue")
        (h.output / "calls/event-0001/response.txt").write_text(json.dumps(final()))
        next_model = ScriptedModel([])
        resumed = PlannerHarness(h.output, next_model).resume()
        self.assertEqual(resumed["status"], "complete")
        self.assertEqual(next_model.inputs, [])

    def test_budget_and_source_change(self):
        h = self.harness([{"action": "workspace", "arguments": {}, "workspace": {"summary": "An unfinished proposal."}}])
        state = h.start(self.source, "Make it blue", max_turns=1)
        self.assertEqual(state["status"], "budget_exhausted")
        resumed = PlannerHarness(h.output, ScriptedModel([final()])).resume(additional_turns=1)
        self.assertEqual(resumed["workspace"]["summary"], "An unfinished proposal.")
        self.assertEqual(resumed["status"], "complete")

    def test_changed_source_blocks_resume(self):
        h = self.harness([RuntimeError("stop")])
        with self.assertRaises(RuntimeError):
            h.start(self.source, "Make it blue")
        state = load(h.output / "state.json")
        state["request"]["source"]["sha256"] = "changed"
        save(h.output / "state.json", state)
        with self.assertRaisesRegex(ValueError, "Source video changed"):
            PlannerHarness(h.output, ScriptedModel([])).resume()

    def test_knowledge_access_and_pagination(self):
        k = Knowledge(ROOT)
        for bad in ["../../etc/passwd", str(ROOT / "benchmark_data/all_samples.json"), "benchmark_data/all_samples.json"]:
            with self.assertRaises(ValueError):
                k.read(bad)
        first = k.read("opuscar-053")
        if first["next_line"]:
            second = k.read("opuscar-053", first["next_line"])
            self.assertEqual(second["start_line"], first["end_line"] + 1)
        self.assertTrue(k.search("transparent watercolor paper")["matches"])

    def test_observation_timing_and_crop(self):
        v = Video(self.source, self.root)
        observed = v.observe("detail", start=.3, end=.7, count=3, crop=[0, 0, .5, .5])
        self.assertEqual([f["frame_index"] for f in observed["frames"]], [3, 5, 7])
        pixels = cv2.imread(observed["frames"][0]["path"])
        self.assertEqual(pixels.shape[:2], (30, 40))
        with self.assertRaises(ValueError):
            v.observe("bad", start=2)

    def test_workspace_cycle_and_unknown_operation_recovery(self):
        h = self.harness([{"action": "workspace", "workspace": {"nodes": [{"id": "a", "parent": "b"}, {"id": "b", "parent": "a"}]}}, {"action": "render", "arguments": {}}, final()])
        state = h.start(self.source, "Make it blue")
        self.assertEqual([e["status"] for e in state["events"]], ["operation_error", "operation_error", "ok"])
        self.assertEqual(state["workspace"]["nodes"], {})

    def test_context_budget_stops_without_truncation(self):
        h = self.harness([])
        state = h.start(self.source, "Make it blue", max_context_chars=10)
        self.assertEqual(state["status"], "context_limit")
        self.assertEqual(state["attempts"], 0)

    def test_exclusive_run_lock(self):
        with RunLock(self.root / "locked"):
            with self.assertRaises(RuntimeError):
                with RunLock(self.root / "locked"):
                    pass


if __name__ == "__main__":
    unittest.main()
