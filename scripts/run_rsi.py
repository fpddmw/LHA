"""Two-level RSI tools. Preparation is local; model/worker execution is explicit."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def make_model(args):
    if args.backend == "codex":
        os.environ["LOW_HIGH_AGENT_CODEX_PLANNER_MODEL"] = args.model
        os.environ["LOW_HIGH_AGENT_CODEX_PLANNER_REASONING_EFFORT"] = args.reasoning
        from vlm.codex_vlm import CodexVisionModel
        return CodexVisionModel(role="planner")
    from vlm.litellm_vlm import LiteLLMVisionModel
    return LiteLLMVisionModel(model=args.model, reasoning_effort=args.reasoning, role="planner")


def main(argv=None):
    from planner_harness.common import load
    from planner_harness.lock import RunLock
    from planner_harness import rsi_data as data, rsi_validation as validation
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    from planner_harness.rsi_cli_ops import register, execute
    operational_commands = register(sub)
    p = sub.add_parser("splits", help="Freeze explicit source-disjoint D/V/T assignments")
    p.add_argument("--tasks", required=True, help="JSON {tasks: [...], exposed_sources: [...]} from metadata")
    p.add_argument("--output", required=True)
    p = sub.add_parser("collect", help="Collect only development-source runs")
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--splits", required=True)
    p.add_argument("--independent-records", nargs="*", default=[], help="Historical records joined only to collected output hashes")
    p.add_argument("--criterion-alignment", help="Reviewed mapping between exact requirement and independent-card versions")
    p.add_argument("--annotations", nargs="*",default=[],help="Reviewed semantic sidecars; original case facts stay immutable")
    p.add_argument("--output", required=True)
    p = sub.add_parser("propose", help="Model proposes several experience changes; no publication")
    p.add_argument("--development", required=True)
    p.add_argument("--feedback", nargs="*", default=[], help="Sealed development replay feedback packets")
    p.add_argument("--output", required=True)
    p = sub.add_parser("replay-feedback", help="Package actual replay reads and decisions without model calls")
    p.add_argument("--replay", required=True)
    p.add_argument("--proposal")
    p.add_argument("--output", required=True)
    p = sub.add_parser("replay", help="Replay one saved input until generate/finish, with no render")
    p.add_argument("--input", required=True)
    p.add_argument("--catalog", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--max-turns", type=int, default=12)
    p = sub.add_parser("prepare-validation", help="Freeze paired validation; start no jobs")
    p.add_argument("--splits", required=True)
    p.add_argument("--proposal", required=True)
    p.add_argument("--protocol", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--cycle")
    p.add_argument("--split", choices=["D", "V", "T"], default="V")
    p.add_argument("--replay-gate")
    p.add_argument("--adoption")
    p = sub.add_parser("run-validation", help="Run/resume one arm using the existing signed-job worker")
    p.add_argument("--manifest", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--arm", required=True, choices=["base", "candidate", "singlepass"])
    p.add_argument("--output", required=True)
    p.add_argument("--worker-command", nargs=argparse.REMAINDER, help="Last argument; argv with {request} and {response}")
    p = sub.add_parser("run-control", help="Direct or compute-matched fixed-prompt control")
    p.add_argument("--manifest", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--kind", required=True, choices=["direct", "best-of-3"])
    p.add_argument("--singlepass-run", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--worker-command", nargs=argparse.REMAINDER)
    p = sub.add_parser("round", help="Collect, propose and replay a frozen development subset")
    p.add_argument("--config", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("record-arm", help="Join independent scores to saved output hashes")
    p.add_argument("--manifest", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--scores", required=True, help="JSON array of normalized, traceable independent scores")
    p.add_argument("--output", required=True)
    p = sub.add_parser("judge-protocol", help="Print the current English independent-judge protocol hash")
    p = sub.add_parser("judge-run", help="Independently score a completed bound run using the frozen judge")
    p.add_argument("--manifest", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("validate", help="Evaluate the predeclared paired gate")
    p.add_argument("--manifest", required=True)
    p.add_argument("--receipts", nargs="+", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("adopt", help="Publish only after user review of this concrete proposal and validation")
    p.add_argument("--proposal", required=True)
    p.add_argument("--validation", required=True)
    p.add_argument("--reviewed-by", required=True)
    p.add_argument("--monitoring")
    p = sub.add_parser("reject", help="Record a rejected candidate for future proposers")
    p.add_argument("--proposal", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--reviewed-by", required=True)
    p = sub.add_parser("rollback", help="Restore the complete prior library from a reviewed journal")
    p.add_argument("--journal", required=True)
    p.add_argument("--reviewed-by", required=True)
    for command in ("propose", "replay", "run-validation", "round"):
        p = sub.choices[command]
        p.add_argument("--backend", choices=["codex", "litellm"], default="codex")
        p.add_argument("--model", default="gpt-6.1-sol")
        p.add_argument("--reasoning", default="xhigh")
        p.add_argument("--execute", action="store_true", help="Explicitly dispatch model/worker calls")
    args = parser.parse_args(argv)
    if args.command in operational_commands:
        result = execute(args, ROOT, make_model)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command in {"propose", "replay", "run-validation", "round"}:
        if not args.execute:
            parser.error("This operation calls a model; supply --execute to dispatch it")
        os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(Path(args.output).resolve() / "model-usage.jsonl")
        model = make_model(args)
    if args.command == "splits":
        value = load(args.tasks)
        result = data.split_manifest(value["tasks"], args.output, exposed_sources=value.get("exposed_sources", []))
    elif args.command == "collect":
        result = data.collect(args.runs, args.splits, args.output, independent_records=args.independent_records, criterion_alignment=args.criterion_alignment, annotations=args.annotations)
    elif args.command == "propose":
        with RunLock(args.output):
            result = data.propose(args.development, args.output, model, feedback=[data.verify_seal(load(p)) for p in args.feedback])
    elif args.command == "replay-feedback":
        from planner_harness.rsi_wiki import replay_feedback
        from planner_harness.ledger import digest
        result = replay_feedback(args.replay, load(args.proposal) if args.proposal else {"summary": "Historical paired behavior diagnostic; no automatic proposal."}, root=ROOT)
        result = data.sealed(args.output, {**result, "sha256": digest(result)})
    elif args.command == "replay":
        from planner_harness.rsi_replay import replay
        with RunLock(args.output):
            result = replay(args.input, args.catalog, args.output, model, max_turns=args.max_turns)
    elif args.command == "prepare-validation":
        with RunLock(args.output):
            result = validation.prepare(args.splits, args.proposal, args.output, load(args.protocol), cycle_path=args.cycle, split=args.split, replay_gate_path=args.replay_gate, adoption_path=args.adoption)
    elif args.command == "run-validation":
        def worker(request, response):
            argv = [v.replace("{request}", str(request)).replace("{response}", str(response)) for v in args.worker_command]
            subprocess.run(argv, check=True)
        result = validation.run_task(args.manifest, args.task, args.arm, args.output, model, worker=worker if args.worker_command else None)
    elif args.command == "run-control":
        if not args.execute:
            parser.error("Controls dispatch renderer/Critic work; supply --execute")
        from planner_harness.rsi_controls import run_control
        def worker(request, response):
            argv = [v.replace("{request}", str(request)).replace("{response}", str(response)) for v in args.worker_command]
            subprocess.run(argv, check=True)
        result = run_control(args.manifest, args.task, args.kind, args.singlepass_run, args.output, root=ROOT, worker=worker if args.worker_command else None)
    elif args.command == "round":
        from planner_harness.rsi_round import run_round
        result = run_round(load(args.config), args.output, model, model, root=ROOT)
    elif args.command == "record-arm":
        result = validation.record_arm(args.manifest, args.run, load(args.scores), args.output)
    elif args.command == "judge-protocol":
        from planner_harness.rsi_judge import protocol_hash
        result = {"schema": "lha-rsi-independent-v1", "sha256": protocol_hash()}
    elif args.command == "judge-run":
        if not args.execute:
            parser.error("Scoring calls the independent model; supply --execute")
        from planner_harness.rsi_judge import judge_run
        from evaluation.backends import OpenAICompatibleJudge
        profile = validation.verify_manifest(args.manifest)["protocol"]["judge"]
        client = OpenAICompatibleJudge(model=profile["model"], reasoning_effort=profile.get("reasoning_effort"))
        with RunLock(args.output):
            rows = judge_run(args.manifest, args.run, args.output, client, root=ROOT)
        result = {"status": "scored", "counts": {"candidates": len(rows)}}
    elif args.command == "validate":
        result = validation.validate(args.manifest, args.receipts, args.output)
    elif args.command == "adopt":
        result = validation.adopt(args.proposal, args.validation, args.reviewed_by, monitoring_path=args.monitoring)
    elif args.command == "reject":
        result = validation.reject(args.proposal, args.reason, args.reviewed_by)
    else:
        result = validation.rollback(args.journal, args.reviewed_by)
    print(json.dumps({k: result[k] for k in ("status", "schema", "sha256", "counts", "primary_mean_delta") if k in result}, indent=2))


if __name__ == "__main__":
    main()
