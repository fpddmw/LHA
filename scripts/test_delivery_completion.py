"""Offline execution checks: scripted Planner/Critic and fixture media, no API or GPU."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from test_rsi import RSITests, call, INTENT
from planner_harness.common import load, save
from planner_harness.delivery import verify_delivery
from planner_harness.runner import PlannerHarness
from test_planner_harness import ScriptedModel


class DeliveryTests(unittest.TestCase):
    setUp = RSITests.setUp
    tearDown = RSITests.tearDown
    start = RSITests.start
    resume = RSITests.resume
    generation = RSITests.generation
    review = RSITests.review
    first_generation = RSITests.first_generation

    def first(self, **kwargs):
        kwargs.setdefault("max_generations", None)
        kwargs.setdefault("max_turns", None)
        kwargs.setdefault("rsi", {"seed_sequence": {"start": 42, "step": 1}})
        return self.first_generation(completion_mode="delivery", **kwargs)

    def assessed(self):
        self.generation()
        self.resume([])
        self.review("partial")

    def test_five_generations_and_model_led_selection_with_unresolved_verdicts(self):
        self.first()
        for n in range(1, 6):
            self.assessed()
            action = call("generate", input_video="source" if n % 2 else "v1", prompt="Blue material relations.", intent=INTENT) if n < 5 else call("finish", video="v4", stop_reason="satisfied", message="The selected fixture candidate is suitable with the recorded tradeoff.")
            state = self.resume([action])
            self.assertEqual(state["status"], "waiting_tool" if n < 5 else "complete")
            context = json.loads(self.model.inputs[0]["user_text"])
            self.assertIsNone(context["resource_status"]["generation_limit"])
        self.assertEqual(state["generation_requests"], 5)
        self.assertEqual(len(state["jobs"]), 10)
        self.assertEqual([j["payload"]["renderer"]["seed"] for j in state["jobs"].values() if j["kind"] == "generate"], [42,43,44,45,46])
        self.assertEqual(verify_delivery(self.output)["selected"], "v4")
        self.assertTrue(state["final"]["unmet"])

    def test_resource_stop_is_incomplete_and_preserves_state_for_resume(self):
        self.first(); self.assessed()
        state = self.resume([call("finish", video="v1", stop_reason="budget")])
        self.assertEqual(state["status"], "budget_exhausted")
        with self.assertRaisesRegex(ValueError, "not reached"):
            verify_delivery(self.output)
        state = self.resume([call("generate", input_video="v1", prompt="Blue material.", intent=INTENT)])
        self.assertEqual(state["status"], "waiting_tool")
        self.assertEqual(state["generation_requests"], 2)
        self.assertEqual(state["interruption_history"][0]["video"], "v1")
        self.assertNotIn("final", state)

    def test_explicit_safety_cap_does_not_force_delivery(self):
        self.first(max_generations=3)
        for n in range(3):
            self.assessed()
            state = self.resume([call("generate", input_video="source", prompt="Blue material.", intent=INTENT)])
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertEqual(state["generation_requests"], 3)
        self.assertNotIn("final", state)
        with self.assertRaises(ValueError):
            verify_delivery(self.output)

    def test_no_promising_repair_is_blocked_not_delivered(self):
        self.first(); self.assessed()
        state = self.resume([call("finish", video="v1", stop_reason="no_promising_attempt", message="The result is not suitable and no viable repair remains.")])
        self.assertEqual(state["status"], "delivery_blocked")
        with self.assertRaises(ValueError):
            verify_delivery(self.output)

    def test_legacy_complete_budget_stop_is_rejected_by_delivery_gate(self):
        self.first(); self.assessed()
        state = self.resume([call("finish", video="v1", stop_reason="budget")])
        state["status"] = "complete"
        save(self.output / "state.json", state)
        with self.assertRaisesRegex(ValueError, "budget"):
            verify_delivery(self.output)

    def test_finite_seed_list_cannot_hide_an_unbounded_run_limit(self):
        with self.assertRaisesRegex(ValueError, "fixed integer seed"):
            self.first(rsi={"seed_schedule": [42,43,44]})

    def test_fixed_experiment_still_records_its_budget_termination(self):
        self.first_generation(max_generations=1, rsi={"seed_schedule": [42]})
        self.assessed()
        state = self.resume([call("finish", video="v1", stop_reason="budget")])
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["config"]["completion_mode"], "bounded_experiment")
        with self.assertRaises(ValueError):
            verify_delivery(self.output)

    def test_explicit_continuation_reopens_old_three_round_stop_without_reset(self):
        self.first_generation(max_generations=3, rsi={"seed_schedule": [42,43,44]})
        for n in range(1, 4):
            self.assessed()
            state = self.resume([call("generate", input_video="source", prompt="Blue material.", intent=INTENT) if n < 3 else call("finish", video="v2", stop_reason="budget")])
        frozen = state["config"]["rsi"]["critic_materials"].copy()
        old_events = len(state["events"])
        model = ScriptedModel([call("generate", input_video="v2", prompt="Continue the useful material treatment.", intent=INTENT)])
        h = PlannerHarness(self.output, model, root=self.root)
        state = h.resume(continue_delivery=True)
        self.assertEqual(state["status"], "waiting_tool")
        self.assertEqual(state["generation_requests"], 4)
        self.assertEqual(state["jobs"][state["pending_tool"]]["payload"]["renderer"]["seed"], 45)
        self.assertEqual(state["jobs"][state["pending_tool"]]["payload"]["input_id"], "v2")
        self.assertEqual(state["config"]["rsi"]["critic_materials"], frozen)
        self.assertEqual(len(state["events"]), old_events + 1)
        self.assertEqual(state["interruption_history"][0]["video"], "v2")
        self.assertEqual(state["delivery_continuations"][0]["previous_config"]["max_generations"], 3)
        self.assertFalse((self.output / "final.json").exists())


if __name__ == "__main__":
    unittest.main()
