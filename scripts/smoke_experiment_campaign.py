"""CPU-only public experiment smoke suite; synthetic media, no API keys or weights.

Runs existing integration tests and public-entry tests in isolated subprocesses.
Their models, renderers and encoders return scripted fixtures. Real orchestration,
video decoding, review validation, maintenance, registration, scoring projection,
blind comparison, reporting and recovery paths remain under test.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = {
    'test_connection_refusal': 'Local connection refusal accounting; original CLI resumes first Planner and second Critic after twelve failures, preserving videos and original receipts',
    'test_selection_recovery': 'Invalid PE evidence references corrected in the original selection call; original command resumes round three and renders only round four',
    'test_maintenance_actions': 'Actual maintenance action spellings, Skill text delivery, format correction and maintenance-only recovery after two failed attempts',
    'test_subscription_submission': 'Native registered result submission, streamed custom tool inputs and separation from commentary',
    'test_subscription_submission': 'Native result submission, four generations and reviews, corrected delivery, recovery and maintenance through the production CLI',
    'test_runtime_completion': 'Empty and invalid replies recover within the original decision, retaining completed work',
    'test_subscription_stream_recovery': 'Saved stream assembly and original-call recovery',
    'test_upgrade_continuation': 'Real historical record projections and cross-version Planner/PE/count-budget recovery',
    'test_same_command_recovery': 'Original-command continuation, four-render Planner recovery, duplicate starts and GPU reassignment',
    'test_fixed117': 'Uniform source normalization, evaluation/export provenance and count-only stopping',
    'test_public_campaign': 'Public check/launch contracts and synthetic delivery-to-scoring handoff',
    'test_pre_experience_parallel': 'N independent task workers, fixed-seed maintenance, atomic appends and public device overrides',
    'test_fixed_budget_completion': 'Four attempts, early-version selection, finish gate and both review modes',
    'test_review_modes': 'Automatic qualitative Critic and in-context Planner self-review',
    'test_experiment_campaign': 'Main stages, private contribution ingestion and held-out reporting',
    'test_experience_families': 'Nonempty seeds, separate reviewer owners, training freeze and read-only use',
    'test_dual_model_campaign': 'Bernini/Ditto profiles, host resolution and separate model runs',
    'test_pe_loop': 'PE refinement, review, selection and receipt recovery',
    'test_pe_budget_scoring_entry': 'Real independent scoring pipeline with scripted judges/encoders; cache reuse',
    'test_chain_integration': 'Actual CLI/client dispatch, maintenance search/read and progress reporting',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'out/public-campaign-smoke')
    parser.add_argument('--timeout', type=float, default=300, help='Timeout per integration module')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error('Use an empty output directory; existing smoke evidence is retained')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='lha-offline-guard-') as tmp:
        guard = Path(tmp)
        (guard / 'sitecustomize.py').write_text('from offline_smoke_guard import install\ninstall()\n', encoding='utf-8')
        env = dict(os.environ)
        env.update(PYTHONPATH=os.pathsep.join([str(guard), str(ROOT / 'scripts')]),
                   CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                   LHA_API_ENV_FILE=str(guard / 'no-credentials.env'),
                   LHA_SMOKE_ARTIFACTS=str(output / 'example'))
        for key in ('OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'):
            env.pop(key, None)
        command = [sys.executable, str(ROOT / 'scripts/check_repository.py'),
                   '--output', str(output / 'tests'), '--timeout', str(args.timeout), '--jobs', '1']
        for module in COVERAGE:
            command += ['--module', module]
        result = subprocess.run(command, cwd=ROOT, env=env)
    manifest = {
        'status': 'passed' if result.returncode == 0 else 'failed',
        'purpose': 'Offline software verification; every example score and model response is synthetic.',
        'coverage': COVERAGE, 'test_summary': 'tests/summary.json',
        'example': 'example/README.md', 'network': 'blocked in workers and Python children',
        'gpu': 'hidden; model/GPU library imports blocked',
        'live_model_calls': 0, 'gpu_generations': 0,
        'not_validated': ['Model quality', 'Provider availability', 'CUDA/VRAM compatibility',
                          'Real encoder values', 'Long-running deployment performance'],
    }
    (output / 'smoke.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': manifest['status'], 'evidence': str(output / 'smoke.json')}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
