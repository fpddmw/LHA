"""Independent judge configuration and construction, separate from online review."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from vlm.openrouter import OpenRouterVisionModel
from vlm.settings import load_credentials

CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs/evaluation.json"


def configuration():
    """Return the exact declared judging configuration, with no credentials."""
    rows = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["judges"]
    if not rows or len({row["model"] for row in rows}) != len(rows):
        raise ValueError("Independent judge names must be nonempty and unique")
    for row in rows:
        if row.get("provider") != "openrouter" or not row.get("provider_model"):
            raise ValueError("Declare an OpenRouter provider model for each judge")
    return copy.deepcopy(rows)


JUDGES = tuple(row["model"] for row in configuration())
MODEL = JUDGES[0]


def judge_spec(name):
    for row in configuration():
        if row["model"] == name:
            return row
    raise ValueError("Unknown independent judge: " + name)


def judge_identity(name):
    spec = judge_spec(name)
    return {key: spec[key] for key in ("model", "provider", "provider_model", "reasoning_effort")}


class OpenRouterJudge(OpenRouterVisionModel):
    """Keep report slot names while sending canonical API model identifiers."""

    def __init__(self, name=MODEL, **options):
        spec = judge_spec(name)
        load_credentials(options.get("credential_file"))
        options.setdefault("api_key_env", spec.get("api_key_env", "OPENROUTER_API_KEY"))
        endpoint = os.environ.get(spec.get("base_url_env", "OPENROUTER_BASE_URL"))
        if endpoint:
            options.setdefault("base_url", endpoint)
        options.setdefault("max_tokens", spec.get("max_output_tokens"))
        super().__init__(
            model=spec["provider_model"],
            reasoning_effort=spec["reasoning_effort"],
            role="benchmark_final",
            **options,
        )
        self.api_model = spec["provider_model"]
        self.model = name


def make_judge(name):
    return OpenRouterJudge(name)
