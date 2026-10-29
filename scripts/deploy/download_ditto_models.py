"""Resume the explicitly pinned Ditto/Wan downloads and verify published hashes."""
import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from huggingface_hub import hf_hub_download


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--models-root", type=Path, default=Path(__file__).resolve().parents[2] / "models")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--placement-map", type=Path,
                        help="Optional mapping from model-folder/filename to its download directory")
    args = parser.parse_args()
    started = time.time()
    spec = json.loads(args.spec.read_text())
    placements = json.loads(args.placement_map.read_text()) if args.placement_map else {}
    args.models_root.mkdir(parents=True, exist_ok=True)

    def fetch(item):
        model, entry = item
        canonical = args.models_root / model["folder"] / entry["path"]
        folder = Path(placements.get(model["folder"] + "/" + entry["path"],
                                     str(args.models_root / model["folder"])))
        path = folder / entry["path"]
        expected = entry.get("sha256")
        if not (path.exists() and path.stat().st_size == entry["bytes"] and
                (not expected or sha256(path) == expected)):
            for attempt in range(3):
                try:
                    hf_hub_download(repo_id=model["repo_id"], filename=entry["path"],
                                    revision=model["revision"], local_dir=folder,
                                    endpoint=os.environ.get("HF_ENDPOINT", "https://huggingface.co"))
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(20)
        if path.stat().st_size != entry["bytes"]:
            raise RuntimeError(f"Size mismatch: {path}")
        actual = sha256(path)
        if expected and actual != expected:
            raise RuntimeError(f"Hash mismatch: {path}")
        if path.absolute() != canonical.absolute():
            canonical.parent.mkdir(parents=True, exist_ok=True)
            if canonical.is_symlink():
                if canonical.resolve() != path.resolve():
                    raise RuntimeError(f"Unexpected existing symlink: {canonical}")
            elif canonical.exists():
                raise RuntimeError(f"Refusing to replace existing file: {canonical}")
            else:
                canonical.symlink_to(path.absolute())
        result = {"repo_id": model["repo_id"], "revision": model["revision"],
                  "path": str(canonical.absolute()), "storage_path": str(path.absolute()),
                  "bytes": path.stat().st_size, "sha256": actual,
                  "published_sha256_matched": bool(expected), "verified_unix": time.time()}
        print(json.dumps({"verified": result}), flush=True)
        return result

    work = [(m, e) for m in spec["models"] for e in m["files"]]
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(fetch, work))
    manifest = args.spec.parent / "ditto-models-verified.json"
    manifest.write_text(json.dumps({"status": "complete", "files": results,
                                   "started_unix": started, "finished_unix": time.time(),
                                   "elapsed_seconds": time.time() - started}, indent=2) + "\n")
    print(json.dumps({"status": "complete", "manifest": str(manifest)}), flush=True)


if __name__ == "__main__":
    main()
