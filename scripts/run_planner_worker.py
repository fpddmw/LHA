"""Execute one durable Planner tool job; the worker never selects a creative route."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from planner_harness.lock import RunLock


class EnglishEvaluationClient:
    """Adapt evidence prose language while retaining the evaluator's scoring contract."""
    def __init__(self, client, directory):
        self.client, self.directory = client, directory
        self.model = client.model
        self.reasoning_effort = client.reasoning_effort

    def predict_json(self, *, system_prompt, user_text, image_paths):
        effective = system_prompt.replace("Report observable evidence in Chinese.", "Report observable evidence in English.")
        directory = self.directory / f"call-{len(list(self.directory.glob('call-*'))) + 1:02d}"
        save(directory / "input.json", {"provided_system": system_prompt, "effective_system": effective,
            "user_text": user_text, "images": [{"path": str(p), "sha256": sha(p)} for p in image_paths]})
        result = self.client.predict_json(system_prompt=effective, user_text=user_text, image_paths=image_paths)
        save(directory / "response.json", result)
        return result


def ditto(job, directory, source, root, verified):
    sys.path.insert(0, str(root / "scripts/deploy"))
    from run_prompt_probe import inspect_video
    cfg = job["payload"]["renderer"]
    info = inspect_video(source)
    output = cfg["output"]
    frames, fps = output["frames"], output["fps"]
    indices = [round(i * info["fps"] / fps) for i in range(frames)]
    if not indices or indices[-1] >= info["frames"]:
        raise ValueError("Configured output would sample beyond the actual input; no tail padding is permitted")
    models = load(root / "configs/ditto_models.json")
    generation = cfg["generation"]
    case = {"case_id": "result", "source_video": str(source), "source_video_sha256": sha(source),
            "prompt": job["payload"]["prompt"], "conditioning_source_indices": indices,
            "fps": fps, "num_frames": frames, "delivery_frames": frames,
            "height": output["height"], "width": output["width"], "seed": cfg.get("seed", 42)}
    manifest = directory / "ditto" / "cases.json"
    spec = {"code_revision": models["code_revision"], "generation": generation, "cases": [case]}
    if manifest.exists() and load(manifest) != spec:
        raise ValueError("Saved renderer manifest differs")
    save(manifest, spec)
    command = [sys.executable, str(root / "scripts/deploy/run_ditto_prompt_probe.py"),
               "--manifest", str(manifest), "--verified-manifest", str(verified)]
    with (directory / "renderer.log").open("a", encoding="utf-8") as log:
        subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
    receipt = load(manifest.parent / "preflight.json")
    actual = load(manifest.parent / "result/input.json")
    result = load(manifest.parent / "result/result.json")
    video = manifest.parent / "result/native.mp4"
    return {"video": {"path": str(video), "sha256": sha(video)}, "execution": {
        "backend": "ditto", "requested_prompt": case["prompt"], "effective_prompt": actual["effective_text"],
        "input_sha256": case["source_video_sha256"], "conditioning_source_indices": indices,
        "input_fps": info["fps"], "output_fps": fps, "settings": generation, "seed": case["seed"],
        "model_revision": receipt["model_revisions"], "code_revision": receipt["code_revision"],
        "tokenizer_revision": models["models"][0]["revision"], "token_count": actual["token_count"],
        "token_limit": 512, "preflight": "passed", "prompt_transforms": [],
        "generation_seconds": result["elapsed_seconds"], "renderer_result": result}}


def evaluate(job, directory, root, model=None):
    import evaluation
    from evaluation.media import prepare
    from evaluation.judges import judge
    from evaluation.scoring import score
    from evaluation.protocol import validate_card
    from vlm.codex_vlm import CodexVisionModel
    p = job["payload"]
    cfg = p["evaluation"]
    card = validate_card(cfg.get("card_data") or load(root / cfg["card"]))
    if card["source_sha256"] != p["original"]["sha256"] or card["requirement"] != p["request"]:
        raise ValueError("Evaluation card does not match the original task")
    if sha(p["video"]["path"]) != p["video"]["sha256"]:
        raise ValueError("Evaluation video changed")
    if model is None:
        os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(directory / "evaluation-usage.jsonl")
    evidence = prepare(card, Path(p["video"]["path"]), directory / "evidence", root=root,
                       dense_ranges=cfg.get("dense_ranges", []), mapping=p["video"].get("time_mapping"))
    client = EnglishEvaluationClient(model or CodexVisionModel(role="online_feedback"), directory / "english-evaluation")
    judgment = judge(card, evidence, client, directory / "judge")
    return {"protocol": {"id": card["protocol"], "version": card["card_sha256"],
                         "implementation_sha256": {p.name: sha(p) for p in Path(evaluation.__file__).parent.glob("*.py")}},
            "language": "English evidence prose; scoring instructions unchanged; exact adapted inputs retained",
            "usage": "online_feedback; not an independent final evaluation", "question": p.get("question", ""),
            "judgment": judgment, "scores": score(card, judgment), "evidence_path": str(directory / "evidence")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--response", type=Path)
    parser.add_argument("--input-video", type=Path, help="Transferred conditioning video; its hash must match")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--verified-manifest", type=Path)
    parser.add_argument("--replay-video", type=Path)
    parser.add_argument("--provenance")
    args = parser.parse_args()
    request = args.request.resolve()
    response_path = args.response.resolve() if args.response else request.with_name("response.json")
    job = load(request)
    body = {k: v for k, v in job.items() if k != "sha256"}
    if signature(body) != job["sha256"]:
        raise ValueError("Request signature mismatch")
    with RunLock(request.parent / "worker"):
        if response_path.exists():
            prior = load(response_path)
            if prior["request_sha256"] != job["sha256"]:
                raise ValueError("Existing response belongs to another request")
            print(json.dumps({"status": prior["status"], "reused": True}))
            return
        response = {"request_sha256": job["sha256"], "mode": job["mode"], "status": "complete"}
        try:
            if job["kind"] == "generate":
                p = job["payload"]
                source = args.input_video.resolve() if args.input_video else Path(p["input"]["path"])
                if sha(source) != p["input"]["sha256"]:
                    raise ValueError("Transferred conditioning video hash mismatch")
                if job["mode"] == "replay":
                    if not args.replay_video or not args.provenance:
                        raise ValueError("Replay requires an explicit archived video and provenance")
                    video = args.replay_video.resolve()
                    response["payload"] = {"video": {"path": str(video), "sha256": sha(video)},
                        "replay_provenance": args.provenance,
                        "execution": {"backend": "replay", "requested_prompt": p["prompt"], "effective_prompt": p["prompt"],
                                      "input_sha256": p["input"]["sha256"], "preflight": "not_run"}}
                elif p["renderer"].get("backend") == "ditto":
                    if not args.verified_manifest:
                        raise ValueError("Ditto needs the deployment's verified model manifest")
                    response["payload"] = ditto(job, request.parent, source, args.root.resolve(), args.verified_manifest.resolve())
                else:
                    raise ValueError("No worker for this renderer; configure the pinned Ditto deployment")
            elif job["kind"] == "evaluate":
                response["payload"] = evaluate(job, request.parent, args.root.resolve())
            elif job["kind"] == "critique":
                from critic_harness.adapter import critique
                response["payload"] = critique(job, request.parent, args.root.resolve())
            else:
                raise ValueError("Unknown tool job")
        except Exception as exc:
            response.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        save(response_path, response)
        print(json.dumps({"status": response["status"], "response": str(response_path), "error": response.get("error")}))


if __name__ == "__main__":
    main()
