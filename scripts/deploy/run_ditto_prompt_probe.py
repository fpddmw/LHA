"""Run full-length saved prompts through pinned official Ditto with the global LoRA."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from run_prompt_probe import digest, inspect_video, save

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--verified-manifest", type=Path, required=True)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    models = json.loads((ROOT / "configs/ditto_models.json").read_text(encoding="utf-8"))
    verified = json.loads(args.verified_manifest.read_text(encoding="utf-8"))
    assert verified["status"] == "complete"
    assert len(verified["files"]) == sum(len(m["files"]) for m in models["models"])
    for entry in verified["files"]:
        assert Path(entry["path"]).stat().st_size == entry["bytes"], entry["path"]
    code = ROOT / "third_party/Ditto-official"
    revision = subprocess.check_output(["git", "-C", str(code), "rev-parse", "HEAD"], text=True).strip()
    assert revision == models["code_revision"] == spec["code_revision"]
    cases = [c for c in spec["cases"] if not args.only or c["case_id"] in args.only]
    if args.only and set(args.only) - {c["case_id"] for c in cases}:
        raise ValueError("Unknown case IDs")
    assert cases
    for case in cases:
        assert digest(ROOT / case["source_video"]) == case["source_video_sha256"]
        assert len(case["conditioning_source_indices"]) == case["num_frames"]
        assert case["height"] % 16 == 0 and case["width"] % 16 == 0

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(code))
    import torch
    from transformers import AutoTokenizer
    from diffsynth import save_video, VideoData
    from diffsynth.pipelines.wan_video_new import WanVideoPipeline, ModelConfig

    base = ROOT / "models/Wan2.1-VACE-14B"
    tokenizer = AutoTokenizer.from_pretrained(str(base / "google/umt5-xxl"), local_files_only=True)
    prepared = []
    for case in cases:
        count = len(tokenizer(case["prompt"], truncation=False, add_special_tokens=True)["input_ids"])
        if count > 512:
            raise ValueError(f"Prompt exceeds text encoder limit: {case['case_id']}")
        prepared.append({**case, "token_count": count,
                         "token_count_scope": "raw prompt with official local UMT5 tokenizer",
                         "system_prompt": "", "effective_text": case["prompt"]})
    preflight = {"manifest_sha256": digest(manifest), "code_revision": revision,
                 "model_revisions": [{"repo_id": m["repo_id"], "revision": m["revision"]} for m in models["models"]],
                 "torch": torch.__version__, "cuda": torch.version.cuda,
                 "gpu": torch.cuda.get_device_name(0), "generation": spec["generation"], "cases": prepared}
    save(manifest.parent / "preflight.json", preflight)
    print(json.dumps({"stage": "preflight", "gpu": preflight["gpu"],
                      "tokens": {c["case_id"]: c["token_count"] for c in prepared}}), flush=True)
    if args.preflight_only:
        return
    pipe = None
    g = spec["generation"]
    for case in prepared:
        directory = manifest.parent / case["case_id"]
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / "edited.mp4"
        native = directory / "native.mp4"
        result_path = directory / "result.json"
        signature = hashlib.sha256(json.dumps({"case": case, "generation": g, "code_revision": revision,
                                    "model_revisions": preflight["model_revisions"]}, sort_keys=True).encode()).hexdigest()
        if result_path.exists():
            prior = json.loads(result_path.read_text(encoding="utf-8"))
            assert prior["signature"] == signature, "Existing case uses different settings"
            if prior["status"] == "complete":
                assert digest(output) == prior["output_sha256"]
                print(json.dumps({"stage": "reuse", "case_id": case["case_id"]}), flush=True)
                continue
        started = time.time()
        result = {"case_id": case["case_id"], "signature": signature, "status": "running",
                  "started_unix": started, "stage": "loading" if pipe is None else "conditioning"}
        save(directory / "input.json", case)
        save(result_path, result)
        try:
            if pipe is None:
                shards = sorted(str(p) for p in base.glob("diffusion_pytorch_model-*.safetensors"))
                assert len(shards) == 7
                pipe = WanVideoPipeline.from_pretrained(
                    torch_dtype=torch.bfloat16, device="cuda",
                    model_configs=[ModelConfig(path=shards, offload_device="cpu"),
                                   ModelConfig(path=str(base / "models_t5_umt5-xxl-enc-bf16.pth"), offload_device="cpu"),
                                   ModelConfig(path=str(base / "Wan2.1_VAE.pth"), offload_device="cpu")],
                    tokenizer_config=ModelConfig(path=str(base / "google/umt5-xxl")), redirect_common_files=False)
                assert pipe.dit is not None and pipe.vace is not None
                with redirect_stdout(io.StringIO()) as lora_log:
                    pipe.load_lora(pipe.vace, str(ROOT / "models/Ditto_models/models/ditto_global.safetensors"), alpha=g["lora_alpha"])
                print(lora_log.getvalue(), flush=True)
                matched = re.search(r"(\d+) tensors are updated by LoRA", lora_log.getvalue())
                assert matched and int(matched.group(1)) == 80
                pipe.enable_vram_management()
                save(manifest.parent / "model-load.json", {"status": "complete", "lora_updated_tensors": 80,
                                                          "elapsed_seconds": time.time()-started})
            source = VideoData(str(ROOT / case["source_video"]), height=case["height"], width=case["width"])
            condition = [source[i] for i in case["conditioning_source_indices"]]
            torch.cuda.reset_peak_memory_stats()
            inference_started = time.time()
            result.update(stage="inference", inference_started_unix=inference_started)
            save(result_path, result)
            print(json.dumps({"stage": "start", "case_id": case["case_id"], "frames": len(condition),
                              "steps": g["num_inference_steps"], "size": [case["width"], case["height"]]}), flush=True)

            def progress(iterable, **kwargs):
                for index, timestep in enumerate(iterable):
                    yield timestep
                    save(directory / "progress.json", {"step": index+1, "total_steps": g["num_inference_steps"],
                         "elapsed_seconds": time.time()-inference_started, "updated_unix": time.time()})
                    if (index+1) % 5 == 0:
                        print(json.dumps({"case_id": case["case_id"], "step": index+1,
                                          "elapsed_seconds": time.time()-inference_started}), flush=True)

            frames = pipe(prompt=case["prompt"], negative_prompt=g["negative_prompt"], vace_video=condition,
                          vace_reference_image=None, height=case["height"], width=case["width"],
                          num_frames=case["num_frames"], num_inference_steps=g["num_inference_steps"],
                          cfg_scale=g["cfg_scale"], seed=case["seed"], tiled=True, progress_bar_cmd=progress)
            assert len(frames) == case["num_frames"]
            result.update(stage="saving")
            save(result_path, result)
            save_video(frames, str(native), fps=case["fps"], quality=5)
            native_info = inspect_video(native)
            assert native_info["frames"] == case["num_frames"] and abs(native_info["fps"]-case["fps"]) < .001
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(native), "-map", "0:v:0",
                            "-frames:v", str(case["delivery_frames"]), "-c:v", "copy", str(output)], check=True)
            delivery = inspect_video(output)
            assert delivery["frames"] == case["delivery_frames"]
            assert [delivery["width"], delivery["height"]] == [case["width"], case["height"]]
            result.update(status="complete", stage="complete", elapsed_seconds=time.time()-started,
                          native=native_info, delivery=delivery, output_sha256=digest(output),
                          peak_gpu_allocated_gb=torch.cuda.max_memory_allocated()/1e9)
            save(result_path, result)
            print(json.dumps(result), flush=True)
        except Exception as exc:
            result.update(status="failed", elapsed_seconds=time.time()-started, error=repr(exc))
            save(result_path, result)
            raise
    save(manifest.parent / "generation-complete.json", {"status": "complete", "case_ids": [c["case_id"] for c in prepared],
                                                       "finished_unix": time.time()})


if __name__ == "__main__":
    main()
