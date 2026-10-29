"""Start paired Planner generations after the current GPU experiment exits."""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--renderer',choices=['ditto','bernini'],required=True)
    p.add_argument('--wait-pid',type=int,required=True)
    p.add_argument('--after-paused-loop',action='store_true',
                   help='Continue the separately authorized Planner comparison after an explicitly paused Bernini loop.')
    args=p.parse_args()
    run=ROOT/f'out/planner_probe/20261029_{args.renderer}'
    run.mkdir(parents=True,exist_ok=True)
    lock=(run/'launcher.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    lock.write(str(__import__('os').getpid()));lock.flush()
    print(json.dumps({'stage':'waiting_for_current_experiment','pid':args.wait_pid}),flush=True)
    # Wait for process completion without repeatedly querying GPU progress.
    if not args.after_paused_loop:
        subprocess.run(['tail',f'--pid={args.wait_pid}','-f','/dev/null'],check=True)
    if args.after_paused_loop:
        assert args.renderer=='bernini'
        prerequisite=ROOT/'out/loop_probe/20261029_bernini/PAUSED.json'
    else:
        prerequisite=ROOT/('out/prompt_probe/20261029_ditto/generation-complete.json' if args.renderer=='ditto'
                           else 'out/loop_probe/20261029_bernini/generation-complete.json')
    marker=json.loads(prerequisite.read_text())
    if args.after_paused_loop:assert marker['status']=='paused' and marker['do_not_resume_without_user_request']
    elif args.renderer=='ditto':assert marker['status']=='complete' and len(marker['case_ids'])==10
    else:assert marker['new_generations']==16
    print(json.dumps({'stage':'loop_paused_by_user' if args.after_paused_loop else 'prerequisite_generation_complete'}),flush=True)
    idle_start=time.time()
    while time.time()-idle_start<7200:
        manifest=run/'cases.json';spec=json.loads(manifest.read_text(encoding='utf-8'))
        pending=[]
        for case in spec['cases']:
            result=run/case['case_id']/'result.json'
            if not result.exists() or json.loads(result.read_text()).get('status')!='complete':pending.append(case['case_id'])
        if pending:
            gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
            if gpu:
                raise RuntimeError('GPU belongs to another active process; leaving it untouched: '+gpu)
            command=[sys.executable,'-u',str(ROOT/'scripts/deploy'/('run_ditto_prompt_probe.py' if args.renderer=='ditto' else 'run_prompt_probe.py')),
                     '--manifest',str(manifest)]
            if args.renderer=='ditto':command+=['--verified-manifest',str(ROOT/'configs/ditto-models-verified.json')]
            print(json.dumps({'stage':'starting_planner_comparison','cases':pending}),flush=True)
            subprocess.run(command,cwd=ROOT,check=True)
            idle_start=time.time()
            continue
        if len(spec['cases'])==spec['expected_cases']:
            (run/'planner-comparison-complete.json').write_text(json.dumps({'status':'complete',
                  'case_ids':[c['case_id'] for c in spec['cases']],'finished_unix':time.time()}))
            return
        print(json.dumps({'stage':'waiting_for_local_planner','ready':len(spec['cases']),'expected':spec['expected_cases']}),flush=True)
        time.sleep(600)
    raise RuntimeError('Waited two hours for remaining Planner handoffs; inspect local run status')


if __name__=='__main__':main()
