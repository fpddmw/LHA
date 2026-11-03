"""Responses message selection and per-request, credential-free stream evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import time

TERMINAL_EVENTS = {"response.completed", "response.incomplete", "response.failed", "error"}


def final_answer(response):
    """Select one answer message, never concatenate separate assistant turns.

    Phase is optional in Responses. Older providers' unphased messages use the
    last-message convention; explicit commentary is never an answer fallback.
    """
    messages = [
        item
        for item in response.get("output", [])
        if item.get("type") == "message" and item.get("role", "assistant") == "assistant"
    ]
    finals = [item for item in messages if item.get("phase") == "final_answer"]
    unphased = [item for item in messages if item.get("phase") is None]
    selected = (finals or unphased or [None])[-1]
    text = (
        ""
        if selected is None
        else "".join(
            part.get("text", "")
            for part in selected.get("content", [])
            if part.get("type") == "output_text"
        )
    )
    return text, {
        "selection": "final_answer" if finals else "last_unphased" if unphased else "no_answer",
        "selected_message_id": selected.get("id") if selected else None,
        "messages": [{"id": item.get("id"), "phase": item.get("phase")} for item in messages],
    }


def safe_exception(exc, secrets=()):
    # Never persist request objects/headers; keep the useful OS/TLS failure text.
    message = str(exc)
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[redacted]")
    message = re.sub(r"(?i)Bearer\s+\S+", "Bearer [redacted]", message)
    message = re.sub(r"\b(?:sk-[\w-]+|eyJ[\w.-]{20,})\b", "[redacted]", message)
    return {
        "type": type(exc).__name__,
        "errno": getattr(exc, "errno", None),
        "message": message[:2000],
    }


def response_headers(response):
    headers = getattr(response, "headers", {})
    return {
        key: headers.get(key)
        for key in (
            "Content-Type",
            "Content-Length",
            "X-Request-ID",
            "X-LHA-Request-ID",
            "X-LHA-Relay-ID",
            "OpenAI-Processing-Ms",
        )
        if headers.get(key) is not None
    }


class EventDecoder:
    def __init__(self):
        self.buffer = b""
        self.data = []

    def line(self, raw):
        line = raw.decode("utf-8").rstrip("\r")
        if line.startswith("data:"):
            self.data.append(line[5:].lstrip(" "))
        elif not line and self.data:
            value = "\n".join(self.data)
            self.data = []
            if value != "[DONE]":
                event = json.loads(value)
                if not isinstance(event, dict):
                    raise ValueError("SSE data must be a JSON object")
                return event
        return None

    def feed(self, chunk):
        self.buffer += chunk
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            event = self.line(line)
            if event is not None:
                yield event

    def finish(self):
        if self.buffer:
            event = self.line(self.buffer)
            self.buffer = b""
            if event is not None:
                yield event
        event = self.line(b"")
        if event is not None:
            yield event


class StreamAudit:
    """Persist received bytes before interpretation, with small searchable metadata.

    An unavailable diagnostics disk is reported in memory, not allowed to turn a
    completed model answer into a failed experiment.
    """

    def __init__(self, directory, metadata):
        self.directory = Path(directory) if directory else None
        self.metadata = metadata
        self.digest = hashlib.sha256()
        self.raw = None
        self.decoder = EventDecoder()
        self.last_saved = 0.0
        self.metadata.update(
            started_unix=time.time(), received_bytes=0, event_count=0, event_types={}
        )
        if self.directory:
            try:
                self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
                self.raw = (self.directory / "stream.bin").open("wb")
                self.metadata["audit_directory"] = str(self.directory)
            except OSError as exc:
                self.metadata["audit_write_error"] = safe_exception(exc)
        self.save()

    def save(self, name="summary.json", value=None):
        if self.directory:
            try:
                path = self.directory / name
                temporary = path.with_suffix(path.suffix + ".tmp")
                temporary.write_text(
                    json.dumps(
                        self.metadata if value is None else value, ensure_ascii=False, indent=2
                    ),
                    encoding="utf-8",
                )
                temporary.replace(path)
                self.last_saved = time.monotonic()
            except OSError as exc:
                self.metadata["audit_write_error"] = safe_exception(exc)

    def received(self, chunk):
        self.digest.update(chunk)
        self.metadata["received_bytes"] += len(chunk)
        self.metadata["stream_sha256"] = self.digest.hexdigest()
        if self.raw:
            try:
                self.raw.write(chunk)
                self.raw.flush()
            except OSError as exc:
                self.metadata["audit_write_error"] = safe_exception(exc)
        # Diagnostics must not prevent a relay from forwarding the original bytes.
        try:
            for event in self.decoder.feed(chunk):
                self.event(event)
        except ValueError as exc:
            self.metadata["event_parse_error"] = safe_exception(exc)
        if time.monotonic() - self.last_saved >= 1 or self.metadata.get("terminal_event"):
            self.save()

    def event(self, event):
        kind = event.get("type", "unknown")
        self.metadata["event_count"] += 1
        self.metadata["event_types"][kind] = self.metadata["event_types"].get(kind, 0) + 1
        self.metadata["last_event"] = kind
        response = event.get("response") or {}
        if response.get("id"):
            self.metadata["response_id"] = response["id"]
        if kind in TERMINAL_EVENTS:
            self.metadata["terminal_event"] = kind
            self.save("response.json", response)

    def finish_events(self):
        try:
            for event in self.decoder.finish():
                self.event(event)
        except ValueError as exc:
            self.metadata["event_parse_error"] = safe_exception(exc)

    def close(self, **values):
        self.finish_events()
        self.metadata.update(finished_unix=time.time(), **values)
        self.save()
        if self.raw:
            try:
                self.raw.close()
            except OSError as exc:
                self.metadata["audit_write_error"] = safe_exception(exc)


def events(stream, audit=None):
    decoder = EventDecoder()
    for raw in stream:
        if audit:
            audit.received(raw)
        yield from decoder.feed(raw)
    yield from decoder.finish()
