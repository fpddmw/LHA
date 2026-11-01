"""Operational commands around the model-led RSI interfaces."""
from pathlib import Path
import os
from .common import load, save, sha


def register(sub):
    specs = {
        "criteria-draft": ("entry", "output"),
        "criteria-freeze": ("draft", "output", "reviewed-by", "reason"),
        "evidence-refresh": ("development", "catalog", "output"),
        "case-annotate": ("cases", "annotation", "output"),
        "branch-library": ("development", "output"),
        "replay-partition": ("decisions", "output"),
        "cycle-progress": ("config", "output"),
        "cycle-run": ("config", "output"),
        "cycle-monitor": ("config", "cycle", "validation", "output"),
        "freeze-cycle": ("splits", "protocol", "output"),
        "paired-replay": ("config", "output"),
        "review-replay": ("replay", "labels", "output"),
        "reconcile-call": ("directory", "action", "reason", "reviewed-by"),
        "recover-tool": ("request", "reason", "reviewed-by"),
        "batch-init": ("manifest", "service-config", "directory"),
        "batch-run": ("directory",), "batch-status": ("directory",),
        "batch-retry": ("directory", "job", "reason"),
        "report": ("manifest", "output"), "health": ("output",),
        "canary": ("report", "limits", "output"), "drift": ("reference", "current", "limits", "output"),
        "calibration-prepare": ("cases", "profile", "output"),
        "calibration-run": ("manifest", "output"),
        "calibration-review": ("comparison", "reviewed-by", "decision", "notes", "output"),
        "remote-fetch": ("request", "profile", "output"),
        "critic-anchor": ("request", "cycle", "output"),
        "critic-drift": ("reference", "current", "limits", "output"),
    }
    parsers = {}
    for name, fields in specs.items():
        p = parsers[name] = sub.add_parser(name)
        for field in fields:
            p.add_argument("--" + field, required=True)
    parsers["paired-replay"].add_argument("--backend", choices=["codex", "litellm"], default="codex")
    parsers["paired-replay"].add_argument("--model", default="gpt-6.1-sol")
    parsers["paired-replay"].add_argument("--reasoning", default="xhigh")
    parsers["criteria-draft"].add_argument("--backend", choices=["codex", "litellm"], default="codex")
    parsers["criteria-draft"].add_argument("--model", default="gpt-6.1-sol")
    parsers["criteria-draft"].add_argument("--reasoning", default="high")
    parsers["criteria-draft"].add_argument("--execute", action="store_true")
    parsers["cycle-run"].add_argument("--backend", choices=["codex", "litellm"], default="codex")
    parsers["cycle-run"].add_argument("--model", default="gpt-6.1-sol")
    parsers["cycle-run"].add_argument("--reasoning", default="high")
    parsers["cycle-run"].add_argument("--execute", action="store_true")
    parsers["evidence-refresh"].add_argument("--previous")
    parsers["cycle-monitor"].add_argument("--runs",nargs="+",required=True)
    for name in ("paired-replay", "batch-run", "calibration-run", "remote-fetch", "critic-anchor"):
        parsers[name].add_argument("--execute", action="store_true")
    parsers["reconcile-call"].add_argument("--response")
    parsers["reconcile-call"].add_argument("--extra-attempts", type=int, default=1)
    parsers["recover-tool"].add_argument("--recovered-response")
    parsers["recover-tool"].add_argument("--confirmed-not-executed", action="store_true")
    parsers["batch-init"].add_argument("--arms", nargs="+", default=["base", "candidate"])
    parsers["batch-init"].add_argument("--no-score", action="store_true")
    parsers["batch-run"].add_argument("--once", action="store_true")
    parsers["report"].add_argument("--receipts", nargs="+", required=True)
    parsers["report"].add_argument("--arms", nargs="+", default=["direct", "singlepass", "best-of-3", "base", "candidate"])
    parsers["health"].add_argument("--runs", nargs="+", required=True)
    parsers["health"].add_argument("--thresholds")
    parsers["canary"].add_argument("--journal")
    return set(specs)


def execute(args, root, make_model):
    name = args.command
    if name in {"cycle-run", "criteria-draft", "paired-replay", "batch-run", "calibration-run", "remote-fetch", "critic-anchor"} and not args.execute:
        raise ValueError("This command dispatches external work; supply --execute")
    if name == "criteria-draft":
        from .task_criteria import draft
        from .rsi_calls import call_once
        import json
        model = make_model(args)
        class SourceOnly:
            model = args.model
            reasoning_effort = args.reasoning
            def predict_json(self, *, system_prompt, user_text, image_paths):
                return json.loads(call_once(Path(args.output) / "builder-call", model, system_prompt, user_text, image_paths))
        return draft(load(args.entry), SourceOnly(), args.output, root=root)
    if name == "criteria-freeze":
        from .task_criteria import freeze
        return freeze(args.draft, args.output, args.reviewed_by, args.reason)
    if name == "case-annotate":
        from .rsi_evidence import annotate
        from .rsi_data import sealed,verify_seal
        rows=verify_seal(load(args.cases))["cases"]
        spec=load(args.annotation)
        case=next(r for r in rows if r["id"]==spec["case_id"])
        return sealed(args.output,annotate(case,**{k:spec[k] for k in ("labels","reviewed_by","reason","evidence")}))
    if name in {"evidence-refresh", "branch-library", "replay-partition"}:
        from .rsi_data import verify_seal, sealed
        from . import rsi_evidence as evidence
        if name == "replay-partition":
            return evidence.freeze_partition(load(args.decisions), args.output)
        development = verify_seal(load(args.development))
        records = development["records"]
        if name == "branch-library":
            return sealed(args.output, evidence.branch_library(records))
        catalog = load(args.catalog)
        if isinstance(catalog, dict): catalog = catalog["entries"]
        previous = verify_seal(load(args.previous)) if args.previous else None
        return sealed(args.output, evidence.refresh(records, catalog, previous=previous,annotations=development.get("annotations", [])))
    if name == "cycle-progress":
        from .rsi_workflow import progress
        return progress(load(args.config), args.output)
    if name == "cycle-monitor":
        from .rsi_workflow import monitor
        return monitor(load(args.config),args.cycle,args.validation,args.runs,args.output)
    if name == "cycle-run":
        from .rsi_workflow import run
        model = make_model(args)
        return run(load(args.config), args.output, model, model, root=root)
    if name == "freeze-cycle":
        from .rsi_cycle import freeze
        return freeze(args.splits, load(args.protocol), args.output, root=root)
    if name == "critic-anchor":
        from .rsi_anchors import run
        return run(args.request, args.cycle, args.output, root=root)
    if name == "critic-drift":
        from .rsi_anchors import compare
        return compare(args.reference, args.current, args.output, **load(args.limits))
    if name == "paired-replay":
        from .rsi_paired_replay import probe
        config = load(args.config)
        from .lock import RunLock
        with RunLock(args.output):
            return probe(config["inputs"], config["base_catalog"], config["candidate_catalog"], args.output, make_model(args), root=root,
                         repetitions=config.get("repetitions", 3), max_turns=config.get("max_turns", 12), targets=config["targets"], cycle_path=config.get("cycle"), partition=config.get("partition"))
    if name == "review-replay":
        from .rsi_paired_replay import review
        return review(args.replay, load(args.labels), args.output)
    if name == "reconcile-call":
        from .rsi_calls import reconcile
        return reconcile(args.directory, args.action, args.reason, args.reviewed_by, response=args.response, extra_attempts=args.extra_attempts)
    if name == "recover-tool":
        from .rsi_recovery import recover_tool
        return recover_tool(args.request, args.reviewed_by, args.reason, recovered_response=args.recovered_response, confirmed_not_executed=args.confirmed_not_executed)
    if name.startswith("batch-"):
        return batch_command(args, root)
    if name == "report":
        from .rsi_reporting import report
        return report(args.manifest, args.receipts, args.output, arms=args.arms)
    if name == "health":
        from .rsi_reporting import health
        return health(args.runs, args.output, thresholds=load(args.thresholds) if args.thresholds else None)
    if name == "canary":
        from .rsi_reporting import canary
        return canary(args.report, args.output, journal=args.journal, **load(args.limits))
    if name == "drift":
        from .rsi_reporting import drift
        return drift(args.reference, args.current, args.output, **load(args.limits))
    if name == "calibration-prepare":
        from .rsi_calibration import prepare
        return prepare(load(args.cases), load(args.profile), args.output)
    if name == "calibration-run":
        from .rsi_calibration import run
        from evaluation.backends import OpenAICompatibleJudge
        profile = load(args.manifest)["profile"]
        client = OpenAICompatibleJudge(model=profile["model"], reasoning_effort=profile.get("reasoning_effort"))
        from .lock import RunLock
        with RunLock(args.output):
            return run(args.manifest, args.output, client, root=root)
    if name == "calibration-review":
        from .rsi_calibration import review
        return review(args.comparison, args.output, args.reviewed_by, args.decision, args.notes)
    if name == "remote-fetch":
        from .rsi_remote import RemoteRenderer
        job = load(args.request)
        payload = RemoteRenderer({**load(args.profile), "allow_dispatch": False})(job, Path(args.output).parent)
        result = {"request_sha256": job["sha256"], "mode": job["mode"], "status": "complete", "payload": payload}
        save(args.output, result)
        return {"status": "fetched", "response": args.output, "sha256": sha(args.output)}
    raise ValueError("Unknown RSI operational command")


def batch_command(args, root):
    from server_runtime.queue import Queue
    directory = Path(args.directory).resolve()
    config_path = directory / "service/config.json"
    if args.command == "batch-init":
        from .rsi_data import sealed
        config = load(args.service_config)
        def secrets(value):
            if isinstance(value, dict):
                return bool({"api_key", "password", "access_token"} & value.keys()) or any(secrets(v) for v in value.values())
            return isinstance(value, list) and any(secrets(v) for v in value)
        if secrets(config):
            raise ValueError("Keep credentials in environment variables, not saved service configuration")
        sealed(directory / "batch-binding.json", {"manifest": str(Path(args.manifest).resolve()), "manifest_sha256": load(args.manifest)["sha256"]})
    else:
        config = load(config_path)
    q = Queue(directory / "queue.sqlite3", config.get("limits"))
    if args.command == "batch-status":
        return q.status()
    if args.command == "batch-retry":
        q.retry(int(args.job), args.reason)
        return {"status": "queued_after_review", "job": int(args.job)}
    # Set process configuration once, before the existing queue starts worker threads.
    os.environ["LOW_HIGH_AGENT_CODEX_MODEL"] = config.get("model", "gpt-6.1-sol")
    os.environ["LOW_HIGH_AGENT_CODEX_REASONING_EFFORT"] = config.get("reasoning_effort", "xhigh")
    os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(directory / "llm-usage.jsonl")
    from server_runtime.service import Service
    from .rsi_batch import Batch
    renderer = None
    if config.get("remote_renderer"):
        from .rsi_remote import RemoteRenderer
        renderer = RemoteRenderer(config["remote_renderer"])
    elif config.get("renderer", {}).get("backend") == "ditto":
        from server_runtime.ditto import PersistentDittoRenderer
        renderer = PersistentDittoRenderer(root, config["renderer"], directory / "gpu")
    service = Service(q, directory / "service", root, config, renderer=renderer)
    binding = load(directory / "batch-binding.json")
    if load(binding["manifest"])["sha256"] != binding["manifest_sha256"]:
        raise ValueError("Batch experiment binding changed")
    batch = Batch(q, directory, binding["manifest"], service, root=root)
    if args.command == "batch-init":
        return {"queued": batch.submit(args.arms, score=not args.no_score), "models_called": 0}
    from server_runtime.engine import Engine
    engine = Engine(q, directory, batch, batch.expand)
    import signal
    def stop(*_):
        q.dispatch("drain"); engine.stop.set(); engine.wakeup.set()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    engine.run(once=args.once)
    return batch.status()
