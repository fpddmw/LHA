"""Build review material from saved evidence; no model, renderer or publication calls."""
import copy
import json
from pathlib import Path
import sys
import shutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from planner_harness.common import load,save,sha
from planner_harness.ledger import digest
from planner_harness.rsi_evidence import refresh,branch_library
from planner_harness.task_criteria import CONTRACT,validate


def item(identity,text,origin,reason,passed,partial,failed,variation=(),temporal=False,mandatory=True):
    return dict(id=identity,text=text,origin=origin,importance_reason=reason,
        source_evidence="User request and the linked previously reviewed source description; current source review pending.",
        pass_rule=passed,partial_rule=partial,fail_rule=failed,allowed_variation=list(variation),
        temporal=temporal,evidence="sequence" if temporal else "frames",mandatory=mandatory)


def group(identity,kind,*items): return dict(id="goal_"+identity,kind=kind,weight=1,items=list(items))


def examples(output):
    old=ROOT/"out/agent_loop_live/20261030/phase2/runtime/deployment/cards"
    cards=[]
    for identity in ("041__short","027__short","fewshot_004__long"):
        historical=load(old/(identity+".json"))
        card={k:historical[k] for k in ("protocol","task_id","source_id","split","track","source_video","source_sha256","requirement","style_family","style_required","creativity","duration_seconds","source_start_seconds")}
        card.update(status="draft",reviewed_by=None,criteria_contract=CONTRACT,
            authoring={"role":"human_reviewed_source","scope":"request_and_source_only","evidence_sha256":sha(old/(identity+".json")),
                       "note":"Editorial proposal based on a saved source review; no new source inspection or independent model call."},
            annotation_note="Review proposal, not a frozen standard. Existing judgments are not rewritten.",ambiguities=[])
        if identity=="041__short":
            card["scene_summary"]="A man writes at a table while a woman is beside him; writing tools, a notebook and a separate sheet are visible in the saved source description."
            card["allowed_changes"]=["Coherent illustration medium, palette, linework, shading and stylized appearance.","Simplification consistent with a recognizable writing scene."]
            card["groups"]=[
                group("storybook","edit",item("storybook_style","A coherent children's-storybook illustration treatment.","user_requirement","This is the requested transformation.","Illustrative treatment is established across the main subjects and setting in observed coverage.","Treatment is recognizable but localized or materially inconsistent.","The scene remains photographic or lacks a recognizable illustrative treatment.",["Watercolor, pencil, cut-paper or another coherent realization; no prescribed palette."])),
                group("interaction","preserve_core",item("writing_relation","The writing activity and the participants' involvement remain recognizable.","source_relation","Changing this interaction would change the depicted activity rather than its rendering.","The writer, nearby companion and tool-to-page activity remain legible.","The activity remains recognizable but a consequential part of the interaction is lost.","Writing is replaced by another action or its participants' roles are lost.",["Stylized faces and simplified contours."])),
                group("temporal","preserve_core",item("writing_continuity","The writing activity continues over the task interval.","source_relation","The task transforms the appearance of an existing video activity.","Observed continuous evidence supports the activity's continuation over the claimed interval.","Continuity is preserved for only part of an adequately observed interval.","A supported sequence shows the writing activity interrupted or replaced.",["Exact photographic micro-motion is not required by the short request."],True)),
                group("details","preserve_detail",item("paper_structure","Report the pen, notebook binding and loose-sheet relationship separately from the writing activity.","source_relation","Incidental structure is useful to report without making it a new mandatory creative constraint.","Visible structures retain their source relationships within stylization.","Some structure remains while another part changes.","The corresponding visible structure is replaced or absent.",["Graphic simplification."],mandatory=False))]
        elif identity=="027__short":
            card["scene_summary"]="An elevated view of roofs, trees, distant domes and towers under a mostly open sky, with slow viewpoint movement."
            card["allowed_changes"]=["Etched linework, hatching, tonal translation, paper texture and graphic simplification."]
            card["ambiguities"]=["The severity boundary between landmark replacement and permissible contour simplification requires source-grounded review; historical judges disagree."]
            card["groups"]=[
                group("etching","edit",item("etching_style","A recognizable nineteenth-century etching treatment.","user_requirement","Requested style.","Line and tonal treatment coherently establish etching across the view.","Etching is visible only in parts or mixed with conflicting photographic treatment.","Etching treatment is absent.",["Different coherent etched palettes and paper treatments."])),
                group("scene","preserve_core",item("scene_relations","The source town view remains recognizable through its main spatial relationships.","source_relation","Spatial organization carries the scene identity.","Foreground roofs, trees and distant skyline retain recognizable ordering and correspondence.","The town remains recognizable but a consequential spatial relation changes.","Major replacement or rearrangement makes the depicted scene a different town view.",["Simplified roof and landmark contours; exact outlines are not automatically mandatory."])),
                group("camera","preserve_core",item("viewpoint","Preserve the broad viewpoint progression.","source_relation","The request changes rendering rather than the camera event.","Continuous evidence supports the same broad movement and view order.","Some movement or view order changes while the broad progression remains.","Movement or view order is replaced.",["Stylized edges may move differently at pixel scale."],True)),
                group("details","preserve_detail",item("incidental_geometry","Report fine roof features and sky additions with their actual effect on scene identity.","source_relation","Incidental geometry is distinct from consequential scene replacement.","Fine structures remain recognizable without unrelated additions.","Some incidental structures change.","Fine structures are extensively replaced.",["Paper grain and hatching are not new scene objects."],mandatory=False))]
        else:
            card["scene_summary"]="Two foreground players rally across a blue table; other people and tables are visible behind them."
            card["allowed_changes"]=["Replace the room with a metallic space-station arena, blue-white lighting and Earth-facing windows.","Sci-fi athletic clothing and blue tabletop-edge emission; retain explicitly requested faces, motion, trajectory, geometry and camera movement."]
            specs=[("arena","A futuristic space-station sports arena with metallic walls.","Metallic enclosing surfaces form a recognizable space-station sports setting."),
                   ("lighting","Blue-white arena lighting.","Blue-white illumination is established in the arena."),
                   ("earth","Earth visible through large windows.","Earth is recognizable through substantial window openings."),
                   ("suits","Sleek sci-fi athletic suits on the players.","Visible players have coherent sleek sci-fi athletic clothing."),
                   ("edges","Blue emission on the tabletop's outer edges.","Blue emission follows the tabletop perimeter; emission confined to legs or underside does not satisfy the location.")]
            card["groups"]=[group(k,"edit",item(k,text,"user_requirement","Explicit requested edit.",passed,
                "The requested property is present in only part of its specified extent or on only some named subjects.",
                "The property is absent or bound exclusively to an incorrect part.",["Coherent implementation choices within the named property."])) for k,text,passed in specs]
            for k,text,temporal in [("faces","Preserve recognizable player faces and identity features.",False),
                    ("geometry","Preserve table shape, perspective and net relationship.",False),
                    ("motion","Preserve playing actions and their broad sequence.",True),
                    ("trajectory","Preserve observable ball path, bounces and contact timing.",True),
                    ("camera","Preserve camera movement and view progression.",True)]:
                card["groups"].append(group(k,"preserve_core",item(k,text,"user_requirement","Explicit preservation demand.",
                    "Suitable source/candidate evidence supports the requested relation over the claimed scope.",
                    "Evidence establishes partial preservation and a specific remaining deviation.",
                    "Evidence establishes replacement or a consequential contradiction of the requested relation.",
                    ["Authorized clothing, environment and surface-light changes."],temporal)))
            card["ambiguities"]=["Small-ball trajectory remains unknown wherever source/candidate sequence evidence is insufficient."]
        validate(card,frozen=False)
        save(output/(identity+".draft.json"),card);cards.append(card)
    return cards


def main():
    output=ROOT/"out/rsi_complete_upgrade/20261031";output.mkdir(parents=True,exist_ok=True)
    cards=examples(output/"task-cards")
    development=load(ROOT/"out/rsi_review_remediation/20261031/development-final.json")
    save(output/"saved-branches.json",branch_library(development["records"]))
    catalog=load(ROOT/"knowledge/staged/rsi-complete-20261031/catalog.json")
    refreshed=refresh(development["records"],catalog["entries"])
    save(output/"saved-evidence-refresh.json",refreshed)
    historical=ROOT/"out/rsi_paired_replay/20261031_real_decisions/cycle/initial-planner-knowledge.json"
    if historical.exists():
        snapshot=load(historical)
        save(output/"historical-E0-snapshot.json",snapshot)
        save(output/"baseline-provenance.json",{"historical_snapshot":{"path":str(historical),"sha256":sha(historical)},
            "current_assisted_catalog":{"path":str(ROOT/"knowledge/experience/catalog.json"),"sha256":sha(ROOT/"knowledge/experience/catalog.json")},
            "scope":"Distinct preserved historical and current assisted assets; no active-library replacement."})
    save(output/"receipt.json",{"scope":"Saved-evidence and editorial review material only","task_card_drafts":len(cards),
         "historical_runs":len(development["records"]),"cases":len(refreshed["cases"]),"claims":refreshed["claims"],
         "paid_model_calls":0,"renderer_calls":0,"publication":"none","active_catalog_sha256":sha(ROOT/"knowledge/experience/catalog.json")})
    sections=["# Complete upgrade: review material", "These task cards are English editorial drafts based on saved source reviews. They are not newly judged outcomes or frozen experiment standards."]
    for c in cards:
        sections += ["## "+c["task_id"],c["requirement"],"Allowed changes: "+" ".join(c["allowed_changes"])]
        for g in c["groups"]:
            for row in g["items"]:
                sections += ["### "+row["id"]+" ("+g["kind"]+")",row["text"],"Reason: "+row["importance_reason"],
                             "Pass: "+row["pass_rule"],"Partial: "+row["partial_rule"],"Fail: "+row["fail_rule"],
                             "Allowed variation: "+" ".join(row["allowed_variation"])]
    sections += ["## Evidence linkage",f"{len(refreshed['cases'])} saved attempts were packaged without new generation. The new mechanism claims require labels/comparisons that these legacy runs do not contain. Unknown support remains unknown.",
                 "Read saved-evidence-refresh.json for claims and cases; saved-branches.json binds each observed branch to its actual recipe. New skill drafts remain under knowledge/staged/rsi-complete-20261031."]
    (output/"review.md").write_text("\n\n".join(sections)+"\n",encoding="utf-8")
    print(json.dumps({"review":str(output/"review.md"),"cases":len(refreshed["cases"]),"calls":0}))


def context_demo(output):
    """Capture the exact production contexts with scripted responses, no remote call."""
    sys.path.insert(0,str(ROOT/"scripts"))
    import test_rsi as fixture
    from test_rsi_complete import card
    from planner_harness.video import Video
    f=fixture.RSITests();f.setUp()
    try:
        info=Video(f.source,f.root/"inspect").info
        path=f.root/"card.json";save(path,card(info["sha256"],info["duration_seconds"]))
        f.start([fixture.call("generate",input_video="source",prompt="Blue surfaces",intent=fixture.INTENT)],rsi={"task_card":str(path)})
        f.generation();f.resume([]);f.review();state=f.resume([fixture.call("finish",video="v1",stop_reason="satisfied")])
        shutil.copytree(f.root,output,dirs_exist_ok=True)
        save(output/"scope.json",{"scope":"Production harness with synthetic video and scripted model answers. No actual Planner reasoning or renderer output is claimed.",
             "original_root":str(f.root),"relocated_root":str(output),"final":state["final"],"paid_calls":0})
    finally:f.tearDown()


def cycle_demo(output):
    """Retain the formal-contract test artifacts for inspection; all answers are fixtures."""
    sys.path.insert(0,str(ROOT/"scripts"))
    from test_rsi_review import ReviewIntegration
    check=ReviewIntegration();check.setUp()
    try:
        check.test_formal_replay_validation_and_test_share_cycle_environment()
        shutil.copytree(check.f.root,output,dirs_exist_ok=True)
        save(output/"scope.json",{"scope":"Software contract demonstration. Scripted replay, synthetic source videos, no renderer or independent judge dispatch. The test-only adoption record exercises a binding and is not actual publication.",
             "original_root":str(check.f.root),"relocated_root":str(output),"paid_calls":0,"active_publication":False})
    finally:check.tearDown()


if __name__=="__main__":
    main()
    context_demo(ROOT/"out/rsi_complete_upgrade/20261031/software-context")
    cycle_demo(ROOT/"out/rsi_complete_upgrade/20261031/software-cycle")
