"""Inspect the current benchmark and a task without model or generation calls."""
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect(sample_id="012", root=ROOT):
    rows = json.loads((Path(root) / "benchmark_data/benchmark.json").read_text(encoding="utf-8"))
    case = next(row for row in rows if row["sample_id"] == sample_id)
    return {
        "benchmark_version": case["benchmark_version"],
        "source_videos": len(rows), "prompt_conditions": 2 * len(rows),
        "splits": dict(Counter(row["split"] for row in rows)),
        "case": {key: case[key] for key in (
            "sample_id", "split", "source_video", "prompt_short_zh", "instruction_zh",
            "prompt_short", "instruction", "prompt_short_file", "prompt_file")},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", default="012")
    args = parser.parse_args()
    print(json.dumps(inspect(args.sample), ensure_ascii=False, indent=2))
