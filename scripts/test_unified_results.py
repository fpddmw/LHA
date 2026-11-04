"""Current-result imports, bounded method adapters and failure recovery; no API/GPU."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from planner_harness import accounting as a
from planner_harness.integrity import IntegrityError
from experiments import results as r, unified_benchmark as u
from experiments.creative_benchmark import GENERATION

_CORPUS = None


def seeded_corpus(root):
    """Real seed/navigation in temporary repos; no empty-library test shortcut."""
    global _CORPUS
    if _CORPUS is None:
        from planner_harness.creative_knowledge import CreativeKnowledge
        _CORPUS = {}
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ('full','none'):
                path = Path(tmp) / (mode + '.json')
                CreativeKnowledge(ROOT,experience_mode=mode).freeze(path)
                snapshot=load(path)
                for name,row in snapshot['documents'].items():
                    _CORPUS[name]=row['text'].encode()
                for name in snapshot['asset_hashes']:
                    _CORPUS[name]=(ROOT/name).read_bytes()
        for name in ('knowledge/creative-loop/manifest.json','knowledge/source-map.json',
                     'knowledge/experience/curated/catalog.json'):
            _CORPUS[name]=(ROOT/name).read_bytes()
    for name,data in _CORPUS.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo, self.output, self.registry = self.root / "repo", self.root / "batch", self.root / "results"
        self.repo.mkdir()
        seeded_corpus(self.repo)
        self.source = self.repo / "source.mp4"
        import av
        import numpy as np
        with av.open(str(self.source), "w") as container:
            stream = container.add_stream("libx264", rate=24)
            stream.width = stream.height = 32
            stream.pix_fmt = "yuv420p"
            for i in range(117):
                frame = av.VideoFrame.from_ndarray(np.full((32, 32, 3), i % 256, dtype=np.uint8), format="rgb24")
                for packet in stream.encode(frame): container.mux(packet)
            for packet in stream.encode(): container.mux(packet)
        rows = []
        for sample, split in [("001", "train"), ("002", "test")]:
            long, short = f"Change the scene color in task {sample}.", f"Blue task {sample}."
            folder = self.repo / "benchmark_data" / sample
            folder.mkdir(parents=True)
            (folder / "long.txt").write_text(long)
            (folder / "short.txt").write_text(short)
            rows.append({"sample_id": sample, "split": split, "source_group": sample,
                "benchmark_version": "lha-benchmark-offline-test", "source_video": "source.mp4", "source_video_sha256": sha(self.source),
                "instruction": long, "prompt_long": long, "prompt_short": short,
                "prompt_file": str((folder / "long.txt").relative_to(self.repo)), "prompt_file_sha256": sha(folder / "long.txt"),
                "prompt_short_file": str((folder / "short.txt").relative_to(self.repo)), "prompt_short_file_sha256": sha(folder / "short.txt")})
        save(self.repo / "benchmark_data/benchmark.json", rows)
        self.rows = rows

    def row(self, **changes):
        result = {"sample_id": "001", "prompt_form": "short", "method": "direct", "seed": 42,
            "video": str(self.source), "video_sha256": sha(self.source), "source_sha256": sha(self.source),
            "request": self.rows[0]["prompt_short"], "generation": GENERATION, "evidence": {"receipt": "offline fixture"}}
        result.update(changes)
        return result

    def prepare(self, **changes):
        options = {"splits": ["train", "test"], "prompt_forms": ["short", "long"],
            "methods": None,
            "best_of_n": None, "results_root": self.registry}
        options.update(changes)
        with patch("planner_harness.creative.experiment_profile", return_value={"sha256": "fixture"}):
            return u.prepare(self.repo, self.output, **options)


class RegistryTests(Fixture):
    def test_current_blind_comparison_keeps_missing_then_fills_once_in_the_same_session(self):
        from evaluation.creative import JUDGES
        from evaluation.low_high import PROTOCOL, profile
        from evaluation.pairwise import QUESTIONS
        r.import_video(self.repo, self.registry, self.row(method="lineage-chain", seed=44))
        r.prepare_evaluation(self.repo, self.registry, evaluation_id="blind")
        models = {name: SimpleNamespace(model=name, reasoning_effort=None, requires_live_budget=False) for name in JUDGES}
        absolute, blind = [], []
        def score(request, source, candidate, directory, *, model, plan):
            absolute.append(model.model)
            return {"source_sha256": source["sha256"], "output_sha256": candidate["sha256"], "model": model.model,
                "profile_sha256": profile()["sha256"], "report": {"protocol_id": PROTOCOL, "main_scores": {}}}
        def compare(request, source, left, right, directory, *, plan, seed, model):
            blind.append(model.model)
            result = {"status": "scored", "judge": model.model, "final_profile_sha256": profile()["sha256"],
                "judgments": {q: {"outcome": "tie", "mapped_orders": ["tie", "tie"]} for q in QUESTIONS}}
            save(Path(directory) / "result.json", result)
            return result
        label = "lineage-source-restart__to__lineage-chain"
        with patch("evaluation.creative.judge_candidate", side_effect=score), patch("evaluation.final_suite.automatic", return_value={"metrics": {}}), \
             patch("evaluation.pairwise.compare", side_effect=compare), \
             patch("experiments.creative_benchmark.shared_source_plan", side_effect=AssertionError("must use the locally frozen original task")):
            view = r.score_evaluation(self.repo, self.registry, None, models=models)
            self.assertEqual(view["blind_comparisons"][label]["glm5.3flash"]["short"]["task_completion"]["missing"], 1)
            self.assertEqual(blind, [])
            r.import_video(self.repo, self.registry, self.row(method="lineage-source-restart", seed=44))
            view = r.score_evaluation(self.repo, self.registry, None, models=models)
            self.assertEqual(view["blind_comparisons"][label]["glm5.3flash"]["short"]["task_completion"]["tie"], 1)
            self.assertEqual(len(absolute), 2)  # identical content is scored once per judge
            self.assertEqual(len(blind), 2)
            r.score_evaluation(self.repo, self.registry, None, models=models)
            self.assertEqual(len(blind), 2)
        self.assertEqual(set(view["blind_comparisons"]), {label})  # no forced Direct/42 versus control/44 pair

    def test_two_missing_judge_receipts_are_complete_with_missing(self):
        from evaluation.creative import JUDGES
        r.import_video(self.repo, self.registry, self.row())
        plan = r.prepare_evaluation(self.repo, self.registry, evaluation_id="missing")
        position = plan["positions"][0]
        directory = self.registry / "evaluations/missing"
        for name in JUDGES:
            key = r._score_key(position, name)
            result_path = directory / "calls" / key / "current-result.json"
            save(result_path, {"status": "missing", "report": None,
                "source_sha256": position["source_sha256"], "output_sha256": position["video_sha256"]})
            save(directory / "scores" / (key + ".json"), {"evaluation_sha256": plan["sha256"], "key": key,
                "position": position, "judge": name, "result_path": str(result_path.relative_to(directory)), "result_sha256": sha(result_path)})
        ready = next(row for row in r.report(self.repo, self.registry)["results"] if row["status"] == "ready")
        self.assertEqual(ready["evaluation_status"], "complete_with_missing")

    def test_evaluation_appends_new_videos_without_repeating_scores_and_keeps_automatic_metrics(self):
        from evaluation.creative import JUDGES
        r.import_video(self.repo, self.registry, self.row())
        plan = r.prepare_evaluation(self.repo, self.registry, evaluation_id="appendable")
        calls = []
        def judge(request, source, candidate, directory, *, model, plan):
            calls.append((request, model.model))
            from evaluation.low_high import PROTOCOL, profile
            return {"source_sha256": source["sha256"], "output_sha256": candidate["sha256"],
                "model": model.model, "profile_sha256": profile()["sha256"], "report": {"protocol_id": PROTOCOL, "main_scores": {}},
                "task_metrics": {"metrics": {"intention_fulfillment": {"status": "scored", "score": 2}}}}
        models = {name: SimpleNamespace(model=name, reasoning_effort=None, requires_live_budget=False) for name in JUDGES}
        metrics = {"metrics": {"clip_f": {"status": "scored", "score": .8}, "dino_f": {"status": "scored", "score": .7}}}
        with patch("evaluation.creative.judge_candidate", side_effect=judge), patch("evaluation.final_suite.automatic", return_value=metrics):
            r.score_evaluation(self.repo, self.registry, None, models=models)
            self.assertEqual(len(calls), 2)
            r.import_video(self.repo, self.registry, self.row(sample_id="002", request=self.rows[1]["prompt_short"]))
            r.score_evaluation(self.repo, self.registry, None, models=models)
            self.assertEqual(len(calls), 4)
            r.score_evaluation(self.repo, self.registry, None, models=models)
            self.assertEqual(len(calls), 4)
        active = r.current_evaluation(self.registry)
        self.assertEqual(active[1]["sha256"], plan["sha256"])
        self.assertEqual(len(active[1]["positions"]), 2)
        self.assertEqual(len(list((active[0] / "additions").glob("*.json"))), 1)
        view = r.report(self.repo, self.registry)
        self.assertTrue(all(row["judges"]["glm5.3flash"]["metrics"]["clip_f"]["score"] == .8 for row in view["results"] if row["status"] == "ready"))

    def test_import_deduplicates_content_without_exposing_provenance_categories_or_old_scores(self):
        one = r.import_video(self.repo, self.registry, self.row())
        target = self.registry / one["video"]
        again = r.import_video(self.repo, self.registry, self.row(video=str(target), evidence={"receipt": "another name"}))
        self.assertEqual(one, again)
        r.import_video(self.repo, self.registry, self.row(method="pe", seed=91))
        save(self.registry / "final-judge/old.json", {"score": 100})
        save(self.registry / "results.json", {"old_score": 100})
        view = r.report(self.repo, self.registry)
        self.assertEqual(len(list((self.registry / "media").glob("*"))), 1)
        self.assertEqual(view["ready"], 2)
        self.assertTrue(all(x["evaluation_status"] == "pending" and not x["judges"] for x in view["results"]))
        self.assertNotIn("old_score", json.dumps(view))
        self.assertTrue(any(x["method"] == "pe" and x["seed"] == 91 for x in view["results"]))

    def test_conflicting_identity_and_bytes_are_refused(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            r.import_video(self.repo, self.registry, self.row(request="Different request."))
        with self.assertRaisesRegex(ValueError, "hash differs"):
            r.import_video(self.repo, self.registry, self.row(video_sha256="0" * 64))
        r.import_video(self.repo, self.registry, self.row())
        with self.assertRaisesRegex(ValueError, "different video/conditions"):
            r.import_video(self.repo, self.registry, self.row(generation={**GENERATION, "num_inference_steps": 50}))

    def test_historical_bernini_id_maps_by_source_and_exact_prompt(self):
        run = self.root / "old-run"
        folder = run / "cases/fewshot_001__short__direct"
        folder.mkdir(parents=True)
        (folder / "native.mp4").write_bytes(self.source.read_bytes())
        case = {"case_id": folder.name, "sample_id": "fewshot_001", "tier": "short", "condition": "direct", "seed": 42,
                "source_sha256": sha(self.source), "prompt": self.rows[0]["prompt_short"]}
        plan = {"generation": GENERATION, "cases": [case]}
        plan["sha256"] = signature(plan)
        save(run / "plan.json", plan)
        binding = {"case": case, "plan_sha256": plan["sha256"], "runtime_sha256": "fixture"}
        save(folder / "input.json", binding)
        save(folder / "result.json", {"status": "complete", "input_sha256": signature(binding),
            "input_file_sha256": sha(folder / "input.json"), "output_sha256": sha(folder / "native.mp4"), "artifact_hashes": {}})
        imported = r.import_bernini(self.repo, self.registry, run)
        self.assertEqual(imported[0]["sample_id"], "001")
        self.assertEqual(imported[0]["evidence"]["original_sample_id"], "fewshot_001")

    def test_sparse_lineage_controls_do_not_expand_to_unrelated_tasks(self):
        r.import_video(self.repo, self.registry, self.row(method="lineage-chain", seed=44))
        r.import_video(self.repo, self.registry, self.row(method="lineage-source-restart", seed=44))
        view = r.report(self.repo, self.registry)
        self.assertEqual(view["planned"], 6)  # four Direct positions plus two actual controls
        self.assertEqual(sum(x["method"].startswith("lineage") for x in view["results"]), 2)

    def test_fresh_evaluation_uses_only_new_bound_scores_and_deduplicates_same_video(self):
        r.import_video(self.repo, self.registry, self.row())
        r.import_video(self.repo, self.registry, self.row(method="pe"))
        plan = r.prepare_evaluation(self.repo, self.registry, evaluation_id="fresh")
        directory = self.registry / "evaluations/fresh"
        old = self.registry / "evaluations/old/scores"
        save(old / "fake.json", {"score": 4})
        position = plan["positions"][0]
        key = r._score_key(position, "glm5.3flash")
        result = {"source_sha256": position["source_sha256"], "output_sha256": position["video_sha256"],
                  "model":"glm5.3flash","profile_sha256":plan['protocol_sha256'],
                  "report": {"protocol_id":__import__('evaluation.low_high',fromlist=['PROTOCOL']).PROTOCOL,
                             "main_scores": {d:{"status":"scored","score":2} for d in __import__('critic_harness.one_shot',fromlist=['DIMENSIONS']).DIMENSIONS}}}
        save(directory / "calls/current.json", result)
        save(directory / "scores" / (key + ".json"), {"evaluation_sha256": plan["sha256"], "key": key,
            "position": position, "judge": "glm5.3flash", "result_path": "calls/current.json", "result_sha256": sha(directory / "calls/current.json")})
        view = r.report(self.repo, self.registry)
        rows = [x for x in view["results"] if x["status"] == "ready"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(x["judges"]["glm5.3flash"]["report"]["main_scores"]["instruction_adherence"]["score"] == 2 for x in rows))
        save(directory / "calls/current.json", {**result, "changed": True})
        with self.assertRaisesRegex(ValueError, "score binding changed"):
            r.report(self.repo, self.registry)


class MethodTests(Fixture):
    def test_unknown_method_settlement_reenters_collection_without_resubmitting_a_late_render(self):
        self.prepare(methods=["direct"], best_of_n=None)
        batch = load(self.output / "batch.json")
        batch["topics"] = batch["topics"][:1]
        lane = {**a.LIMITS, "model_calls": 0, "render_requests": 1, "compute_requests": 0, "tokens": 0, "wall_seconds": 20, "amount": None}
        policy = {"version": a.VERSION, "mode": "live", "cost_control": "count_limits_only", "lanes": ["direct"],
            "batch": {**lane, "wall_seconds": 100}, "topic": lane, "allocations": {"direct": lane}, "max_call_seconds": .03}
        release = threading.Event()
        calls = []
        from planner_harness.video import Video
        receipt = self.root / "owned-render.json"
        def render_actual():
            calls.append(1)
            release.wait(3)
            save(receipt, {"status": "complete", "video_sha256": sha(self.source)})
            return {"video": Video(self.source, self.root / "info").info, "response": str(receipt), "seed": 42}
        class Runtime:
            def __init__(inner, *args):pass
            def render(inner, topic, method, prompt, seed, number, scope):
                return a.invoke(scope, "owned-render", "render", "render:bernini", render_actual)
            def close(inner):pass
        with patch("experiments.unified_benchmark.verify", return_value=batch), patch("experiments.unified_benchmark.policy", return_value=a.validate_policy(policy)), patch("experiments.preflight.renderer_asset_paths"):
            try:
                with self.assertRaises(a.ExternalExecutionUnknown):
                    u.run(self.repo, self.output, {"budget": policy,"maintenance":{"enabled":False},"renderer":{"backend":"bernini"}}, runtime_factory=Runtime)
            finally:
                release.set()
                deadline = time.monotonic() + 3
                while a.active(self.output / "accounting") and time.monotonic() < deadline:time.sleep(.01)
            result = u.run(self.repo, self.output, {"budget": policy,"maintenance":{"enabled":False},"renderer":{"backend":"bernini"}}, runtime_factory=Runtime)
        self.assertEqual(result["positions"][0]["status"], "ready")
        self.assertEqual(calls, [1])
        self.assertTrue((self.output / "methods/001__short/direct/original-unknown-settlement.json").is_file())

    def test_native_metadata_fallback_checks_actual_pts_and_rejects_vfr(self):
        from run_bernini_benchmark import inspect_video
        import av
        import numpy as np
        from fractions import Fraction
        variable = self.root / "vfr.mp4"
        with av.open(str(variable), "w") as container:
            stream = container.add_stream("libx264", rate=24)
            stream.width = stream.height = 32
            stream.pix_fmt = "yuv420p"
            for pts in (0, 1, 2, 4, 5):
                frame = av.VideoFrame.from_ndarray(np.full((32, 32, 3), pts * 20, dtype=np.uint8), format="rgb24")
                frame.pts, frame.time_base = pts, Fraction(1, 10)
                for packet in stream.encode(frame):container.mux(packet)
            for packet in stream.encode():container.mux(packet)
        with patch("run_bernini_benchmark.shutil.which", return_value=None):
            self.assertEqual(inspect_video(self.source)["frames"], 117)
            with self.assertRaisesRegex(ValueError, "constant-frame-rate"):
                inspect_video(variable)

    def test_current_splits_forms_and_single_seed_sequence_share_method_positions(self):
        batch = self.prepare(seed_start=17, seed_step=4, max_generations=3)
        self.assertEqual(len(batch["topics"]), 4)
        self.assertEqual(batch["seed_sequence"], {"start": 17, "step": 4})
        self.assertEqual({t["prompt_form"] for t in batch["topics"]}, {"short", "long"})
        self.assertEqual({t["split"] for t in batch["topics"]}, {"train", "test"})
        self.assertEqual(next(t['methods'] for t in batch['topics'] if t['split']=='train'),['none'])
        self.assertEqual(set(next(t['methods'] for t in batch['topics'] if t['split']=='test')),set(r.DEFAULT_TEST_METHODS))
        self.assertEqual(r.report(self.repo, self.registry)["planned"], 2+2*len(r.DEFAULT_TEST_METHODS))

    def test_raw_direct_is_not_a_planner_and_existing_first_sample_is_not_rendered_again(self):
        batch = self.prepare(methods=["direct-best-of-n"], best_of_n=2)
        topic = batch["topics"][0]
        r.import_video(self.repo, self.registry, self.row())
        a.install(self.output / "accounting")
        calls = []
        receipt = self.root / "render-receipt.json"
        save(receipt, {"status": "complete"})
        from planner_harness.video import Video
        class Runtime:
            def render(inner, topic, method, prompt, seed, number, scope):
                calls.append((prompt, seed))
                return {"video": Video(self.source, self.root / "info").info, "response": str(receipt), "seed": seed}
            def review(inner, *args):
                return {"report": {"summary":"Visible blue scene.","findings":[]}}
            def choose(inner, topic, candidates, reviews, directory, scope):
                return 1,{"policy":u.SELECTOR,"selected_index":1,"reason":"The requested blue treatment is clearer.","model_called":True}
        result = u.execute_method(self.repo, self.output, topic, "direct-best-of-n", load(self.output / "batch.json"), Runtime())
        self.assertEqual(result["status"], "ready")
        self.assertEqual(calls, [(topic["request"], 43)])
        u.execute_method(self.repo, self.output, topic, "direct-best-of-n", load(self.output / "batch.json"), Runtime())
        self.assertEqual(len(calls), 1)

    def test_single_planner_call_rewrites_before_rendering(self):
        batch = self.prepare(methods=["planner-once"], best_of_n=None)
        a.install(self.output / "accounting")
        class Model:
            model, reasoning_effort = "gpt-6.1-sol", "high"
            calls = 0
            def predict_text(inner, **kwargs):
                inner.calls += 1
                return json.dumps({"prompt": "A blue painted scene, preserving its visible objects."})
        model = Model()
        model.lha_accounting_scope = a.scope(self.output / "accounting", "once", "planner-once")
        prompt = u.planner_once(self.repo, batch["topics"][0], self.root / "once", model)
        self.assertIn("blue painted", prompt)
        self.assertTrue((self.root / "once/call/response.txt").is_file())
        self.assertEqual(len(a.load_ledger(self.output / "accounting")["operations"]), 1)
        self.assertEqual(u.planner_once(self.repo, batch["topics"][0], self.root / "once", model), prompt)
        self.assertEqual(len(a.load_ledger(self.output / "accounting")["operations"]), 1)

    def test_selected_loop_v3_records_the_actual_seed(self):
        batch = self.prepare(methods=["full"], best_of_n=None,splits=['test'])
        batch = load(self.output / "batch.json")
        topic = batch["topics"][0]
        a.install(self.output / "accounting")
        from planner_harness.video import Video
        video = {**Video(self.source, self.root / "info").info, "job_id": "g3", "execution": {"seed": 44}}
        run = self.root / "loop"
        save(run / "state.json", {"jobs": {"g3": {"payload": {"renderer": {"seed": 44}}}}})
        loop = {"first": "v3", "selected": "v3", "videos": {"v3": video}, "record_directory": str(run), "completion_record": {"path": str(run / "state.json")}}
        runtime = SimpleNamespace(loop=lambda *args: loop)
        with patch("experiments.creative_benchmark.verify_arm"):
            u.execute_method(self.repo, self.output, topic, "full", batch, runtime)
        entry = r.find(self.registry, topic['sample_id'], "short", "full", 42)
        self.assertEqual(entry["seed"], 42)
        self.assertEqual(entry["evidence"]["selected_render_seed"], 44)

    def test_rich_direct_receipt_matches_shared_settings_without_regeneration(self):
        batch = self.prepare(methods=["direct"], best_of_n=None)
        topic = batch["topics"][0]
        row = r.import_video(self.repo, self.registry, self.row(generation={**GENERATION, "backend": "bernini",
            "task_type": "v2v", "num_frames": 117, "fps": 24.0, "omega_txt": 4.0, "seed": 42}))
        u.check_entry(topic, "direct", batch, row)
        with self.assertRaises(IntegrityError):
            u.check_entry(topic, "direct", batch, {**row, "generation": {**row["generation"], "fps": 20.0}})


class BudgetRecoveryTests(Fixture):
    def test_explicit_count_limits_only_keeps_unknown_money_and_real_usage(self):
        lane = {**a.LIMITS, "model_calls": 1, "render_requests": 1, "compute_requests": 1, "tokens": 20, "wall_seconds": 10, "amount": None}
        policy = {"version": a.VERSION, "mode": "live", "cost_control": "count_limits_only", "lanes": ["direct"],
            "batch": lane, "topic": lane, "allocations": {"direct": lane}, "max_call_seconds": 1}
        a.install(self.output / "accounting", policy, require_live=True, required_quotes=("model:fixture/none",))
        scope = a.scope(self.output / "accounting", "counted", "direct")
        a.admit_topic(scope)
        a.invoke(scope, "one", "model", "model:fixture/none", lambda: {}, tokens=8, usage_getter=lambda: {"total_tokens": 6})
        summary = a.summary(self.output / "accounting")
        self.assertEqual(summary["reserved_or_settled_totals"]["tokens"], 6)
        self.assertIsNone(summary["total_amount"])
        self.assertFalse(summary["invoice_ceiling_verified"])
        with self.assertRaises(a.ResourceExhausted):
            a.invoke(scope, "two", "model", "model:fixture/none", lambda: self.fail("count cap must refuse"))
        with self.assertRaises(a.BudgetConfigurationError):
            a.validate_policy({**policy, "cost_control": "quoted_allowance"}, require_live=True)

    def test_unsupported_api_hard_requirement_refuses_before_dispatch(self):
        from planner_harness.model_call import call_text
        class UnsupportedAPI:
            def budget_capabilities(self):return {'hard_output_tokens':False,'hard_invoice':False}
            def predict_text(self,**kwargs):raise AssertionError('must not dispatch')
        client = UnsupportedAPI()
        client.model, client.reasoning_effort, client.output_limit_mode = "fixture", "high", "hard"
        client.runtime_identity = lambda: {"fixture": True}
        a.install(self.output / "accounting")
        client.lha_accounting_scope = a.scope(self.output / "accounting", "hard")
        with patch.object(client, "predict_text", side_effect=AssertionError("must not dispatch")):
            with self.assertRaises(a.BudgetConfigurationError):
                call_text(self.root / "hard-call", client, "s", "u", [])
        self.assertFalse(a.load_ledger(self.output / "accounting")["operations"])
        self.assertFalse(list((self.root / "hard-call").glob("attempts/*/submitted.json")))
        with self.assertRaises(a.BudgetConfigurationError):
            a.validate_policy({"version": a.VERSION, "mode": "offline", "hard_requirements": {"invoice": True}})

    def test_glm_honors_the_actual_requested_output_cap_and_report_layer_requests_16384(self):
        from evaluation.creative import ParateraJudge, SonnetJudge
        from planner_harness.report_call import call_report, POLICY
        self.assertEqual(ParateraJudge.build_payload("s", "u", [], 73)["max_tokens"], 73)
        self.assertEqual(SonnetJudge.build_payload("s", "u", [], 73)["max_tokens"], 73)
        observed = []
        class Model:
            model, reasoning_effort = "fixture", None
            def predict_text(inner, **kwargs):
                observed.append(kwargs["max_new_tokens"])
                return '{"ok":true}'
        call_report(self.root / "report", Model(), {"system_prompt": "s", "user_text": "u", "images": []}, [], lambda x, p: x)
        self.assertEqual(observed, [POLICY["output_tokens_per_attempt"]])
        self.assertEqual(observed, [16384])

    def test_late_owned_model_answer_is_collected_without_a_second_submission(self):
        from planner_harness.model_call import call_text
        a.install(self.output / "accounting", {"version": a.VERSION, "mode": "offline", "max_call_seconds": .05})
        entered, release = threading.Event(), threading.Event()
        calls = []
        class Model:
            model, reasoning_effort = "fixture", None
            def predict_text(inner, **kwargs):
                calls.append(1); entered.set(); release.wait(3)
                return '{"ok":true}'
        model = Model()
        model.lha_accounting_scope = a.scope(self.output / "accounting", "late")
        try:
            with self.assertRaises(a.ExternalExecutionUnknown):
                call_text(self.root / "call", model, "s", "u", [], attempts=1)
            self.assertTrue(entered.is_set())
        finally:
            release.set()
            deadline = time.monotonic() + 3
            while a.active(self.output / "accounting") and time.monotonic() < deadline: time.sleep(.01)
        self.assertEqual(call_text(self.root / "call", model, "s", "u", [], attempts=1), '{"ok":true}')
        self.assertEqual(calls, [1])
        self.assertTrue((self.root / "call/attempts/01/unknown.json").exists())

    def test_unknown_render_recovers_only_its_original_completed_receipt(self):
        a.install(self.output / "accounting", {"version": a.VERSION, "mode": "offline", "max_call_seconds": .03})
        scope = a.scope(self.output / "accounting", "late", "direct")
        directory = self.root / "render"
        request = {"mode": "live", "accounting_scope": scope, "sha256": "request-identity"}
        save(directory / "response.json", {"status": "failed", "outcome_unknown": True})
        release = threading.Event();calls = []
        def render():
            calls.append(1);release.wait(3)
            return {"video": {"path": str(self.source), "sha256": sha(self.source)}}
        try:
            with self.assertRaises(a.ExternalExecutionUnknown):
                a.invoke(scope, request["sha256"], "render", "render:bernini", render)
            with self.assertRaises(a.ExternalExecutionUnknown):u.reconcile_render(directory, request)
        finally:
            release.set()
            deadline = time.monotonic() + 3
            while a.active(self.output / "accounting") and time.monotonic() < deadline:time.sleep(.01)
        recovered = u.reconcile_render(directory, request)
        self.assertEqual(load(recovered)["status"], "complete")
        self.assertFalse(load(recovered)["reconciliation"]["new_submission"])
        self.assertTrue(load(directory / "response.json")["outcome_unknown"])
        self.assertEqual(calls, [1])


class HygieneTests(unittest.TestCase):
    def test_frozen_historical_cards_resolve_to_verified_migrated_source(self):
        from evaluation.protocol import validate_card, resolve_card_source
        for name in ("041_short", "041_long"):
            card = validate_card(load(ROOT / "examples/evaluation" / (name + ".card.json")))
            self.assertEqual(sha(resolve_card_source(card, ROOT)), card["source_sha256"])
            self.assertEqual(card["source_video"], "benchmark_data/main/041/041.mp4")

    def test_source_publication_excludes_media_and_history_and_preserves_originals(self):
        from prepare_publication import prepare
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo";root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "source.py").write_text("print('fixture')\n")
            (root / "clip.mp4").write_bytes(b"unverified media")
            (root / ".env").write_text("SECRET=fixture")
            output = Path(temp) / "source.zip"
            prepare(root, output)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(set(archive.namelist()), {"source.py", "PUBLICATION-MANIFEST.json"})
                manifest = json.loads(archive.read("PUBLICATION-MANIFEST.json"))
                self.assertFalse(manifest["git_history_included"])
            self.assertEqual((root / "clip.mp4").read_bytes(), b"unverified media")
            with self.assertRaises(ValueError):prepare(root, output)


if __name__ == "__main__":
    unittest.main()
