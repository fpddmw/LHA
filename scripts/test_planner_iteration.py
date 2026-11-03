"""Regression for neutral budgets, source retrieval and persistent read context."""

import copy
import json
from pathlib import Path
import sys
import time
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness import accounting, continuation, resources
from planner_harness.creative_knowledge import CreativeKnowledge
from planner_harness.knowledge_search import search
from planner_harness.working_memory import retain, visible, fit_display
import test_creative_loop as fixtures


class BudgetTests(unittest.TestCase):
    def test_defaults_campaign_and_accounting_agree(self):
        from experiments.campaign import configuration, stage_config
        state = {"config": {}}
        policy = resources.configure(state)
        self.assertEqual((policy["max_generations"], policy["max_wall_seconds"]), (4, 5400))
        budget = accounting.validate_policy(accounting.default_online_policy())
        self.assertEqual(budget["online_task_budget"]["max_generations"], 4)
        self.assertEqual(budget["online_task_budget"]["wall_seconds"], 5400)
        config = configuration(ROOT / "configs/experiment-campaign.json")
        self.assertEqual((config["max_generations"], stage_config(config, "zero")["task_wall_seconds"]), (4, 5400))
        self.assertEqual(resources.configure({"config": {}}, backend="ditto")["max_wall_seconds"], 10800)

    def test_late_generation_needs_no_extra_explanation_and_hints_hide_numbers(self):
        state = {"config": {}, "videos": {}, "jobs": {}, "submitted_generation_ids": []}
        resources.configure(state)
        continuation.configure(state)
        for fraction in (0, .45, .65, .85):
            state["online_clock"] = {"started_unix": time.time() - resources.MAX_WALL_SECONDS * fraction}
            view = continuation.view(state)
            self.assertFalse(view["justification_required"])
            self.assertEqual(view["continuation_questions"], [])
            self.assertTrue(view["generation_available"])
            self.assertIsNone(continuation.authorize(state, {"prompt": "A new realization."}, "new"))
            self.assertNotRegex(view["budget_awareness"], r"[0-9%]")
            for wording in ("restraint", "prefer", "deliver", "confirm", "justify"):
                self.assertNotIn(wording, view["budget_awareness"].lower())
        for n in range(4):
            state["jobs"][str(n)] = {"kind": "generate"}
            state["submitted_generation_ids"].append(str(n))
        self.assertEqual(continuation.authorize(state, {}, "extra")["status"], "generation_unavailable")
        resources.check_wall(state)  # Reading and delivery are still available.
        state["online_clock"]["started_unix"] = time.time() - resources.MAX_WALL_SECONDS - 1
        with self.assertRaises(resources.TaskDeadline):
            resources.check_wall(state)


class MemoryTests(unittest.TestCase):
    def material(self, n, size=5000):
        return {"id": f"source-{n}", "read_id": f"read-{n}", "title": f"Source {n}",
                "sha256": str(n), "text": f"1: Useful source {n}. " + "detail " * (size // 7),
                "start_line": 1, "end_line": 2, "current_entries": ["catalog" * 1000]}

    def test_reads_above_old_limit_survive_and_rereads_do_not_duplicate(self):
        state = {}
        pages = [self.material(i) for i in range(8)]
        for n, material in enumerate(pages):
            retain(state, [material], f"event-{n}")
        self.assertGreater(sum(len(r["material"]["text"]) for r in state["knowledge_memory"]), 18000)
        self.assertEqual(len(state["knowledge_memory"]), 8)
        self.assertFalse(state.get("memory_evictions"))
        self.assertTrue(all("current_entries" not in r["material"] for r in state["knowledge_memory"]))
        again = {**pages[0], "read_id": "reread"}
        retain(state, [again], "later")
        self.assertEqual(len(state["knowledge_memory"]), 8)
        payload = {"recent_operations": [{"result": {"materials": [copy.deepcopy(again)]}}]}
        visible(payload, state)
        self.assertNotIn("text", payload["recent_operations"][0]["result"]["materials"][0])
        self.assertEqual(payload["working_memory"]["retained_reads"][-1]["material"]["text"], pages[0]["text"])

    def test_actual_capacity_keeps_each_source_and_restores_complete_pages(self):
        state = {}
        for n in range(12):
            retain(state, [self.material(n)], f"event-{n}")
        original = copy.deepcopy(state)
        payload = {"task": "Original request"}
        visible(payload, state)
        fit_display(payload, 16000, 500)
        rows = payload["working_memory"]["retained_reads"]
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(r["material"]["text"] and r["open"] for r in rows))
        self.assertTrue(all(not r["material"]["text_is_complete"] for r in rows))
        self.assertLessEqual(500 + len(json.dumps(payload, ensure_ascii=False, indent=2)), 16000)
        self.assertEqual(state, original)
        visible(payload, state)
        self.assertEqual([r["material"]["text"] for r in payload["working_memory"]["retained_reads"]],
                         [r["material"]["text"] for r in original["knowledge_memory"]])


class Corpus:
    enabled = True

    def __init__(self, rows):
        self.items = {str(n): {"id": str(n), "path": f"{n}.md", "kind": kind, "title": title, **meta}
                      for n, (title, kind, text, meta) in enumerate(rows)}
        self.texts = {str(n): text for n, (_, _, text, _) in enumerate(rows)}

    def document(self, row):
        return {"text": self.texts[row["id"]]}


class SearchTests(unittest.TestCase):
    def test_named_work_and_related_features_are_distinct(self):
        rows = [
            ("Grand Hotel", "entries", "A silver black and white lobby. Hotel hotel hotel grand hotel.", {}),
            ("Pastel architecture", "entries", "Pink pastel walls and ordered decorative layers organize the hotel scene through balanced symmetry.", {}),
        ]
        q = "Grand Budapest Hotel pastel pink symmetry"
        found = search(Corpus(rows), q, scope="style")
        self.assertFalse(found["named_reference"]["found_in_corpus"])
        self.assertEqual(found["matches"][0]["title"], "Pastel architecture")
        self.assertEqual(found["matches"][0]["match_type"], "related_reference")
        self.assertIn("budapest", found["terms_absent_from_corpus"])
        rows.append(("Grand Budapest Hotel", "entries", "Pastel colors shape a specific named reference, with a deliberately arranged interior.", {}))
        found = search(Corpus(rows), q, scope="style")
        self.assertTrue(found["named_reference"]["found_in_corpus"])
        self.assertEqual(found["matches"][0]["title"], "Grand Budapest Hotel")

    def test_metadata_search_precedes_top_k_and_style_scope_has_prose(self):
        rows = [(f"Generic {n}", "entries", "Hotel architecture and cinematic lighting.", {}) for n in range(20)]
        rows += [("Identity account", "experience", "A useful body description.", {"summary": "lost face identity conditioning"})]
        result = search(Corpus(rows), "lost face", scope="experience")
        self.assertEqual(result["matches"][0]["title"], "Identity account")
        result = search(Corpus(rows), "hotel", scope="style")
        self.assertTrue(all(row["kind"] == "entries" for row in result["matches"]))

    def test_actual_frozen_full_none_and_chinese_discovery(self):
        for mode in ("full", "none"):
            with tempfile.TemporaryDirectory() as tmp:
                snapshot = Path(tmp) / "knowledge.json"
                CreativeKnowledge(ROOT, experience_mode=mode).freeze(snapshot)
                knowledge = CreativeKnowledge(ROOT, snapshot, experience_mode=mode)
            result = knowledge.search("水彩", scope="style")
            self.assertTrue(result["matches"])
            self.assertTrue(all(r["kind"] in {"entries", "guides", "domain_references"} for r in result["matches"]))
            self.assertTrue(all(r["open"] and r["matches"] for r in result["matches"]))
            experience = knowledge.search("人脸", scope="experience")
            if mode == "none":
                self.assertEqual(experience["matches"], [])
            else:
                self.assertEqual(experience["matches"][0]["id"], "EX-instance-identity")


class LoopTests(unittest.TestCase):
    setUp, tearDown = fixtures.CreativeTests.setUp, fixtures.CreativeTests.tearDown
    start, respond, resume = fixtures.CreativeTests.start, fixtures.CreativeTests.respond, fixtures.CreativeTests.resume

    def test_actual_case_reads_survive_search_generation_and_finish(self):
        ids = ["understand-and-design", "experience-map", "EX-environment-replacement",
               "EX-renderer-profiles", "review", "understand-and-revise", "EX-instance-identity"]
        self.start([
            fixtures.action("read", targets=[{"id": i} for i in ids[:4]]),
            fixtures.action("read", targets=[{"id": i} for i in ids[4:]]),
            fixtures.action("search", query="pastel pink symmetry", scope="style"),
            fixtures.action("generate", input_video="source", prompt="A blue treatment."),
        ])
        context = json.loads(self.model.inputs[-1]["user_text"])
        retained = context["working_memory"]["retained_reads"]
        self.assertEqual([r["material"]["id"] for r in retained], ids)
        self.assertTrue(all(r["material"]["text"] for r in retained))
        self.assertFalse(self.h.state.get("memory_evictions"))
        original_text = [r["material"]["text"] for r in retained]
        original_limit = self.h.state["config"]["max_context_chars"]
        self.h.state["config"]["max_context_chars"] = 24000
        small, images, _ = self.h.context()
        short = json.loads(small)["working_memory"]["retained_reads"]
        self.assertEqual([r["material"]["id"] for r in short], ids)
        self.assertTrue(all(r["material"]["text"] for r in short))
        self.assertLessEqual(len(small) + len(self.h.system), 24000)
        self.h.state["config"]["max_context_chars"] = original_limit
        restored = json.loads(self.h.context()[0])["working_memory"]["retained_reads"]
        self.assertEqual([r["material"]["text"] for r in restored], original_text)
        self.respond()
        self.resume([fixtures.action("finish", video="v1", message="Select this result with its observed tradeoffs.")])
        self.assertEqual(self.h.state["status"], "complete")
        self.assertEqual(len(self.model.inputs), 1)
        self.assertEqual(self.h.state["generation_requests"], 1)


if __name__ == "__main__":
    unittest.main()
