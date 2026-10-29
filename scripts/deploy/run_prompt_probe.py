"""Run saved prompts directly through Bernini-R, without the LHA agent loop."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def inspect_video(path: Path) -> dict:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames,duration",
        "-of", "json", str(path),
    ], capture_output=True, text=True, check=True)
    stream = json.loads(result.stdout)["streams"][0]
    count = int(stream["nb_read_frames"])
    numerator, denominator = stream["avg_frame_rate"].split("/")
    fps = float(numerator) / float(denominator)
    return {"frames": count, "fps": fps, "seconds": count / fps,
            "width": stream["width"], "height": stream["height"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models/Bernini-R-1.3B-Diffusers")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--max-jobs", type=int, default=0)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    spec = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = [c for c in spec["cases"] if not args.only or c["case_id"] in args.only]
    if args.only and set(args.only) - {c["case_id"] for c in cases}:
        raise ValueError("Unknown case IDs")
    if args.max_jobs:
        cases = cases[:args.max_jobs]
    if not cases:
        raise ValueError("No cases selected")
    for case in cases:
        assert digest(ROOT / case["source_video"]) == case["source_video_sha256"], case["case_id"]

    sys.path.insert(0, str(ROOT / "third_party/Bernini"))
    import torch
    from transformers import AutoTokenizer
    from bernini.cli import add_common_args, build_pipeline, generation_kwargs, resolve_system_prompt
    from bernini.pipeline import _prompt_clean

    cli_parser = add_common_args(argparse.ArgumentParser())
    cli = cli_parser.parse_args([
        "--config", str(args.model_dir.resolve()), "--task_type", "v2v",
        "--guidance_mode", spec["generation"]["guidance_mode"],
        "--num_inference_steps", str(spec["generation"]["num_inference_steps"]),
        "--max_image_size", str(spec["generation"]["max_image_size"]),
        "--neg_prompt", spec["generation"]["negative_prompt"],
    ])
    tokenizer = AutoTokenizer.from_pretrained(str(args.model_dir), subfolder="tokenizer", local_files_only=True)
    prefix = resolve_system_prompt({"task_type": "v2v"}, cli)
    prepared = []
    for case in cases:
        effective = prefix + _prompt_clean(case["prompt"])
        tokens = tokenizer(effective, truncation=False, add_special_tokens=True)["input_ids"]
        if len(tokens) > 512:
            raise ValueError(f"{case['case_id']}: {len(tokens)} tokens would be truncated")
        prepared.append({**case, "system_prompt": prefix, "effective_text": effective,
                         "token_count": len(tokens)})
    preflight = {"manifest_sha256": digest(manifest_path), "model_config_sha256": digest(args.model_dir / "config.json"),
                 "torch": torch.__version__, "cuda": torch.version.cuda,
                 "gpu": torch.cuda.get_device_name(0), "cases": prepared,
                 "generation": spec["generation"]}
    save(manifest_path.parent / "preflight.json", preflight)
    print(json.dumps({"stage": "preflight", "gpu": preflight["gpu"],
                      "tokens": {c["case_id"]: c["token_count"] for c in prepared}}), flush=True)
    if args.preflight_only:
        return

    pipeline = None
    for case in prepared:
        case_dir = manifest_path.parent / case["case_id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        native = case_dir / "native.mp4"
        output = case_dir / "edited.mp4"
        result_path = case_dir / "result.json"
        signature = hashlib.sha256(json.dumps({"case": case, "generation": spec["generation"],
                       "model_config_sha256": preflight["model_config_sha256"]}, sort_keys=True).encode()).hexdigest()
        if result_path.exists():
            previous = json.loads(result_path.read_text())
            if previous.get("signature") != signature:
                raise ValueError(f"Existing result uses different inputs: {case_dir}")
            if previous.get("status") == "complete" and output.exists():
                assert digest(output) == previous["output_sha256"]
                print(json.dumps({"stage": "reuse", "case_id": case["case_id"]}), flush=True)
                continue
        if pipeline is None:
            torch.cuda.set_device(0)
            pipeline = build_pipeline(cli, torch.device("cuda:0"))
        started = time.time()
        save(case_dir / "input.json", case)
        result = {"case_id": case["case_id"], "signature": signature, "status": "running", "started_unix": started}
        save(result_path, result)
        print(json.dumps({"stage": "start", "case_id": case["case_id"]}), flush=True)
        try:
            options = generation_kwargs(cli)
            options.update(num_frames=case["num_frames"], fps=case["fps"], seed=case["seed"])
            pipeline(case["prompt"], video=str(ROOT / case["source_video"]),
                     output_path=str(native), system_prompt=prefix, **options)
            native_info = inspect_video(native)
            assert native_info["frames"] == case["num_frames"], native_info
            assert abs(native_info["fps"] - case["fps"]) < 0.001, native_info
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(native),
                            "-map", "0:v:0", "-frames:v", str(case["delivery_frames"]),
                            "-c:v", "copy", str(output)], check=True)
            output_info = inspect_video(output)
            assert output_info["frames"] == case["delivery_frames"], output_info
            result.update(status="complete", elapsed_seconds=time.time()-started,
                          native=native_info, delivery=output_info, output_sha256=digest(output))
            save(result_path, result)
            print(json.dumps(result), flush=True)
        except Exception as exc:
            result.update(status="failed", elapsed_seconds=time.time()-started, error=str(exc))
            save(result_path, result)
            raise


if __name__ == "__main__":
    main()
