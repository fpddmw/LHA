"""Bounded recorded response attempts; accepted tool effects execute separately once."""
from __future__ import annotations
import copy
from pathlib import Path
import time
from .common import load, save, sha, stamp
from .ledger import digest


def _accept(directory, raw, attempt):
    temporary = directory / "response.part"
    temporary.write_text(raw, encoding="utf-8")
    temporary.replace(directory / "response.txt")
    save(directory / "returned.json", {"response_sha256": sha(directory / "response.txt"), "attempt": attempt, "at": stamp()})


def reconcile(directory, action, reason, reviewed_by, *, response=None, extra_attempts=1):
    from .lock import RunLock
    with RunLock(Path(directory) / "call-owner"):
        return _reconcile(directory, action, reason, reviewed_by, response=response, extra_attempts=extra_attempts)


def _reconcile(directory, action, reason, reviewed_by, *, response=None, extra_attempts=1):
    """Resolve old/exhausted calls without deleting their evidence. Caller owns the run lock."""
    directory = Path(directory)
    request = load(directory / "single-call.json")
    if not reason.strip() or not reviewed_by.strip():
        raise ValueError("Reconciliation requires a reason and reviewer")
    if (directory / "response.txt").exists():
        raise ValueError("This call already has an accepted response")
    row = {"request_sha256": request["sha256"], "action": action, "reason": reason, "reviewed_by": reviewed_by, "at": stamp()}
    if action == "accept":
        if not response or not Path(response).read_text(encoding="utf-8").strip():
            raise ValueError("Provide the recovered provider response")
        raw = Path(response).read_text(encoding="utf-8")
        row["recovered_response_sha256"] = sha(response)
    elif action == "retry":
        if type(extra_attempts) is not int or not 1 <= extra_attempts <= 3:
            raise ValueError("Authorize one to three additional response attempts")
        row["extra_attempts"] = extra_attempts
    elif action != "abandon":
        raise ValueError("Use accept, retry or abandon")
    history = load(directory / "reconciliations.json") if (directory / "reconciliations.json").exists() else []
    history.append(row)
    save(directory / "reconciliations.json", history)
    if action == "accept":
        _accept(directory, raw, "operator_recovered")
    return row


def call_once(directory, model, system, user, images=(), max_tokens=7000, *, retry_policy=None):
    from .lock import RunLock
    with RunLock(Path(directory) / "call-owner"):
        return _call_once(directory, model, system, user, images, max_tokens, retry_policy=retry_policy)


def _call_once(directory, model, system, user, images=(), max_tokens=7000, *, retry_policy=None):
    """Accept one response; retry new response-only calls under a frozen finite budget.

    Legacy uncertain submissions require reconciliation. This never executes tools or
    renderers and never mutates the caller's shared model configuration.
    """
    directory = Path(directory)
    policy = retry_policy or getattr(model, "rsi_retry_policy", None) or {"max_attempts": 3, "backoff_seconds": 2}
    if set(policy) != {"max_attempts", "backoff_seconds"} or type(policy["max_attempts"]) is not int or not 1 <= policy["max_attempts"] <= 5:
        raise ValueError("Freeze one to five response attempts")
    if type(policy["backoff_seconds"]) not in {int, float} or not 0 <= policy["backoff_seconds"] <= 60:
        raise ValueError("Retry backoff must be between zero and sixty seconds")
    packet = {"system_prompt": system, "user_text": user,
              "images": [{"path": str(p), "sha256": sha(p)} for p in images],
              "model": getattr(model, "model", type(model).__name__),
              "reasoning_effort": getattr(model, "reasoning_effort", "unknown"), "max_new_tokens": max_tokens}
    fingerprint = digest(packet)
    request, response, marker = directory / "single-call.json", directory / "response.txt", directory / "submitted.json"
    if request.exists():
        frozen = load(request)
        if frozen["sha256"] != fingerprint:
            raise ValueError("Frozen model call changed")
        if frozen.get("retry_policy") and frozen["retry_policy"] != policy:
            raise ValueError("Frozen response retry policy changed")
    else:
        if response.exists():
            raise ValueError("Response has no call provenance")
        frozen = {"sha256": fingerprint, "packet": packet, "version": 2, "retry_policy": policy}
        save(request, frozen)
    if response.exists():
        if (directory / "returned.json").exists() and load(directory / "returned.json")["response_sha256"] != sha(response):
            raise ValueError("Accepted response changed")
        return response.read_text(encoding="utf-8")
    reconciliations = load(directory / "reconciliations.json") if (directory / "reconciliations.json").exists() else []
    if reconciliations and reconciliations[-1]["action"] == "abandon":
        raise RuntimeError("Response call was explicitly abandoned")
    additional = sum(r.get("extra_attempts", 0) for r in reconciliations if r["request_sha256"] == fingerprint)
    legacy = frozen.get("version", 1) < 2
    if legacy and marker.exists() and not additional:
        raise RuntimeError("Uncertain legacy model call: reconcile the recorded submission before retrying")
    existing = sorted((directory / "attempts").glob("*/submitted.json"))
    for p in existing:
        returned = p.with_name("response.txt")
        if returned.exists():
            raw = returned.read_text(encoding="utf-8")
            _accept(directory, raw, p.parent.name)
            return raw
    limit = (0 if legacy and marker.exists() else policy["max_attempts"]) + additional
    if len(existing) >= limit:
        raise RuntimeError("Response retry budget exhausted; reconcile or quarantine this task")
    client = copy.copy(model) if any(hasattr(model, k) for k in ("attempts", "retries")) else model
    for field in ("attempts", "retries"):
        if hasattr(client, field):
            setattr(client, field, 1)
    last = None
    for number in range(len(existing) + 1, limit + 1):
        attempt = directory / "attempts" / f"{number:03d}"
        submitted = {"sha256": fingerprint, "at": stamp(), "attempt": number, "status": "submitted_outcome_unknown"}
        save(attempt / "submitted.json", submitted)
        save(marker, {**submitted, "version": 2})
        try:
            raw = client.predict_text(system_prompt=system, user_text=user, image_paths=list(images), max_new_tokens=max_tokens)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("Provider returned no text")
            (attempt / "response.txt").write_text(raw, encoding="utf-8")
            _accept(directory, raw, number)
            return raw
        except Exception as exc:
            last = exc
            # Provider errors can contain credentials; retain the exception type only.
            save(attempt / "error.json", {"at": stamp(), "type": type(exc).__name__, "provider_outcome": "unknown"})
            if number < limit:
                time.sleep(policy["backoff_seconds"])
    raise RuntimeError("Response retry budget exhausted; recorded attempts need reconciliation") from last
