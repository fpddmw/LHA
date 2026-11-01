"""Prepare/apply an explicitly authorized local protocol transition; never execute models or renders."""
from __future__ import annotations

import copy
from pathlib import Path
import shutil

from .common import load, save, sha, stamp
from .execution import immutable, signature
from .lock import RunLock
from .delivery_review import PROTOCOL
from .continuation import VERSION

TOUCHED = {'state.json','system-prompt.txt','final.json','report.html','report.md',
           'continuation-index.json','experience-usage.json'}
INSTRUCTIONS = ('Complete the video task using the limited budget deliberately. Answer the continuation questions '
                'in generate justification when requested. A satisfied finish proposes delivery; a valid matching '
                'report is reused, or requested if absent. The full report is supplied for that proposal in a '
                'subsequent input; confirm the same candidate with finish or continue work. Independent final '
                'judgments are not Planner feedback.')


def prepare_batch(root, batch_file, previous_profile_file, output):
    """Versioned profile/diff package from saved snapshots; no live inspection or changes."""
    root, output = Path(root).resolve(), Path(output).resolve()
    batch, previous = load(batch_file), load(previous_profile_file)
    if signature({k:v for k,v in batch.items() if k!='sha256'})!=batch['sha256'] or signature({k:v for k,v in previous.items() if k!='sha256'})!=previous['sha256'] or batch['profile_sha256']!=previous['sha256']:
        raise ValueError('Baseline batch/profile snapshot identities differ')
    from .creative import experiment_profile
    target=experiment_profile(root)
    if any(previous[k]!=target[k] for k in ('critic','planner','independent_judges')):
        raise ValueError('Preparation must preserve role settings and the frozen rubric')
    scope_differences={}
    for mode, old_scope in previous['knowledge_scopes'].items():
        new_scope=target['knowledge_scopes'][mode]
        if any(new_scope.get(k)!=v for k,v in old_scope.items()):
            raise ValueError('A baseline knowledge item is missing or changed; retain the frozen content')
        extra={k:v for k,v in new_scope.items() if k not in old_scope}
        if extra:scope_differences[mode]=extra
    if previous['files']['src/evaluation/creative.py']!=target['files']['src/evaluation/creative.py']:
        raise ValueError('Independent judging adapter changed; cached-score compatibility needs separate review')
    output.mkdir(parents=True,exist_ok=True)
    for source,name in [(batch_file,'baseline-batch.json'),(previous_profile_file,'baseline-profile.json')]:
        destination=output/name
        if destination.exists() and sha(destination)!=sha(source):raise ValueError('Existing baseline snapshot differs')
        if not destination.exists():shutil.copyfile(source,destination)
    immutable(output/'target-profile.json',target)
    changed={p:{'previous':previous['files'].get(p),'target':target['files'].get(p)}
             for p in sorted(set(previous['files'])|set(target['files'])) if previous['files'].get(p)!=target['files'].get(p)}
    body={'schema':'creative-batch-transition-preparation-v1',
          'status':'prepared_requires_environment_reconciliation' if scope_differences else 'prepared_not_applied_live_pause',
          'baseline_batch_sha256':batch['sha256'],'previous_profile_sha256':previous['sha256'],
          'target_profile_sha256':target['sha256'],'target_profile_path':str(output/'target-profile.json'),
          'runtime_policy':target['runtime_policy'],'changed_files':changed,
          'local_preview_only':bool(scope_differences),'scope_presence_differences':scope_differences,
          'scope_note':'Every baseline item retains its exact hash. Additional locally available files are not authorized as an expanded live scope; freeze the target again in the original physical layout after resume authorization.' if scope_differences else 'Exact scope identities retained.',
          'independent_judge_cache':'Exact request/source/candidate/Critic-protocol/model/adapter identities remain compatible; do not rescore unchanged media.',
          'direct':'Unchanged; retain its exact completed receipt and media.',
          'run_migration':'prepare_creative_protocol.py --run <settled-original-run> --profile <distinct-target-profile> --reason <authorization> --output <plan>',
          'readiness':'Per-run migration is offline-tested. Actual host/process/receipt status is intentionally unknown until a separate resume authorization.',
          'required_before_apply':['Confirm explicit authorization to inspect/deploy/migrate the paused live experiment.',
             'Verify actual external calls are settled; preserve original frozen checkout/profile and per-run prefix snapshots.',
             'Create explicit versioned batch/service bindings to the new shared profile; never overwrite the baseline profile or old service configuration.',
             'Apply per-run transitions under existing ownership locks; retain old finals/archives and confirm through a real post-proposal Planner input.',
             'Retain all five scoring positions and use the existing cache; version a superseded completed topic archive before changing its selection.'],
          'executes_external_calls':False,'modifies_live_state':False,'resumes_heartbeat':False}
    result={**body,'sha256':signature(body)}
    immutable(output/'preparation.json',result)
    return result


def plan(run, root, reason, *, profile=None):
    run, root = Path(run).resolve(), Path(root).resolve()
    if not reason.strip():
        raise ValueError('Record why this protocol transition is authorized')
    state = load(run/'state.json')
    if state['config'].get('workflow')!='creative_loop_v1':
        raise ValueError('Only creative Loops use this migration; Direct remains unchanged')
    from .creative import experiment_profile, verify_experiment
    target = verify_experiment(profile,root) if profile else experiment_profile(root)
    previous_path = state['config']['execution'].get('experiment_profile')
    previous = load(previous_path) if previous_path else None
    if previous and previous['sha256']!=signature({k:v for k,v in previous.items() if k!='sha256'}):
        raise ValueError('Previous frozen profile signature changed')
    if previous_path and profile is None:
        raise ValueError('A shared experiment migration needs a distinct newly frozen profile path')
    if previous_path and Path(profile).resolve()==Path(previous_path).resolve():
        raise ValueError('Preserve the previous frozen profile; do not replace it in place')
    if previous and any(previous[k]!=target[k] for k in ('critic','planner','independent_judges','knowledge_scopes')):
        raise ValueError('Protocol migration must preserve role identities, rubric and knowledge content')
    blocked = []
    if state.get('pending_event'):
        blocked.append('Settle the existing Planner call and retain its exact input/response before changing instructions.')
    if state.get('unresolved_jobs'):
        blocked.append('Reconcile existing uncertain tool outcomes without replacement dispatch.')
    pending = state.get('pending_tool')
    if pending:
        response = run/'jobs'/pending/'response.json'
        if not response.exists() or load(response).get('status') not in {'complete','failed'}:
            blocked.append('Allow the active tool call to settle and retain its final receipt.')
    prefix = {p.relative_to(run).as_posix():sha(p) for p in sorted(run.rglob('*'))
              if p.is_file() and 'protocol-migrations' not in p.relative_to(run).parts and p.name!='.run.lock'
              and not p.name.endswith(('.tmp','.part','.partial'))}
    body = {'schema':'creative-protocol-transition-v1','reason':reason,
            'target_delivery_protocol':PROTOCOL,'target_continuation_policy':VERSION,
            'previous_state_sha256':sha(run/'state.json'),
            'previous_profile_sha256':previous['sha256'] if previous else None,
            'previous_profile_path':previous_path,'target_profile_sha256':target['sha256'],
            'target_profile_path':str(Path(profile).resolve()) if profile else None,
            'previous_system_prompt_sha256':sha(run/'system-prompt.txt'),
            'knowledge_snapshot_sha256':sha(run/'knowledge-snapshot.json'),
            'candidate_prefix':{i:{k:v.get(k) for k in ('sha256','job_id','parent','prompt')} for i,v in state['videos'].items()},
            'previous_status':state['status'],'previous_final':copy.deepcopy(state.get('final')),
            'pending_tool':pending,'prefix_files':prefix,'blocked_requirements':blocked,
            'executes_external_calls':False,'restores_dispatch_or_polling':False}
    return {**body,'sha256':signature(body)}


def apply(run, root, proposal, authorization):
    """Apply only after separate operator authorization and a settled run boundary."""
    if not isinstance(authorization,str) or not authorization.strip():
        raise ValueError('Explicit migration authorization is required')
    run, root = Path(run).resolve(), Path(root).resolve()
    with RunLock(run):
        current = plan(run,root,proposal['reason'],profile=proposal['target_profile_path'])
        if current!=proposal or current['blocked_requirements']:
            raise ValueError('Migration prefix changed or an external call remains unresolved')
        state = load(run/'state.json'); pending = state.get('pending_tool')
        from contextlib import nullcontext
        with RunLock(run/'jobs'/pending/'worker') if pending else nullcontext():
            directory = run/'protocol-migrations'/proposal['sha256']
            before = directory/'before';before.mkdir(parents=True,exist_ok=True)
            for name in TOUCHED:
                path = run/name
                if path.exists():
                    shutil.copyfile(path,before/name)
            if proposal['previous_profile_path']:
                shutil.copyfile(proposal['previous_profile_path'],before/'experiment-profile.json')
            from .creative import experiment_profile, system_prompt
            immutable(directory/'target-profile.json',experiment_profile(root))
            from .runner import PlannerHarness
            from .creative_knowledge import CreativeKnowledge
            harness = PlannerHarness(run,None,root=root)
            harness.state=state;harness.knowledge=CreativeKnowledge(root,run/'knowledge-snapshot.json')
            previous_final = state.pop('final',None)
            if previous_final is not None:
                state.setdefault('interruption_history',[]).append({'origin':'authorized_protocol_transition','final':previous_final,
                    'original_state_sha256':proposal['previous_state_sha256'],'snapshot':str(before/'state.json')})
                (run/'final.json').unlink(missing_ok=True)
            state['config']['delivery_review_protocol']=PROTOCOL
            from .continuation import configure, record_outcome
            configure(state)
            for job_id,job in state['jobs'].items():
                path=run/'jobs'/job_id/'response.json'
                if job['kind']=='generate' and path.exists():
                    record_outcome(state,job,load(path))
            state['active_delivery_proposal']=None
            state['config']['run_instructions']=INSTRUCTIONS
            if proposal['target_profile_path']:
                state['config']['execution']['experiment_profile']=proposal['target_profile_path']
            new_system = system_prompt(harness)
            (run/'system-prompt.txt').write_text(new_system,encoding='utf-8')
            state['system_prompt_sha256']=sha(run/'system-prompt.txt')
            state['runtime_sources']={p.name:sha(p) for p in (root/'src/planner_harness').iterdir() if p.suffix in {'.py','.md'}}
            state['status']='waiting_tool' if pending else 'running'
            if previous_final and previous_final.get('stop_reason')=='satisfied' and previous_final.get('video') not in {None,'source'}:
                from .delivery_review import propose
                propose(harness,{'video':previous_final['video'],'message':previous_final.get('message',''),
                                 'stop_reason':'satisfied'},'migration-'+proposal['sha256'][:16],origin='authorized_legacy_completion')
            event_id='protocol-migration-'+proposal['sha256'][:16]
            receipt={'at':stamp(),'authorization':authorization,'plan':proposal,
                     'before_snapshot':str(before),'new_system_prompt_sha256':state['system_prompt_sha256'],
                     'scope':'Protocol/instruction transition only; previous candidate/call/job/knowledge bytes retained. No external call or dispatch resume.'}
            state.setdefault('protocol_migrations',[]).append(receipt)
            event={'event_id':event_id,'at':receipt['at'],'status':'ok','request':{'action':'operator_protocol_transition'},'result':receipt}
            state['events'].append(event);save(run/'events'/(event_id+'.json'),event)
            harness.checkpoint()
            for relative,digest in proposal['prefix_files'].items():
                if relative in TOUCHED:
                    snapshot=before/relative
                    if not snapshot.exists() or sha(snapshot)!=digest:
                        raise ValueError('Original mutable record was not retained')
                elif sha(run/relative)!=digest:
                    raise ValueError('A retained immutable prefix artifact changed')
            if sha(run/'knowledge-snapshot.json')!=proposal['knowledge_snapshot_sha256']:
                raise ValueError('Knowledge snapshot changed during migration')
            immutable(directory/'receipt.json',receipt)
            return receipt
