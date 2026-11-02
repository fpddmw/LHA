"""Offline memory/lineage analysis; optional control intents are never submitted."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.common import load, save
from planner_harness.lineage import analyze, control_plan
from planner_harness.working_memory import timeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--control-candidate")
    args = parser.parse_args()
    state = load(args.run / "state.json")
    save(args.output / "lineage-analysis.json", analyze(state))
    save(args.output / "memory-analysis.json", timeline(args.run, state))
    if args.control_candidate:
        save(args.output / "control-plan.json", control_plan(state, args.control_candidate))


if __name__ == "__main__":
    main()
