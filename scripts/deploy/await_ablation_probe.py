"""Run audited single-shot ablations only after the existing loop has completed and released its GPU."""
import argparse,fcntl,json,os,subprocess,sys,time
from pathlib import Path
from run_prompt_probe import ROOT,digest,save


def resume_loop_after_priority(args,run,loop):
    """Resume saved requests after a scheduler-owned stop, then queue the remaining ablation cases."""
    schedule=json.loads((run/'priority-schedule.json').read_text(encoding='utf-8'))
    assert not (loop/'PAUSED.json').exists(), 'User paused the loop; leave it paused'
    assert (loop/'STOP').read_text()==schedule['stop_token'], 'Stop ownership changed; do not resume'
    active=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    assert not active,'GPU was taken by another process: '+active
    archive=loop/'lifecycle'/schedule['schedule_id'];archive.mkdir(parents=True,exist_ok=True)
    (loop/'STOP').replace(archive/'scheduler-STOP')
    environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    if args.renderer=='bernini':
        environment['LD_LIBRARY_PATH']='/input0/.lha-runtime/venv/lib/python3.11/site-packages/cusparselt/lib:'+environment.get('LD_LIBRARY_PATH','')
    with (ROOT/schedule['loop_log']).open('ab') as log:
        worker=subprocess.Popen(schedule['loop_argv'],cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=environment)
    # The next launcher waits for this scheduler to exit before acquiring launcher.lock.
    with (run/'session.log').open('ab') as log:
        following=subprocess.Popen([sys.executable,'-u',str(Path(__file__)),
            '--renderer',args.renderer,'--wait-pid',str(worker.pid),'--after-scheduler-pid',str(os.getpid())],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=environment)
    save(run/'priority-resume.json',{'loop_worker_pid':worker.pid,'following_launcher_pid':following.pid,
        'resumed_unix':time.time(),'schedule_id':schedule['schedule_id'],
        'remaining_order':'Resume unfinished loop, then render remaining ablation cases without repeating the first pair.'})
    save(run/'launcher-state.json',{'status':'priority_pair_finished_loop_resumed',
        'loop_worker_pid':worker.pid,'following_launcher_pid':following.pid})


def main():
    p=argparse.ArgumentParser();p.add_argument('--renderer',choices=['bernini','ditto'],required=True)
    p.add_argument('--wait-pid',type=int,required=True)
    p.add_argument('--priority-pair-after-yield',action='store_true')
    p.add_argument('--after-scheduler-pid',type=int);args=p.parse_args()
    if args.after_scheduler_pid:
        subprocess.run(['tail',f'--pid={args.after_scheduler_pid}','-f','/dev/null'],check=True)
    base=ROOT/'out/ablation_probe/20261030_no_knowledge';run=base/('render_'+args.renderer)
    run.mkdir(parents=True,exist_ok=True)
    assert not (run/'STOP').exists() and not (run/'PAUSED.json').exists(), 'Ablation was stopped or paused'
    lock=(run/'launcher.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    lock.seek(0);lock.truncate();lock.write(str(os.getpid()));lock.flush()
    save(run/'launcher-state.json',{'status':'waiting_for_safe_yield' if args.priority_pair_after_yield else 'waiting_for_loop',
         'wait_pid':args.wait_pid,'pid':os.getpid()})
    subprocess.run(['tail',f'--pid={args.wait_pid}','-f','/dev/null'],check=True)
    loop=ROOT/f'out/loop_probe/20261029_{args.renderer}'
    results=[json.loads(p.read_text(encoding='utf-8')) for p in loop.glob('*/result.json')]
    loop_complete=len(results)==16 and all(r['status']=='complete' for r in results)
    if args.priority_pair_after_yield:
        schedule=json.loads((run/'priority-schedule.json').read_text(encoding='utf-8'))
        assert schedule['wait_loop_pid']==args.wait_pid
        assert not (loop/'PAUSED.json').exists() and (loop/'STOP').read_text()==schedule['stop_token']
        assert all(r['status']=='complete' for r in results), 'Loop did not stop cleanly at a completed candidate boundary'
    else:
        marker=json.loads((loop/'generation-complete.json').read_text(encoding='utf-8'))
        assert marker['new_generations']==16 and loop_complete, 'Existing loop has not completed'
    for _ in range(72):
        assert not (run/'STOP').exists() and not (run/'PAUSED.json').exists(), 'Ablation was stopped or paused'
        spec=json.loads((run/'cases.json').read_text(encoding='utf-8'))
        if spec['planning_terminal'] and len(spec['cases'])+len(spec['planning_failures'])==8:break
        save(run/'launcher-state.json',{'status':'waiting_for_local_plans','ready':len(spec['cases']),'pid':os.getpid()})
        time.sleep(600)
    else:raise RuntimeError('Planning did not finish within 12 hours; no renderer started')
    active=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    assert not active,'GPU is used by another process; leave it untouched: '+active
    runner=ROOT/'scripts/deploy'/('run_prompt_probe.py' if args.renderer=='bernini' else 'run_ditto_prompt_probe.py')
    assert digest(runner)==spec['renderer_runner_sha256'], 'Renderer code changed since manifest freeze'
    command_runner=runner
    if spec.get('runtime_loader_adapter'):
        assert args.renderer=='ditto'
        command_runner=ROOT/spec['runtime_loader_adapter']['path']
        assert digest(command_runner)==spec['runtime_loader_adapter']['sha256'], 'Loader adapter changed'
    subprocess.run([sys.executable,'-u',str(ROOT/'scripts/deploy/preflight_ablation_probe.py'),
        '--renderer',args.renderer,'--manifest',str(run/'cases.json')],cwd=ROOT,check=True)
    preflight=json.loads((run/'token-preflight.json').read_text(encoding='utf-8'))
    allowed=[]
    for item in preflight['cases']:
        path=run/item['case_id']/'result.json'
        if path.exists():
            previous=json.loads(path.read_text(encoding='utf-8'))
            if previous['status'] in ['complete','failed']:continue
            raise RuntimeError('Previous generation has an unresolved status; inspect before retrying')
        if args.priority_pair_after_yield and not loop_complete and item['case_id'] not in schedule['priority_case_ids']:
            continue
        if item['passed']:allowed.append(item['case_id'])
        else:
            path.parent.mkdir(exist_ok=True)
            save(path,{'case_id':item['case_id'],'status':'failed','failure_phase':'token_preflight',
                'reason':'Exact prompt exceeds actual renderer limit; no truncation or rewriting applied',**item})
    save(run/'launcher-state.json',{'status':'rendering' if allowed else 'no_eligible_prompts',
         'case_ids':allowed,'pid':os.getpid(),'started_unix':time.time()})
    try:
        if allowed:
            command=[sys.executable,'-u',str(command_runner),'--manifest',str(run/'cases.json'),'--only',*allowed]
            if args.renderer=='ditto':command+=['--verified-manifest',str(ROOT/'configs/ditto-models-verified.json')]
            subprocess.run(command,cwd=ROOT,check=True)
    finally:
        if args.priority_pair_after_yield and not loop_complete:
            save(run/'priority-pair-finished.json',{'finished_unix':time.time(),'case_ids':schedule['priority_case_ids'],
                 'outcomes':{cid:json.loads((run/cid/'result.json').read_text())['status'] if (run/cid/'result.json').exists() else 'not_generated'
                             for cid in schedule['priority_case_ids']}})
            resume_loop_after_priority(args,run,loop)
    if args.priority_pair_after_yield and not loop_complete:return
    outcomes={p.parent.name:json.loads(p.read_text(encoding='utf-8'))['status'] for p in run.glob('*/result.json')}
    assert len(outcomes)+len(spec['planning_failures'])==8 and all(v in ['complete','failed'] for v in outcomes.values())
    save(run/'ablation-generation-complete.json',{'status':'terminal','outcomes':outcomes,
         'planning_failures':spec['planning_failures'],'finished_unix':time.time()})
    save(run/'launcher-state.json',{'status':'finished','pid':os.getpid(),'outcomes':outcomes})


if __name__=='__main__':main()
