#!/usr/bin/env bash
# Run inside the inherited OpenBayes workspace; compatible with RTX PRO 6000.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${LHA_RUNTIME_ROOT:-/openbayes/home/.lha-runtime}"
UV="$RUNTIME/bootstrap/bin/uv"
PY="$RUNTIME/venv/bin/python"
export UV_CACHE_DIR="$RUNTIME/cache/uv"
mkdir -p "$ROOT/out/deployment/blackwell"
"$UV" pip install --python "$PY" --index-url https://download.pytorch.org/whl/cu128 \
  'torch==2.7.1+cu128' 'torchvision==0.22.1+cu128'
"$PY" - <<'PY'
import torch
print('torch:', torch.__version__, 'CUDA:', torch.version.cuda, 'GPU:', torch.cuda.get_device_name(0))
assert 'sm_120' in torch.cuda.get_arch_list()
assert (torch.ones(8,device='cuda')+1).sum().item()==16
from flash_attn import flash_attn_func
q=torch.randn(1,32,4,64,device='cuda',dtype=torch.bfloat16)
y=flash_attn_func(q,q,q)
assert y.shape==q.shape and torch.isfinite(y).all()
print('Blackwell CUDA and FlashAttention execution passed')
PY
"$UV" pip freeze --python "$PY" > "$ROOT/out/deployment/blackwell/requirements-resolved.txt"
PYTHONPATH="$ROOT/third_party/Bernini" "$PY" -c \
 'from bernini.pipeline import BerniniRendererPipeline; print("Bernini imports passed")'
