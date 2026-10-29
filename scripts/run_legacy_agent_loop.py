"""Historical outer-loop controller; renderer/evaluator adapters consume file jobs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Adopt completed planning and publish the first render request")
    init.add_argument("--planner-run", required=True)
    init.add_argument("--renderer-config", required=True)
    init.add_argument("--mode", choices=["live", "replay"], default="live")
    init.add_argument("--max-candidates", type=int, default=3)
    init.add_argument("--max-render-jobs", type=int)
    sub.add_parser("advance", help="Consume available responses; exit when waiting for external work")
    sub.add_parser("status", help="Read durable status without running models or adapters")
    reply = sub.add_parser("respond", help="Atomically publish an external adapter response")
    reply.add_argument("--file", required=True)
    retry = sub.add_parser("retry", help="Create a new job identity after an explicit adapter failure")
    retry.add_argument("--reason", required=True)
    revise = sub.add_parser("revise", help="Run or resume the pending child Planner, without rendering")
    revise.add_argument("--backend", choices=["codex", "litellm"], default="codex")
    revise.add_argument("--model", default="gpt-6.1-sol")
    revise.add_argument("--reasoning", default="xhigh")
    revise.add_argument("--additional-turns", type=int, default=0)
    args = parser.parse_args()
    from agent_loop import AgentLoop
    from agent_loop.core import publish_response
    from planner_harness.common import load
    loop = AgentLoop(args.run)
    if args.command == "init":
        state = loop.initialize(args.planner_run, load(args.renderer_config), mode=args.mode,
                                max_candidates=args.max_candidates, max_render_jobs=args.max_render_jobs)
    elif args.command == "advance":
        state = loop.advance()
    elif args.command == "retry":
        state = loop.retry(args.reason)
    elif args.command == "revise":
        if args.backend == "codex":
            os.environ["LOW_HIGH_AGENT_CODEX_PLANNER_MODEL"] = args.model
            os.environ["LOW_HIGH_AGENT_CODEX_PLANNER_REASONING_EFFORT"] = args.reasoning
            from vlm.codex_vlm import CodexVisionModel
            model = CodexVisionModel(role="planner")
        else:
            from vlm.litellm_vlm import LiteLLMVisionModel
            model = LiteLLMVisionModel(model=args.model, reasoning_effort=args.reasoning, role="planner")
        state = loop.revise(model, additional_turns=args.additional_turns)
    else:
        if args.command == "respond":
            publish_response(args.run, load(args.file))
        state = load(Path(args.run) / "state.json")
    print(json.dumps({"status": state["status"], "mode": state["mode"], "incumbent": state["incumbent"],
                      "pending_job": state.get("job", {}).get("id") if state.get("job") else None,
                      "report": str(loop.output / "report.md")}, indent=2))
    return 2 if state["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
