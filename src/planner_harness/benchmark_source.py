"""Bind a normalized Planner input to its original benchmark and preparation."""
from pathlib import Path

from .common import load, sha
from .execution import signature
from .video import Video


def verify_normalized_source(root, state, row, source):
    """Return verified provenance, or None for a historical native-input task."""
    execution = state['config']['execution']
    binding = execution.get('benchmark_source')
    if binding is None:
        return None
    from experiments.video_contract import POLICY, FRAMES, FPS, sample_indices

    root = Path(root)
    original = (root / binding['original_source']).resolve()
    normalized = (root / binding['source']).resolve()
    record = binding['normalization']
    plan_binding = binding['input_plan']
    plan = load(plan_binding['path'])
    plan_hash = signature({k: v for k, v in plan.items() if k != 'sha256'})
    if plan.get('sha256') != plan_hash or plan_binding['sha256'] != plan_hash:
        raise ValueError('Maintenance input plan changed')
    cases = [c for c in plan['cases'] if c['case_id'] == plan_binding['case_id']]
    if len(cases) != 1:
        raise ValueError('Maintenance input plan has no unique source case')
    case = cases[0]
    if (case['sample_id'] != row['sample_id'] or case['split'] != row['split']
            or case['tier'] != execution['task_track']
            or case['prompt'] != state['request']['text']
            or case.get('normalization') != record
            or case.get('original_source_sha256') != binding['original_source_sha256']
            or case['source_sha256'] != binding['source_sha256']
            or Path(case['original_source_video']).resolve() != original
            or Path(case['source_video']).resolve() != normalized):
        raise ValueError('Maintenance source/request differs from the frozen input case')
    if (original != (root / row['source_video']).resolve()
            or binding['original_source_sha256'] != row['source_video_sha256']
            or sha(original) != row['source_video_sha256']
            or source.get('sha256') != binding['source_sha256']
            or Path(source['path']).resolve() != normalized
            or sha(normalized) != binding['source_sha256']):
        raise ValueError('Maintenance original or normalized source changed')
    request_source = state['request'].get('source', source)
    if request_source.get('sha256') != source['sha256']:
        raise ValueError('Maintenance request uses a different source')
    receipt = normalized.with_name('normalization.json')
    if load(receipt) != record:
        raise ValueError('Maintenance normalization receipt changed')
    original_info = Video(original, original.parent).info
    normalized_info = Video(normalized, normalized.parent).info
    shape = ('frames', 'fps', 'width', 'height')
    if (record.get('policy') != POLICY
            or record.get('original_sha256') != row['source_video_sha256']
            or record.get('normalized_sha256') != source['sha256']
            or record.get('original_info') != {k: original_info[k] for k in shape}
            or case.get('original_source_info') != record['original_info']
            or case.get('source_info') != {k: normalized_info[k] for k in shape}
            or record.get('source_indices') != sample_indices(original_info['frames'])
            or record.get('frames') != FRAMES or record.get('fps') != FPS
            or normalized_info['frames'] != FRAMES or abs(normalized_info['fps'] - FPS) > .001
            or any(normalized_info[k] != original_info[k] for k in ('width', 'height'))
            or case.get('num_frames') != FRAMES or abs(case.get('fps', 0) - FPS) > .001):
        raise ValueError('Maintenance normalization or frame indices differ')
    return {'source_sha256': source['sha256'], 'original_source_sha256': row['source_video_sha256'],
            'normalization': record, 'input_plan_sha256': plan_hash,
            'input_case_id': case['case_id'], 'input_case_sha256': signature(case)}
