"""Durable text response with bounded, recorded transport retries; no semantic retries."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import time

from .common import load, save, sha, stamp
from .execution import immutable
from .lock import RunLock


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
                                   "stream disconnected", "unexpected eof", "502", "503", "504"))


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
        # Clone only transport controls. Never change the shared model instance.
        client = copy.copy(model)
        for key in ("attempts", "max_retries"):
            if hasattr(client, key):
                setattr(client, key, 1 if key == "attempts" else 0)
        for number in range(1, attempts + 1):
            entry = directory / "attempts" / f"{number:02d}"
            if (entry / "response.txt").exists():
                raw = (entry / "response.txt").read_text(encoding="utf-8")
                write_text_atomic(raw_path, raw)
                return raw
            if (entry / "failed.json").exists():
                if not load(entry / "failed.json")["retryable"]:
                    raise RuntimeError("Recorded permanent model failure; no automatic replay")
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
                if not retryable or number == attempts:
                    raise RuntimeError("Model transport failed; inspect recorded attempt status") from None
                time.sleep(retry_delay * number)
                continue
            write_text_atomic(entry / "response.txt", raw)
            write_text_atomic(raw_path, raw)
            save(directory / "returned.json", {"attempt": number, "at": stamp(), "sha256": sha(raw_path),
                                                "usage": getattr(client, "last_usage", {})})
            return raw
        raise RuntimeError("Recorded transport retry budget exhausted; no new call submitted")
