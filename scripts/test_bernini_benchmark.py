"""CPU-only guards for portable full-benchmark dispatch and paid-call reuse."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_bernini_benchmark as runner

INFO = {"frames": 14, "fps": 30.0, "width": 64, "height": 48}


class Backend:
    identity = {"test_backend": "CPU synthetic; no real model or rendering quality evidence"}

    def __init__(self, *, fail_pe=False, long_pe=False):
        self.fail_pe, self.long_pe = fail_pe, long_pe
        self.pe_calls, self.render_calls = 0, 0

    def tokens(self, prompt):
        return (600 if prompt == "TOO LONG" else 10), "prefix " + prompt

    def enhance(self, case, folder):
        self.pe_calls += 1
        record = {"elapsed_seconds": 0.01, "raw_response": "recorded mocked response"}
        runner.write(folder / "result.json", record)
        if self.fail_pe:
            raise RuntimeError("Official PE failed; raw fallback not accepted")
        return "TOO LONG" if self.long_pe else "Enhanced " + case["prompt"], record

    def render(self, case, prompt, output):
        self.render_calls += 1
        output.write_bytes((prompt + str(case["seed"])).encode())
        runner.write(output.parent / "conditioning.json", {"indices": list(range(case["num_frames"]))})
        return {"generation_seconds": 0.02}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "source.mp4").write_bytes(b"synthetic input, not a video")
        self.manifest = self.root / "new.json"
        self.out = self.root / "results"

    def prepare(self, samples=None, **kwargs):
        if samples is None:
            samples = [{"id": "new_001", "source_video": "source.mp4",
                        "prompts": {"short": "Exact short <script>", "long": " Exact long.\n"}}]
        runner.write(self.manifest, {"samples": samples})
        kwargs.setdefault("conditions", ["direct", "pe"])
        with patch.object(runner, "inspect_video", return_value=INFO):
            return runner.prepare(self.manifest, self.out, **kwargs)

    def execute(self, plan, case, backend):
        with patch.object(runner, "inspect_video", return_value={**INFO, "frames": 13}):
            return runner.execute(case, self.out, plan["sha256"], backend)

    def test_arbitrary_full_cohort_exact_prompts_paired_seeds_and_missing_tiers(self):
        samples = [{"sample_id": f"new_{i:03d}", "source_video": "source.mp4",
                    "prompt_short": None if i == 0 else "Short", "prompt_long": " Long\n"}
                   for i in range(23)]
        plan = self.prepare(samples)
        self.assertEqual(plan["sample_count"], 23)
        self.assertEqual(len(plan["cases"]), 90)
        self.assertEqual(len(plan["missing_prompts"]), 1)
        self.assertEqual({c["seed"] for c in plan["cases"]}, {42})
        self.assertEqual({c["num_frames"] for c in plan["cases"]}, {13})
        self.assertEqual({c["tail_frames_omitted"] for c in plan["cases"]}, {1})
        self.assertEqual(plan["cases"][0]["prompt"], " Long\n")
        self.assertEqual(runner.load_plan(self.out / "plan.json"), plan)

    def test_identity_change_duplicate_ids_or_manifest_tamper_rejected(self):
        plan = self.prepare()
        self.assertEqual(self.prepare(seed=43),plan)
        changed = copy.deepcopy(plan)
        changed["cases"][0]["prompt"] = "changed"
        runner.write(self.out / "plan.json", changed)
        with self.assertRaisesRegex(ValueError, "identity"):
            runner.load_plan(self.out / "plan.json")
        self.out = self.root/"new-duplicate-test"
        row = {"id": "dup", "source_video": "source.mp4", "prompt": "Prompt"}
        with self.assertRaisesRegex(ValueError, "unique"):
            self.prepare([row, row])

    def test_jsonl_all_rows_single_instruction_and_direct_only(self):
        self.manifest = self.root / "new.jsonl"
        self.manifest.write_text('\n'.join(json.dumps({"id": str(i), "video": "source.mp4", "instruction": "Exact"}) for i in range(3)))
        with patch.object(runner, "inspect_video", return_value=INFO):
            plan = runner.prepare(self.manifest, self.out, conditions=["direct"])
        self.assertEqual(len(plan["cases"]), 3)
        self.assertEqual({c["tier"] for c in plan["cases"]}, {"single"})

    def test_complete_reuse_no_new_calls_and_media_or_pe_trace_tamper_rejected(self):
        plan = self.prepare()
        backend = Backend()
        case = next(c for c in plan["cases"] if c["condition"] == "pe")
        first = self.execute(plan, case, backend)
        self.assertIn("pe/result.json", first["artifact_hashes"])
        self.assertEqual(self.execute(plan, case, backend), first)
        self.assertEqual((backend.pe_calls, backend.render_calls), (1, 1))
        path = self.out / "cases" / case["case_id"] / "pe/result.json"
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, "trace changed"):
            self.execute(plan, case, backend)
        self.assertEqual((backend.pe_calls, backend.render_calls), (1, 1))
        summary = runner.report(self.out)
        self.assertEqual(summary["counts"]["integrity_failed"], 1)

    def test_failed_pe_never_renders_raw_fallback_or_repeats_external_call(self):
        plan = self.prepare()
        case = next(c for c in plan["cases"] if c["condition"] == "pe")
        backend = Backend(fail_pe=True)
        with self.assertRaisesRegex(RuntimeError, "fallback"):
            self.execute(plan, case, backend)
        with self.assertRaisesRegex(RuntimeError, "no external call repeated"):
            self.execute(plan, case, backend)
        self.assertEqual((backend.pe_calls, backend.render_calls), (1, 0))
        result = runner.read(self.out / "cases" / case["case_id"] / "result.json")
        self.assertEqual(result["status"], "failed")

    def test_pe_effective_token_overflow_is_retained_without_truncation_or_render(self):
        plan = self.prepare()
        case = next(c for c in plan["cases"] if c["condition"] == "pe")
        backend = Backend(long_pe=True)
        with self.assertRaisesRegex(ValueError, "512-token"):
            self.execute(plan, case, backend)
        prompt = runner.read(self.out / "cases" / case["case_id"] / "prompt.json")
        self.assertEqual(prompt["render_prompt"], "TOO LONG")
        self.assertEqual(prompt["token_count"], 600)
        self.assertEqual(backend.render_calls, 0)

    def test_completed_video_survives_source_and_runtime_updates(self):
        plan = self.prepare()
        case, backend = plan["cases"][0], Backend()
        self.execute(plan, case, backend)
        other = Backend()
        other.identity = {"test_backend": "different model"}
        self.execute(plan, case, other)
        self.assertEqual(other.render_calls,0)
        (self.root / "source.mp4").write_bytes(b"changed")
        self.execute(plan, case, backend)
        self.assertEqual(backend.render_calls,1)
        summary = runner.report(self.out)
        self.assertEqual(summary["positions"], 4)
        self.assertEqual(summary["counts"]["not_started"], 3)
        self.assertIn("&lt;script&gt;", (self.out / "index.html").read_text())
        self.assertNotIn("<script>", (self.out / "index.html").read_text())

    def test_existing_uncommitted_artifact_and_shared_gpu_lock_stop_second_owner(self):
        plan = self.prepare()
        case, backend = plan["cases"][0], Backend()
        folder = self.out / "cases" / case["case_id"]
        folder.mkdir(parents=True)
        (folder / "render-started.json").write_text('{}')
        with self.assertRaisesRegex(RuntimeError, "Uncommitted"):
            self.execute(plan, case, backend)
        with runner.lock(self.root / "gpu.lock"):
            with self.assertRaisesRegex(RuntimeError, "Another process"):
                with runner.lock(self.root / "gpu.lock"):
                    self.fail("Second owner acquired the GPU")
        self.assertEqual(backend.render_calls, 0)

    def official_pe_backend(self, *, fail=False):
        path = Path(__file__).resolve().parents[1] / "third_party/Bernini/bernini/prompt_enhancer.py"
        spec = importlib.util.spec_from_file_location("benchmark_test_official_pe", path)
        pe_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pe_module)
        calls = []

        class Client:
            max_retries = 2

            def __init__(self, **kwargs):
                self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

            def create(self, **kwargs):
                calls.append(kwargs)
                if fail:
                    raise ConnectionError("mock transport failure")
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Exact short <script>"))],
                    usage=SimpleNamespace(model_dump=lambda: {"prompt_tokens": 12, "completion_tokens": 4}),
                    model_dump=lambda **kw: {"model": "mock-vision", "choices": [{"message": {"content": "Exact short <script>"}}]})

            def close(self):
                pass

        backend = object.__new__(runner.OfficialBackend)
        backend.pe_module, backend.pe_key = pe_module, "FAKE_KEY_MUST_NOT_BE_SAVED"
        backend.requires_live_budget = False  # Offline SDK fixture; no real billing/provider.
        backend.identity = {"pe": {"base_url": "https://example.invalid/v1", "model": "mock-vision",
                                    "outer_attempts": 2, "video_frames": 3}}
        return backend, Client, calls

    def test_official_pe_payload_audit_and_unchanged_success_remain_valid(self):
        plan = self.prepare()
        case = plan["cases"][1]
        backend, client, calls = self.official_pe_backend()
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=client)}), \
             patch.object(backend.pe_module, "extract_uniform_frames", return_value=["frame0", "frame1", "frame2"]) as sampler:
            effective, record = backend.enhance(case, self.root / "pe-audit")
        self.assertEqual(effective, case["prompt"])
        self.assertEqual(record["status"], "enhanced")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["max_completion_tokens"], 8192)
        self.assertEqual(calls[0]["model"], "mock-vision")
        self.assertEqual(sum(x["type"] == "image_url" for x in calls[0]["messages"][1]["content"]), 3)
        sampler.assert_called_once_with(case["source_video"], num_frames=3)
        self.assertEqual(record["attempts"][0]["usage"]["completion_tokens"], 4)
        for path in (self.root / "pe-audit").rglob("*.json"):
            self.assertNotIn("FAKE_KEY_MUST_NOT_BE_SAVED", path.read_text())

    def test_official_failure_keeps_bounded_attempts_and_detects_raw_fallback(self):
        plan = self.prepare()
        backend, client, calls = self.official_pe_backend(fail=True)
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=client)}), \
             patch.object(backend.pe_module, "extract_uniform_frames", return_value=["frame"]), \
             patch.object(backend.pe_module.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "raw fallback"):
                backend.enhance(plan["cases"][1], self.root / "failed-pe")
        saved = runner.read(self.root / "failed-pe/result.json")
        self.assertEqual(saved["status"], "failed_raw_fallback")
        self.assertEqual(len(saved["attempts"]), 2)
        self.assertEqual(len(calls), 2)

    def canonical_rows(self):
        rows = []
        for index, split in enumerate(["train", "validation", "test"]):
            prompt = self.root / (str(index) + '-prompt.txt')
            prompt.write_text('Canonical request ' + str(index) + '\n')
            short = self.root / (str(index) + '-short.txt')
            short.write_text('Approved short style ' + str(index) + '\n')
            rows.append({"sample_id": str(index), "split": split, "benchmark_version": "lha-benchmark-fixture-final",
                "origin": "fixture", "source_group": "source-" + str(index), "source_video": "source.mp4",
                "source_video_sha256": runner.digest(self.root / 'source.mp4'), "prompt_file": prompt.name,
                "prompt_file_sha256": runner.digest(prompt), "instruction": prompt.read_text().strip(),
                "prompt_long": prompt.read_text().strip(), "prompt_short": short.read_text().strip(),
                "prompt_short_file": short.name, "prompt_short_file_sha256": runner.digest(short)})
        return rows

    def test_final_default_pe_keeps_both_prompt_forms_and_distinct_source_denominator(self):
        runner.write(self.manifest, self.canonical_rows())
        with patch.object(runner, 'inspect_video', return_value=INFO):
            with self.assertRaisesRegex(ValueError, 'splits explicitly'):
                runner.prepare(self.manifest, self.out)
            with self.assertRaisesRegex(ValueError, 'prompt forms explicitly'):
                runner.prepare(self.manifest, self.out, splits=['train', 'validation', 'test'])
            plan = runner.prepare(self.manifest, self.out, splits=['train', 'validation', 'test'], prompt_forms=['short', 'long'])
        self.assertEqual(len(plan['cases']), 6)
        self.assertEqual(plan['sample_count'], 3)
        self.assertEqual(plan['conditions'], ['pe'])
        self.assertEqual(plan['missing_prompts'], [])
        self.assertEqual({c['tier'] for c in plan['cases']}, {'short', 'long'})
        self.assertEqual({c['case_id'] for c in plan['cases']}, {f'{i}__{tier}__pe' for i in range(3) for tier in ['short', 'long']})
        summary = runner.report(self.out)
        self.assertEqual({s: r['samples'] for s, r in summary['by_split'].items()}, {'train': 1, 'validation': 1, 'test': 1})
        self.assertEqual(summary['by_split']['test']['by_origin']['fixture']['samples'], 1)
        self.assertEqual(summary['by_split']['test']['positions'], 2)
        self.assertEqual(summary['by_prompt_form']['short']['sources'], 3)

    def test_canonical_selected_split_and_project_root_paths(self):
        rows = self.canonical_rows()
        (self.root / 'benchmark_data').mkdir()
        manifest = self.root / 'benchmark_data/benchmark.json'
        for row in rows:
            target = self.root / 'benchmark_data' / row['prompt_file']
            target.write_bytes((self.root / row['prompt_file']).read_bytes())
            row['prompt_file'] = 'benchmark_data/' + row['prompt_file']
            row['source_video'] = 'benchmark_data/source.mp4'
        (self.root / 'benchmark_data/source.mp4').write_bytes((self.root / 'source.mp4').read_bytes())
        runner.write(manifest, rows)
        with patch.object(runner, 'inspect_video', return_value=INFO):
            plan = runner.prepare(manifest, self.out, splits=['test'], prompt_forms=['long'])
        self.assertEqual(plan['inventory_count'], 3)
        self.assertEqual(plan['sample_count'], 1)
        self.assertEqual(plan['cases'][0]['sample_id'], '2')
        self.assertEqual(plan['cases'][0]['source_video'], str(self.root / 'benchmark_data/source.mp4'))

    def test_final_changed_long_alias_or_approved_short_file_is_rejected(self):
        rows = self.canonical_rows()
        rows[0]['prompt_long'] = 'Unapproved changed long instruction'
        runner.write(self.manifest, rows)
        with patch.object(runner, 'inspect_video', return_value=INFO):
            with self.assertRaisesRegex(ValueError, 'aliases differ'):
                runner.prepare(self.manifest, self.out, splits=['train'], prompt_forms=['short', 'long'])
        rows[0]['prompt_long'] = rows[0]['instruction']
        runner.write(self.manifest, rows)
        (self.root / rows[0]['prompt_short_file']).write_text('changed')
        with patch.object(runner, 'inspect_video', return_value=INFO):
            with self.assertRaisesRegex(ValueError, 'short prompt file changed'):
                runner.prepare(self.manifest, self.out, splits=['train'], prompt_forms=['short', 'long'])


if __name__ == "__main__":
    unittest.main()
