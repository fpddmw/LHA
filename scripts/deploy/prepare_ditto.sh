#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${LHA_RUNTIME_ROOT:-/openbayes/home/.lha-runtime}"
PY="$RUNTIME/venv/bin/python"
UV="$RUNTIME/bootstrap/bin/uv"
export UV_CACHE_DIR="$RUNTIME/cache/uv"
SPEC="${1:-$ROOT/configs/ditto_models.json}"
CODE="$ROOT/third_party/Ditto-official"
REVISION="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["code_revision"])' "$SPEC")"
if [[ ! -d "$CODE/.git" ]]; then
  git clone --depth 1 https://github.com/EzioBy/Ditto.git "$CODE"
fi
if ! git -C "$CODE" cat-file -e "$REVISION^{commit}"; then
  git -C "$CODE" fetch --depth 1 origin "$REVISION"
fi
git -C "$CODE" checkout --detach "$REVISION"
"$UV" pip install --python "$PY" --index-url https://repo.huaweicloud.com/repository/pypi/simple 'modelscope==1.40.2' 'pynvml==13.0.1'
# The pinned upstream setup.py imports pkg_resources during its build.
"$UV" pip install --python "$PY" --index-url https://repo.huaweicloud.com/repository/pypi/simple 'setuptools==80.9.0' 'wheel==0.48.0'
"$UV" pip install --python "$PY" --no-build-isolation --no-deps -e "$CODE"
PYTHONPATH="$CODE" "$PY" -c \
 'from diffsynth.pipelines.wan_video_new import WanVideoPipeline, ModelConfig; print("Ditto imports passed")'
mkdir -p "$ROOT/out/deployment/blackwell"
git -C "$CODE" rev-parse HEAD > "$ROOT/out/deployment/blackwell/ditto-code-revision.txt"
"$UV" pip freeze --python "$PY" > "$ROOT/out/deployment/blackwell/requirements-with-ditto.txt"
