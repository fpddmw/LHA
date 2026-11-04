"""Ordered main experiment and optional reviewer ablation, using existing runners."""
from pathlib import Path
import copy

from planner_harness.resources import estimate_budget
from .video_contract import POLICY as VIDEO_POLICY, FRAMES, FPS
from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock

# Split labels describe RSI roles only. Every method covers the full population.
STAGES = {
    'pre-experience': (('pre-experience',), 'critic', True),
    'full-experience': (('full',), 'critic', False),
    'direct': (('direct',), 'critic', False),
    'pe-loop': (('pe-loop',), 'critic', False),
    'self-review-pre-experience': (('pre-experience',), 'planner', True),
    'self-review-full-experience': (('full',), 'planner', False),
}
MAIN = ('pre-experience', 'full-experience', 'direct', 'pe-loop', 'score')
SELF_REVIEW = ('self-review-pre-experience', 'self-review-full-experience')
ALL = (*MAIN[:-1], *SELF_REVIEW, 'score')
VERSION = 'lha-experiment-campaign-v6'


def seed_library(root, output, initial=None):
    """Bind a nonempty pre-existing corpus before any campaign stage can run.

    The pre-experience arm uses this exact seed online and after settlement.
    """
    from planner_harness.creative_knowledge import CreativeKnowledge
    from planner_harness.training_experience import validate_snapshot
    output = Path(output)
    target = output / 'initial-experience.json'
    if target.exists():
        value = load(target)
        if initial and value != load(initial):
            raise ValueError('Campaign initial knowledge differs; retain the original snapshot')
    elif initial:
        value = load(initial)
    else:
        # Existing ordered runs retain their original seed when resumed.
        original = output / 'pre-experience/training-experience/versions/base/snapshot.json'
        if original.exists():
            value = load(original)
        else:
            knowledge = CreativeKnowledge(root, experience_mode='full')
            if not knowledge.curated_catalog['entries']:
                raise ValueError('Campaign requires pre-existing knowledge entries, not an empty library')
            knowledge.freeze(target)
            value = load(target)
    knowledge = validate_snapshot(root, value)
    if not knowledge.curated_catalog['entries']:
        raise ValueError('Campaign requires pre-existing knowledge entries, not an empty library')
    immutable(target, value)
    immutable(output / 'initial-experience-receipt.json', {
        'snapshot_sha256': sha(target), 'preexisting_entries': len(knowledge.curated_catalog['entries']),
        'online_exposure': 'pre-experience reads this seed online and after settlement',
        'maintenance': 'train contributions enter the current campaign; test contributions are deferred',
    })
    return target


def execute_models(root, output, config, hosts, stage, *, execute_paid=False):
    """One invocation, separate model runs/registries, and the same initial corpus."""
    if not execute_paid:
        raise ValueError('Execution requires --execute')
    if not hosts or set(hosts) - {'bernini', 'ditto'}:
        raise ValueError('Choose bernini and/or ditto hosts')
    for name, host in hosts.items():
        if host.get('renderer', {}).get('backend') != name:
            raise ValueError('Host backend does not match model key: ' + name)
    output = Path(output)
    with RunLock(output / 'models-owner'):
        seed = None if stage == 'score' else seed_library(root, output)
        return {name: execute(root, output / name, config, host, stage,
                              execute_paid=True, initial_snapshot=seed)
                for name, host in hosts.items()}


def configuration(path):
    value = load(path)
    expected = {'version', 'max_generations', 'prompt_forms', 'seed_start', 'seed_step',
                'task_budget', 'model', 'reasoning_effort', 'evaluation_id', 'maintenance', 'reuse_direct_results', 'pe_max_generations', 'rsi_partition'}
    if set(value) != expected or value['version'] != VERSION:
        raise ValueError('Use the versioned campaign configuration')
    for key in ('max_generations', 'pe_max_generations', 'seed_step'):
        if type(value[key]) is not int or value[key] < 1:
            raise ValueError(key + ' must be positive')
    if type(value['seed_start']) is not int or value['seed_start'] < 0:
        raise ValueError('Invalid seed')
    for backend in ('bernini', 'ditto'):
        estimate_budget(backend, value['max_generations'], **value['task_budget'])
    forms = value['prompt_forms']
    if not forms or len(set(forms)) != len(forms) or set(forms) - {'short', 'long'}:
        raise ValueError('Choose distinct short/long conditions')
    if not isinstance(value['model'],str) or not value['model'].strip() or not isinstance(value['reasoning_effort'],str) or not value['reasoning_effort'].strip():
        raise ValueError('Declare the API model and reasoning effort explicitly')
    if value['model']=='gpt-6.1-sol':value['model']='openai/gpt-6.1-sol'
    if value['reuse_direct_results'] is not None and not isinstance(value['reuse_direct_results'], str):
        raise ValueError('reuse_direct_results must be a local registry path or null')
    from planner_harness.maintenance import configuration as maintenance_configuration
    value['maintenance'] = maintenance_configuration(value['maintenance'])
    if not value['maintenance']['enabled'] or value['maintenance']['automatic_phase'] != 'after_each_training_task':
        raise ValueError('Training requires post-task private maintenance')
    return value


def population(root, config):
    rows = load(Path(root) / 'benchmark_data/benchmark.json')
    partition = config['rsi_partition']
    if set(partition) != {'train_count', 'test_count'} or any(type(v) is not int or v < 1 for v in partition.values()):
        raise ValueError('Declare positive RSI train/test row counts')
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate benchmark sample IDs')
    training = [r for r in rows if r['split'] == 'train']
    heldout = [r for r in rows if r['split'] == 'test']
    if len(training) != partition['train_count'] or len(heldout) != partition['test_count'] or len(training) + len(heldout) != len(rows):
        raise ValueError('Current benchmark differs from the configured RSI partition; recheck actual IDs/counts')
    for key in ('source_group', 'source_video_sha256'):
        if {r.get(key, r['sample_id']) for r in training} & {r.get(key, r['sample_id']) for r in heldout}:
            raise ValueError('A source group/video crosses the RSI partition: ' + key)
    return {'benchmark_sha256': sha(Path(root) / 'benchmark_data/benchmark.json'),
            'main_sample_ids': [r['sample_id'] for r in rows],
            'rsi_train_ids': [r['sample_id'] for r in training], 'rsi_test_ids': [r['sample_id'] for r in heldout]}


def stage_config(config, stage, backend='bernini'):
    count = 1 if stage == 'direct' else config['pe_max_generations'] if stage == 'pe-loop' else config['max_generations']
    estimate = estimate_budget(backend, count, **config['task_budget'])
    return {**config, 'max_generations': count, 'budget_estimate': estimate,
            'task_wall_seconds': estimate['max_wall_seconds']}


def plan(root, config):
    cohort = population(root, config)
    count = len(cohort['main_sample_ids']) * len(config['prompt_forms'])
    train_count = len(cohort['rsi_train_ids']) * len(config['prompt_forms'])
    batches = []
    for stage, (methods, review, maintain) in STAGES.items():
        n = stage_config(config, stage)['max_generations']
        batches.append({'stage': stage, 'scope': 'all', 'methods': list(methods), 'review_mode': review,
                        'conditions': count, 'trajectories': count * len(methods),
                        'max_generations': count * n * len(methods), 'generations_per_condition': n * len(methods),
                        'task_budgets': {name: estimate_budget(name, n, **config['task_budget']) for name in ('bernini', 'ditto')},
                        'post_task_maintenance': count if maintain else 0,
                        'current_campaign_contribution_conditions': train_count if maintain else 0,
                        'deferred_contribution_conditions': count - train_count if maintain else 0,
                        'rsi_train_conditions': train_count, 'rsi_test_conditions': count - train_count,
                        'additional_ablation': stage.startswith('self-review')})
    return {'version': VERSION, 'video_policy': {'id': VIDEO_POLICY, 'frames': FRAMES, 'fps': FPS}, 'planner_N': config['max_generations'], 'pe_N': config['pe_max_generations'],
            'seed': config['seed_start'], 'prompt_forms': config['prompt_forms'], 'population': cohort, 'batches': batches,
            'main_max_generations': sum(b['max_generations'] for b in batches if not b['additional_ablation']),
            'main_trajectories': sum(b['trajectories'] for b in batches if not b['additional_ablation']),
            'extra_training_generations': 0, 'validation_conditions_scheduled': 0,
            'model_calls': 'metered separately; maintenance adds no video generation',
            'reuse': 'RSI train/test are subsets of the same full-population runs, never extra runs. First/last/final and identical task/video scores are reused.'}


def reuse_direct(root, output, batch, host, registry):
    """Import compatible Direct videos, never old scores or legacy loop traces."""
    from . import results, unified_benchmark as runner
    source = (Path(root) / registry).resolve()
    target = Path(batch['results_root'])
    rows = []
    for topic in batch['topics']:
        existing = results.find(target, topic['sample_id'], topic['prompt_form'], 'direct', batch['seed_sequence']['start'])
        if existing:
            runner.check_entry(topic,'direct',{**batch,'renderer_identity':host['renderer']},existing)
            rows.append({'topic': topic['id'], 'status': 'already_registered'})
            continue
        old = results.find(source, topic['sample_id'], topic['prompt_form'], 'direct', batch['seed_sequence']['start'])
        if old is None:
            rows.append({'topic': topic['id'], 'status': 'not_found'})
            continue
        try:
            runner.check_entry(topic, 'direct', {**batch, 'renderer_identity': host['renderer'], 'results_root': str(source)}, old)
            row = copy.deepcopy(old)
            row['video'] = str(source / row['video'])
            if row.get('normalization'):row['source'] = str(source / row['source'])
            for candidate in row.get('candidates', []):
                candidate['video'] = str(source / candidate['video'])
            results.import_video(root, target, row)
            rows.append({'topic': topic['id'], 'status': 'reused', 'entry_sha256': old['sha256']})
        except (ValueError, OSError, RuntimeError) as exc:
            rows.append({'topic': topic['id'], 'status': 'incompatible', 'reason': str(exc)})
    save(Path(output) / 'direct-reuse.json', {'source': str(source), 'positions': rows})
    return rows


def online_budget(config, methods, conditions):
    from planner_harness import accounting
    # Online policy owns generation-count stopping. Count fields are explicit inputs to the
    # existing normalizer, which meters API calls/tokens without extra task caps.
    estimate = config.get('budget_estimate') or estimate_budget('bernini', config['max_generations'], **config['task_budget'])
    lane = {**accounting.LIMITS, 'render_requests': config['max_generations'],
            'tokens': estimate['estimated_total_tokens'],
            'wall_seconds': estimate['max_wall_seconds'], 'amount': None}
    topic = {k: None if v is None else v * len(methods) for k, v in lane.items()}
    batch = {k: None if v is None else v * max(conditions, 1) for k, v in topic.items()}
    return {'version': accounting.VERSION, 'mode': 'live', 'cost_control': 'count_limits_only',
            'max_call_seconds': estimate['max_wall_seconds'], 'budget_estimate': estimate, 'batch': batch, 'topic': topic,
            'lanes': list(methods), 'allocations': {m: copy.deepcopy(lane) for m in methods}}


def evaluation_budget(config, conditions):
    from planner_harness import accounting
    # Each condition has <= 16 distinct first/last/final positions including the
    # optional ablation; two automatic compute families fit within 64 requests.
    topic = {**accounting.LIMITS, 'model_calls': 0, 'render_requests': 0,
             'compute_requests': 64, 'tokens': 0, 'wall_seconds': None, 'amount': None}
    batch = {k: None if v is None else v * max(conditions, 1) for k, v in topic.items()}
    return {'version': accounting.VERSION, 'mode': 'live', 'cost_control': 'count_limits_only',
            'max_call_seconds': None, 'batch': batch, 'topic': topic,
            'lanes': ['independent'], 'allocations': {'independent': topic}}


def freeze_training(root, output, *, review_mode="critic"):
    """Freeze only settled training contributions; no validation-set gate."""
    from planner_harness.training_experience import current, validate_snapshot, validate_owner
    output = Path(output)
    if review_mode not in {'critic', 'planner'}:
        raise ValueError('Unknown review family')
    source = output / ('pre-experience' if review_mode == 'critic' else 'self-review-pre-experience')
    name = 'trained-experience' if review_mode == 'critic' else 'self-review-trained-experience'
    if not (source / 'batch.json').exists():
        source = output / ('zero' if review_mode == 'critic' else 'self-review-zero')
    batch = load(source / 'batch.json')
    method, = batch['arms']
    if batch.get('review') != {'mode':review_mode} or not batch.get('training_maintenance') or method not in {'none', 'pre-experience'}:
        raise ValueError('Freeze requires the matching accumulating review family')
    coverage=[]
    from .unified_benchmark import training_completion
    for topic in batch['topics']:
        settled = load(source / 'methods' / topic['id'] / method / 'settlement.json')
        if settled['status'] in {'execution_unknown','topic_quarantined','unexecuted','running'}:
            raise ValueError('Training task needs original execution recovery: '+topic['id'])
        if topic['split'] != 'train' and method != 'pre-experience':
            continue
        result=training_completion(source,topic['id'])
        if result['status'] in {'pending','execution_unknown'}:
            raise ValueError('Training maintenance needs recovery: '+topic['id'])
        record = {'topic': topic['id'], 'online_status': settled['status'], 'maintenance': result}
        if method == 'pre-experience':
            record['split'] = topic['split']
        coverage.append(record)
    revision = current(root, source)
    validate_owner(revision['owner'],output=source,review_mode=review_mode,renderer_backend=batch['backend'])
    if revision['owner'] != batch.get('experience_owner'):
        raise ValueError('Frozen training batch and library owner differ')
    value = load(revision['snapshot']); validate_snapshot(root, value)
    immutable(output / (name + '.json'), value)
    immutable(output / (name + '-receipt.json'), {
        'training_batch_sha256': batch['sha256'], 'conditions': sum(row.get('split', 'train') == 'train' for row in coverage), 'full_run_conditions': len(batch['topics']),
        'revision': revision, 'snapshot_sha256': sha(output / (name + '.json')),
        'online_mode': method, 'maintenance_scope': 'fixed seed; test contributions deferred' if method == 'pre-experience' else 'private accumulated full library after task settlement','coverage':coverage})
    return output / (name + '.json')


def score_stage(root, output, config, summary):
    """Score collected videos independently of generation settings and seed libraries."""
    from . import results
    registry = output / 'results'
    results.ensure_evaluation(root, registry, evaluation_id=config['evaluation_id'])
    budget = evaluation_budget(config, next(b['conditions'] for b in summary['batches'] if b['stage'] == 'pre-experience'))
    results.score_evaluation(root, registry, budget)
    baseline = output / 'pre-experience/batch.json'
    if not baseline.exists():
        baseline = output / 'zero/batch.json'  # Historical score-only input.
    control = 'none' if baseline.exists() and load(baseline)['arms'] == ['none'] else 'pre-experience'
    results.report(root, registry, splits=['test'], methods=[control, 'full'], review_modes=['critic'],
                   analysis_population='rsi', output_name='rsi')
    return results.report(root, registry)


def execute(root, output, config, host, stage, *, execute_paid=False, initial_snapshot=None):
    if not execute_paid:
        raise ValueError('Execution requires --execute; use plan to inspect counts without calls')
    if stage not in {*STAGES, 'self-review', 'main', 'all', 'score'}:
        raise ValueError('Unknown campaign stage')
    from . import unified_benchmark as runner, results
    from planner_harness import accounting
    from planner_harness.training_experience import validate_snapshot
    root, output = Path(root).resolve(), Path(output).resolve()
    if stage == 'score':
        with RunLock(output / 'campaign-owner'):
            return score_stage(root, output, config, plan(root, config))
    if stage != 'score' and not host:
        raise ValueError('Generation requires --host-config with verified renderer assets/devices')
    if host and (host.get('local_results_root') or host.get('shard_count', 1) != 1):
        raise ValueError('Campaign uses its own result roots/models and one host with N GPUs; use the lower-level runner for read-only sharding')
    from . import render_profiles
    name = render_profiles.backend({'backend': host['renderer']['backend']}) if host else None
    if host and host['renderer'].get('generation', render_profiles.generation(name)) != render_profiles.generation(name):
        raise ValueError('Host generation settings differ from the supported renderer profile')
    stages = {'main': MAIN, 'all': ALL, 'self-review': SELF_REVIEW}.get(stage, (stage,))
    summary = plan(root, config)
    registry = output / 'results'
    with RunLock(output / 'campaign-owner'):
        immutable(output / 'campaign.json', {'configuration': config, 'benchmark_sha256': sha(root / 'benchmark_data/benchmark.json')})
        immutable(output / 'plan.json', summary)
        immutable(registry / 'analysis-population.json', summary['population'])
        if host:
            from .resumption import bind_deployment
            bind_deployment(output / 'host-input.json', host)
        seed_snapshot = seed_library(root, output, initial_snapshot)
        for item in stages:
            if item == 'score':
                score_stage(root, output, config, summary)
                continue
            methods, review, maintain = STAGES[item]
            local_config = stage_config(config, item, name)
            snapshot = seed_snapshot
            owner = None
            if item in {'full-experience', 'self-review-full-experience'}:
                snapshot = freeze_training(root, output) if review == 'critic' else freeze_training(root, output, review_mode='planner')
                validate_snapshot(root, load(snapshot))
                receipt = load(snapshot.with_name(snapshot.stem + '-receipt.json'))
                owner = receipt['revision']['owner']
            folder = output / item
            settings = {'model': config['model'], 'reasoning_effort': config['reasoning_effort']}
            resolved,critic,roles=runner.model_configuration(settings,host.get('models'))
            if resolved!=settings or critic!=settings:raise ValueError('Host API model roles differ from campaign configuration')
            if not (folder / 'batch.json').exists():
                runner.prepare(root, folder, splits=['train','test'], prompt_forms=config['prompt_forms'], methods=list(methods),
                               seed_start=config['seed_start'], seed_step=config['seed_step'], max_generations=local_config['max_generations'],
                               results_root=registry,
                               planner=settings, models=roles, review={'mode': review}, experience_snapshot=snapshot, experience_owner=owner,
                               budget_settings=config['task_budget'], training_maintenance=maintain,
                               backend=name, output_dimensions=host['renderer'].get('output'))
            batch = runner.verify(root, folder)
            immutable(output/'runtime-profile.json',{'profile_sha256':batch['profile_sha256']})
            expected = {'arms': list(methods), 'review': {'mode': review},
                        'max_generations': local_config['max_generations'], 'training_maintenance':maintain,
                        'seed_sequence': {'start': config['seed_start'], 'step': config['seed_step']},
                        'requested_splits': ['train','test'], 'requested_prompt_forms': config['prompt_forms'],
                        'results_root': str(registry)}
            expected['experience_seed_sha256'] = sha(snapshot)
            if owner is not None:expected['experience_owner'] = owner
            if any(batch.get(k) != v for k, v in expected.items()):
                raise ValueError('Existing batch differs from the requested campaign stage: ' + item)
            if item == 'direct' and config['reuse_direct_results']:
                reuse_direct(root, folder, batch, host, config['reuse_direct_results'])
            budget = online_budget(local_config, methods, len(batch['topics']))
            immutable(folder / 'launch-budget.json', budget)
            run_host = {**host, 'models':roles,'budget': budget, 'maintenance': config['maintenance']}
            runner.preflight(root, folder, run_host)
            accounting.install(folder / 'accounting', runner.policy(batch, budget), require_live=True)
            result = runner.run(root, folder, run_host)
            save(output / 'stage-status.json', {'stage': item, 'result': result['status']})
            bad = [p for p in result['positions'] if p['status'] in {'execution_unknown','topic_quarantined','unexecuted','model_unavailable'}]
            if bad or result['status'] not in {'settled','complete'}:
                raise RuntimeError(f'{item}: unresolved trajectories or dispatch need attention; retained original receipts, no new dependent stage')
            if item == 'pre-experience':
                freeze_training(root, output)
            elif item == 'self-review-pre-experience':
                freeze_training(root, output, review_mode='planner')
        return summary


def batch_status(output):
    """Project existing live records and settlements; never mutate the queue."""
    from collections import Counter

    output = Path(output)
    checkpoint_path = output / 'checkpoint.json'
    dispatch_path = output / 'dispatch-status.json'
    checkpoint = load(checkpoint_path) if checkpoint_path.exists() else {}
    dispatch = load(dispatch_path) if dispatch_path.exists() else {}
    rows = {}
    for record in [checkpoint, *[load(p) for p in sorted((output / 'workers').glob('*/checkpoint.json'))]]:
        for row in record.get('positions', record.get('settled', [])):
            rows[(row['topic'], row.get('method'))] = row
    # Durable per-method outcomes supersede a worker's partial summary.
    for path in sorted((output / 'methods').glob('*/*/settlement.json')):
        row = load(path)
        rows[(row['topic'], row.get('method'))] = row
    counts = dict(Counter(r['status'] for r in rows.values()))
    claims = dispatch.get('claims', [])
    claim_counts = dict(Counter(r['status'] for r in claims))
    workers = dispatch.get('workers', {})
    final_checkpoint = (checkpoint.get('status') in {'settled', 'complete', 'partial'}
                        and (not dispatch_path.exists() or checkpoint_path.stat().st_mtime_ns >= dispatch_path.stat().st_mtime_ns))
    unresolved_states = {'execution_unknown', 'topic_quarantined', 'recovery_required', 'gpu_quarantined', 'unexecuted','model_unavailable'}
    if final_checkpoint:
        state, basis = checkpoint['status'], 'final_checkpoint'
    elif dispatch:
        active = any(code is None for code in workers.values()) or claim_counts.get('claimed', 0)
        state = 'running' if active else 'partial' if any(r['status'] in unresolved_states | {'pending'} for r in claims) else 'settling'
        basis = 'latest_dispatch_record'
    elif checkpoint:
        state, basis = checkpoint.get('status', 'incomplete'), 'serial_checkpoint'
    elif rows:
        state, basis = 'incomplete', 'method_settlements'
    else:
        state = 'prepared' if (output / 'batch.json').exists() else 'not_started'
        basis = 'batch_manifest' if state == 'prepared' else 'no_run_records'
    planned = None
    if (output / 'batch.json').exists():
        batch = load(output / 'batch.json')
        planned = sum(len(t.get('methods', batch['arms'])) for t in batch['topics'])
    return {'status': state, 'status_basis': basis,
            'ready': counts.get('ready', 0), 'recorded': len(rows), 'planned': planned,
            'outcome_counts': counts, 'claim_counts': claim_counts, 'claims': claims, 'workers': workers,
            'unresolved': [r for r in rows.values() if r['status'] in unresolved_states],
            'observation': 'Read-only saved progress; worker return codes are last recorded values, not a fresh process-liveness check.'}


def status(output):
    output = Path(output)
    answer = {stage: batch_status(output / stage) for stage in STAGES}
    # Inspect historical results under their original names, never relabel an
    # actual no-knowledge run as a new pre-experience control.
    for stage in ('zero', 'knowledge', 'self-review-zero', 'self-review-knowledge'):
        if (output / stage / 'batch.json').exists():
            answer[stage] = batch_status(output / stage)
    answer['trained_snapshot'] = (output / 'trained-experience.json').exists()
    answer['self_review_trained_snapshot'] = (output / 'self-review-trained-experience.json').exists()
    answer['results'] = str(output / 'results/index.html')
    from .resumption import preview
    answer['recovery'] = preview(output)
    return answer
