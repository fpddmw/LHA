"""Independent creative-loop judging through Paratera; never a Planner tool."""
from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from planner_harness.common import load, save, sha
from planner_harness.execution import immutable
from planner_harness.model_call import call_text
from critic_harness.one_shot import frozen_profile, prepare_request, validate_report

MODEL = "glm5.3flash"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Paratera redirected the authenticated request; verify the configured endpoint")


class ParateraJudge:
    model = MODEL
    reasoning_effort = None

    def __init__(self, *, base_url=None, timeout=300):
        self.base_url = (base_url or os.environ.get("LHA_PARATERA_BASE_URL", "")).rstrip("/")
        parsed = urllib.parse.urlsplit(self.base_url)
        if parsed.scheme != "https" or parsed.hostname != "llmapi.paratera.com" or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Set the verified HTTPS API base URL on llmapi.paratera.com")
        self.api_key = os.environ.get("LHA_PARATERA_API_KEY", "")
        if not self.api_key:
            raise ValueError("Set LHA_PARATERA_API_KEY outside the repository")
        self.timeout = timeout

    @staticmethod
    def build_payload(system_prompt, user_text, image_paths, max_tokens=7000):
        from PIL import Image
        content = [{"type": "text", "text": user_text}]
        for path in image_paths:
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((960, 960))
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=90)
                encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + encoded}})
        # Minimal compatible wire contract. Endpoint/model capabilities remain unverified
        # until the user resumes live experiments; no GPT reasoning or repair parameters.
        return {"model": MODEL, "messages": [{"role": "system", "content": system_prompt},
                {"role": "user", "content": content}], "max_tokens": max_tokens}

    def predict_text(self, *, system_prompt, user_text, image_paths, max_new_tokens=7000):
        payload = self.build_payload(system_prompt, user_text, image_paths, max_new_tokens)
        request = urllib.request.Request(self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"})
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=self.timeout) as response:
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            # Store no headers, request object or provider response body in error logs.
            raise RuntimeError(f"Paratera HTTP {exc.code}") from None
        except urllib.error.URLError:
            raise ConnectionError("Paratera connection error") from None
        text = body["choices"][0]["message"]["content"]
        if not isinstance(text, str):
            raise ValueError("Paratera returned no text response")
        self.last_usage = body.get("usage", {})
        return text


def prepare_final_request(request, source, candidate, directory):
    """No arm, iteration, Planner notes, online scores or supplemental checks accepted."""
    return prepare_request(request, "candidate", {"source": source, "candidate": candidate},
                           Path(directory) / "evidence", frozen_profile())


def judge_candidate(request, source, candidate, directory, *, model=None):
    directory = Path(directory)
    client = model or ParateraJudge()
    if client.model != MODEL or getattr(client, "reasoning_effort", None) is not None:
        raise ValueError("Independent creative judge is fixed to glm5.3flash without GPT reasoning options")
    packet, images = prepare_final_request(request, source, candidate, directory)
    raw = call_text(directory / "call", client, packet["system_prompt"], packet["user_text"], images)
    stripped = raw.strip()
    if stripped.startswith("```json\n") and stripped.endswith("```"):
        stripped = stripped[8:-3].strip()
    try:
        report = validate_report(json.loads(stripped), packet)
    except (ValueError, TypeError, KeyError) as exc:
        save(directory / "invalid-report.json", {"error": str(exc), "semantic_retry": False})
        raise
    result = {"usage": "independent_final", "model": MODEL, "reasoning_effort": None,
              "source_sha256": source["sha256"], "output_sha256": candidate["sha256"],
              "profile_sha256": packet["profile_sha256"], "report": report,
              "request_path": str(directory / "evidence/request.json")}
    immutable(directory / "judgment.json", result)
    return result


def paired_summary(pairs):
    """Summarize valid per-dimension pairs; missing scores never become zeros."""
    from critic_harness.one_shot import DIMENSIONS
    result = {}
    for key in DIMENSIONS:
        deltas = [b["main_scores"][key]["score"] - a["main_scores"][key]["score"] for a, b in pairs
                  if a["main_scores"][key]["status"] == b["main_scores"][key]["status"] == "scored"]
        result[key] = {"planned": len(pairs), "valid": len(deltas), "missing": len(pairs) - len(deltas),
                       "mean_delta": sum(deltas) / len(deltas) if deltas else None,
                       "improved": sum(d > 0 for d in deltas), "tied": deltas.count(0),
                       "worsened": sum(d < 0 for d in deltas)}
    return result
