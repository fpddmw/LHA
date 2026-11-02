#!/usr/bin/env bash
# Versioned colleague assignment: final benchmark, short and long, PE only.
set -euo pipefail
if [[ $# -lt 4 || $# -gt 5 ]]; then
  echo "Usage: bash run_pe.sh DATA_ROOT BERNINI_CODE MODEL_DIR OUTPUT [--preflight-only]" >&2
  exit 2
fi
BENCH_DATA_ROOT=$1
BENCH_CODE=$2
BENCH_MODEL=$3
BENCH_OUTPUT=$4
if [[ $# -eq 5 && $5 != --preflight-only ]]; then
  echo "The fifth argument must be --preflight-only" >&2
  exit 2
fi
BENCH_SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BENCH_PYTHON=${BENCH_PYTHON:-python}
BENCH_DEVICE=${BENCH_DEVICE:-0}
BENCH_GPU_LOCK=${BENCH_GPU_LOCK:-/tmp/lha-bernini-device-${BENCH_DEVICE}/.run.lock}
"$BENCH_PYTHON" - "$BENCH_SCRIPT_DIR/../examples/bernini-benchmark/handoff-final.json" "$BENCH_DATA_ROOT" <<'PY'
import hashlib,json,sys
from pathlib import Path
h=json.loads(Path(sys.argv[1]).read_text())
index=Path(sys.argv[2])/h['benchmark_index']
if hashlib.sha256(index.read_bytes()).hexdigest()!=h['benchmark_index_sha256']:
    raise SystemExit('Benchmark differs from the assigned final release; inspect it before running.')
rows=json.loads(index.read_text())
counts={s:sum(r['split']==s for r in rows) for s in h['splits']}
if (len(rows)!=h['sample_count'] or counts!=h['split_counts'] or h['conditions']!=['pe']
    or h['prompt_forms']!=['short','long'] or len(rows)*2!=h['output_positions']):
    raise SystemExit('Assignment counts or condition differ.')
print('Verified final assignment: 75 sources, 150 short/long PE outputs; source splits 40/10/25.')
PY
"$BENCH_PYTHON" "$BENCH_SCRIPT_DIR/run_bernini_benchmark.py" prepare \
  --benchmark "$BENCH_DATA_ROOT/benchmark_data/benchmark.json" --data-root "$BENCH_DATA_ROOT" \
  --split train validation test --prompt-form short long --conditions pe --output "$BENCH_OUTPUT"
"$BENCH_PYTHON" "$BENCH_SCRIPT_DIR/run_bernini_benchmark.py" run \
  --output "$BENCH_OUTPUT" --bernini-code "$BENCH_CODE" --model-dir "$BENCH_MODEL" \
  --device "$BENCH_DEVICE" --preflight-only
if [[ $# -eq 5 ]]; then
  exit 0
fi
exec "$BENCH_PYTHON" "$BENCH_SCRIPT_DIR/run_bernini_benchmark.py" run \
  --output "$BENCH_OUTPUT" --bernini-code "$BENCH_CODE" --model-dir "$BENCH_MODEL" \
  --device "$BENCH_DEVICE" --gpu-lock "$BENCH_GPU_LOCK"
