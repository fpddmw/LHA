"""Offline software checks only: synthetic media and scripted responses, no model/API calls."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness import PlannerHarness
from planner_harness.common import load, save
from planner_harness.knowledge import Knowledge
import test_planner_harness as fixtures
ScriptedModel = fixtures.ScriptedModel


def call(action, **arguments):
    return {"action": action, "arguments": arguments}


class LightweightTests(unittest.TestCase):
    def setUp(self):
        fixtures.Tests.setUp(self)
        self.library = self.root / "library"
        k = self.library / "knowledge"
        k.mkdir(parents=True)
        for name in ("README.md", "READING.md", "INTEGRATION.md"):
            (k / name).write_text("Fixture guidance.", encoding="utf-8")
        (k / "meaning.md").write_text("Fixture meaning guidance.", encoding="utf-8")
        save(k / "source-map.json", {"guides": [{"id": "meaning", "path": "knowledge/meaning.md", "title": "Meaning"}], "totals": {}})
        save(k / "entrances.json", {"meaning": {"use_for": "Find source relationships.", "scope": "Fixture only."}})
        self.h = PlannerHarness(self.root / "run", ScriptedModel([]), root=self.library)
        self.h.start(self.source, "A fixture request.", max_turns=0)
        self.h.state["videos"]["v1"] = {**self.h.video.info, "parent": "source", "prompt": "Fixture prompt."}

    tearDown = fixtures.Tests.tearDown

    def test_comparison_keeps_both_video_labels_times_and_reopens_images(self):
        result = self.h.operate(call("observe", video=["source", "v1"], start=.3, end=.7, count=3), "compare")
        self.assertEqual([o["video_id"] for o in result["observations"]], ["source", "v1"])
        for o in result["observations"]:
            self.assertEqual([f["timestamp_seconds"] for f in o["frames"]], [.3, .5, .7])
        text, images, mapping = self.h.context()
        self.assertEqual({m["video_id"] for m in mapping}, {"source", "v1"})
        self.assertIn("do not establish motion alignment", text)
        count = len(self.h.state["observations"])
        self.h.operate(call("observe", video="source", start=1, end=1.2, count=2), "later")
        self.h.operate(call("observe", observation=["compare-1", "compare-2"]), "reopen")
        self.assertEqual(len(self.h.state["observations"]), count + 1)
        self.assertEqual(self.h.context()[1], images)

    def test_new_candidate_overview_replaces_old_focus(self):
        self.h.operate(call("observe", video=["source", "v1"], count=2), "compare")
        latest = self.h.video.observe("result-v2", count=2)
        latest["video_id"] = "v2"
        self.h.state["observations"].append(latest)
        self.assertEqual({m["video_id"] for m in self.h.context()[2]}, {"source", "v2"})

    def test_unknown_video_and_changed_saved_images_fail_without_claiming_observations(self):
        before = copy.deepcopy(self.h.state["observations"])
        with self.assertRaisesRegex(ValueError, "available video"):
            self.h.operate(call("observe", video=["source", "missing"]), "bad")
        self.assertEqual(self.h.state["observations"], before)
        Path(before[0]["frames"][0]["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Recorded observation changed"):
            self.h.operate(call("observe", observation="overview"), "bad-reopen")

    def test_older_feedback_has_exact_summary_unknowns_and_full_paged_retrieval(self):
        old = {"video_id": "v1", "protocol": "lha-online-critic-v1", "usage": "online_feedback",
               "question": "Inspect the hand region.", "identity_map": {"candidate": "v1"},
               "outcome": {"findings": [{"id": "unknown", "verdict": "unknown", "claim": "Motion unresolved."}] +
                           [{"id": str(i), "verdict": "partial", "claim": "Detailed finding " + str(i)} for i in range(150)],
                           "unresolved": ["Fine motion unavailable."],
                           "comparisons": [{"against": "source", "unknowns": ["Identity remains uncertain."]}]},
               "feedback": {"summary": "A quoted summary.", "planner_feedback": "A detailed suggestion."}}
        self.h.state["evaluations"] = {"old": old, "latest": {**old, "video_id": "v2"}}
        before = json.dumps(self.h.state, sort_keys=True)
        payload = json.loads(self.h.context()[0])
        self.assertEqual(payload["evaluations"]["old"]["summary"], "A quoted summary.")
        self.assertEqual(payload["evaluations"]["old"]["question"], old["question"])
        self.assertEqual(payload["evaluations"]["old"]["identity_map"], old["identity_map"])
        self.assertEqual(payload["evaluations"]["old"]["unknown_findings"], old["outcome"]["findings"][:1])
        self.assertEqual(payload["evaluations"]["latest"], self.h.state["evaluations"]["latest"])
        lines, start = [], 1
        while start:
            result = self.h.operate(call("history", feedback="old", start_line=start), "history")
            lines.extend(line.split(": ", 1)[1] for line in result["text"].splitlines())
            start = result["next_line"]
        self.assertEqual(json.loads("\n".join(lines)), old)
        self.assertEqual(json.dumps(self.h.state, sort_keys=True), before)

    def test_inline_note_is_optional_and_can_be_replaced_without_workflow(self):
        self.h.operate({**call("video", id="v1"), "note": "A useful observed limitation."}, "with-note")
        self.assertEqual(json.loads(self.h.context()[0])["notes"], "A useful observed limitation.")
        self.h.operate(call("note", text="Updated interpretation.", append=False), "replace")
        self.assertEqual(self.h.state["notes"], "Updated interpretation.")
        result = self.h.operate(call("submit", prompt="Make the scene blue."), "minimal")
        self.assertTrue(result["accepted"])

    def test_compact_video_preserves_full_provenance_on_request(self):
        original = copy.deepcopy(self.h.state["videos"]["v1"])
        context = json.loads(self.h.context()[0])
        self.assertNotIn("prompt", context["videos"]["v1"])
        self.assertEqual(self.h.operate(call("video", id="v1"), "open"), original)
        self.assertNotIn("workspace", context)

    def test_legacy_run_keeps_full_context_and_saved_instructions(self):
        self.h.state["config"].pop("context_version")
        self.h.checkpoint()
        original_system = (self.h.output / "system-prompt.txt").read_text(encoding="utf-8")
        model = ScriptedModel([call("submit", prompt="A legacy continuation.")])
        resumed = PlannerHarness(self.h.output, model, root=self.library)
        resumed.resume(additional_turns=1)
        payload = json.loads(model.inputs[0]["user_text"])
        self.assertEqual(payload["videos"]["v1"]["prompt"], "Fixture prompt.")
        self.assertIn("workspace", payload)
        self.assertEqual(model.inputs[0]["system_prompt"], original_system)
        self.assertNotIn("context_version", resumed.state["config"])

    def test_entrance_descriptions_are_frozen_and_old_snapshots_do_not_import_new_descriptions(self):
        snapshot = self.h.output / "knowledge-snapshot.json"
        save(self.library / "knowledge/entrances.json", {"meaning": {"use_for": "Changed live entrance."}})
        frozen = Knowledge(self.library, snapshot)
        self.assertEqual(frozen.browse("meaning")["material"]["use_for"], "Find source relationships.")
        self.assertEqual(frozen.search("meaning")["matches"][0]["scope"], "Fixture only.")
        data = load(snapshot)
        data.pop("entrances")
        old = self.root / "old-snapshot.json"
        save(old, data)
        self.assertNotIn("use_for", Knowledge(self.library, old).browse("meaning")["material"])

    def test_compact_entrances_respect_an_existing_availability_filter(self):
        disabled = {"entrances": [], "guidance": "Knowledge unavailable in this fixture."}
        with patch.object(self.h.knowledge, "browse", return_value=disabled):
            self.assertEqual(self.h.knowledge.overview(), disabled)


if __name__ == "__main__":
    unittest.main(verbosity=2)
