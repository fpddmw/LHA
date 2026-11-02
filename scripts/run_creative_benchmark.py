"""Prepare/check selected current sources and methods; execute on authorized assets."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "preflight", "provider-preflight", "recover-direct", "recover-pe-loop", "run", "status"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-config", type=Path)
    parser.add_argument("--backend", choices=["bernini", "ditto"], default=None)
    parser.add_argument("--budget-config",type=Path,help="Explicit batch/topic resource limits; choose quoted allowance or count_limits_only")
    from evaluation.providers import JUDGES
    parser.add_argument("--judge", choices=JUDGES, default=JUDGES[0])
    parser.add_argument("--device")
    parser.add_argument("--devices",nargs="+",help="Physical devices or auto; default reads host config")
    parser.add_argument("--shard-rank",type=int)
    parser.add_argument("--shard-count",type=int)
    parser.add_argument("--topic")
    parser.add_argument("--reason")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--not-executed", action="store_true")
    parser.add_argument("--split", nargs="+", choices=["train", "validation", "test"], default=["test"])
    parser.add_argument("--sample-ids", nargs="+", help="Prepare only these sample IDs within the selected splits")
    parser.add_argument("--prompt-form", nargs="+", choices=["short", "long"], default=["short", "long"])
    from experiments.results import RUN_METHODS
    parser.add_argument("--method", nargs="+", choices=RUN_METHODS, default=None,
                        help="Test default: direct pe-loop none full; pe retains the legacy single enhancement")
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--seed-step", type=int, default=1)
    from planner_harness.resources import MAX_GENERATIONS
    parser.add_argument("--max-generations", type=int, default=MAX_GENERATIONS)
    parser.add_argument("--max-turns", type=int, default=None, help="Deprecated metering field; online tasks stop at time/generation policy")
    parser.add_argument("--best-of-n", type=int)
    parser.add_argument("--results-root", type=Path, default=ROOT / "out/benchmark_results")
    parser.add_argument("--resource-policy", type=Path)
    parser.add_argument("--experience-snapshot",type=Path,help="Final private training snapshot, frozen read-only for validation/test")
    parser.add_argument("--planner-config", type=Path, help="Freeze explicit API Planner model/effort")
    parser.add_argument("--model-config", type=Path, help="Role-to-API-factory/options configuration; no Codex CLI")
    parser.add_argument("--review-mode", choices=["critic","planner"], default="critic",
                        help="Planner Loop reviewer; PE Loop always uses the independent online Critic")
    parser.add_argument('--no-maintenance',action='store_true',help='Run all selected tasks read-only, including RSI train-labelled samples')
    args = parser.parse_args()
    from planner_harness.common import load, save
    from experiments.creative_benchmark import prepare, verify_batch
    from experiments.creative_benchmark import run
    from experiments.preflight import local_preflight, host_preflight, provider_preflight
    host = load(args.host_config) if args.host_config else None
    if args.command == "prepare":
        result = prepare(ROOT, args.output, backend=args.backend or (host or {}).get("renderer", {}).get("backend", "bernini"),
            output_dimensions=(host or {}).get("renderer", {}).get("output"), splits=args.split, prompt_forms=args.prompt_form, methods=args.method,
            seed_start=args.seed_start, seed_step=args.seed_step, max_generations=args.max_generations,
            max_turns=args.max_turns, best_of_n=args.best_of_n, results_root=args.results_root,
            resource_policy=load(args.resource_policy) if args.resource_policy else None,
            planner=load(args.planner_config) if args.planner_config else None,experience_snapshot=args.experience_snapshot,
            models=load(args.model_config) if args.model_config else None,review={"mode":args.review_mode},training_maintenance=False if args.no_maintenance else None,
            **({"sample_ids":args.sample_ids} if args.sample_ids is not None else {}))
        print(json.dumps({"status": "prepared", "topics": len(result["topics"]), "arms": result["arms"], "planned_matrix":[{"topic":t["id"],"methods":t.get("methods",result["arms"])} for t in result["topics"]], "model_calls": 0, "gpu_jobs": 0}))
    elif args.command == "preflight":
        batch = verify_batch(ROOT, args.output)
        if batch.get("schema") == "lha-unified-benchmark-v1":
            from experiments.unified_benchmark import preflight
            result = preflight(ROOT, args.output, host)
        else:
            result = {"local": local_preflight(ROOT, args.output), "host": host_preflight(ROOT, host, execute=bool(host))}
        save(args.output / "preflight.json", result)
        print(json.dumps(result))
    elif args.command == "provider-preflight":
        from planner_harness.supervisor import maybe_supervise_cli
        if maybe_supervise_cli(args.output,[__file__,*sys.argv[1:]]):return
        print(json.dumps(provider_preflight(args.output, name=args.judge)))
    elif args.command == 'recover-pe-loop':
        if not args.topic or not args.reason:
            parser.error('PE recovery requires --topic and --reason')
        verify_batch(ROOT, args.output)
        from experiments.recovery import recover_pe_loop
        print(json.dumps(recover_pe_loop(args.output, args.topic, args.reason)))
    elif args.command == "recover-direct":
        if args.device is None or not args.topic or not args.reason:
            parser.error("Direct recovery requires --device, --topic and --reason")
        from experiments.recovery import recover_direct
        print(json.dumps(recover_direct(args.output, args.device, args.topic, args.reason,
                                       receipt=args.receipt, not_executed=args.not_executed)))
    elif args.command == "run":
        if host is None:
            parser.error("Use --host-config for explicitly opened devices and verified assets")
        if args.devices:host["devices"]="auto" if args.devices==["auto"] else args.devices
        for field,default in (("shard_rank",0),("shard_count",1)):
            override=getattr(args,field)
            if override is not None:host[field]=override
            else:host.setdefault(field,default)
        if args.budget_config:host["budget"] = load(args.budget_config)
        from planner_harness.accounting import install,validate_cohort
        batch=verify_batch(ROOT,args.output)
        if batch.get("schema") == "lha-unified-benchmark-v1":
            from experiments.unified_benchmark import policy as unified_policy
            policy=unified_policy(batch, host.get("budget"))
        else:
            policy=validate_cohort(host.get("budget"),max_generations=batch["max_generations"],topics=batch["topics"])
        install(args.output/"accounting",policy,require_live=True)
        from planner_harness.supervisor import maybe_supervise_cli
        if maybe_supervise_cli(args.output,[__file__,*sys.argv[1:]]):return
        result = run(ROOT, args.output, host)
        print(json.dumps({"status": result["status"], "topics": len(result["topics"])}))
    else:
        print(json.dumps(load(args.output / "checkpoint.json") if (args.output / "checkpoint.json").exists() else {"status": "prepared_not_started"}))


if __name__ == "__main__":
    from planner_harness.supervisor import cli_entry
    cli_entry(main)
