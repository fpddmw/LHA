"""Durable text response with bounded, recorded transport retries; no semantic retries."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import time

from .common import load, save, sha, stamp
from .execution import immutable
from .lock import RunLock


class ModelTransportError(RuntimeError):
    def __init__(self, message, *, retryable=True):
        super().__init__(message)
        self.retryable = retryable
        self.failure_kind = "model_transport"


def reopen_call(directory, reason, extra_attempts=1):
    """Operator recovery of the same request; no inference or semantic retry."""
    directory = Path(directory)
    if not reason.strip() or type(extra_attempts) is not int or not 1 <= extra_attempts <= 3:
        raise ValueError("Record a recovery reason and one to three additional transport attempts")
    with RunLock(directory):
        if not (directory / "input.json").exists():
            raise ValueError("There is no submitted immutable call to recover")
        if (directory / "response.txt").exists() or list((directory / "attempts").glob("*/response.txt")):
            raise ValueError("A response already exists; valid or invalid answers cannot be reinterpreted")
        attempts = [p for p in (directory / "attempts").glob("*") if p.is_dir() and p.name.isdigit()]
        if not attempts:
            raise ValueError("No transport attempt has been recorded")
        last = max(int(p.name) for p in attempts)
        policy = {"first": last + 1, "last": last + extra_attempts}
        history = directory / "recoveries"
        entry = history / f"{len(list(history.glob('*.json'))) + 1:04d}.json"
        immutable(entry, {"at": stamp(), "reason": reason, "input_sha256": sha(directory / "input.json"),
                          "previous": load(directory / "allowance.json") if (directory / "allowance.json").exists() else None,
                          "next": policy, "note": "Interrupted provider calls may have incurred cost; previous attempts are retained."})
        save(directory / "allowance.json", policy)
        return policy


def write_text_atomic(path, text):
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def transient(exc):
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    text = str(exc).lower()
    if any(x in text for x in ("unauthorized", "forbidden", "quota", "invalid_api_key", "unsupported")):
        return False
    return any(x in text for x in ("timed out", "timeout", "connection reset", "connection error",
                                   "stream disconnected", "unexpected eof", "502", "503", "504", "429",
                                   "workspace routing discovery failed", "error sending request", "rate limit"))


def call_text(directory, model, system, user, images, *, attempts=3, retry_delay=2):
    directory = Path(directory)
    with RunLock(directory):
        binding = {"system_prompt": system, "user_text": user,
                   "images": [{"path": str(p), "sha256": sha(p)} for p in images],
                   "model": model.model, "reasoning_effort": getattr(model, "reasoning_effort", None)}
        immutable(directory / "input.json", binding)
        raw_path = directory / "response.txt"
        if raw_path.exists():
            return raw_path.read_text(encoding="utf-8")
        policy_path = directory / "allowance.json"
        if not policy_path.exists():
            immutable(policy_path, {"first": 1, "last": attempts})
        policy = load(policy_path)
        # Clone only transport controls. Never change the shared model instance.
        client = copy.copy(model)
        for key in ("attempts", "max_retries"):
            if hasattr(client, key):
                setattr(client, key, 1 if key == "attempts" else 0)
        for number in range(policy["first"], policy["last"] + 1):
            entry = directory / "attempts" / f"{number:02d}"
            if (entry / "response.txt").exists():
                raw = (entry / "response.txt").read_text(encoding="utf-8")
                write_text_atomic(raw_path, raw)
                return raw
            if (entry / "failed.json").exists():
                if not load(entry / "failed.json")["retryable"]:
                    raise ModelTransportError("Recorded permanent model failure; explicit recovery is required", retryable=False)
                continue
            if (entry / "submitted.json").exists():
                # A process interruption may have lost a response. LLM retries are
                # allowed, unlike renders, but consume the same finite attempt budget.
                save(entry / "failed.json", {"type": "InterruptedTransport", "retryable": True,
                                             "outcome": "unknown; retry may duplicate provider cost"})
                continue
            save(entry / "submitted.json", {"at": stamp(), "logical_call": str(directory), "attempt": number})
            try:
                raw = client.predict_text(system_prompt=system, user_text=user,
                                          image_paths=images, max_new_tokens=7000)
                if not isinstance(raw, str):
                    raise ValueError("Model did not return text")
            except Exception as exc:
                retryable = transient(exc)
                # Do not persist provider error bodies that can contain credentials.
                save(entry / "failed.json", {"type": type(exc).__name__, "retryable": retryable})
                if not retryable or number == policy["last"]:
                    raise ModelTransportError("Model transport failed; inspect recorded attempt status", retryable=retryable) from None
                time.sleep(retry_delay * number)
                continue
            write_text_atomic(entry / "response.txt", raw)
            write_text_atomic(raw_path, raw)
            save(directory / "returned.json", {"attempt": number, "at": stamp(), "sha256": sha(raw_path),
                                                "usage": getattr(client, "last_usage", {})})
            return raw
        raise ModelTransportError("Recorded transport retry budget exhausted; explicitly reopen the same call")
