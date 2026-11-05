"""Training Planner contributions: ordered private activation or explicit shared-library candidate maintenance."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import time
from functools import lru_cache
from .common import load,save,sha,stamp,page
from .execution import immutable,signature
from .lock import RunLock

VERSION="lha-post-task-maintenance-v1"
SKILLS=("lha-experience-analysis","lha-experience-use-review","lha-experience-curation")
DEFAULTS={"enabled":False,"wall_seconds":None,"model_calls":32,"tokens":2000000,"attempts":2,
          "automatic_phase":"after_batch_settlement","publish":False}
PROMPT="""You are reviewing this task after its online outcome has settled. Contribute useful
conditional judgments for the next Planner using analysis, use-review or curation
Skills as needed. Read actual requests, inputs, prompts and results. Distinguish
original online exposure from the full library available only in this maintenance
session. Challenge your own choices, reviews and old guidance where the case warrants
it. State the practical preference, its explanation and the conditions that change it.

Write in the style of the current library. Read the relevant maintenance Skill,
the authoring standard, and a nearby entry before drafting. The writing references
point to representative entries in this private snapshot. Learn their decisiveness
and explanatory detail, not their particular scene or a fixed section template.
Lead with what the next Planner should do. Explain the visual construction or
renderer behavior that makes the advice useful, give a concrete way to apply it,
and keep exact cases and evidence status in a compact footer. Use an exception to
change the decision, not to retreat into generic cautions. Comments can be short;
a new account should be readable and useful without the maintainer's conversation.

You may create a new experience, recommend, clarify, comment or propose an exact
revision. These become linked, searchable contributions in an authorized private
library. Existing entries, summaries, manuals and Skills remain unchanged. Library
curation is a separately authorized operation. Use a linked correction when existing
guidance is wrong; do not soften a useful conclusion merely because it is new.
No increment is a valid conclusion. Do not render, run a new judge, publish shared
knowledge or change the online result. Record useful findings, not private reasoning.

Return one JSON action with arguments:
skill {id}; browse {id}; search {query};
read {source:run|knowledge|reference,id,start_line?,start_char?,max_chars?};
view_image {ids}; observe {video_id,start?,end?,count?,crop?}; note {text};
contribute {text,changes?}.

A change uses op=create with id,title,text,summary,questions?,renderers?,
layer?,tracks?,families?,stages?;
or op=comment|clarify|recommend|propose_revision with id (existing experience or
contribution),text,summary?,title?,questions?,renderers?,layer?,tracks?,families?,stages?.
For new accounts choose layer=principle|renderer|condition, tracks=[short,long] as
applicable, families as task-family labels, and stages from design|inspect|revise|deliver.
Linked comments inherit placement unless explicitly qualified. Renderer accounts
name their renderer. These fields organize discovery; the account itself is prose.
A proposed revision describes
the exact improvement; it does not replace the target. Manuals/Skills cannot be
mutation targets. Put suggestions about those in the contribution's prose for a
separate development review. Runtime adds source cases, target versions and inspected
frame identities. Only saved source/candidate videos are observable; reading a source case also makes
its bound videos available under case-prefixed IDs. New observations
are post-task evidence, not frames the original Planner necessarily saw. Empty changes
retains a prose-only report. The frozen task and experiment profile determine admission
and exposure; do not infer them from the Skill text.
"""


def configuration(value=None):
    cfg={**DEFAULTS,**(value or {})}
    if set(cfg)!=set(DEFAULTS) or type(cfg['enabled']) is not bool or cfg['publish'] is not False or cfg['automatic_phase'] not in {'after_batch_settlement','after_each_training_task'}:
        raise ValueError('Maintenance is a separate post-batch candidate workflow')
    if cfg['wall_seconds'] is not None and (type(cfg['wall_seconds']) is not int or cfg['wall_seconds'] < 1):
        raise ValueError('Optional maintenance time must be positive or null')
    for name in ('model_calls','tokens','attempts'):
        if type(cfg[name]) is not int or cfg[name]<1:raise ValueError('Finite maintenance allowances required')
    return cfg


REFERENCES=('docs/experience-authoring-standard.md','docs/experience-usage-interface.md','docs/online-event-observation.md')


def writing_references(knowledge):
    """Resolve examples from the bound private library, never today's mutable files."""
    preferred = (('principle', 'EX-P-every-plane', 'A decisive construction judgment developed through a contrast.'),
                 ('renderer', 'EX-B-emission-binding', 'A renderer-specific recommendation with an exact spatial relation.'),
                 ('condition', 'EX-C-long', 'A task-conditioned method connected to observed outcomes.'))
    entries = knowledge.curated_catalog['entries']
    result = []
    for layer, identity, purpose in preferred:
        row = next((r for r in entries if r['id'] == identity), None)
        row = row or next((r for r in entries if r.get('layer') == layer), None)
        if row:
            result.append({**{key:row[key] for key in ('id','title','sha256','version')},
                           'purpose':purpose, 'read':{'source':'knowledge','id':row['id']}})
    return result


@lru_cache(maxsize=16)
def _materials(root,batch):
    root=Path(root)
    code_root=Path(__file__).resolve().parents[2]
    def item(name):
        path=root/name
        return {'path':name,'text':path.read_text(),'sha256':sha(path)} if path.is_file() else None
    return {'instructions':PROMPT,'skills':{name:item('.agents/skills/'+name+'/SKILL.md') for name in SKILLS},
        'references':{name:item(name) for name in REFERENCES},
        'implementation':{name:sha(code_root/name) for name in ('src/planner_harness/maintenance.py','src/planner_harness/training_experience.py','src/planner_harness/experience_contributions.py')}}


def stage_profile(root,batch,config=None):
    materials=copy.deepcopy(_materials(str(Path(root).resolve()),str(Path(batch).resolve())))
    cfg=configuration({**(config or {}),'enabled':True,'automatic_phase':'after_each_training_task'})
    body={**materials,'configuration':cfg}
    from .upgrade import retain
    return retain(Path(batch)/'maintenance/profile.json', {**body,'sha256':signature(body)})


def eligible(run,split, *, deferred=False):
    run=Path(run)
    if (split != 'train' and not (deferred and split == 'test')) or not (run/'state.json').is_file():return False
    state=load(run/'state.json')
    if state.get('config',{}).get('workflow') not in {'creative_loop_v1','single_planner_trace'} or not state.get('final'):return False
    if state.get('status') in {'running','waiting_tool','needs_reconciliation','interrupted'}:return False
    # A real returned Planner request/answer, not invented Direct self-reflection.
    for path in [*(run/'calls').glob('*/input.json'),*(run/'call').glob('input.json')]:
        returned=path.parent/('returned.json' if path.parent.name=='call' else 'transport/returned.json')
        answer=path.parent/'response.txt'
        if answer.is_file() and returned.is_file() and load(returned).get('sha256')==sha(answer):return True
    return False


def provenance(root,run,split, *, deferred=False):
    """Verify actual benchmark membership, rather than trusting a split argument."""
    state=load(Path(run)/'state.json')
    metadata=state['config']['execution'].get('benchmark_metadata',{})
    sample=metadata.get('sample_id')
    rows=load(Path(root)/'benchmark_data/benchmark.json')
    row=next((r for r in rows if r['sample_id']==sample),None)
    deferred = deferred and state['config']['execution'].get('experience_condition') == 'pre-experience'
    if (split != 'train' and not (deferred and split == 'test')) or metadata.get('split')!=split or row is None or row['split']!=split:
        raise ValueError('New library candidates require an attested training task; test/validation are excluded')
    source=state.get('videos',{}).get('source',state.get('source',{}))
    from .benchmark_source import verify_normalized_source
    normalized = verify_normalized_source(root, state, row, source)
    if normalized is None and source.get('sha256')!=row['source_video_sha256']:
        raise ValueError('Maintenance source is not the attested benchmark source')
    prompts=[row.get('prompt_short'),row.get('prompt_long'),row.get('instruction')]
    if state['request']['text'] not in prompts:raise ValueError('Maintenance request differs from the attested task')
    body={'split':split,'sample_id':sample,'source_group':row.get('source_group',sample),
          'source_sha256':row['source_video_sha256'],'request_sha256':signature({'text':state['request']['text']}),
          'benchmark_row_sha256':signature(row),'run_state_sha256':sha(Path(run)/'state.json')}
    if normalized is not None:
        body['normalized_source'] = normalized
    from .training_experience import family
    body.update(family(state))
    return {**body,'sha256':signature(body)}


def enqueue(root, batch_output, run, *, split, topic, method, batch_sha256, maintenance_profile=None, maintenance_snapshot=None):
    """Idempotent after fixed settlement; no model, dataset write or activation."""
    run,batch_output=Path(run).resolve(),Path(batch_output).resolve()
    pre_experience = method == 'pre-experience'
    if not eligible(run, split, deferred=pre_experience):return None
    batch_path=batch_output/'batch.json'
    if batch_path.exists() and load(batch_path).get('training_maintenance') is False:
        return None
    state=load(run/'state.json')
    from .training_experience import initialize, bound_snapshot, family, verify_pre_experience
    if pre_experience:
        verify_pre_experience(run, maintenance_snapshot)
    identity=signature({'run':str(run),'batch_sha256':batch_sha256})
    directory=batch_output/'maintenance/jobs'/identity
    if (directory/'job.json').exists():
        existing=load(directory/'job.json')
        from .upgrade import record
        record(directory, 'settled_state_metadata', existing['run_state_sha256'], sha(run/'state.json'))
        if existing['knowledge_snapshot_sha256']!=sha(run/'knowledge-snapshot.json'):
            raise ValueError('Original maintenance knowledge is missing or corrupt')
        bound_snapshot(root,existing.get('maintenance_snapshot'),output=batch_output,**family(state))
        if maintenance_snapshot and maintenance_snapshot.get('owner') != existing['maintenance_snapshot']['owner']:
            raise ValueError('Existing maintenance job belongs to another library')
        return identity
    # Online none is an exposure policy. Maintenance always has a full seed.
    if maintenance_snapshot is None:
        maintenance_snapshot=initialize(root,batch_output,**family(state))
    bound_snapshot(root,maintenance_snapshot,output=batch_output,**family(state))
    profile=maintenance_profile or stage_profile(root,batch_output)
    if any(v is None for v in [*profile['skills'].values(),*profile['references'].values()]):raise ValueError('Maintenance reading material is missing')
    body={'version':VERSION,'implementation_sha256':sha(__file__),'run':str(run),'run_state_sha256':sha(run/'state.json'),
          'knowledge_snapshot_sha256':sha(run/'knowledge-snapshot.json'),'batch_sha256':batch_sha256,
          'provenance':provenance(root,run,split,deferred=pre_experience),'split':split,'topic':topic,'method':method,'settlement':copy.deepcopy(state['final']),
          'experience_mode':state['config']['execution'].get('experience_mode'),
          'events':[e['event_id'] for e in state.get('events',[])],
          'entry_versions':{r['id']:{k:r.get(k) for k in ('version','sha256')} for r in load(run/'knowledge-snapshot.json').get('curated_catalog',{}).get('entries',[])},
          'maintenance_snapshot':copy.deepcopy(maintenance_snapshot),'instructions':profile['instructions'],'maintenance_identity':profile['sha256'],
          'maintenance_configuration':profile['configuration'],'references':profile['references'],'skills':profile['skills']}
    identity=signature({k:body[k] for k in ('run','batch_sha256')})
    directory=batch_output/'maintenance/jobs'/identity
    immutable(directory/'job.json',{**body,'id':identity})
    if not (directory/'status.json').exists():save(directory/'status.json',{'status':'queued','attempts':0})
    return identity


def seal_batch(output,batch,positions):
    """Default maintenance admission requires every online position settled."""
    output=Path(output)
    expected={(t['id'],m) for t in batch['topics'] for m in t.get('methods',batch['arms'])}
    actual={(r['topic'],r['method']) for r in positions}
    if expected!=actual or any(r['status']=='execution_unknown' for r in positions):
        raise ValueError('Default maintenance waits for complete online batch settlement')
    immutable(output/'maintenance/batch-settled.json',{'batch_sha256':batch['sha256'],
        'positions':[{'topic':r['topic'],'method':r['method'],'sha256':signature(r)} for r in positions]})


def saved_videos(state):
    """Only files identified by the settled task, never model-supplied paths."""
    videos = copy.deepcopy(state.get('videos', {}))
    if 'source' not in videos and isinstance(state.get('source'), dict):
        videos['source'] = state['source']
    return {identity: {k: row[k] for k in ('path', 'sha256', 'duration_seconds') if k in row}
            for identity, row in videos.items() if row.get('path') and row.get('sha256')}


def observe_saved(videos, folder, args, identity):
    from .video import Video
    if set(args) - {'video_id', 'start', 'end', 'count', 'crop'}:
        raise ValueError('Use a saved video ID and bounded observation arguments')
    row = videos[args['video_id']]
    if sha(row['path']) != row['sha256']:
        raise ValueError('Saved video changed since task settlement')
    count = args.get('count', 6)
    if type(count) is not int or not 1 <= count <= 8:
        raise ValueError('Inspect 1 to 8 sampled frames per maintenance observation')
    result = Video(row['path'], folder).observe(identity, args.get('start', 0), args.get('end'), count, args.get('crop'))
    if sha(row['path']) != row['sha256']:
        raise ValueError('Saved video changed during observation')
    result.update(video_id=args['video_id'], video_sha256=row['sha256'], evidence_phase='post_task')
    immutable(Path(folder)/'observations'/identity/'record.json', result)
    return result


def case_videos(knowledge, case_id):
    """Open only videos bound by an already-readable, immutable case record."""
    row = knowledge.items[case_id]
    if row.get('kind') != 'experience_case':
        return {}
    document = knowledge.document(row)
    text = document['text']
    body = json.loads(text.split('\n\n', 1)[1])
    return {case_id+':'+identity: value for identity, value in saved_videos(body).items()}


def model_view(payload):
    """Project repeated transport metadata out of maintenance inputs only."""
    from .context import observation_view
    result = copy.deepcopy(payload)
    result['run_sources'] = {k: {'characters': v['characters']} for k, v in payload.get('run_sources', {}).items()}
    images, seen = {}, set()
    for identity, row in payload.get('image_catalog', {}).items():
        key = (row.get('sha256'), row.get('video_id'), row.get('timestamp_seconds'))
        if key in seen and identity not in payload.get('attached_images', []):
            continue
        seen.add(key)
        images[identity] = {k: row[k] for k in ('video_id', 'timestamp_seconds', 'observation_id') if k in row}
    result['image_catalog'] = images
    result['image_catalog_scope'] = 'Each saved image is listed once; original call/image IDs remain readable.'
    result['observations'] = observation_view(result.get('observations', []))
    current = result.get('current_result')
    for row in result.get('retained_reading', []):
        if row.get('result') == current:
            row['result'] = {'text_location': 'current_result'}
    if isinstance(current, dict) and 'skill' in current and current.get('text') == result.get('loaded_skills', {}).get(current['skill']):
        current.pop('text', None)
        current['text_location'] = 'loaded_skills.' + current['skill']
    return result


def _execute(root,folder,job,cfg,model):
    from .creative_knowledge import CreativeKnowledge
    from .model_call import call_text
    from .json_output import decode_object
    from . import accounting
    run=Path(job['run'])
    from .upgrade import record, retain
    record(folder, 'state_metadata', job['run_state_sha256'], sha(run/'state.json'))
    if sha(run/'knowledge-snapshot.json')!=job['knowledge_snapshot_sha256']:
        raise ValueError('Original maintenance knowledge is missing or corrupt')
    retain(Path(folder)/'task-state.json', load(run/'state.json'))
    library=job.get('maintenance_snapshot')
    from .training_experience import bound_snapshot, family, verify_pre_experience
    if job['method'] == 'pre-experience':
        verify_pre_experience(run, library)
    knowledge=bound_snapshot(root,library,**family(load(run/'state.json')))
    files={'state':Path(folder)/'task-state.json','knowledge-snapshot':run/'knowledge-snapshot.json'}
    for identity,path in job.get('additional_sources',{}).items():files[identity]=Path(path)
    for path in sorted([*(run/'calls').glob('*/*'),*(run/'call').glob('*')]):
        if path.name in {'input.json','response.txt','experience-exposure.json','continuation-policy.json'}:
            files[path.relative_to(run).as_posix()]=path
    image_catalog={}
    for call in [*(run/'calls').glob('*/input.json'),*(run/'call').glob('input.json')]:
        saved=load(call)
        for number,row in enumerate(saved.get('images',[])):
            if isinstance(row,str):continue
            if row.get('path') and row.get('sha256'):
                identity=call.relative_to(run).as_posix()+':image-'+str(number+1)
                image_catalog[identity]={k:row[k] for k in ('path','sha256','video_id','timestamp_seconds','observation_id') if k in row}
    video_catalog = saved_videos(load(run/'state.json'))
    observations = []
    image_focus=[]
    source_index={identity:{'sha256':sha(path),'characters':path.stat().st_size} for identity,path in files.items()}
    policy={'version':accounting.VERSION,'mode':'live' if getattr(model,'requires_live_budget',False) else 'offline',
            'cost_control':'count_limits_only','max_call_seconds':cfg['wall_seconds'],
            'batch':{**accounting.LIMITS,'model_calls':cfg['model_calls'],'tokens':cfg['tokens'],'wall_seconds':cfg['wall_seconds']},
            'topic':{**accounting.LIMITS,'model_calls':cfg['model_calls'],'tokens':cfg['tokens'],'wall_seconds':cfg['wall_seconds']},
            'lanes':['independent'],'allocations':{'independent':{**accounting.LIMITS,'model_calls':cfg['model_calls'],'tokens':cfg['tokens'],'wall_seconds':cfg['wall_seconds']}}}
    budget=accounting.install(folder/'accounting',policy,require_live=bool(getattr(model,'requires_live_budget',False)))
    model=accounting.attach(model,accounting.scope(budget,job['id']))
    deadline=None if cfg['wall_seconds'] is None else time.time()+cfg['wall_seconds']
    result={'job':{k:job[k] for k in ('id','topic','method','split','settlement','experience_mode','entry_versions')},
            'skills':[{"id":name,"description":job['skills'][name]['text'].split('description:',1)[1].split('---',1)[0].strip()} for name in SKILLS],
            'run_sources':source_index,'maintenance_references':{k:{'sha256':v['sha256'],'scope':'Post-task writing/usage guidance, not original online exposure'} for k,v in job.get('references',{}).items()},'image_catalog':image_catalog,'video_catalog':video_catalog,'knowledge_entrances':knowledge.overview(), 'library_scope':'Post-task private library; online exposure remains the run knowledge-snapshot', 'maintenance_snapshot':library}
    result['writing_references'] = writing_references(knowledge)
    loaded_skills={};reading_cache=[];notes=''
    task_identity=copy.deepcopy(result['job'])
    for number in range(cfg['model_calls']):
        if deadline is not None and time.time()>=deadline:raise TimeoutError('Maintenance time allowance exhausted')
        for identity in image_focus:
            if sha(image_catalog[identity]['path'])!=image_catalog[identity]['sha256']:raise ValueError('Original Planner image changed')
        raw=call_text(folder/'calls'/f'{number+1:04d}',model,job.get('instructions',PROMPT),json.dumps(model_view(result),ensure_ascii=False,separators=(',',':')),[image_catalog[i]['path'] for i in image_focus],attempts=1)
        action=decode_object(raw, allow_prose=True);kind=action.get('action');args=action.get('arguments',{})
        try:
            if kind=='skill':
                loaded_skills[args['id']]=job['skills'][args['id']]['text']
                result={'skill':args['id'],'text':loaded_skills[args['id']]}
            elif kind=='browse':result=knowledge.browse(args.get('id','map'))
            elif kind=='search':
                result=knowledge.search(args['query'])
                for match in result['matches']:
                    match['open']={'action':'read','arguments':{'source':'knowledge','id':match['id']}}
            elif kind=='read' and args.get('source')=='knowledge':
                result=knowledge.read(args['id'],args.get('start_line',1),start_char=args.get('start_char',0),max_chars=min(8000,args.get('max_chars',6000)))
                if result.get('kind') == 'experience_case':
                    opened = case_videos(knowledge, result['id'])
                    video_catalog.update(opened)
                    result['saved_videos'] = opened
            elif kind=='read' and args.get('source')=='reference':
                reference=job['references'][args['id']]
                result={'id':args['id'],'sha256':reference['sha256'],'scope':'Explicit frozen post-task reference; it was not supplied in the original online task',
                    **page(reference['text'],args.get('start_line',1),max_chars=min(8000,args.get('max_chars',6000)),start_char=args.get('start_char',0),split_long_lines=True)}
            elif kind=='read' and args.get('source')=='run':
                path=files[args['id']]
                if sha(path)!=source_index[args['id']]['sha256']:raise ValueError('Original run source changed')
                result=page(path.read_text(),args.get('start_line',1),max_chars=min(8000,args.get('max_chars',6000)),start_char=args.get('start_char',0),split_long_lines=True)
            elif kind=='observe':
                observed = observe_saved(video_catalog, folder, args, 'maintenance-'+str(number+1))
                observations.append(observed)
                image_focus = []
                for index, frame in enumerate(observed['frames']):
                    identity = observed['observation_id']+':'+str(index)
                    image_catalog[identity] = {**frame, 'video_id': observed['video_id'],
                                               'observation_id': observed['observation_id'], 'scope':'post_task_observation'}
                    image_focus.append(identity)
                result = observed
            elif kind=='view_image':
                identities=args['ids']
                if not isinstance(identities,list) or not 1<=len(identities)<=8 or any(i not in image_catalog for i in identities):raise ValueError('Choose 1 to 8 original Planner image IDs')
                image_focus=list(dict.fromkeys(identities))
                result={'attached_images':[{'id':i,**image_catalog[i]} for i in image_focus],
                        'scope':'Image identities distinguish original Planner exposure from new post-task observation. Saved reviews remain attributed.'}
            elif kind=='note':
                notes=args['text']
                if not isinstance(notes,str) or len(notes)>12000:raise ValueError('Keep a concise maintenance working note')
                result={'saved':True}
            elif kind=='contribute':
                text=args['text']
                if not isinstance(text,str) or not text.strip():raise ValueError('Use concise professional prose or state no increment')
                changes=args.get('changes',[])
                if not isinstance(changes,list):raise ValueError('changes must be a list')
                if changes:
                    from .experience_contributions import append
                    append(knowledge.snapshot, changes, job['provenance'])
                contribution={'maintenance_identity' :signature({'instructions':job.get('instructions',PROMPT),'skills':{k:v['sha256'] for k,v in job['skills'].items()},'references':{k:v['sha256'] for k,v in job['references'].items()},'configuration':cfg,'implementation':job.get('implementation_sha256')}),'changes':copy.deepcopy(changes),'contribution_call':{'path':str(folder/'calls'/f'{number+1:04d}'),'input_sha256':sha(folder/'calls'/f'{number+1:04d}'/'input.json'),'response_sha256':sha(folder/'calls'/f'{number+1:04d}'/'response.txt'),'returned_sha256':sha(folder/'calls'/f'{number+1:04d}'/'returned.json')},'version':VERSION,'provenance':job['provenance'],'job_path':job.get('original_job_path'), 'job_sha256':job.get('original_job_sha256'),'job_id':job['id'],'text':text,'run':job['run'],
                    'run_state_sha256':job['run_state_sha256'],'knowledge_snapshot_sha256':job['knowledge_snapshot_sha256'],
                    'entry_versions':job['entry_versions'],'event_refs':job['events'],
                    'visibility':job['experience_mode'],'source_index':source_index,'model_call':number+1,
                    'activation':'append_only_private_contribution_when_authorized', 'observations':copy.deepcopy(observations)}
                immutable(folder/'contribution.json',contribution)
                (folder/'contribution.md').write_text(text+'\n')
                return contribution
            else:raise ValueError('Choose an available maintenance action')
        except (ValueError,KeyError,TypeError) as exc:result={'error':str(exc),'scope':'No render, score or publication was submitted'}
        if kind in {'read','search','browse'}:
            reading_cache[:] = [row for row in reading_cache if row['action'] != action]
            reading_cache.append({'action':action,'result':copy.deepcopy(result)})
            while reading_cache and len(json.dumps(reading_cache,ensure_ascii=False))>24000:reading_cache.pop(0)
        result={'current_result':result,'task':task_identity,'original_request':load(run/'state.json')['request']['text'],
                'knowledge_mode':job['experience_mode'],'loaded_skills':loaded_skills,'retained_reading':reading_cache,
                'writing_references':writing_references(knowledge),
                'notes':notes,'available_skills':list(SKILLS),'run_sources':source_index,'maintenance_references':{k:v['sha256'] for k,v in job.get('references',{}).items()},'image_catalog':image_catalog,'video_catalog':video_catalog,'observations':observations,'attached_images':image_focus,
                'archive_scope':'Older exact pages remain available through read; only the bounded cache is omitted.'}
    raise RuntimeError('Maintenance call allowance exhausted')


def drain(root,output,config=None,*,model_factory=None):
    cfg=configuration(config);output=Path(output)
    if not cfg['enabled']:return {'status':'disabled','online_results_changed':False}
    if not (output/'maintenance/batch-settled.json').exists():raise ValueError('Online batch has not fully settled')
    if model_factory is None:
        from vlm.openrouter import OpenRouterVisionModel
        model_factory=lambda:OpenRouterVisionModel(role='post_task_planner')
    results=[]
    with RunLock(output/'maintenance/owner'):
        for path in sorted((output/'maintenance/jobs').glob('*/job.json')):
            folder=path.parent;job=load(path);job['original_job_path']=str(path);job['original_job_sha256']=sha(path);state=load(folder/'status.json')
            if job['batch_sha256']!=load(output/'maintenance/batch-settled.json')['batch_sha256']:raise ValueError('Maintenance batch identity changed')
            if state['status']=='complete' or state['attempts']>=cfg['attempts']:continue
            # Unknown external work blocks a blind retry of this maintenance job only.
            if state['status']=='execution_unknown':continue
            state.update(status='running',attempts=state['attempts']+1);save(folder/'status.json',state)
            try:
                _execute(root,folder/('attempt-'+str(state['attempts'])),job,cfg,model_factory())
                state['status']='complete'
            except Exception as exc:
                state.update(status='execution_unknown' if getattr(exc,'outcome_unknown',False) else 'failed',error_type=type(exc).__name__)
            save(folder/'status.json',state);results.append({'job_id':job['id'],**state})
        bundle=merge_candidates(output)
        # Curation is explicitly invoked; draining contributions does not start another model.
    return {'status':'settled','jobs':results,'candidate_bundle':str(bundle),'online_results_changed':False}


def merge_candidates(output):
    """One cross-task candidate input; no active-library writes or new evaluation."""
    output=Path(output);rows=[]
    for path in sorted((output/'maintenance/jobs').glob('*/*/contribution.json')):
        value = load(path)
        deferred = output / 'training-experience/deferred' / (path.parent.parent.name + '.json')
        if deferred.exists() and value.get('provenance', {}).get('split') == 'test':
            receipt = load(deferred)
            if receipt.get('contribution') == {'path': str(path.resolve()), 'sha256': sha(path)}:
                continue
        rows.append({'path':str(path),'sha256':sha(path),**value})
    for row in rows:
        if row.get('provenance',{}).get('split')!='train':raise ValueError('Test or unattested contribution cannot enter a formal candidate revision')
    body={'version':VERSION,'contributions':rows,'activation':'candidate_only_requires_user_review',
          'scope':'Cross-task source bundle for the delegated curation pass; shared explanations and conflicting conditions remain attributed.'}
    identity=signature(body);directory=output/'maintenance/candidates'/identity
    immutable(directory/'bundle.json',body)
    (directory/'README.md').write_text('# Candidate contributions for one reviewed library revision\n\n'+'\n\n'.join('## '+r['job_id']+'\n\n'+r['text'] for r in rows))
    return directory/'bundle.json'


def curate_candidate_revision(root,output,bundle,cfg,model_factory):
    """A separate post-batch curation pass produces proposed text, never applies it."""
    bundle=Path(bundle)
    target=bundle.parent/'revision'
    if (target/'status.json').exists():return
    jobs=[job for p in (Path(output)/'maintenance/jobs').glob('*/job.json')
          if (job := load(p)).get('split') == 'train']
    if not jobs:return
    source=next((j for j in jobs if j['experience_mode']=='full'),jobs[0])
    job=copy.deepcopy(source)
    job['id']='batch-curation-'+bundle.parent.name
    job['topic']='Cross-task curation: consolidate useful judgments, reconcile conditions and propose exact next-version entry/summary/navigation/manual text. Avoid one new entry per task; state no change when warranted. No publication.'
    job['additional_sources']={'candidate-bundle':str(bundle),'candidate-reading-page':str(bundle.parent/'README.md')}
    for i,row in enumerate(load(bundle)['contributions']):job['additional_sources']['contribution-'+str(i+1)]=row['path']
    try:
        contribution=_execute(root,target,job,cfg,model_factory())
        (bundle.parent/'candidate-revision.md').write_text(contribution['text']+'\n')
        save(target/'status.json',{'status':'complete','active_library_changed':False})
    except Exception as exc:
        save(target/'status.json',{'status':'execution_unknown' if getattr(exc,'outcome_unknown',False) else 'failed','error_type':type(exc).__name__,'active_library_changed':False})


def enqueue_planner_once(root,output,topic,settlement,batch):
    """Adapt genuine one-call work; no loop events or retrospective self-report."""
    if topic.get('split')!='train':return None
    run=Path(output)/'methods'/topic['id']/'planner-once/planner'
    if not (run/'call/returned.json').exists() or not (run/'call/response.txt').exists():return None
    state={'config':{'workflow':'single_planner_trace','execution':{'experience_mode':'none','benchmark_metadata':{'split':topic['split'],'sample_id':topic['sample_id']}}},
           'source':{'sha256':topic['source_sha256']},'request':{'text':topic['request']},'status':'settled','final':settlement,
           'events':[{'event_id':'planning','source_call':str(run/'call'),'scope':'The actual single planning call; no loop trajectory is implied'}],
           'trace_adaptation':{'plan':str(run/'plan.json'),'input':str(run/'call/input.json'),
                'response':str(run/'call/response.txt'),'response_sha256':sha(run/'call/response.txt')}}
    immutable(run/'state.json',state)
    return enqueue(root,output,run,split='train',topic=topic['id'],method='planner-once',batch_sha256=batch['sha256'])


def validate_candidate_publication(root,bundle):
    """Publication prerequisite: reject test-derived or unbound new contributions."""
    bundle=Path(bundle);body=load(bundle)
    if bundle.parent.name!=signature(body):raise ValueError('Candidate bundle identity changed')
    for row in body['contributions']:
        if sha(row['path'])!=row['sha256']:raise ValueError('Contribution changed')
        contribution=load(row['path']);job_path=Path(contribution['job_path'])
        if sha(job_path)!=contribution['job_sha256']:raise ValueError('Contribution job binding changed')
        job=load(job_path)
        if contribution['provenance']!=job['provenance'] or provenance(root,job['run'],job['split'])!=job['provenance']:
            raise ValueError('Candidate has no verified training provenance')
    return {'status':'eligible_for_user_review','contributions':len(body['contributions']),'published':False}
