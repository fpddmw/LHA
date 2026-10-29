"""Manage a local-disk durable pipeline. No deployment, credential copying or remote shutdown."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.common import load
from server_runtime.queue import Queue


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", type=Path, required=True, help="Host-local state directory, never a network share")
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--config", type=Path, required=True)
    for cmd in ("submit", "evaluate"):
        sub = commands.add_parser(cmd)
        sub.add_argument("--manifest", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--once", action="store_true", help="Finish runnable dependency chains, then exit at idle")
    commands.add_parser("status")
    commands.add_parser("drain", help="Persistently stop dispatch; finish in-flight calls and exit")
    commands.add_parser("resume", help="Allow dispatch again; does not launch a process")
    retry = commands.add_parser("retry")
    retry.add_argument("--job", required=True, type=int)
    retry.add_argument("--reason", required=True, help="Record inspection and why another external attempt is authorized")
    args = parser.parse_args(argv)
    directory = args.service.resolve()
    if args.command != "init" and not (directory / "config.json").is_file():
        parser.error("Initialize this service before use")
    config = load(args.config if args.command == "init" else directory / "config.json")
    q = Queue(directory / "queue.sqlite3", config.get("limits"))
    if args.command == "status":
        print(json.dumps(q.status(), ensure_ascii=False, indent=2))
        return
    if args.command in {"drain", "resume"}:
        print(json.dumps({"dispatch": q.dispatch("drain" if args.command == "drain" else "running")}))
        return
    if args.command == "retry":
        q.retry(args.job, args.reason)
        return
    # Process-wide environment is set once before any worker threads are started.
    os.environ["LOW_HIGH_AGENT_CODEX_TIMEOUT"] = str(config.get("llm_timeout_seconds", 1800))
    os.environ["LOW_HIGH_AGENT_CODEX_ATTEMPTS"] = "1"
    os.environ["LOW_HIGH_AGENT_CODEX_MODEL"] = config.get("model", "gpt-6.1-sol")
    os.environ["LOW_HIGH_AGENT_CODEX_REASONING_EFFORT"] = config.get("reasoning_effort", "xhigh")
    os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(directory / "llm-usage.jsonl")
    from server_runtime.service import Service
    service = Service(q, directory, args.root.resolve(), config)
    if args.command == "init":
        print(json.dumps({"status": "initialized", "service": str(directory), "models_loaded": False}))
    elif args.command in {"submit", "evaluate"}:
        manifest = load(args.manifest)
        items = manifest if isinstance(manifest, list) else [manifest]
        submit = service.submit if args.command == "submit" else service.submit_evaluation
        print(json.dumps({"jobs": [submit(item) for item in items]}))
    elif args.command == "run":
        from server_runtime.engine import Engine
        engine = Engine(q, directory, service, service.expand)
        def stop(*_):
            q.dispatch("drain")
            engine.stop.set()
            engine.wakeup.set()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        engine.run(once=args.once)
        if any(row["state"] in {"failed", "needs_review"} for row in q.summary()):
            raise SystemExit(2)


if __name__ == "__main__":
    main()
