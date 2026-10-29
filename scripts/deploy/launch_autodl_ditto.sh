#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${LHA_RUNTIME_ROOT:-/root/lha-runtime}"
RUN="$ROOT/out/prompt_probe/20261029_ditto"
DEPLOY="$ROOT/out/deployment/autodl-h800"
mkdir -p "$RUNTIME" "$RUN" "$DEPLOY"
exec 9>"$RUNTIME/ditto-probe.lock"
flock -n 9 || { echo 'Ditto deployment/probe already running'; exit 1; }
export PATH="/root/miniconda3/bin:$PATH"
if [[ -f /etc/network_turbo ]]; then
    set +u
    source /etc/network_turbo >/dev/null 2>&1
    set -u
fi
export HF_HUB_DISABLE_XET=1 HF_HUB_DOWNLOAD_TIMEOUT=120
export HF_ENDPOINT="${HF_ENDPOINT:-https://huggingface.co}"
export PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
cd "$ROOT"
date -u +%FT%TZ > "$DEPLOY/started-utc.txt"
bash "$ROOT/scripts/deploy/setup_autodl_ditto.sh" > "$DEPLOY/setup.log" 2>&1 9>&- &
setup_pid=$!
PY="$RUNTIME/venv/bin/python"
while ! "$PY" -c 'import huggingface_hub, safetensors' >/dev/null 2>&1; do
    if ! kill -0 "$setup_pid" 2>/dev/null; then
        wait "$setup_pid"
        echo 'Setup exited before download dependencies were ready'
        exit 1
    fi
    sleep 5
done
"$PY" -u "$ROOT/scripts/deploy/download_ditto_models.py" \
    --spec "$ROOT/configs/ditto_models.json" --models-root "$ROOT/models" \
    --placement-map "$DEPLOY/model-placement.json" --workers 3 \
    > "$DEPLOY/download.log" 2>&1 9>&- &
download_pid=$!
echo "setup_pid=$setup_pid download_pid=$download_pid"
wait "$setup_pid"
wait "$download_pid"
echo 'Environment and original model hashes verified; starting full-length generation'
"$PY" -u "$ROOT/scripts/deploy/run_ditto_prompt_probe.py" \
    --manifest "$RUN/cases.json" --verified-manifest "$ROOT/configs/ditto-models-verified.json" \
    > "$RUN/session.log" 2>&1
date -u +%FT%TZ > "$DEPLOY/generation-finished-utc.txt"
