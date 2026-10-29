#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env_openbayes.sh"
cd "$LHA_PROJECT_ROOT"
RUN_DIR="${LHA_RUN_DIR:-out/openbayes_e2e/$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$RUN_DIR"
RUN_DIR="$(cd "$RUN_DIR" && pwd)"
export LOW_HIGH_VLM_AUDIT_LOG="$RUN_DIR/vlm-calls.jsonl"
# Bounded initial integration run, matching the existing 17-frame Bernini protocol.
export LOW_HIGH_BENCH_NUM_FRAMES="${LOW_HIGH_BENCH_NUM_FRAMES:-17}"
export LOW_HIGH_BENCH_FPS="${LOW_HIGH_BENCH_FPS:-20}"
python -c 'from edit.video_editor import EDIT_VARIANTS, _variant_availability; ok, missing = _variant_availability(EDIT_VARIANTS["bernini1.3b"]); assert ok, "Incomplete model: " + str(missing)'
python -u scripts/run_planner_and_edit.py --variant bernini1.3b \
    --sample-id "${LHA_SAMPLE_ID:-2}" --max-attempts "${LHA_MAX_ATTEMPTS:-2}" \
    --output-dir "$RUN_DIR/loop" --memory-path "$RUN_DIR/memory.json" "$@" \
    2>&1 | tee "$RUN_DIR/run.log"
python scripts/deploy/verify_e2e.py "$RUN_DIR" | tee "$RUN_DIR/verification.log"
