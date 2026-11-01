"""Approved scheduling adapter; all frozen experiment modules remain unchanged."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait
import multiprocessing
import json
import os
import signal
import sqlite3
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock
from experiments.creative_fewshot import (ARMS, cache_judgment, verify_arm,
                                         verify_batch, copy_verified, init_worker,
                                         run_arm, seal_topic, verify_archive, PAIRS)
from evaluation.creative import JUDGES


def eligible(root, output, topic):
    """Verify complete receipts before exposing only first/delivery candidates."""
    root, output = Path(root), Path(output)
    batch = load(output / 'batch.json')
    result = {}
    for arm in ARMS:
        receipt = output / 'topics' / topic['id'] / (arm + '.json')
        if receipt.exists():
            data = load(receipt)
            verify_arm(topic, arm, data, batch['profile_sha256'])
            for position, identity in [('first', data['first']), ('final', data['selected'])]:
                result['direct' if arm == 'direct' else arm + '_' + position] = data['videos'][identity]
            continue
        if arm == 'direct':
            continue
        states = list(output.glob('workers/*/tasks/' + topic['id'] + '__' + arm + '/run/state.json'))
        if len(states) > 1:
            raise ValueError('More than one worker owns the same arm')
        if not states:
            continue
        state = load(states[0])
        videos = [(k,v) for k,v in state['videos'].items() if k != 'source' and not v.get('imported')]
        if not videos:
            continue
        identity, video = videos[0]
        folder = states[0].parent / 'jobs' / video['job_id']
        request, response = load(folder / 'request.json'), load(folder / 'response.json')
        if signature({k:v for k,v in request.items() if k != 'sha256'}) != request['sha256']:
            raise ValueError('Generation request identity changed')
        if response['status'] != 'complete' or response['request_sha256'] != request['sha256']:
            raise ValueError('First output has no complete matching render receipt')
        native = response['payload']['video']
        if native['sha256'] != video['sha256'] or sha(native['path']) != video['sha256'] or sha(video['path']) != video['sha256']:
            raise ValueError('First output bytes differ from the completed render receipt')
        record = {'topic':topic['id'], 'arm':arm, 'candidate':identity, 'video_sha256':video['sha256'],
                  'request_sha256':request['sha256'], 'response_sha256':sha(folder / 'response.json'),
                  'profile_sha256':batch['profile_sha256']}
        immutable(output / 'scheduling' / 'eligibility' / topic['id'] / (arm + '-first.json'), record)
        result[arm + '_first'] = video
    if sha(root / topic['source']) != topic['source_sha256']:
        raise ValueError('Original source changed')
    return result


def score_available(root, output, topic, *, judges=None):
    output = Path(output)
    positions = eligible(root, output, topic)
    def provider(name):
        rows = {}
        with RunLock(output / 'judge-providers' / name, timeout=7200):
            for position, video in positions.items():
                rows[position] = cache_judgment(root, output, topic, video, name=name,
                                               judge=judges[name] if judges else None)
                print(json.dumps({'event':'judged', 'topic':topic['id'], 'position':position,
                                  'judge':name, 'key':rows[position]['key']}), flush=True)
        return rows
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {name:pool.submit(provider,name) for name in JUDGES}
        results = {name:f.result() for name,f in futures.items()}
    save(output / 'scheduling' / (topic['id'] + '-positions.json'), results)
    return results


class Scoring:
    """One executor per provider; shared OS locks and the existing immutable cache."""
    def __init__(self, root, output, *, judges=None):
        self.root, self.output, self.judges = Path(root), Path(output), judges
        self.pools = {name:ThreadPoolExecutor(max_workers=1) for name in JUDGES}
        self.jobs = {}

    def submit_available(self, topic):
        positions = eligible(self.root, self.output, topic)
        for name in JUDGES:
            for position, video in positions.items():
                key = (topic['id'], name, video['sha256'])
                if key not in self.jobs:
                    self.jobs[key] = self.pools[name].submit(self.score, topic, name, video)
        return positions

    def score(self, topic, name, video):
        with RunLock(self.output / 'judge-providers' / name, timeout=7200):
            result = cache_judgment(self.root, self.output, topic, video, name=name,
                                   judge=self.judges[name] if self.judges else None)
        print(json.dumps({'event':'judged','topic':topic['id'],'judge':name,
                          'candidate_sha256':video['sha256'],'key':result['key']}), flush=True)
        return result

    def results(self, topic):
        positions = self.submit_available(topic)
        required = {'direct','full_first','full_final','none_first','none_final'}
        if set(positions) != required:
            raise ValueError('All five delivered reporting positions are required before archival')
        return {name:{position:self.jobs[(topic['id'],name,video['sha256'])].result()
                      for position,video in positions.items()} for name in JUDGES}

    def close(self):
        for pool in self.pools.values():
            pool.shutdown(wait=True)


class UnscoredIntermediate(dict):
    """The frozen HTML writer can display explicitly unscored trajectory videos."""
    def __missing__(self, identity):
        return {'result':{'report':{'main_scores':{
            'status':'not independently scored',
            'reason':'Trajectory candidate outside the five approved reporting positions.'}}}}


def archive_topic(root, output, topic, arms, positions):
    judgments = {}
    for name in JUDGES:
        groups = {}
        for arm in ARMS:
            result = arms[arm]
            chosen = {'direct':result['first']} if arm == 'direct' else {
                arm + '_first':result['first'], arm + '_final':result['selected']}
            rows = UnscoredIntermediate()
            for position, identity in chosen.items():
                row = positions[name][position]
                if row['result']['output_sha256'] != result['videos'][identity]['sha256']:
                    raise ValueError('Position judgment does not match its delivered candidate')
                rows[identity] = row
            groups[arm] = rows
        judgments[name] = groups
    scope = {'authorization':'2026-11-01 five-position early judging amendment',
             'positions':{arm:{'first':r['first'],'final':r['selected']} for arm,r in arms.items()},
             'unscored_intermediates':{arm:[v for v in r['videos'] if v not in {r['first'],r['selected']}] for arm,r in arms.items()},
             'deduplication':'Frozen source/request/candidate/protocol/model/adapter identity',
             'schedule_adapter_sha256':sha(Path(__file__))}
    immutable(Path(output)/'topics'/topic['id']/'archive'/'scoring-scope.json',scope)
    return seal_topic(root, output, topic, arms, judgments)


def retire_legacy(root, output, parent_pid, worker_pid):
    """Retire only a stopped parent and an idle/returning worker at a durable boundary."""
    root, output = Path(root), Path(output)
    complete = output/'scheduling'/'legacy-retired.json'
    if complete.exists():
        return True
    parent = Path('/proc')/str(parent_pid)
    worker = Path('/proc')/str(worker_pid)
    cmd = (parent/'cmdline').read_bytes().replace(b'\0',b' ').decode()
    if '/creative-20261101/run_batch.py' not in cmd:
        raise RuntimeError('Legacy parent PID identity differs')
    state = next(x for x in (parent/'status').read_text().splitlines() if x.startswith('State:'))
    if 'T' not in state.split(':',1)[1].strip().split()[0]:
        raise RuntimeError('Legacy parent must remain stopped; old judging is not authorized')
    wchan = (worker/'wchan').read_text().strip()
    if wchan not in {'anon_pipe_read','anon_pipe_write','pipe_read','pipe_write'}:
        return False
    os.kill(worker_pid,signal.SIGSTOP)
    safe = False
    try:
        with sqlite3.connect('file:'+str(output/'workers/0/queue.sqlite3')+'?mode=ro',uri=True) as db:
            active = db.execute("SELECT id,key,kind,state FROM jobs WHERE state='running'").fetchall()
        states = []
        for path in output.glob('workers/*/tasks/*/run/state.json'):
            data = load(path)
            states.append({'path':str(path),'status':data['status'],'pending_tool':data.get('pending_tool')})
            if data['status'] != 'complete':
                return False
        if active or not states:
            return False
        batch = verify_batch(root,output)
        first = batch['topics'][0]
        receipt = output/'topics'/first['id']/'full.json'
        if not receipt.exists():
            return False
        verify_arm(first,'full',load(receipt),batch['profile_sha256'])
        record = {'at_unix':time.time(),'parent_pid':parent_pid,'worker_pid':worker_pid,
                  'worker_wait_before_stop':wchan,'active_queue_jobs':active,'states':states,
                  'reason':'Completed arm receipt and idle IPC boundary; no active model or render call',
                  'frozen_profile_sha256':batch['profile_sha256']}
        immutable(output/'scheduling'/'legacy-retirement-authorized.json',record)
        os.kill(worker_pid,signal.SIGKILL)
        os.kill(parent_pid,signal.SIGKILL)
        safe = True
        save(complete,{**record,'action':'Retired idle legacy processes; frozen files unchanged'})
        print(json.dumps({'event':'legacy_retired','parent':parent_pid,'worker':worker_pid}),flush=True)
        return True
    finally:
        if not safe:
            os.kill(worker_pid,signal.SIGCONT)


def advance(root, output, execute_arm, *, judges=None, poll_seconds=30):
    """Render sequentially on the supplied worker while judges consume eligible outputs."""
    from evaluation.creative import paired_summary
    output = Path(output)
    batch = verify_batch(root,output)
    summaries = []
    scoring = Scoring(root,output,judges=judges)
    try:
        with ThreadPoolExecutor(max_workers=1) as generation:
            for topic in batch['topics']:
                directory = output/'topics'/topic['id']
                if (directory/'archive-manifest.json').exists():
                    summaries.append(verify_archive(directory))
                    continue
                save(output/'checkpoint.json',{'status':'running','topic':topic['id'],'stage':'generation_and_eligible_judging'})
                arms = {}
                scoring.submit_available(topic)
                for arm in ARMS:
                    receipt = directory/(arm+'.json')
                    if receipt.exists():
                        result = load(receipt)
                    else:
                        future = generation.submit(execute_arm,topic,arm)
                        while not future.done():
                            wait([future],timeout=poll_seconds)
                            scoring.submit_available(topic)
                        result = future.result()
                    verify_arm(topic,arm,result,batch['profile_sha256'])
                    immutable(receipt,result)
                    arms[arm] = result
                    scoring.submit_available(topic)
                save(output/'checkpoint.json',{'status':'running','topic':topic['id'],'stage':'independent_judging'})
                positions = scoring.results(topic)
                save(output/'scheduling'/(topic['id']+'-positions.json'),positions)
                summaries.append(archive_topic(root,output,topic,arms,positions))
                save(output/'checkpoint.json',{'status':'running','topic':topic['id'],'stage':'archived'})
        combined = {name:{a+'__to__'+b:paired_summary([
            (s['judges'][name]['positions'][a]['result']['report'],s['judges'][name]['positions'][b]['result']['report'])
            for s in summaries]) for a,b in PAIRS} for name in JUDGES}
        result = {'status':'complete','topics':summaries,'comparisons':combined,'data_role':'development_regression'}
        immutable(output/'results.json',result)
        save(output/'checkpoint.json',{'status':'complete','topics':len(summaries)})
        return result
    except BaseException as exc:
        current = load(output/'checkpoint.json')
        save(output/'checkpoint.json',{**current,'status':'blocked','error_type':type(exc).__name__,'error':str(exc)})
        raise
    finally:
        scoring.close()


def run(root, output, host, *, legacy_parent=None, legacy_worker=None):
    output = Path(output).resolve()
    batch = verify_batch(root,output)
    if host.get('devices') != [0]:
        raise ValueError('This deployment is authorized for the existing single device 0 only')
    immutable(output/'scheduling'/'amendment.json',{
        'authorization':'2026-11-01 explicit execution handoff and five-position schedule',
        'adapter_sha256':sha(Path(__file__)),'frozen_profile_sha256':batch['profile_sha256'],
        'frozen_files_modified':False,'reporting_positions':['direct','full_first','full_final','none_first','none_final'],
        'intermediate_candidates':'Retain videos and complete traces without final scores',
        'generation_limits':None,'judge_feedback_to_planner':False})
    with RunLock(output/'schedule-owner'), RunLock(output/'scoring-owner',timeout=7200):
        if legacy_parent:
            scoring = Scoring(root,output)
            try:
                topic = batch['topics'][0]
                while not retire_legacy(root,output,legacy_parent,legacy_worker):
                    scoring.submit_available(topic)
                    time.sleep(30)
            finally:
                scoring.close()
        with RunLock(output/'batch-owner'):
            from experiments.preflight import verify_provider_receipt
            for name in JUDGES:
                verify_provider_receipt(output,name)
            immutable(output/'host.json',host)
            context = multiprocessing.get_context('spawn')
            pool = context.Pool(1,initializer=init_worker,initargs=(0,str(root),str(output),host))
            try:
                return advance(root,output,lambda topic,arm:pool.apply(run_arm,(topic,arm)))
            finally:
                pool.close()
                pool.join()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['score','run'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--topic')
    parser.add_argument('--host-config',type=Path)
    parser.add_argument('--legacy-parent',type=int)
    parser.add_argument('--legacy-worker',type=int)
    args = parser.parse_args()
    batch = verify_batch(ROOT, args.output)
    if args.command == 'score':
        topic = next(t for t in batch['topics'] if t['id'] == args.topic)
        with RunLock(args.output / 'scoring-owner'):
            score_available(ROOT, args.output, topic)
    else:
        if not args.host_config or bool(args.legacy_parent)!=bool(args.legacy_worker):
            parser.error('Run needs the existing host config and either both legacy PIDs or neither')
        run(ROOT,args.output,load(args.host_config),legacy_parent=args.legacy_parent,legacy_worker=args.legacy_worker)


if __name__ == '__main__':
    main()
