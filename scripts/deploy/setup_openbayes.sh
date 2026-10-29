#!/usr/bin/env bash
# Rebuild the runtime in OpenBayes' persistent volume. Safe to rerun.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${LHA_RUNTIME_ROOT:-/openbayes/home/.lha-runtime}"
export UV_PYTHON_INSTALL_DIR="$RUNTIME/python"
export UV_PYTHON_BIN_DIR="$RUNTIME/python-bin"
export UV_CACHE_DIR="$RUNTIME/cache/uv"
export HF_HOME="$RUNTIME/cache/huggingface"
export HF_ENDPOINT="${HF_ENDPOINT:-https://huggingface.co}"
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-0}"
export HF_HUB_DOWNLOAD_TIMEOUT=120
mkdir -p "$RUNTIME" "$ROOT/out/deployment"
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
    apt-get update
    apt-get install -y ffmpeg libgl1 libglib2.0-0
fi
if [[ ! -x "$RUNTIME/bootstrap/bin/uv" ]]; then
    python3 -m pip install --target "$RUNTIME/bootstrap" uv==0.9.11
fi
UV="$RUNTIME/bootstrap/bin/uv"
"$UV" python install 3.11.14
if [[ ! -x "$RUNTIME/venv/bin/python" ]] || ! "$RUNTIME/venv/bin/python" -c \
    'import sys; assert sys.base_prefix.startswith(sys.argv[1])' "$RUNTIME/python"; then
    "$UV" venv --clear --python "$RUNTIME/python/cpython-3.11.14-linux-x86_64-gnu/bin/python3.11" "$RUNTIME/venv"
fi
PYTHON="$RUNTIME/venv/bin/python"
INDEX="${LHA_PYPI_INDEX:-https://repo.huaweicloud.com/repository/pypi/simple}"
CAPABILITY="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -n 1)"
TORCH_FLAVOR="${LHA_TORCH_FLAVOR:-cu126}"
if [[ -z "${LHA_TORCH_FLAVOR:-}" && "${CAPABILITY%%.*}" -ge 10 ]]; then
    TORCH_FLAVOR=cu128
fi
"$UV" pip install --python "$PYTHON" --index-url "https://download.pytorch.org/whl/$TORCH_FLAVOR" \
    "torch==2.7.1+$TORCH_FLAVOR" "torchvision==0.22.1+$TORCH_FLAVOR"
"$UV" pip install --python "$PYTHON" --index-url "$INDEX" \
    -r "$ROOT/requirements.openbayes.txt"
# Bernini imports VeOmni utilities even on its single-GPU renderer path.
# Avoid installing the separate VeOmni training dependency set.
"$UV" pip install --python "$PYTHON" --no-deps \
    'veomni @ git+https://github.com/ByteDance-Seed/VeOmni.git@f90b3dc6fbb0ce693745223cc7a94064123dbf4d'
# The current vendored full-model imports also load Qwen attention, which
# requires FA2 even when the selected model is renderer-only. Official CUDA 12
# wheel for CPython 3.11 / torch 2.7 / C++11 ABI; no local CUDA compilation.
"$UV" pip install --python "$PYTHON" --no-deps \
    'https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3%2Bcu12torch2.7cxx11abiTRUE-cp311-cp311-linux_x86_64.whl'
if [[ ! -x "$RUNTIME/codex/node_modules/.bin/codex" ]]; then
    npm install --prefix "$RUNTIME/codex" @openai/codex@0.165.0
fi
PYTHONPATH="$ROOT/src:$ROOT/third_party/Bernini" "$PYTHON" -c \
    'import torch; from bernini.pipeline import BerniniRendererPipeline; from vlm import resolve_vision_model; print("CUDA:", torch.cuda.is_available(), torch.cuda.get_device_name(0)); print("Bernini imports OK")'
"$UV" pip freeze --python "$PYTHON" > "$ROOT/out/deployment/installed-requirements.txt"
if [[ "${LHA_DOWNLOAD_MODELS:-1}" == 1 ]]; then
    "$PYTHON" "$ROOT/scripts/deploy/download_models.py"
fi
echo "Ready. Run: source scripts/deploy/env_openbayes.sh"
