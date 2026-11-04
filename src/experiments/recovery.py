"""Explicit recovery of saved tool jobs and PE phases."""
from pathlib import Path
from planner_harness.common import load, save, sha, stamp
from planner_harness.execution import signature, immutable
from planner_harness.lock import RunLock
from server_runtime.queue import Queue


def pe_prompt_recovery_plan(output, topic, device):
    """Inspect one recorded length refusal and its original budget without calls."""
    from planner_harness import accounting
    output = Path(output).resolve()
    batch = load(output / "batch.json")
    if batch.get("sha256") != signature({k: v for k, v in batch.items() if k != "sha256"}):
        raise ValueError("Frozen batch changed")
    task = next(t for t in batch["topics"] if t["id"] == topic)
    directory = output / "methods" / topic / "pe-loop"
    worker = output / "workers" / str(device)
    if not directory.resolve().is_relative_to(output) or not worker.resolve().is_relative_to(output):
        raise ValueError("Recovery paths must belong to the original run")
    binding = load(directory / "loop.json")
    if binding["profile_sha256"] != batch["profile_sha256"] or binding["source_sha256"] != task["source_sha256"]:
        raise ValueError("PE loop does not belong to this batch and source")
    if (directory / "settlement.json").exists() and load(directory / "settlement.json").get("status") == "ready":
        return {"status": "complete", "topic": topic}
    prior = directory / "prompt-length-recovery/execution.json"
    if prior.exists():
        folder = directory / "rounds" / f"{load(prior)['round']:04d}"
    else:
        folder = next(p for p in sorted((directory / "rounds").iterdir())
                      if p.is_dir() and p.name.isdigit() and not (p / "candidate.json").exists())
    jobdir = worker / "baselines" / topic / "pe-loop" / str(int(folder.name) - 1)
    request, response = load(jobdir / "request.json"), load(jobdir / "response.json")
    if (request["sha256"] != signature({k: v for k, v in request.items() if k != "sha256"})
            or response.get("request_sha256") != request["sha256"]
            or response.get("status") != "failed" or response.get("outcome_unknown")
            or response.get("error") not in {
                "ValueError: Prompt exceeds tokenizer limit; automatic truncation is disabled",
                "ValueError: Prompt exceeds tokenizer limit; truncation is disabled"}
            or (jobdir / "render-started.json").exists() or (jobdir / "renderer-input.json").exists()):
        raise ValueError("Recovery requires a definite tokenizer refusal before generation")
    prompt = load(folder / "prompt.json")
    if signature(prompt["value"]) != prompt["sha256"] or request["payload"]["prompt"] != prompt["value"]:
        raise ValueError("Original PE prompt changed")
    scope = accounting.scope(output / "accounting", topic, lane="pe-loop")
    if request.get("accounting_scope") != scope:
        raise ValueError("Recovery must use the original PE accounting scope")
    ledger = accounting.load_ledger(scope["root"])
    clock = ledger["topics"].get(topic, {}).get("lanes", {}).get("pe-loop", {})
    if not isinstance(clock.get("started_unix"), (int, float)) or (clock.get("deadline_unix") is not None and not isinstance(clock["deadline_unix"], (int, float))):
        raise ValueError("Original PE task clock is unavailable")
    unresolved = [r["id"] for r in ledger["operations"].values()
                  if r["topic"] == topic and r["status"] != "not_submitted" and not r.get("completion")]
    if unresolved:
        raise ValueError("Reconcile original external operations before recovery: " + ", ".join(unresolved))
    record = ledger["operations"].get(request["sha256"])
    if record and record["status"] != "not_submitted":
        raise ValueError("Original request has a recorded generation submission")
    return {"status": "recoverable", "topic": topic, "round": int(folder.name),
            "batch_sha256": batch["sha256"], "loop_sha256": sha(directory / "loop.json"),
            "request_sha256": request["sha256"], "response_sha256": sha(jobdir / "response.json"),
            "worker": str(worker), "scope": scope,
            "topic_closed": ledger["topics"].get(topic, {}).get("closed", False),
            "clock": clock}


def recover_pe_prompt(output, topic, device, reason, *, execute=False):
    """Resume one PE with the current repair code, original receipts and budget."""
    import copy
    import os
    from planner_harness import accounting
    from planner_harness.protocol_sources import protocol_inventory
    from . import unified_benchmark as unified
    from .pe_loop import COMPACT_PROMPT, MAX_PROMPT_REVISIONS
    from server_runtime.service import Service

    output = Path(output).resolve()
    root = Path(__file__).resolve().parents[2]
    plan = pe_prompt_recovery_plan(output, topic, device)
    if not execute or plan["status"] == "complete":
        return plan
    if not reason.strip():
        raise ValueError("Describe the inspected failure being recovered")
    with RunLock(output / "unified-owner"), RunLock(output / "batch-owner"):
        plan = pe_prompt_recovery_plan(output, topic, device)
        if plan["status"] == "complete":
            return plan
        batch = load(output / "batch.json")
        task = next(t for t in batch["topics"] if t["id"] == topic)
        directory = output / "methods" / topic / "pe-loop"
        worker = Path(plan["worker"])
        binding = load(directory / "loop.json")
        batch = {**batch, "renderer_identity": binding["renderer"]}
        host_path = worker / "host.json"
        if host_path.exists() and load(host_path).get("local_results_root"):
            batch["results_root"] = load(host_path)["local_results_root"]
        repair = directory / "prompt-length-recovery"
        record = {k: plan[k] for k in ("topic", "round", "batch_sha256", "loop_sha256", "request_sha256", "response_sha256", "scope")}
        record.update(reason=reason, runtime_sources=protocol_inventory(root),
                      max_prompt_revisions=MAX_PROMPT_REVISIONS,
                      compaction_prompt_sha256=signature({"text": COMPACT_PROMPT}))
        immutable(repair / "execution.json", record)
        # A scheduler settlement can close the topic before its original deadline.
        # Reopen only that bookkeeping flag; all clocks and charges stay in place.
        try:
            accounting.check_task(plan["scope"])
        except accounting.ResourceExhausted:
            pass  # The PE loop will settle its last committed choice without calls.
        else:
            with RunLock(output / "accounting/accounting-lock", timeout=10):
                ledger = accounting.load_ledger(output / "accounting")
                current = ledger["topics"].get(topic, {})
                if current.get("closed"):
                    current["closed"] = False
                    accounting._event(ledger, "topic_admit", topic,
                                      {"recovery": True, "reason": reason,
                                       "original_clocks": current.get("lanes", {})})
                    save(output / "accounting/ledger.json", ledger)
        config = copy.deepcopy(load(worker / "config.json"))
        config.pop("experiment_profile", None)
        config["accounting_root"] = plan["scope"]["root"]
        config["budget"] = load(output / "accounting/policy.json")
        queue = Queue(repair / "service/queue.sqlite3", {"gpu": 1, "llm": 1, "cpu": 1})
        os.environ["CUDA_VISIBLE_DEVICES"] = str(device)
        class ResidentService(Service):
            def close(self):
                pass

        service = ResidentService(queue, repair / "service", root, config)

        class RecoveryRuntime(unified.Runtime):
            def __init__(self):
                self.root, self.output, self.batch = root, output, batch
                self.directory, self.queue, self.service = worker, queue, service
                self.host, self.pe_backend = config, None

            def ready(self):
                # Load the renderer only if a new admitted request needs it.
                pass

        runtime = RecoveryRuntime()
        try:
            result = unified.execute_method(root, output, task, "pe-loop", batch, runtime)
            path = directory / "settlement.json"
            if path.exists():
                previous = load(path)
                immutable(directory / "settlement-history" / (signature(previous) + ".json"), previous)
            row = {"topic": topic, "method": "pe-loop", "review_mode": "shared",
                   "batch_sha256": batch["sha256"], **result,
                   "recovery_execution": str(repair / "execution.json")}
            save(path, row)
            save(repair / "result.json", row)
            accounting.close_topic(plan["scope"])
            return row
        finally:
            runtime.close()


def settle_pe_interruption(output, topic, device, *, execute=False):
    """Register cached PE videos after an interrupted model call, without calls."""
    from planner_harness import accounting
    from . import unified_benchmark as unified
    from .pe_loop import RecordedInterruption

    output = Path(output).resolve()
    directory = output / "methods" / topic / "pe-loop"
    worker = output / "workers" / str(device)
    if not directory.resolve().is_relative_to(output) or not worker.resolve().is_relative_to(output):
        raise ValueError("Settlement paths must belong to the original run")
    with RunLock(output / "unified-owner"), RunLock(output / "batch-owner"):
        batch = load(output / "batch.json")
        if batch.get("sha256") != signature({k: v for k, v in batch.items() if k != "sha256"}):
            raise ValueError("Frozen batch changed")
        path = directory / "settlement.json"
        if path.exists() and load(path).get("status") == "ready":
            return {"status": "complete", "topic": topic}
        task = next(t for t in batch["topics"] if t["id"] == topic)
        progress = load(directory / "progress.json")
        if (progress.get("phase") not in {"enhance", "review", "select"} or progress.get("status") != "awaiting_recovery"
                or progress.get("error_type") != "ExternalExecutionUnknown"
                or not 2 <= progress.get("round", 0) <= batch["max_generations"]):
            raise ValueError("Settlement requires a recorded interrupted PE model call after a completed choice")
        number, phase = progress["round"], progress["phase"]
        folder = directory / "rounds" / f"{number:04d}"
        phase_folder = folder / {"enhance": "enhance", "review": "review", "select": "selection"}[phase]
        scope = accounting.scope(output / "accounting", topic, lane="pe-loop")
        ledger = accounting.load_ledger(scope["root"])
        clock = ledger["topics"].get(topic, {}).get("lanes", {}).get("pe-loop", {})
        if not isinstance(clock.get("started_unix"), (int, float)) or (clock.get("deadline_unix") is not None and not isinstance(clock["deadline_unix"], (int, float))):
            raise ValueError("Original PE task clock is unavailable")
        unknown = [r["id"] for r in ledger["operations"].values()
                   if r["topic"] == topic and r["lane"] == "pe-loop" and r["kind"] == "model"
                   and r["status"] in {"in_flight_unknown", "failed_unknown_cost"}
                   and Path(r["id"]).is_relative_to(phase_folder)]
        if not unknown:
            raise ValueError("Original phase has no unresolved model operation")
        phase_names = ["prompt", "candidate", "feedback", "choice"]
        current_names = {"enhance": [], "review": phase_names[:2], "select": phase_names[:3]}[phase]
        for i in range(1, number + 1):
            current = directory / "rounds" / f"{i:04d}"
            names = phase_names if i < number else current_names
            for name in names:
                receipt = load(current / (name + ".json"))
                if receipt.get("sha256") != signature(receipt["value"]):
                    raise ValueError("Saved PE phase changed: " + str(current / name))
        if any((folder / (name + ".json")).exists() for name in phase_names[len(current_names):]):
            raise ValueError("A later completed phase is available; collect its original result")
        plan = {"status": "settlement_ready", "topic": topic, "round": number, "phase": phase,
                "batch_sha256": batch["sha256"], "loop_sha256": sha(directory / "loop.json"),
                "progress_sha256": sha(directory / "progress.json"), "scope": scope,
                "clock": clock, "unknown_operations": unknown, "model_calls": 0, "renders": 0}
        if not execute:
            return plan
        repair = directory / "selection-settlement"
        immutable(repair / "execution.json", {**plan, "reason": progress["reason"]})
        renderer = load(directory / "loop.json")["renderer"]
        if renderer is not None:
            batch = {**batch, "renderer_identity": renderer}
        host_path = worker / "host.json"
        if host_path.exists() and load(host_path).get("local_results_root"):
            batch["results_root"] = load(host_path)["local_results_root"]

        class CachedRuntime:
            def unavailable(self, *args, **kwargs):
                raise ValueError("An earlier PE phase receipt is missing")

            def settle(self, *args, **kwargs):
                raise RecordedInterruption(progress["reason"])

            render = unavailable
            refine = settle if phase == "enhance" else unavailable
            review = settle if phase == "review" else unavailable

            def choose(self, *args, **kwargs):
                raise accounting.ExternalExecutionUnknown(progress["reason"])

        root = Path(__file__).resolve().parents[2]
        result = unified.execute_method(root, output, task, "pe-loop", batch, CachedRuntime())
        if path.exists():
            previous = load(path)
            immutable(directory / "settlement-history" / (signature(previous) + ".json"), previous)
        row = {"topic": topic, "method": "pe-loop", "review_mode": "shared",
               "batch_sha256": batch["sha256"], **result,
               "recovery_execution": str(repair / "execution.json")}
        save(path, row)
        save(repair / "result.json", row)
        accounting.close_topic(scope)
        return row


def settle_planner_failure(output, topic, device, *, method="full", execute=False):
    """Register retained Planner candidates while keeping the failed run intact."""
    from . import unified_benchmark as unified
    from .creative_benchmark import verify_arm
    from planner_harness.candidate_selection import recorded_choice

    output = Path(output).resolve()
    if method not in {"full", "none", "pre-experience"}:
        raise ValueError("Choose a Planner loop method")
    directory = output / "methods" / topic / method
    worker = output / "workers" / str(device)
    if not directory.resolve().is_relative_to(output) or not worker.resolve().is_relative_to(output):
        raise ValueError("Settlement paths must belong to the original run")
    with RunLock(output / "unified-owner"), RunLock(output / "batch-owner"):
        batch = load(output / "batch.json")
        if batch.get("sha256") != signature({k: v for k, v in batch.items() if k != "sha256"}):
            raise ValueError("Frozen batch changed")
        task = next(t for t in batch["topics"] if t["id"] == topic)
        path = directory / "settlement.json"
        if path.exists() and load(path).get("status") == "ready":
            return {"status": "complete", "topic": topic}
        receipt_path = output / "topics" / topic / (method + ".json")
        receipt = load(receipt_path)
        run = Path(receipt["record_directory"]).resolve()
        if not run.is_relative_to(worker):
            raise ValueError("Specify the original Planner worker")
        with RunLock(run):
            verify_arm(task, method, receipt, batch["profile_sha256"])
            state = load(run / "state.json")
            if receipt.get("outcome") != "execution_failed":
                raise ValueError("This entry settles a recorded Planner execution failure")
            selection = recorded_choice(state)
            if not selection:
                raise ValueError("No committed candidate choice is available")
            plan = {"status": "settlement_ready", "topic": topic, "method": method,
                    "batch_sha256": batch["sha256"], "native_state_sha256": sha(run / "state.json"),
                    "arm_receipt_sha256": sha(receipt_path), "selection": selection,
                    "run_outcome": "execution_failed", "planner_confirmed": False,
                    "clock": state.get("online_clock"), "model_calls": 0, "renders": 0}
            if not execute:
                return plan
            repair = directory / "failure-settlement"
            immutable(repair / "execution.json", plan)
            host = load(worker / "host.json") if (worker / "host.json").exists() else {}
            if host.get("renderer"):
                batch = {**batch, "renderer_identity": host["renderer"]}
            if host.get("local_results_root"):
                batch = {**batch, "results_root": host["local_results_root"]}

            class CachedRuntime:
                def loop(self, *args):
                    raise ValueError("The original completed arm receipt is required")

            root = Path(__file__).resolve().parents[2]
            result = unified.execute_method(root, output, task, method, batch, CachedRuntime())
            if path.exists():
                previous = load(path)
                immutable(directory / "settlement-history" / (signature(previous) + ".json"), previous)
            row = {"topic": topic, "method": method, "review_mode": unified.method_review_mode(method, batch),
                   "batch_sha256": batch["sha256"], **result,
                   "recovery_execution": str(repair / "execution.json")}
            save(path, row)
            save(repair / "result.json", row)
            return row


def recover_pe_loop(output, topic, reason):
    """Reopen settlement/dispatch only; reuse all original PE phase receipts."""
    import sqlite3
    output = Path(output).resolve()
    with RunLock(output / 'unified-owner'), RunLock(output / 'batch-owner'):
        batch = load(output / 'batch.json')
        if batch.get('sha256') != signature({k:v for k,v in batch.items() if k != 'sha256'}):
            raise ValueError('Frozen batch changed')
        task = next((t for t in batch['topics'] if t['id'] == topic), None)
        if not reason.strip() or not task or 'pe-loop' not in task.get('methods', batch['arms']):
            raise ValueError('Supply a planned PE Loop topic and recovery reason')
        directory = output / 'methods' / topic / 'pe-loop'
        if not directory.resolve().is_relative_to(output) or not (directory / 'loop.json').exists():
            raise ValueError('No original PE Loop to recover')
        path = directory / 'settlement.json'
        previous = load(path) if path.exists() else None
        if previous and previous.get('status') == 'ready':
            return {'status': 'already_ready', 'topic': topic}
        ledger = load(output / 'accounting/ledger.json')
        unresolved = [r['id'] for r in ledger['operations'].values() if r['topic'] == topic
                      and r['status'] != 'not_submitted' and not r.get('completion')]
        if unresolved:
            raise ValueError('Reconcile original external operations before PE recovery: ' + ', '.join(unresolved))
        database = output / 'device-queue.sqlite3'
        connection = sqlite3.connect(database) if database.exists() else None
        try:
            ids = (topic, topic + '__baselines')
            if connection:
                connection.execute('BEGIN IMMEDIATE')
                rows = connection.execute('SELECT id,status FROM tasks WHERE id IN (?,?)', ids).fetchall()
                if any(status == 'claimed' for _,status in rows):
                    raise ValueError('Settle or recover the existing worker claim before reopening PE')
            record = {'batch_sha256': batch['sha256'], 'topic': topic, 'reason': reason, 'at': stamp(),
                      'previous_settlement_sha256': sha(path) if previous else None,
                      'action': 'resume_original_phases', 'model_calls': 0, 'gpu_jobs': 0}
            history = directory / 'recovery-history'
            immutable(history / (f'{len(list(history.glob("*.json"))) + 1:04d}.json'), record)
            save(directory / 'recovery.json', record)
            if connection:
                connection.execute('UPDATE tasks SET status="pending",owner=NULL WHERE id IN (?,?)', ids)
                connection.commit()
            return record
        finally:
            if connection:
                connection.close()


def recover_direct(output, device, topic, reason, *, receipt=None, not_executed=False):
    output = Path(output).resolve()
    if not reason.strip() or bool(receipt) == bool(not_executed):
        raise ValueError("Supply a definite receipt OR explicit non-execution confirmation and a reason")
    batch = load(output / "batch.json")
    if topic not in {t["id"] for t in batch["topics"]}:
        raise ValueError("Unknown topic")
    service = output / "workers" / str(device)
    if not service.resolve().is_relative_to(output / "workers"):
        raise ValueError("Invalid worker")
    with RunLock(output / "batch-owner"), RunLock(service / "service-owner"):
        q = Queue(service / "queue.sqlite3")
        modern_key=topic+'__direct__0'
        jobs = [j for j in q.rows() if j["key"].startswith(topic + "/direct") or j["key"]==modern_key]
        if not jobs or any(j["state"] in {"queued", "running"} for j in jobs):
            raise ValueError("Inspect and stop the existing Direct job before recovery")
        job = jobs[-1]
        modern=job['key']==modern_key
        if modern and not_executed:
            raise ValueError('A modern signed Direct request cannot be resubmitted under its original identity; retain it and authorize a separate replacement attempt')
        folder = Path(job["payload"]["request"]).parent
        request = load(folder / "request.json")
        if request["sha256"] != signature({k:v for k,v in request.items() if k != "sha256"}):
            raise ValueError("Signed Direct request changed")
        response_path = folder / "response.json"
        def intent(record):
            settlement=output/'methods'/topic/'direct'/'settlement.json'
            value={**record,'batch_sha256':batch['sha256'],'topic':topic,
                'previous_settlement_sha256':sha(settlement) if settlement.exists() else None,'model_calls':0,'gpu_jobs':0}
            save(settlement.parent/'recovery.json',value)
        if response_path.exists() and load(response_path).get("status") == "complete":
            if modern:intent({'at':stamp(),'reason':reason,'request_sha256':request['sha256'],'action':'reuse_committed_response'})
            if job["state"] in {"failed", "needs_review"}:
                q.retry(job["id"], "Reuse committed response: " + reason)
            return {"status": "committed_response_reused", "job": job["id"]}
        response = load(receipt) if receipt else None
        if response is not None:
            if response.get("request_sha256") != request["sha256"] or response.get("mode") != "live" or response.get("status") != "complete":
                raise ValueError("Supply the completed response for this exact Direct request")
            video = response["payload"]["video"]
            if sha(video["path"]) != video["sha256"]:
                raise ValueError("Recovered video hash mismatch")
        history = folder / "recoveries"
        entry = history / f"{len(list(history.glob('*'))) + 1:04d}"
        entry.mkdir(parents=True)
        names = ["response.json"] + (["render-started.json"] if not_executed else [])
        for name in names:
            path = folder / name
            if path.exists():
                path.replace(entry / name)
        record = {"at": stamp(), "reason": reason, "request_sha256": request["sha256"],
                  "action": "confirmed_not_executed" if not_executed else "import_complete_receipt"}
        save(entry / "record.json", record)
        if response is not None:
            save(response_path, response)
        if modern:
            intent(record)
        if job["state"] in {"failed", "needs_review"}:
            q.retry(job["id"], reason)
        else:
            q.enqueue(topic + "/direct/recovery-" + str(len(jobs)), "tool", "gpu", job["payload"])
        return record
