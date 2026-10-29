#!/usr/bin/env bash
# Source this file from any working directory after setup.
LHA_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LHA_RUNTIME_ROOT="${LHA_RUNTIME_ROOT:-/openbayes/home/.lha-runtime}"
export LHA_PROJECT_ROOT LHA_RUNTIME_ROOT
export PATH="$LHA_RUNTIME_ROOT/venv/bin:$LHA_RUNTIME_ROOT/codex/node_modules/.bin:$PATH"
export PYTHONPATH="$LHA_PROJECT_ROOT/src:$LHA_PROJECT_ROOT/third_party/Bernini${PYTHONPATH:+:$PYTHONPATH}"
export HF_HOME="$LHA_RUNTIME_ROOT/cache/huggingface"
export HF_ENDPOINT="${HF_ENDPOINT:-https://huggingface.co}"
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-0}"
export CODEX_HOME="${CODEX_HOME:-/openbayes/home/.codex}"
export LOW_HIGH_CODEX_BIN="$LHA_RUNTIME_ROOT/codex/node_modules/.bin/codex"
export LOW_HIGH_AGENT_VLM_BACKEND="${LOW_HIGH_AGENT_VLM_BACKEND:-codex}"
export LOW_HIGH_AGENT_CODEX_MODEL=gpt-6.1-sol
export LOW_HIGH_AGENT_CODEX_REASONING_EFFORT=xhigh
export LOW_HIGH_AGENT_LITELLM_MODEL=gpt-6.1-sol
export LOW_HIGH_AGENT_LITELLM_REASONING_EFFORT=xhigh
export LOW_HIGH_AGENT_LITELLM_RETRIES=3
export LOW_HIGH_AGENT_USE_LOCAL_QWEN=0
# Load an optional private gateway configuration; never store keys in tracked files.
if [[ -f "$LHA_PROJECT_ROOT/.env.openbayes" ]]; then
    set -a
    source "$LHA_PROJECT_ROOT/.env.openbayes"
    set +a
fi
