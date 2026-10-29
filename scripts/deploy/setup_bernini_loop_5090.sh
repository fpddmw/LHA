#!/usr/bin/env bash
# Reuse the read-only Bernini asset volume; rebuild only disposable runtime.
set -euo pipefail
ROOT=/openbayes/home/LHA
OLD=/openbayes/input/input0/.lha-runtime
RUNTIME=/opt/lha-loop
mkdir -p "$ROOT/out/deployment/bernini-loop-5090" "$RUNTIME"
if [[ ! -e /openbayes/home/.lha-runtime ]]; then
  ln -s "$OLD" /openbayes/home/.lha-runtime
fi
UV="$OLD/bootstrap/bin/uv"
export UV_CACHE_DIR="$RUNTIME/cache"
export PYTHONDONTWRITEBYTECODE=1
if [[ ! -x "$RUNTIME/venv/bin/python" ]]; then
  "$UV" venv --python "$OLD/python/cpython-3.11.14-linux-x86_64-gnu/bin/python3.11" "$RUNTIME/venv"
fi
TORCH_WHEEL="$RUNTIME/torch-2.7.1+cu128-cp311-cp311-manylinux_2_28_x86_64.whl"
TORCH_SPEC='torch==2.7.1+cu128'
if [[ -f "$TORCH_WHEEL" ]]; then
  echo 'c301dc280458afd95450af794924c98fe07522dd148ff384739b810e3e3179f2  '"$TORCH_WHEEL" | sha256sum -c -
  TORCH_SPEC="$TORCH_WHEEL"
fi
if [[ -d /usr/local/lib/python3.10/site-packages/nvidia ]] && python -c 'import torch; assert torch.version.cuda=="12.8"'; then
  # NVIDIA shared libraries do not depend on the Python minor ABI. The image
  # already supplies CUDA 12.8; reuse them with the matching CPython-3.11 torch.
  "$UV" pip install --python "$RUNTIME/venv/bin/python" --no-deps \
    --index-url https://download.pytorch.org/whl/cu128 "$TORCH_SPEC" 'torchvision==0.22.1+cu128'
  ln -sfn /usr/local/lib/python3.10/site-packages/nvidia "$RUNTIME/venv/lib/python3.11/site-packages/nvidia"
else
  "$UV" pip install --python "$RUNTIME/venv/bin/python" --index-url https://download.pytorch.org/whl/cu128 \
    "$TORCH_SPEC" 'torchvision==0.22.1+cu128'
fi
# All other pinned dependencies remain on the original read-only volume.
printf '%s\n' "$OLD/venv/lib/python3.11/site-packages" > "$RUNTIME/venv/lib/python3.11/site-packages/old-bernini.pth"
export PYTHONPATH="$ROOT/third_party/Bernini"
export LD_LIBRARY_PATH="$OLD/venv/lib/python3.11/site-packages/cusparselt/lib:${LD_LIBRARY_PATH:-}"
"$RUNTIME/venv/bin/python" - <<'PY'
import torch
print('torch', torch.__version__, 'CUDA', torch.version.cuda, 'GPU', torch.cuda.get_device_name(0), flush=True)
assert 'sm_120' in torch.cuda.get_arch_list()
assert (torch.ones(8,device='cuda')+1).sum().item()==16
from flash_attn import flash_attn_func
q=torch.randn(1,32,4,64,device='cuda',dtype=torch.bfloat16)
assert torch.isfinite(flash_attn_func(q,q,q)).all()
from bernini.pipeline import BerniniRendererPipeline
print('CUDA, FlashAttention and Bernini imports passed', flush=True)
PY
"$UV" pip freeze --python "$RUNTIME/venv/bin/python" > "$ROOT/out/deployment/bernini-loop-5090/runtime.txt"
exec "$RUNTIME/venv/bin/python" -u "$ROOT/scripts/deploy/run_bernini_loop_queue.py" --run "$ROOT/out/loop_probe/20261029_bernini"
