"""Loopback Responses relay: one credential owner for multiple SSH-connected hosts."""

from __future__ import annotations

from http.client import HTTPException, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import re
import ssl
import time
import urllib.error
import urllib.request
import uuid

from .chatgpt_auth import RESOURCE, access_token, credential_path
from .responses_stream import StreamAudit, response_headers, safe_exception


class UpstreamHandshakeFailed(OSError):
    """TLS connection setup failed before sending the Responses request."""


def open_upstream(request, timeout):
    deadline = time.monotonic() + timeout

    class Connection(HTTPSConnection):
        def connect(self):
            for attempt in (1, 2):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise UpstreamHandshakeFailed("TLS setup exhausted the request timeout")
                self.timeout = remaining
                try:
                    # Includes TCP, optional proxy CONNECT, and TLS handshake.
                    # HTTPConnection.send writes the Responses request only
                    # after this method returns successfully.
                    return super().connect()
                except ssl.SSLEOFError as exc:
                    self.close()
                    request.lha_connect_failures.append(safe_exception(exc))
                    if attempt == 2:
                        raise UpstreamHandshakeFailed("TLS setup ended before sending the request") from exc

    class Handler(urllib.request.HTTPSHandler):
        def https_open(self, req):
            if req is not request:
                return super().https_open(req)
            return self.do_open(Connection, req, context=self._context)

    request.lha_connect_failures = []
    return urllib.request.build_opener(Handler()).open(request, timeout=timeout)


def make_server(port, credential_file=None, timeout=3600, audit_dir=None):
    audit_root = (
        Path(audit_dir)
        if audit_dir
        else credential_path(credential_file).parent / "subscription-relay-audit"
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            self.forward()

        def do_POST(self):
            self.forward()

        def forward(self):
            if (self.command, self.path) not in {("GET", "/models"), ("POST", "/responses")}:
                self.send_error(404)
                return
            incoming_id = self.headers.get("X-LHA-Request-ID", "")
            self.request_id = (
                incoming_id if re.fullmatch(r"[a-f0-9]{32}", incoming_id) else uuid.uuid4().hex
            )
            # A separate relay attempt ID keeps evidence even if a caller repeats
            # its correlation ID; the relay itself never resubmits a POST.
            self.relay_id = uuid.uuid4().hex
            if self.command == "POST":
                try:
                    length = int(self.headers["Content-Length"])
                    if length < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    self.send_error(411)
                    return
                body = self.rfile.read(length)
                if len(body) != length:
                    return
            else:
                body = None
            metadata = {
                "request_id": self.request_id,
                "relay_id": self.relay_id,
                "method": self.command,
                "path": self.path,
                "request_bytes": len(body or b""),
                "request_sha256": hashlib.sha256(body or b"").hexdigest(),
            }
            audit = StreamAudit(audit_root / self.request_id / self.relay_id, metadata)
            sent_headers = False
            stage = "authorization"
            token = ""
            try:
                try:
                    token = access_token(credential_file)
                except Exception as exc:
                    metadata.update(outcome="authorization_error", error=safe_exception(exc))
                    self.reply_error(401, "subscription_authorization_unavailable")
                    return
                request = urllib.request.Request(
                    RESOURCE + self.path,
                    data=body,
                    method=self.command,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream" if body is not None else "application/json",
                        "X-Client-Request-ID": self.request_id,
                    },
                )
                stage = "upstream_connect"
                with open_upstream(request, timeout) as response:
                    metadata.update(http_status=response.status, headers=response_headers(response))
                    stage = "downstream_headers"
                    self.send_response(response.status)
                    self.send_header(
                        "Content-Type", response.headers.get("Content-Type", "application/json")
                    )
                    self.send_header("X-LHA-Request-ID", self.request_id)
                    self.send_header("X-LHA-Relay-ID", self.relay_id)
                    if response.headers.get("X-Request-ID"):
                        self.send_header("X-Request-ID", response.headers["X-Request-ID"])
                    self.send_header("Connection", "close")
                    self.end_headers()
                    sent_headers = True
                    self.close_connection = True
                    while True:
                        stage = "upstream_read"
                        chunk = response.read1(65536)
                        if not chunk:
                            break
                        audit.received(chunk)
                        stage = "downstream_write"
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    stage = "upstream_eof"
                    audit.finish_events()
                    metadata["outcome"] = (
                        "terminal_received"
                        if metadata.get("terminal_event")
                        else "eof_without_terminal"
                        if body is not None
                        else "complete"
                    )
                    if body is not None and not metadata.get("terminal_event"):
                        self.reply_unknown(
                            sent_headers,
                            stage,
                            {
                                "type": "EOF",
                                "message": "Upstream ended without a terminal response",
                            },
                        )
            except urllib.error.HTTPError as exc:
                metadata.update(http_status=exc.code, headers=response_headers(exc))
                try:
                    raw_error = exc.read()
                    audit.received(raw_error)
                    code = (json.loads(raw_error).get("error") or {}).get("code")
                except (ValueError, AttributeError):
                    code = None
                metadata.update(outcome="upstream_http_error", provider_error_code=code)
                self.reply_error(exc.code, code or "upstream_http_error")
            except (OSError, ValueError, HTTPException) as exc:
                if isinstance(getattr(exc, "partial", None), bytes):
                    audit.received(exc.partial)
                error = safe_exception(exc, secrets=(token,))
                predispatch = isinstance(getattr(exc, "reason", exc), UpstreamHandshakeFailed)
                if predispatch:
                    stage = "upstream_tls_setup"
                metadata.update(outcome="transport_error", failure_stage=stage, error=error)
                if not stage.startswith("downstream_"):
                    try:
                        if predispatch and not sent_headers:
                            metadata["outcome"] = "not_submitted"
                            self.reply_error(502, "relay_tls_not_submitted", stage=stage, upstream_error=error)
                        elif self.command == "POST":
                            self.reply_unknown(sent_headers, stage, error)
                        elif not sent_headers:
                            self.reply_error(502, "model_catalog_unavailable")
                    except (OSError, HTTPException) as downstream:
                        metadata["downstream_error"] = safe_exception(downstream)
                self.close_connection = True
            finally:
                failures = getattr(locals().get("request"), "lha_connect_failures", [])
                if failures:
                    metadata["upstream_tls_failures"] = failures
                audit.close(stage=stage)

        def reply_unknown(self, sent_headers, stage, error):
            if not sent_headers:
                self.reply_error(502, "relay_execution_unknown", stage=stage, upstream_error=error)
            else:
                event = {
                    "type": "lha.relay.execution_unknown",
                    "request_id": self.request_id,
                    "relay_id": self.relay_id,
                    "stage": stage,
                    "error": error,
                }
                self.wfile.write(b"\n\ndata: " + json.dumps(event).encode() + b"\n\n")
                self.wfile.flush()
            self.close_connection = True

        def reply_error(self, status, code, **detail):
            body = json.dumps({"error": {"code": code, **detail}}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-LHA-Request-ID", self.request_id)
            self.send_header("X-LHA-Relay-ID", self.relay_id)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
