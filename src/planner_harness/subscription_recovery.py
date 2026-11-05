"""Offline correction of an empty cached answer from its completed SSE receipt."""
import copy
import hashlib
from contextlib import ExitStack
from pathlib import Path
import shutil
import sqlite3

from .common import load, save, sha
from .execution import immutable
from .lock import RunLock


def recover_answer(run, event, stream, *, execute=False):
    from vlm.responses_stream import replay_answer
    from .model_call import returned_receipt, write_text_atomic
    from server_runtime.queue import Queue

    run, stream = Path(run).resolve(), Path(stream).resolve()
    if not event.startswith('event-') or not event[6:].isdigit():
        raise ValueError('Use an original Planner event ID')
    call = run / 'calls' / event
    transport = call / 'transport'
    history = run / 'response-recoveries' / (event + '-' + sha(stream))
    if (history / 'completed.json').exists():
        return load(history / 'completed.json')
    worker = run.parents[2]
    with ExitStack() as stack:
        for lock in (worker / 'service-owner', run, transport):
            stack.enter_context(RunLock(lock))
        state = load(run / 'state.json')
        if (state['config'].get('workflow') != 'creative_loop_v1' or state.get('jobs')
                or state.get('generation_requests', 0)
                or any(e.get('status') != 'response_error' for e in state.get('events', []))):
            raise ValueError('This correction requires a task with no executed actions or renders')
        if state.get('final') and state['final'].get('outcome') not in {'incomplete', 'deadline_delivery', 'execution_failed'}:
            raise ValueError('Task already has a settled creative outcome')
        returned = load(transport / 'returned.json')
        entry = transport / 'attempts' / f"{returned['attempt']:02d}"
        result = load(entry / 'result.json')
        audit = result.get('client_execution') or load(entry / 'client-audit/summary.json')
        replay = replay_answer(stream)
        if not replay['text'].strip():
            return {'status': 'completed_without_answer', 'event': event,
                    'stream_sha256': replay['stream_sha256'], 'model_calls': 0, 'renders': 0}
        if not audit.get('response_id') or audit['response_id'] != replay['response_id']:
            raise ValueError('Stream belongs to a different model response')
        if audit.get('stream_sha256') != replay['stream_sha256']:
            relay = load(stream.with_name('summary.json'))
            if (relay.get('request_id') != audit.get('request_id')
                    or relay.get('response_id') != audit['response_id']
                    or relay.get('stream_sha256') != replay['stream_sha256']):
                raise ValueError('Stream hash does not match its original client or relay receipt')
        raw_files = [entry / 'response.txt', transport / 'response.txt', call / 'response.txt']
        if any(p.exists() and p.read_text(encoding='utf-8').strip() for p in raw_files):
            raise ValueError('An existing nonempty answer is retained unchanged')
        if returned.get('sha256') != sha(transport / 'response.txt'):
            raise ValueError('Original empty returned receipt changed')
        after = copy.deepcopy(state)
        after['events'] = [e for e in after.get('events', []) if e.get('event_id') != event]
        after['status'] = 'running'
        after['pending_event'] = event
        after.pop('final', None)
        after.setdefault('unresolved_calls', {}).pop(event, None)
        # Keep attempts, all other calls, usage, generation counts and clocks.
        output = next((p for p in run.parents if (p / 'batch.json').exists()), None)
        scope_path = run / 'budget-scope.json'
        scope = load(scope_path) if scope_path.exists() else None
        remove = [run / 'final.json', run / 'events' / (event + '.json')]
        claims = []
        if output and scope:
            topic, method = scope['topic'], scope['lane']
            for p in (output / 'methods' / topic / method / 'settlement.json',
                      output / 'topics' / topic / (method + '.json')):
                if p.exists():
                    if load(p).get('status') == 'ready' or load(p).get('selected'):
                        raise ValueError('A delivered method is retained unchanged')
                    remove.append(p)
            db = output / 'device-queue.sqlite3'
            if db.exists():
                with sqlite3.connect(db) as connection:
                    claims = connection.execute('SELECT id,status FROM tasks WHERE id IN (?,?)',
                        (topic, topic + '__training_' + method)).fetchall()
                if any(status == 'claimed' for _, status in claims):
                    raise ValueError('Original device claim is still active')
        queue = Queue(worker / 'queue.sqlite3')
        jobs = [j for j in queue.rows() if j['kind'] == 'planner' and j['payload'].get('run') == str(run)]
        if not jobs or any(j['state'] == 'running' for j in jobs):
            raise ValueError('A stopped original Planner queue job is required')
        job = jobs[-1]
        remove.append(worker / 'jobs' / str(job['id']) / 'receipt.json')
        ledger = Path(scope['root']) / 'ledger.json' if scope else None
        plan = {'status': 'prepared_not_executed' if execute else 'recoverable', 'event': event,
                'run': str(run), 'stream_sha256': replay['stream_sha256'],
                'response_id': replay['response_id'], 'request_id': audit.get('request_id'),
                'selection': replay['selection'], 'characters': len(replay['text']),
                'answer_sha256': hashlib.sha256(replay['text'].encode('utf-8')).hexdigest(), 'history': str(history),
                'ledger_sha256': sha(ledger) if ledger else None, 'model_calls': 0, 'renders': 0}
        if not execute:
            return plan
        files = [run / 'state.json', transport / 'returned.json', entry / 'result.json',
                 call / 'input.json', transport / 'input.json', *raw_files, *remove]
        immutable(history / 'plan.json', plan)
        immutable(history / 'queue-job.json', job)
        for path in files:
            if path.exists():
                if path.is_relative_to(run):
                    relative = path.relative_to(run)
                elif output and path.is_relative_to(output):
                    relative = Path('batch') / path.relative_to(output)
                else:
                    relative = Path('service') / path.relative_to(worker)
                target = history / 'original' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        immutable(history / 'replayed-answer.json', replay)
        for path in remove:
            if path.exists():
                path.unlink()
        (transport / 'returned.json').unlink()
        for path in raw_files:
            write_text_atomic(path, replay['text'])
        returned_receipt(transport)
        after.setdefault('response_recoveries', []).append({'event_id': event, 'record': str(history / 'plan.json')})
        save(run / 'state.json', after)
        with queue.transaction() as db:
            db.execute("UPDATE jobs SET state='queued',owner=NULL,result=NULL,finished=NULL,expanded=0,error=? WHERE id=?",
                       ('retry authorized: Offline correction from original completed SSE', job['id']))
        if claims:
            with sqlite3.connect(output / 'device-queue.sqlite3') as db:
                db.executemany('UPDATE tasks SET status="pending",owner=NULL WHERE id=?', [(r[0],) for r in claims])
        if ledger and sha(ledger) != plan['ledger_sha256']:
            raise ValueError('Accounting changed during offline response correction')
        immutable(history / 'completed.json', plan)
        return plan
