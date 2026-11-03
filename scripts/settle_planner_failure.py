"""Register a failed Planner loop's retained videos without external calls."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    from experiments.recovery import settle_planner_failure
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--device", required=True, help="Original worker directory ID")
    parser.add_argument("--method", choices=("full", "none"), default="full")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(settle_planner_failure(args.output, args.topic, args.device,
                     method=args.method, execute=args.execute), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
