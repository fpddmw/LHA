"""Prepare one interrupted text call for continuation; never dispatch API/GPU work.

Copy this standalone script into a frozen checkout's scripts directory. It uses
the original runtime and leaves its protocol, prompts, clocks and videos intact.
"""
from contextlib import ExitStack
import argparse
import copy
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from planner_harness import accounting
from planner_harness.common import load, save, sha, stamp
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock
from server_runtime.queue import Queue


def _call(run, state):
    event = state.get('pending_event')
    job = state.get('pending_tool')
    if event and not job:
        return run / 'calls' / event / 'transport', 'planner', None
    if job and state['jobs'][job]['kind'] == 'critique':
        review = run / 'jobs' / job / 'one-shot-critic'
        current = load(review / 'state.json')
        return review / 'calls' / f"review-{current['attempts'] + 1:04d}" / 'call', 'critic', job
    raise ValueError('Choose the pending Planner or qualitative Critic text call')


def _inspect(run, audit_sha256, reason):
    state = load(run / 'state.json')
    clock = state.get('online_clock') or {}
    deadline = clock.get('deadline_unix')
    if state.get('final') or clock.get('frozen_unix') or (deadline is not None and time.time() >= deadline):
        raise ValueError('Original task is settled or expired; retain its existing result')
    if state.get('status') != 'needs_reconciliation':
        raise ValueError('This entry resumes a recorded needs_reconciliation task')
    call, role, job_id = _call(run, state)
    if not call.resolve().is_relative_to(run):
        raise ValueError('Call must belong to the original run')
    attempts = sorted(p for p in (call / 'attempts').iterdir() if p.is_dir() and p.name.isdigit())
    entry = attempts[-1]
    if any((p / 'unknown.json').exists() for p in attempts[:-1]):
        raise ValueError('An earlier unresolved attempt needs its own reconciliation')
    if (call / 'response.txt').exists() or any((p / 'response.txt').exists() for p in attempts):
        raise ValueError('An original answer exists; collect it through the original runtime')
    unknown = load(entry / 'unknown.json')
    audit_path = entry / 'client-audit/summary.json'
    audit = load(audit_path)
    if sha(audit_path) != audit_sha256:
        raise ValueError('Client audit differs from the inspected SHA256')
    client = unknown.get('client_execution') or {}
    if not client.get('request_id') or client['request_id'] != audit.get('request_id'):
        raise ValueError('Unknown receipt and client audit must identify the same request')
    error = audit.get('relay_error') or {}
    if (audit.get('http_status') != 502 or audit.get('outcome') != 'execution_unknown'
            or error.get('code') != 'relay_execution_unknown' or not audit.get('finished_unix')
            or audit.get('terminal_event')):
        raise ValueError('This recovery entry accepts a completed local relay-502 interruption')
    stream = entry / 'client-audit/stream.bin'
    if sha(stream) != audit.get('stream_sha256'):
        raise ValueError('Original relay error body changed')
    scope = unknown['scope']
    accounting.check_task(scope)
    operation = accounting.operation(scope, str(entry))
    if not operation or operation['kind'] != 'model' or not operation.get('completion'):
        raise ValueError('The original local model operation must have finished')
    completion = operation['completion']
    if sha(completion['path']) != completion['sha256'] or load(completion['path'])['status'] != 'failed':
        raise ValueError('Expected the original failed local model completion')
    worker, output = run.parents[2], run.parents[4]
    if run.parent.parent.name != 'tasks' or worker.parent.name != 'workers':
        raise ValueError('Use the original workers/DEVICE/tasks/TASK/run directory')
    queue = Queue(worker / 'queue.sqlite3')
    rows = [r for r in queue.rows() if
            (role == 'planner' and r['kind'] == 'planner' and r['payload'].get('run') == str(run)) or
            (role == 'critic' and r['kind'] == 'tool' and
             r['payload'].get('request') == str(run / 'jobs' / job_id / 'request.json'))]
    if not rows:
        raise ValueError('Original service queue job is absent')
    row = max(rows, key=lambda r: r['id'])
    if row['state'] not in {'complete', 'failed', 'needs_review'}:
        raise ValueError('Original queue job is still runnable or owned')
    if role == 'planner' and row['state'] == 'complete' and (row.get('result') or {}).get('state', {}).get('status') != 'needs_reconciliation':
        raise ValueError('Completed Planner queue result has a different outcome')
    after = copy.deepcopy(state)
    after['status'] = 'waiting_tool' if role == 'critic' else 'interrupted'
    after.setdefault('unresolved_calls', {}).pop(state.get('pending_event'), None)
    if job_id:
        after.setdefault('unresolved_jobs', {}).pop(job_id, None)
    files = [run / 'state.json', call / 'allowance.json', entry / 'unknown.json',
             worker / 'jobs' / str(row['id']) / 'receipt.json',
             worker / 'jobs' / str(row['id']) / 'planner-state.json',
             worker / 'jobs' / str(row['id']) / 'started.json']
    remove = [entry / 'unknown.json', worker / 'jobs' / str(row['id']) / 'receipt.json']
    if job_id:
        response = run / 'jobs' / job_id / 'response.json'
        if (response.parent / 'collected.json').exists() or load(response).get('status') != 'failed':
            raise ValueError('Critic tool must have its original uncollected failed response')
        files.append(response)
        remove.append(response)
    topic, method = scope['topic'], scope['lane']
    for path, field, allowed in [
            (output / 'topics' / topic / (method + '.json'), 'outcome', {'execution_unknown'}),
            (output / 'methods' / topic / method / 'settlement.json', 'status', {'execution_unknown', 'topic_quarantined'})]:
        if path.exists():
            value = load(path)
            if value.get(field) not in allowed:
                raise ValueError('Original method already has a different settlement')
            files.append(path)
            remove.append(path)
    claims = []
    db_path = output / 'device-queue.sqlite3'
    if db_path.exists():
        with sqlite3.connect(db_path) as db:
            claims = db.execute('SELECT id,status,owner FROM tasks WHERE id IN (?,?)',
                                (topic, topic + '__training_' + method)).fetchall()
        if any(status == 'claimed' for _, status, _ in claims):
            raise ValueError('The device task is still claimed; finish its owner first')
    return {'version': 'lha-model-transport-recovery-v1', 'at': stamp(), 'reason': reason,
            'run': str(run), 'worker': str(worker), 'output': str(output), 'call': str(call),
            'entry': str(entry), 'role': role, 'scope': scope, 'operation': operation,
            'audit_path': str(audit_path), 'audit_sha256': audit_sha256,
            'request_id': audit['request_id'], 'relay_error': error,
            'submission': 'possibly_submitted', 'cost': 'original unknown charge retained',
            'next_attempt': int(entry.name) + 1, 'clock': clock, 'queue_job': row,
            'claims': claims, 'state_after': after,
            'files': {str(p.relative_to(output)): sha(p) for p in files if p.exists()},
            'remove': [str(p.relative_to(output)) for p in remove if p.exists()],
            'input_sha256': sha(call / 'input.json'), 'model_calls': 0, 'renders': 0}


def recover(run, audit_sha256, reason, *, execute=False, abandon_response=False):
    run = Path(run).resolve()
    if not reason.strip() or len(audit_sha256) != 64 or any(c not in '0123456789abcdef' for c in audit_sha256):
        raise ValueError('Supply the inspected client-audit SHA256 and a recovery reason')
    if execute and not abandon_response:
        raise ValueError('Use --abandon-response to retain unknown usage and request one replacement text attempt')
    worker, output = run.parents[2], run.parents[4]
    history = run / 'model-recoveries' / audit_sha256
    with ExitStack() as stack:
        for lock in (output / 'unified-owner', output / 'batch-owner',
                     output / ('device-owner-' + worker.name), worker / 'service-owner', run):
            stack.enter_context(RunLock(lock))
        if (history / 'completed.json').exists():
            return load(history / 'completed.json')
        existing = history / 'plan.json'
        plan = load(existing) if existing.exists() else _inspect(run, audit_sha256, reason)
        call, entry = Path(plan['call']), Path(plan['entry'])
        stack.enter_context(RunLock(call))
        opdir = Path(plan['scope']['root']) / 'operations' / signature({'id': str(entry)})
        stack.enter_context(RunLock(opdir / 'execution-owner'))
        if not execute:
            return {k: v for k, v in plan.items() if k not in {'state_after', 'queue_job', 'operation', 'files', 'remove'}}
        state = load(run / 'state.json')
        if state.get('final') or state.get('online_clock') != plan['clock']:
            raise ValueError('Task changed after recovery inspection')
        if sha(call / 'input.json') != plan['input_sha256'] or (
                sha(run / 'state.json') != plan['files'][str((run / 'state.json').relative_to(output))]
                and signature(state) != signature(plan['state_after'])):
            raise ValueError('Original call or task progressed after recovery inspection')
        accounting.check_task(plan['scope'])
        immutable(existing, plan)
        # Copy originals first. Interrupted preparation can replay this same journal.
        for name, digest in plan['files'].items():
            original, backup = output / name, history / 'originals' / name
            if backup.exists():
                if sha(backup) != digest:
                    raise ValueError('Recovery backup changed')
                continue
            if sha(original) != digest:
                raise ValueError('Original changed after recovery inspection: ' + name)
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(original.read_bytes())
        immutable(history / 'original-operation.json', plan['operation'])
        for name in plan['remove']:
            (output / name).unlink(missing_ok=True)
        save(entry / 'failed.json', {'type': 'InterruptedTextResponse', 'retryable': True,
             'failure_kind': 'model_transport', 'submission': 'possibly_submitted',
             'cost': 'unknown_retained', 'recovery': str(existing), 'audit_sha256': audit_sha256})
        save(call / 'allowance.json', {'first': plan['next_attempt'], 'last': plan['next_attempt']})
        save(run / 'state.json', plan['state_after'])
        queue = Queue(worker / 'queue.sqlite3')
        with queue.transaction() as db:
            db.execute("UPDATE jobs SET state='queued',owner=NULL,result=NULL,finished=NULL,expanded=0,error=? WHERE id=?",
                       ('retry authorized: ' + reason, plan['queue_job']['id']))
        if plan['claims']:
            with sqlite3.connect(output / 'device-queue.sqlite3') as db:
                db.executemany('UPDATE tasks SET status="pending",owner=NULL WHERE id=?',
                               [(r[0],) for r in plan['claims']])
        result = {'status': 'prepared_not_executed', 'role': plan['role'], 'run': str(run),
                  'call': str(call), 'next_attempt': plan['next_attempt'], 'clock': plan['clock'],
                  'submission': plan['submission'], 'cost': plan['cost'],
                  'queue_job': plan['queue_job']['id'], 'history': str(history), 'model_calls': 0, 'renders': 0}
        immutable(history / 'completed.json', result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--audit-sha256', required=True)
    parser.add_argument('--reason', required=True)
    parser.add_argument('--execute', action='store_true', help='Prepare original state and queue; no dispatch')
    parser.add_argument('--abandon-response', action='store_true', help='Keep unknown usage; authorize one replacement text attempt')
    args = parser.parse_args()
    print(json.dumps(recover(args.run, args.audit_sha256, args.reason,
                            execute=args.execute, abandon_response=args.abandon_response), indent=2))


if __name__ == '__main__':
    main()
