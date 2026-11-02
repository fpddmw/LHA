"""Historical direct-provider adapters; current runs use evaluation.providers."""

import base64
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from planner_harness.integrity import IntegrityError

MODEL = "glm5.3flash"
API_MODEL = "GLM-5.3-Flash"


class ProviderHTTPError(RuntimeError):
    """Safe request diagnosis; HTTP status alone does not prove retry safety."""

    def __init__(self, provider, error, secret=None):
        import re

        self.http_status = error.code
        diagnostic = {
            "status": error.code,
            "provider": provider,
            "code": None,
            "message": None,
            "scope": "configuration_or_auth_possible"
            if error.code in {401, 403, 404}
            else "request",
            "retry_safety": "Not established by HTTP status; use bounded recovery/operator evidence",
        }

        def redact(value):
            if not isinstance(value, str):
                return None
            if secret:
                value = value.replace(secret, "[redacted]")
            value = re.sub(r'(?i)Bearer\s+[^\s,;"<>]+', "Bearer [redacted]", value)
            value = re.sub(
                r'(?i)(authorization|x-api-key|api[_ -]?key|access[_ -]?token|token|secret|password)([\s"\']*[:=][\s"\']*)[^\s"\',;}]+',
                r"\1\2[redacted]",
                value,
            )
            value = re.sub(r"\b(?:sk-ant|sk|sess)[-_][A-Za-z0-9_-]{8,}", "[redacted]", value)
            return value[:512]

        try:
            body = json.loads(error.read(32768))
            detail = body.get("error", body)
            if isinstance(detail, dict):
                diagnostic["code"] = redact(detail.get("code") or detail.get("type"))
                diagnostic["message"] = redact(detail.get("message"))
        except (ValueError, AttributeError, OSError):
            pass
        detail_text = (
            (diagnostic.get("code") or "") + " " + (diagnostic.get("message") or "")
        ).lower()
        if re.search(
            r"insufficient[_ ](?:quota|balance)|balance[_ ]insufficient|quota[_ ]exhausted|预扣费额度失败|余额不足|credit balance.*too low",
            detail_text,
        ):
            diagnostic["category"] = (
                "provider_balance_insufficient"
                if re.search(r"balance|预扣费|余额|credit", detail_text)
                else "quota_exhausted"
            )
            diagnostic["scope"] = "provider"
            diagnostic["dispatch"] = "pause_until_external_change"
        self.safe_diagnostic = diagnostic
        super().__init__(f"{provider} HTTP {error.code}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError(
            "Paratera redirected the authenticated request; verify the configured endpoint"
        )


class ParateraJudge:
    requires_live_budget = True
    model = MODEL
    reasoning_effort = None

    @staticmethod
    def budget_capabilities():
        return {
            "hard_output_tokens": True,
            "hard_invoice": False,
            "control": "chat.completions.max_tokens",
            "scope": "Provider response-token contract; provider billing remains external",
        }

    def __init__(self, *, base_url=None, timeout=600):
        self.base_url = (base_url or os.environ.get("LHA_PARATERA_BASE_URL", "")).rstrip("/")
        parsed = urllib.parse.urlsplit(self.base_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "llmapi.paratera.com"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Set the verified HTTPS API base URL on llmapi.paratera.com")
        self.api_key = os.environ.get("LHA_PARATERA_API_KEY", "")
        if not self.api_key:
            raise ValueError("Set LHA_PARATERA_API_KEY outside the repository")
        self.timeout = timeout

    @staticmethod
    def build_payload(system_prompt, user_text, image_paths, max_tokens=16384):
        from PIL import Image

        content = [{"type": "text", "text": user_text}]
        for path in image_paths:
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((960, 960))
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=90)
                encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            content.append(
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + encoded}}
            )
        # Minimal provider contract; no GPT reasoning or repair parameters.
        if max_tokens is not None and (type(max_tokens) is not int or max_tokens <= 0):
            raise ValueError("Output-token limit must be a positive integer")
        payload = {
            "model": API_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return payload

    def predict_text(self, *, system_prompt, user_text, image_paths, max_new_tokens=16384):
        payload = self.build_payload(system_prompt, user_text, image_paths, max_new_tokens)
        self.last_output_limit = {
            "requested_tokens": payload.get("max_tokens"),
            "mode": "provider_protocol_maximum"
            if max_new_tokens is None and "max_tokens" in payload
            else "provider_default"
            if max_new_tokens is None
            else "explicit_online_cap",
        }
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.build_opener(NoRedirect).open(
                request, timeout=self.timeout
            ) as response:
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            # Store no headers, request object or provider response body in error logs.
            raise ProviderHTTPError("Paratera", exc, self.api_key) from None
        except urllib.error.URLError:
            raise ConnectionError("Paratera connection error") from None
        self.last_provider_response = body
        self.last_usage = body.get("usage", {})
        actual_model = body.get("model")
        if actual_model not in {MODEL, API_MODEL}:
            raise IntegrityError(
                "Paratera reported a different model from the requested GLM-5.3-Flash"
            )
        self.last_provider_model = actual_model
        text = body["choices"][0]["message"]["content"]
        if text is None and body["choices"][0].get("finish_reason") in {"length", "max_tokens"}:
            text = ""
        if not isinstance(text, str):
            raise ValueError("Paratera returned no text response")
        self.last_usage = body.get("usage", {})
        return text


class SonnetJudge:
    requires_live_budget = True
    """Native Messages API preserves the explicitly requested high effort setting."""
    model = "sonnet-5.5high"
    api_model = "claude-sonnet-5-5"
    reasoning_effort = "high"

    @staticmethod
    def budget_capabilities():
        return {
            "hard_output_tokens": True,
            "hard_invoice": False,
            "control": "messages.max_tokens",
            "scope": "Provider response-token contract; provider billing remains external",
        }

    def __init__(self, *, base_url=None, timeout=300):
        self.base_url = (base_url or os.environ.get("LHA_SONNET_BASE_URL", "")).rstrip("/")
        parsed = urllib.parse.urlsplit(self.base_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.tu-zi.com"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Set the verified HTTPS API base URL on api.tu-zi.com")
        self.api_key = os.environ.get("LHA_SONNET_API_KEY", "")
        if not self.api_key:
            raise ValueError("Set LHA_SONNET_API_KEY outside the repository")
        self.timeout = timeout

    @staticmethod
    def build_payload(system_prompt, user_text, image_paths, max_tokens=7000):
        # Messages requires max_tokens. 128000 is the published Sonnet5.5 model
        # maximum, a protocol capacity rather than a user spending allowance.
        if max_tokens is None:
            max_tokens = 128000
        wire = ParateraJudge.build_payload(system_prompt, user_text, image_paths, max_tokens)
        content = [{"type": "text", "text": user_text}]
        for row in wire["messages"][1]["content"][1:]:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": row["image_url"]["url"].split(",", 1)[1],
                    },
                }
            )
        return {
            "model": SonnetJudge.api_model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": "high"},
        }

    def predict_text(self, *, system_prompt, user_text, image_paths, max_new_tokens=7000):
        payload = self.build_payload(system_prompt, user_text, image_paths, max_new_tokens)
        self.last_output_limit = {
            "requested_tokens": payload.get("max_tokens"),
            "mode": "provider_protocol_maximum"
            if max_new_tokens is None and "max_tokens" in payload
            else "provider_default"
            if max_new_tokens is None
            else "explicit_online_cap",
        }
        request = urllib.request.Request(
            self.base_url + "/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.build_opener(NoRedirect).open(
                request, timeout=self.timeout
            ) as response:
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            raise ProviderHTTPError("Sonnet provider", exc, self.api_key) from None
        except urllib.error.URLError:
            raise ConnectionError("Sonnet provider connection error") from None
        if body.get("model") != self.api_model:
            raise IntegrityError("Sonnet provider reported a different or missing model")
        self.last_provider_model = body["model"]
        self.last_provider_response = body
        self.last_usage = body.get("usage", {})
        return "\n".join(row["text"] for row in body["content"] if row["type"] == "text")
