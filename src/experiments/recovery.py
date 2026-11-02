"""Explicit recovery of an existing Direct job; never dispatches a render."""
from pathlib import Path
from planner_harness.common import load, save, sha, stamp
from planner_harness.execution import signature, immutable
from planner_harness.lock import RunLock
from server_runtime.queue import Queue


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
