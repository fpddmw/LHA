"""Canonical five-position scheduler for new bounded creative v2 cohorts."""
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
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock
from planner_harness.resources import ResourceExhausted
from planner_harness.accounting import ExternalExecutionUnknown
from experiments.creative_benchmark import (ARMS, verify_arm,
                                         verify_batch, copy_verified, init_worker,
                                         run_arm, seal_topic, verify_archive, PAIRS)
from evaluation.creative import JUDGES
from experiments.creative_benchmark import cache_judgment, missing_judgment, outcome_counts, shared_source_plan, isolated_arm


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
                if identity is not None:
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
    source_plan = shared_source_plan(root,output,topic,model=judges["glm5.3flash"] if judges else None) if positions else None
    def provider(name):
        rows = {}
        with RunLock(output / 'judge-providers' / name, timeout=7200):
            for position, video in positions.items():
                rows[position] = cache_judgment(root, output, topic, video, name=name,
                                               judge=judges[name] if judges else None, source_plan=source_plan)
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
        source_plan = shared_source_plan(self.root,self.output,topic,model=self.judges["glm5.3flash"] if self.judges else None)
        with RunLock(self.output / 'judge-providers' / name, timeout=7200):
            result = cache_judgment(self.root, self.output, topic, video, name=name,
                                   judge=self.judges[name] if self.judges else None, source_plan=source_plan)
        print(json.dumps({'event':'judged','topic':topic['id'],'judge':name,
                          'candidate_sha256':video['sha256'],'key':result['key']}), flush=True)
        return result

    def results(self, topic):
        positions = self.submit_available(topic)
        required = ['direct','full_first','full_final','none_first','none_final']
        result = {name:{position:(self.jobs[(topic['id'],name,positions[position]['sha256'])].result()
                                  if position in positions else missing_judgment('no_delivered_candidate'))
                      for position in required} for name in JUDGES}

        from evaluation.final_suite import blind_pairs
        blind_pairs(self.root,self.output,topic,positions,judges=self.judges)
        return result

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
                if identity is None:
                    continue
                row = positions[name][position]
                if row['result'].get('status') == 'missing':
                    rows[identity] = row
                    continue
                if row['result']['output_sha256'] != result['videos'][identity]['sha256']:
                    raise ValueError('Position judgment does not match its delivered candidate')
                rows[identity] = row
            groups[arm] = rows
        judgments[name] = groups
    scope = {'authorization':'2026-11-01 five-position early judging amendment',
             'positions':{arm:{'first':r['first'],'final':r['selected']} for arm,r in arms.items()},
             'unscored_intermediates':{arm:[v for v in r['videos'] if v not in {r['first'],r['selected']}] for arm,r in arms.items()},
             'deduplication':'Frozen source/request/candidate/protocol/model/adapter identity',
             'validation_status':{name:{p:r.get('validation_status','native_passed') for p,r in rows.items()} for name,rows in positions.items()},
             'supplemental_validator_sha256':sha(Path(__file__).with_name('creative_final_validation.py')),
             'schedule_adapter_sha256':sha(Path(__file__))}
    immutable(Path(output)/'topics'/topic['id']/'archive'/'scoring-scope.json',scope)
    return seal_topic(root, output, topic, arms, judgments)


def retire_legacy(*args, **kwargs):
    """Historical forced retirement is disabled in the current scheduler."""
    raise RuntimeError('Legacy process signals are disabled. Request identity-bound cooperative drain with server_runtime.lifecycle; old workers require an explicit operator migration.')


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
                    if (output/'accounting/policy.json').exists():
                        from planner_harness.accounting import topic_scope,close_topic
                        close_topic(topic_scope(output,topic['id']))
                    continue
                save(output/'checkpoint.json',{'status':'running','topic':topic['id'],'stage':'generation_and_eligible_judging'})
                from planner_harness.accounting import topic_scope,admit_topic
                if (output/'accounting/policy.json').exists():admit_topic(topic_scope(output,topic['id']))
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
                        try:result = future.result()
                        except ExternalExecutionUnknown as exc:
                            result=isolated_arm(output,topic,arm,batch['profile_sha256'],reason=str(exc),outcome='execution_unknown',evidence={'supervised_worker_retained':True})
                        except ResourceExhausted as exc:
                            result=isolated_arm(output,topic,arm,batch['profile_sha256'],reason=str(exc),outcome='resource_unavailable',evidence={'submission_refused':True})
                    verify_arm(topic,arm,result,batch['profile_sha256'])
                    immutable(receipt,result)
                    arms[arm] = result
                    scoring.submit_available(topic)
                save(output/'checkpoint.json',{'status':'running','topic':topic['id'],'stage':'independent_judging'})
                positions = scoring.results(topic)
                save(output/'scheduling'/(topic['id']+'-positions.json'),positions)
                summaries.append(archive_topic(root,output,topic,arms,positions))
                if (output/'accounting/policy.json').exists():
                    from planner_harness.accounting import topic_scope,close_topic
                    close_topic(topic_scope(output,topic['id']))
                save(output/'checkpoint.json',{'status':'running','topic':topic['id'],'stage':'archived'})
        combined = {name:{a+'__to__'+b:paired_summary([
            (s['judges'][name]['positions'][a]['result']['report'],s['judges'][name]['positions'][b]['result']['report'])
            for s in summaries]) for a,b in PAIRS} for name in JUDGES}
        result = {'status':'complete','topics':summaries,'comparisons':combined,'data_role':'development_regression',
                  'planned_topics':len(batch['topics']),'outcome_counts':outcome_counts(summaries)}
        from evaluation.final_suite import aggregate
        result['metrics']=aggregate(summaries)
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
    from planner_harness.accounting import validate_policy,REQUIRED_QUOTES,validate_cohort
    validate_cohort(host.get('budget'),max_generations=batch['max_generations'],topics=batch['topics'])
    devices = host.get('devices', [])
    if not 1 <= len(devices) <= 2 or len(set(map(str, devices))) != len(devices):
        raise ValueError('Supply one or two distinct explicitly authorized existing devices')
    if legacy_parent or legacy_worker:
        retire_legacy()
    immutable(output/'scheduling'/'amendments'/(sha(Path(__file__))+'.json'),{
        'authorization':'code policy only; actual execution requires the current user authorization',
        'adapter_sha256':sha(Path(__file__)),'frozen_profile_sha256':batch['profile_sha256'],
        'supplemental_validator_sha256':sha(Path(__file__).with_name('creative_final_validation.py')),
        'frozen_files_modified':False,'reporting_positions':['direct','full_first','full_final','none_first','none_final'],
        'intermediate_candidates':'Retain videos and complete traces without final scores',
        'generation_limits':batch['max_generations'], 'turn_limit':batch['max_turns'],'judge_feedback_to_planner':False})
    with RunLock(output/'schedule-owner'), RunLock(output/'scoring-owner',timeout=7200):
        with RunLock(output/'batch-owner'):
            from experiments.preflight import verify_provider_receipt
            for name in JUDGES:
                verify_provider_receipt(output,name)
            immutable(output/'host.json',host)
            from planner_harness.accounting import install,REQUIRED_QUOTES,validate_policy,validate_cohort
            policy = validate_cohort(host.get('budget'),max_generations=batch['max_generations'],topics=batch['topics'])
            install(output/'accounting',policy,require_live=True,required_quotes=REQUIRED_QUOTES)
            from planner_harness.supervisor import ResidentWorker
            host_file = output/'host.json'
            workers = [ResidentWorker(root,output,device,host_file) for device in devices]
            try:
                def execute(topic,arm):
                    slot = 1 if arm == 'none' and len(workers)>1 else 0
                    return workers[slot].execute(topic,arm,timeout=policy['topic']['wall_seconds']+30)
                return advance(root,output,execute)
            finally:
                for worker in workers:worker.close(wait_seconds=1)



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['score','run'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--topic')
    parser.add_argument('--budget-config',type=Path)
    parser.add_argument('--host-config',type=Path)
    parser.add_argument('--legacy-parent',type=int)
    parser.add_argument('--legacy-worker',type=int)
    args = parser.parse_args()
    batch = verify_batch(ROOT, args.output)
    if args.command == 'score':
        from planner_harness.accounting import install,REQUIRED_QUOTES
        if args.budget_config:install(args.output/'accounting',load(args.budget_config),require_live=True,required_quotes=('compute:features','compute:temporal'))
        from planner_harness.supervisor import maybe_supervise_cli
        if maybe_supervise_cli(args.output,[__file__,*sys.argv[1:]]):return
        topic = next(t for t in batch['topics'] if t['id'] == args.topic)
        with RunLock(args.output / 'scoring-owner'):
            score_available(ROOT, args.output, topic)
    else:
        if not args.host_config or bool(args.legacy_parent)!=bool(args.legacy_worker):
            parser.error('Run needs the existing host config and either both legacy PIDs or neither')
        run(ROOT,args.output,load(args.host_config),legacy_parent=args.legacy_parent,legacy_worker=args.legacy_worker)


if __name__ == '__main__':
    from planner_harness.supervisor import cli_entry
    cli_entry(main)
