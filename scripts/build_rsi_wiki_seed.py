"""Reproduce the reviewed-scope Wiki seed from saved replay evidence; no model calls."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.common import load, save, sha
from planner_harness.ledger import digest
from planner_harness.rsi_data import sealed
from planner_harness.rsi_wiki import replay_feedback


def build():
    archive = ROOT / "out/rsi_paired_replay/20261031_real_decisions"
    dest = ROOT / "knowledge/wiki"
    catalog_path = ROOT / "knowledge/experience/catalog.json"
    catalog = load(catalog_path)
    receipt_dir = ROOT / "out/wiki_proposer/20261031"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    before = receipt_dir / "catalog-before.json"
    if not before.exists():
        save(before, catalog)
    descriptions = {
        "bernini_027_after_v1": ("Etching and architectural identity", "wiki-scene-identity",
            "Both replay arms proposed another source generation in all three samples. They treated altered architectural silhouettes as core preservation requirements. The historical online and independent judgments disagree about severity. This case locates a classification question; it does not establish that stopping or regenerating is optimal."),
        "bernini_024_before_v3": ("Glitch: source restart and overlapping realizations", "wiki-realization",
            "Both arms proposed source restart in all three samples. New proposals described translucent RGB echoes and picture-bearing strips, overlapping previous prompt demands. Two assisted samples also proposed comparing v1. No new rendering tested whether the revised descriptions changed the failure-producing construction."),
        "ditto_024_before_v3": ("Glitch: earlier candidate and the retry exception", "wiki-realization",
            "Both arms chose v1 in all three samples. All assisted samples read S5 yet continued under a different-realization exception. The previous prompt already requested displaced picture strips and scene-bearing rectangles. Mosaic wording may or may not elicit a different result; this remains untested."),
        "bernini_003_before_v3": ("Fantasy study: authored occlusion and a concrete revision", "wiki-connected-change",
            "Both arms proposed source restart in all three samples. Both removed or reduced an authored robe and excessive book glow; assisted samples consistently used the original fitted jacket shape. Occlusion of chair support does not by itself establish deletion of chair geometry. These intercepted proposals have no new generated outcome.")}
    rows = []
    cases_dir = dest / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    for name, (title, concept, interpretation) in descriptions.items():
        prefix_path = archive / "cases" / name / "prefix.json"
        prefix = load(prefix_path)
        result_path = archive / "runs" / name / "result.json"
        result = load(result_path)
        sample = result["samples"][0]
        call = load(result_path.parent / digest(sample["decision_id"])[:16] / "0/base/calls/001/single-call.json")
        mapping = json.loads(call["packet"]["user_text"])["attached_images_in_order"]
        identity = "case-" + name.replace("_", "-")
        payload = prefix["neutral_payload"]
        record = {"case": name, "origin": "Historical development evidence; not an automatic RSI proposal",
                  "prefix_path": str(prefix_path.relative_to(ROOT)), "prefix_sha256": sha(prefix_path),
                  "task": payload["task"], "videos": payload["videos"], "evaluations": payload["evaluations"],
                  "replay_result_path": str(result_path.relative_to(ROOT)), "replay_result_sha256": sha(result_path),
                  "replay_comparisons": result["comparisons"], "samples": result["samples"]}
        record_path = cases_dir / (name + ".json")
        sealed(record_path, record)
        assets = [{"id": identity + "-record", "path": record_path.relative_to(ROOT).as_posix(), "sha256": sha(record_path), "title": title + ": complete task, prompts, reviews and decisions"}]
        lines = ["# " + title, "", "Historical development case. Interpretation below is human-assisted, not a newly measured result.", "",
                 "## Task", "", payload["task"]["text"], "", "## What this case exposes", "", interpretation, "",
                 "Read [["+concept+"|the contextual distinction]] or [["+identity+"-record|the complete actual prompts, reviews and replay decisions]].", "",
                 "## Sampled frame comparisons", "", "These are archived frames already shown to Planner. They support appearance judgments; temporal behavior needs sequence evidence.", ""]
        for video in sorted({r.get("video_id", "source") for r in mapping}):
            frames = [r for r in mapping if r.get("video_id", "source") == video]
            for index in sorted({0, len(frames)-1}):
                frame = frames[index]
                path = Path(frame["path"])
                if sha(path) != frame["sha256"]:
                    raise ValueError("Archived frame changed")
                target = dest / "assets" / (identity+"-"+video+"-"+str(index)+".jpg")
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and sha(target) != frame["sha256"]:
                    raise ValueError("Wiki evidence changed")
                if not target.exists():
                    shutil.copyfile(path, target)
                asset_id = target.stem
                title_frame = f"{video} at {frame.get('timestamp_seconds', 'unknown')} seconds"
                assets.append({"id": asset_id, "path": target.relative_to(ROOT).as_posix(), "sha256": sha(target),
                               "title": title_frame, "video_id": video, "timestamp_seconds": frame.get("timestamp_seconds")})
                lines += [f"[[{asset_id}|Inspect {title_frame}]]", "", f"![{title_frame}](../assets/{target.name})", ""]
        lines += ["## Provenance", "", f"Recorded prefix SHA256: `{sha(prefix_path)}`.", "", f"Replay result SHA256: `{sha(result_path)}`.", "",
                  "Later outcomes in this historical library make this development material. It is not a held-out test case.", ""]
        file = cases_dir / (name + ".md")
        file.write_text("\n".join(lines), encoding="utf-8")
        rows.append({"id": identity, "title": title, "path": file.relative_to(ROOT).as_posix(), "kind": "experiment_case",
                     "version": 1, "origin": "human_assisted_historical_case", "assets": assets})
        feedback = replay_feedback(result_path, {"summary": "Historical E0 versus assisted E1; no automated proposal."}, root=ROOT)
        sealed(receipt_dir / "feedback" / (name+".json"), {**feedback, "sha256": digest(feedback)})
    concepts = [("wiki-scene-identity", "Scene identity and stylization", "When geometry differs, relate its consequence to this task's identity, action and spatial relationships; inspect the disputed cases."),
                ("wiki-realization", "Rewording and changed visual realization", "When another attempt depends on a new realization, compare the actual earlier prompt and changed visual relationships; a new label alone leaves the hypothesis unresolved."),
                ("wiki-connected-change", "Connected visual changes and local repair", "When a proposed repair affects interacting surfaces, light or occlusion, examine those relationships and the renderer's actual controls before predicting locality.")]
    for identity, title, summary in concepts:
        rows.append({"id": identity, "title": title, "path": "knowledge/wiki/"+identity+".md", "kind": "concept", "version": 1,
                     "origin": "human_assisted_interpretation_unvalidated", "cards": [{"id": identity, "summary": summary, "status": "interpretation_unvalidated", "renderer_scope": "any"}]})
    rows.append({"id": "wiki-map", "title": "Judgment concepts and experimental cases", "path": "knowledge/wiki/README.md", "kind": "knowledge_map", "version": 1, "origin": "human_assisted_navigation"})
    ids = {r["id"] for r in rows}
    save(catalog_path, [r for r in catalog if r["id"] not in ids] + rows)
    save(receipt_dir / "seed-receipt.json", {"case_count": len(descriptions), "concept_count": len(concepts),
         "catalog_before_sha256": sha(before), "catalog_after_sha256": sha(catalog_path), "model_calls": 0, "renderer_calls": 0,
         "scope": "Authorized human-assisted starting knowledge. Historical E1 and replay artifacts unchanged; no automatic knowledge promotion."})


if __name__ == "__main__":
    build()
