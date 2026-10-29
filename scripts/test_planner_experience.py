"""Experience publication checks use temporary libraries, never shared knowledge."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness import experience
from planner_harness.common import load, save, sha


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = self.root / "knowledge/experience/choose.md"
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b"Original common-sense advice.\r\n")
        self.original = sha(self.target)
        save(self.root / "knowledge/experience/catalog.json", [{"id": "choose", "path": "knowledge/experience/choose.md", "version": 1}])
        self.proposal = self.root / "proposal/proposal.json"
        save(self.proposal, {"status": "proposed", "topic": "choose", "target": "knowledge/experience/choose.md",
            "base_sha256": self.original, "proposed_text": "Revised common-sense advice.\n", "evidence": [{"test": "fixture, not empirical evidence"}]})

    def tearDown(self):
        self.temp.cleanup()

    def test_publication_retry_and_reviewed_rollback(self):
        record = experience.publish(self.proposal, "test reviewer", self.root)
        self.assertEqual(record["new_version"], 2)
        self.assertEqual(experience.publish(self.proposal, "test reviewer", self.root), record)
        destination = self.root / "rollback"
        experience.rollback_proposal("choose", self.original, destination, self.root)
        self.assertEqual(sha(self.target), record["new_sha256"])
        experience.publish(destination / "proposal.json", "test reviewer", self.root)
        self.assertEqual(sha(self.target), self.original)

    def test_stale_base_and_stable_manual_are_rejected(self):
        p = load(self.proposal)
        p["target"] = "knowledge/READING.md"
        save(self.proposal, p)
        with self.assertRaisesRegex(ValueError, "outside"):
            experience.publish(self.proposal, "test", self.root)
        p["target"] = "knowledge/experience/choose.md"
        p["base_sha256"] = "0" * 64
        save(self.proposal, p)
        with self.assertRaisesRegex(ValueError, "changed"):
            experience.publish(self.proposal, "test", self.root)

    def test_interrupted_publication_recovers_same_review(self):
        original_replace = experience.os.replace
        calls = []
        def interrupt(source, target):
            if str(source).endswith(".publication-tmp"):
                calls.append(str(target))
                if len(calls) == 2:
                    raise OSError("Injected interruption")
            return original_replace(source, target)
        with patch.object(experience.os, "replace", side_effect=interrupt):
            with self.assertRaisesRegex(OSError, "Injected"):
                experience.publish(self.proposal, "test", self.root)
        self.assertEqual(load(self.root / "knowledge/experience/.publication.json")["status"], "pending")
        record = experience.publish(self.proposal, "test", self.root)
        self.assertEqual(record["new_version"], 2)
        self.assertEqual(sha(self.target), record["new_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
