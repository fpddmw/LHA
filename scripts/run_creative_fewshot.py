"""Prepare/check the seven-topic cohort; execute only after the user opens the GPUs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "preflight", "provider-preflight", "recover-direct", "run", "status"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-config", type=Path)
    parser.add_argument("--judge", choices=["glm5.3flash", "sonnet-5.5high"], default="glm5.3flash")
    parser.add_argument("--device")
    parser.add_argument("--topic")
    parser.add_argument("--reason")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--not-executed", action="store_true")
    args = parser.parse_args()
    from planner_harness.common import load, save
    from experiments.creative_fewshot import prepare, verify_batch, run
    from experiments.preflight import local_preflight, host_preflight, provider_preflight
    host = load(args.host_config) if args.host_config else None
    if args.command == "prepare":
        result = prepare(ROOT, args.output)
        print(json.dumps({"status": "prepared", "topics": len(result["topics"]), "arms": result["arms"], "model_calls": 0, "gpu_jobs": 0}))
    elif args.command == "preflight":
        verify_batch(ROOT, args.output)
        result = {"local": local_preflight(ROOT, args.output), "host": host_preflight(ROOT, host, execute=bool(host))}
        save(args.output / "preflight.json", result)
        print(json.dumps(result))
    elif args.command == "provider-preflight":
        print(json.dumps(provider_preflight(args.output, name=args.judge)))
    elif args.command == "recover-direct":
        if args.device is None or not args.topic or not args.reason:
            parser.error("Direct recovery requires --device, --topic and --reason")
        from experiments.recovery import recover_direct
        print(json.dumps(recover_direct(args.output, args.device, args.topic, args.reason,
                                       receipt=args.receipt, not_executed=args.not_executed)))
    elif args.command == "run":
        if host is None:
            parser.error("Use --host-config for explicitly opened devices and verified assets")
        result = run(ROOT, args.output, host)
        print(json.dumps({"status": result["status"], "topics": len(result["topics"])}))
    else:
        print(json.dumps(load(args.output / "checkpoint.json") if (args.output / "checkpoint.json").exists() else {"status": "prepared_not_started"}))


if __name__ == "__main__":
    main()
