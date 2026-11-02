"""Propose experience revisions; shared publication is a separate explicit command."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.experience import propose, publish, rollback_proposal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("propose"); p.add_argument("--topic", required=True); p.add_argument("--runs", nargs="+", required=True); p.add_argument("--output", required=True)
    p = sub.add_parser("publish"); p.add_argument("--proposal", required=True); p.add_argument("--reviewed-by", required=True)
    p = sub.add_parser("rollback-proposal"); p.add_argument("--topic", required=True); p.add_argument("--previous-hash", required=True); p.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "propose":
        from vlm.openrouter import OpenRouterVisionModel
        os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(Path(args.output).resolve() / "model-usage.jsonl")
        result = propose(args.topic, args.runs, args.output, OpenRouterVisionModel(role="experience"))
    elif args.command == "publish":
        result = publish(args.proposal, args.reviewed_by)
    else:
        result = rollback_proposal(args.topic, args.previous_hash, args.output)
    print(json.dumps({k:v for k,v in result.items() if k != "proposed_text"}, indent=2))


if __name__ == "__main__":
    main()
