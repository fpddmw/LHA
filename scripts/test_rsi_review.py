"""Regression cases from the Opus review. All models, judgments and media are fixtures."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness import ledger
from planner_harness.common import load, save, sha
from planner_harness.rsi_calls import call_once, reconcile
from planner_harness.rsi_support import experience_digest
from planner_harness.rsi_validation import common_selection, decision_metrics


REQ = [{"id":"E", "text":"Apply a painted medium.", "kind":"edit", "priority":"core"},
       {"id":"P", "text":"Retain the writing action.", "kind":"preserve", "priority":"core"}]


class ResponseModel:
    model = "software-fixture"
    reasoning_effort = "none"
    retries = 8
    rsi_retry_policy = {"max_attempts": 3, "backoff_seconds": 0}
    def __init__(self, responses):
        self.responses = list(responses); self.seen = []
    def predict_text(self, **kwargs):
        self.seen.append(self.retries)
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class ReviewRepairs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def state(self, outcomes, targets=None):
        req = ledger.requirements(REQ)
        s = {"requirements":req, "videos":{"source":{}}, "jobs":{}, "evaluations":{}}
        for i, pair in enumerate(outcomes, 1):
            video, job = "v"+str(i), "g"+str(i)
            s["videos"][video] = {"job_id":job}
            s["jobs"][job] = {"kind":"generate", "payload":{"input_id":"source", "comparison_baseline":"v"+str(i-1) if i>1 else "source", "requirements":req,
                "intent":{"targets":targets[i-1] if targets else ["E"], "change":"A new visual realization.", "expect":"The medium becomes clearer."}}}
            s["evaluations"]["f"+str(i)] = {"video_id":video, "outcome":{"requirements_sha256":req["sha256"], "major_damage":False,
                "requirement_verdicts":[{"id":k,"verdict":v} for k,v in zip(("E","P"),pair)]}}
        return s

    def test_source_restart_uses_candidate_baseline_and_detects_damage(self):
        state = self.state([("partial","pass"),("pass","fail")])
        value = ledger.build(state)
        self.assertEqual(value["attempts"][1]["prediction"]["outcome"], "hit")
        self.assertEqual(value["attempts"][1]["collateral_regressions"], ["P"])
        self.assertEqual(value["attempts"][1]["input"], "source")
        self.assertEqual(value["attempts"][1]["baseline"], "v1")
        self.assertEqual(ledger.resolve_baseline(state, {}), "v2")
        self.assertEqual(ledger.resolve_baseline(state, {"baseline":"v1"}), "v1")
        self.assertNotIn("source", value["candidates"])

    def test_target_failures_survive_unrelated_and_unknown_attempts(self):
        state = self.state([("fail","pass"),("fail","partial"),("unknown","pass"),("partial","pass")], [["E"],["P"],["E"],["E"]])
        memory = ledger.build(state)
        self.assertEqual(memory["targeted_nonachievement_counts"]["E"], 2)
        self.assertEqual(memory["targeted_unknown_counts"]["E"], 1)
        self.assertEqual(memory["targeted_nonachievement_counts"]["P"], 0)

    def test_first_target_check_has_no_synthetic_source_judgment(self):
        memory = ledger.build(self.state([("pass","pass")]))
        attempt = memory["attempts"][0]
        self.assertEqual(attempt["prediction"]["checks"], {"E":"hit"})
        self.assertIn("free-text", attempt["prediction"]["basis"])
        self.assertEqual(attempt["baseline_status"], "unreviewed_reference")

    def test_all_45_summaries_are_visible_with_applicability(self):
        class Knowledge:
            enabled=True
            experiences=load(ROOT / "knowledge/staged/e1-20261030/catalog.json")
        cards = experience_digest(Knowledge(), "bernini", 1)
        self.assertEqual(len(cards), 45)
        by_id = {c["id"]:c for c in cards}
        self.assertEqual(by_id["D1"]["applicability"], "other_renderer_only")
        self.assertIn("two targeted attempts", by_id["S5"]["summary"])
        self.assertIn("X4", by_id)
        self.assertNotEqual(by_id["D1"]["summary"], "Apply S1.")

    def temporal(self, verdict, counterexample=None):
        req = ledger.requirements([{**REQ[1], "temporal":True}])
        row = {"id":"P", "verdict":verdict, "evidence":"Observed local sequence.", "observations":["x"]}
        if counterexample: row["counterexample_interval"] = counterexample
        observations = {"x":{"frames":[{"video":"source"},{"video":"v1"}], "videos":{k:{"actual_interval":[0,.5],"continuous":True,"crop":None} for k in ("source","v1")}}}
        return ledger.validate_review({"major_damage":None,"requirement_verdicts":[row]}, req, "v1", {"source":{"duration_seconds":2},"v1":{"duration_seconds":2}}, observations)

    def test_local_temporal_failure_and_sampled_pass_have_distinct_scope(self):
        failure = self.temporal("fail", [0,.5])["requirement_verdicts"][0]
        self.assertEqual(failure["verdict"], "fail")
        self.assertEqual(failure["temporal_coverage"]["source"]["fraction"], .25)
        sampled = self.temporal("pass")["requirement_verdicts"][0]
        self.assertEqual(sampled["verdict"], "unknown")
        self.assertEqual(sampled["observed_interval_verdict"], "pass")
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.temporal("fail", [0,1])

    def test_response_retries_are_bounded_and_do_not_mutate_shared_client(self):
        model = ResponseModel([TimeoutError(), '{"action":"finish"}'])
        value = call_once(self.root / "call", model, "s", "u")
        self.assertEqual(model.retries, 8)
        self.assertEqual(model.seen, [1,1])
        self.assertEqual(call_once(self.root / "call", model, "s", "u"), value)
        self.assertEqual(len(model.seen), 2)
        self.assertEqual(len(list((self.root / "call/attempts").glob("*/submitted.json"))), 2)

    def test_exhausted_call_requires_reconciliation_before_more_dispatch(self):
        path=self.root / "call"; model=ResponseModel([TimeoutError()]*3)
        with self.assertRaisesRegex(RuntimeError,"exhausted"): call_once(path,model,"s","u")
        fresh=ResponseModel(['{"ok":true}'])
        with self.assertRaisesRegex(RuntimeError,"exhausted"): call_once(path,fresh,"s","u")
        self.assertEqual(fresh.seen, [])
        reconcile(path,"retry","Reviewed provider outcome; permit one bounded response retry.","fixture-reviewer")
        self.assertEqual(call_once(path,fresh,"s","u"), '{"ok":true}')
        self.assertEqual(len(list((path / "attempts").glob("*/submitted.json"))),4)

    def test_legacy_ambiguous_submission_stays_blocked(self):
        path=self.root / "legacy"; model=ResponseModel(['ok'])
        packet={"system_prompt":"s","user_text":"u","images":[],"model":model.model,"reasoning_effort":"none","max_new_tokens":7000}
        save(path / "single-call.json",{"sha256":ledger.digest(packet),"packet":packet})
        save(path / "submitted.json",{"status":"unknown"})
        with self.assertRaisesRegex(RuntimeError,"legacy"):call_once(path,model,"s","u")
        self.assertEqual(model.seen,[])

    def test_unselected_unknown_keeps_selected_metrics_and_regret_bounds(self):
        metrics=decision_metrics([{"id":"v1","success":True,"core":1,"utility":.8},{"id":"v2","success":None,"core":None,"utility":None}],"v1")
        self.assertEqual(metrics["success"],1)
        self.assertEqual(metrics["core"],1)
        self.assertIsNone(metrics["selection_regret"])
        self.assertAlmostEqual(metrics["bounds"]["selection_regret"][1],.2)
        self.assertEqual(metrics["bounds"]["selection_regret"][0],0)

    def test_control_selector_can_rank_unknown_without_fabricating_score(self):
        state=self.state([("pass","unknown")])
        self.assertEqual(common_selection(state,{"order":["preserve_core","edit","preserve_detail"]}),"v1")
        self.assertIsNone(ledger.build(state)["candidates"]["v1"]["scores"]["preserve_core"]["score"])

    def test_real_card_diff_counts_hidden_rewrites(self):
        from planner_harness.rsi_cards import changed_cards
        cards=[{"id":f"C{i}","summary":"Old","status":"hypothesis"} for i in range(4)]
        old={"id":"topic","cards":cards}
        text="\n".join(f"### C{i} · rule\nOld explanation." for i in range(4))
        change={**old,"operation":"upsert","text":text.replace("Old explanation","New explanation")}
        self.assertEqual(len(changed_cards(old,text,change)),4)

    def test_replay_prefix_removes_old_advice_but_keeps_actual_attempt(self):
        from planner_harness.rsi_replay import neutralize
        payload={"notes":"OLD RULE", "recent_operations":[{"request":{"action":"read"},"result":"OLD RULE"},{"request":{"action":"generate","arguments":{"prompt":"Actual prior prompt"}}}]}
        p,s=neutralize(payload,{"reads":{"x":"OLD RULE"},"notes":"OLD RULE","videos":{"source":{}},"events":payload["recent_operations"]})
        self.assertNotIn("OLD RULE",json.dumps([p,s]))
        self.assertIn("Actual prior prompt",json.dumps([p,s]))

    def test_replay_gate_requires_predicted_behavior_not_just_a_decision(self):
        from planner_harness.rsi_paired_replay import summarize
        rows=[{"id":a,"decision_id":"r/e","arm":a,"status":"decision_recorded","decision":{"action":"generate","arguments":{"input_video":"source"}},"earlier_candidates":[],"decision_sha256":a} for a in ("base","candidate")]
        target={"decision_id":"r/e","metric":"stop_rate","direction":"increase"}
        self.assertEqual(summarize(rows,[target])["status"],"no_predicted_shift")
        rows[1]["decision"]={"action":"finish","arguments":{"video":"v1"}}
        self.assertEqual(summarize(rows,[target])["status"],"passed")

    def test_statistics_retain_missing_historical_predictions(self):
        from planner_harness.rsi_statistics import aggregate
        record={"id":"r1","source_sha256":"s","renderer":"bernini","attempts":[{"job":"g1","candidate":"v1","input":"source","independent_evaluations":[{"result":{"result":{"success":"pass","major_damage":False}}}]}]}
        result=aggregate([record])
        self.assertEqual(result["first_attempt_success"]["rate"],1)
        self.assertEqual(result["predictions"]["counts"],{"historically_missing":1})
        self.assertIsNone(result["critic_independent_agreement"]["major_damage"]["rate"])

    def test_reviewed_flag_alone_cannot_unlock_judge(self):
        from planner_harness.rsi_calibration import verify_calibration
        with self.assertRaisesRegex(ValueError,"actual reviewed"):
            verify_calibration({"model":"fixture","calibration_status":"reviewed"})

    def test_render_recovery_preserves_job_seed_and_requires_known_nonexecution(self):
        from planner_harness.rsi_recovery import recover_tool
        from planner_harness.execution import signature
        body={"id":"g1","kind":"generate","mode":"live","payload":{"renderer":{"seed":42}}}
        job={**body,"sha256":signature(body)}; request=self.root / "job/request.json"
        save(request,job);save(request.with_name("response.json"),{"request_sha256":job["sha256"],"status":"failed"})
        with self.assertRaisesRegex(ValueError,"uncertain render"):
            recover_tool(request,"fixture-reviewer","Investigated the failure.")
        receipt=recover_tool(request,"fixture-reviewer","Confirmed the worker never started.",confirmed_not_executed=True)
        self.assertEqual(receipt["seed"],42)
        self.assertEqual(load(request),job)
        self.assertFalse(request.with_name("response.json").exists())

    def test_remote_receipt_cannot_change_seed_or_input(self):
        from planner_harness.rsi_remote import verify_response
        p=self.root / "video.mp4";p.write_bytes(b"synthetic fixture bytes")
        job={"sha256":"job","mode":"live","payload":{"input":{"sha256":"input"},"prompt":"Painted.","renderer":{"seed":42}}}
        response={"request_sha256":"job","mode":"live","status":"complete","payload":{"video":{"sha256":sha(p)},"execution":{"input_sha256":"input","effective_prompt":"Painted.","seed":43}}}
        with self.assertRaisesRegex(ValueError,"seed mismatch"):verify_response(job,response,p)


class ReviewIntegration(unittest.TestCase):
    def setUp(self):
        import test_rsi as fixtures
        self.f=fixtures.RSITests();self.f.setUp();self.fixtures=fixtures
    def tearDown(self):self.f.tearDown()

    def test_legacy_prefix_keeps_order_and_recovers_inaccessible_remote_export(self):
        from planner_harness import rsi_replay as replay_module
        from unittest.mock import patch
        f=self.f;run=f.root / "archive/run";input_path=run / "calls/event-0003/input.json"
        source={"path":str(f.source),"sha256":sha(f.source)}
        remote="/root/remote/run/videos/v1/video.avi"
        archived=run / "videos/v1/video.avi";archived.parent.mkdir(parents=True);archived.write_bytes(f.source.read_bytes())
        v1={"path":remote,"sha256":sha(archived)}
        save(run / "jobs/j1/request.json",{"kind":"generate","payload":{"input_id":"source","input":source}})
        payload={"task":{"text":"Make it blue.","source":source},"videos":{"source":{},"v1":{}},"recent_operations":[{"request":{"action":"tool_result","arguments":{"job_id":"j1"}},"result":{"video_id":"v1","video":v1}}]}
        save(input_path,{"user_text":json.dumps(payload),"images":[],"system_prompt":"Fixture"})
        original=replay_module.local_path
        def inaccessible(value,root):
            if str(value)==remote:raise PermissionError("Remote root unavailable")
            return original(value,root)
        with patch.object(replay_module,"local_path",inaccessible):
            _,_,state,_=replay_module.prefix(input_path,f.root)
        self.assertEqual(list(state["videos"]),["source","v1"])
        self.assertEqual(state["videos"]["v1"]["path"],str(archived.resolve()))

    def test_source_restart_auto_review_includes_prior_candidate(self):
        f=self.f; call=self.fixtures.call
        f.first_generation();f.generation();f.resume([]);f.review("partial")
        f.resume([call("generate",input_video="source",prompt="A connected painted surface.",intent={"targets":["E1"],"change":"Change the visual realization.","expect":"Clearer pigment."})])
        job=f.h.state["jobs"][f.h.state["pending_tool"]]
        self.assertEqual(job["payload"]["comparison_baseline"],"v1")
        f.generation();state=f.resume([])
        review=state["jobs"][state["pending_tool"]]
        self.assertEqual(set(review["payload"]["videos"]),{"source","v1","v2"})
        f.review();state=f.resume([call("finish",video="v2",stop_reason="satisfied")])
        self.assertEqual(state["task_memory"]["attempts"][-1]["prediction"]["outcome"],"hit")

    def test_cycle_critic_stays_fixed_across_active_experience_edits(self):
        from planner_harness.rsi_cycle import freeze,verify
        f=self.f; path=f.root / "cycle"
        cycle=freeze(f.splits(),f.protocol(),path,root=f.root)
        knowledge=load(cycle["critic"]["knowledge"]["path"])
        self.assertEqual(knowledge["experiences"],[])
        (f.root / "knowledge/experience/task-advice.md").write_text("Changed active advice.",encoding="utf8")
        self.assertEqual(verify(path / "cycle.json")["sha256"],cycle["sha256"])

    def test_proposal_rejects_four_actual_card_changes(self):
        from planner_harness.rsi_data import stage_proposal
        f=self.f
        cards=[{"id":f"C{i}","summary":"A conditional action.","status":"hypothesis","renderer_scope":"any"} for i in range(4)]
        result={"summary":"Fixture","limitations":[],"changes":[{"id":"new-advice","operation":"upsert","evidence":["r1"],"counterexamples":[],"predicted_behavior":"Stop more often.","replay_decisions":["r1/e1"],"metric":"stop_rate","direction":"increase","rationale":"Fixture","title":"Advice","cards":cards,"text":"\n".join(f"### C{i} · rule\nWhen a condition holds, act." for i in range(4))}]}
        with self.assertRaisesRegex(ValueError,"revision budget"):
            stage_proposal(result,f.packet(),f.root / "knowledge/staged/four",root=f.root)

    def test_repeated_paired_replay_uses_same_prefix_and_resumes_without_calls(self):
        from planner_harness.rsi_paired_replay import probe
        f=self.f; f.first_generation()
        proposal=load(f.proposal()); out=f.root / "paired"
        actions=[self.fixtures.call("finish",stop_reason="budget") for _ in range(4)]
        model=self.fixtures.ScriptedModel(actions)
        args=({"r1/e1":f.output / "calls/event-0002/input.json"}, f.root / "knowledge/experience/catalog.json", proposal["candidate_catalog"],out,model)
        targets=[{"decision_id":"r1/e1","metric":"stop_rate","direction":"increase"}]
        first=probe(*args,root=f.root,repetitions=2,targets=targets)
        self.assertEqual(first["status"],"no_predicted_shift")
        self.assertEqual(len(first["samples"]),4)
        self.assertEqual(len({r["prefix_sha256"] for r in first["samples"]}),1)
        self.assertEqual(probe(*args,root=f.root,repetitions=2,targets=targets),first)
        self.assertEqual(len(model.inputs),4)

    def test_planner_selection_drives_receipt_even_when_common_selector_disagrees(self):
        from planner_harness import rsi_validation as v
        from planner_harness.rsi_reporting import report
        f=self.f; call=self.fixtures.call
        dest=f.root / "validation"
        v.prepare(f.splits(),f.proposal(),dest,f.protocol(),root=f.root)
        manifest=dest / "manifest.json"
        def worker(request,response):
            f.output=Path(request).parents[2]
            if load(request)["kind"] == "generate": f.generation()
            else: f.review()
        run=f.root / "candidate"
        actions=[call("requirements",items=self.fixtures.REQ)]+[call("generate",input_video="source",prompt="Blue.",intent=self.fixtures.INTENT)]*2+[call("finish",video="v2",stop_reason="budget")]
        state=v.run_task(manifest,"v","candidate",run,self.fixtures.ScriptedModel(actions),worker=worker,root=f.root)
        rows=[]
        for identity in ("v1","v2"):
            video=state["videos"][identity]; raw=run / (identity+"-independent.json")
            metrics={"success":True,"core":1,"utility":.9 if identity=="v1" else .4}
            save(raw,{"rsi_metrics":metrics,"output_sha256":video["sha256"],"source_sha256":state["request"]["source"]["sha256"],"judge":f.protocol()["judge"]})
            rows.append({"id":identity,"output_sha256":video["sha256"],"judge":f.protocol()["judge"],"raw":str(raw),"raw_sha256":sha(raw),**metrics})
        receipt=v.record_arm(manifest,run,rows,run / "receipt.json")
        self.assertEqual(receipt["selected"],"v2")
        self.assertEqual(receipt["common_selected"],"v1")
        self.assertEqual(receipt["metrics"]["utility"],.4)
        self.assertAlmostEqual(receipt["metrics"]["selection_regret"],.5)
        self.assertEqual(receipt["common_selection_metrics"]["selection_regret"],0)
        result=report(manifest,[run / "receipt.json"],f.root / "report.json")
        panels={p["arm"]:p for p in result["panels"] if p["track"]=="all"}
        self.assertEqual(len(panels),5)
        self.assertEqual(panels["base"]["metrics"]["utility"]["received"],0)
        self.assertEqual(panels["candidate"]["selected_minus_first_utility"]["mean"],-.5)

    def test_calibration_requires_reviewed_real_artifact_chain(self):
        from planner_harness import rsi_calibration as c
        from planner_harness.rsi_judge import protocol_hash
        from unittest.mock import patch
        from types import SimpleNamespace
        f=self.f; root=f.root
        card=root / "card.json"; ref=root / "reference.json"; manifest=root / "calibration.json"
        save(card,{"source_sha256":sha(f.source),"requirement":"Make it blue."})
        scores={"semantic":{"edit":{"score":.5}},"success":"fail","major_damage":False}
        save(ref,{"rsi_metrics":{},"score":scores})
        profile={"model":"fixture-judge","reasoning_effort":None,"protocol_sha256":protocol_hash(),"utility_weights":{"edit":1}}
        c.prepare([{"id":"saved","card":str(card),"reference":str(ref),"video":str(f.source)}],profile,manifest)
        def scorer(task,video,profile,client,directory,**kwargs):
            raw=directory / "judgment.json";save(raw,{"score":scores})
            return {"raw":str(raw),"raw_sha256":sha(raw)}
        with patch("planner_harness.rsi_judge.score_case",scorer):
            c.run(manifest,root / "calibration",SimpleNamespace(model="fixture-judge",reasoning_effort=None),root=root)
        review=root / "calibration/review.json"
        c.review(root / "calibration/comparison.json",review,"fixture-human","approved","Synthetic comparator, not an accuracy experiment.")
        bound={**profile,"calibration":{"path":str(review),"sha256":sha(review)}}
        self.assertEqual(c.verify_calibration(bound)["decision"],"approved")
        with self.assertRaisesRegex(ValueError,"exact judge"):
            c.verify_calibration({**bound,"model":"different"})
        save(root / "calibration/saved/judgment.json",{"score":"modified"})
        with self.assertRaisesRegex(ValueError,"judgment changed"):c.verify_calibration(bound)

    def test_batch_runs_dependencies_once_and_isolates_failed_arm(self):
        from planner_harness import rsi_validation as v
        from planner_harness.rsi_batch import Batch
        from server_runtime.queue import Queue
        from server_runtime.engine import Engine
        from types import SimpleNamespace
        f=self.f; call=self.fixtures.call
        dest=f.root / "validation";v.prepare(f.splits(),f.proposal(),dest,f.protocol(),root=f.root)
        queue=Queue(f.root / "queue.sqlite3",{"gpu":1,"llm":1,"cpu":1})
        model=self.fixtures.ScriptedModel([call("requirements",items=self.fixtures.REQ),call("generate",input_video="source",prompt="Blue.",intent=self.fixtures.INTENT),call("finish",video="v1",stop_reason="satisfied")])
        class Worker:
            model_factory=lambda self,role:model
            close=lambda self:None
            def __call__(self,job,directory):
                request=Path(job["payload"]["request"]);f.output=request.parents[2]
                if load(request)["kind"] == "generate":f.generation()
                else:f.review()
                response=request.with_name("response.json")
                return {"artifacts":[{"path":str(response),"sha256":sha(response)}]}
        batch=Batch(queue,f.root / "batch",dest / "manifest.json",Worker(),root=f.root)
        batch.submit(["candidate"],score=False)
        Engine(queue,f.root / "batch",batch,batch.expand,interval=.01).run(once=True)
        self.assertTrue(all(r["state"]=="complete" for r in queue.rows()))
        self.assertEqual(load(batch._run("v","candidate") / "state.json")["generation_requests"],1)
        before=len(model.inputs)
        Engine(queue,f.root / "batch",batch,batch.expand,interval=.01).run(once=True)
        self.assertEqual(len(model.inputs),before)
        request=f.root / "failed/request.json";save(request,{"kind":"critique"});save(request.with_name("response.json"),{"status":"failed"})
        failed=queue.enqueue("failed-arm","tool","llm",{"request":str(request)})
        independent=queue.enqueue("other-arm","test-independent","cpu",{})
        class FailureWorker:
            def __call__(self,job,directory):return {}
        batch.service=FailureWorker()
        with self.assertRaisesRegex(RuntimeError,"quarantine"):
            batch.recover({"kind":"tool","payload":{"request":str(request)}},f.root / "recover")
        claimed=queue.claim("llm","fixture")
        queue.finish(claimed,error="quarantined")
        self.assertEqual(queue.claim("cpu","fixture")["id"],independent)

    def test_live_failed_tool_keeps_paired_seed_slot(self):
        from planner_harness.rsi_validation import require_resolved_tool
        f=self.f;f.first_generation(rsi={"seed_schedule":[42,43,44]});f.generation(failed=True)
        with self.assertRaisesRegex(RuntimeError,"logical seed"):
            require_resolved_tool(f.output,{"execution":{"mode":"live"}})
        state=load(f.output / "state.json")
        self.assertEqual(state["generation_requests"],1)
        self.assertEqual(state["jobs"][state["pending_tool"]]["payload"]["renderer"]["seed"],42)

    def test_formal_replay_validation_and_test_share_cycle_environment(self):
        from planner_harness import rsi_validation as v, rsi_data as data
        from planner_harness.rsi_cycle import freeze
        from planner_harness.rsi_paired_replay import probe
        from test_rsi_complete import card as card_fixture
        from planner_harness.rsi_evidence import freeze_partition
        from planner_harness.video import Video
        from planner_harness.runner import PlannerHarness
        f=self.f;call=self.fixtures.call;f.first_generation()
        original_splits=load(f.splits())["tasks"]
        tsource=f.root / "test.avi";tsource.write_bytes(f.source.read_bytes()+b"test source")
        original_splits.append({"id":"t","source":str(tsource),"split":"T","request":"Make it blue.","renderer":"fixture"})
        hsource=f.root / "heldout.avi";hsource.write_bytes(f.source.read_bytes()+b"heldout replay source")
        original_splits.append({"id":"h","source":str(hsource),"split":"D","request":"Make it blue.","renderer":"fixture"})
        for task in original_splits:
            card=card_fixture(sha(task["source"]),Video(task["source"],f.root/"inspect").info["duration_seconds"],task["request"])
            path=f.root / (task["id"]+"-card.json");save(path,card);task["card"]=str(path)
        split=f.root / "all-splits.json";data.split_manifest(original_splits,split)
        protocol=f.protocol();protocol["execution"]["mode"]="live"
        protocol.update(primary_metric="selected_utility",baseline_role="original",analysis_plan="Synthetic frozen-contract integration test",
                        replay_gate={"minimum_repetitions":2,"minimum_decision_points":1,"minimum_delta":.25},
                        quality_gate={"minimum_sources":2,"minimum_primary_gain":.1,"max_core_drop":0,"max_success_drop":0,"max_major_damage_increase":0})
        protocol["judge"]["utility_weights"]={"edit":.5,"rating:style":.5}
        cycle=freeze(split,protocol,f.root / "cycle",root=f.root);cycle_path=f.root / "cycle/cycle.json"
        proposal=f.proposal();p=load(proposal)
        generate=call("generate",input_video="source",prompt="Blue.",intent=self.fixtures.INTENT)
        finish=call("finish",stop_reason="budget")
        model=self.fixtures.ScriptedModel([generate,finish,finish,generate])
        (f.root / "knowledge/READING.md").write_text("Changed after cycle; must not enter either probe arm.",encoding="utf8")
        # A separate source with independently frozen criteria supplies the held-out prefix.
        heldrun=f.root/"heldout-run"
        heldtask=next(t for t in original_splits if t["id"]=="h")
        PlannerHarness(heldrun,self.fixtures.ScriptedModel([generate]),root=f.root).start(heldtask["source"],heldtask["request"],mode="loop",
            execution=f.protocol()["execution"],rsi={"task_card":heldtask["card"]})
        heldinput=heldrun/"calls/event-0001/input.json"
        partition=f.root/"replay-partition.json"
        freeze_partition([{"id":"held/e1","role":"heldout","source_sha256":sha(heldtask["source"]),"trajectory":"held",
                           "input":str(heldinput),"input_sha256":sha(heldinput)}],partition)
        result=probe({"held/e1":heldinput},f.root / "knowledge/experience/catalog.json",p["candidate_catalog"],f.root / "probe",model,root=f.root,repetitions=2,
                     targets=[{"decision_id":"held/e1","metric":"stop_rate","direction":"increase"}],cycle_path=cycle_path,partition=partition)
        self.assertEqual(result["status"],"passed")
        self.assertNotIn("Changed after cycle",str(model.inputs))
        manifest=v.prepare(split,proposal,f.root / "v",protocol,root=f.root,cycle_path=cycle_path,replay_gate_path=f.root / "probe/result.json")
        self.assertEqual(load(manifest["frozen"]["critic-knowledge.json"]["path"])["experiences"],[])
        adoption=f.root / "fixture-adoption.json";save(adoption,{"status":"complete","reviewed_by":"fixture-reviewer","proposal_sha256":p["sha256"]})
        final=v.prepare(split,proposal,f.root / "t",protocol,root=f.root,cycle_path=cycle_path,split="T",adoption_path=adoption)
        self.assertEqual(final["base_role"],"cycle_E0")
        self.assertEqual(load(final["frozen"]["base-knowledge.json"]["path"]),load(cycle["initial_planner_knowledge"]["path"]))

    def test_replace_library_can_retire_an_entrance_without_touching_active_library(self):
        from planner_harness.rsi_support import candidate_knowledge
        f=self.f
        save(f.root / "knowledge/entrances.json",{"task-advice":{"use_for":"Existing advice"}})
        catalog=f.root / "knowledge/staged/delete/catalog.json"
        save(catalog,{"mode":"replace_experience","entries":[load(f.root / "knowledge/experience/catalog.json")[0]]})
        candidate=candidate_knowledge(f.root,catalog)
        self.assertNotIn("task-advice",candidate.items)
        self.assertEqual(len(load(f.root / "knowledge/experience/catalog.json")),2)

    def test_critic_anchor_uses_frozen_cycle_and_reports_verdict_drift(self):
        from planner_harness.rsi_cycle import freeze
        from planner_harness.rsi_anchors import run,compare
        from unittest.mock import patch
        f=self.f
        cycle=freeze(f.splits(),f.protocol(),f.root / "cycle",root=f.root)
        f.first_generation(rsi={"cycle":str(f.root / "cycle/cycle.json")});f.generation();state=f.resume([])
        request=f.output / "jobs" / state["pending_tool"] / "request.json"
        def review(job,directory,root,model=None):
            feedback={"outcome":{"requirements_sha256":job["payload"]["requirements"]["sha256"],
                                  "requirement_verdicts":[{"id":"E1","verdict":model}]}}
            save(directory / "active-critic/feedback.json",feedback)
            return feedback
        with patch("critic_harness.adapter.critique",review):
            run(request,f.root / "cycle/cycle.json",f.root / "anchor1",root=f.root,model="pass")
            run(request,f.root / "cycle/cycle.json",f.root / "anchor2",root=f.root,model="unknown")
        result=compare(f.root / "anchor1/anchor.json",f.root / "anchor2/anchor.json",f.root / "drift.json",maximum_changed_fraction=.2)
        self.assertEqual(result["status"],"needs_review")
        self.assertEqual(result["unknown_pairs"],1)


if __name__ == "__main__":unittest.main()
