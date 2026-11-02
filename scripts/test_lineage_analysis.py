"""Offline checks of comparable lineage measurements and historical evidence."""
import copy
import sys
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.lineage import analyze, control_plan
from planner_harness.execution import signature


def state():
    data = {"request": {"text": "Change the room, preserve people."}, "videos": {"source": {}},
            "jobs": {}, "evaluations": {}}
    for key, parent, seconds in [("v1", "source", 10), ("v2", "v1", None), ("v3", "source", 12)]:
        data["videos"][key] = {"parent": parent, "job_id": key, "execution": {"generation_seconds": seconds}}
        data["jobs"][key] = {"payload": {"input_id": parent, "prompt": "Blue room.", "renderer": {"seed": 42}}}
    return data


class LineageTests(unittest.TestCase):
    def test_historical_feedback_keeps_qualitative_scale_and_coverage(self):
        data = state()
        for key, verdict in [("v1", "pass"), ("v2", "unknown")]:
            data["evaluations"][key] = {"video_id": key, "protocol": "historic-rsi",
                "outcome": {"summary": key, "requirements_sha256": "same-requirements",
                    "requirement_verdicts": [{"id": "faces", "verdict": verdict,
                        "evidence": "Saved finding", "claim_scope": "local", "temporal_coverage": {"fraction": .5}}]}}
        result = analyze(data)
        change = result["parent_child_changes"][0]["assessment_difference"]
        self.assertEqual(change["score_deltas"], {})
        self.assertEqual(change["requirement_transitions"][0]["right"], "unknown")
        self.assertEqual(change["requirement_transitions"][0]["right_coverage"], {"fraction": .5})

    def test_same_profile_scores_have_paired_deltas_and_evidence(self):
        data = state()
        for key, score in [("v1", 3), ("v2", 1)]:
            data["evaluations"][key] = {"video_id": key, "protocol": "current", "profile_sha256": "a",
                "report": {"main_scores": {"preservation": {"status": "scored", "score": score, "evidence_refs": [key]}}}}
        change = analyze(data)["parent_child_changes"][0]["assessment_difference"]
        self.assertEqual(change["score_deltas"]["preservation"]["delta"], -2)
        self.assertEqual(change["score_deltas"]["preservation"]["right_evidence_refs"], ["v2"])
        data["evaluations"]["v2"]["profile_sha256"] = "b"
        self.assertEqual(analyze(data)["parent_child_changes"][0]["assessment_difference"]["status"], "unavailable")

    def test_multiple_reports_and_changed_requirement_contract_do_not_pick_a_result(self):
        data = state()
        for key, version in [("v1", "old"), ("v2", "new")]:
            data["evaluations"][key] = {"video_id": key, "protocol": "historic",
                "outcome": {"requirements_sha256": version, "requirement_verdicts": [{"id": "x", "verdict": "pass"}]}}
        self.assertEqual(analyze(data)["parent_child_changes"][0]["assessment_difference"]["requirement_transitions"], [])
        data["evaluations"]["extra"] = copy.deepcopy(data["evaluations"]["v2"])
        self.assertEqual(analyze(data)["parent_child_changes"][0]["assessment_difference"]["status"], "unavailable")

    def test_ancestry_cost_retains_unknown_and_excludes_unrelated_branches(self):
        row = next(r for r in analyze(state())["candidates"] if r["candidate"] == "v2")
        self.assertEqual(row["ancestry_cost"]["known_generation_seconds"], 10)
        self.assertEqual(row["ancestry_cost"]["unknown_generations"], 1)
        self.assertEqual(row["ancestry_cost"]["candidates"], ["v1", "v2"])

    def test_controls_need_same_seed_prompt_and_complete_renderer_settings(self):
        data = state()
        self.assertEqual(len(analyze(data)["matched_restart_controls"]), 2)
        data["jobs"]["v2"]["payload"]["renderer"].pop("seed")
        self.assertEqual(analyze(data)["matched_restart_controls"], [])
        with self.assertRaises(ValueError):
            control_plan(data, "v2")

    def test_control_intent_is_bound_and_does_not_mutate_history(self):
        data = state(); before = copy.deepcopy(data)
        plan = control_plan(data, "v2")
        self.assertEqual(data, before)
        self.assertEqual(plan["status"], "not_submitted")
        for row in plan["requests"]:
            request = row["request"]
            self.assertEqual(request["sha256"], signature({k: v for k, v in request.items() if k != "sha256"}))
            self.assertEqual(request["payload"]["renderer"], {"seed": 42})

    def test_cycles_and_signed_input_disagreement_are_rejected(self):
        data = state(); data["videos"]["v1"]["parent"] = "v2"
        with self.assertRaises(ValueError): analyze(data)
        data = state(); data["jobs"]["v2"]["payload"]["input_id"] = "source"
        with self.assertRaises(ValueError): analyze(data)

    def test_remote_paths_use_verified_local_media_without_reading_remote_roots(self):
        from analyze_lineage_cohort import local_media
        from planner_harness.common import sha
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); run = root / "run"
            media = run / "videos/v1/video.mp4"
            media.parent.mkdir(parents=True); media.write_bytes(b"test-media-identity")
            video = {"path": "/root/historical-host/videos/v1/video.mp4", "sha256": sha(media)}
            self.assertEqual(local_media(root, run, "v1", video, {}), media)
            video["sha256"] = "wrong"
            self.assertIsNone(local_media(root, run, "v1", video, {}))


if __name__ == "__main__":
    unittest.main()
