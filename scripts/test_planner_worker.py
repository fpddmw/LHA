"""Tool boundary checks; replay and mocked evaluation are explicitly synthetic."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import test_planner_harness as legacy
import run_planner_worker as worker
from planner_harness.common import load, save, sha
from planner_harness.execution import signature, prepare_profile, request_job, collect
from planner_harness.video import Video


class WorkerTests(unittest.TestCase):
    setUp = legacy.Tests.setUp
    tearDown = legacy.Tests.tearDown

    def job(self):
        body = {"id": "test", "kind": "generate", "mode": "replay", "payload": {
            "input": {"path": str(self.source), "sha256": sha(self.source)}, "prompt": "Make it blue.", "renderer": {}}}
        job = {**body, "sha256": signature(body)}
        request = self.root / "job/request.json"
        save(request, job)
        return request, job

    def test_replay_receipt_and_duplicate_worker_reuse(self):
        request, job = self.job()
        argv = ["worker", "--request", str(request), "--replay-video", str(self.source),
                "--provenance", "Synthetic test fixture; no generation occurred."]
        with patch.object(sys, "argv", argv):
            worker.main()
            first = request.with_name("response.json").read_bytes()
            worker.main()
        response = load(request.with_name("response.json"))
        self.assertEqual(first, request.with_name("response.json").read_bytes())
        self.assertEqual(response["mode"], "replay")
        self.assertEqual(response["request_sha256"], job["sha256"])
        self.assertEqual(response["payload"]["execution"]["preflight"], "not_run")

    def test_changed_input_is_a_failed_worker_response(self):
        request, _ = self.job()
        self.source.write_bytes(b"changed")
        with patch.object(sys, "argv", ["worker", "--request", str(request)]):
            worker.main()
        response = load(request.with_name("response.json"))
        self.assertEqual(response["status"], "failed")
        self.assertIn("hash mismatch", response["error"])

    def test_signed_request_cannot_be_modified(self):
        request, job = self.job()
        job["payload"]["prompt"] = "Another instruction."
        save(request, job)
        with patch.object(sys, "argv", ["worker", "--request", str(request)]):
            with self.assertRaisesRegex(ValueError, "signature"):
                worker.main()
        self.assertFalse(request.with_name("response.json").exists())

    def test_existing_evaluator_contract_is_frozen_and_passed_through(self):
        card = load(ROOT / "examples/evaluation/041_short.card.json")
        task = {"text": card["requirement"], "source": {"sha256": card["source_sha256"]}}
        cfg = prepare_profile({"evaluation": {"card": "examples/evaluation/041_short.card.json"}}, ROOT, task)
        self.assertEqual(cfg["evaluation"]["card_data"], card)
        with self.assertRaisesRegex(ValueError, "exact user request"):
            prepare_profile(cfg, ROOT, {**task, "text": "Changed task"})
        p = {"video": {"path": str(self.source), "sha256": sha(self.source)}, "original": task["source"],
             "request": task["text"], "evaluation": cfg["evaluation"], "question": "Inspect the writing action."}
        with patch("evaluation.media.prepare", return_value={"synthetic": True}) as prepare, \
             patch("evaluation.judges.judge", return_value={"synthetic": "judgment"}), \
             patch("evaluation.scoring.score", return_value={"synthetic": "scores"}), \
             patch("vlm.codex_vlm.CodexVisionModel"):
            result = worker.evaluate({"payload": p}, self.root, ROOT)
        self.assertEqual(result["protocol"]["version"], card["card_sha256"])
        self.assertEqual(result["scores"], {"synthetic": "scores"})
        self.assertIn("online_feedback", result["usage"])
        self.assertEqual(prepare.call_args.kwargs["mapping"], None)

    def live_fixture(self):
        output = self.root / "contract-test"
        source = Video(self.source, output).info
        state = {"config": {"mode": "loop", "max_generations": 2, "execution": {"mode": "live", "renderer": {
            "seed": 42, "generation": {"steps": 1}, "output": {"frames": 20, "fps": 10, "width": 80, "height": 60}}}},
            "videos": {"source": source}, "jobs": {}, "events": [], "observations": [], "generation_requests": 0}
        h = SimpleNamespace(state=state, output=output, checkpoint=lambda: None)
        request_job(h, "generate", {"input_video": "source", "prompt": "Blue."}, "event-1")
        job = state["jobs"][state["pending_tool"]]
        response = {"request_sha256": job["sha256"], "status": "complete", "mode": "live", "payload": {
            "video": {"path": str(self.source), "sha256": sha(self.source)}, "execution": {
                "backend": "synthetic-contract-fixture", "requested_prompt": "Blue.", "effective_prompt": "Blue.",
                "input_sha256": source["sha256"], "preflight": "passed", "model_revision": "test-only",
                "code_revision": "test-only", "token_count": 2, "token_limit": 10, "settings": {"steps": 1},
                "seed": 42, "conditioning_source_indices": list(range(20))}}}
        path = output / "jobs" / job["id"] / "response.json"
        return h, path, response

    def test_live_contract_records_original_time_mapping(self):
        h, path, response = self.live_fixture()
        save(path, response)
        self.assertTrue(collect(h))
        result = h.state["videos"]["v1"]
        self.assertEqual(result["parent"], "source")
        self.assertEqual(result["time_mapping"]["source_times_seconds"], [i / 10 for i in range(20)])
        self.assertIsNone(h.state["pending_tool"])

    def test_effective_prompt_mismatch_is_not_collected(self):
        h, path, response = self.live_fixture()
        response["payload"]["execution"]["effective_prompt"] = "Silently changed."
        save(path, response)
        with self.assertRaisesRegex(ValueError, "Effective renderer text"):
            collect(h)
        self.assertNotIn("v1", h.state["videos"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
