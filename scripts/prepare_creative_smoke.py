"""Prepare one source-bound GPU smoke through the existing service; never start execution."""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def prepare(host_path,output,sample_id,prompt_form,device,*,experience='full',seed=42,max_generations=1,wall_seconds=9000):
    from planner_harness.common import load,sha
    from planner_harness.execution import immutable
    from planner_harness.creative import experiment_profile
    from planner_harness import accounting
    from planner_harness.resources import configure
    from planner_harness.video import Video
    output=Path(output).resolve();host=load(host_path)
    rows=load(ROOT/'benchmark_data/benchmark.json')
    row=next(r for r in rows if r['sample_id']==sample_id)
    source=(ROOT/row['source_video']).resolve()
    if sha(source)!=row['source_video_sha256']:raise ValueError('Current source hash differs from benchmark')
    if row['split']=='train' and experience!='full':raise ValueError('Training Planner smoke uses full experience')
    request=row['prompt_short'] if prompt_form=='short' else row.get('prompt_long',row['instruction'])
    if type(device) is not int or device<0:raise ValueError('Select a nonnegative physical GPU index')
    renderer=copy.deepcopy(host['renderer'])
    if renderer.get('backend','bernini')!='bernini':raise ValueError('Use the authorized Bernini host configuration')
    if sha(ROOT/renderer['asset_manifest'])!=renderer['asset_manifest_sha256']:raise ValueError('Asset manifest changed')
    renderer['backend']='bernini'
    renderer['gpu_lock']=str(Path(host.get('lock_directory','/tmp'))/('lha-bernini-device-'+str(device)))
    state={'config':{'max_generations':max_generations}}
    resources=configure(state,{'max_wall_seconds':wall_seconds})
    lane=experience
    limits={**accounting.LIMITS,'amount':None,'wall_seconds':wall_seconds}
    policy=accounting.validate_policy({'version':accounting.VERSION,'mode':'live','cost_control':'count_limits_only',
        'batch':limits,'topic':limits,'max_call_seconds':wall_seconds,'lanes':[lane],'allocations':{lane:limits},
        'online_task_budget':{'version':'online-task-v2','lanes':[lane],'max_generations':max_generations,'wall_seconds':wall_seconds}},require_live=True)
    profile=experiment_profile(ROOT);immutable(output/'profile.json',profile)
    config={'workflow':'creative_loop_v1','planner':{'model':'gpt-6.1-sol','reasoning_effort':'high'},
        'critic':{'model':'gpt-6.1-sol','reasoning_effort':'high'},'enable_final_evaluation':False,
        'limits':{'gpu':1,'llm':1,'cpu':1},'renderer':renderer,'budget':policy,'experiment_profile':str(output/'profile.json')}
    if host.get('models'):config['models']=copy.deepcopy(host['models'])
    info=Video(source,output/'preparation').info
    frames=((info['frames']-1)//4)*4+1
    identity=sample_id+'__'+prompt_form+'__'+experience+'__seed'+str(seed)
    task={'id':identity,'workflow':'creative_loop_v1','source':str(source),'source_sha256':info['sha256'],'request':request,
        'max_generations':max_generations,'completion_mode':'delivery','budget_topic':identity,'budget_lane':lane,
        'execution':{'mode':'live','experience_mode':experience,'task_track':prompt_form,'benchmark_metadata':{'split':row['split'],'sample_id':sample_id,'seed':seed},'resource_policy':resources,
            'experiment_profile':str(output/'profile.json'),'seed_sequence':{'start':seed,'step':1},
            'renderer':{'backend':'bernini','seed':seed,'output':{'frames':frames,'fps':info['fps']},'generation':renderer['generation']}}}
    if row['split']=='train':
        from planner_harness.training_experience import initialize
        revision=initialize(ROOT,output)
        task['execution'].update(experience_snapshot=revision['snapshot'],experience_snapshot_sha256=revision['snapshot_sha256'])
    immutable(output/'service-config.json',config);immutable(output/'task.json',task)
    body={'schema':'lha-single-task-smoke-v1','topics':[{'id':identity,'split':row['split'],'sample_id':sample_id,'prompt_form':prompt_form}],
        'arms':[lane],'task_id':identity,'profile_sha256':profile['sha256'],'validation_only':True}
    from planner_harness.execution import signature
    immutable(output/'smoke-manifest.json',{**body,'sha256':signature(body)})
    return {'status':'prepared_not_executed','task_id':identity,'service':str(output/'service'),'device':device,
        'source_sha256':info['sha256'],'online_profile_sha256':profile['sha256'],'gpu_jobs':0,'provider_calls':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sample-id',required=True);p.add_argument('--prompt-form',choices=['short','long'],default='short');p.add_argument('--device',required=True,type=int)
    p.add_argument('--experience',choices=['full','none'],default='full');p.add_argument('--seed',type=int,default=42)
    p.add_argument('--max-generations',type=int,default=1);p.add_argument('--wall-seconds',type=int,default=9000);args=p.parse_args()
    print(json.dumps(prepare(args.host_config,args.output,args.sample_id,args.prompt_form,args.device,
        experience=args.experience,seed=args.seed,max_generations=args.max_generations,wall_seconds=args.wall_seconds)))

if __name__=='__main__':main()
