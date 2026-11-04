"""Receipt-only recovery shared by the existing runtime and batch entry points."""
from pathlib import Path
from .common import load, save, sha
from .execution import immutable, signature
from .lock import RunLock


def reconcile_accounting(root):
    from . import accounting as a
    root = Path(root)
    if not (root / 'ledger.json').exists():
        return []
    repaired = []
    for key, record in a.load_ledger(root)['operations'].items():
        directory = root / 'operations' / signature({'id': key})
        receipt = directory / 'completion.json'
        if record.get('completion') or not receipt.exists():
            continue
        binding = a.scope(root, record['topic'], record['lane'])
        try:
            a.reconcile(binding, key, evidence=receipt, reason='Recover durable original completion')
        except RuntimeError as exc:
            if 'owned by another process' in str(exc):
                continue
            raise
        repaired.append(key)
    return repaired


def call_ready(directory):
    """Whether the original call can advance without replacing an uncertain request."""
    directory = Path(directory)
    if (directory / 'response.txt').exists():
        return True
    attempts = directory / 'attempts'
    allowance = load(directory / 'allowance.json') if (directory / 'allowance.json').exists() else None
    used = 0
    for entry in sorted(attempts.glob('*')):
        if not entry.is_dir() or not entry.name.isdigit():
            continue
        used = max(used, int(entry.name))
        if (entry / 'response.txt').exists():
            return True
        if (entry / 'unknown.json').exists():
            return False
        if (entry / 'failed.json').exists():
            # A separately authorized transport recovery has its own saved range.
            # Historical failures stay recorded but do not block that range.
            if int(entry.name) >= (allowance or {}).get('first', 1) and not load(entry / 'failed.json').get('retryable'):
                return False
        elif (entry / 'submitted.json').exists():
            return False
        else:
            return True
    return allowance is None or used < allowance['last']


def recover_texts(directory, accounting_root):
    """Recreate transport answers from saved attempts/accounting, without a model."""
    from .model_call import returned_receipt, write_text_atomic
    from . import accounting as a
    directory = Path(directory)
    ledger = a.load_ledger(accounting_root) if (Path(accounting_root) / 'ledger.json').exists() else {'operations': {}}
    for allowance in directory.rglob('allowance.json'):
        call = allowance.parent
        for attempt in sorted((call / 'attempts').glob('*')):
            if not attempt.is_dir() or not attempt.name.isdigit():
                continue
            raw = attempt / 'response.txt'
            record = ledger['operations'].get(str(attempt.resolve()), {})
            completion = record.get('completion')
            if not raw.exists() and completion:
                if sha(completion['path']) != completion['sha256']:
                    raise ValueError('Original model completion changed')
                value = load(completion['path'])
                if value.get('status') == 'complete' and isinstance(value.get('result', {}).get('text'), str):
                    result = value['result']
                    save(attempt / 'result.json', {'usage': result.get('usage', value.get('usage', {})),
                         'finish_reason': result.get('finish_reason'), 'recovered_completion': completion})
                    write_text_atomic(raw, result['text'])
            if raw.exists():
                target = call / 'response.txt'
                if target.exists() and sha(target) != sha(raw):
                    raise ValueError('Conflicting saved model answers')
                if not target.exists():
                    write_text_atomic(target, raw.read_text(encoding='utf-8'))
                returned_receipt(call)
                break


def repair_render_response(path):
    """Publish only an owned accounting result; never invoke a renderer."""
    from . import accounting as a
    path = Path(path)
    request = load(path)
    if request.get('kind') != 'generate' or not request.get('accounting_scope'):
        return False
    response_path = path.with_name('response.json')
    old = load(response_path) if response_path.exists() else None
    if old and not old.get('outcome_unknown'):
        return False
    record = a.operation(request['accounting_scope'], request['sha256'])
    completion = (record or {}).get('completion')
    if not completion:
        return False
    if sha(completion['path']) != completion['sha256']:
        raise ValueError('Render completion changed')
    saved = load(completion['path'])
    if saved['status'] != 'complete':
        # An interrupted execution is not evidence of definite renderer failure.
        return False
    payload = saved['result']
    if sha(payload['video']['path']) != payload['video']['sha256']:
        raise ValueError('Recovered video changed')
    if old:
        immutable(response_path.parent / 'recovery-history' / (signature(old) + '.json'), old)
    save(response_path, {'request_sha256': request['sha256'], 'mode': request['mode'],
         'status': 'complete', 'payload': payload, 'recovered_completion': completion})
    return True


def calls_ready(directory):
    return all(call_ready(p.parent) for p in Path(directory).rglob('allowance.json'))


def planner_ready(run):
    run = Path(run)
    if not (run / 'state.json').exists():
        return True
    state = load(run / 'state.json')
    if state.get('status') == 'complete':return True
    if state.get('final') and state['final'].get('outcome') not in {'incomplete','deadline_delivery'}:
        return False
    event = state.get('pending_event')
    if event and not call_ready(run / 'calls' / event / 'transport'):
        return False
    tool = state.get('pending_tool')
    if tool:
        path = run / 'jobs' / tool / 'response.json'
        if path.exists() and load(path).get('outcome_unknown'):
            return False
    return True


def reopen_interrupted_state(run, state):
    """Remove a technical settlement only; preserve all decisions and consumed slots."""
    run = Path(run)
    if state.get('status') == 'complete' or not state.get('final'):return state
    if state['final'].get('outcome') not in {'incomplete','deadline_delivery'}:return state
    if not planner_ready(run) or not calls_ready(run):return state
    archive_remove(run/'final.json', run/'recovery-history')
    state.setdefault('recovery_history', []).append({'previous_status':state['status'], 'final':state['final'],
        'reason':'Resume interrupted original task with original generation allowance'})
    state.pop('final')
    state['status'] = 'running'
    save(run/'state.json', state)
    return state


def archive_remove(path, history):
    path = Path(path)
    if path.exists():
        value = load(path)
        immutable(Path(history) / (path.stem + '-' + signature(value) + '.json'), value)
        path.unlink()
