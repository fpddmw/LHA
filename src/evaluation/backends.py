"""Optional standalone OpenAI-compatible judge; no repository planner imports."""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.request

from .protocol import require


class OpenAICompatibleJudge:
    """Credentials are environment-only and are never written to judge provenance."""
    def __init__(self, *, role="benchmark_final", model=None, reasoning_effort="xhigh", timeout=1800):
        self.role = role
        self.model = model or os.environ.get("LHA_EVAL_MODEL", "gpt-6.1-sol")
        self.reasoning_effort = reasoning_effort
        self.base_url = os.environ.get("LHA_EVAL_BASE_URL", "").rstrip("/")
        self.api_key = os.environ.get("LHA_EVAL_API_KEY", "")
        self.timeout = timeout
        require(self.base_url.startswith(("https://", "http://localhost", "http://127.0.0.1")), "Configure LHA_EVAL_BASE_URL with HTTPS or a local endpoint")
        require(self.api_key, "Configure LHA_EVAL_API_KEY")

    def predict_json(self, *, system_prompt, user_text, image_paths):
        from PIL import Image
        content = [{"type": "text", "text": user_text}]
        for path in image_paths:
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((1024, 1024))
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=95)
                encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + encoded}})
        payload = {"model": self.model, "messages": [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}], "max_completion_tokens": 32768,
                   "response_format": {"type": "json_object"}}
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        request = urllib.request.Request(self.base_url + "/chat/completions",
                  data=json.dumps(payload).encode("utf-8"),
                  headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            value = json.load(response)
        answer = value["choices"][0]["message"]["content"]
        require(isinstance(answer, str), "Judge returned no text content")
        stripped = answer.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(stripped)
        require(isinstance(result, dict), "Judge must return a JSON object")
        return result
