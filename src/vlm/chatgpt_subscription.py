"""Text/image Responses API through the user's explicitly authorized ChatGPT plan."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from http.client import HTTPException

from .chatgpt_auth import RESOURCE, access_token, credential_path
from .openrouter import _image_to_data_url
from pathlib import Path
from .responses_stream import events, StreamAudit, ResponseOutput, response_headers, safe_exception


class SubscriptionAPIError(RuntimeError):
    def __init__(self, status, code, *, retry_after=None):
        self.http_status = status
        self.retryable = status in {408, 429, 500, 502, 503, 504} and code not in {
            "subscription_sharing_usage_limit_exceeded",
            "subscription_sharing_usage_unavailable",
        }
        self.safe_diagnostic = {"status": status, "code": code}
        if retry_after is not None:
            self.safe_diagnostic["retry_after_seconds"] = retry_after
        self.retry_after = retry_after
        super().__init__(f"ChatGPT Responses API: HTTP {status}, {code}")


def _stream_error(detail, fallback):
    code = detail.get("code") or fallback
    if code != "server_is_overloaded" or detail.get("type") not in {None, "service_unavailable_error"}:
        return SubscriptionAPIError(422, code)
    headers = detail.get("headers") or {}
    delays = []
    if isinstance(headers, dict):
        for name, divisor in (("retry-after", 1), ("retry-after-ms", 1000)):
            value = str(headers.get(name, ""))
            if value.isascii() and value.isdecimal() and len(value) <= 12:
                delays.append(int(value) / divisor)
    return SubscriptionAPIError(503, code, retry_after=max(delays, default=None))


def _deadline_timeout(client):
    timeout = client.timeout
    binding = getattr(client, "lha_accounting_scope", None)
    if binding:
        from planner_harness import accounting
        from planner_harness.resources import TaskDeadline

        accounting.check_task(binding)
        ledger = accounting.load_ledger(binding["root"])
        task = (
            ledger.get("topics", {})
            .get(binding["topic"], {})
            .get("lanes", {})
            .get(binding.get("lane", "independent"), {})
        )
        if task.get("deadline_unix"):
            timeout = min(timeout, task["deadline_unix"] - time.time())
            if timeout <= 0:
                raise TaskDeadline("Task deadline reached before API dispatch")
    return timeout


class ChatGPTSubscriptionVisionModel:
    is_live_api = True
    requires_live_budget = False

    def __init__(
        self,
        *,
        model="openai/gpt-6.1-sol",
        reasoning_effort="high",
        role="planner",
        credential_file=None,
        relay_url=None,
        timeout=3600,
    ):
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.role = role
        self.credential_file = str(credential_path(credential_file))
        self.timeout = timeout
        self.base_url = (relay_url or RESOURCE).rstrip("/")
        self.relay_url = relay_url
        self.api_url = self.base_url + "/responses"

    @property
    def api_model(self):
        # Recovery restores self.model from the original call, not launch defaults.
        return self.model.removeprefix("openai/")

    def budget_capabilities(self):
        return {
            "hard_output_tokens": False,
            "hard_invoice": False,
            "output_limit_mode": "provider_default",
        }

    def _open(self, request, timeout):
        if self.relay_url:
            # The SSH endpoint is local; a host's outbound HTTPS proxy must not
            # capture this internal hop. The credential owner handles egress.
            return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
                request, timeout=timeout
            )
        return urllib.request.urlopen(request, timeout=timeout)

    def runtime_identity(self):
        return {
            "backend": "chatgpt_subscription",
            "endpoint": self.api_url,
            "upstream_endpoint": RESOURCE + "/responses",
            "provider_model": self.api_model,
            "protocol": "responses-sse-submission-v4",
            "reasoning_effort": self.reasoning_effort,
            "output_limit_mode": "provider_default",
            "image_transport": "original-bytes-data-url",
            "model_fallback": False,
        }

    def predict_text(self, *, system_prompt, user_text, image_paths, max_new_tokens=None):
        from planner_harness.accounting import ExternalExecutionUnknown

        self.last_usage = {}
        self.last_provider_response = {}
        self.last_finish_reason = None
        self.last_provider_model = None
        self.last_output_limit = {
            "requested_tokens": None,
            "hard_enforced": False,
            "mode": "provider_default",
        }
        content = [{"type": "input_text", "text": user_text}]
        content.extend(
            {"type": "input_image", "image_url": _image_to_data_url(Path(path))}
            for path in image_paths
        )
        body = {
            "model": self.api_model,
            "instructions": system_prompt,
            "input": [{"role": "user", "content": content}],
            "store": False,
            "stream": True,
        }
        if self.reasoning_effort:
            body["reasoning"] = {"effort": self.reasoning_effort}
        from .response_contract import apply_contract
        apply_contract(body)
        encoded = json.dumps(body, ensure_ascii=False).encode()
        self.last_client_audit = {
            **self.runtime_identity(),
            "requested_model": self.api_model,
            "request_sha256": hashlib.sha256(encoded).hexdigest(),
            "image_count": len(image_paths),
            "output_limit": self.last_output_limit,
            "request_id": uuid.uuid4().hex,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-LHA-Request-ID": self.last_client_audit["request_id"],
        }
        if not self.relay_url:
            headers["Authorization"] = "Bearer " + access_token(self.credential_file)
        request = urllib.request.Request(
            self.api_url,
            data=encoded,
            headers=headers,
        )
        started = time.monotonic()
        timeout = _deadline_timeout(self)
        audit = StreamAudit(getattr(self, "lha_audit_directory", None), self.last_client_audit)
        stage = "connect"
        try:
            with self._open(request, timeout) as response:
                stage = "read_stream"
                self.last_client_audit.update(
                    http_status=getattr(response, "status", None),
                    headers=response_headers(response),
                )
                content_type = self.last_client_audit["headers"].get("Content-Type", "")
                # Some gateways label a genuine SSE body as application/json.
                # The event framing and terminal response determine completion;
                # retain the header discrepancy as evidence, not a rejection gate.
                self.last_client_audit["content_type_mismatch"] = bool(
                    content_type and "text/event-stream" not in content_type.lower()
                )
                output = ResponseOutput()
                for event in events(response, audit):
                    output.feed(event)
                    kind = event.get("type")
                    value = event.get("response") or {}
                    if value.get("id"):
                        self.last_client_audit["response_id"] = value["id"]
                    usage = value.get("usage") or event.get("usage")
                    if isinstance(usage, dict):
                        self.last_usage = usage
                    if kind in {"response.completed", "response.incomplete", "response.failed"}:
                        self.last_provider_model = value.get("model")
                        self.last_finish_reason = {
                            "response.completed": "stop",
                            "response.incomplete": "length",
                            "response.failed": "error",
                        }[kind]
                        self.last_provider_response = value
                        self.last_client_audit["terminal_event"] = kind
                        self.last_client_audit["returned_model"] = value.get("model")
                        if kind != "response.completed":
                            detail = value.get("error") or value.get("incomplete_details") or {}
                            raise _stream_error(detail, detail.get("reason") or kind)
                        if value.get("status") != "completed":
                            stage = "invalid_terminal"
                            raise ExternalExecutionUnknown(
                                "ChatGPT completion event has no completed response status"
                            )
                        answer, selection = output.answer(value)
                        self.last_client_audit.update(selection)
                        self.last_client_audit["outcome"] = "completed"
                        return answer
                    if kind == "lha.relay.execution_unknown":
                        self.last_client_audit["relay_error"] = event.get("error")
                        raise ExternalExecutionUnknown(
                            "ChatGPT relay interrupted: " + str(event.get("stage"))
                        )
                    if kind == "error":
                        detail = event.get("error")
                        detail = detail if isinstance(detail, dict) else event
                        if isinstance(detail.get("usage"), dict):
                            self.last_usage = detail["usage"]
                        self.last_finish_reason = "error"
                        raise _stream_error(detail, "stream_error")
                    if time.monotonic() - started >= timeout:
                        stage = "deadline"
                        raise ExternalExecutionUnknown(
                            "ChatGPT stream exceeded the task deadline without a terminal response"
                        )
                stage = "eof_without_terminal"
                raise ExternalExecutionUnknown("ChatGPT stream ended without a terminal response")
        except urllib.error.HTTPError as exc:
            self.last_client_audit.update(http_status=exc.code, headers=response_headers(exc))
            raw_error = exc.read()
            audit.received(raw_error)
            try:
                detail = json.loads(raw_error).get("error") or {}
                code = detail.get("code")
            except (ValueError, AttributeError):
                detail, code = {}, None
            self.last_client_audit["provider_error_code"] = code
            if code == "relay_execution_unknown":
                self.last_client_audit.update(outcome="execution_unknown", relay_error=detail)
                raise ExternalExecutionUnknown(
                    "ChatGPT relay interrupted: " + str(detail.get("stage"))
                ) from None
            self.last_client_audit["outcome"] = "http_error"
            raise SubscriptionAPIError(exc.code, code or "http_error") from None
        except SubscriptionAPIError as exc:
            self.last_client_audit.update(outcome="provider_error", error=exc.safe_diagnostic, usage=self.last_usage)
            raise
        except ExternalExecutionUnknown as exc:
            self.last_client_audit.update(outcome="execution_unknown", error=safe_exception(exc))
            raise
        except (OSError, ValueError, HTTPException) as exc:
            if isinstance(getattr(exc, "partial", None), bytes):
                audit.received(exc.partial)
            self.last_client_audit.update(outcome="execution_unknown", error=safe_exception(exc))
            raise ExternalExecutionUnknown(
                "ChatGPT request interrupted before a terminal response ("
                + type(exc).__name__
                + "; "
                + stage
                + ")"
            ) from None
        finally:
            audit.close(stage=stage, elapsed_seconds=time.monotonic() - started)

    def predict_json(self, *, system_prompt, user_text, image_paths):
        from planner_harness.json_output import decode_object

        return decode_object(
            self.predict_text(
                system_prompt=system_prompt, user_text=user_text, image_paths=image_paths
            )
        )

    def list_models(self):
        request = urllib.request.Request(
            self.base_url + "/models",
            headers={}
            if self.relay_url
            else {"Authorization": "Bearer " + access_token(self.credential_file)},
        )
        try:
            with self._open(request, 30) as response:
                return [
                    {"slug": row["slug"], "display_name": row.get("display_name", row["slug"])}
                    for row in json.load(response).get("models", [])
                    if row.get("visibility") == "list"
                ]
        except urllib.error.HTTPError as exc:
            raise SubscriptionAPIError(exc.code, "model_catalog_unavailable") from None
