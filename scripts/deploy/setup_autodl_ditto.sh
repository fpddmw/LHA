#!/usr/bin/env bash
# Reuse the AutoDL PyTorch 2.8 / CUDA 12.8 image and preserve original model files.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${LHA_RUNTIME_ROOT:-/root/lha-runtime}"
BASE_PYTHON="${LHA_BASE_PYTHON:-/root/miniconda3/bin/python}"
mkdir -p "$RUNTIME" "$ROOT/out/deployment/autodl-h800"
if [[ ! -x "$RUNTIME/venv/bin/python" ]]; then
    "$BASE_PYTHON" -m venv --system-site-packages "$RUNTIME/venv"
fi
PY="$RUNTIME/venv/bin/python"
INDEX="${LHA_PYPI_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
"$PY" -m pip install --no-cache-dir --index-url "$INDEX" \
    'huggingface-hub==0.35.1' 'safetensors==0.6.2'
echo "DOWNLOAD_DEPENDENCIES_READY"
"$PY" -m pip install --no-cache-dir --index-url "$INDEX" \
    -r "$ROOT/requirements.openbayes.txt" \
    'modelscope==1.40.2' 'pynvml==13.0.1' 'setuptools==80.9.0' 'wheel==0.48.0' 'uv==0.9.11'
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ffmpeg libgl1
fi
CODE="$ROOT/third_party/Ditto-official"
REVISION="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["code_revision"])' "$ROOT/configs/ditto_models.json")"
mkdir -p "$ROOT/third_party"
if [[ ! -d "$CODE/.git" ]]; then
    git clone --depth 1 https://github.com/EzioBy/Ditto.git "$CODE"
fi
if ! git -C "$CODE" cat-file -e "$REVISION^{commit}"; then
    git -C "$CODE" fetch --depth 1 origin "$REVISION"
fi
git -C "$CODE" checkout --detach "$REVISION"
"$RUNTIME/venv/bin/uv" pip install --python "$PY" --no-cache --no-build-isolation --no-deps -e "$CODE"
"$PY" -m pip install --no-cache-dir --no-deps \
    'https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3%2Bcu12torch2.8cxx11abiTRUE-cp312-cp312-linux_x86_64.whl'
PYTHONPATH="$CODE" "$PY" - <<'PY'
import torch
from flash_attn import flash_attn_func
from diffsynth.pipelines.wan_video_new import WanVideoPipeline, ModelConfig
assert torch.__version__ == '2.8.0+cu128'
q = torch.randn(1,32,4,64,device='cuda',dtype=torch.bfloat16)
y = flash_attn_func(q,q,q)
assert y.shape == q.shape and torch.isfinite(y).all()
print('H800 CUDA, FlashAttention, and Ditto imports passed', torch.cuda.get_device_name(0))
PY
git -C "$CODE" rev-parse HEAD > "$ROOT/out/deployment/autodl-h800/ditto-code-revision.txt"
"$PY" -m pip freeze > "$ROOT/out/deployment/autodl-h800/requirements-resolved.txt"
touch "$ROOT/out/deployment/autodl-h800/environment-ready"
echo "ENVIRONMENT_READY"
