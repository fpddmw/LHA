"""Download the pinned Bernini-R checkpoint; interrupted downloads resume."""
from pathlib import Path
import json
import os
import time

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[2]
REPO = "ByteDance/Bernini-R-1.3B-Diffusers"
REVISION = "ff4c5d4d2d31365c2ffeb30e9753065ee18f58ce"

if __name__ == "__main__":
    destination = ROOT / "models" / "Bernini-R-1.3B-Diffusers"
    manifest_path = destination / "download-manifest.json"
    if manifest_path.exists():
        saved = json.loads(manifest_path.read_text())
        entries = [f for f in saved.get("files", []) if f["path"].endswith(".safetensors")]
        expected = {f"text_encoder/model-{i:05d}-of-00005.safetensors" for i in range(1, 6)}
        expected |= {f"transformer/diffusion_pytorch_model-{i:05d}-of-00002.safetensors" for i in range(1, 3)}
        expected.add("vae/diffusion_pytorch_model.safetensors")
        if (saved.get("repo_id") == REPO and saved.get("revision") == REVISION
                and {f["path"] for f in entries} == expected
                and all((destination / f["path"]).is_file() and (destination / f["path"]).stat().st_size == f["bytes"] for f in entries)):
            print("Pinned Bernini model is already present; no download needed.", flush=True)
            raise SystemExit(0)
    for attempt in range(3):
        try:
            snapshot_download(
                REPO, revision=REVISION, local_dir=destination,
                endpoint=os.environ.get("HF_ENDPOINT", "https://huggingface.co"),
                allow_patterns=["*.json", "tokenizer/*", "text_encoder/*", "transformer/*", "vae/*", "scheduler/*", "README.md"],
                max_workers=4,
            )
            break
        except Exception:
            if attempt == 2:
                raise
            print(f"Download interrupted; resuming from cache in 30 seconds (attempt {attempt + 2}/3)", flush=True)
            time.sleep(30)
    weights = list(destination.rglob("*.safetensors"))
    if len(weights) != 8:
        raise RuntimeError(f"Expected 8 weight shards, found {len(weights)}")
    manifest = {"repo_id": REPO, "revision": REVISION, "files": [
        {"path": str(p.relative_to(destination)), "bytes": p.stat().st_size}
        for p in sorted(weights)
    ]}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2), flush=True)
