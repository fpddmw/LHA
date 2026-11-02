"""Shared API defaults, external credentials and per-role configuration.

Configuration precedence: factory options, role section, top-level configuration,
role environment, shared environment, built-in defaults. An explicit None effort
is preserved. Credentials are read only when a client/settings resolver is used.
"""

from __future__ import annotations

import os
from pathlib import Path
import re

DEFAULT_MODEL = "openai/gpt-6.1-sol"
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_ENV_FILE = "~/.config/lha/openrouter.env"

_ENV_KEYS = {
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_MODEL",
    "OPENROUTER_REASONING_EFFORT",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
}


def load_credentials(path=None):
    """Load an external env file; already exported process values take priority."""
    target = Path(path or os.environ.get("LHA_API_ENV_FILE", DEFAULT_ENV_FILE)).expanduser()
    if not target.is_file():
        return
    for line in target.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.strip().partition("=")
        role_key = re.fullmatch(r"LHA_API_[A-Z_]+_(?:MODEL|REASONING_EFFORT)", key)
        if separator and (key in _ENV_KEYS or role_key):
            os.environ.setdefault(key, value.strip().strip("\"'"))


def role_settings(config, role):
    """Resolve the same model identity used by the runtime API client."""
    options = config.get("models", {}).get(role, {}).get("options", {})
    load_credentials(options.get("credential_file") or config.get("credential_file"))
    section = "critic" if role == "online_critic" else role
    nested = config.get(section, {})
    prefix = "LHA_API_" + role.upper() + "_"
    defaults = {
        "model": os.environ.get(prefix + "MODEL")
        or os.environ.get("OPENROUTER_MODEL")
        or DEFAULT_MODEL,
        "reasoning_effort": os.environ.get(prefix + "REASONING_EFFORT")
        or os.environ.get("OPENROUTER_REASONING_EFFORT", DEFAULT_REASONING_EFFORT),
    }
    return {
        name: options.get(name, nested.get(name, config.get(name, default)))
        for name, default in defaults.items()
    }
