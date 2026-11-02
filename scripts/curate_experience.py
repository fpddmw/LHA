"""Apply explicitly reviewed entry curation to a private library; no model calls."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='Existing batch/private-library directory')
    parser.add_argument('--decisions', required=True, type=Path, help='Explicit curation decisions JSON list')
    parser.add_argument('--expected-snapshot-sha256', required=True)
    parser.add_argument('--authorization', required=True, help='Reference to the explicit curation instruction/review')
    args = parser.parse_args()
    from planner_harness.common import load
    from planner_harness.training_experience import curate_library
    result = curate_library(ROOT, args.output, load(args.decisions), authorization=args.authorization,
                            expected_snapshot_sha256=args.expected_snapshot_sha256)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
