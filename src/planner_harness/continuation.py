"""Factual spent resources and non-semantic continuation questions; operator policy stays private."""
from __future__ import annotations

import copy
import math

from .common import load, sha
from .execution import immutable, signature

VERSION = 'creative-continuation-v1'
QUESTIONS = [
    'Which retained candidate currently seems most suitable for delivery, and what unresolved issue makes you choose to continue?',
    'What will this attempt change or establish, and why use this input video? State plainly if it is resampling rather than a new realization.',
    'Why is the expected benefit worth another generation instead of entering delivery confirmation now?',
]
PRESSURE = {
    'exploration':'This task operates under a limited budget. Use the available resources deliberately while developing and evaluating your proposal.',
    'continuation':'Before spending resources on another generation, answer the continuation questions using the actual candidates, previous prompts and observed results.',
    'deliberate':'Further generation warrants a deliberate choice. Explain why another attempt is preferable to reviewing and delivering a retained candidate, and what this attempt is intended to change or establish.',
}


def configure(state, supplied=None):
    policy = {'version':VERSION,'free_successes':2,'deliberate_after_successes':6,'hard_generation_limit':None}
    supplied = copy.deepcopy(supplied or {})
    if set(supplied)-set(policy):
        raise ValueError('Unknown operator continuation policy setting')
    policy.update(supplied)
    if policy['version']!=VERSION or policy['free_successes']!=2:
        raise ValueError('Use the approved continuation policy version and exploration setting')
    if type(policy['deliberate_after_successes']) is not int or policy['deliberate_after_successes']<policy['free_successes']:
        raise ValueError('Invalid internal continuation wording transition')
    old_limit = state['config'].get('max_generations')
    explicit = policy['hard_generation_limit']
    if explicit is not None and (type(explicit) is not int or explicit<0):
        raise ValueError('Optional actual generation limit must be a nonnegative integer')
    if old_limit is not None:
        if explicit is not None and explicit!=old_limit:
            raise ValueError('Conflicting operator generation limits')
        policy['hard_generation_limit'] = old_limit
    state['config']['continuation_policy'] = policy
    # This legacy branch must never stop the whole creative task after a refused render.
    state['config']['max_generations'] = None
    return policy


def usage(state):
    generated = {v.get('job_id'):v for k,v in state['videos'].items() if k!='source' and not v.get('imported')}
    requests = {k:j for k,j in state.get('jobs',{}).items() if j['kind']=='generate'}
    outcomes = state.get('render_outcomes',{})
    failures = [k for k,v in outcomes.items() if k in requests and v['status']=='failed' and not v.get('uncertain')]
    uncertain = {k for k,v in state.get('unresolved_jobs',{}).items() if k in requests}
    uncertain.update(k for k,v in outcomes.items() if k in requests and v.get('uncertain'))
    times = []
    for video in generated.values():
        value = video.get('execution',{}).get('generation_seconds')
        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0:
            times.append(value)
    for key in failures:
        value = outcomes[key].get('generation_seconds')
        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0:
            times.append(value)
    return {'generated_candidates':len(generated),'submitted_render_requests':len(requests),
            'failed_render_attempts':len(failures),'uncertain_render_attempts':len(uncertain),
            'pending_or_uncollected_render_requests':max(0,len(requests)-len(generated)-len(failures)-len(uncertain)),
            'known_rendering_elapsed_seconds':sum(times),'render_cost_records_missing':len(generated)+len(failures)+len(uncertain)-len(times),
            'elapsed_time_scope':'Known rendering wall time from receipts; failed/uncertain costs may be unknown. This is not exact GPU compute time or monetary cost.'}


def phase(state):
    policy = state['config']['continuation_policy']; n = usage(state)['generated_candidates']
    return 'exploration' if n<policy['free_successes'] else 'continuation' if n<policy['deliberate_after_successes'] else 'deliberate'


def view(state):
    policy = state['config']['continuation_policy']; facts = usage(state)
    required = facts['generated_candidates']>=policy['free_successes']
    cap = policy['hard_generation_limit']
    return {'spent_resources':facts,'budget_awareness':PRESSURE[phase(state)],
            'justification_required':required,'continuation_questions':copy.deepcopy(QUESTIONS) if required else [],
            'generation_available':not state.get('unresolved_jobs') and (cap is None or facts['submitted_render_requests']<cap)}


def record_input(harness, event_id, call_dir):
    saved = load(call_dir/'input.json')
    import json
    actual = json.loads(saved['user_text']).get('continuation')
    if actual!=view(harness.state):
        raise ValueError('Saved continuation prompt differs from the current receipt-based projection')
    record = {'event_id':event_id,'model_input_sha256':sha(call_dir/'input.json'),
              'policy':copy.deepcopy(harness.state['config']['continuation_policy']),
              'stage':phase(harness.state),'trigger_state':usage(harness.state),'visible':actual}
    immutable(call_dir/'continuation-policy.json',record)


def authorize(state, args, event_id):
    existing = state.get('generation_decisions',{}).get(event_id+'-generate')
    if existing:
        if existing['arguments']!=args:
            raise ValueError('Recovered generation explanation or arguments changed')
        return None
    visible = view(state)
    if not visible['generation_available']:
        return {'status':'generation_unavailable','message':'Additional generation is unavailable under the current resource policy. Observation, reading, review and delivery confirmation remain available.',
                'continuation':visible}
    explanation = args.get('justification')
    if explanation is not None and not isinstance(explanation,str):
        raise ValueError('justification must be free text')
    if visible['justification_required'] and (explanation is None or not explanation.strip()):
        return {'status':'justification_required','message':'Answer the continuation questions in the justification field together with the actual prompt and input video. No render was submitted.',
                'continuation':visible}
    return None


def record_dispatch(harness, job, args, event_id):
    state = harness.state; key = job['id']
    record = {'event_id':event_id,'job_id':key,'request_sha256':job['sha256'],
              'arguments':copy.deepcopy(args),'justification':args.get('justification'),
              'policy_version':VERSION,'stage':phase(state),'visible':view(state),
              'input_id':job['payload']['input_id'],'input_sha256':job['payload']['input']['sha256'],
              'prompt':job['payload']['prompt'],'prompt_sha256':signature({'text':job['payload']['prompt']}),
              'model_input_path':str(harness.output/'calls'/event_id/'input.json')}
    prior = state.setdefault('generation_decisions',{}).get(key)
    if prior:
        if prior['arguments']!=args or prior['request_sha256']!=job['sha256']:
            raise ValueError('Recovered generation decision changed')
        return
    # Capture the pre-dispatch view: adding the signed job has not yet spent its slot here.
    immutable(harness.output/'jobs'/key/'continuation.json',record)
    state['generation_decisions'][key] = record


def record_outcome(state, job, response):
    if job['kind']!='generate':
        return
    execution = response.get('payload',{}).get('execution',{})
    state.setdefault('render_outcomes',{})[job['id']] = {
        'status':response['status'],'uncertain':bool(response.get('outcome_unknown')),
        'generation_seconds':execution.get('generation_seconds'),'request_sha256':job['sha256']}


def index(run, state):
    """Passive operator navigation, never a model-side usefulness grade."""
    run = str(run)
    return {'policy_version':VERSION,'scope':'Raw continuation explanations and actual outcomes; no usefulness grading or causal attribution.',
            'spent_resources':usage(state),'generations':[{
                **copy.deepcopy(record),'request_path':run+'/jobs/'+key+'/request.json',
                'response_path':run+'/jobs/'+key+'/response.json',
                'outcome':copy.deepcopy(state.get('render_outcomes',{}).get(key)),
                'candidate_ids':[i for i,v in state['videos'].items() if v.get('job_id')==key]}
                for key,record in state.get('generation_decisions',{}).items()]}
