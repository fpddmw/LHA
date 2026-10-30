"""Generate or check the reference table from the executable metric registry."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from evaluation.registry import markdown


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "docs/evaluation-metrics.md")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    expected = markdown()
    if args.check:
        if not args.out.exists() or args.out.read_text(encoding="utf-8") != expected:
            raise SystemExit("Metric documentation is stale; regenerate it from registry.py")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(expected, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
