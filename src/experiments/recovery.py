"""Explicit recovery of an existing Direct job; never dispatches a render."""
from pathlib import Path
from planner_harness.common import load, save, sha, stamp
from planner_harness.execution import signature
from planner_harness.lock import RunLock
from server_runtime.queue import Queue


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
        jobs = [j for j in q.rows() if j["key"].startswith(topic + "/direct")]
        if not jobs or any(j["state"] in {"queued", "running"} for j in jobs):
            raise ValueError("Inspect and stop the existing Direct job before recovery")
        job = jobs[-1]
        folder = Path(job["payload"]["request"]).parent
        request = load(folder / "request.json")
        if request["sha256"] != signature({k:v for k,v in request.items() if k != "sha256"}):
            raise ValueError("Signed Direct request changed")
        response_path = folder / "response.json"
        if response_path.exists() and load(response_path).get("status") == "complete":
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
        if job["state"] in {"failed", "needs_review"}:
            q.retry(job["id"], reason)
        else:
            q.enqueue(topic + "/direct/recovery-" + str(len(jobs)), "tool", "gpu", job["payload"])
        return record
