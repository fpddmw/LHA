#!/usr/bin/env bash
# Install controller dependencies separately from the renderer used by older jobs.
set -euo pipefail
ROOT="${1:?Pass the frozen deployment checkout}"
RUNTIME="${LHA_AGENT_RUNTIME:-/opt/lha-agent-loop}"
OLD=/openbayes/input/input0/.lha-runtime
UV="$OLD/bootstrap/bin/uv"
mkdir -p "$RUNTIME" "$ROOT/deployment"
if [[ ! -x "$RUNTIME/venv/bin/python" ]]; then
  "$UV" venv --python "$OLD/python/cpython-3.11.14-linux-x86_64-gnu/bin/python3.11" "$RUNTIME/venv"
fi
printf '%s\n' /opt/lha-loop/venv/lib/python3.11/site-packages "$OLD/venv/lib/python3.11/site-packages" > "$RUNTIME/venv/lib/python3.11/site-packages/renderer-dependencies.pth"
"$UV" pip install --python "$RUNTIME/venv/bin/python" --index-url "${LHA_PYPI_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}" -r "$ROOT/requirements.server-runtime.txt"
cat > "$ROOT/deployment/environment.sh" <<'ENV'
export PYTHONDONTWRITEBYTECODE=1
export LOW_HIGH_AGENT_VLM_BACKEND=openrouter
export OPENROUTER_MODEL=openai/gpt-6.1-sol
export OPENROUTER_REASONING_EFFORT=high
export LD_LIBRARY_PATH=/openbayes/input/input0/.lha-runtime/venv/lib/python3.11/site-packages/cusparselt/lib:${LD_LIBRARY_PATH:-}
ENV
source "$ROOT/deployment/environment.sh"
"$RUNTIME/venv/bin/python" - <<'PY'
import av, cv2, numpy, torch
from PIL import Image
import json
print(json.dumps({'torch':torch.__version__,'av':av.__version__,'opencv':cv2.__version__,'numpy':numpy.__version__,'Pillow':Image.__version__,'cuda_initialized':torch.cuda.is_initialized()}))
assert av.__version__ == '15.1.0'
assert not torch.cuda.is_initialized()
PY
"$UV" pip freeze --python "$RUNTIME/venv/bin/python" > "$ROOT/deployment/controller-packages.txt"
