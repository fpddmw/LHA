"""Run an isolated online Critic review of existing videos. Never dispatch generation."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-turns", type=int, default=18)
    parser.add_argument("--additional-turns", type=int, default=0)
    args = parser.parse_args()
    from planner_harness.common import load
    from planner_harness.lock import RunLock
    from vlm.codex_vlm import CodexVisionModel
    from critic_harness import CriticHarness
    os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(args.output.resolve() / "usage.jsonl")
    with RunLock(args.output):
        harness = CriticHarness(args.output, CodexVisionModel(role="online_critic"))
        state = harness.resume(args.additional_turns) if args.resume else harness.start(load(args.spec), max_turns=args.max_turns)
    print(f"Critic status: {state['status']}; report: {args.output / 'report.html'}", flush=True)
    return 0 if state["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
