"""Default auxiliary metrics; independent raw units, immutable shared candidate caches."""
from pathlib import Path
import math
from . import features, temporal
from .registry import LOW_HIGH_METRICS, LOW_HIGH_RECAST_EXTENT
from planner_harness.common import load,sha
from planner_harness.execution import immutable,signature
from planner_harness.lock import RunLock

CONFIG = {
    'clip_revision':'32bd64288804d66eefd0ccbe215aa642df71cc41',
    'dino_revision':'47b73eefe95e8d44ec3623f8890bd894b6ea2d6c',
    'sample_fps':4.0,'device':'cpu','max_side':512,
}


def automatic(source,candidate,plan,directory,*,accounting_scope=None):
    """Always schedule features and flow. Unavailable jobs have null scores with reasons."""
    from .low_high import check_plan
    check_plan(plan,plan['task']['original_request'],source)
    if any(sha(v['path'])!=v['sha256'] for v in (source,candidate)):
        raise ValueError('Automatic metric video identity changed')
    request=plan['task']['original_request']
    identity={'protocol_id':'lha-automatic-v3','source':source['sha256'],'candidate':candidate['sha256'],
              'request_sha256':signature({'text':request}),
              'motion_scope':plan['task']['motion_preservation'],'config':CONFIG,
              'implementation':{n:sha(Path(__file__).parent/n) for n in ('features.py','temporal.py','media.py','final_suite.py')}}
    directory=Path(directory)/signature(identity)
    with RunLock(directory,timeout=7200):
        immutable(directory/'identity.json',identity)
        if (directory/'result.json').exists():
            result=load(directory/'result.json')
            if load(directory/'binding.json')!={'identity':signature(identity),'result':sha(directory/'result.json')}:
                raise ValueError('Automatic metric cache changed')
            return result
        metrics={};details={}
        jobs=(('features',('clip_f','dino_f')+LOW_HIGH_RECAST_EXTENT,lambda:features.compute(candidate['path'],
                    clip_revision=CONFIG['clip_revision'],dino_revision=CONFIG['dino_revision'],
                    sample_fps=CONFIG['sample_fps'],device=CONFIG['device'],accounting_scope=accounting_scope,
                    source=source['path'],request=request)),
              ('temporal',('flow_warp_l1','motion_diagonals_per_second','low_motion_duration_fraction'),
                  lambda:temporal.compute(candidate['path'],source=source['path'],
                    motion_scope=plan['task']['motion_preservation'],max_side=CONFIG['max_side'],accounting_scope=accounting_scope)))
        from planner_harness.accounting import BudgetConfigurationError, ExternalExecutionUnknown
        from planner_harness.resources import ResourceExhausted
        for kind,names,compute in jobs:
            try:
                raw=compute();details[kind]=raw
                for name in names:
                    value=raw.get(name)
                    if value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
                        raise ValueError('Non-finite automatic metric')
                    metrics[name]={'status':'scored' if value is not None else 'unknown','score':value}
                    if name=='target_text_gain_clip' and raw.get('clip_text_input'):
                        text=raw['clip_text_input']
                        metrics[name]['text_coverage']={k:text[k] for k in (
                            'scope','truncated','original_content_tokens','encoded_content_tokens',
                            'content_token_span','content_token_coverage','encoded_text')}
                        metrics[name]['text_input_record']='details.features.clip_text_input'
                if kind=='temporal':
                    motion=raw['source_motion']
                    metrics['flow_velocity_error']={'status':motion['status'],'score':motion.get('flow_velocity_error'),
                        'reason':motion.get('reason'),'planned_pairs':motion.get('planned_pairs'),'valid_pairs':motion.get('valid_pairs')}
            except (ImportError,OSError,RuntimeError,ValueError,ResourceExhausted,ExternalExecutionUnknown) as exc:
                # Explicitly distinguish unconfigured work from execution failure; no synthetic values.
                status='not_measured' if isinstance(exc,(ImportError,OSError,BudgetConfigurationError)) else 'execution_failed'
                details[kind]={'status':status,'reason':type(exc).__name__}
                for name in names+(('flow_velocity_error',) if kind=='temporal' else ()):
                    metrics[name]={'status':status,'score':None,'reason':type(exc).__name__}
        result={'identity':identity,'metrics':metrics,'details':details,'directory':str(directory)}
        immutable(directory/'result.json',result)
        immutable(directory/'binding.json',{'identity':signature(identity),'result':sha(directory/'result.json')})
        return result


def ratings(result):
    if not result:return {}
    return {**(result.get('report') or {}).get('main_scores',{}),
            **result.get('task_metrics',{}).get('metrics',{}),**result.get('automatic',{}).get('metrics',{})}


def metric_pairs(pairs):
    out={}
    for name,spec in LOW_HIGH_METRICS.items():
        values=[]
        for before,after in pairs:
            a,b=ratings(before).get(name),ratings(after).get(name)
            if a and b and a['status']==b['status']=='scored':values.append(b['score']-a['score'])
        direction=spec.get('direction','higher')
        signed=[-x if direction=='lower' else x for x in values]
        out[name]={'planned':len(pairs),'valid':len(values),'missing':len(pairs)-len(values),
                   'mean_delta':sum(values)/len(values) if values else None,'unit':spec['unit'],
                   'improved':sum(x>0 for x in signed) if direction in {'higher','lower'} else None,
                   'tied':values.count(0),'worsened':sum(x<0 for x in signed) if direction in {'higher','lower'} else None}
    return out


def blind_pairs(root,output,topic,positions,*,judges=None,source_plan=None,pairs=None,media_root=None,write_topic_record=True,retain_unknown=False):
    """Default six reporting contrasts. Provider locks share the absolute-score queue."""
    from experiments.creative_benchmark import PAIRS,shared_source_plan,copy_verified
    from evaluation.creative import JUDGES,make_judge
    from evaluation.pairwise import compare
    from planner_harness.video import Video
    from planner_harness.accounting import topic_scope,attach,bind,ExternalExecutionUnknown
    from planner_harness.resources import ResourceExhausted
    from .low_high import profile
    output=Path(output);source,plan=source_plan or shared_source_plan(root,output,topic)
    results={}
    for name in JUDGES:
        rows={};client=None
        for a,b in (PAIRS if pairs is None else pairs):
            label=a+'__to__'+b
            if a not in positions or b not in positions:
                rows[label]={'status':'missing','reason':'no_delivered_pair','judgments':None};continue
            left,right=positions[a],positions[b]
            identity={'source':source['sha256'],'left':left['sha256'],'right':right['sha256'],
                      'plan':plan['sha256'],'profile':profile()['sha256'],'judge':name,'seed':0}
            directory=output/'blind-judge'/signature(identity)
            with RunLock(output/'judge-providers'/name,timeout=7200),RunLock(directory,timeout=7200):
                immutable(directory/'identity.json',identity)
                if (directory/'sealed.json').exists():
                    record=load(directory/'sealed.json')
                    files={p.relative_to(directory).as_posix():sha(p) for p in sorted(directory.rglob('*'))
                           if p.is_file() and p.name not in {'.run.lock','sealed.json'}}
                    if record['files']!=files:raise ValueError('Blind evaluation cache changed')
                    rows[label]=load(directory/'result.json');continue
                if client is None:client=attach(judges[name] if judges else make_judge(name),topic_scope(output,topic['id']))
                bind(directory,topic_scope(output,topic['id']))
                anonymous=[]
                for video in (left,right):
                    path=Path(media_root or output/'media')/(video['sha256']+'.mp4');copy_verified(video['path'],path,video['sha256'])
                    anonymous.append(Video(path,directory/'info').info)
                try:
                    result=compare(topic['request'],source,*anonymous,directory,plan=plan,seed=0,model=client)
                except (ResourceExhausted,ExternalExecutionUnknown) as exc:
                    if retain_unknown and isinstance(exc,ExternalExecutionUnknown):raise
                    result={'status':'missing','reason':type(exc).__name__,'judgments':None,'judge':name}
                    immutable(directory/'result.json',result)
                files={p.relative_to(directory).as_posix():sha(p) for p in sorted(directory.rglob('*')) if p.is_file() and p.name not in {'.run.lock','sealed.json'}}
                immutable(directory/'sealed.json',{'files':files})
                rows[label]=result
        results[name]=rows
    if write_topic_record:immutable(output/'topics'/topic['id']/'blind.json',results)
    return results


def aggregate(summaries):
    """Default batch views, retaining task length, judge and each planned contrast."""
    from .low_high_summary import summarize,paired
    from .pairwise import summary as blind_summary
    from experiments.creative_benchmark import PAIRS
    rows=[];comparisons={a+'__to__'+b:[] for a,b in PAIRS};blinds={k:[] for k in comparisons}
    for topic in summaries:
        base={'source_id':topic.get('source_id',topic['topic']),'sample_id':topic['topic'],
              'length':topic.get('track','long')}
        for judge,data in topic['judges'].items():
            positions=data['positions']
            for variant,row in positions.items():rows.append({**base,'judge':judge,'variant':variant,'result':row['result']})
            for a,b in PAIRS:
                key=a+'__to__'+b
                comparisons[key].append({**base,'judge':judge,'before':positions[a]['result'],'after':positions[b]['result']})
                blind=topic.get('blind',{}).get(judge,{}).get(key)
                blinds[key].append({**base,'judge':judge,'comparison':key,'result':blind if blind and blind.get('judgments') else None})
    return {'scores':summarize(rows),'paired':{k:paired(v) for k,v in comparisons.items()},
            'blind':{k:blind_summary(v) for k,v in blinds.items()}}
