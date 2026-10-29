"""Fingerprint existing Bernini assets without downloading, loading CUDA or starting tasks."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from evaluation.protocol import file_hash
from planner_harness.execution import immutable


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--model-dir", default="models/Bernini-R-1.3B-Diffusers")
    p.add_argument("--code-dir", default="third_party/Bernini")
    p.add_argument("--model-revision", required=True, help="Revision recorded by the existing verified deployment")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    model, code = root / args.model_dir, root / args.code_dir
    if not (model / "config.json").is_file() or not (code / "bernini/pipeline.py").is_file():
        raise ValueError("Expected the existing Bernini model and source directories")
    revision = subprocess.check_output(["git", "-C", str(code), "rev-parse", "HEAD"], text=True).strip()
    files = [p for p in model.rglob("*") if p.is_file() and not any(x.startswith(".") for x in p.relative_to(model).parts)]
    files += list(code.rglob("*.py"))
    rows = [{"path": str(p.relative_to(root)).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": file_hash(p)} for p in sorted(files)]
    immutable(args.output, {"model_dir": args.model_dir, "code_dir": args.code_dir,
        "model_revision": args.model_revision, "code_revision": revision, "files": rows,
        "provenance": "Actual installed bytes; model revision is operator-supplied deployment provenance, not independently fetched here."})
    print(file_hash(args.output))


if __name__ == "__main__":
    main()
