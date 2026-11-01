"""A delivery proposal, a valid reused/new report, and a real Planner confirmation."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from .common import load, save, sha
from .execution import immutable, signature

PROTOCOL = 'creative-delivery-review-v2'


def invalidate(state, reason, event_id):
    identity = state.get('active_delivery_proposal')
    if identity:
        proposal = state['delivery_reviews'][identity]
        proposal.update(status='superseded', invalidation={'reason':reason,'event_id':event_id})
        state['active_delivery_proposal'] = None


def binding(state, identity):
    return {'protocol':PROTOCOL, 'candidate_id':identity,
            'candidate_sha256':state['videos'][identity]['sha256'],
            'source_sha256':state['videos']['source']['sha256'],
            'request_sha256':signature({'text':state['request']['text']}),
            'critic_profile_sha256':state['config']['execution']['critic']['frozen_profile']['sha256']}


def review_payload(harness, identity, proposal_id):
    state = harness.state
    proposal = state['delivery_reviews'][proposal_id]
    if proposal['binding'] != binding(state, identity):
        raise ValueError('Delivery proposal binding changed')
    allowed = {'path','sha256','fps','frames','duration_seconds','width','height'}
    videos = {i:{k:v for k,v in state['videos'][i].items() if k in allowed} for i in ['source',identity]}
    return {'video_id':identity,'videos':videos,'original':videos['source'],
            'request':state['request']['text'],'compare_to':None,'focus':'','extra_checks':[],
            'critic':copy.deepcopy(state['config']['execution']['critic']),
            'delivery_review':{'protocol':PROTOCOL,'proposal_id':proposal_id,
                               'binding_sha256':signature(proposal['binding'])}}


def propose(harness, args, event_id, *, origin='planner_finish'):
    from .execution import request_job
    state = harness.state; identity = args['video']
    proposal_id = event_id + '-delivery'
    body = {'id':proposal_id,'event_id':event_id,'origin':origin,
            'binding':binding(state,identity),'finish_arguments':copy.deepcopy(args)}
    immutable(harness.output/'delivery-proposals'/proposal_id/'proposal.json',body)
    proposal = state.setdefault('delivery_reviews',{}).setdefault(proposal_id,{**body,'status':'pending','planner_inputs':{}})
    if any(proposal.get(k)!=v for k,v in body.items()):
        raise ValueError('Delivery proposal identity was reused with different inputs')
    state['active_delivery_proposal'] = proposal_id
    rejected = {}
    for job_id in reversed(state.get('evaluations', {})):
        if state['evaluations'][job_id].get('video_id') != identity:
            continue
        try:
            feedback = validated_feedback(harness.output, state, identity, job_id)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            rejected[job_id] = str(exc)
            continue
        proposal.update(review_job=job_id, review_origin='reused', status='ready',
                        response_sha256=sha(harness.output/'jobs'/job_id/'response.json'),
                        feedback_sha256=signature(feedback),collection_event_id=job_id+'-result')
        immutable(harness.output/'delivery-proposals'/proposal_id/'review-binding.json',
                  {k:proposal[k] for k in ('review_job','review_origin','response_sha256','feedback_sha256')})
        return {'status':'review_ready','proposal_id':proposal_id,'delivery_status':'proposed_not_confirmed',
                'message':'The matching valid report is reused. It will be supplied completely in your next model input; decide whether to confirm this candidate or continue work.'}
    prior = [key for key, job in state.get('jobs', {}).items()
             if job['kind'] == 'critique' and job['payload']['video_id'] == identity]
    if prior:
        job_id = prior[-1]
        issue = rejected.get(job_id, 'The original review request has no valid collected report.')
        proposal.update(review_job=job_id, review_origin='existing_request', status='unresolved', review_issue=issue)
        state.setdefault('unresolved_jobs', {})[job_id] = {
            'job_id': job_id, 'failure_kind': 'delivery_review_unusable', 'error': issue,
            'scope': 'Retain the original request and answer. Transport recovery uses that request; an invalid answer is not re-scored.'}
        state['status'] = 'needs_reconciliation'
        return {'status': 'review_unavailable', 'proposal_id': proposal_id, 'job_id': job_id,
                'delivery_status': 'proposed_not_confirmed',
                'message': 'The existing review needs reconciliation. No replacement scoring request was submitted.'}
    result = request_job(harness,'critique',{'video':identity},event_id,
                         internal=True,delivery_proposal=proposal_id)
    proposal.update(review_job=result['job_id'],review_origin='requested')
    return {**result,'proposal_id':proposal_id,'delivery_status':'proposed_not_confirmed',
            'message':'A delivery review is pending because no valid matching report was available. After its report returns, decide whether to confirm this candidate with finish or continue work.'}


def before_finish(harness, args, event_id):
    state = harness.state; identity = args.get('video')
    if state['config'].get('delivery_review_protocol') != PROTOCOL:
        raise ValueError('Creative delivery requires an explicit delivery-review protocol migration')
    if identity in {None,'source'} or state['videos'][identity].get('imported'):
        raise ValueError('Successful delivery requires a generated candidate')
    if not isinstance(args.get('message'),str) or not args['message'].strip():
        raise ValueError('Use the existing message field for a concise delivery explanation')
    active_id = state.get('active_delivery_proposal')
    proposal = state.get('delivery_reviews',{}).get(active_id)
    if proposal and proposal['binding'] != binding(state,identity):
        invalidate(state,'delivery candidate changed',event_id); proposal = None
    if proposal:
        if proposal['status'] in {'ready','confirmed'}:
            proof = confirmation(harness.output,state,proposal,event_id)
            proposal.update(status='confirmed',confirmation=proof)
            immutable(harness.output/'delivery-proposals'/proposal['id']/'confirmation.json',proof)
            return {'status':'confirmed','proof':proof}
        if proposal['status']=='pending':
            return {'status':'pending','job_id':proposal['review_job'],'proposal_id':proposal['id'],
                    'delivery_status':'proposed_not_confirmed'}
        raise ValueError('The delivery review is unresolved; no replacement review was submitted')
    return propose(harness,args,event_id)


def collected(harness, job, response):
    marker = job['payload'].get('delivery_review')
    if not marker:
        return
    state = harness.state; proposal = state['delivery_reviews'][marker['proposal_id']]
    if marker['binding_sha256']!=signature(proposal['binding']) or proposal['binding']!=binding(state,job['payload']['video_id']):
        raise ValueError('Delivery report does not match its proposal')
    proposal.update(status='ready',response_sha256=sha(harness.output/'jobs'/job['id']/'response.json'),
                    feedback_sha256=signature(response['payload']),
                    collection_event_id=job['id']+'-result')
    immutable(harness.output/'delivery-proposals'/proposal['id']/'review-binding.json',
              {k:proposal[k] for k in ('review_job','review_origin','response_sha256','feedback_sha256')})


def context(state):
    identity = state.get('active_delivery_proposal')
    proposal = state.get('delivery_reviews',{}).get(identity)
    if not proposal:
        return {'protocol':PROTOCOL,'status':'no_active_proposal',
                'next_action':'A satisfied finish first proposes a candidate and reuses a matching valid report, or requests one if absent. Only a later Planner finish after the full report in the new proposal context confirms delivery.'}
    result = {'protocol':PROTOCOL,'proposal_id':identity,'binding':copy.deepcopy(proposal['binding']),
              'review_job':proposal['review_job'],'status':proposal['status']}
    if proposal['status'] in {'ready','confirmed'}:
        result['report'] = copy.deepcopy(state['evaluations'][proposal['review_job']]['report'])
        result['review_origin'] = proposal['review_origin']
        result['next_action'] = ('The complete delivery report is supplied here for this proposal. Decide whether to finish with this same candidate and a concise explanation, inspect evidence, change candidate, or generate again. Scores and unknowns impose no acceptance threshold.')
    return result


def record_input(harness, event_id, call_dir):
    state = harness.state; identity = state.get('active_delivery_proposal')
    proposal = state.get('delivery_reviews',{}).get(identity)
    if not proposal or proposal['status'] not in {'ready','confirmed'}:
        return
    saved = load(call_dir/'input.json'); visible = json.loads(saved['user_text'])
    expected = context(state)
    if visible.get('delivery_review') != expected or event_id == proposal['event_id']:
        raise ValueError('A subsequent Planner input must contain the complete bound delivery report')
    receipt = {'input_path':str(call_dir/'input.json'),'input_sha256':sha(call_dir/'input.json'),
               'proposal_id':identity,'feedback_sha256':proposal['feedback_sha256']}
    old = proposal.setdefault('planner_inputs',{}).get(event_id)
    if old is not None and old != receipt:
        raise ValueError('Recorded delivery-report exposure changed')
    proposal['planner_inputs'][event_id] = receipt
    harness.checkpoint()


def validated_feedback(run, state, identity, job_id):
    """Validate the original report under its own legitimate focus/comparison/checks."""
    from critic_harness.one_shot import validate_report, verify_profile
    for i in ['source',identity]:
        if sha(state['videos'][i]['path']) != state['videos'][i]['sha256']:
            raise ValueError('Delivery media changed')
    job = state['jobs'][job_id]
    if job['kind']!='critique' or job['payload']['video_id']!=identity or job['payload']['request']!=state['request']['text']:
        raise ValueError('Cached review belongs to a different candidate or request')
    folder = run/'jobs'/job['id']
    if load(folder/'request.json') != job or signature({k:v for k,v in job.items() if k!='sha256'}) != job['sha256']:
        raise ValueError('Delivery review signed request changed')
    response = load(folder/'response.json')
    if response['status']!='complete' or response['request_sha256']!=job['sha256'] or response.get('mode')!=job['mode']:
        raise ValueError('Delivery review has no complete matching response')
    if load(folder/'collected.json')!=response:
        raise ValueError('Delivery report was not collected unchanged')
    feedback = response['payload']; packet = load(feedback['request_path']); visible = json.loads(packet['user_text'])
    frozen = state['config']['execution']['critic']['frozen_profile']
    verify_profile(frozen)
    if job['payload']['critic']['frozen_profile']!=frozen or feedback.get('usage')!='online_feedback' or feedback.get('profile_sha256')!=frozen['sha256'] or feedback.get('protocol')!=frozen['protocol_id'] or feedback.get('video_id')!=identity:
        raise ValueError('Cached review protocol/model differs from this task')
    if packet['profile_sha256']!=frozen['sha256'] or packet['system_prompt']!=frozen['rubric']:
        raise ValueError('Delivery review rubric changed')
    if visible['original_request']!=state['request']['text'] or visible['candidate_id']!=identity or not {'source',identity}<=set(visible['videos']) or set(visible['videos'])!=set(job['payload']['videos']):
        raise ValueError('Delivery review task/evidence identity changed')
    if visible['focus']!=job['payload'].get('focus','') or visible['compare_to']!=job['payload'].get('compare_to') or [c['text'] for c in visible['extra_checks']]!=job['payload'].get('extra_checks',[]):
        raise ValueError('Cached review focus/comparison/checks differ from its signed request')
    for i,v in visible['videos'].items():
        if v['sha256']!=job['payload']['videos'][i]['sha256'] or v['sha256']!=state['videos'][i]['sha256']:
            raise ValueError('Delivery review media binding changed')
    for frame in packet['images']:
        if sha(frame['path'])!=frame['sha256']:
            raise ValueError('Delivery evidence changed')
    call = folder/'one-shot-critic/call'
    sent = load(call/'input.json')
    if sent['model']!=frozen['model'] or sent['reasoning_effort']!=frozen['reasoning_effort'] or sent['system_prompt']!=packet['system_prompt'] or sent['user_text']!=packet['user_text']:
        raise ValueError('Original Critic call identity/input does not match the frozen report')
    if sent['images']!=[{'path':e['path'],'sha256':e['sha256']} for e in packet['images']]:
        raise ValueError('Original Critic call evidence differs from its packet')
    raw = (call/'response.txt').read_text().strip()
    if raw.startswith('```json\n') and raw.endswith('```'):raw=raw[8:-3].strip()
    if json.loads(raw)!=feedback['report']:
        raise ValueError('Cached report differs from the original Critic answer')
    validate_report(feedback['report'],packet)
    if state['evaluations'][job['id']]['report']!=feedback['report']:
        raise ValueError('Planner delivery report differs from the returned report')
    return feedback


def checked_feedback(run, state, proposal):
    identity = proposal['binding']['candidate_id']
    if proposal['binding']!=binding(state,identity):
        raise ValueError('Delivery candidate/request/profile binding changed')
    body = {k:proposal[k] for k in ('id','event_id','origin','binding','finish_arguments')}
    if load(run/'delivery-proposals'/proposal['id']/'proposal.json')!=body:
        raise ValueError('Original delivery proposal changed')
    job = state['jobs'][proposal['review_job']]
    if proposal['review_origin']=='requested' and job['payload'].get('delivery_review')!={
        'protocol':PROTOCOL,'proposal_id':proposal['id'],'binding_sha256':signature(proposal['binding'])}:
        raise ValueError('Requested review does not belong to this proposal')
    feedback = validated_feedback(run,state,identity,job['id'])
    if sha(run/'jobs'/job['id']/'response.json')!=proposal['response_sha256'] or signature(feedback)!=proposal['feedback_sha256']:
        raise ValueError('Bound delivery report changed')
    if load(run/'delivery-proposals'/proposal['id']/'review-binding.json')!={k:proposal[k] for k in ('review_job','review_origin','response_sha256','feedback_sha256')}:
        raise ValueError('Delivery report reuse/request binding changed')
    return feedback


def confirmation(run, state, proposal, event_id):
    run = Path(run)
    feedback = checked_feedback(run,state,proposal)
    exposure = proposal.get('planner_inputs',{}).get(event_id)
    if not exposure or event_id==proposal['event_id']:
        raise ValueError('Delivery needs a new Planner response after its complete report for this proposal')
    path = run/'calls'/event_id/'input.json'
    if sha(path)!=exposure['input_sha256'] or exposure['feedback_sha256']!=proposal['feedback_sha256']:
        raise ValueError('Delivery confirmation model input changed')
    saved = load(path); visible = json.loads(saved['user_text']); delivered = visible.get('delivery_review',{})
    if delivered.get('proposal_id')!=proposal['id'] or delivered.get('binding')!=proposal['binding'] or delivered.get('report')!=feedback['report'] or delivered.get('status')!='ready':
        raise ValueError('Confirmation input did not contain the complete pending delivery report')
    call = path.parent; response = call/'response.txt'
    transport = call/'transport'
    if (transport/'response.txt').read_text()!=response.read_text() or load(transport/'returned.json')['sha256']!=sha(response):
        raise ValueError('Delivery confirmation is not the returned Planner response')
    sent = load(transport/'input.json')
    if sent['user_text']!=saved['user_text'] or sent['system_prompt']!=saved['system_prompt']:
        raise ValueError('Saved Planner input differs from the actual transport input')
    if sent['model']!=state['config']['model'] or sent['reasoning_effort']!=state['config']['reasoning_effort']:
        raise ValueError('Delivery confirmation used a different Planner identity')
    decision = json.loads(response.read_text()); args = decision.get('arguments',{})
    if decision.get('action')!='finish' or args.get('video')!=proposal['binding']['candidate_id'] or args.get('stop_reason','satisfied')!='satisfied' or not isinstance(args.get('message'),str) or not args['message'].strip():
        raise ValueError('Post-report Planner response did not confirm this delivery')
    return {'protocol':PROTOCOL,'proposal_id':proposal['id'],'proposal_event_id':proposal['event_id'],
            'review_job':proposal['review_job'],'review_response_sha256':proposal['response_sha256'],
            'review_origin':proposal['review_origin'],
            'feedback_sha256':proposal['feedback_sha256'],'planner_event_id':event_id,
            'planner_input_sha256':sha(path),'planner_response_sha256':sha(response),
            'candidate_sha256':proposal['binding']['candidate_sha256'],'message':args['message']}


def verify(run, state):
    run = Path(run)
    if state['config'].get('delivery_review_protocol')!=PROTOCOL:
        raise ValueError('Old creative completion needs an explicit delivery-review migration')
    proof = state.get('final',{}).get('delivery_review')
    if not proof:
        raise ValueError('Delivery lacks proposal/review/Planner-confirmation evidence')
    proposal = state.get('delivery_reviews',{}).get(proof.get('proposal_id'))
    if not proposal or proposal['status']!='confirmed' or state.get('active_delivery_proposal')!=proposal['id']:
        raise ValueError('Delivery proposal is stale or unconfirmed')
    expected = confirmation(run,state,proposal,proof['planner_event_id'])
    if proof!=expected or proposal.get('confirmation')!=expected or load(run/'delivery-proposals'/proposal['id']/'confirmation.json')!=expected:
        raise ValueError('Delivery confirmation relationship changed')
    events = {e['event_id']:e for e in state['events']}
    event = events.get(proof['planner_event_id'],{})
    if event.get('status')!='ok' or event.get('request')!=json.loads((run/'calls'/proof['planner_event_id']/'response.txt').read_text()):
        raise ValueError('Delivery confirmation is not an accepted subsequent Planner event')
    order = [e['event_id'] for e in state['events']]
    if proposal['collection_event_id'] not in order or order.index(proposal['collection_event_id'])>=order.index(proof['planner_event_id']):
        raise ValueError('Delivery report was not returned before confirmation')
    if state['final']['video']!=proposal['binding']['candidate_id'] or state['final']['message']!=proof['message']:
        raise ValueError('Final delivery differs from the confirmed Planner decision')
    return proof
