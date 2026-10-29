"""Focused continuous-task checks using explicitly scripted models and replay media."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness import PlannerHarness
from planner_harness.common import load, save, sha
import test_planner_harness as legacy
ScriptedModel = legacy.ScriptedModel


def call(action, **arguments):
    return {"action": action, "arguments": arguments}


class ContinuousTests(unittest.TestCase):
    setUp = legacy.Tests.setUp
    tearDown = legacy.Tests.tearDown

    def start(self, actions, **kwargs):
        self.model = ScriptedModel(actions)
        self.h = PlannerHarness(self.root / "run", self.model)
        return self.h.start(self.source, "Make the scene blue.", mode="loop", execution={"mode": "replay", "renderer": {}}, **kwargs)

    def respond(self, failed=False):
        state = load(self.h.output / "state.json")
        job = state["jobs"][state["pending_tool"]]
        p = job["payload"]
        response = {"request_sha256": job["sha256"], "mode": "replay", "status": "failed" if failed else "complete"}
        if failed:
            response["error"] = "Scripted worker failure"
        else:
            response["payload"] = {"video": {"path": str(self.source), "sha256": sha(self.source)},
                "replay_provenance": "Synthetic test video; this prompt was not rendered.",
                "execution": {"requested_prompt": p["prompt"], "effective_prompt": p["prompt"], "input_sha256": p["input"]["sha256"]}}
        save(self.h.output / "jobs" / job["id"] / "response.json", response)

    def resume(self, actions):
        self.model = ScriptedModel(actions)
        self.h = PlannerHarness(self.h.output, self.model)
        return self.h.resume()

    def test_minimal_plan_submission_has_no_required_report_form(self):
        h = PlannerHarness(self.root / "minimal", ScriptedModel([call("submit", prompt="Make the scene blue.")]))
        state = h.start(self.source, "Make it blue")
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["proposal"]["prompt"], "Make the scene blue.")
        self.assertEqual(state["proposal"]["self_review"], "")

    def test_continuity_arbitrary_candidate_and_no_acceptance_stage(self):
        state = self.start([call("read", targets=[{"id": "choose-editing-input"}]),
                            call("note", text="A useful direction remains open."),
                            call("generate", input_video="source", prompt="Make it blue.")])
        self.assertEqual(state["status"], "waiting_tool")
        self.respond()
        state = self.resume([call("generate", input_video="v1", prompt="Add a subtle warm highlight.")])
        context = json.loads(self.model.inputs[0]["user_text"])
        self.assertIn("direction remains open", context["notes"])
        self.assertIn("read-0001", context["read_receipts"])
        self.assertEqual(state["videos"]["v1"]["parent"], "source")
        self.respond()
        self.resume([call("generate", input_video="v1", prompt="Try a muted highlight instead.")])
        self.respond()
        state = self.resume([call("finish", video="v2", message="Use this earlier alternative.")])
        self.assertEqual(state["videos"]["v2"]["parent"], "v1")
        self.assertEqual(state["videos"]["v3"]["parent"], "v1")
        self.assertEqual(state["final"]["video"], "v2")
        self.assertNotIn("incumbent", state)

    def test_waiting_does_not_call_model_or_duplicate_job(self):
        state = self.start([call("generate", input_video="source", prompt="Blue.")])
        pending, attempts = state["pending_tool"], state["attempts"]
        state = self.resume([])
        self.assertEqual(state["pending_tool"], pending)
        self.assertEqual(state["attempts"], attempts)
        self.assertEqual(state["generation_requests"], 1)
        self.assertEqual(self.model.inputs, [])

    def test_failed_generation_returns_to_same_planner(self):
        self.start([call("generate", input_video="source", prompt="Blue.")])
        self.respond(failed=True)
        state = self.resume([call("finish", message="No generated result is available.")])
        self.assertEqual(set(state["videos"]), {"source"})
        self.assertIn("Scripted worker failure", self.model.inputs[0]["user_text"])
        self.assertEqual(state["final"]["outcome"], "stopped_without_video")

    def test_generation_budget_and_missing_evaluator_are_visible(self):
        state = self.start([call("generate", input_video="source", prompt="Blue."),
                            call("evaluate", video="source"), call("finish", message="Execution is unavailable.")], max_generations=0)
        self.assertEqual(state["events"][0]["result"]["status"], "limit_reached")
        self.assertEqual(state["events"][1]["result"]["status"], "unavailable")
        self.assertEqual(state["generation_requests"], 0)

    def test_snapshot_survives_shared_material_revision(self):
        library = self.root / "library"
        k = library / "knowledge"; k.mkdir(parents=True)
        for name in ("READING.md", "README.md", "INTEGRATION.md"):
            (k / name).write_text("Test reading guidance.", encoding="utf-8")
        (k / "topic.md").write_text("Version one advice.", encoding="utf-8")
        save(k / "source-map.json", {"guides": [{"id": "topic", "path": "knowledge/topic.md"}], "totals": {}})
        output = self.root / "snapshot-run"
        h = PlannerHarness(output, ScriptedModel([call("read", targets=[{"id": "topic"}]), RuntimeError("pause")]), root=library)
        with self.assertRaises(RuntimeError):
            h.start(self.source, "Test version isolation")
        (k / "topic.md").write_text("Version two advice.", encoding="utf-8")
        save(k / "source-map.json", {"guides": [{"id": "topic", "path": "knowledge/topic.md"}], "totals": {}, "new_version": 2})
        model = ScriptedModel([call("read", targets=[{"id": "topic"}]), call("submit", prompt="Blue.", sources=[{"read_id":"read-0001","use":"Use the recorded advice."}])])
        state = PlannerHarness(output, model, root=library).resume()
        material = state["events"][1]["result"]["materials"][0]["text"]
        self.assertIn("Version one", material)
        self.assertEqual(state["status"], "complete")


if __name__ == "__main__":
    unittest.main(verbosity=2)
