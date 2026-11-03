"""Current final judge, summaries and cache namespaces support tenth-step ratings."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import test_low_high as fixtures
from test_unified_results import Fixture
from evaluation import low_high, low_high_summary, registry, task_metrics
from evaluation.creative import judge_candidate
from evaluation.validation import validate_report
from experiments import results
from planner_harness.common import load, save, sha
from planner_harness.execution import signature


class DecimalJudge(fixtures.Judge):
    def predict_text(self, **kwargs):
        value = json.loads(super().predict_text(**kwargs))
        for row in value.get("main_scores", {}).values():
            if row["status"] == "scored":
                row["score"] = 3.7
        for row in value.get("specialties", {}).values():
            if row["status"] == "scored":
                row["score"] = 2.3
        for index, row in enumerate(value.get("aesthetics", {}).values()):
            if row["status"] == "scored":
                row["score"] = round(3 + index / 10, 1)
        return json.dumps(value)


class RatingTests(unittest.TestCase):
    def test_full_range_and_invalid_numbers(self):
        for value in [0, 4, *(i / 10 for i in range(41))]:
            self.assertEqual(registry.validate_low_high_rating(value), value)
        for value in (True, False, None, "3.7", -0.1, 4.1, 3.11, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                registry.validate_low_high_rating(value)
        self.assertEqual(registry.RATING_SCALE, (1.0, 4.0))  # Historical card contract stays separate.
        self.assertEqual(registry.LOW_HIGH_RATING_SCALE, (0.0, 4.0))


class FinalPathTests(unittest.TestCase):
    setUp, tearDown = fixtures.Tests.setUp, fixtures.Tests.tearDown

    def test_actual_final_entry_keeps_decimal_main_specialty_and_aesthetic_scores(self):
        for track in ("short", "long"):
            plan = low_high.freeze_plan({**fixtures.body(), "track": track}, self.request, self.source, self.root / track)
            judge, directory = DecimalJudge(), self.root / ("judge-" + track)
            result = judge_candidate(self.request, self.source, self.source, directory, model=judge, plan=plan)
            self.assertTrue(all(row["score"] == 3.7 for row in result["report"]["main_scores"].values()))
            self.assertEqual(result["main_projection"]["errors"], [])
            diagnostics = result["task_metrics"]
            self.assertEqual(diagnostics["field_projection"]["errors"], [])
            self.assertAlmostEqual(diagnostics["metrics"]["aesthetic_mean"]["score"], 3.2)
            self.assertEqual(diagnostics["metrics"]["style_realization"]["score"], 2.3 if track == "short" else None)
            task_metrics.verify(directory / "task-metrics", judge)
            packet = load(directory / "evidence/request.json")
            self.assertIn("0.1 steps", packet["system_prompt"])
            self.assertIn("recasting across worlds and media", packet["system_prompt"])
            self.assertIn("agreement with source timing or poses is not TC evidence", packet["system_prompt"])
            self.assertIn("0.1 steps", load(directory / "task-metrics/request.json")["system_prompt"])
            validate_report(result["report"], packet)
            old_packet, old_report = copy.deepcopy(packet), copy.deepcopy(result["report"])
            visible = json.loads(old_packet["user_text"])
            visible["protocol_id"] = old_report["protocol_id"] = "lha-low-high-final-v4"
            old_packet["user_text"] = json.dumps(visible)
            with self.assertRaisesRegex(ValueError, "identity"):
                validate_report(old_report, old_packet)
            row = {"source_id": "source", "sample_id": "sample", "length": track,
                   "judge": judge.model, "variant": "direct", "result": result}
            summary = low_high_summary.summarize([row])
            self.assertEqual(summary["groups"][0]["dimensions"]["instruction_adherence"]["mean_source_macro"], 3.7)
            before = copy.deepcopy(result)
            before["report"]["main_scores"]["instruction_adherence"]["score"] = 3.4
            paired = low_high_summary.paired([{**row, "before": before, "after": result}])
            self.assertAlmostEqual(paired[0]["dimensions"]["instruction_adherence"]["mean_delta_source_macro"], .3)
            original = sha(directory / "judgment.json")
            calls = len(judge.calls)
            judge_candidate(self.request, self.source, self.source, directory, model=judge, plan=plan)
            self.assertEqual(len(judge.calls), calls)
            self.assertEqual(sha(directory / "judgment.json"), original)


class CacheTests(Fixture):
    def test_old_integer_session_is_retained_and_new_scores_use_a_fresh_namespace(self):
        results.import_video(self.repo, self.registry, self.row())
        current = low_high.profile()
        old = copy.deepcopy(current)
        old["protocol_id"] = "lha-low-high-final-v3"
        old["policy"]["single_score"] = "integer 0..4; missing=null"
        old["sha256"] = signature({k: v for k, v in old.items() if k != "sha256"})
        with patch.object(low_high, "profile", return_value=old):
            previous = results.prepare_evaluation(self.repo, self.registry, evaluation_id="integer-fixture")
        path = self.registry / "evaluations/integer-fixture/scores/old.json"
        save(path, {"protocol_id": old["protocol_id"], "score": 3})
        checksum = sha(path)
        self.assertIsNone(results.current_evaluation(self.registry))
        fresh = results.prepare_evaluation(self.repo, self.registry, evaluation_id="tenths-fixture")
        self.assertNotEqual(previous["protocol_sha256"], fresh["protocol_sha256"])
        self.assertEqual(fresh["protocol_sha256"], current["sha256"])
        directory, active = results.current_evaluation(self.registry)
        self.assertEqual(active["evaluation_id"], "tenths-fixture")
        self.assertFalse((directory / "scores/old.json").exists())
        self.assertEqual(sha(path), checksum)


if __name__ == "__main__":
    unittest.main()
