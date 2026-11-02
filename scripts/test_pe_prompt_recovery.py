"""Original-clock recovery and isolated service setup; no API or GPU calls."""
from pathlib import Path
import copy
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import test_pe_loop as pe_fixtures
from test_unified_results import Fixture
from experiments import recovery, unified_benchmark as unified, render_profiles
from planner_harness import accounting
from planner_harness.common import load, save, sha
from planner_harness.resources import ResourceExhausted


class RecoveryTests(Fixture):
    setup_loop, run_loop = pe_fixtures.PELoopTests.setup_loop, pe_fixtures.PELoopTests.run_loop

    def failed_round(self):
        batch, runtime = self.setup_loop(n=2)
        task = batch["topics"][0]
        worker = self.output / "workers/0"
        original = runtime.render

        def render(topic, method, prompt, seed, number, scope):
            if number == 0:
                return original(topic, method, prompt, seed, number, scope)
            body = {"id": topic["id"] + "__pe-loop__1", "kind": "generate", "mode": "live",
                    "accounting_scope": scope, "payload": {"input_id": "source", "input": topic["source_info"],
                    "prompt": prompt, "renderer": render_profiles.renderer_spec(topic, batch, seed)}}
            request = {**body, "sha256": unified.signature(body)}
            folder = worker / "baselines" / topic["id"] / "pe-loop/1"
            save(folder / "request.json", request)
            save(folder / "response.json", {"request_sha256": request["sha256"], "mode": "live", "status": "failed",
                 "error": "ValueError: Prompt exceeds tokenizer limit; automatic truncation is disabled"})
            raise RuntimeError("Recorded pre-fix render failure")

        runtime.render = render
        with self.assertRaisesRegex(RuntimeError, "pre-fix"):
            self.run_loop(batch, runtime)
        directory = self.output / "methods" / task["id"] / "pe-loop"
        save(directory / "settlement.json", {"status": "failed", "batch_sha256": load(self.output / "batch.json")["sha256"]})
        save(worker / "config.json", {"workflow": "creative_loop_v1", "experiment_profile": "old-profile.json"})
        ledger = load(self.output / "accounting/ledger.json")
        ledger["topics"][task["id"]]["closed"] = True
        accounting._event(ledger, "topic_close", task["id"], {"unused_admission_capacity_released": True})
        save(self.output / "accounting/ledger.json", ledger)
        return task, directory, worker, ledger

    def test_plan_and_execution_keep_receipts_clock_and_accounting(self):
        task, directory, worker, ledger = self.failed_round()
        original = {str(p): sha(p) for p in directory.glob("rounds/*/*.json")}
        plan = recovery.recover_pe_prompt(self.output, task["id"], "0", "Known length failure")
        self.assertEqual((plan["status"], plan["round"], plan["topic_closed"]), ("recoverable", 2, True))
        self.assertEqual(load(self.output / "accounting/ledger.json"), ledger)
        created = []

        class Service:
            def __init__(self, queue, path, root, config):
                self.directory, self.config = path, config
                created.append(self)
            def close(self):
                pass

        def execute(root, output, selected, method, batch, runtime):
            now = load(self.output / "accounting/ledger.json")
            self.assertFalse(now["topics"][task["id"]]["closed"])
            self.assertEqual(now["topics"][task["id"]]["lanes"], ledger["topics"][task["id"]]["lanes"])
            self.assertEqual(runtime.directory, worker)
            self.assertNotEqual(runtime.directory, runtime.service.directory)
            self.assertEqual(runtime.service.config["budget"], load(self.output / "accounting/policy.json"))
            self.assertNotIn("experiment_profile", runtime.service.config)
            return {"status": "ready", "partial": False}

        with patch("server_runtime.service.Service", Service), patch.object(unified, "execute_method", side_effect=execute):
            result = recovery.recover_pe_prompt(self.output, task["id"], "0", "Known length failure", execute=True)
        self.assertEqual(result["status"], "ready")
        self.assertEqual({p: sha(p) for p in original}, original)
        self.assertEqual(load(self.output / "accounting/ledger.json")["operations"], ledger["operations"])
        self.assertTrue(list((directory / "settlement-history").glob("*.json")))
        self.assertEqual(len(created), 1)
        self.assertEqual(recovery.recover_pe_prompt(self.output, task["id"], "0", "Known length failure", execute=True)["status"], "complete")

    def test_expired_closed_task_remains_closed_for_cached_settlement(self):
        task, directory, worker, ledger = self.failed_round()
        class Service:
            def __init__(self, queue, path, root, config):
                self.directory = path
            def close(self):
                pass
        with patch("server_runtime.service.Service", Service), \
             patch.object(accounting, "check_task", side_effect=ResourceExhausted("original deadline")), \
             patch.object(unified, "execute_method", return_value={"status": "ready", "partial": True}):
            recovery.recover_pe_prompt(self.output, task["id"], "0", "Known length failure", execute=True)
        self.assertEqual(load(self.output / "accounting/ledger.json"), ledger)

    def lock_failure(self):
        task, directory, worker, ledger = self.failed_round()
        slot = worker / "baselines" / task["id"] / "pe-loop/1-prompt-1"
        request = copy.deepcopy(load(slot.parent / "1/request.json"))
        request.pop("sha256")
        request["id"] += "-prompt-1"
        request["payload"]["prompt"] = "The saved compact blue scene."
        request["sha256"] = unified.signature(request)
        save(slot / "request.json", request)
        save(slot / "response.json", {"request_sha256": request["sha256"], "mode": "live", "status": "failed", "error": "EOFError: "})
        prompt = request["payload"]["prompt"]
        save(slot.parent / "1/prompt-revisions/1/prompt.json", {"value": prompt, "sha256": unified.signature(prompt)})
        save(directory / "prompt-length-recovery/execution.json", {"round": 2, "reason": "Original length recovery"})
        save(directory / "prompt-length-recovery/service/config.json", {"workflow": "creative_loop_v1"})
        return task, directory, worker, ledger, slot

    def test_lock_retry_preserves_prompt_and_original_receipts_then_reuses_candidate(self):
        from recover_pe_prompt import retry_render
        from planner_harness.video import Video
        task, directory, worker, ledger, slot = self.lock_failure()
        request = load(slot / "request.json")
        originals = {p: sha(p) for p in (slot / "request.json", slot / "response.json", directory / "rounds/0002/prompt.json")}
        class Service:
            def __init__(self, queue, path, root, config):
                self.directory = path
            def model_factory(self, role):
                raise AssertionError("Render retry must not call a model")
            def close(self):
                pass
        value = {"video": Video(self.source, self.root / "media").info,
                 "response": str(self.root / "new-response.json"), "seed": request["payload"]["renderer"]["seed"]}
        with patch("server_runtime.service.Service", Service), patch.object(unified.Runtime, "_render", return_value=value) as render:
            result = retry_render(self.output, task["id"], "0", "1-prompt-1", "Confirmed failed initialization", execute=True)
            self.assertEqual(result["status"], "candidate_ready")
            self.assertEqual(render.call_args.args[2:5], (request["payload"]["prompt"], value["seed"], "1-prompt-1-retry-1"))
            retry_render(self.output, task["id"], "0", "1-prompt-1", "Confirmed failed initialization", execute=True)
            self.assertEqual(render.call_count, 1)
        candidate = load(directory / "rounds/0002/candidate.json")["value"]
        self.assertEqual(candidate["prompt"], request["payload"]["prompt"])
        self.assertEqual(candidate["id"], "v2")
        self.assertEqual(candidate["prompt_revisions"], 1)
        self.assertEqual({p: sha(p) for p in originals}, originals)
        self.assertEqual(accounting.load_ledger(self.output / "accounting"), ledger)

    def test_lock_retry_respects_deadline_and_rejects_dispatched_or_unknown_requests(self):
        from recover_pe_prompt import retry_render
        task, directory, worker, ledger, slot = self.lock_failure()
        args = (self.output, task["id"], "0", "1-prompt-1", "Confirmed failed initialization")
        with patch.object(accounting, "check_task", side_effect=ResourceExhausted("original deadline")), \
             patch.object(unified.Runtime, "_render") as render:
            self.assertEqual(retry_render(*args, execute=True)["status"], "deadline_settlement")
            render.assert_not_called()
        response = load(slot / "response.json")
        save(slot / "response.json", {**response, "outcome_unknown": True})
        with self.assertRaisesRegex(ValueError, "before render dispatch"):
            retry_render(*args)
        save(slot / "response.json", response)
        save(slot / "render-started.json", {"request_sha256": response["request_sha256"]})
        with self.assertRaisesRegex(ValueError, "before render dispatch"):
            retry_render(*args)


if __name__ == "__main__":
    unittest.main()
