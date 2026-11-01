"""RSI integration and publication checks. All model answers and videos are fixtures."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from test_planner_harness import Tests as Legacy, ScriptedModel
from planner_harness.common import load, save, sha
from planner_harness.runner import PlannerHarness
from planner_harness.knowledge import Knowledge
from planner_harness import ledger, rsi_data as data, rsi_validation as validation
from planner_harness.rsi_calls import call_once
from planner_harness.rsi_replay import replay
from planner_harness.rsi_support import candidate_knowledge, experience_digest
from critic_harness.adapter import critique


def call(action, **arguments):
    return {"action": action, "arguments": arguments}


REQ = [{"id": "E1", "text": "Make the scene blue.", "kind": "edit", "priority": "core"},
       {"id": "P1", "text": "Keep the scene layout.", "kind": "preserve", "priority": "core", "origin": "source_relation"}]
INTENT = {"targets": ["E1"], "change": "Describe blue surfaces.", "expect": "The scene reads as blue.", "checks": {"E1": "pass"}}


class RSITests(unittest.TestCase):
    tearDown = Legacy.tearDown

    def setUp(self):
        Legacy.setUp(self)
        save(self.root / "knowledge/source-map.json", {"entries": [], "domain_references": [], "guides": [], "model_experience": [], "totals": {}})
        for name in ("README.md", "READING.md", "INTEGRATION.md"):
            (self.root / "knowledge" / name).write_text("Read to understand the visual task.\n", encoding="utf-8")
        catalog = [{"id": "experience-map", "path": "knowledge/experience/map.md", "title": "Experience map", "version": 1},
                   {"id": "task-advice", "path": "knowledge/experience/task-advice.md", "title": "Advice", "version": 1,
                    "cards": [{"id": "A1", "summary": "Choose an explicit visual mechanism.", "status": "common_sense", "renderer_scope": "any"}]}]
        save(self.root / "knowledge/experience/catalog.json", catalog)
        (self.root / "knowledge/experience/map.md").write_text("# Map\n", encoding="utf-8")
        (self.root / "knowledge/experience/task-advice.md").write_text("# Advice\nInitial working hypothesis.\n", encoding="utf-8")
        self.output = self.root / "run"

    def start(self, actions, rsi=True, **kwargs):
        kwargs.setdefault("max_generations", 3)  # These fixtures exercise bounded experiment semantics.
        self.model = ScriptedModel(actions)
        self.h = PlannerHarness(self.output, self.model, root=self.root)
        return self.h.start(self.source, "Make it blue.", mode="loop", execution={"mode": "replay", "renderer": {}, "critic": {"model": "scripted-test-only", "reasoning_effort": "none"}}, rsi=rsi, **kwargs)

    def resume(self, actions):
        self.model = ScriptedModel(actions)
        self.h = PlannerHarness(self.output, self.model, root=self.root)
        return self.h.resume()

    def generation(self, failed=False):
        state = load(self.output / "state.json")
        job = state["jobs"][state["pending_tool"]]
        p = job["payload"]
        response = {"request_sha256": job["sha256"], "mode": "replay", "status": "failed" if failed else "complete"}
        if failed:
            response["error"] = "Synthetic failed generation"
        else:
            response["payload"] = {"video": {"path": str(self.source), "sha256": sha(self.source)},
                "replay_provenance": "Synthetic fixture, not rendered from a prompt.",
                "execution": {"requested_prompt": p["prompt"], "effective_prompt": p["prompt"], "input_sha256": p["input"]["sha256"]}}
        save(self.output / "jobs" / job["id"] / "response.json", response)

    def review(self, verdict="pass", failed=False):
        state = load(self.output / "state.json")
        job = state["jobs"][state["pending_tool"]]
        identity = job["payload"]["video_id"]
        response = {"request_sha256": job["sha256"], "mode": "replay", "status": "failed" if failed else "complete"}
        if failed:
            response["error"] = "Synthetic review failure"
        else:
            assessment = {"summary": "Synthetic evidence only.", "major_damage": False,
                "findings": [{"id": "color", "dimension": "edit", "origin": "user_requirement", "importance": "core", "verdict": verdict,
                              "claim": "Fixture color judgment.", "partial_boundary": "Some surfaces satisfy the synthetic criterion.", "evidence": [{"observation_id": "overview", "video": identity}]}],
                "requirement_verdicts": [{"id": r["id"], "verdict": verdict, "evidence": "Fixture observation.", "observations": ["overview"]} for r in REQ]}
            model = ScriptedModel([call("assess", **assessment), call("process_context"), call("finish", summary="Fixture completed.", failure_types={"E1": ["explicit-unrealized"]})])
            response["payload"] = critique(job, self.output / "jobs" / job["id"], self.root, model)
            self.critic_model = model
        save(self.output / "jobs" / job["id"] / "response.json", response)

    def first_generation(self, **kwargs):
        return self.start([call("requirements", items=REQ), call("generate", input_video="source", prompt="Blue surfaces.", intent=INTENT)], **kwargs)

    def test_auto_review_once_and_real_adapter(self):
        self.first_generation(rsi={"seed_schedule": [42, 43, 44]})
        self.generation()
        state = self.resume([])
        self.assertEqual(self.model.inputs, [])
        self.assertEqual(len(state["jobs"]), 2)
        self.assertEqual(state["jobs"][state["pending_tool"]]["kind"], "critique")
        self.resume([])
        self.assertEqual(len(self.h.state["jobs"]), 2)
        self.review()
        state = self.resume([call("finish", video="v1", stop_reason="satisfied")])
        self.assertEqual(state["final"]["unmet"], [])
        self.assertEqual(state["task_memory"]["attempts"][0]["prediction"]["outcome"], "hit")
        self.assertNotIn(INTENT["expect"], self.critic_model.inputs[0]["user_text"])
        self.assertEqual(state["generation_requests"], 1)

    def test_three_generations_arbitrary_parent_and_backselection(self):
        self.first_generation()
        for index, parent in [(1, "v1"), (2, "source"), (3, None)]:
            self.generation()
            self.resume([])
            self.review("partial" if index < 3 else "pass")
            action = call("generate", input_video=parent, prompt="Blue material relations.", intent=INTENT) if parent else call("finish", video="v2", stop_reason="no_promising_attempt")
            state = self.resume([action])
        self.assertEqual(state["videos"]["v2"]["parent"], "v1")
        self.assertEqual(state["videos"]["v3"]["parent"], "source")
        self.assertEqual(state["final"]["video"], "v2")
        self.assertEqual(len(state["task_memory"]["attempts"]), 3)
        self.assertEqual(len(state["jobs"]), 6)

    def test_failed_review_is_visible_without_regeneration(self):
        self.first_generation(); self.generation(); self.resume([]); self.review(failed=True)
        state = self.resume([call("finish", video="v1", stop_reason="budget")])
        self.assertEqual(state["generation_requests"], 1)
        self.assertEqual(len(state["jobs"]), 2)
        self.assertEqual(state["final"]["unmet"], ["E1", "P1"])

    def test_new_review_id_cannot_bypass_uncertain_call(self):
        self.first_generation(); self.generation(); self.resume([])
        prior = self.h.state["pending_tool"]
        save(self.output / "jobs" / prior / "active-critic/calls/event-0001/submitted.json", {"status":"submitted_outcome_unknown"})
        self.review(failed=True)
        state = self.resume([call("critique", video="v1"), call("finish", video="v1", stop_reason="budget")])
        event = next(e for e in state["events"] if e.get("request", {}).get("action") == "critique")
        self.assertEqual(event["result"]["status"], "requires_reconciliation")
        self.assertEqual(len(state["jobs"]), 2)

    def test_failed_generation_has_no_auto_review(self):
        self.first_generation(); self.generation(failed=True)
        state = self.resume([call("finish", stop_reason="budget")])
        self.assertEqual(len(state["jobs"]), 1)

    def test_uncertain_call_is_not_repeated(self):
        with self.assertRaises(RuntimeError):
            self.start([RuntimeError("Unknown transport outcome")])
        with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
            self.resume([call("requirements", items=REQ)])
        self.assertEqual(self.model.inputs, [])

    def test_seed_override_rejected_before_charge(self):
        state = self.start([call("requirements", items=REQ), call("generate", input_video="source", prompt="Blue.", intent=INTENT, seed=1), call("finish", stop_reason="budget")], rsi={"seed_schedule": [42, 43, 44]})
        self.assertEqual(state["generation_requests"], 0)
        self.assertEqual(state["events"][1]["status"], "operation_error")

    def test_no_knowledge_and_frozen_critic(self):
        state = self.start([call("finish", stop_reason="budget")], rsi={"knowledge_enabled": False})
        payload = json.loads(self.model.inputs[0]["user_text"])
        self.assertEqual(payload["experience_digest"], [])
        with self.assertRaises(ValueError):
            self.h.knowledge.read("task-advice")
        critic = load(state["config"]["rsi"]["critic_materials"]["knowledge"])
        self.assertTrue(critic["enabled"])
        self.assertEqual(critic["experiences"], [])
        self.assertNotIn("knowledge/experience/task-advice.md", critic["documents"])

    def test_requirements_versions_keep_old_judgments_separate(self):
        state = {"evaluations": {}, "jobs": {}}
        first = ledger.set_requirements(state, REQ)
        with self.assertRaises(ValueError):
            ledger.set_requirements(state, REQ)
        second = ledger.set_requirements(state, REQ, "Clarify the task wording.")
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(len(state["requirement_versions"]), 2)

    def test_unknown_bounds_and_target_hit_do_not_hide_regression(self):
        scores = ledger.scores(REQ, {"E1": "pass", "P1": "unknown"})
        self.assertEqual((scores["preserve"]["lower"], scores["preserve"]["upper"]), (0, 1))
        self.assertIsNone(scores["preserve"]["score"])
        self.assertEqual(ledger.prediction({"checks": {"E1": "improve"}}, {}, {"E1": "pass"})["outcome"], "unknown")

    def test_review_needs_source_and_comparison_evidence(self):
        report = {"major_damage": None, "requirement_verdicts": [{"id": "P1", "verdict": "pass", "evidence": "Visible.", "observations": ["x"]}]}
        req = ledger.requirements([REQ[1]])
        with self.assertRaisesRegex(ValueError, "source"):
            ledger.validate_review(report, req, "v1", {"source": {}, "v1": {}}, {"x": {"frames": [{"video": "v1"}]}})

    def test_critic_authors_one_verdict_list_without_duplicate_findings(self):
        self.first_generation(); self.generation(); self.resume([])
        state = self.h.state; job = state["jobs"][state["pending_tool"]]
        assessment = {"summary":"Minimal fixture.", "major_damage":False, "requirement_verdicts":[
            {"id":r["id"],"verdict":"pass","evidence":"Fixture evidence.","observations":["overview"]} for r in REQ]}
        model = ScriptedModel([call("assess", **assessment), call("finish", summary="Minimal fixture complete.")])
        result = critique(job, self.output / "jobs" / job["id"], self.root, model)
        self.assertEqual(len(model.inputs), 2)
        self.assertEqual({f["projection"] for f in result["outcome"]["findings"]}, {"requirement_verdicts"})

    def test_draft_snapshot_and_digest_are_immutable(self):
        original = sha(self.root / "knowledge/experience/catalog.json")
        k = Knowledge(self.root)
        k.freeze(self.root / "frozen.json")
        (self.root / "knowledge/experience/task-advice.md").write_text("Changed live advice.")
        self.assertIn("Initial", k.read("task-advice")["text"])
        self.assertEqual(sha(self.root / "knowledge/experience/catalog.json"), original)
        self.assertEqual(len(experience_digest(k, "Bernini", 12)), 1)

    def packet(self):
        catalog = load(self.root / "knowledge/experience/catalog.json")
        return {"development": {"sha256": "dev", "records": [{"id": "r1", "source_sha256": sha(self.source), "decisions": [{"id": "e1"}]}]}, "base_catalog": catalog,
                "base_catalog_sha256": sha(self.root / "knowledge/experience/catalog.json"),
                "base_files": {r["path"]: sha(self.root / r["path"]) for r in catalog},
                "base_documents": {r["id"]: (self.root / r["path"]).read_text() for r in catalog}, "created_at": "fixture"}

    def proposal(self):
        result = {"summary": "Fixture candidate.", "limitations": ["Synthetic evidence."], "changes": [
            {"id": "task-advice", "operation": "upsert", "evidence": ["r1"], "counterexamples": ["Transfer remains unknown."],
             "predicted_behavior": "Use a different conditioning hypothesis.", "rationale": "Test fixture.", "title": "Advice",
             "replay_decisions": ["r1/e1"], "metric": "stop_rate", "direction": "increase",
             "text": "# Advice\nCandidate working hypothesis.\n", "cards": [{"id": "A1", "summary": "Candidate mechanism.", "status": "hypothesis", "renderer_scope": "any"}]}]}
        output = self.root / "knowledge/staged/test"
        data.stage_proposal(result, self.packet(), output, root=self.root)
        return output / "proposal.json"

    def splits(self):
        self.validation_source = self.root / "validation.avi"
        self.validation_source.write_bytes(self.source.read_bytes() + b"separate fixture source")
        path = self.root / "splits.json"
        data.split_manifest([{"id": "d", "source": str(self.source), "split": "D", "request": "Make it blue.", "renderer": "fixture"},
                             {"id": "v", "source": str(self.validation_source), "split": "V", "request": "Make it blue.", "renderer": "fixture"}], path)
        return path

    def protocol(self):
        return {"execution": {"mode": "replay", "renderer": {}, "critic": {"model": "scripted-test-only", "reasoning_effort": "none"}},
                "planner": {"model": "scripted-test-only", "reasoning_effort": "none"},
                "judge": {"model": "independent-fixture", "protocol_sha256": "fixture"},
                "selector": {"kind": "online_ledger_lexicographic", "order": ["preserve_core", "edit", "preserve_detail"], "unknown": "lower_bound", "ties": "earliest"},
                "seed_schedule": [42,43,44], "generation_budget": 3, "primary_metric": "non_improving_generations"}

    def test_collect_rejects_validation_and_keeps_missing_intent(self):
        self.start([call("generate", input_video="source", prompt="Blue.")], rsi=False)
        path = self.splits()
        packet = data.collect([self.output], path, self.root / "collection.json", root=self.root)
        self.assertEqual(packet["records"][0]["attempts"][0]["intent_status"], "historically_missing")
        splits = load(path); splits["tasks"][0]["split"] = "V"
        splits["sha256"] = ledger.digest({k:v for k,v in splits.items() if k != "sha256"})
        save(path, splits)
        with self.assertRaisesRegex(ValueError, "development"):
            data.collect([self.output], path, self.root / "bad.json", root=self.root)

    def test_split_source_hash_or_group_cannot_leak(self):
        with self.assertRaisesRegex(ValueError, "disjoint"):
            data.split_manifest([{"id":"a","source":str(self.source),"split":"D"}, {"id":"b","source":str(self.source),"split":"V"}], self.root / "bad.json")

    def test_proposal_freezes_unchanged_topics_and_checks_evidence(self):
        proposal = load(self.proposal())
        k = candidate_knowledge(self.root, proposal["candidate_catalog"])
        self.assertIn("Candidate", k.read("task-advice")["text"])
        self.assertIn("Initial", Knowledge(self.root).read("task-advice")["text"])
        catalog = load(proposal["candidate_catalog"])
        (self.root / catalog["entries"][1]["path"]).write_text("Tampered.")
        with self.assertRaisesRegex(ValueError, "changed"):
            candidate_knowledge(self.root, proposal["candidate_catalog"])

    def test_replay_stops_before_render_and_has_no_future_state(self):
        self.first_generation()
        input_path = self.output / "calls/event-0002/input.json"
        # Mutate only final state: a valid prefix replay must never read this secret.
        later = load(self.output / "state.json")
        later["notes"] = "FUTURE_RESULT_SECRET"
        save(self.output / "state.json", later)
        p = load(self.proposal())
        model = ScriptedModel([call("read", targets=[{"id": "task-advice"}]), call("generate", input_video="source", prompt="Blue.", intent=INTENT)])
        result = replay(input_path, p["candidate_catalog"], self.root / "replay", model, root=self.root)
        self.assertEqual(result["renderer_calls"], 0)
        self.assertEqual(result["status"], "decision_recorded")
        self.assertFalse((self.root / "replay/workspace/jobs").exists())
        self.assertNotIn("FUTURE_RESULT_SECRET", str(model.inputs))
        self.assertIn("Candidate working", model.inputs[-1]["user_text"])

    def test_gate_requires_complete_paired_evidence(self):
        p = self.proposal()
        manifest = validation.prepare(self.splits(), p, self.root / "validation", self.protocol(), root=self.root)
        result = validation.validate(self.root / "validation/manifest.json", [], self.root / "gate.json")
        self.assertEqual(result["status"], "incomplete")
        with self.assertRaisesRegex(ValueError, "passed"):
            validation.adopt(p, self.root / "gate.json", "fixture-reviewer", root=self.root)
        self.assertEqual(len(result["missing"]), 2)

    def test_unknown_independent_metrics_do_not_pass(self):
        metrics = validation.decision_metrics([{"id":"v1","success":None,"core":1,"utility":1}], "v1")
        self.assertIsNone(metrics["success"])
        self.assertEqual(metrics["core"], 1)
        self.assertEqual(metrics["bounds"]["success"], [0, 1])
        measured = validation.decision_metrics([{"id":"v1","success":True,"core":1,"utility":.8}, {"id":"v2","success":True,"core":1,"utility":.7}], "v1")
        self.assertEqual(measured["non_improving_generations"], 1)
        self.assertEqual(measured["selection_regret"], 0)

    def test_paired_runner_scores_gate_and_control_reuse(self):
        proposal = self.proposal()
        directory = self.root / "validation"
        validation.prepare(self.splits(), proposal, directory, self.protocol(), root=self.root)
        manifest_path = directory / "manifest.json"
        def worker(request, response):
            job = load(request)
            self.output = Path(request).parents[2]
            if job["kind"] == "generate":
                self.generation()
            else:
                self.review()
        receipts = []
        for arm, repeats in (("base", 2), ("candidate", 1), ("singlepass", 1)):
            out = self.root / arm
            actions = [call("requirements", items=REQ)] + [call("generate", input_video="source", prompt="Blue.", intent=INTENT) for _ in range(repeats)] + [call("finish", video="v1", stop_reason="satisfied")]
            state = validation.run_task(manifest_path, "v", arm, out, ScriptedModel(actions), worker=worker, root=self.root)
            self.assertEqual(state["status"], "complete")
            rows = []
            for identity, video in state["videos"].items():
                if not video.get("job_id"):
                    continue
                raw = out / (identity + "-independent.json")
                metrics = {"success": True, "core": 1, "utility": .8}
                save(raw, {"rsi_metrics": metrics, "scope": "Synthetic independent-judge fixture", "output_sha256": video["sha256"],
                           "source_sha256": state["request"]["source"]["sha256"], "judge": self.protocol()["judge"]})
                rows.append({"id": identity, "output_sha256": video["sha256"], "judge": self.protocol()["judge"], "raw": str(raw), "raw_sha256": sha(raw), **metrics})
            receipt = out / "receipt.json"
            validation.record_arm(manifest_path, out, rows, receipt)
            if arm != "singlepass":
                receipts.append(receipt)
        gate = validation.validate(manifest_path, receipts, self.root / "gate.json")
        self.assertEqual(gate["status"], "passed")
        self.assertEqual(gate["primary_mean_delta"], -1)
        with self.assertRaisesRegex(ValueError, "fixtures"):
            validation.adopt(proposal, self.root / "gate.json", "fixture-reviewer", root=self.root)
        from planner_harness.rsi_controls import run_control
        controlled = run_control(manifest_path, "v", "best-of-3", self.root / "singlepass", self.root / "bestof", worker=worker, root=self.root)
        jobs = [j for j in controlled["jobs"].values() if j["kind"] == "generate"]
        self.assertEqual([j["payload"]["renderer"]["seed"] for j in jobs], [42,43,44])
        self.assertEqual({j["payload"]["prompt"] for j in jobs}, {"Blue."})
        self.assertEqual({j["payload"]["input_id"] for j in jobs}, {"source"})
        self.assertEqual(controlled["videos"]["v1"]["reuse_provenance"]["scope"], "Shared first sample; no additional renderer call.")

    def test_real_proposer_interface_is_staged_and_cached(self):
        development = {"records": [{"id": "r1", "attempts": [], "decisions": []}], "schema": "fixture"}
        development["sha256"] = ledger.digest(development)
        path = self.root / "development.json"; save(path, development)
        model = ScriptedModel([{"summary": "No supported change.", "changes": [], "limitations": ["Fixture lacks useful evidence."]}])
        out = self.root / "knowledge/staged/proposer"
        result = data.propose(path, out, model, root=self.root)
        self.assertEqual(result["status"], "no_change")
        again = data.propose(path, out, model, root=self.root)
        self.assertEqual(result, again)
        self.assertEqual(len(model.inputs), 1)

    def test_temporal_requirement_unknown_without_sequence(self):
        req = ledger.requirements([{**REQ[0], "temporal": True}])
        report = {"major_damage": None, "requirement_verdicts": [{"id": "E1", "verdict": "pass", "evidence": "Sparse fixture.", "observations": ["x"]}]}
        result = ledger.validate_review(report, req, "v1", {"v1":{"duration_seconds":2}}, {"x":{"frames":[{"video":"v1"}],"videos":{}}})
        self.assertEqual(result["requirement_verdicts"][0]["verdict"], "unknown")
        self.assertEqual(result["requirement_verdicts"][0]["observed_interval_verdict"], "pass")

    def test_renderer_scoped_digest(self):
        k = Knowledge(self.root)
        k.experiences[1]["cards"] += [{"id": "D1", "summary": "Ditto hypothesis.", "status": "hypothesis", "renderer_scope": "ditto"}]
        self.assertEqual(next(r for r in experience_digest(k, "Bernini-R", 12) if r["id"] == "D1")["applicability"], "other_renderer_only")
        self.assertIn("D1", {r["id"] for r in experience_digest(k, "Ditto", 12)})

    def test_durable_judge_uses_english_and_reuses_response(self):
        from planner_harness.rsi_judge import DurableJudge
        class Client:
            model = "independent-fixture"
            reasoning_effort = "none"
            calls = 0
            def predict_json(inner, **kwargs):
                self.assertIn("in English", kwargs["system_prompt"])
                inner.calls += 1
                return {"result": "fixture"}
        client = Client()
        judge = DurableJudge(client, self.root / "judge")
        args = {"system_prompt": "Report evidence in Chinese.", "user_text": "Fixture.", "image_paths": []}
        self.assertEqual(judge.predict_json(**args), judge.predict_json(**args))
        self.assertEqual(client.calls, 1)

    def test_independent_judge_rejects_runtime_drift(self):
        from planner_harness import rsi_judge
        with patch.object(rsi_judge, "verify_manifest", return_value={"runtime": {}}):
            with self.assertRaisesRegex(ValueError, "runtime changed"):
                rsi_judge.judge_run("unused", "unused", "unused", object(), root=self.root)

    def test_known_damage_still_has_a_measurable_selection(self):
        req = ledger.requirements(REQ)
        outcome = {"requirements_sha256": req["sha256"], "major_damage": True,
                   "requirement_verdicts": [{"id": r["id"], "verdict": "fail"} for r in REQ]}
        state = {"requirements": req, "evaluations": {"e": {"video_id":"v1", "outcome":outcome}}, "jobs": {}}
        self.assertEqual(validation.common_selection(state, self.protocol()["selector"]), "v1")

    def test_multi_file_transaction_resume_and_rollback(self):
        catalog = self.root / "knowledge/experience/catalog.json"
        before = catalog.read_bytes()
        encode = __import__("base64").b64encode
        journal_path = self.root / "knowledge/experience/versions/fixture.json"
        journal = {"status": "pending", "writes": [
            {"path": "knowledge/experience/new.md", "before": None, "after": encode(b"# New\n").decode()},
            {"path": "knowledge/experience/catalog.json", "before": encode(before).decode(), "after": encode(b"[]\n").decode()}]}
        save(journal_path, journal)
        validation._write_transaction(journal, journal_path, self.root)
        validation._write_transaction(journal, journal_path, self.root)
        validation.rollback(journal_path, "fixture-reviewer", root=self.root)
        self.assertEqual(catalog.read_bytes(), before)
        self.assertFalse((self.root / "knowledge/experience/new.md").exists())
        validation.rollback(journal_path, "fixture-reviewer", root=self.root)

    def test_reviewed_adoption_publishes_the_bound_library(self):
        # Gate computation is covered by the paired-run test. Isolate publication here.
        proposal_path = self.proposal()
        proposal = load(proposal_path)
        before = (self.root / "knowledge/experience/catalog.json").read_bytes()
        result = {"status": "passed", "proposal_sha256": proposal["sha256"], "manifest": "fixture-manifest",
                  "manifest_sha256": "fixture-manifest-hash", "receipt_paths": [], "receipt_hashes": []}
        result["sha256"] = ledger.digest(result)
        gate_path = self.root / "fixture-gate.json"; save(gate_path, result)
        manifest = {"sha256": "fixture-manifest-hash", "protocol": {"execution": {"mode": "live"}}}
        with patch.object(validation, "verify_manifest", return_value=manifest), patch.object(validation, "validate", return_value={"status":"passed"}):
            record = validation.adopt(proposal_path, gate_path, "fixture-reviewer", root=self.root)
            again = validation.adopt(proposal_path, gate_path, "fixture-reviewer", root=self.root)
        self.assertEqual(record, again)
        self.assertIn("Candidate working", Knowledge(self.root).read("task-advice")["text"])
        journal = self.root / "knowledge/experience/versions" / (proposal["sha256"][:20] + ".json")
        validation.rollback(journal, "fixture-reviewer", root=self.root)
        self.assertEqual((self.root / "knowledge/experience/catalog.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
