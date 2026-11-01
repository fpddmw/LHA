"""Wiki/revision integration checks with scripted responses; no paid models or GPUs."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import test_rsi as fixtures
from planner_harness.common import load, save, sha
from planner_harness.knowledge import Knowledge
from planner_harness.ledger import digest
from planner_harness import rsi_data as data
from planner_harness.rsi_wiki import evidence_images, replay_feedback


class WikiTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RSITests(); self.f.setUp(); self.root = self.f.root
    def tearDown(self):
        self.f.tearDown()

    def add_case(self):
        catalog = load(self.root / "knowledge/experience/catalog.json")
        image = self.root / "knowledge/frame.jpg"; image.write_bytes(b"fixture image bytes")
        file = self.root / "knowledge/case.md"; file.write_text("# Case\n[[case-frame|Inspect the archived frame]]\n")
        catalog.append({"id":"case-one", "title":"Case", "kind":"experiment_case", "path":"knowledge/case.md", "version":1,
                        "assets":[{"id":"case-frame", "path":"knowledge/frame.jpg", "sha256":sha(image)}]})
        save(self.root / "knowledge/experience/catalog.json", catalog)
        return image

    def test_links_resolve_and_snapshot_protects_evidence(self):
        image = self.add_case(); k=Knowledge(self.root)
        self.assertTrue(k.read("case-one")["links"][0]["available"])
        snapshot=self.root / "snapshot.json"; k.freeze(snapshot)
        image.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"changed"):
            Knowledge(self.root,snapshot).resolve("case-frame")
        with self.assertRaisesRegex(ValueError,"changed"):
            Knowledge(self.root).freeze(self.root / "bad.json")

    def test_proposer_reads_linked_image_and_caches(self):
        image = self.add_case()
        body={"records":[], "aggregates":{}}; body["sha256"]=digest(body)
        path=self.root / "development.json"; save(path,body)
        model=fixtures.ScriptedModel([
            {"action":"read_knowledge","arguments":{"id":"case-one"}},
            {"action":"view_reference","arguments":{"id":"case-frame"}},
            {"summary":"Need a task-matched comparison.","changes":[],"limitations":["Scripted fixture."],
             "evidence_requests":["Compare alternative prompts on the same input."]}])
        out=self.root / "knowledge/staged/images"
        result=data.propose(path,out,model,root=self.root)
        packet=load(out / "model-calls/003/single-call.json")["packet"]
        self.assertEqual(packet["images"][0]["sha256"],sha(image))
        self.assertEqual(json.loads(packet["user_text"])["operations"][0]["result"]["links"][0]["id"],"case-frame")
        self.assertEqual(result["status"],"no_change")
        self.assertEqual(data.propose(path,out,model,root=self.root),result)
        self.assertEqual(len(model.inputs),3)

    def test_concept_stage_preserves_kind_and_rejects_evidence_rewrite(self):
        self.add_case(); original=load(self.f.proposal())
        change=copy.deepcopy(original["changes"][0]);change.update(id="new-concept",kind="concept",text="# Concept\n[[case-one|Boundary evidence]]\n")
        change["cards"][0]["id"]="concept-card"
        result={"summary":"Explain a boundary.","changes":[change],"limitations":["Unvalidated."]}
        proposal=data.stage_proposal(result,self.f.packet(),self.root / "knowledge/staged/concept",root=self.root)
        row=next(r for r in load(proposal["candidate_catalog"])["entries"] if r["id"]=="new-concept")
        self.assertEqual(row["kind"],"concept")
        result["changes"][0]["id"]="case-one"
        with self.assertRaisesRegex(ValueError,"immutable"):
            data.stage_proposal(result,self.f.packet(),self.root / "knowledge/staged/rewrite",root=self.root)

    def test_dangling_links_and_outside_feedback_are_rejected(self):
        original=load(self.f.proposal());original["changes"][0]["text"]="[[nonexistent]]"
        with self.assertRaisesRegex(ValueError,"unavailable"):
            data.stage_proposal(original,self.f.packet(),self.root / "knowledge/staged/dangling",root=self.root)
        body={"records":[]};body["sha256"]=digest(body);path=self.root / "development.json";save(path,body)
        with self.assertRaisesRegex(ValueError,"collected development"):
            data.propose(path,self.root / "knowledge/staged/leak",None,root=self.root,feedback=[{"samples":[{"decision_id":"heldout/e1"}]}])

    def test_replay_delivers_reference_on_next_call(self):
        image=self.add_case()
        second=self.root / "knowledge/second.jpg";second.write_bytes(image.read_bytes())
        catalog=load(self.root / "knowledge/experience/catalog.json")
        catalog[-1]["assets"].append({"id":"second-frame","path":"knowledge/second.jpg","sha256":sha(second)})
        save(self.root / "knowledge/experience/catalog.json",catalog)
        self.f.start([fixtures.call("requirements",items=fixtures.REQ),fixtures.call("generate",input_video="source",prompt="Blue.",intent=fixtures.INTENT)])
        proposal=self.f.proposal()
        model=fixtures.ScriptedModel([fixtures.call("view_reference",id=["case-frame","second-frame"]), fixtures.call("finish",video="source",stop_reason="no_promising_attempt")])
        from planner_harness.rsi_replay import replay
        out=self.root / "replay"
        replay(self.f.output / "calls/event-0002/input.json",load(proposal)["candidate_catalog"],out,model,root=self.root)
        packet=load(out / "calls/002/single-call.json")["packet"]
        self.assertTrue(any(i["path"].endswith("frame.jpg") for i in packet["images"]))
        self.assertTrue(any(i["path"].endswith("second.jpg") for i in packet["images"]))
        self.assertEqual(json.loads(packet["user_text"])["attached_images_in_order"][-1]["kind"],"knowledge reference, not source-video evidence")

    def test_recorded_evidence_is_labeled_and_missing_video_stays_missing(self):
        self.f.start([fixtures.call("requirements",items=fixtures.REQ),fixtures.call("generate",input_video="source",prompt="Blue.",intent=fixtures.INTENT)])
        path=self.f.output / "calls/event-0002/input.json"
        packet={"development":{"records":[{"id":"r", "decisions":[{"id":"e","input":str(path),"input_sha256":sha(path)}]}]}}
        value=evidence_images(packet,{"id":"r","decision":"e","videos":["source","v9"]},self.root)
        self.assertEqual(value["missing_videos"],["v9"])
        self.assertTrue(value["images"])
        self.assertTrue(all(i["run_id"]=="r" and i["video_id"]=="source" for i in value["images"]))

    def test_bounded_revision_feeds_actual_trace_and_resumes(self):
        from planner_harness import rsi_round
        p=self.root / "input.json";save(p,{"fixture":True})
        development={"records":[{"id":"r1","decisions":[{"id":"e1","input":str(p),"input_sha256":sha(p)}]}],"sha256":"fixture"}
        proposal=load(self.f.proposal()); feedback_seen=[]
        config={"runs":[],"splits":"fixture", "replay_decisions":["r1/e1"],"candidate_directory":str(self.root / "knowledge/staged/series"),"max_revisions":2}
        def propose(*args,**kwargs):
            feedback_seen.append(kwargs["feedback"].copy())
            return proposal if not kwargs["feedback"] else {**proposal,"status":"no_change","evidence_requests":["Need an actual visual outcome."]}
        def probe(*args,**kwargs):
            out=Path(args[3]);decision={"action":"generate","arguments":{"input_video":"source","prompt":"Blue."}}
            trace_path=out / digest("r1/e1")[:16] / "0/base/result.json"
            trace={"decision":decision,"operations":[{"request":{"action":"read"},"result":{"text":"Actual returned evidence."}}]};save(trace_path,trace)
            row={"id":"r1/e1/0/base","decision_id":"r1/e1","sample":0,"arm":"base","decision_sha256":digest(decision)}
            body={"status":"no_predicted_shift","samples":[row],"comparisons":[]};body["sha256"]=digest(body);save(out / "result.json",body);return body
        with patch.object(rsi_round,"collect",return_value=development),patch.object(rsi_round,"propose",side_effect=propose),patch.object(rsi_round,"probe",side_effect=probe):
            result=rsi_round.run_round(config,self.root / "series",None,None,root=self.root)
            self.assertEqual(result["status"],"needs_evidence")
            self.assertEqual(len(result["revisions"]),2)
            self.assertEqual(feedback_seen[1][0]["samples"][0]["operations"][0]["result"]["text"],"Actual returned evidence.")
            again=rsi_round.run_round(config,self.root / "series",None,None,root=self.root)
            self.assertEqual(result,again)

    def test_real_seed_has_resolvable_links_and_verified_assets(self):
        k=Knowledge(ROOT)
        rows=[r for r in k.experiences if r.get("kind") in {"concept","experiment_case","knowledge_map"}]
        self.assertEqual(len(rows),8)
        for row in rows:
            self.assertTrue(all(link["available"] for link in k.read(row["id"])["links"]),row["id"])
            for asset in row.get("assets",[]):
                _,path=k.resolve(asset["id"])
                self.assertEqual(sha(path),asset["sha256"])

    def test_round_uses_real_proposer_feedback_contract_and_cached_calls(self):
        from planner_harness import rsi_round
        seed=load(self.f.proposal())
        decision_file=self.root / "input.json";save(decision_file,{"fixture":True})
        dev={"records":[{"id":"r1","attempts":[],"decisions":[{"id":"e1","input":str(decision_file),"input_sha256":sha(decision_file)}]}]}
        dev["sha256"]=digest(dev)
        def collect(*args,**kwargs):
            return data.sealed(args[2],dev)
        def probe(*args,**kwargs):
            out=Path(args[3]); action={"action":"generate","arguments":{"input_video":"source","prompt":"Blue."}}
            save(out / digest("r1/e1")[:16] / "0/base/result.json",{"decision":action,"operations":[{"request":{"action":"read"},"result":{"text":"The advice was read."}}]})
            body={"status":"no_predicted_shift","comparisons":[],"samples":[{"id":"r1/e1/0/base","decision_id":"r1/e1","sample":0,"arm":"base","decision_sha256":digest(action)}]}
            return data.sealed(out / "result.json",{**body,"sha256":digest(body)})
        model=fixtures.ScriptedModel([{k:seed[k] for k in ("summary","changes","limitations")},
            {"action":"read_feedback","arguments":{"index":0}},
            {"summary":"Evidence is insufficient.","changes":[],"limitations":["Software fixture."],"evidence_requests":["Need a paired render."]}])
        config={"runs":[],"splits":"fixture","replay_decisions":["r1/e1"],"candidate_directory":str(self.root / "knowledge/staged/automatic"),"max_revisions":2}
        with patch.object(rsi_round,"collect",side_effect=collect),patch.object(rsi_round,"probe",side_effect=probe):
            result=rsi_round.run_round(config,self.root / "round",model,None,root=self.root)
            self.assertEqual(result["status"],"needs_evidence")
            self.assertEqual(len(model.inputs),3)
            again=rsi_round.run_round(config,self.root / "round",model,None,root=self.root)
            self.assertEqual(result,again)
            self.assertEqual(len(model.inputs),3)
        packet=load(self.root / "knowledge/staged/automatic-revision-2/model-calls/002/single-call.json")["packet"]
        self.assertIn("The advice was read.",packet["user_text"])


if __name__=="__main__":
    unittest.main()
