"""Reporting contract checks; fixtures and saved-data audit make zero model calls."""
import copy
import csv
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/eval")]
from evaluation.aggregate import export_report, paired_difference, summarize
from evaluation.cli import main
from evaluation.protocol import read, write
from evaluation.reporting import display, metric_spec, normalized_records, normalized_result
from evaluation.scoring import score
import test_evaluation as fixtures
from reexport_first_wave import primary_cohort


class ReportingTests(unittest.TestCase):
    def result(self, value=100, source="a", track="short", task=None):
        card = fixtures.card_fixture()
        r = score(card, fixtures.judgment_fixture(card))
        r.update(source_id=source, task_id=task or source + "__" + track, track=track)
        r["semantic"]["edit"].update(score=value, lower=value, upper=value)
        return r

    def rows(self):
        return [{"method": m, "renderer": "fixture", "seed": 42,
                 "result": self.result(value, source, track)}
                for m in ("direct", "planner")
                for source, track, value in (("a", "short", 0), ("b", "short", 100), ("c", "long", 100), ("d", "long", 100))]

    def cohort(self, rows):
        return [{"method": r["method"], "seed": r["seed"], **{k: r["result"][k] for k in ("source_id", "task_id", "track", "split")}} for r in rows]

    def test_legacy_normalization_and_idempotence(self):
        result = self.result(68.75)
        original = copy.deepcopy(result)
        norm = normalized_result(result)
        self.assertEqual(norm["semantic"]["edit"]["score"], .6875)
        self.assertEqual(display(.6875, "edit"), "0.69")
        self.assertEqual(norm["semantic"]["edit"]["coverage"], 100)
        self.assertEqual(norm, normalized_result(norm))
        self.assertEqual(result, original)
        self.assertEqual(norm["success"], original["success"])

    def test_unknown_bounds_and_proportions_preserved(self):
        r = self.result()
        r["semantic"]["edit"].update(score=None, lower=25, upper=75, complete_rate=None, coverage=50)
        norm = normalized_result(r)["semantic"]["edit"]
        self.assertIsNone(norm["score"])
        self.assertEqual((norm["lower"], norm["upper"], norm["coverage"]), (.25, .75, 50))
        self.assertIsNone(norm["complete_rate"])

    def test_rating_precision_is_display_only(self):
        self.assertEqual(display(3.64, "aesthetic_mean", aggregate=False), "3.6")
        self.assertEqual(display(3.7, "style", aggregate=False), "3.7")
        self.assertEqual(metric_spec("style", aggregate=False)["raw_step"], .1)
        self.assertFalse(metric_spec("style", aggregate=False)["computed_mean"])
        self.assertTrue(metric_spec("aesthetic_mean", aggregate=False)["computed_mean"])
        self.assertTrue(metric_spec("style")["computed_mean"])

    def test_overall_and_tracks_keep_four_sources_and_task_weight(self):
        rows = normalized_records(self.rows())
        summary = summarize(rows, include_overall=True, repeats=0)
        self.assertEqual(len(summary), 6)
        for method in ("direct", "planner"):
            panels = {p["track"]: p for p in summary if p["method"] == method}
            self.assertEqual(panels["all"]["track_task_counts"], {"long": 2, "short": 2})
            for track, n, expected in (("all", 4, .75), ("short", 2, .5), ("long", 2, 1)):
                self.assertEqual(panels[track]["metrics"]["edit"]["mean"], expected)
                self.assertEqual(panels[track]["metrics"]["edit"]["n_sources"], n)

    def test_missing_planned_case_keeps_denominator(self):
        all_rows = normalized_records(self.rows())
        plan = self.cohort(all_rows)
        rows = all_rows[1:]
        p = next(p for p in summarize(rows, include_overall=True, cohort=plan, repeats=0) if p["method"] == "direct" and p["track"] == "all")
        self.assertEqual((p["n_records"], p["expected_records"], p["missing_records"]), (3, 4, 1))
        self.assertEqual((p["metrics"]["edit"]["n_sources"], p["metrics"]["edit"]["total_sources"]), (3, 4))
        p = next(p for p in summarize([], include_overall=True, cohort=plan, repeats=0) if p["track"] == "all")
        self.assertEqual(p["expected_records"], 4)
        self.assertEqual(p["metrics"]["edit"]["missing_sources"], 4)

    def test_variants_and_seed_counts_do_not_inflate_source_weight(self):
        rows = [{"method": "m", "seed": seed, "result": self.result(v, "a", "short", task)}
                for seed, task, v in ((1, "a_short", 100), (2, "a_short", 100), (1, "a_variant", 0))]
        p = summarize(normalized_records(rows), repeats=0)[0]["metrics"]["edit"]
        self.assertEqual((p["mean"], p["n_sources"]), (.5, 1))

    def test_paired_overall_has_same_task_seed_and_missing_coverage(self):
        rows = normalized_records(self.rows())
        rows[-1]["result"]["semantic"]["edit"]["score"] = None
        panels = {p["track"]: p for p in paired_difference(rows, "planner", "direct", "edit", include_overall=True, repeats=0)}
        self.assertEqual(panels["all"]["total_sources"], 4)
        self.assertEqual(panels["all"]["missing_sources"], 1)
        self.assertEqual(panels["all"]["mean"], 0)

    def test_export_preserves_precision_and_machine_readable_units(self):
        rows = [{"method": "m", "seed": 1, "result": self.result(68.75)}]
        rows[0]["result"]["ratings"]["aesthetic_mean"] = 3.64
        with tempfile.TemporaryDirectory() as temp:
            export_report(rows, temp, repeats=0)
            path = Path(temp)
            data = read(path / "records.normalized.json")
            self.assertEqual(data[0]["result"]["ratings"]["aesthetic_mean"], 3.64)
            self.assertEqual(data[0]["result"]["semantic"]["edit"]["score"], .6875)
            meta = read(path / "metadata.json")["metrics"]
            self.assertEqual(meta["edit"]["scale"], [0, 1])
            self.assertEqual(meta["edit_coverage"]["unit"], "percent")
            with (path / "metrics.csv").open(encoding="utf-8-sig", newline="") as stream:
                csv_rows = list(csv.DictReader(stream))
            aesthetic = next(r for r in csv_rows if r["metric"] == "aesthetic_mean")
            self.assertEqual((aesthetic["mean"], aesthetic["display_mean"]), ("3.64", "3.6"))

    def test_mixed_or_unknown_scale_is_rejected_until_normalized(self):
        legacy = {"method": "m", "seed": 1, "result": self.result()}
        scaled = {"method": "m", "seed": 2, "result": normalized_result(self.result())}
        with self.assertRaisesRegex(ValueError, "mixed semantic"):
            summarize([legacy, scaled])
        self.assertEqual(len(summarize(normalized_records([legacy, scaled]))), 1)
        legacy["result"]["reporting"] = {"semantic_score_scale": "unknown"}
        with self.assertRaisesRegex(ValueError, "Unknown semantic"):
            normalized_result(legacy["result"])

    def test_compare_cli_uses_normalized_deltas_and_signed_scale(self):
        rows = self.rows()
        rows[4]["result"]["semantic"]["edit"].update(score=100, lower=100, upper=100)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            write(path / "records.json", rows)
            main(["compare", "--records", str(path / "records.json"), "--a", "planner", "--b", "direct", "--metric", "edit", "--out", str(path / "diff.json")])
            result = read(path / "diff.json")
            overall = next(r for r in result if r["track"] == "all")
            self.assertEqual(overall["mean"], .25)
            self.assertEqual(overall["metadata"]["scale"], [-1, 1])

    def test_declared_primary_selection_retains_track_and_excludes_variants(self):
        run = ROOT / "out/evaluation_runs/20261030_first_wave"
        if not run.exists():
            self.skipTest("Local saved first-wave records are not distributed as unit fixtures")
        selected, cohort = primary_cohort(run, read(run / "records.json"))
        self.assertEqual((len(selected), len(cohort)), (16, 16))
        self.assertEqual(len({r["result"]["source_id"] for r in selected}), 4)
        self.assertFalse(any("long_keep" in r["case_id"] or "source_control" in r["case_id"] for r in selected))
        self.assertEqual(sum(r["result"]["track"] == "short" for r in selected), 8)
        self.assertEqual(len({(r["renderer"], r["result"]["task_id"]) for r in selected}), 8)


if __name__ == "__main__":
    unittest.main()
