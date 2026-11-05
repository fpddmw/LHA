"""Summarize one explicit run/batch's saved model usage without API calls."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from planner_harness.usage_report import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.run.is_dir():
        parser.error("run must be an existing output directory")
    result = summarize(args.run)
    if args.output:
        from planner_harness.common import save
        save(args.output, result)
    print(json.dumps({"scope": result["scope"], "roles": result["roles"], "notes": result["notes"]}, indent=2))


if __name__ == "__main__":
    main()
