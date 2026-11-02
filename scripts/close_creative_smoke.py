"""Verify one real smoke trajectory and optionally run its bounded post-task maintenance."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--maintenance-config',type=Path);args=p.parse_args()
    from planner_harness.common import load,save,sha
    from planner_harness.execution import signature
    from planner_harness.delivery import verify_settlement
    from planner_harness.maintenance import enqueue,stage_profile
    output=args.output.resolve();manifest=load(output/'smoke-manifest.json');task=load(output/'task.json')
    if signature({k:v for k,v in manifest.items() if k!='sha256'})!=manifest['sha256']:raise ValueError('Smoke manifest changed')
    run=output/'service/tasks'/manifest['task_id']/'run';state=load(run/'state.json')
    if state['request']['text']!=task['request'] or state['request']['source']['sha256']!=task['source_sha256']:
        raise ValueError('Smoke trajectory belongs to another task')
    settlement=verify_settlement(run)
    identity=enqueue(ROOT,output,run,split=manifest['topics'][0]['split'],topic=manifest['task_id'],method=manifest['arms'][0],batch_sha256=manifest['sha256'],maintenance_profile=stage_profile(ROOT,output,load(args.maintenance_config) if args.maintenance_config else None))
    result={'settlement':settlement,'run':str(run),'state_sha256':sha(run/'state.json'),'maintenance_job':identity,
            'quality_evaluation':'No independent final score requested','active_library_changed':False}
    if identity and manifest['topics'][0]['split']=='train' and manifest['arms'][0]=='full':
        from planner_harness.training_experience import maintain
        result['maintenance']=maintain(ROOT,output,run,identity,load(args.maintenance_config) if args.maintenance_config else None)
        result['maintenance_validated']=result['maintenance']['status'] in {'activated','no_increment'}
        result['training_current']=load(output/'training-experience/current.json')
        result['maintenance_status']='private_training_revision_only'
    else:
        result['maintenance_validated']=False;result['maintenance_status']='read_only_split_or_no_genuine_full_planner_trace'
    if sha(run/'state.json')!=result['state_sha256']:raise ValueError('Maintenance altered the frozen online trajectory')
    save(output/'smoke-closeout.json',result);print(json.dumps(result))
    if manifest['topics'][0]['split']=='train' and manifest['arms'][0]=='full' and not result['maintenance_validated']:raise SystemExit(2)

if __name__=='__main__':main()
