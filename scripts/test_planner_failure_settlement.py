"""Register saved Planner outcomes after a provider failure; no API/GPU calls."""
from pathlib import Path
import copy
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from test_unified_results import Fixture
from experiments import recovery, unified_benchmark as unified, results
from planner_harness import accounting, candidate_selection
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from planner_harness.integrity import IntegrityError
from planner_harness.video import Video


class PlannerFailureTests(Fixture):
    def failed_loop(self, *, with_selection=True):
        self.prepare(methods=["full"], best_of_n=None, splits=["test"])
        batch = load(self.output / "batch.json")
        topic = batch["topics"][0]
        accounting.install(self.output / "accounting")
        scope = accounting.topic_scope(self.output, topic["id"], lane="full")
        clock = accounting.start_task(scope, wall_seconds=9000)
        run = self.output / "workers/0/tasks" / (topic["id"] + "__full") / "run"
        info = Video(self.source, self.root / "info").info
        videos = {"v" + str(i): {**info, "job_id": "g" + str(i)} for i in range(1, 4)}
        state = {"status": "execution_failed", "request": {"text": topic["request"]},
                 "config": {"workflow": "creative_loop_v1", "execution": {"review": batch["review"]}},
                 "videos": {"source": info, **videos},
                 "jobs": {"g" + str(i): {"payload": {"renderer": {"seed": 41 + i}}} for i in range(1, 4)},
                 "submitted_generation_ids": ["g1", "g2", "g3"],
                 "reviews": {identity: {"status": "complete", "mode": "critic"} for identity in videos},
                 "delivery_candidate": "v1", "online_clock": clock,
                 "final": {"video": None, "outcome": "incomplete", "stop_reason": "execution_failure",
                           "message": "Recorded provider overload fixture"}}
        if with_selection:
            candidate_selection.refresh(state)
        save(run / "state.json", state)
        loop = {"arm": "full", "outcome": "execution_failed", "successful": False, "selected": None,
                "first": "v1", "record_directory": str(run), "videos": videos,
                "binding": {"topic": topic["id"], "source": topic["source_sha256"],
                            "request": signature({"text": topic["request"]}), "profile": batch["profile_sha256"]},
                "completion_record": {"path": str(run / "state.json"), "sha256": sha(run / "state.json")}}
        loop["sha256"] = signature(loop)
        save(self.output / "topics" / topic["id"] / "full.json", loop)
        save(self.output / "methods" / topic["id"] / "full/settlement.json",
             {"status": "execution_failed", "entry_sha256": None})
        return batch, topic, run, state

    def test_failure_registers_all_candidates_without_changing_native_failure(self):
        batch, topic, run, state = self.failed_loop()
        receipt = self.output / "topics" / topic["id"] / "full.json"
        originals = {p: sha(p) for p in (run / "state.json", receipt)}
        ledger = accounting.load_ledger(self.output / "accounting")
        plan = recovery.settle_planner_failure(self.output, topic["id"], "0")
        self.assertEqual(plan["selection"]["selected"], "v1")
        self.assertEqual((plan["model_calls"], plan["renders"], plan["planner_confirmed"]), (0, 0, False))
        original_execute = unified.execute_method
        def execute(root, *args):
            return original_execute(self.repo, *args)
        with patch.object(unified, "execute_method", side_effect=execute), \
             patch.object(accounting, "check_task", side_effect=AssertionError("Cached registration needs no admission")):
            result = recovery.settle_planner_failure(self.output, topic["id"], "0", execute=True)
        self.assertEqual((result["status"], result["run_outcome"], result["partial"], result["planner_confirmed"]),
                         ("ready", "execution_failed", True, False))
        row = results.find(self.registry, topic["sample_id"], topic["prompt_form"], "full", 42)
        self.assertEqual(row["evidence"]["delivery_kind"], "interrupted_delivery")
        self.assertEqual(row["evidence"]["actual_generations"], 3)
        self.assertEqual(row["evidence"]["run_outcome"], "execution_failed")
        self.assertFalse(row["evidence"]["planner_confirmed"])
        self.assertEqual([c["roles"] for c in row["candidates"]], [["first", "selected"], [], ["last"]])
        self.assertEqual({p: sha(p) for p in originals}, originals)
        self.assertEqual(accounting.load_ledger(self.output / "accounting"), ledger)
        self.assertEqual(recovery.settle_planner_failure(self.output, topic["id"], "0", execute=True)["status"], "complete")

    def test_no_committed_choice_preserves_failed_outcome(self):
        batch, topic, run, state = self.failed_loop(with_selection=False)
        class Runtime:
            def loop(self, *args):
                raise AssertionError("No live loop call")
        result = unified.execute_method(self.repo, self.output, topic, "full", batch, Runtime())
        self.assertEqual(result, {"status": "execution_failed", "entry_sha256": None})
        self.assertIsNone(results.find(self.registry, topic["sample_id"], topic["prompt_form"], "full", 42))

    def test_saved_choice_preserves_identity_and_deadline_requirement(self):
        batch, topic, run, state = self.failed_loop()
        self.assertEqual(candidate_selection.recorded_choice(state)["selected"], "v1")
        with self.assertRaisesRegex(IntegrityError, "persisted freeze"):
            candidate_selection.deadline_choice(state)
        changed = copy.deepcopy(state)
        changed["delivery_candidate"] = "v2"
        with self.assertRaises(IntegrityError):
            candidate_selection.recorded_choice(changed)

    def test_supervisor_failure_without_native_state_keeps_its_outcome(self):
        from experiments.creative_benchmark import isolated_arm
        self.prepare(methods=["full"], best_of_n=None, splits=["test"])
        batch = load(self.output / "batch.json")
        topic = batch["topics"][0]
        accounting.install(self.output / "accounting")
        for outcome in ("execution_failed", "execution_unknown"):
            with self.subTest(outcome=outcome):
                receipt = isolated_arm(self.root / outcome, topic, "full", batch["profile_sha256"],
                    reason="Fixture worker unavailable", outcome=outcome, evidence={})
                save(self.output / "topics" / topic["id"] / "full.json", receipt)
                result = unified.execute_method(self.repo, self.output, topic, "full", batch, object())
                self.assertEqual(result, {"status": outcome, "entry_sha256": None})


if __name__ == "__main__":
    unittest.main()
