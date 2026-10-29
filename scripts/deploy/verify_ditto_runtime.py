"""Check the full Ditto model with a tiny forward pass, not a quality experiment."""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads((ROOT / "configs/ditto_models.json").read_text())
    verified = json.loads(args.verified_manifest.read_text())
    assert verified["status"] == "complete"
    expected = sum(len(model["files"]) for model in spec["models"])
    assert len(verified["files"]) == expected
    for entry in verified["files"]:
        assert Path(entry["path"]).stat().st_size == entry["bytes"]
    code = ROOT / "third_party/Ditto-official"
    revision = subprocess.check_output(["git", "-C", str(code), "rev-parse", "HEAD"], text=True).strip()
    assert revision == spec["code_revision"]
    sys.path.insert(0, str(code))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from diffsynth import save_video, VideoData
    from diffsynth.pipelines.wan_video_new import WanVideoPipeline, ModelConfig

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"purpose": "Runtime smoke only; 13 frames and 2 steps cannot assess editing quality",
              "status": "running", "code_revision": revision,
              "torch": torch.__version__, "cuda": torch.version.cuda,
              "gpu": torch.cuda.get_device_name(0), "frames": 13,
              "steps": 2, "height": 256, "width": 448, "seed": 42,
              "cfg_scale": 5.0, "lora_alpha": 1.0, "negative_prompt": ""}
    report_path = args.output_dir / "runtime-check.json"
    report_path.write_text(json.dumps(report, indent=2))
    started = time.time()
    base = ROOT / "models/Wan2.1-VACE-14B"
    shards = sorted(str(p) for p in base.glob("diffusion_pytorch_model-*.safetensors"))
    assert len(shards) == 7
    try:
        pipe = WanVideoPipeline.from_pretrained(
            torch_dtype=torch.bfloat16, device="cuda",
            model_configs=[
                ModelConfig(path=shards, offload_device="cpu"),
                ModelConfig(path=str(base / "models_t5_umt5-xxl-enc-bf16.pth"), offload_device="cpu"),
                ModelConfig(path=str(base / "Wan2.1_VAE.pth"), offload_device="cpu"),
            ],
            tokenizer_config=ModelConfig(path=str(base / "google/umt5-xxl")),
            redirect_common_files=False,
        )
        assert pipe.dit is not None and pipe.vace is not None and pipe.vae is not None
        lora = ROOT / "models/Ditto_models/models/ditto_global.safetensors"
        with redirect_stdout(io.StringIO()) as lora_log:
            pipe.load_lora(pipe.vace, str(lora), alpha=1.0)
        print(lora_log.getvalue(), flush=True)
        count = re.search(r"(\d+) tensors are updated by LoRA", lora_log.getvalue())
        assert count and int(count.group(1)) > 0, "No LoRA tensors were applied"
        report["lora_updated_tensors"] = int(count.group(1))
        pipe.enable_vram_management()
        report["load_seconds"] = time.time() - started
        report_path.write_text(json.dumps(report, indent=2))
        source = VideoData(str(ROOT / "benchmark_data/main/027/027.mp4"), height=256, width=448)
        frames = pipe(prompt="Make it look like a 19th-century etching.", negative_prompt="",
                      vace_video=[source[i] for i in range(13)], vace_reference_image=None,
                      num_frames=13, height=256, width=448, num_inference_steps=2,
                      cfg_scale=5.0, seed=42, tiled=True)
        assert len(frames) == 13
        video_path = args.output_dir / "smoke-not-for-quality.mp4"
        save_video(frames, str(video_path), fps=20, quality=5)
        from run_prompt_probe import inspect_video, digest
        output = inspect_video(video_path)
        assert output["frames"] == 13 and output["width"] == 448 and output["height"] == 256
        report.update(status="complete", elapsed_seconds=time.time()-started,
                      output=output, output_sha256=digest(video_path),
                      peak_gpu_allocated_gb=torch.cuda.max_memory_allocated()/1e9)
    except Exception as exc:
        report.update(status="failed", elapsed_seconds=time.time()-started, error=repr(exc))
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
