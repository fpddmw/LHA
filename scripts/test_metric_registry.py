"""Registry/status/denominator tests. All judgments are synthetic, with zero model calls."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from evaluation.registry import METRICS, VERSION, SCORE_VERSION, DEFINITIONS, applicable, fingerprint, judgment_fingerprint, scoring_fingerprint, markdown, snapshot, spec
from evaluation.scoring import score, error_result, flat_metrics
from evaluation.aggregate import summarize, paired_difference, export_report
from evaluation.compat import canonical_result
from evaluation.protocol import freeze, write, read, validate_judgment
from evaluation.cli import evaluate_manifest
import test_evaluation as fixtures


class RegistryTests(unittest.TestCase):
    def card(self, source, *, style=True):
        card = fixtures.card_fixture()
        card.update(source_id=source, task_id=source + "__long", style_required=style)
        return freeze(card, "test-only")

    def record(self, source, *, style=True, unknown=False, failure=None):
        card = self.card(source, style=style)
        j = fixtures.judgment_fixture(card)
        if unknown: j["ratings"]["style"].update(score=None, status="unknown")
        r = error_result(card, {"status": "invalid" if failure == "missing_output" else "valid"}, "fixture", status=failure) if failure else score(card, j, role="final")
        return {"method": "fixture", "seed": 42, "result": r}

    def summary(self, rows, metric="style"):
        return summarize(rows, repeats=0)[0]["metrics"][metric]

    def test_registry_complete_and_strict(self):
        for name in METRICS:
            s = spec(name)
            for key in ("definition", "scale", "display_decimals", "calculation", "aggregation", "applicability", "evidence", "direction", "missing_policy"):
                self.assertIn(key, s)
        with self.assertRaises(KeyError): spec("unknown_column")
        self.assertNotEqual(spec("preserve_time")["definition"], spec("temporal_coherence")["definition"])

    def test_native_score_uses_unit_interval_and_retains_raw_status(self):
        r = self.record("a", style=False)["result"]
        self.assertEqual(r["scoring_version"], SCORE_VERSION)
        self.assertEqual(r["semantic_scale"], "unit_interval")
        self.assertEqual(flat_metrics(r)["edit"], 1)
        self.assertEqual(r["rating_status"]["style"], "not_applicable")
        self.assertEqual(r["rating_status"]["relative_originality"], "not_applicable")
        self.assertEqual(r["metric_registry_sha256"], fingerprint())
        self.assertEqual(canonical_result(r), r)

    def test_unknown_na_error_have_different_denominators_and_counts(self):
        rows = [self.record("a", style=False), self.record("b"), self.record("c", unknown=True), self.record("d", failure="evaluation_error")]
        stats = self.summary(rows)
        self.assertEqual((stats["n_sources"], stats["applicable_sources"], stats["total_sources"]), (1, 3, 4))
        self.assertEqual(stats["missing_sources"], 2)
        self.assertEqual(stats["observation_counts"]["unknown"], 1)
        self.assertEqual(stats["observation_counts"]["not_applicable"], 1)
        self.assertEqual(stats["observation_counts"]["evaluation_error"], 1)
        self.assertAlmostEqual(stats["coverage_percent"], 100/3)
        self.assertEqual(stats["mean"], 3.7)

    def test_all_na_is_not_missing(self):
        stats = self.summary([self.record("a", style=False), self.record("b", style=False)])
        self.assertEqual((stats["n_sources"], stats["applicable_sources"], stats["missing_sources"]), (0, 0, 0))
        self.assertEqual(stats["not_applicable_sources"], 2)
        self.assertIsNone(stats["coverage_percent"])

    def test_population_bounds_include_unknown_sources(self):
        rows = [self.record(str(n)) for n in range(10)]
        for i, row in enumerate(rows):
            r = row["result"]
            r["semantic"]["edit"].update(score=.9 if i < 8 else None, lower=.9 if i < 8 else 0, upper=.9 if i < 8 else 1,
                                           status="scored" if i < 8 else "unknown")
            r["metric_status"]["edit"] = "scored" if i < 8 else "unknown"
        stats = self.summary(rows, "edit")
        self.assertAlmostEqual(stats["mean"], .9)
        self.assertAlmostEqual(stats["population_lower"], .72)
        self.assertAlmostEqual(stats["population_upper"], .92)
        self.assertEqual(stats["coverage_percent"], 80)

    def test_failure_does_not_fabricate_evidence_unknowns(self):
        r = self.record("a", failure="missing_output")["result"]
        self.assertEqual(r["success"], "fail")
        self.assertEqual(r["metric_status"]["edit"], "missing_output")
        self.assertEqual(r["semantic"]["edit"]["unknown"], 0)
        self.assertGreater(r["semantic"]["edit"]["unassessed_items"], 0)
        self.assertEqual(self.summary([{"method": "m", "seed": 1, "result": r}], "edit")["observation_counts"]["unknown"], 0)

    def test_evaluation_error_has_no_fake_judgment_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root / "card.json", self.card("a"))
            (root / "video.mp4").write_bytes(b"synthetic transport failure fixture")
            with patch("evaluation.cli.prepare", return_value={"delivery": {"status": "valid"}}), patch("evaluation.cli.judge", side_effect=RuntimeError("transport fixture")):
                rows = evaluate_manifest([{"case_id": "case", "method": "m", "seed": 1, "card": "card.json", "output_video": "video.mp4"}], root / "run", root, None)
            self.assertFalse((root / "run/case/judgment.json").exists())
            self.assertEqual(rows[0]["result"]["evaluation_status"], "evaluation_error")
            self.assertEqual(rows[0]["result"]["delivery"], "valid")

    def test_unknown_seed_keeps_source_in_applicable_denominator(self):
        a = self.record("a"); b = copy.deepcopy(a); b["seed"] = 43
        b["result"]["ratings"]["style"] = None
        b["result"]["rating_status"]["style"] = b["result"]["metric_status"]["style"] = "unknown"
        stats = self.summary([a, b])
        self.assertEqual((stats["n_sources"], stats["applicable_sources"]), (0, 1))
        self.assertIsNone(stats["mean"])

    def test_fixed_card_applicability_cannot_change_per_output(self):
        a = self.record("a"); b = copy.deepcopy(a); b["method"] = "b"
        b["result"]["ratings"]["style"] = None
        b["result"]["rating_status"]["style"] = b["result"]["metric_status"]["style"] = "not_applicable"
        with self.assertRaisesRegex(ValueError, "Applicability"):
            summarize([a, b])
        card = self.card("a"); j = fixtures.judgment_fixture(card)
        j["ratings"]["style"].update(status="not_applicable", score=None)
        with self.assertRaisesRegex(ValueError, "applicability"):
            validate_judgment(card, j)

    def test_online_diagnostics_are_rejected_by_final_report(self):
        row = self.record("a"); row["result"]["evaluation_role"] = "online_feedback"
        with self.assertRaisesRegex(ValueError, "Online diagnostics"):
            summarize([row])

    def test_legacy_unrecoverable_null_is_not_guessed_to_be_na(self):
        r = self.record("a", unknown=True)["result"]
        for key in ("scoring_version", "semantic_scale", "metric_status", "rating_status"):
            r.pop(key)
        for part in r["semantic"].values():
            for field in ("score", "lower", "upper"):
                if part[field] is not None: part[field] *= 100
        r = canonical_result(r)
        self.assertEqual(r["rating_status"]["style"], "legacy_status_unavailable")
        self.assertEqual(r["semantic"]["edit"]["score"], 1)
        self.assertEqual(canonical_result(r), r)

    def test_registry_revision_is_bound_to_judgment(self):
        card = self.card("a"); j = fixtures.judgment_fixture(card)
        j["metric_registry_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "registry revision"):
            score(card, j)
        row = self.record("a"); row["result"]["metric_registry_sha256"] = "different"
        row["result"].pop("scoring_contract_sha256")
        with self.assertRaisesRegex(ValueError, "registry revision"):
            summarize([row])

    def test_explicit_unit_scale_survives_a_missing_version(self):
        r = self.record("a")["result"]
        r.pop("scoring_version")
        self.assertEqual(canonical_result(r)["semantic"]["edit"]["score"], 1)
        r["reporting"] = {"semantic_score_scale": "legacy_0_100"}
        with self.assertRaisesRegex(ValueError, "Conflicting semantic"):
            canonical_result(r)

    def test_display_only_changes_reuse_raw_judgment_and_scores(self):
        card = self.card("a"); j = fixtures.judgment_fixture(card)
        j.update(metric_registry_sha256=fingerprint(), judgment_contract_sha256=judgment_fingerprint())
        row = self.record("a")
        raw_hash, calc_hash, full_hash = judgment_fingerprint(), scoring_fingerprint(), fingerprint()
        with patch.dict(DEFINITIONS["style"], {"display_decimals": 2, "label": "临时显示名称"}):
            self.assertNotEqual(fingerprint(), full_hash)
            self.assertEqual(judgment_fingerprint(), raw_hash)
            self.assertEqual(scoring_fingerprint(), calc_hash)
            self.assertEqual(score(card, j)["ratings"]["style"], 3.7)
            self.assertEqual(summarize([row], repeats=0)[0]["metrics"]["style"]["mean"], 3.7)

    def test_docs_are_generated_from_actual_registry(self):
        self.assertEqual((ROOT / "docs/evaluation-metrics.md").read_text(encoding="utf-8"), markdown())


if __name__ == "__main__":
    unittest.main()
