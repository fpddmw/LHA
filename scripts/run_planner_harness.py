"""Run a model-led planning task or a continuous tool-using video task."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source")
    parser.add_argument("--request")
    parser.add_argument("--request-file")
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=["codex", "litellm"], default="codex")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--reasoning", default="xhigh")
    parser.add_argument("--target", default="unspecified")
    parser.add_argument("--mode", choices=["plan", "loop"], default="plan")
    parser.add_argument("--execution-config")
    parser.add_argument("--import-videos", help="JSON list of existing videos with truthful provenance")
    parser.add_argument("--max-generations", type=int, default=3)
    parser.add_argument("--label", default="")
    parser.add_argument("--max-turns", type=int, default=24)
    parser.add_argument("--max-context-chars", type=int, default=180000)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--additional-turns", type=int, default=0)
    parser.add_argument("--worker-command", nargs=argparse.REMAINDER,
                        help="Optional worker argv, last on the command line. {request} and {response} are substituted without a shell.")
    args = parser.parse_args()
    if not args.resume and (not args.source or not (args.request or args.request_file)):
        parser.error("A new run requires --source and --request or --request-file")
    from planner_harness import PlannerHarness
    from planner_harness.lock import RunLock
    if args.backend == "codex":
        os.environ["LOW_HIGH_AGENT_CODEX_PLANNER_MODEL"] = args.model
        os.environ["LOW_HIGH_AGENT_CODEX_PLANNER_REASONING_EFFORT"] = args.reasoning
        from vlm.codex_vlm import CodexVisionModel
        model = CodexVisionModel(role="planner")
    else:
        from vlm.litellm_vlm import LiteLLMVisionModel
        model = LiteLLMVisionModel(model=args.model, reasoning_effort=args.reasoning, role="planner")
    output = Path(args.output).resolve()
    os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(output / "model-usage.jsonl")
    with RunLock(output):
        harness = PlannerHarness(output, model)
        import json
        execution = json.loads(Path(args.execution_config).read_text(encoding="utf-8")) if args.execution_config else None
        if args.resume:
            state = harness.resume(additional_turns=args.additional_turns, execution=execution)
        else:
            request = Path(args.request_file).read_text(encoding="utf-8") if args.request_file else args.request
            imported = json.loads(Path(args.import_videos).read_text(encoding="utf-8")) if args.import_videos else None
            state = harness.start(args.source, request, target=args.target, label=args.label, max_turns=args.max_turns,
                                  max_context_chars=args.max_context_chars, mode=args.mode, execution=execution,
                                  max_generations=args.max_generations, imported=imported)
        while state["status"] == "waiting_tool" and args.worker_command:
            job = output / "jobs" / state["pending_tool"]
            substitutions = {"{request}": str(job / "request.json"), "{response}": str(job / "response.json")}
            command = list(args.worker_command)
            for marker, value in substitutions.items():
                command = [part.replace(marker, value) for part in command]
            subprocess.run(command, check=True)
            if not (job / "response.json").exists():
                # A dispatch-only worker leaves a durable pending task. It does not trigger model polling.
                break
            state = harness.resume()
    print(f"Planner status: {state['status']}; report: {output / 'report.html'}", flush=True)
    return 0 if state["status"] in {"complete", "waiting_tool"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
