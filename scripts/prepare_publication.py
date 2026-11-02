"""Make a reviewable source-only ZIP from the worktree, preserving Git history.

No upload, history rewrite, removal, or claim of media redistribution permission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MEDIA = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".wav", ".mp3", ".safetensors", ".ckpt", ".pt", ".pth"}


def reason(name):
    path = Path(name)
    if path.suffix.lower() in MEDIA:
        return "media_or_weights_redistribution_unverified"
    if any(p in {".git", "out", "node_modules", "__pycache__", ".venv", "venv"} for p in path.parts):
        return "local_runtime_or_history"
    if path.name.startswith(".env") or path.name in {"auth.json", "credentials.json"} or path.suffix.lower() in {".pem", ".key", ".p12"}:
        return "private_configuration"
    return None


def prepare(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.suffix.lower() != ".zip" or output.exists() or output.is_relative_to(root / ".git"):
        raise ValueError("Choose a new ZIP path outside Git metadata; existing files are never replaced")
    files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
    included, excluded = [], []
    for name in sorted(set(filter(None, files))):
        path = root / name
        why = reason(name)
        if why:
            excluded.append({"path": name, "reason": why})
        elif path.is_symlink():
            excluded.append({"path": name, "reason": "symlink_requires_review"})
        elif path.is_file():
            if not path.resolve().is_relative_to(root):
                raise ValueError("Publication path escapes the repository")
            included.append((name, path))
    manifest = {"schema": "lha-source-publication-v1", "git_history_included": False,
        "media_license_status": "unverified; excluded", "original_media_recovery": "Original repository Git objects remain unchanged",
        "included": [], "excluded": excluded}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".partial", delete=False) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, path in included:
                data = path.read_bytes()
                archive.writestr(name, data)
                manifest["included"].append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
            archive.writestr("PUBLICATION-MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("Publication ZIP integrity check failed")
            for item in manifest["included"]:
                if hashlib.sha256(archive.read(item["path"])).hexdigest() != item["sha256"]:
                    raise ValueError("Publication file hash mismatch")
        # Reserve the final name atomically, so even a competing creator is safe.
        with output.open("xb") as target, temporary.open("rb") as source:
            import shutil
            shutil.copyfileobj(source, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"output": str(output), "included": len(included), "excluded": len(excluded),
            "git_history_modified": False, "media_license_status": "unverified"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(ROOT, args.output), ensure_ascii=False))
