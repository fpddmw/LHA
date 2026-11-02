"""Verbatim original requirements and reproducible evidence/motion configuration."""
import re
import copy
from planner_harness.execution import signature


def judge_view(task):
    """The judge needs verbatim requirements, not request-string offsets.

    Character spans remain in the immutable plan for provenance. Video event
    coordinates use explicit seconds in the model-facing projection.
    """
    result = copy.deepcopy(task)
    result['requirements'] = [{k: row[k] for k in ('id', 'text')} for row in task['requirements']]
    result['events'] = [event_view(event) for event in task['events']]
    return result


def event_view(event):
    return {**{k: v for k, v in event.items() if k not in {'start', 'end'}},
            'start_seconds': event['start'], 'end_seconds': event['end']}


def scope_view(scope):
    result = copy.deepcopy(scope)
    if 'event' in result:
        result['event'] = event_view(result['event'])
    if 'requested_interval' in result:
        result['requested_interval_seconds'] = result.pop('requested_interval')
    for coverage in result.get('coverage', {}).values():
        if 'interval' in coverage:
            coverage['interval_seconds'] = coverage.pop('interval')
    return result


def clauses(request):
    # Stable verbatim spans, not an LLM-expanded list of requirements.
    pieces = re.finditer(r".+?(?:(?<=[。！？!?;；\n])|(?<=\.)(?=\s|$)|$)", request, re.DOTALL)
    rows = []
    for match in pieces:
        raw = match.group().strip()
        if raw:
            start = match.start() + len(match.group()) - len(match.group().lstrip())
            rows.append({"id":"r"+str(len(rows)+1),"text":raw,"start":start,"end":start+len(raw)})
    return rows


def build(request, duration, *, track='long', events=None, motion=None):
    if track not in {'short','long'}:raise ValueError('Task track must be explicit short/long')
    if not isinstance(request,str) or not request.strip():raise ValueError('Original request required')
    # Deterministic, candidate-independent whole-timeline event; subdivided by native source PTS.
    events = events if events is not None else [{'id':'timeline','start':0.0,'end':duration,'reason':'Fixed complete source timeline; no output-dependent selection'}]
    motion = motion if motion is not None else {'required':False,'reason':'Exact source-motion retention has not been declared','regions':[]}
    return {'original_request':request,'track':track,'requirements':clauses(request),
            'events':events,'motion_preservation':motion}


def validate(task, request, duration):
    expected={'original_request','track','requirements','events','motion_preservation'}
    if not isinstance(task,dict) or set(task)!=expected:raise ValueError('Use the v2 original-task specification; expanded interpretation cards are historical')
    if task['original_request']!=request or task['requirements']!=clauses(request):raise ValueError('Requirement spans differ from original request')
    if task['track'] not in {'short','long'}:raise ValueError('Unknown task track')
    events=task['events'];ids=set()
    if not isinstance(events,list):raise ValueError('Events must be a list')
    import math
    for e in events:
        if not isinstance(e,dict) or set(e)!={'id','start','end','reason'} or not isinstance(e['id'],str) or not e['id'].isalnum() or e['id'] in ids:
            raise ValueError('Invalid unique event identity')
        ids.add(e['id'])
        if any(type(e[k]) not in (int,float) or not math.isfinite(e[k]) for k in ('start','end')) or not 0<=e['start']<e['end']<=duration or not isinstance(e['reason'],str) or not e['reason'].strip():raise ValueError('Invalid fixed event interval')
    m=task['motion_preservation']
    if not isinstance(m,dict) or set(m)!={'required','reason','regions'} or type(m['required']) is not bool or not isinstance(m['reason'],str) or not m['reason'].strip() or not isinstance(m['regions'],list):raise ValueError('Invalid declared motion scope')
    for r in m['regions']:
        if not isinstance(r,list) or len(r)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in r) or not 0<=r[0]<r[2]<=1 or not 0<=r[1]<r[3]<=1:raise ValueError('Invalid registered motion region')
    return task
