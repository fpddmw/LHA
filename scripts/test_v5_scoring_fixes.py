"""Offline v5 validation/provenance/entry checks; no model downloads or API calls."""
import contextlib
import copy
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from evaluation import features, final_projection, task_metrics, final_suite
from evaluation.low_high import freeze_plan, prepare_final
from planner_harness.common import save, sha
from planner_harness.video import Video
import test_planner_harness as fixture
import test_creative_loop as loop
import preview_reevaluation as entry


class ProjectionTests(unittest.TestCase):
    setUp, tearDown = fixture.Tests.setUp, fixture.Tests.tearDown
    def packet(self):
        info = Video(self.source, self.root / "info").info
        plan = freeze_plan({"track": "short"}, "Make it blue.", info, self.root / "plan")
        return prepare_final("Make it blue.", info, info, self.root / "evidence", plan=plan)[0]

    def test_ambiguous_statuses_never_promote_numeric_placeholders(self):
        packet = self.packet()
        main = loop.review_fixture(packet["user_text"])
        main.pop("task_diagnostics", None)
        diagnostic_packet = task_metrics.request_packet(packet, "independent_final")
        diagnostics = loop.review_fixture(diagnostic_packet["user_text"])
        for status in (None, "", "unverified", "not_evaluated", "not_scored", "unknown", "missing-key"):
            for kind in ("main", "diagnostic"):
                with self.subTest(status=status, kind=kind):
                    raw = copy.deepcopy(main if kind == "main" else diagnostics)
                    row = raw["main_scores"]["visual_integrity"] if kind == "main" else raw["aesthetics"]["color_texture"]
                    row["status"] = status
                    row["score"] = 3
                    if status == "missing-key":
                        row.pop("status")
                    projected, errors, _ = (final_projection.project(raw, packet) if kind == "main"
                                             else task_metrics.project_final(raw, diagnostic_packet))
                    result = projected["main_scores"]["visual_integrity"] if kind == "main" else projected["aesthetics"]["color_texture"]
                    self.assertEqual(result["status"], "unknown")
                    self.assertIsNone(result["score"])
                    self.assertEqual(errors[0]["original"], row)

    def test_observed_alias_requires_valid_score_and_evidence(self):
        packet = self.packet()
        base = loop.review_fixture(packet["user_text"]); base.pop("task_diagnostics", None)
        for score, refs, expected in ((3, None, "scored"), (9, None, "unknown"), (3, [], "unknown")):
            raw = copy.deepcopy(base); row = raw["main_scores"]["visual_integrity"]
            row.update(status="observed", score=score)
            if refs is not None:
                row["evidence_refs"] = refs
            projected, _, normalized = final_projection.project(raw, packet)
            self.assertEqual(projected["main_scores"]["visual_integrity"]["status"], expected)
            if expected == "scored":
                self.assertEqual(normalized[0]["original"]["status"], "observed")


class Tokenizer:
    all_special_ids = [0, 99]
    model_max_length = 6
    truncation_side = "right"

    def __call__(self, text, **kwargs):
        return {"input_ids": [0] + [1000 + ord(c) for c in text] + [99]}

    def decode(self, ids, **kwargs):
        return "".join(chr(i - 1000) for i in ids if i not in self.all_special_ids)


class TextCoverageTests(unittest.TestCase):
    def test_actual_mask_and_full_prefix_suffix_coverage(self):
        tokenizer = Tokenizer()
        cases = [("ab", "ab", "right", "full_request", [0, 2], False),
                 ("abcdefgh", "abcd", "right", "request_prefix", [0, 4], True),
                 ("abcdefgh", "efgh", "left", "request_suffix", [4, 8], True)]
        for request, encoded, side, scope, span, truncated in cases:
            with self.subTest(scope=scope):
                tokenizer.truncation_side = side
                ids = tokenizer(encoded)["input_ids"]
                tokens = {"input_ids": [ids + [99, 99]], "attention_mask": [[1] * len(ids) + [0, 0]]}
                record = features.clip_text_record(request, tokenizer, tokens, model_max_positions=6)
                self.assertEqual(record["input_ids"], tokens["input_ids"][0])
                self.assertEqual(record["encoded_text"], encoded)
                self.assertEqual(record["content_token_span"], span)
                self.assertEqual(record["scope"], scope)
                self.assertEqual(record["truncated"], truncated)
                self.assertEqual(record["content_token_coverage"], len(encoded) / len(request))

    def test_unaligned_tokens_do_not_invent_a_source_span(self):
        tokenizer = Tokenizer(); ids = tokenizer("zz")["input_ids"]
        record = features.clip_text_record("abcdefgh", tokenizer, {"input_ids": [ids]})
        self.assertEqual(record["encoded_text"], "zz")
        self.assertIsNone(record["content_token_span"])
        self.assertIsNone(record["content_token_coverage"])


class PipelineTests(unittest.TestCase):
    setUp, tearDown = fixture.Tests.setUp, fixture.Tests.tearDown

    def test_compute_records_the_tokens_actually_sent_to_clip(self):
        import numpy as np
        class Tensor:
            def __init__(self, value): self.value = np.array(value)
            def __getitem__(self, key): return Tensor(self.value[key])
            def float(self): return self
            def cpu(self): return self
            def tolist(self): return self.value.tolist()
        class Batch(dict):
            def to(self, device): return self
        class Processor:
            tokenizer = Tokenizer()
            def __call__(self, images=None, text=None, **kwargs):
                if text is not None:
                    ids = self.tokenizer(text[0][:4])["input_ids"]
                    return Batch(input_ids=[ids], attention_mask=[[1] * len(ids)])
                return Batch(images=images)
        seen = []
        class Model:
            config = SimpleNamespace(text_config=SimpleNamespace(max_position_embeddings=6), _commit_hash="fixture")
            def to(self, device): return self
            def eval(self): return self
            def get_image_features(self, images): return Tensor([[1., 0.]] * len(images))
            def get_text_features(self, **tokens):
                seen.append(copy.deepcopy(tokens)); return Tensor([[1., 0.]])
            def __call__(self, images): return SimpleNamespace(last_hidden_state=Tensor([[[1., 0.]]] * len(images)))
        transformers = SimpleNamespace()
        transformers.CLIPProcessor = transformers.AutoImageProcessor = SimpleNamespace(from_pretrained=lambda *a, **k: Processor())
        transformers.CLIPModel = transformers.AutoModel = SimpleNamespace(from_pretrained=lambda *a, **k: Model())
        torch = SimpleNamespace(inference_mode=contextlib.nullcontext, __version__="fixture-only")
        with patch.dict(sys.modules, torch=torch, transformers=transformers):
            raw = features._compute(self.source, source=self.source, request="abcdefgh")
        record = raw["clip_text_input"]
        self.assertEqual(record["input_ids"], seen[0]["input_ids"][0])
        self.assertEqual(record["encoded_text"], "abcd")
        self.assertTrue(record["truncated"])
        self.assertAlmostEqual(raw["target_text_gain_clip"], 0)
        info = Video(self.source, self.root / "info").info
        plan = freeze_plan({"track": "long"}, "abcdefgh", info, self.root / "plan")
        with patch.object(features, "compute", return_value=raw), patch.object(final_suite.temporal, "compute", side_effect=ImportError("fixture")):
            suite = final_suite.automatic(info, info, plan, self.root / "automatic")
        self.assertEqual(suite["metrics"]["target_text_gain_clip"]["text_coverage"]["encoded_text"], "abcd")


class EntryTests(unittest.TestCase):
    setUp, tearDown = fixture.Tests.setUp, fixture.Tests.tearDown

    def prepare(self):
        digest = sha(self.source); media = self.root / "media"; media.mkdir()
        shutil.copyfile(self.source, media / (digest + ".mp4"))
        sample = {"sample_id": "001", "source_video": str(self.source), "source_sha256": digest,
                  "original_short_request": "Blue.", "original_long_request": "Make the scene blue."}
        candidate = {"id": "v1", "video_sha256": digest}
        result = {"rounds": [candidate], "first": candidate, "delivery": candidate}
        snapshot = {"hosts": {"fixture": {"samples": [
            {"sample_id": "001", "prompt_form": form, "methods": {"full": result, "pe-loop": result}}
            for form in ("short", "long")]}}}
        save(self.root / "selection.json", {"samples": [sample]}); save(self.root / "snapshot.json", snapshot)
        output = self.root / "v5"
        with patch("evaluation.providers.make_judge", side_effect=AssertionError("No model during preparation")):
            manifest = entry.prepare(self.root / "selection.json", self.root / "snapshot.json", media, output)
        return output, manifest

    def test_preparation_is_frozen_offline_deduplicated_and_original_task_only(self):
        output, manifest = self.prepare()
        self.assertEqual(len(manifest["records"]), 2)
        self.assertEqual({r["request"] for r in manifest["records"]}, {"Blue.", "Make the scene blue."})
        self.assertEqual(len(manifest["records"][0]["positions"]), 2)
        self.assertFalse((output / "scores").exists())
        self.assertEqual(entry.verify(output), manifest)
        with self.assertRaisesRegex(ValueError, "explicit --execute"), patch.object(entry.subprocess, "run") as run:
            entry.run(output)
        run.assert_not_called()
        with self.assertRaises(FileExistsError):
            entry.prepare(self.root / "selection.json", self.root / "snapshot.json", self.root / "media", output)
        with patch.object(entry, "profile", return_value={"sha256": "changed"}):
            with self.assertRaisesRegex(ValueError, "profile changed"):
                entry.verify(output)
        request = output / next(p for p in manifest["files"] if p.endswith("request.txt"))
        request.write_text("Changed task")
        with self.assertRaisesRegex(ValueError, "request or plan changed"):
            entry.verify(output)

    def test_execute_reuses_existing_scoring_cli_after_verification(self):
        output, manifest = self.prepare()
        with patch.object(entry.importlib.util, "find_spec", return_value=True), patch.object(entry.subprocess, "run") as invoke:
            entry.run(output, execute=True, budget_config=self.root / "compute.json")
        self.assertEqual(invoke.call_count, 2)
        for call in invoke.call_args_list:
            argv = call.args[0]
            self.assertIn("--execute", argv)
            self.assertEqual(argv[argv.index("--judge") + 1], "glm5.3flash")
            self.assertTrue(Path(argv[argv.index("--output") + 1]).is_relative_to(output / "scores"))


if __name__ == "__main__":
    unittest.main()
