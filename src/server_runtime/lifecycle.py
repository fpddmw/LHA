"""Cooperative, identity-bound drain/exit; no process signals or PID heuristics."""
import os
from pathlib import Path
import time

from planner_harness.common import load, save
from planner_harness.execution import immutable
from planner_harness.lock import RunLock


def process_identity(owner, *, proc_root=Path("/proc")):
    proc_root = Path(proc_root)
    identity = {"pid": os.getpid(), "owner": owner}
    if (proc_root / str(os.getpid()) / "stat").exists():
        stat = (proc_root / str(os.getpid()) / "stat").read_text().rsplit(")", 1)[1].split()
        identity.update(start_ticks=stat[19], boot_id=(proc_root / "sys/kernel/random/boot_id").read_text().strip())
    return identity


def request_exit(directory, queue, expected_identity):
    directory = Path(directory)
    with RunLock(directory / "lifecycle-control"):
        current = load(directory / "worker-lifecycle.json")
        if current["identity"] != expected_identity:
            raise ValueError("Worker identity/start identifier changed; no drain was requested")
        target = directory / "lifecycle" / current["generation"] / "drain-request.json"
        if not target.exists():
            immutable(target, {"identity": expected_identity, "at_unix": time.time(),
                               "action": "stop accepting work; finish active calls and retain queued tasks"})
        queue.dispatch("drain")
        return load(target)


def verify_exit(directory, queue, expected_identity):
    directory = Path(directory)
    current = load(directory / "worker-lifecycle.json")
    if current["identity"] != expected_identity:
        raise ValueError("Worker identity changed")
    stopped = directory / "lifecycle" / current["generation"] / "exited.json"
    if not stopped.exists():
        return {"status": "draining", "identity": expected_identity}
    receipt = load(stopped)
    if receipt["identity"] != expected_identity or receipt.get("active_jobs") != 0 or receipt.get("reason") != "drained":
        raise ValueError("Worker has no clean matching drain/exit receipt")
    rows = queue.rows()
    if any(r["state"] == "running" for r in rows):
        raise ValueError("Queue still records active work")
    return {"status": "exited", "receipt": receipt,
            "scope": "Engine loop drained and handler close returned; this is not an assertion that the OS process exited.",
            "retained_jobs": [{"id":r["id"], "state":r["state"]} for r in rows if r["state"] != "complete"]}
