"""Behavioral tests. Synthetic scores/videos are fixtures, never benchmark results."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from evaluation import PROTOCOL
from evaluation.aggregate import export_report, paired_difference, summarize
from evaluation.cli import evaluate_manifest, scaffold
from evaluation.features import adjacent_cosine
from evaluation.judges import cached_call, covers_interval, judge, pairwise, unknown_judgment
from evaluation.loop import analyze, transition
from evaluation.media import delivery_status, nearest, prepare
from evaluation.protocol import file_hash, freeze, read, signature, validate_card, validate_judgment, write
from evaluation.reliability import agreement, preferences
from evaluation.scoring import score


def card_fixture():
    def item(id, mandatory=True, sequence=False):
        return {"id": id, "text": id, "mandatory": mandatory, "temporal": sequence,
                "evidence": "sequence" if sequence else "frames", "partial_rule": "Some requested extent is met"}
    return freeze({"protocol": PROTOCOL, "task_id": "fixture__long", "source_id": "fixture",
                   "source_video": "source.mp4", "source_sha256": "a" * 64, "requirement": "Turn the shirt blue; preserve identity and action",
                   "track": "long", "split": "development", "style_family": "fixture", "status": "draft",
                   "creativity": "none", "allowed_changes": ["shirt color"], "style_required": False,
                   "duration_seconds": 2.0, "groups": [
                       {"id": "e1", "kind": "edit", "items": [item("shirt")]},
                       {"id": "e2", "kind": "edit", "items": [item("x", False), item("y", False), item("z", False)]},
                       {"id": "p1", "kind": "preserve_core", "items": [item("identity"), item("action", sequence=True)]},
                       {"id": "p2", "kind": "preserve_detail", "items": [item("button", False)]}]}, "synthetic-test-fixture")


def judgment_fixture(card=None):
    card = card or card_fixture()
    j = unknown_judgment(card, {"status": "valid", "reason": "synthetic fixture"}, "synthetic fixture")
    for row in j["items"]:
        row.update(label="pass", times_seconds=[0.1, 1.9], evidence_kind="sequence" if row["id"] == "action" else "frames")
    for r in j["ratings"].values():
        if r["status"] != "not_applicable":
            r.update(status="scored", score=3.7)
    j["damage_review"] = "complete"
    return j


def label(judgment, item, value):
    next(r for r in judgment["items"] if r["id"] == item)["label"] = value


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.card = card_fixture()
        self.j = judgment_fixture(self.card)

    def test_decimals_are_preserved(self):
        result = score(self.card, self.j)
        self.assertAlmostEqual(result["ratings"]["aesthetic_mean"], 3.7)
        self.assertEqual(result["success"], "pass")

    def test_invalid_precision_rejected(self):
        self.j["ratings"]["color_texture"]["score"] = 3.77
        with self.assertRaisesRegex(ValueError, "0.1"):
            score(self.card, self.j)

    def test_nan_rejected(self):
        self.j["ratings"]["color_texture"]["score"] = float("nan")
        with self.assertRaises(ValueError):
            score(self.card, self.j)

    def test_hierarchical_weighting(self):
        label(self.j, "shirt", "fail")
        self.assertEqual(score(self.card, self.j)["semantic"]["edit"]["score"], 50)

    def test_partial_and_complete_rate_differ(self):
        label(self.j, "shirt", "partial")
        e = score(self.card, self.j)["semantic"]["edit"]
        self.assertEqual(e["score"], 75)
        self.assertEqual(e["complete_rate"], 50)

    def test_unknown_retains_bounds(self):
        label(self.j, "shirt", "unknown")
        result = score(self.card, self.j)
        self.assertIsNone(result["semantic"]["edit"]["score"])
        self.assertEqual((result["semantic"]["edit"]["lower"], result["semantic"]["edit"]["upper"]), (50, 100))
        self.assertEqual(result["success"], "unresolved")

    def test_detail_loss_not_automatically_hard_failure(self):
        label(self.j, "button", "fail")
        self.assertEqual(score(self.card, self.j)["success"], "pass")

    def test_core_failure_not_offset_by_beauty(self):
        label(self.j, "identity", "fail")
        for r in self.j["ratings"].values():
            if r["status"] == "scored": r["score"] = 4.0
        self.assertEqual(score(self.card, self.j)["success"], "fail")

    def test_core_optional_mistake_still_hard(self):
        self.card["groups"][2]["items"][0]["mandatory"] = False
        self.card = freeze(self.card, "fixture")
        self.j = judgment_fixture(self.card)
        label(self.j, "identity", "fail")
        self.assertEqual(score(self.card, self.j)["success"], "fail")

    def test_sequence_claim_requires_sequence(self):
        next(r for r in self.j["items"] if r["id"] == "action")["evidence_kind"] = "frames"
        with self.assertRaisesRegex(ValueError, "Sparse"):
            score(self.card, self.j)

    def test_invalid_delivery_is_failure(self):
        self.j["delivery"] = {"status": "invalid", "reason": "short clip"}
        self.assertEqual(score(self.card, self.j)["success"], "fail")

    def test_duplicate_fact_rejected(self):
        self.j["items"][-1] = self.j["items"][0]
        with self.assertRaisesRegex(ValueError, "exactly once"):
            score(self.card, self.j)

    def test_stale_card_rejected(self):
        self.card["requirement"] = "Change a different thing"
        with self.assertRaisesRegex(ValueError, "changed"):
            validate_card(self.card)

    def test_originality_requires_reference_set(self):
        self.card["creativity"] = "open"
        self.card = freeze(self.card, "fixture")
        self.j = judgment_fixture(self.card)
        with self.assertRaisesRegex(ValueError, "comparison set"):
            score(self.card, self.j)

    def test_no_repeated_frame_short_clip_acceptance(self):
        self.assertEqual(delivery_status(0.85, 5, 0.05)["status"], "invalid")
        with self.assertRaises(ValueError):
            nearest([0, .1, .2], 4, .05)

    def test_cosine_scale(self):
        self.assertAlmostEqual(adjacent_cosine([[1, 0], [1, 0]]), 1)
        self.assertAlmostEqual(adjacent_cosine([[1, 0], [0, 1]]), 0)
        with self.assertRaises(ValueError): adjacent_cosine([[0, 0], [1, 0]])

    def test_no_detail_metric_when_not_applicable(self):
        self.card["groups"].pop()
        self.card = freeze(self.card, "fixture")
        self.assertIsNone(score(self.card, judgment_fixture(self.card))["semantic"]["preserve_detail"]["score"])

    def test_macro_cluster_not_frame_or_seed_count(self):
        result = score(self.card, self.j)
        records = [{"method": "A", "seed": s, "result": result} for s in (1, 2, 3)]
        metrics = summarize(records, repeats=100)[0]["metrics"]
        self.assertEqual(metrics["edit"]["n_sources"], 1)
        self.assertIsNone(metrics["edit"]["ci95"])

    def test_missing_seed_not_removed(self):
        result = score(self.card, self.j)
        label(self.j, "shirt", "unknown")
        other = score(self.card, self.j)
        stats = summarize([{"method": "A", "seed": 1, "result": result}, {"method": "A", "seed": 2, "result": other}])[0]["metrics"]
        self.assertIsNone(stats["edit"]["mean"])
        self.assertEqual(stats["edit_lower"]["mean"], 75)

    def test_paired_difference_uses_same_seed(self):
        result = score(self.card, self.j)
        label(self.j, "shirt", "fail")
        other = score(self.card, self.j)
        records = [{"method": "A", "seed": 1, "result": result}, {"method": "B", "seed": 1, "result": other}]
        self.assertEqual(paired_difference(records, "A", "B", "edit")[0]["mean"], 50)
        records[1]["seed"] = 2
        self.assertIsNone(paired_difference(records, "A", "B", "edit")[0]["mean"])

    def test_report_preserves_decimals(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_report([{"method": "A", "seed": 1, "result": score(self.card, self.j)}], tmp)
            text = (Path(tmp) / "report.md").read_text(encoding="utf-8")
            self.assertIn("| rating | 3.7 |", text)
            self.assertIn("| score | 1.00 |", text)
            self.assertIn("100.00", text)

    def test_loop_compares_previous_accepted_not_rejected(self):
        start = copy.deepcopy(self.j); label(start, "shirt", "fail")
        rejected = copy.deepcopy(self.j); label(rejected, "identity", "fail")
        rounds = [
            {"id": "r1", "input_version": "source", "accepted": True, "judgment": start},
            {"id": "r2", "input_version": "r1", "previous_accepted": "r1", "accepted": False, "judgment": rejected},
            {"id": "r3", "input_version": "r1", "previous_accepted": "r1", "accepted": True, "judgment": self.j}]
        for r in rounds:
            r.update(final_judge_independent=True, prompt="fixture", decision_reason="fixture", generation_seconds=10)
        result = analyze(self.card, rounds)
        self.assertEqual(result["final_version"], "r3")
        self.assertEqual(result["transitions"][1]["repair"]["rate"], 100)
        self.assertEqual(result["generation_count"], 3)
        self.assertEqual(result["false_accept_rate"], 0)

    def test_loop_unknown_not_false_repair(self):
        before = copy.deepcopy(self.j); label(before, "shirt", "fail")
        label(self.j, "shirt", "unknown")
        repair = transition(self.card, before, self.j)["repair"]
        self.assertIsNone(repair["rate"])
        self.assertEqual((repair["lower"], repair["upper"]), (0, 100))

    def test_cache_reuse_and_changed_input(self):
        class Client:
            model = "synthetic"; calls = 0
            def predict_json(self, **kwargs):
                self.calls += 1
                return {"test_fixture": True}
        client = Client()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            cached_call(client, "system", {"a": 1}, [], path)
            cached_call(client, "system", {"a": 1}, [], path)
            self.assertEqual(client.calls, 1)
            with self.assertRaisesRegex(ValueError, "Stale"):
                cached_call(client, "system", {"a": 2}, [], path)

    def test_scaffold_preserves_short_long_distinction(self):
        rows = scaffold([{"sample_id": "x", "split": "fewshot", "source_video": "x.mp4", "source_video_sha256": "a" * 64,
                          "prompt_short": None, "prompt_long": "exact original request"}])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["requirement"], "exact original request")
        self.assertEqual(rows[0]["status"], "draft")

    def test_optional_damage_cannot_be_escalated(self):
        self.j["damages"] = [{"severity": "major", "related_item_ids": ["button"], "evidence": "fixture"}]
        with self.assertRaisesRegex(ValueError, "Optional-detail"):
            score(self.card, self.j)

    def test_dense_interval_coverage(self):
        self.assertFalse(covers_interval([[1, 2]], [0, 5]))
        self.assertTrue(covers_interval([[0, 2], [2, 5]], [0, 5]))
        self.assertFalse(covers_interval([[0, 2], [3, 5]], [0, 5]))
        self.assertTrue(covers_interval([[0, 5]], [1, 2]))

    def test_missing_output_kept_in_batch_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); write(root / "card.json", self.card)
            records = evaluate_manifest([{"case_id": "missing", "method": "A", "seed": 1,
                                          "card": "card.json", "output_video": "missing.mp4"}], root / "run", root, None)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["result"]["success"], "fail")
            self.assertEqual(records[0]["result"]["delivery"], "invalid")

    def test_agreement_retains_missing(self):
        result = agreement([{"case_id": "a", "a": 3.5, "b": 3.2}, {"case_id": "b", "a": None, "b": 4.0}])
        self.assertEqual((result["n"], result["total"]), (1, 2))
        self.assertAlmostEqual(result["mean_absolute_difference"], .3)

    def test_creativity_overview_preserves_dense_semantic_evidence(self):
        card = copy.deepcopy(self.card)
        card["creativity"] = "open"
        card = freeze(card, "fixture")
        truth = judgment_fixture(card)
        requests = []

        class Client:
            model = "synthetic-fixture"

            def predict_json(self, *, system_prompt, user_text, image_paths):
                requests.append((json.loads(user_text), len(image_paths)))
                if "For EVERY item" in system_prompt:
                    return {k: copy.deepcopy(truth[k]) for k in ("items", "damage_review", "damages")}
                creative = "optional fixed anonymous REFERENCE" in system_prompt
                return {"ratings": {k: copy.deepcopy(v) for k, v in truth["ratings"].items()
                                    if (k in {"scene_specific_design", "relative_originality"}) == creative}}

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.jpg"
            path.write_bytes(b"opaque fake-client-only evidence")
            evidence = {"card_sha256": card["card_sha256"], "source_sha256": card["source_sha256"],
                        "output_sha256": "b" * 64, "source_images": [str(path)] * 3,
                        "output_images": [str(path)] * 3, "image_sha256": [file_hash(path)] * 6,
                        "dense_ranges": [[0, 2]], "delivery": truth["delivery"],
                        "pairs": [{"source_seconds": t, "output_seconds": t, "overview": n != 1, "dense": True}
                                  for n, t in enumerate([.1, 1.0, 1.9])]}
            evidence["evidence_sha256"] = signature(evidence)
            refs = {"task_id": card["task_id"], "candidates": [
                {"images": [str(path)], "image_sha256": [file_hash(path)], "output_sha256": "b" * 64},
                {"images": [str(path)], "image_sha256": [file_hash(path)], "output_sha256": "c" * 64}]}
            result = judge(card, evidence, Client(), Path(tmp) / "judge", references=refs,
                           creativity_overview=True, creativity_exclude_self=True)
            self.assertEqual([n for _, n in requests], [6, 3, 5])
            self.assertEqual(requests[0][0]["dense_ranges"], [[0, 2]])
            self.assertEqual(requests[1][0]["dense_ranges"], [[0, 2]])
            self.assertEqual(requests[2][0]["dense_ranges"], [])
            self.assertEqual(requests[2][0]["image_groups"], [2, 2, 1])
            self.assertEqual(requests[2][0]["excluded_self_reference_count"], 1)
            self.assertEqual(len(requests[2][0]["pairs"]), 2)
            self.assertEqual(result["comparison_set_sha256"], signature(refs))
            self.assertEqual(result["ratings"]["temporal_coherence"]["score"], 3.7)

    def test_blind_calls_and_counterbalanced_preferences(self):
        card, truth = self.card, copy.deepcopy(self.j)
        label(truth, "action", "unknown")
        truth["ratings"]["temporal_coherence"] = {"status": "unknown", "score": None, "evidence": "sparse fixture"}
        class Client:
            model = "synthetic-fixture"; requests = []
            def predict_json(self, *, system_prompt, user_text, image_paths):
                request = json.loads(user_text); self.requests.append(request)
                if "Compare original-task semantics" in system_prompt:
                    return {"semantics": "unknown", "design": "A", "creativity": "not_applicable", "evidence": "fixture"}
                if "For EVERY item" in system_prompt:
                    response = {k: copy.deepcopy(truth[k]) for k in ("items", "damage_review", "damages")}
                    # Attempts to overwrite trusted wrapper metadata must be ignored.
                    response["delivery"] = {"status": "invalid", "reason": "untrusted extra field"}
                    return response
                return {"ratings": {k: copy.deepcopy(v) for k, v in truth["ratings"].items() if k not in {"scene_specific_design", "relative_originality"}}}
        client = Client()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.jpg"; path.write_bytes(b"opaque fake-client-only evidence")
            evidence = {"card_sha256": card["card_sha256"], "source_sha256": card["source_sha256"], "output_sha256": "b" * 64,
                        "source_images": [str(path), str(path)], "output_images": [str(path), str(path)],
                        "image_sha256": [file_hash(path)] * 4, "dense_ranges": [], "delivery": truth["delivery"],
                        "pairs": [{"source_seconds": .1, "output_seconds": .1}, {"source_seconds": 1.9, "output_seconds": 1.9}]}
            evidence["evidence_sha256"] = signature(evidence)
            result = judge(card, evidence, client, Path(tmp) / "judge")
            self.assertEqual(result["delivery"]["status"], "valid")
            self.assertNotIn("groups", client.requests[1]["card"])
            self.assertNotIn("source_video", client.requests[0]["card"])
            pair = pairwise(card, evidence, evidence, client, Path(tmp) / "pair")
            self.assertEqual(pair["result"]["design"]["verdict"], "tie")
            self.assertTrue(pair["result"]["design"]["order_disagreement"])
            self.assertEqual(pair["result"]["semantics"]["verdict"], "unknown")
            summary = preferences([pair])
            self.assertEqual(summary["design"]["a_preference_percent"], 50)
            self.assertIsNone(summary["semantics"]["a_preference_percent"])


class MediaIntegrationTests(unittest.TestCase):
    def test_actual_decode_pts_and_evidence_hash(self):
        try:
            import av
            from PIL import Image
        except ImportError:
            self.skipTest("Optional av/Pillow not installed")
        from evaluation.judges import verify_evidence
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source.mp4"
            with av.open(str(path), "w") as container:
                stream = container.add_stream("mpeg4", rate=10)
                stream.width = stream.height = 64
                stream.pix_fmt = "yuv420p"
                for i in range(20):
                    frame = av.VideoFrame.from_image(Image.new("RGB", (64, 64), (i * 10, 30, 50)))
                    for packet in stream.encode(frame): container.mux(packet)
                for packet in stream.encode(): container.mux(packet)
            card = card_fixture(); card["source_sha256"] = file_hash(path); card = freeze(card, "fixture")
            evidence = prepare(card, path, root / "evidence", root=root)
            verify_evidence(card, evidence)
            self.assertEqual(evidence["delivery"]["status"], "valid")
            self.assertEqual(len(evidence["pairs"]), 12)
            (Path(evidence["output_images"][0])).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed"):
                verify_evidence(card, evidence)


if __name__ == "__main__":
    unittest.main()
