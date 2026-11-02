"""Compatibility imports preserve one implementation; creative identity stays narrow."""

import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]


class BoundaryTests(unittest.TestCase):
    def test_twenty_two_rsi_aliases_share_actual_compat_modules(self):
        names = sorted(p.stem for p in (ROOT / "src/planner_harness").glob("rsi_*.py"))
        self.assertEqual(len(names), 22)
        for name in names:
            old = importlib.import_module("planner_harness." + name)
            actual = importlib.import_module("planner_harness.compat.rsi." + name)
            self.assertIs(old, actual)
            self.assertIn("/compat/rsi/", actual.__file__)
            self.assertLess(
                len((ROOT / "src/planner_harness" / f"{name}.py").read_text().splitlines()), 10
            )

    def test_legacy_alias_and_resource_root_preserve_old_locations(self):
        from planner_harness.compat import HARNESS_ROOT

        self.assertEqual(HARNESS_ROOT, ROOT / "src/planner_harness")
        for name in ("experience", "ledger", "task_criteria"):
            old = importlib.import_module("planner_harness." + name)
            self.assertIs(old, importlib.import_module("planner_harness.compat.legacy." + name))
        self.assertTrue((HARNESS_ROOT / "OPERATIONS.md").exists())
        self.assertTrue((HARNESS_ROOT / "RSI.md").exists())

    def test_protocol_contains_accounting_supervision_and_standalone_not_compat(self):
        from planner_harness import protocol_sources as p

        actual = p.protocol_inventory(ROOT)
        for name in (
            "src/planner_harness/accounting.py",
            "src/planner_harness/supervisor.py",
            "scripts/accounting_worker.py",
            "scripts/run_bernini_benchmark.py",
        ):
            self.assertIn(name, actual)
        self.assertFalse(
            any("/compat/" in key or "/rsi_" in key or key.endswith("/RSI.md") for key in actual)
        )
        audit = p.audit_inventory(ROOT)
        self.assertIn("src/planner_harness/compat/rsi/rsi_data.py", audit)

        def changed(path):
            return "changed" if path.name == "accounting.py" else original(path)

        original = p.sha
        p._protocol_inventory.cache_clear()
        try:
            with patch.object(p, "sha", side_effect=changed):
                self.assertNotEqual(actual, p.protocol_inventory(ROOT))
        finally:
            p._protocol_inventory.cache_clear()
        with patch.object(
            p,
            "sha",
            side_effect=lambda path: "changed" if path.name == "RSI.md" else original(path),
        ):
            self.assertEqual(actual, p.protocol_inventory(ROOT))
            self.assertNotEqual(audit, p.audit_inventory(ROOT))

    def test_rsi_replay_hashes_actual_compatibility_implementation(self):
        from planner_harness.compat.rsi import rsi_replay as replay

        before = replay.harness_hashes()
        self.assertIn("compat/rsi/rsi_calls.py", before)
        self.assertIn("compat/legacy/actions.py", before)
        original = replay.sha
        with patch.object(
            replay,
            "sha",
            side_effect=lambda path: (
                "changed" if path.as_posix().endswith("compat/rsi/rsi_calls.py") else original(path)
            ),
        ):
            self.assertNotEqual(before, replay.harness_hashes())

    def test_current_dispatch_does_not_import_legacy_actions(self):
        from planner_harness import PlannerHarness
        from planner_harness import creative_actions

        harness = PlannerHarness("/tmp/unused-boundary-fixture", None)
        harness.state = {"config": {"workflow": "creative_loop_v1"}}
        with patch.object(creative_actions, "operate", return_value={"current": True}) as called:
            self.assertEqual(harness._operate({"action": "fixture"}, "event"), {"current": True})
            called.assert_called_once()


if __name__ == "__main__":
    unittest.main()
