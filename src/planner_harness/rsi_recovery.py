"""Reviewed same-job recovery. No new sample, seed, or hidden render retry."""
from pathlib import Path
from .common import load, save, sha, stamp
from .execution import signature
from .lock import RunLock


def recover_tool(request_path, reviewed_by, reason, *, recovered_response=None, confirmed_not_executed=False):
    request_path = Path(request_path).resolve()
    if not reviewed_by.strip() or not reason.strip():
        raise ValueError("Tool recovery needs reviewer and reason")
    with RunLock(request_path.parent / "worker"):
        job = load(request_path)
        if signature({k: v for k, v in job.items() if k != "sha256"}) != job["sha256"]:
            raise ValueError("Signed job changed")
        response_path = request_path.with_name("response.json")
        prior = load(response_path) if response_path.exists() else None
        if prior and prior.get("status") == "complete":
            raise ValueError("Completed tool output is immutable")
        if prior and prior.get("request_sha256") != job["sha256"]:
            raise ValueError("Existing response belongs to another job")
        receipt = {"request_sha256": job["sha256"], "reviewed_by": reviewed_by, "reason": reason,
                   "at": stamp(), "seed": job["payload"].get("renderer", {}).get("seed"),
                   "scope": "Same logical job; preserve the paired attempt seed and record physical recovery cost separately."}
        replacement = None
        if recovered_response:
            replacement = load(recovered_response)
            if replacement.get("request_sha256") != job["sha256"] or replacement.get("status") != "complete" or replacement.get("mode") != job["mode"]:
                raise ValueError("Recovered output must complete the exact signed job")
            receipt.update(action="accept_recovered", response_sha256=sha(recovered_response))
        elif job["kind"] == "generate":
            if not confirmed_not_executed:
                raise ValueError("An uncertain render must be reconciled; retry only after confirming it never executed")
            receipt.update(action="retry_same_job", confirmed_not_executed=True)
        else:
            receipt.update(action="resume_same_review", note="Reconcile any exhausted model call separately before resuming")
        folder = request_path.parent / "recoveries"
        number = len(list(folder.glob("*.json"))) + 1
        if prior:
            save(folder / f"{number:03d}-prior-response.json", prior)
        save(folder / f"{number:03d}-decision.json", receipt)
        started = request_path.with_name("render-started.json")
        if confirmed_not_executed and started.exists() and not replacement:
            save(folder / f"{number:03d}-prior-started.json", load(started))
            started.unlink()
        if replacement:
            save(response_path, replacement)
        elif response_path.exists():
            response_path.unlink()
        return receipt
