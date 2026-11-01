"""Behavioral contracts for the full upgrade; no paid models or GPU work."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness import ledger, task_criteria as criteria, rsi_evidence as evidence
from planner_harness.common import load, save, sha
from evaluation import PROTOCOL
from evaluation.protocol import signature


def card(source_hash="a"*64, duration=2, request="Make it blue."):
    def item(identity, origin):
        return {"id":identity,"text":"Blue treatment" if origin == "user_requirement" else "Recognizable scene relation",
                "mandatory":True,"temporal":False,"evidence":"frames","partial_rule":"Localized achievement only",
                "origin":origin,"importance_reason":"Requested outcome" if origin == "user_requirement" else "Defines the depicted interaction",
                "source_evidence":"Request or source observation fixture", "pass_rule":"Established across relevant observed content",
                "fail_rule":"Absent or contradicting the source relation", "allowed_variation":["Coherent stylization"]}
    value = {"protocol":PROTOCOL,"task_id":"fixture","source_id":"fixture","source_video":"source.mp4",
        "source_sha256":source_hash,"requirement":request,"style_family":"fixture","track":"short","split":"development",
        "creativity":"open","allowed_changes":["Appearance"],"style_required":True,"duration_seconds":duration,
        "status":"frozen","reviewed_by":"software-fixture","criteria_contract":criteria.CONTRACT,"ambiguities":[],
        "authoring":{"role":"human_reviewed_source","scope":"request_and_source_only","evidence_sha256":"b"*64},
        "groups":[{"id":"edit","kind":"edit","weight":1,"items":[item("E1","user_requirement")]},
                  {"id":"preserve","kind":"preserve_core","weight":1,"items":[item("P1","source_relation")]}]}
    value["card_sha256"] = signature(value)
    return value


class Contracts(unittest.TestCase):
    def state(self):
        value={"request":{"text":"Make it blue.","source":{"sha256":"a"*64,"duration_seconds":2}}}
        criteria.install(value, card())
        return value

    def test_planner_cannot_move_criteria_and_objection_does_not_change_hash(self):
        state=self.state(); before=state["requirements"]["sha256"]
        with self.assertRaisesRegex(ValueError,"independently frozen"):
            ledger.set_requirements(state, state["requirements"]["items"], "Make passing easier")
        criteria.objection(state,"A source relation may be ambiguous.","The contact is occluded in the source.")
        self.assertEqual(state["requirements"]["sha256"],before)
        criteria.verify_state(state)

    def test_tampered_grade_fails_before_resume(self):
        state=self.state(); state["requirements"]["items"][0]["priority"]="detail"
        with self.assertRaisesRegex(ValueError,"Frozen criteria changed"): criteria.verify_state(state)

    def test_wrong_source_and_missing_boundaries_rejected(self):
        value=card(); value["groups"][0]["items"][0].pop("pass_rule"); value.pop("card_sha256");value["card_sha256"]=signature(value)
        with self.assertRaisesRegex(ValueError,"pass_rule"): criteria.validate(value)
        state=self.state();state["request"]["source"]["sha256"]="c"*64
        with self.assertRaisesRegex(ValueError,"source/request"): criteria.install(state,card())

    def test_goal_weight_survives_item_splitting(self):
        a={"id":"A","kind":"edit","priority":"core","group":"G1","group_weight":1}
        b={**a,"id":"B","group":"G2"}
        first=ledger.scores([a,b],{"A":"pass","B":"fail"})["edit"]["score"]
        second=ledger.scores([a,{**a,"id":"A2"},b],{"A":"pass","A2":"pass","B":"fail"})["edit"]["score"]
        self.assertEqual(first,second)

    def test_declared_prediction_and_cards_remain_optional(self):
        req=self.state()["requirements"]
        value={"targets":["E1"],"change":"Blue pigment","expect":"Blue becomes visible"}
        ledger.intent(value,req)
        ledger.intent({**value,"expected_verdicts":{"E1":"pass"},"cards":["S1"]},req)
        with self.assertRaises(ValueError): ledger.intent({**value,"expected_verdicts":{"E1":"excellent"}},req)

    def test_major_damage_cannot_be_unsupported_or_detail_only(self):
        req=self.state()["requirements"]
        obs={"o":{"frames":[{"video":"source"},{"video":"v1"}]}}
        report={"major_damage":True,"requirement_verdicts":[{"id":k,"verdict":"pass","evidence":"Observed.","observations":["o"]} for k in ("E1","P1")]}
        with self.assertRaisesRegex(ValueError,"rationale"): ledger.validate_review(copy.deepcopy(report),req,"v1",{"source":{},"v1":{}},obs)
        report["requirement_verdicts"][1]["verdict"]="fail"
        report["damages"]=[{"requirement_ids":["P1"],"reason":"Interaction is lost","evidence":"Visible replacement","observations":["o"]}]
        ledger.validate_review(copy.deepcopy(report),req,"v1",{"source":{},"v1":{}},obs)
        req["items"][1]["priority"]="detail"
        with self.assertRaisesRegex(ValueError,"Detail-only"): ledger.validate_review(report,req,"v1",{"source":{},"v1":{}},obs)

    def test_delivered_success_differs_from_best_in_set(self):
        from planner_harness.rsi_validation import decision_metrics
        rows=[{"id":"v1","success":True,"core":1,"utility":.9},{"id":"v2","success":False,"core":.5,"utility":.3}]
        result=decision_metrics(rows,"v2")
        self.assertEqual(result["delivered_success"],0)
        self.assertEqual(result["candidate_set_success"],1)
        self.assertEqual(result["selected_utility"],.3)

    def test_visual_quality_enters_explicit_utility_and_unknown_stays_unknown(self):
        from planner_harness.rsi_judge import utility_components
        scored={"semantic":{"edit":{"score":1}},"ratings":{"style":4},"rating_status":{"style":"scored"}}
        self.assertEqual(utility_components(scored,{"edit":.5,"rating:style":.5}),{"edit":1,"rating:style":1})
        scored["rating_status"]["style"]="unknown"
        self.assertIsNone(utility_components(scored,{"rating:style":1})["rating:style"])

    def test_live_gate_rejects_action_count_objective(self):
        from planner_harness.rsi_validation import validate_quality_protocol
        with self.assertRaisesRegex(ValueError,"delivered quality"):
            validate_quality_protocol({"primary_metric":"non_improving_generations"})

    def test_maintain_correct_replay_target_passes_without_forced_change(self):
        from planner_harness.rsi_paired_replay import summarize
        rows=[{"id":arm,"decision_id":"x","arm":arm,"status":"decision_recorded","decision":{"action":"generate","arguments":{"input_video":"source"}},"earlier_candidates":[]} for arm in ("base","candidate")]
        result=summarize(rows,[{"decision_id":"x","metric":"stop_rate","direction":"maintain","tolerance":0}])
        self.assertEqual(result["status"],"passed")

    def test_claim_queries_count_counterexamples_and_keep_unknown(self):
        record={"id":"r","source_sha256":"a"*64,"request":"Blue","renderer":"bernini","state_sha256":"b"*64,"attempts":[],"task_memory":{}}
        for i,value in enumerate((True,False,None)):
            record["attempts"].append({"job":str(i),"input":"source","independent_evaluations":[{"result":{"success":value}}]})
        claim={"id":"EC1","claim":"A proposed association","mechanism":"Unverified explanation","comparison":"No randomized comparison","limitations":"One source", "query":{"where":{"renderer":"bernini"},"outcome":"independent_success","expected":True}}
        result=evidence.refresh([record],[{"claims":[claim],"cards":[{"id":"S1","evidence_claims":["EC1"]}]}])
        self.assertEqual(result["claims"]["EC1"]["known"],2)
        self.assertEqual(result["claims"]["EC1"]["unknown"],1)
        self.assertEqual(result["claims"]["EC1"]["status"],"mixed")
        self.assertEqual(result["todos"][0]["kind"],"review_skill")
        self.assertTrue(result["publication"].startswith("none"))

    def test_query_code_and_dangling_skill_evidence_rejected(self):
        with self.assertRaises(ValueError): evidence.validate_claim({"id":"x","claim":"x","mechanism":"x","comparison":"x","limitations":"x","query":{"eval":"evil"}})
        with self.assertRaisesRegex(ValueError,"unavailable"): evidence.refresh([],[{"cards":[{"id":"x","evidence_claims":["absent"]}]}])

    def test_partition_rejects_neighboring_source_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"prefix.json";save(path,{"fixture":True})
            row={"id":"a","role":"development","source_sha256":"a"*64,"trajectory":"t","input":str(path),"input_sha256":sha(path)}
            with self.assertRaisesRegex(ValueError,"leakage"):
                evidence.freeze_partition([row,{**row,"id":"b","role":"heldout"}],Path(tmp)/"partition.json")

    def test_workflow_does_not_claim_rsi_after_proposal(self):
        from planner_harness.rsi_workflow import progress
        from planner_harness.rsi_data import sealed
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);body={"records":[]};sealed(root/"d.json",{**body,"sha256":ledger.digest(body)})
            result=progress({"development":str(root/"d.json")},root/"workflow")
            self.assertEqual(result["status"],"development_recorded")
            self.assertEqual(result["next_action"],"propose")

    def test_append_drafts_keep_existing_library_and_expose_claims(self):
        from planner_harness.rsi_support import candidate_knowledge
        result=candidate_knowledge(ROOT,"knowledge/staged/rsi-complete-20261031/catalog.json")
        ids={r["id"] for r in result.experiences}
        self.assertTrue({r["id"] for r in load(ROOT/"knowledge/experience/catalog.json")} <= ids)
        self.assertIn("judgment-identity",ids)

    def test_detail_is_not_promoted_by_mandatory_boolean(self):
        value=card();value["groups"].append({"id":"details","kind":"preserve_detail","weight":1,
            "items":[{**value["groups"][1]["items"][0],"id":"P2","mandatory":True}]})
        value.pop("card_sha256");value["card_sha256"]=signature(value)
        state=self.state();criteria.install(state,value)
        self.assertEqual(next(i for i in state["requirements"]["items"] if i["id"]=="P2")["priority"],"detail")

    def test_reviewed_semantic_labels_are_separate_and_queryable(self):
        record={"id":"r","source_sha256":"a"*64,"renderer":"bernini","request":"Blue","state_sha256":"b"*64,
                "attempts":[{"job":"j","input":"source","independent_evaluations":[{"result":{"success":True}}]}]}
        original=evidence.cases([record])[0]
        with tempfile.TemporaryDirectory() as tmp:
            ref=Path(tmp)/"review.txt";ref.write_text("Scripted semantic review",encoding="utf-8")
            annotation=evidence.annotate(original,{"realization_change":"substantive"},reviewed_by="fixture",reason="Test interpretation",evidence=[{"path":str(ref),"sha256":sha(ref)}])
            claim={"id":"C","claim":"Test association","mechanism":"Hypothesis","comparison":"Uncontrolled","limitations":"Fixture",
                   "query":{"where":{"label.realization_change":"substantive"},"outcome":"independent_success","expected":True}}
            result=evidence.refresh([record],[{"claims":[claim]}],annotations=[annotation])
            self.assertEqual(result["claims"]["C"]["support_count"],1)
            self.assertEqual(result["cases"][0]["original_case_sha256"],original["sha256"])
            ref.write_text("Changed",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"evidence changed"):
                evidence.refresh([record],[],annotations=[annotation])

    def test_monitoring_missing_observations_cannot_authorize_adoption(self):
        from planner_harness.rsi_workflow import monitor,verify_monitoring
        from planner_harness.rsi_data import sealed
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            def artifact(name,body):
                path=p/name;sealed(path,{**body,"sha256":ledger.digest(body)});return path
            cycle=artifact("cycle.json",{"protocol":{}})
            manifest=artifact("manifest.json",{"cycle":{"sha256":load(cycle)["sha256"]}})
            validation=artifact("validation.json",{"manifest":str(manifest),"status":"passed"})
            with patch("planner_harness.rsi_cycle.verify",return_value=load(cycle)):
                result=monitor({},cycle,validation,[],p/"monitor")
            self.assertEqual(result["status"],"needs_review")
            with self.assertRaisesRegex(ValueError,"incomplete"):
                verify_monitoring(p/"monitor/result.json",load(validation),load(cycle))

    def test_cycle_orchestrator_reuses_queue_and_stops_before_publication(self):
        from planner_harness.rsi_workflow import run
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            receipts=p/"batch/receipts/task";receipts.mkdir(parents=True)
            for arm in ("base","candidate"):save(receipts/(arm+".json"),{"run":str(p/arm)})
            cycle={"protocol":{"judge":{}},"splits":"splits.json"}
            round_result={"status":"ready_for_validation","revisions":[{"proposal":"proposal.json"}],"heldout_replay":{"path":"replay.json"}}
            with patch("planner_harness.rsi_cycle.verify",return_value=cycle),patch("planner_harness.rsi_calibration.verify_calibration"), \
                 patch("planner_harness.rsi_round.run_round",return_value=round_result), \
                 patch("planner_harness.rsi_validation.prepare",return_value={"tasks":[{"id":"task"}]}), \
                 patch("planner_harness.rsi_cli_ops.batch_command",return_value={"status":"complete"}) as batch, \
                 patch("planner_harness.rsi_validation.validate",return_value={"status":"passed"}), \
                 patch("planner_harness.rsi_workflow.monitor",return_value={"status":"passed"}), \
                 patch("planner_harness.rsi_validation.adopt") as adopt:
                result=run({"cycle":"cycle.json","round":{"heldout_replay":{"configured":True}},"service_config":"service.json"},p,object(),object(),root=ROOT)
                self.assertEqual(result["status"],"awaiting_adoption_review")
                self.assertEqual([c.args[0].command for c in batch.call_args_list],["batch-init","batch-run"])
                adopt.assert_not_called()

    def test_configured_anchors_are_reused_without_implicit_extra_jobs(self):
        from planner_harness.rsi_workflow import repeat_anchors
        with tempfile.TemporaryDirectory() as tmp:
            config={"cycle":"cycle.json","anchor_jobs":[{"kind":"critic_drift","request":"signed-request.json","reference":"previous-anchor.json"}]}
            with patch("planner_harness.rsi_anchors.run") as run:
                result=repeat_anchors(config,{},Path(tmp),root=ROOT)
                run.assert_called_once()
                self.assertEqual(result["critic_drift"]["reference"],"previous-anchor.json")
                self.assertEqual(repeat_anchors({}, {}, Path(tmp),root=ROOT),{})
                self.assertEqual(run.call_count,1)


class Integration(unittest.TestCase):
    def test_independent_card_to_auto_critic_to_delivery_without_requirements_form(self):
        import test_rsi as legacy
        from planner_harness.video import Video
        f=legacy.RSITests();f.setUp()
        try:
            info=Video(f.source,f.root/"inspect").info
            path=f.root/"card.json";save(path,card(info["sha256"],info["duration_seconds"]))
            state=f.start([legacy.call("generate",input_video="source",prompt="Blue surfaces",intent=legacy.INTENT)],rsi={"task_card":str(path)})
            self.assertEqual(state["criteria_authority"],"independent_frozen")
            self.assertEqual(len(state["requirement_versions"]),1)
            self.assertIn("task_criteria",json.loads(f.model.inputs[0]["user_text"]))
            f.generation();state=f.resume([])
            self.assertTrue(state["pending_tool"].endswith("auto-critique"))
            f.review();state=f.resume([legacy.call("finish",video="v1",stop_reason="satisfied")])
            self.assertEqual(state["status"],"complete")
            self.assertEqual(state["final"]["delivery_status"],"criteria_satisfied")
        finally: f.tearDown()


if __name__=="__main__": unittest.main()
