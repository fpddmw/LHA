"""Read-only publication checks. No client construction, GPU query or network I/O."""
from pathlib import Path
import importlib.util
import re

from planner_harness.common import load, sha


def module_available(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def check(root, config, hosts=None, *, verify_assets=False):
    from . import campaign, render_profiles
    from .unified_benchmark import model_configuration
    from planner_harness.creative_knowledge import CreativeKnowledge
    from evaluation.providers import configuration as judge_configuration

    root = Path(root).resolve()
    checks = []

    def record(name, operation):
        try:
            details = operation()
            checks.append({'name': name, 'status': 'passed', 'details': details})
        except (ValueError, OSError, KeyError, TypeError) as exc:
            # Do not echo exception text: private host values may contain credentials.
            checks.append({'name': name, 'status': 'needs_configuration',
                           'error_type': type(exc).__name__})

    record('campaign', lambda: {
        key: value for key, value in campaign.plan(root, config).items()
        if key in {'planner_N', 'pe_N', 'main_max_generations', 'main_trajectories', 'prompt_forms'}
    })

    def dataset():
        rows = load(root / 'benchmark_data/benchmark.json')
        failures = []
        for row in rows:
            for field in ('source_video', 'prompt_file', 'prompt_short_file'):
                path = root / row[field]
                if not path.is_file() or sha(path) != row[field + '_sha256']:
                    failures.append({'sample_id': row['sample_id'], 'field': field})
        return {'files': len(rows) * 3, 'invalid_files': len(failures), 'examples': failures[:10]}

    record('dataset_files', dataset)
    if checks[-1].get('details', {}).get('invalid_files'):
        checks[-1]['status'] = 'needs_configuration'

    def knowledge():
        full = CreativeKnowledge(root, experience_mode='full')
        none = CreativeKnowledge(root, experience_mode='none')
        entries = full.curated_catalog['entries']
        if not entries or none.curated_catalog['entries']:
            raise ValueError('Knowledge seed or online exposure is invalid')
        for library in (full, none):
            for name in ('manual', 'map', 'meaning', 'design-expression'):
                library.read(name)
        return {'seed_entries': len(entries), 'none_online_entries': 0}

    record('knowledge', knowledge)
    record('judges', lambda: [{key: row.get(key) for key in
                               ('model', 'provider', 'provider_model', 'reasoning_effort')}
                              for row in judge_configuration()])

    if not hosts:
        checks.append({'name': 'hosts', 'status': 'needs_configuration',
                       'details': 'Supply --host-config for the selected renderer(s).'})
    for name, host in (hosts or {}).items():
        def declaration(name=name, host=host):
            if host.get('renderer', {}).get('backend') != name:
                raise ValueError('Host backend mismatch')
            if not isinstance(host.get('devices'), list) or not host['devices']:
                raise ValueError('Declare devices explicitly')
            if len(set(map(str, host['devices']))) != len(host['devices']):
                raise ValueError('Repeated device')
            expected = {'model': config['model'], 'reasoning_effort': config['reasoning_effort']}
            planner, critic, _ = model_configuration(expected, host.get('models'))
            if planner != expected or critic != expected:
                raise ValueError('Online model identity differs from campaign')
            renderer = host['renderer']
            if renderer.get('generation', render_profiles.generation(name)) != render_profiles.generation(name):
                raise ValueError('Generation profile differs')
            return {'backend': name, 'device_count': len(host['devices']),
                    'planner': planner, 'critic': critic}
        record(name + '_host', declaration)

        def assets(host=host):
            renderer = host['renderer']
            path = root / renderer['asset_manifest']
            digest = renderer['asset_manifest_sha256']
            if not re.fullmatch('[a-f0-9]{64}', digest) or sha(path) != digest:
                raise ValueError('Missing or changed asset manifest')
            manifest = load(path)
            files = manifest['files']
            if not files:
                raise ValueError('Asset manifest must list installed files')
            for row in files:
                file = root / row['path']
                if not file.is_file() or file.stat().st_size != row['bytes']:
                    raise ValueError('Missing or changed asset file')
                if verify_assets and sha(file) != row['sha256']:
                    raise ValueError('Asset content hash differs')
            return {'files': len(files), 'manifest_sha256': digest,
                    'file_check': 'sha256_and_size' if verify_assets else 'existence_and_size'}
        record(name + '_assets', assets)

    return {
        'status': 'offline_checks_passed' if all(c['status'] == 'passed' for c in checks) else 'needs_configuration',
        'checks': checks, 'live_model_calls': 0, 'gpu_jobs': 0,
        'scoring_modules_present': {name: module_available(name)
                                    for name in ('av', 'cv2', 'torch', 'transformers')},
        'not_checked': ['provider access and visual capability', 'GPU/CUDA compatibility and memory',
                        'renderer initialization and encoder weight availability',
                        'output disk capacity and runtime performance'],
        'next': 'Install/check runtime dependencies and perform the separately authorized live preflight on the execution host.',
    }
