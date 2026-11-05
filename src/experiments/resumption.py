"""Same-command recovery and device-independent task locations; no new scheduler."""
import copy
import socket
from pathlib import Path
from planner_harness.common import load, save
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock


def semantic_host(value):
    value = copy.deepcopy(value)
    for key in ('devices', 'host', 'lock_directory'):
        value.pop(key, None)
    value.get('renderer', {}).pop('gpu_lock', None)
    return value


def bind_deployment(path, value):
    """Keep original deployment history while allowing a different physical GPU."""
    path = Path(path)
    if path.exists():
        previous = load(path)
        from planner_harness.upgrade import record
        record(path.parent, path.stem+'-defaults', semantic_host(previous), semantic_host(value))
        effective = copy.deepcopy(previous)
        for key in ('devices', 'host', 'lock_directory'):
            if key in value: effective[key] = value[key]
        for key in ('gpu_lock', 'weights', 'model_path', 'checkpoint_path', 'asset_manifest'):
            if key in value.get('renderer', {}): effective.setdefault('renderer', {})[key] = value['renderer'][key]
        value = effective
        if previous != value:
            immutable(path.parent / 'deployment-history' / (path.stem + '-' + signature(previous) + '.json'), previous)
            save(path, value)
    else:
        immutable(path, value)
    return value


def task_directory(output, topic, method):
    """Pin new tasks independently of GPUs, or retain an existing legacy worker."""
    output = Path(output).resolve()
    key = signature({'topic': topic, 'method': method})
    path = output / 'task-locations' / (key + '.json')
    with RunLock(output / 'task-location-owner', timeout=30):
        if path.exists():
            record = load(path)
            if record['topic'] != topic or record['method'] != method:
                raise ValueError('Task location identity changed')
            directory = (output / record['directory']).resolve()
        else:
            candidates = [p for p in (output / 'workers').glob('*')
                          if (p / 'tasks' / (topic + '__' + method) / 'task.json').exists()
                          or (p / 'baselines' / topic / method).exists()
                          or (method == 'direct' and (p / 'direct' / topic).exists())]
            if len(candidates) > 1:
                raise ValueError('Multiple legacy owners for one task; reconcile before dispatch')
            directory = candidates[0] if candidates else output / 'executions' / topic / method
            immutable(path, {'topic': topic, 'method': method,
                            'directory': str(directory.relative_to(output)), 'legacy': bool(candidates)})
        if not directory.is_relative_to(output):
            raise ValueError('Task location escapes the original batch')
        return directory


def check_owners(output):
    """A live worker is not reclaimed even if the coordinator's lock was released."""
    from planner_harness.owned_process import birth
    output = Path(output)
    paths = list((output / 'workers').glob('*/worker-lifecycle.json'))
    paths += list((output / 'executions').glob('*/*/worker-lifecycle.json'))
    for path in paths:
        value = load(path)
        identity = value.get('identity', {})
        # Engine OS lock also covers workers whose old lifecycle has no identity.
        with RunLock(path.parent / 'service-owner'):
            pass
        boot = Path('/proc/sys/kernel/random/boot_id')
        started = birth(identity.get('pid', -1))
        alive = (started is not None and boot.exists()
                 and identity.get('boot_id') == boot.read_text().strip()
                 and identity.get('start_ticks') == started)
        if alive:
            stopped = path.parent / 'lifecycle' / str(value.get('generation', '')) / 'exited.json'
            if not stopped.exists():
                raise RuntimeError('Original worker still owns execution: ' + str(path.parent))
    for path in (output / 'workers').glob('*/dispatch-identity.json'):
        value = load(path)
        if value.get('host') == socket.gethostname() and birth(value['pid']) == value.get('birth') and value.get('birth') is not None:
            raise RuntimeError('Original GPU worker is still running: ' + str(path.parent))


def reconcile_batch(root, output):
    """Collect original evidence before requeueing; no external calls here."""
    from planner_harness.resumption import reconcile_accounting, recover_texts, repair_render_response
    from planner_harness.training_experience import _recover_activations
    output = Path(output)
    repaired = reconcile_accounting(output / 'accounting')
    if (output/'accounting/policy.json').exists():
        from planner_harness.accounting import lift_time_limits
        lift_time_limits(output/'accounting')
    recover_texts(output, output / 'accounting')
    from planner_harness.resumption import calls_ready, archive_remove
    for job in (output/'maintenance/jobs').glob('*'):
        for attempt in job.glob('training-attempt-*'):
            reconcile_accounting(attempt/'accounting')
            recover_texts(attempt,attempt/'accounting')
        result = job/'training-maintenance.json'
        if result.exists() and load(result).get('status') in {'failed','execution_unknown'}:
            attempts = list(job.glob('training-attempt-*'))
            if attempts and all(calls_ready(p) for p in attempts):
                archive_remove(result,job/'recovery-history')
    for path in output.rglob('request.json'):
        value = load(path)
        if value.get('kind') == 'generate' and value.get('accounting_scope'):
            repair_render_response(path)
    if (output / 'training-experience/current.json').exists():
        with RunLock(output / 'training-experience/owner', timeout=30):
            _recover_activations(root, output)
    return {'reconciled_operations': repaired, 'new_model_calls': 0, 'new_renders': 0}


def method_recoverable(output, topic, method):
    from planner_harness import accounting as a
    from planner_harness.resumption import calls_ready, planner_ready
    output = Path(output)
    if (output/'accounting/ledger.json').exists() and not (output/'accounting/policy.json').exists():return False
    ledger = a.load_ledger(output / 'accounting') if (output / 'accounting/ledger.json').exists() else {'operations': {}}
    operations = [r for r in ledger['operations'].values() if r['topic'] == topic and r.get('lane') == method]
    if any(r.get('kind') != 'model' and r['status'] not in {'not_submitted', 'reserved'} and not r.get('completion') for r in operations):
        return False
    directory = task_directory(output, topic, method)
    run = directory / 'tasks' / (topic + '__' + method) / 'run'
    if run.exists():
        state = load(run / 'state.json') if (run / 'state.json').exists() else {}
        if state.get('status') == 'complete':return True
        if not planner_ready(run) or not calls_ready(run):
            return False
        return not state.get('final') or state.get('status') == 'complete' or state['final'].get('outcome') in {'incomplete','deadline_delivery'}
    if method == 'pe-loop':
        folder = output / 'methods' / topic / method
        return not (folder / 'complete.json').exists() and calls_ready(folder)
    responses = list((directory / 'baselines' / topic / method).glob('*/response.json'))
    if method == 'direct' and responses:
        return any(load(p).get('status') == 'complete' for p in responses)
    settlement = output/'methods'/topic/method/'settlement.json'
    if settlement.exists() and load(settlement).get('status') in {'execution_unknown','recovery_required','topic_quarantined'}:
        return False
    return not operations


def reopen_method(output, topic, method):
    from planner_harness.resumption import archive_remove
    output = Path(output)
    path = output / 'methods' / topic / method / 'settlement.json'
    if path.exists() and load(path).get('status') in {'failed', 'execution_unknown', 'topic_quarantined', 'unexecuted', 'model_unavailable','recovery_required'}:
        if method_recoverable(output, topic, method):
            archive_remove(path, path.parent / 'settlement-history')
            arm = output / 'topics' / topic / (method + '.json')
            if arm.exists() and not load(arm).get('successful'):
                archive_remove(arm, path.parent / 'recovery-history')
            return True
    return False


def preview(output):
    """Read-only snapshot, suitable for check/status without model or GPU access."""
    from collections import Counter
    output = Path(output)
    if not output.exists():
        return {'status': 'new_run', 'new_topics_on_resume': None, 'extra_generation_allowance': None,
                'reason': 'No saved task manifest; inspect plan for proposed new work'}
    batches = [output] if (output / 'batch.json').exists() else [p.parent for p in output.rglob('batch.json') if (p.parent / 'inputs').exists()]
    counts = Counter()
    tasks = []
    for folder in batches:
        batch = load(folder / 'batch.json')
        ledger = load(folder/'accounting/ledger.json') if (folder/'accounting/ledger.json').exists() else {'operations':{}}
        for topic in batch['topics']:
            for method in topic.get('methods', batch['arms']):
                p = folder / 'methods' / topic['id'] / method / 'settlement.json'
                state = load(p) if p.exists() else {'status':'unfinished'}
                counts[state['status']] += 1
                records = [r for r in ledger['operations'].values() if r['topic']==topic['id'] and r.get('lane')==method]
                charged = sum(r['kind']=='render' and r['status']!='not_submitted' for r in records)
                unknown = sum(r['status'] not in {'reserved','not_submitted'} and not r.get('completion') for r in records)
                limit = 1 if method in {'direct','pe','planner-once'} else batch['max_generations']
                tasks.append({'batch':str(folder),'topic':topic['id'],'method':method,'status':state['status'],
                              'reserved_or_submitted_renders':charged,'remaining_generation_slots':max(0,limit-charged),
                              'unresolved_external_operations':unknown,'failure_kind':state.get('failure_kind')})
    return {'status': 'existing_run' if batches else 'no_saved_batch', 'method_states': dict(counts),
            'saved_batches':len(batches), 'saved_method_positions':len(tasks),
            'new_topics_on_resume':0 if batches else None,
            'tasks':tasks,
            'extra_generation_allowance': 0 if batches else None, 'process_liveness': 'checked by run before dispatch',
            'policy': 'Reuse completed work; continue original tasks; unresolved external execution stays blocked'}
