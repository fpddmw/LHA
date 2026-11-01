"""Resource-separated execution with receipt recovery and one host owner."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import socket
import threading
import time
import uuid

from planner_harness.common import load, save, sha
from planner_harness.lock import RunLock


class Engine:
    def __init__(self, queue, directory, handler, expand, *, interval=1.0):
        self.queue, self.directory, self.handler, self.expand = queue, Path(directory), handler, expand
        self.interval = interval
        self.owner = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4()}"
        self.wakeup = threading.Event()
        self.stop = threading.Event()

    def execute(self, job):
        directory = self.directory / "jobs" / str(job["id"])
        receipt, started = directory / "receipt.json", directory / "started.json"
        try:
            if receipt.exists():
                saved = load(receipt)
                if saved["signature"] != job["signature"]:
                    raise ValueError("Receipt does not belong to queued job")
                for artifact in saved["result"].get("artifacts", []):
                    if sha(artifact["path"]) != artifact["sha256"]:
                        raise ValueError("Completed artifact changed; refusing receipt reuse")
                self.queue.finish(job, result=saved["result"])
                return
            retry = bool(job.get("error", "") and job["error"].startswith("retry authorized:"))
            if started.exists() and load(started)["signature"] != job["signature"]:
                raise ValueError("Interrupted execution signature changed")
            if started.exists() and job["resource"] != "cpu" and not retry:
                recover = getattr(self.handler, "recover", lambda *args: None)
                result = recover(job, directory)
                if result is not None:
                    save(receipt, {"signature": job["signature"], "result": result})
                    self.queue.finish(job, result=result)
                    return
                self.queue.finish(job, error="Prior external execution has no committed receipt; inspect artifacts and explicitly authorize retry",
                                  state="needs_review")
                return
            save(started, {"signature": job["signature"], "attempt": job["attempt"], "owner": job["owner"], "at": time.time()})
            result = self.handler(job, directory)
            save(receipt, {"signature": job["signature"], "result": result})
            self.queue.finish(job, result=result)
        except Exception as exc:
            self.queue.finish(job, error=f"{type(exc).__name__}: {exc}",
                              state="needs_review" if getattr(exc, "outcome_unknown", False) or getattr(exc, "failure_kind", None) == "model_transport" else "failed")
        finally:
            self.wakeup.set()

    def run(self, *, once=False):
        with RunLock(self.directory / "service-owner"):
            self.queue.recover()
            pools = {r: ThreadPoolExecutor(max_workers=n, thread_name_prefix=f"lha-{r}") for r, n in self.queue.limits.items()}
            active = {}
            fatal = None
            try:
                while True:
                    # Clear before scanning: completion between scan and wait is never lost.
                    self.wakeup.clear()
                    for future in list(active):
                        if future.done():
                            future.result()
                            del active[future]
                    for row in self.queue.pending_expansions():
                        self.expand(row)
                        self.queue.expanded(row["id"])
                    if not self.stop.is_set():
                        for resource, pool in pools.items():
                            while True:
                                job = self.queue.claim(resource, self.owner)
                                if job is None:
                                    break
                                active[pool.submit(self.execute, job)] = job["id"]
                    rows = self.queue.summary()
                    save(self.directory / "status.json", {"pid": os.getpid(), "owner": self.owner, "updated_unix": time.time(),
                         "dispatch": self.queue.dispatch(), "draining": self.stop.is_set(),
                         "limits": self.queue.limits, "jobs": rows})
                    if not active and (self.stop.is_set() or once or self.queue.dispatch() == "drain"):
                        break
                    self.wakeup.wait(self.interval)
            except BaseException as exc:
                fatal = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                for pool in pools.values():
                    pool.shutdown(wait=True)
                close = getattr(self.handler, "close", None)
                if close:
                    close()
                states = [row["state"] for row in self.queue.summary()]
                reason = "error" if fatal else "drained" if self.stop.is_set() or self.queue.dispatch() == "drain" else "blocked" if any(s != "complete" for s in states) else "idle"
                save(self.directory / "stopped.json", {"owner": self.owner, "pid": os.getpid(), "at": time.time(),
                     "reason": reason, "error": fatal, "counts": {s: states.count(s) for s in sorted(set(states))}})
