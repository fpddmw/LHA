"""Recover one empty Planner cache from its original SSE, without API or rendering."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from planner_harness.subscription_recovery import recover_answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--event', required=True)
    parser.add_argument('--stream', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='Prepare cached answer and original queue; no dispatch')
    args = parser.parse_args()
    print(json.dumps(recover_answer(args.run, args.event, args.stream, execute=args.execute), indent=2))


if __name__ == '__main__':
    main()
