"""Frozen online review with bounded, question-led continuous-event evidence."""
from __future__ import annotations

import copy
from functools import lru_cache
import json
import re
from pathlib import Path

from planner_harness.common import load, save, sha
from planner_harness.execution import signature, immutable
from planner_harness.video import Video

from .qualitative import PROTOCOL



def frozen_profile(model=None,reasoning_effort='__configured_default__'):
    from .qualitative import profile
    return profile(model,reasoning_effort)


def verify_profile(profile):
    if profile.get('sha256')!=signature({k:v for k,v in profile.items() if k!='sha256'}):
        raise ValueError('Frozen review profile hash mismatch')
    if profile.get('protocol_id')!=PROTOCOL or not isinstance(profile.get('rubric'),str):
        raise ValueError('Unexpected online review protocol')


def prepare_request(request,candidate_id,videos,directory,profile,*,compare_to=None,focus='',extra_checks=None,events=None,track='long'):
    from .qualitative import observe,packet
    verify_profile(profile)
    ids=list(dict.fromkeys(['source',videos[candidate_id].get('parent','source'),candidate_id]+([compare_to] if compare_to else [])))
    payload={'request':request,'video_id':candidate_id,'input_id':videos[candidate_id].get('parent','source'),
        'actual_prompt':videos[candidate_id].get('prompt',''),'submitted_prompt':videos[candidate_id].get('prompt',''),
        'videos':{i:videos[i] for i in ids},'compare_to':compare_to,'focus':focus,'extra_checks':extra_checks or [],'events':events or [],'track':track}
    state={'videos':payload['videos'],'observations':[]}
    observe(state,directory,{'video':ids,'count':6},'overview')
    result=packet(payload,state,profile);immutable(Path(directory)/'request.json',result)
    return result,[r['path'] for r in result['images']]




def validate_focus(focus,checks):
    if not isinstance(focus,str) or not isinstance(checks,list) or any(not isinstance(v,str) for v in checks):
        raise ValueError('Review focus and questions must be text')


def validate_report(report, packet):
    """Compatibility dispatcher for historical callers; online reports stay qualitative."""
    if json.loads(packet["user_text"]).get("protocol_id") == PROTOCOL:
        from .qualitative import validate
        return validate(report, packet)
    from evaluation.validation import validate_report as validate_final
    return validate_final(report, packet)


def __getattr__(name):
    if name == "DIMENSIONS":
        from evaluation.validation import DIMENSIONS
        return DIMENSIONS
    raise AttributeError(name)



def online_projection(report, packet=None):
    """Withhold explicit action instructions from online prose; preserve raw assessment.

    This narrow syntactic filter is telemetry/feedback policy, never score validity.
    Ambiguous semantics remain a documented limitation of descriptive prompting.
    """
    report = copy.deepcopy(report)
    if 'main_scores' not in report:return report
    pattern = (r"\b(recommend(?:ed|ation|ations)?|next (?:step|attempt|generation)|"
                 r"(?:you|we|the planner)\s+should\s+(?:use|generate|edit|render|select|try)|"
                 r"(?:rewrite|revise|change) the prompt|(?:choose|select|deliver) (?:v\d+|candidate)|"
                 r"(?:restart|regenerate|stop generating|continue editing)|"
                 r"(?:use|take|keep|retain)\s+(?:v\d+|source|the source|this candidate|the candidate)\s+(?:as|for)|"
                 r"(?:further|another|new)\s+(?:render|generation|pass)\b.{0,100}\b(?:would|could|will|can)|"
                 r"(?:edit|generate|render)\s+(?:again|from)|"
                 r"(?:deliver|select|choose)\s+(?:this|that|it)|"
                 r"(?:rewrite|revise|modify|strengthen|shorten)\s+(?:the|your)\s+prompt|"
                 r"using\s+v\d+\s+as\s+(?:the\s+)?base\s+would|"
                 r"rendering\s+(?:once\s+more|again)\s+from)\b")
    def safe(text):
        return "Explicit action guidance withheld by online feedback policy." if re.search(pattern, text, re.I) else text
    for row in list(report["main_scores"].values()) + report["comparisons"] + report["extra_checks"]:
        row["reason"] = safe(row["reason"])
        if "limitations" in row:
            row["limitations"] = [safe(v) for v in row["limitations"]]
    report["unassessed"] = [safe(v) for v in report["unassessed"]]
    def project_diagnostics(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key == "reason" and isinstance(item,str):value[key] = safe(item)
                else:project_diagnostics(item)
        elif isinstance(value,list):
            for item in value:project_diagnostics(item)
    project_diagnostics(report.get("task_diagnostics",{}))
    if packet is not None:
        questions={c['id']:c['text'] for c in json.loads(packet['user_text'])['extra_checks']}
        for row in report['extra_checks']:row['question']=questions[row['id']]
    return report


def projection_fields(original, projected, path=""):
    if isinstance(original, dict):
        return [p for k in original.keys() | projected.keys() for p in ([path+"/"+k] if k not in original or k not in projected else projection_fields(original[k], projected[k], path+"/"+k))]
    if isinstance(original, list):
        return [p for i, value in enumerate(original) for p in projection_fields(value, projected[i], path + "/" + str(i))]
    return [path] if original != projected else []


def run_review(payload,directory,model=None):
    from .qualitative import run
    return run(payload,directory,model)
