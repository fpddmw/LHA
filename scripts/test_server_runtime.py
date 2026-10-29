"""Offline contract tests: scripted decisions/synthetic media, never experiment results."""
import concurrent.futures
import copy
import json
import os
from pathlib import Path
import shutil
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
from planner_harness.lock import RunLock
from server_runtime.queue import Queue
from server_runtime.engine import Engine
from server_runtime.service import Service
from server_runtime.media_cache import DecodeCache
from evaluation.media import decode, prepare
from evaluation.protocol import freeze
import test_planner_harness as fixtures
ScriptedModel = fixtures.ScriptedModel
from test_evaluation import card_fixture, judgment_fixture


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.q = Queue(self.root / "queue.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def engine(self, handler, expand=lambda job: None):
        return Engine(self.q, self.root, handler, expand, interval=.01)

    def test_idempotency_and_dependency_gating(self):
        first = self.q.enqueue("a", "planner", "llm", {"seed": 42})
        self.assertEqual(first, self.q.enqueue("a", "planner", "llm", {"seed": 42}))
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.q.enqueue("a", "planner", "llm", {"seed": 43})
        self.q.enqueue("b", "render", "gpu", {}, parents=[first])
        self.assertIsNone(self.q.claim("gpu", "x"))
        job = self.q.claim("llm", "x")
        self.q.finish(job, error="known failure")
        self.assertEqual(self.q.status()["jobs"][1]["blocked_by"], [first])
        self.assertIsNone(self.q.claim("gpu", "x"))
        with self.assertRaisesRegex(ValueError, "Dependencies"):
            self.q.enqueue("bad", "render", "gpu", {}, parents=[999])

    def test_atomic_concurrency_and_stale_owner(self):
        for n in range(10):
            self.q.enqueue(str(n), "planner", "llm", {})
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            claims = list(pool.map(lambda n: self.q.claim("llm", str(n)), range(10)))
        jobs = [j for j in claims if j]
        self.assertEqual(len(jobs), 2)
        self.q.recover()
        new = self.q.claim("llm", "new-owner")
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.q.finish(jobs[0], result={})
        self.q.finish(new, result={})
        self.assertEqual(self.q.status()["jobs"][0]["attempts"][0]["outcome"], "interrupted")

    def test_receipt_recovery_does_not_call_external(self):
        self.q.enqueue("video", "render", "gpu", {})
        job = self.q.claim("gpu", "old")
        media = self.root / "output.bin"
        media.write_bytes(b"already completed")
        save(self.root / "jobs" / str(job["id"]) / "receipt.json", {"signature": job["signature"],
             "result": {"artifacts": [{"path": str(media), "sha256": sha(media)}]}})
        calls = []
        self.engine(lambda *args: calls.append(args)).run(once=True)
        self.assertEqual(calls, [])
        self.assertEqual(self.q.rows()[0]["state"], "complete")

    def test_uncertain_call_waits_for_explicit_retry(self):
        identity = self.q.enqueue("video", "render", "gpu", {})
        job = self.q.claim("gpu", "old")
        save(self.root / "jobs" / str(identity) / "started.json", {"signature": job["signature"]})
        calls = []
        engine = self.engine(lambda *args: (calls.append(1) or {"ok": True}))
        engine.run(once=True)
        self.assertEqual(self.q.rows()[0]["state"], "needs_review")
        self.assertEqual(calls, [])
        self.q.retry(identity, "Fixture operator verified that no usable artifact exists; allow one attempt")
        engine.run(once=True)
        self.assertEqual(calls, [1])
        self.assertEqual(self.q.rows()[0]["state"], "complete")

    def test_receipt_hash_corruption_stops_recovery(self):
        self.q.enqueue("video", "render", "gpu", {})
        job = self.q.claim("gpu", "old")
        media = self.root / "changed.bin"
        media.write_bytes(b"changed")
        save(self.root / "jobs" / str(job["id"]) / "receipt.json", {"signature": job["signature"],
             "result": {"artifacts": [{"path": str(media), "sha256": "0" * 64}]}})
        self.engine(lambda *args: self.fail("Must not regenerate")).run(once=True)
        self.assertEqual(self.q.rows()[0]["state"], "failed")

    def test_expansion_replay_is_idempotent(self):
        self.q.enqueue("parent", "planner", "llm", {})
        fail_once = [True]
        def expand(job):
            if job["key"] == "parent":
                self.q.enqueue("child", "render", "gpu", {}, parents=[job["id"]])
                if fail_once.pop() if fail_once else False:
                    raise RuntimeError("Injected process failure after enqueue, before marking expansion")
        with self.assertRaisesRegex(RuntimeError, "Injected"):
            self.engine(lambda *args: {}, expand).run(once=True)
        self.engine(lambda *args: {}, expand).run(once=True)
        self.assertEqual([r["key"] for r in self.q.rows()], ["parent", "child"])
        self.assertTrue(all(r["state"] == "complete" for r in self.q.rows()))

    def test_gpu_llm_cpu_overlap_and_drain(self):
        for name, resource in [("gpu1", "gpu"), ("gpu2", "gpu"), ("llm1", "llm"), ("llm2", "llm"), ("cpu", "cpu")]:
            self.q.enqueue(name, "fixture", resource, {})
        barrier = threading.Barrier(4)
        entered, lock = [], threading.Lock()
        def handler(job, directory):
            with lock:
                entered.append(job["key"])
            barrier.wait(timeout=10)  # All four can overlap; a second GPU call cannot enter.
            self.q.dispatch("drain")
            return {}
        self.engine(handler).run(once=True)
        self.assertCountEqual(entered, ["gpu1", "llm1", "llm2", "cpu"])
        self.assertEqual(self.q.rows()[1]["state"], "queued")
        self.assertEqual(Queue(self.q.path).dispatch(), "drain")
        self.q.dispatch("running")
        self.engine(lambda *args: {}).run(once=True)
        self.assertTrue(all(r["state"] == "complete" for r in self.q.rows()))

    def test_one_process_owner(self):
        with RunLock(self.root / "service-owner"):
            with self.assertRaisesRegex(RuntimeError, "already owned"):
                self.engine(lambda *args: {}).run(once=True)

    def test_snapshot_lock_can_wait_without_changing_exclusive_default(self):
        entered = threading.Event()
        def reader():
            with RunLock(self.root / "snapshot", timeout=5):
                entered.set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            with RunLock(self.root / "snapshot"):
                future = pool.submit(reader)
                self.assertFalse(entered.wait(.1))
                with self.assertRaisesRegex(RuntimeError, "already owned"):
                    with RunLock(self.root / "snapshot", timeout=.05):
                        pass
            future.result(timeout=5)
            self.assertTrue(entered.is_set())

    def test_cli_process_drain_resume_and_idle_exit(self):
        config = self.root / "config-input.json"
        save(config, {})
        command = [sys.executable, str(ROOT / "scripts/run_server_pipeline.py"), "--service", str(self.root / "cli")]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.run(command + ["init", "--config", str(config)], check=True, capture_output=True, creationflags=flags)
        process = subprocess.Popen(command + ["run"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
        try:
            deadline = time.monotonic() + 20
            while not (self.root / "cli/status.json").exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue((self.root / "cli/status.json").exists())
            subprocess.run(command + ["drain"], check=True, capture_output=True, creationflags=flags)
            out, err = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, err.decode(errors="replace"))
            self.assertEqual(load(self.root / "cli/stopped.json")["reason"], "drained")
            subprocess.run(command + ["resume"], check=True, capture_output=True, creationflags=flags)
            subprocess.run(command + ["run", "--once"], check=True, capture_output=True, timeout=20, creationflags=flags)
            self.assertEqual(load(self.root / "cli/stopped.json")["reason"], "idle")
        finally:
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=10)


class ServiceTests(unittest.TestCase):
    setUp = fixtures.Tests.setUp
    tearDown = fixtures.Tests.tearDown

    def service(self, **kwargs):
        root = self.root / "service"
        q = Queue(root / "queue.sqlite3")
        return Service(q, root, ROOT, kwargs.pop("config", {}), **kwargs)

    def task(self):
        return {"id": "fixture", "source": str(self.source), "source_sha256": sha(self.source),
                "request": "Make the scene blue.", "max_generations": 2,
                "execution": {"mode": "live", "renderer": {"backend": "fixture", "generation": {"steps": 50}, "seed": 42,
                    "output": {"frames": 20, "fps": 10, "width": 80, "height": 60}}, "critic": {"max_calls": 3}}}

    def test_real_harness_queue_two_generations_critic_and_finish(self):
        def action(name, **args):
            return {"action": name, "arguments": args}
        model = ScriptedModel([action("generate", input_video="source", prompt="Blue."),
            action("critique", video="v1", question="Check whether the requested color changed."),
            action("generate", input_video="v1", prompt="Soften the blue.", seed=43),
            action("finish", video="v2", message="Choose the second fixture candidate.")])
        renders, critiques = [], []
        def render(job, directory):
            p = job["payload"]
            renders.append(copy.deepcopy(p))
            native = directory / "fixture.avi"
            shutil.copyfile(p["input"]["path"], native)
            return {"video": {"path": str(native), "sha256": sha(native)}, "execution": {
                "requested_prompt": p["prompt"], "effective_prompt": p["prompt"], "input_sha256": p["input"]["sha256"],
                "preflight": "passed", "settings": p["renderer"]["generation"], "seed": p["renderer"]["seed"],
                "token_count": 3, "token_limit": 512, "model_revision": "synthetic-fixture-only", "code_revision": "fixture",
                "conditioning_source_indices": list(range(20))}}
        def critic(job, *args, **kwargs):
            critiques.append(job)
            return {"usage": "online_critic", "finding": "synthetic review: soften blue"}
        service = self.service(model_factory=lambda role: model, renderer=render)
        identity = service.submit(self.task())
        with patch("critic_harness.adapter.critique", side_effect=critic):
            engine = Engine(service.queue, service.directory, service, service.expand, interval=.01)
            engine.run(once=True)
        rows = service.queue.rows()
        self.assertTrue(all(r["state"] == "complete" for r in rows), [(r["key"], r["error"]) for r in rows])
        state = load(service.directory / "tasks/fixture/run/state.json")
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["final"]["video"], "v2")
        self.assertEqual(state["generation_requests"], 2)
        self.assertEqual([p["renderer"]["seed"] for p in renders], [42, 43])
        self.assertEqual(renders[1]["input_id"], "v1")
        self.assertEqual(state["videos"]["v2"]["time_mapping"]["source_times_seconds"], [i / 10 for i in range(20)])
        self.assertEqual(len(critiques), 1)
        self.assertIn("soften blue", model.inputs[2]["user_text"])
        self.assertEqual(identity, service.submit(self.task()))
        engine.run(once=True)
        self.assertEqual(len(renders), 2)
        self.assertEqual(len(service.queue.rows()), 7)

    def test_final_evaluation_off_by_default(self):
        service = self.service(renderer=lambda *args: {})
        task = self.task()
        task["final_evaluation"] = {"card": "does-not-exist"}
        with self.assertRaisesRegex(ValueError, "disabled"):
            service.submit(task)
        with self.assertRaisesRegex(ValueError, "disabled"):
            service.submit_evaluation({})
        self.assertEqual(service.queue.rows(), [])

    def test_runtime_revision_change_requires_new_service(self):
        service = self.service()
        manifest = service.directory / "runtime-sources.json"
        save(manifest, {"changed": "fixture"})
        with self.assertRaisesRegex(ValueError, "Job record changed"):
            self.service()

    def test_signed_tool_response_recovers_without_resampling(self):
        service = self.service(renderer=lambda *args: self.fail("Completed tool must not render again"))
        body = {"id": "fixture-generate", "kind": "generate", "mode": "live", "payload": {}}
        request = {**body, "sha256": signature(body)}
        path = self.root / "tool/request.json"
        save(path, request)
        save(path.with_name("response.json"), {"request_sha256": request["sha256"], "mode": "live", "status": "complete",
             "payload": {"video": {"path": str(self.source), "sha256": sha(self.source)}}})
        identity = service.queue.enqueue("tool", "tool", "gpu", {"request": str(path), "request_sha256": request["sha256"]})
        job = service.queue.claim("gpu", "previous-process")
        save(service.directory / "jobs" / str(identity) / "started.json", {"signature": job["signature"]})
        Engine(service.queue, service.directory, service, service.expand, interval=.01).run(once=True)
        self.assertEqual(service.queue.rows()[0]["state"], "complete")

    def test_resident_bernini_passes_exact_profile_and_reuses_pipeline(self):
        from server_runtime.renderers import PersistentRenderer
        sys.path.insert(0, str(ROOT / "scripts/deploy"))
        calls, builds = [], []
        g = {"num_inference_steps": 40, "guidance_mode": "v2v_apg", "max_image_size": 848,
             "negative_prompt": "", "prompt_enhancer": False}
        renderer = PersistentRenderer(ROOT, {"backend": "bernini", "generation": g, "asset_manifest_sha256": "fixture"}, self.root / "gpu")
        renderer.ready, renderer.assets = True, {"model_revision": "fixture-only", "code_revision": "fixture-only"}
        renderer.cli = object()
        renderer.torch = SimpleNamespace(device=lambda value: value, __version__="fixture", version=SimpleNamespace(cuda=None))
        renderer.prefix, renderer.clean = "official fixture prefix ", lambda text: text.lower()
        renderer.tokenizer = lambda *args, **kwargs: {"input_ids": [1, 2, 3]}
        renderer.reader = lambda path: SimpleNamespace(length=21, fps=10)
        renderer.indices = lambda *args, **kwargs: list(range(21))
        renderer.kwargs = lambda cli: {"num_inference_steps": 40, "guidance_mode": "v2v_apg"}
        def pipeline(prompt, **kwargs):
            calls.append((prompt, kwargs))
            Path(kwargs["output_path"]).write_bytes(b"synthetic adapter fixture; not a real generated video")
        renderer.build = lambda *args: (builds.append(1) or pipeline)
        cfg = {"backend": "bernini", "generation": g, "seed": 42, "output": {"frames": 21, "fps": 10, "width": 80, "height": 60}}
        job = {"payload": {"renderer": cfg, "input_id": "source", "input": {"path": str(self.source), "sha256": sha(self.source)}, "prompt": "Exact RAW Prompt."}}
        with patch("run_prompt_probe.inspect_video", return_value={"frames": 21, "fps": 10, "width": 80, "height": 60}):
            first = renderer(job, self.root / "g1")
            job["payload"]["renderer"]["seed"] = 43
            second = renderer(job, self.root / "g2")
            self.assertEqual(builds, [1])
            self.assertEqual([c[0] for c in calls], ["Exact RAW Prompt."] * 2)
            self.assertEqual([c[1]["seed"] for c in calls], [42, 43])
            self.assertEqual(first["execution"]["settings"], g)
            self.assertEqual(second["execution"]["conditioning_source_indices"], list(range(21)))
            renderer.tokenizer = lambda *args, **kwargs: {"input_ids": [1] * 513}
            with self.assertRaisesRegex(ValueError, "tokenizer limit"):
                renderer(job, self.root / "oversized")
            self.assertEqual(len(calls), 2)
            job["payload"]["renderer"]["generation"] = {**g, "num_inference_steps": 20}
            with self.assertRaisesRegex(ValueError, "differs"):
                renderer(job, self.root / "changed")

    def test_submission_rejects_unsupported_renderer_before_model_calls(self):
        service = self.service()
        with self.assertRaisesRegex(ValueError, "resident renderer"):
            service.submit(self.task())
        self.assertEqual(service.queue.rows(), [])

    def card(self):
        card = card_fixture()
        card.update(source_video=str(self.source), source_sha256=sha(self.source))
        return freeze(card, "fixture")

    def test_final_judge_is_separate_and_reuses_prepared_evidence(self):
        card = self.card()
        truth = judgment_fixture(card)
        requests = []
        class Judge:
            model, reasoning_effort = "fixture-only", "none"
            def predict_json(self, **kwargs):
                requests.append(kwargs)
                if "For EVERY item" in kwargs["system_prompt"]:
                    return {k: copy.deepcopy(truth[k]) for k in ("items", "damage_review", "damages")}
                return {"ratings": {k: copy.deepcopy(v) for k, v in truth["ratings"].items()
                        if k not in {"scene_specific_design", "relative_originality"}}}
        service = self.service(config={"enable_final_evaluation": True}, model_factory=lambda role: Judge())
        case = {"case_id": "fixture-final", "method": "SECRET_METHOD", "seed": 42, "card_data": card,
                "output_video": str(self.source), "output_sha256": sha(self.source), "prompt": "SECRET_GENERATION_PROMPT",
                "online_critic": "SECRET_CRITIC"}
        service.submit_evaluation(case)
        engine = Engine(service.queue, service.directory, service, service.expand, interval=.01)
        engine.run(once=True)
        self.assertTrue(all(r["state"] == "complete" for r in service.queue.rows()), service.queue.rows())
        self.assertEqual(len(requests), 2)
        for req in requests:
            self.assertNotIn("SECRET", req["user_text"])
        self.assertEqual(load(service.directory / "evaluations/fixture-final/record.json")["result"]["ratings"]["aesthetic_mean"], 3.7)
        engine.run(once=True)
        self.assertEqual(len(requests), 2)

    def test_exact_pixel_cache_and_cached_evidence(self):
        calls = []
        cache = DecodeCache(decoder=lambda p: (calls.append(str(p)) or decode(p)))
        first = cache(self.source)
        duplicate = self.root / "duplicate.avi"
        shutil.copyfile(self.source, duplicate)
        second = cache(duplicate)
        self.assertEqual(len(calls), 1)
        self.assertEqual(first["times"], second["times"])
        self.assertEqual([x.tobytes() for x in first["frames"]], [x.tobytes() for x in second["frames"]])
        card = self.card()
        direct = prepare(card, self.source, self.root / "direct", root=ROOT, dense_ranges=[[0, 2]])
        cached = prepare(card, self.source, self.root / "cached", root=ROOT, dense_ranges=[[0, 2]], decoder=cache)
        self.assertEqual(direct["pairs"], cached["pairs"])
        self.assertEqual(direct["image_sha256"], cached["image_sha256"])
        small = DecodeCache(max_bytes=1, decoder=lambda p: (calls.append(str(p)) or decode(p)))
        small(self.source); small(self.source)
        self.assertEqual(small.bytes, 0)
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
