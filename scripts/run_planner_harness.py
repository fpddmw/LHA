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
    parser.add_argument("--run-instructions-file", help="Optional operator instructions, separate from the original video requirement")
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=["codex", "litellm"], default="codex")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--reasoning", default=None)
    parser.add_argument("--workflow", choices=["legacy", "creative_loop_v1"], default=None)
    parser.add_argument("--profile", type=Path, help="Creative role/default configuration JSON")
    parser.add_argument("--experiment-profile", type=Path, help="Optional shared frozen cohort profile")
    parser.add_argument("--target", default="unspecified")
    parser.add_argument("--mode", choices=["plan", "loop"], default="plan")
    parser.add_argument("--execution-config")
    parser.add_argument("--rsi", action="store_true", help="Enable requirement-linked task learning and automatic Critic")
    parser.add_argument("--rsi-config", help="Optional JSON RSI configuration, including candidate experience and fixed seeds")
    parser.add_argument("--task-card", help="Reviewed independent v2 task card; required for new live RSI runs")
    parser.add_argument("--import-videos", help="JSON list of existing videos with truthful provenance")
    parser.add_argument("--critic-feedback", action="append", default=[], help="Verified online Critic feedback JSON to import")
    parser.add_argument("--max-generations", type=int, default=None, help="Optional explicit generation limit; omitted means no fixed generation count")
    parser.add_argument("--completion-mode", choices=["delivery", "bounded_experiment"], default="delivery")
    parser.add_argument("--label", default="")
    parser.add_argument("--max-turns", type=int, default=None, help="Optional safety ceiling; delivery runs otherwise have no fixed turn count")
    parser.add_argument("--max-context-chars", type=int, default=None, help="New capacity or explicit resume capacity; default 180000 for new runs")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--continue-delivery", action="store_true", help="Explicitly reopen a resolved budget stop; preserve evidence and frozen Critic while removing the count ceiling")
    parser.add_argument("--additional-turns", type=int, default=0)
    parser.add_argument("--worker-command", nargs=argparse.REMAINDER,
                        help="Optional worker argv, last on the command line. {request} and {response} are substituted without a shell.")
    args = parser.parse_args()
    import json
    profile = json.loads(args.profile.read_text(encoding="utf-8")) if args.profile else {}
    if profile:
        if profile.get("workflow") != "creative_loop_v1" or (args.workflow and args.workflow != profile["workflow"]):
            parser.error("Profile must identify the selected creative workflow")
        args.workflow = profile["workflow"]
        if not args.resume:
            if args.max_generations is None:
                args.max_generations = profile.get("max_generations")
            if args.max_turns is None:
                args.max_turns = profile.get("max_turns")
    if args.resume:
        import json
        recorded = json.loads((Path(args.output) / "state.json").read_text(encoding="utf-8"))["config"]
        if args.workflow and args.workflow != recorded.get("workflow", "legacy"):
            parser.error("Resume must retain the recorded workflow")
        args.workflow = recorded.get("workflow", "legacy")
        args.reasoning = args.reasoning or recorded["reasoning_effort"]
    args.workflow = args.workflow or "legacy"
    args.reasoning = args.reasoning or ("high" if args.workflow == "creative_loop_v1" else "xhigh")
    if args.workflow == "creative_loop_v1":
        from planner_harness.creative import role_settings
        settings = role_settings(profile, "planner")
        role_settings(profile, "online_critic")
        if args.model != settings["model"] or args.reasoning != settings["reasoning_effort"]:
            parser.error("Creative roles are fixed to gpt-6.1-sol/high")
    if args.workflow == "creative_loop_v1" and (args.rsi or args.rsi_config or args.task_card or args.critic_feedback):
        parser.error("Creative loop excludes RSI, task cards and imported legacy feedback")
    if args.continue_delivery and not args.resume:
        parser.error("--continue-delivery requires --resume")
    if not args.resume and (not args.source or not (args.request or args.request_file)):
        parser.error("A new run requires --source and --request or --request-file")
    from planner_harness import PlannerHarness
    from planner_harness.lock import RunLock
    if args.backend == "codex":
        os.environ["LOW_HIGH_AGENT_CODEX_PLANNER_MODEL"] = args.model
        os.environ["LOW_HIGH_AGENT_CODEX_PLANNER_REASONING_EFFORT"] = args.reasoning
        from vlm.codex_vlm import CodexVisionModel
        model = CodexVisionModel(role="planner", model=args.model, reasoning_effort=args.reasoning)
    else:
        from vlm.litellm_vlm import LiteLLMVisionModel
        model = LiteLLMVisionModel(model=args.model, reasoning_effort=args.reasoning, role="planner")
    output = Path(args.output).resolve()
    os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(output / "model-usage.jsonl")
    with RunLock(output):
        harness = PlannerHarness(output, model)
        import json
        execution = json.loads(Path(args.execution_config).read_text(encoding="utf-8")) if args.execution_config else None
        if not args.resume and args.workflow=='creative_loop_v1' and profile.get('continuation_policy'):
            execution = dict(execution or {})
            execution.setdefault('continuation_policy', profile['continuation_policy'])
        if args.experiment_profile and not args.resume:
            execution = {**(execution or {}), "experiment_profile": str(args.experiment_profile.resolve())}
        elif args.experiment_profile:
            from planner_harness.creative import verify_experiment
            verify_experiment(args.experiment_profile, ROOT)
            if recorded["execution"].get("experiment_profile") != str(args.experiment_profile.resolve()):
                parser.error("Resume must use its recorded shared profile")
        if args.resume:
            state = harness.resume(additional_turns=args.additional_turns, execution=execution, continue_delivery=args.continue_delivery,
                                   max_context_chars=args.max_context_chars)
        else:
            request = Path(args.request_file).read_text(encoding="utf-8") if args.request_file else args.request
            rsi = json.loads(Path(args.rsi_config).read_text(encoding="utf-8")) if args.rsi_config else {} if args.rsi or args.task_card else None
            if args.task_card:
                rsi["task_card"] = str(Path(args.task_card).resolve())
            imported = json.loads(Path(args.import_videos).read_text(encoding="utf-8")) if args.import_videos else None
            state = harness.start(args.source, request, target=args.target, label=args.label, max_turns=args.max_turns,
                                  max_context_chars=args.max_context_chars or profile.get("max_context_chars", 180000), mode=args.mode, execution=execution,
                                  max_generations=args.max_generations, completion_mode=args.completion_mode,
                                  imported=imported, feedback_files=args.critic_feedback,
                                  rsi=rsi, workflow=args.workflow,
                                  run_instructions=Path(args.run_instructions_file).read_text(encoding="utf-8") if args.run_instructions_file else "")
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
