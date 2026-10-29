"""Record exploratory visual judgments for completed direct-prompt samples."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def frames(video, destination, count=12):
    import av
    destination.mkdir(parents=True, exist_ok=True)
    with av.open(str(video)) as container:
        decoded = [(float(f.time), f.to_image()) for f in container.decode(video=0)]
    indices = sorted({round(i * (len(decoded)-1)/(count-1)) for i in range(count)})
    paths, times = [], []
    for index in indices:
        t, image = decoded[index]
        path = destination / f"{index:04d}.jpg"
        image.save(path, quality=94)
        paths.append(str(path)); times.append(round(t, 3))
    return paths, times


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--only", nargs="*")
    args = p.parse_args()
    spec = json.loads(args.manifest.read_text(encoding="utf-8"))
    samples = {r["sample_id"]: r for r in json.loads((ROOT/"benchmark_data/all_samples.json").read_text(encoding="utf-8"))}
    from vlm.codex_vlm import CodexVisionModel
    model = CodexVisionModel(role="probe_evaluator")
    for case in spec["cases"]:
        if args.only and case["case_id"] not in args.only:
            continue
        directory = args.manifest.resolve().parent / case["case_id"]
        result_path = directory / "result.json"
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text())
        if result.get("status") != "complete":
            continue
        judgment_path = directory / "judgment.json"
        if judgment_path.exists():
            prior = json.loads(judgment_path.read_text())
            if prior.get("output_sha256") != result["output_sha256"]:
                raise ValueError("Stale judgment exists for a changed output")
            continue
        source_paths, source_times = frames(ROOT/case["source_video"], directory/"judge_source")
        output_paths, output_times = frames(directory/"edited.mp4", directory/"judge_output")
        sample = samples[case["sample_id"]]
        requirement = sample["prompt_short"] if case["condition"] == "short" else sample["prompt_long"]
        request = {"user_requirement": requirement, "source_frame_times_seconds": source_times,
                   "output_frame_times_seconds": output_times, "source_images_first": len(source_paths),
                   "style_observations": case["evaluation"]["style"],
                   "preserve_observations": case["evaluation"]["preserve"],
                   "note": case["evaluation_note"]}
        system = """Compare source and edited video frames. You are judging a direct video model,
not a planner. The first image group is SOURCE and the second is OUTPUT, both in time order.
Report observable evidence only. Separate requested style transformation from semantic damage.
Illustration/etching may change texture, color and realistic facial rendering. Glitch art may
intentionally shift pixels and flicker. Judge preservation of identifiable entities, spatial
relationships, roles and actions under those allowed changes. Do not require invisible details.
Only sampled frames are available: exact fast ball trajectories, precise motion timing and
between-frame stability may be unjudgeable. Do not claim full temporal verification.
Return JSON with keys: style_match {label: clear|partial|absent|unjudgeable, evidence},
edits [{item, explicitly_required: boolean, label: done|partial|not_done|unjudgeable, evidence,
times_seconds}], preservation [{item, label: kept|partial|changed|unjudgeable, evidence,
times_seconds}], unintended_damage [observations], temporal_limitations [observations],
summary. Cover every provided observation item exactly once and copy its item text exactly. For a short style-only request,
detailed rendering cues can support the style judgment but are not automatically mandatory.
Do not output a combined score, infer the prompting condition, or offer edits to code."""
        os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(args.manifest.resolve().parent/"judge_calls.jsonl")
        (directory/"judge_input.json").write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding="utf-8")
        response = model.predict_json(system_prompt=system,
                                      user_text=json.dumps(request,ensure_ascii=False),
                                      image_paths=source_paths+output_paths)
        (directory/"judge_raw.json").write_text(json.dumps(response,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        expected = {"edits":case["evaluation"]["style"], "preservation":case["evaluation"]["preserve"]}
        for key, items in expected.items():
            if sorted(r["item"] for r in response[key]) != sorted(items):
                raise ValueError(f"Judge did not cover the requested {key} items")
        payload = {"case_id":case["case_id"],"output_sha256":result["output_sha256"],
                   "model":model.model,"reasoning_effort":model.reasoning_effort,
                   "evidence_scope":"12 sampled frames per clip; exploratory VLM judgment",
                   "judgment":response}
        judgment_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"case_id":case["case_id"],"style_match":response["style_match"],
                          "preservation_labels":[r["label"] for r in response["preservation"]]},ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()
