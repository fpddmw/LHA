"""Run a model-led planning task or a continuous tool-using video task."""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def creative_configuration(args, profile, execution, recorded, parser):
    """Resolve new-task overrides or retain the exact saved client on resume."""
    from vlm.settings import role_settings

    declared_factory = (execution or {}).get("models", {}).get("planner", {}).get("factory")
    if recorded is not None:
        saved = recorded["execution"]
        if execution is not None and execution != saved:
            parser.error("Resume retains the recorded execution configuration")
        execution = copy.deepcopy(saved)
        for field in ("model", "reasoning_effort"):
            supplied = args.model if field == "model" else args.reasoning
            if supplied is not None and supplied != recorded[field]:
                parser.error("Resume retains the recorded " + field)
        if args.review_mode and args.review_mode != saved.get("review", {}).get("mode", "critic"):
            parser.error("Resume retains its original review mode")
        count = recorded.get("resource_policy", {}).get("max_generations", recorded.get("max_generations"))
        if args.max_generations is not None and args.max_generations != count:
            parser.error("Resume retains its recorded generation limit")
        # A profile may confirm a resume, but cannot silently switch its client.
        for role in ("planner", "online_critic"):
            proposed = profile.get("models", {}).get(role, {})
            original = saved.get("models", {}).get(role, {})
            if proposed.get("factory", original.get("factory")) != original.get("factory"):
                parser.error("Resume retains its recorded model factory")
            if any(original.get("options", {}).get(k) != v for k, v in proposed.get("options", {}).items()):
                parser.error("Resume retains its recorded model options")
        execution.setdefault("models", {}).setdefault("planner", {}).setdefault("options", {}).update(
            model=recorded["model"], reasoning_effort=recorded["reasoning_effort"]
        )
    else:
        supplied = copy.deepcopy(execution or {})
        execution = copy.deepcopy(supplied)
        for field in ("review", "planner", "critic", "resource_policy", "continuation_policy",
                      "credential_file", "llm_timeout_seconds"):
            if field in profile:
                execution.setdefault(field, copy.deepcopy(profile[field]))
        roles = copy.deepcopy(profile.get("models", {}))
        for role, spec in supplied.get("models", {}).items():
            default = roles.get(role, {})
            roles[role] = {**default, **spec, "options": {**default.get("options", {}), **spec.get("options", {})}}
        execution["models"] = roles
        if args.review_mode:
            execution["review"] = {"mode": args.review_mode}
        execution.setdefault("review", {"mode": "critic"})
        if args.max_generations is not None:
            execution.setdefault("resource_policy", {})["max_generations"] = args.max_generations
            execution.setdefault("continuation_policy", {})["hard_generation_limit"] = args.max_generations
        else:
            args.max_generations = supplied.get("resource_policy", {}).get("max_generations", profile.get("max_generations"))

    spec = execution.setdefault("models", {}).setdefault("planner", {})
    if args.backend:
        factory = {"openrouter": "vlm.openrouter:OpenRouterVisionModel", "litellm": "vlm.litellm_vlm:LiteLLMVisionModel"}[args.backend]
        explicit = recorded is not None or args.profile is not None or declared_factory is not None
        if explicit and spec.get("factory", factory) != factory:
            parser.error("--backend conflicts with the configured model factory; use the matching profile")
        spec["factory"] = factory
    spec.setdefault("factory", "vlm.openrouter:OpenRouterVisionModel")
    options = spec.setdefault("options", {})
    if args.model is not None:
        options["model"] = args.model
    if args.reasoning is not None:
        options["reasoning_effort"] = args.reasoning
    resolved = role_settings(execution, "planner")
    options.update(resolved)
    execution["planner"] = resolved
    role_settings(execution, "online_critic")
    args.model, args.reasoning = resolved["model"], resolved["reasoning_effort"]
    return execution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source")
    parser.add_argument("--request")
    parser.add_argument("--request-file")
    parser.add_argument("--run-instructions-file", help="Optional operator instructions, separate from the original video requirement")
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=["openrouter", "litellm"], help="Optional client choice; must agree with an explicit profile or saved run")
    parser.add_argument("--model", default=None)
    parser.add_argument("--reasoning", default=None)
    parser.add_argument("--workflow", choices=["legacy", "creative_loop_v1"], default=None, help="New tasks default to creative_loop_v1; legacy is explicit, resumes retain their workflow")
    parser.add_argument("--profile", type=Path, help="Creative role/default configuration JSON")
    parser.add_argument("--review-mode", choices=["critic", "planner"], help="Reviewer after every successful generation")
    parser.add_argument("--experiment-profile", type=Path, help="Optional shared frozen cohort profile")
    parser.add_argument("--target", default="unspecified")
    parser.add_argument("--mode", choices=["plan", "loop"], help="Creative tasks use loop; explicit legacy tasks default to plan")
    parser.add_argument("--execution-config")
    parser.add_argument("--rsi", action="store_true", help="Enable requirement-linked task learning and automatic Critic")
    parser.add_argument("--rsi-config", help="Optional JSON RSI configuration, including candidate experience and fixed seeds")
    parser.add_argument("--task-card", help="Reviewed independent v2 task card; required for new live RSI runs")
    parser.add_argument("--import-videos", help="JSON list of existing videos with truthful provenance")
    parser.add_argument("--critic-feedback", action="append", default=[], help="Verified online Critic feedback JSON to import")
    parser.add_argument("--max-generations", type=int, default=None, help="New-task generation limit; overrides the profile consistently (current default: 4)")
    parser.add_argument("--completion-mode", choices=["delivery", "bounded_experiment"], default="delivery")
    parser.add_argument("--label", default="")
    parser.add_argument("--max-turns", type=int, default=None, help="Legacy turn limit; creative tasks use generation and time limits")
    parser.add_argument("--max-context-chars", type=int, default=None, help="New capacity or explicit resume capacity; default 180000 for new runs")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--continue-delivery", action="store_true", help="Continue an eligible stopped delivery with its recorded generation and time policy")
    parser.add_argument("--additional-turns", type=int, default=0)
    parser.add_argument("--worker-command", nargs=argparse.REMAINDER,
                        help="Optional worker argv, last on the command line. {request} and {response} are substituted without a shell.")
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8")) if args.profile else {}
    if profile:
        if profile.get("workflow") != "creative_loop_v1" or (args.workflow and args.workflow != profile["workflow"]):
            parser.error("Profile must identify the selected creative workflow")
        args.workflow = profile["workflow"]
    recorded = None
    if args.resume:
        recorded = json.loads((Path(args.output) / "state.json").read_text(encoding="utf-8"))["config"]
        if args.workflow and args.workflow != recorded.get("workflow", "legacy"):
            parser.error("Resume must retain the recorded workflow")
        args.workflow = recorded.get("workflow", "legacy")
    args.workflow = args.workflow or "creative_loop_v1"
    args.mode = args.mode or ("loop" if args.workflow == "creative_loop_v1" else "plan")
    execution = json.loads(Path(args.execution_config).read_text(encoding="utf-8")) if args.execution_config else None
    if args.workflow == "creative_loop_v1":
        if not args.resume and not args.profile:
            profile = json.loads((ROOT / "configs/creative-loop-v1.json").read_text(encoding="utf-8"))
        if args.mode != "loop":
            parser.error("Creative tasks use --mode loop; use --workflow legacy for proposal-only planning")
        if args.max_turns is not None:
            parser.error("Creative tasks use generation and time limits, not --max-turns")
        execution = creative_configuration(args, profile, execution, recorded, parser)
    elif recorded:
        args.reasoning = args.reasoning if args.reasoning is not None else recorded["reasoning_effort"]
        args.model = args.model or recorded["model"]
        args.backend = args.backend or ("litellm" if recorded.get("backend") == "LiteLLMVisionModel" else "openrouter")
    from vlm.openrouter import DEFAULT_MODEL
    args.model = args.model or DEFAULT_MODEL
    if args.workflow != 'creative_loop_v1': args.reasoning = args.reasoning or 'xhigh'
    if args.workflow == "creative_loop_v1" and (args.rsi or args.rsi_config or args.task_card or args.critic_feedback):
        parser.error("Creative loop excludes RSI, task cards and imported legacy feedback")
    if args.continue_delivery and not args.resume:
        parser.error("--continue-delivery requires --resume")
    if not args.resume and (not args.source or not (args.request or args.request_file)):
        parser.error("A new run requires --source and --request or --request-file")
    from planner_harness import PlannerHarness
    from planner_harness.lock import RunLock
    if args.workflow == "creative_loop_v1":
        from vlm.settings import create_client
        model = create_client({**execution, "workflow": args.workflow}, "planner")
    elif args.backend in {None, "openrouter"}:
        os.environ["LHA_API_PLANNER_MODEL"] = args.model
        if args.reasoning is not None:
            os.environ["LHA_API_PLANNER_REASONING_EFFORT"] = args.reasoning
        from vlm.openrouter import OpenRouterVisionModel
        model = OpenRouterVisionModel(role="planner", model=args.model, reasoning_effort=args.reasoning)
    else:
        from vlm.litellm_vlm import LiteLLMVisionModel
        model = LiteLLMVisionModel(model=args.model, reasoning_effort=args.reasoning, role="planner")
    output = Path(args.output).resolve()
    os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(output / "model-usage.jsonl")
    with RunLock(output):
        harness = PlannerHarness(output, model)
        if args.experiment_profile and not args.resume:
            execution = {**(execution or {}), "experiment_profile": str(args.experiment_profile.resolve())}
        elif args.experiment_profile:
            from planner_harness.creative import verify_experiment
            verify_experiment(args.experiment_profile, ROOT)
            if recorded["execution"].get("experiment_profile") != str(args.experiment_profile.resolve()):
                parser.error("Resume must use its recorded shared profile")
        if args.resume:
            state = harness.resume(additional_turns=args.additional_turns, execution=None if args.workflow == "creative_loop_v1" else execution, continue_delivery=args.continue_delivery,
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
