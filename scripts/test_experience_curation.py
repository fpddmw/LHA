"""Focused regression cases. Execution deferred; no live model/GPU dependency.

Run in the normal project test environment when verification is resumed.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("experience_usage", ROOT / "src/planner_harness/experience_usage.py")
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.call = self.root / "run/calls/event-0001"
        self.entry = {"id": "EX-a", "path": "knowledge/experience/curated/a.md", "title": "A",
                      "sha256": "a" * 64, "version": "1"}
        self.index = {"catalog_revision": "one", "items": {"EX-a": self.entry}}

    def tearDown(self):
        self.temp.cleanup()

    def save_input(self, payload):
        usage.write_json(self.call / "input.json", {"user_text": json.dumps(payload), "system_prompt": "tools", "images": []})

    def test_compacted_reference_does_not_claim_full_page_or_adoption(self):
        self.save_input({"knowledge_entrances": {"entrances": [self.entry]},
                         "notes": "I used EX-a", "recent_operations": [{"event_id": "old", "open": {"id": "EX-a"}}]})
        usage.record_exposure(self.call, self.index, "snapshot")
        r = usage.read_json(self.call / "experience-exposure.json")
        self.assertEqual([s["surface"] for s in r["surfaces"]], ["catalog_reference"])
        self.assertEqual(usage.call_status(self.call), "prepared_dispatch_unconfirmed")
        (self.call / "response.txt").write_text("A malformed answer still proves a response was saved.")
        self.assertEqual(usage.call_status(self.call), "response_recorded")

    def test_exact_page_and_retry_receipt_are_bound_once(self):
        page = {**self.entry, "text": "8: a fragment", "start_line": 8, "end_line": 8, "start_char": 2,
                "end_char": 12, "read_id": "read-0001"}
        self.save_input({"recent_operations": [{"result": {"materials": [page]}}]})
        usage.record_exposure(self.call, self.index, "snapshot")
        original = (self.call / "experience-exposure.json").read_bytes()
        usage.record_exposure(self.call, self.index, "snapshot")
        self.assertEqual(original, (self.call / "experience-exposure.json").read_bytes())
        self.assertEqual(usage.read_json(self.call / "experience-exposure.json")["surfaces"][0]["start_char"], 2)
        self.save_input({"recent_operations": []})
        with self.assertRaises(ValueError):
            usage.record_exposure(self.call, self.index, "snapshot")

    def test_missing_historical_exposure_is_not_fabricated(self):
        run = self.root / "run"
        self.save_input({"notes": "EX-a"})
        usage.write_json(run / "knowledge-snapshot.json", {"experiences": [self.entry], "documents": {}})
        usage.write_json(run / "state.json", {"config": {}, "reads": {}, "videos": {}, "evaluations": {},
            "events": [{"event_id": "e1", "request": {"action": "note", "arguments": {"text": "EX-a does not fit this case."}}}]})
        r = usage.project_run(run)
        self.assertEqual(r["surfaces"], [])
        self.assertFalse(r["calls"][0]["exposure_recorded"])
        self.assertEqual(r["model_references"][0]["basis"], "literal_model_reference")
        self.assertIn("unclassified", r["model_references"][0]["interpretation"])

    def test_batch_preserves_missing_and_excludes_heldout_without_reading(self):
        manifest = self.root / "manifest.json"
        usage.write_json(manifest, {"purpose": "development_maintenance", "runs": [
            {"id": "missing", "path": "missing", "data_role": "development"},
            {"id": "test", "path": "never-read", "data_role": "test"}]})
        result = usage.export_batch(manifest, self.root / "export")
        self.assertEqual(result["specified_runs"], 2)
        self.assertEqual(result["record_counts"], {"unavailable": 1, "excluded": 1})
        with self.assertRaises(ValueError):
            usage.export_batch(manifest, self.root / "export")


class CatalogTests(unittest.TestCase):
    def test_saved_snapshot_uses_saved_catalog_not_current_disk(self):
        sys.path.insert(0, str(ROOT / "src"))
        from planner_harness.creative_knowledge import CreativeKnowledge
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            original = CreativeKnowledge(ROOT)
            original.freeze(path)
            saved = usage.read_json(path)
            saved["curated_catalog"]["revision"] = "saved-identity"
            restored = CreativeKnowledge(ROOT, saved)
            self.assertEqual(restored.usage_index()["catalog_revision"], "saved-identity")
            self.assertNotIn("S1", restored.items)
            self.assertIn("understand-and-design", restored.items)

    def test_draft_or_missing_bound_content_is_rejected(self):
        sys.path.insert(0, str(ROOT / "src"))
        from planner_harness.creative_knowledge import CreativeKnowledge
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            knowledge = CreativeKnowledge(ROOT)
            knowledge.freeze(path)
            saved = usage.read_json(path)
            row = {"id": "EX-draft", "path": "knowledge/experience/curated/draft.md", "title": "Draft",
                "version": "1", "sha256": "a" * 64, "review_reference": "pending", "review_status": "draft",
                "summary": "A draft", "questions": [], "renderers": [], "evidence_ids": []}
            saved["curated_catalog"]["entries"] = [row]
            with self.assertRaises(ValueError):
                CreativeKnowledge(ROOT, saved)
            approved = copy.deepcopy(saved)
            approved["curated_catalog"]["entries"][0]["review_status"] = "approved"
            with self.assertRaises(ValueError):
                CreativeKnowledge(ROOT, approved)


if __name__ == "__main__":
    unittest.main()
