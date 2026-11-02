"""Original-task evaluation contract and independent, segmented final evidence."""
from __future__ import annotations

import bisect
import hashlib
import json
import math
from pathlib import Path

from .validation import validate_report
from planner_harness.common import load, sha
from planner_harness.execution import immutable, signature
from planner_harness.video import Video
from planner_harness.report_call import call_report, verify_answer, verify_inputs, ReportUnavailable, FINAL_POLICY

PROTOCOL = "lha-low-high-final-v3"
PLAN_PROTOCOL = "lha-low-high-task-plan-v3"
POLICY = {"overview_frames_per_six_seconds": 20, "overview_minimum": 20,
          "event_selection": "fixed full source timeline unless an operator freezes explicit intervals", "event_frames": "all native consecutive frames",
          "event_source_segment_stride": 28, "decoder": "native-pts-v1",
          "time_mapping": "identity seconds; unequal durations retained as missing coverage",
          "online_feedback": False, "single_score": "integer 0..4; missing=null"}

PLAN_PROMPT = "Original request verbatim and fixed evidence configuration; no additional task interpretation."
EVENT_PROMPT = """Observe this source/candidate event under the original task.
Return JSON with exactly status ('observed' or 'unknown'), observations (list of
{finding:text,evidence_refs:list of supplied frame IDs}), limitations (list of text).
Describe event onset, progression/outcome, contacts, continuity, structural defects
and source correspondence. Distinguish unseen from absent. Do not assign scores,
recommend edits, choose a winner or infer an unseen interval. Report only supplied
consecutive frames; split long events retain their declared segment scope.
"""


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def profile():
    root = Path(__file__).parents[1]
    rubric = (root / "critic_harness/CREATIVE_RUBRIC.md").read_text(encoding="utf-8")
    definitions = (root / "critic_harness/SCORE_DEFINITIONS.md").read_text(encoding="utf-8")
    body = {"protocol_id": PROTOCOL, "policy": POLICY, "rubric": rubric.replace("{{SCORE_DEFINITIONS}}", definitions),
            "source_plan_prompt": PLAN_PROMPT, "event_prompt": EVENT_PROMPT,"execution_policy":FINAL_POLICY,
            "implementation": {name: sha(root / name) for name in
                ("evaluation/low_high.py", "evaluation/final_suite.py", "evaluation/features.py", "evaluation/temporal.py", "evaluation/task_spec.py", "evaluation/task_metrics.py", "evaluation/final_projection.py", "evaluation/registry.py", "critic_harness/one_shot.py", "planner_harness/video.py",
                 "critic_harness/evidence.py", "planner_harness/report_call.py", "planner_harness/model_call.py", "evaluation/creative.py", "evaluation/providers.py", "evaluation/validation.py", "vlm/openrouter.py", "vlm/settings.py", "evaluation/pairwise.py")}}
    from .providers import configuration
    body["judges"] = configuration()
    return {**body, "sha256": signature(body)}


def freeze_plan(body, request, source, directory):
    from .task_spec import build, validate
    if set(body)-{'track','events','motion_preservation'}:
        raise ValueError('Plan body accepts track and optional evidence/motion scope only')
    task=build(request,source['duration_seconds'],track=body.get('track','long'),
               events=body.get('events'),motion=body.get('motion_preservation'))
    validate(task,request,source['duration_seconds'])
    content={'protocol_id':PLAN_PROTOCOL,'source_sha256':source['sha256'],
             'request_sha256':text_sha(request),'task':task}
    plan={**content,'sha256':signature(content)}
    immutable(Path(directory)/'plan.json',plan)
    return plan


def check_plan(plan, request, source):
    if plan.get('sha256')!=signature({k:v for k,v in plan.items() if k!='sha256'}) or plan.get('protocol_id')!=PLAN_PROTOCOL or plan.get('source_sha256')!=source['sha256'] or plan.get('request_sha256')!=text_sha(request):
        raise ValueError('Task plan version or identity changed; use a new evaluation directory')
    from .task_spec import validate
    validate(plan['task'],request,source['duration_seconds'])
    return plan


def _frames(video, identity, group, indices, kind):
    result = []
    for offset in range(0, len(indices), 16):
        part = indices[offset:offset+16]
        observation = video.observe(f"{group}-{offset}", indices=part, count=len(part))
        for frame in observation["frames"]:
            result.append({**frame, "id": f"{identity}:{group}:{frame['frame_index']}",
                           "video_id": identity, "kind": kind})
    return result


def _index(video, time):
    pos = bisect.bisect_left(video.times, time)
    return min(range(max(0, pos-1), min(len(video.times), pos+1)), key=lambda i:abs(video.times[i]-time))


def _visible(rows):
    # File paths, hashes and generation labels are audit-only, never model-visible.
    return [{k:v for k,v in row.items() if k not in {"path", "sha256"}} for row in rows]


def _packet(system, visible, rows, profile_hash):
    from .task_spec import judge_view, scope_view

    rows = [{**row, "attachment": i+1} for i,row in enumerate(rows)]
    visible = {**visible, "evidence": _visible(rows)}
    if visible.get("task_spec") is not None:
        visible["task_spec"] = judge_view(visible["task_spec"])
    if "scope" in visible:
        visible["scope"] = scope_view(visible["scope"])
    if "event_observations" in visible:
        visible["event_observations"] = [
            {**row, "scope": scope_view(row["scope"])}
            for row in visible["event_observations"]
        ]
    return {"system_prompt": system, "user_text": json.dumps(visible, ensure_ascii=False, indent=2),
            "images": rows, "profile_sha256": profile_hash,"input_projection":"evidence-v2-text-requirements-seconds"}


def collect_evidence(request, source, candidates, directory, plan=None):
    directory = Path(directory)
    if plan is not None:
        check_plan(plan, request, source)
    infos = {"source": source, **candidates}
    videos = {}
    for identity, info in infos.items():
        if sha(info["path"]) != info["sha256"]:
            raise ValueError("Evaluation video changed")
        videos[identity] = Video(info["path"], directory / identity)
    source_video = videos["source"]
    count = max(20, math.ceil(source_video.info["duration_seconds"] * 20 / 6))
    targets = [source_video.times[-1] * i / (count-1) for i in range(count)]
    overview, coverage = [], {}
    for identity, video in videos.items():
        available = [t for t in targets if t <= video.times[-1] + 1e-9]
        indices = sorted({_index(video, t) for t in available})
        overview.extend(_frames(video, identity, "overview", indices, "overview"))
        coverage[identity] = {"duration_seconds": video.info["duration_seconds"], "requested_overview": count,
                              "observed_overview": len(indices), "missing_targets": len(targets)-len(available),
                              "overview_mapping": [{"source_time":t,"frame_index":_index(video,t),
                                "actual_time":video.times[_index(video,t)]} for t in available]}
    segments = []
    for event in (plan["task"]["events"] if plan else []):
        event_indices = {}
        for identity, video in videos.items():
            # Include the immediate boundary frame on each side, then every ordinal.
            if event["start"] > video.times[-1]:
                event_indices[identity] = []
            else:
                first = max(0, bisect.bisect_right(video.times, event["start"])-1)
                last = min(len(video.times)-1, bisect.bisect_left(video.times, event["end"]))
                event_indices[identity] = list(range(first,last+1))
        # Freeze subdivision boundaries from SOURCE PTS alone, independent of method/FPS.
        source_indices = event_indices["source"]
        boundaries = [event["start"]]
        for offset in range(28,len(source_indices)-1,28):
            time = source_video.times[source_indices[offset]]
            if boundaries[-1] < time < event["end"]:
                boundaries.append(time)
        boundaries.append(event["end"])
        for part,(lo,hi) in enumerate(zip(boundaries,boundaries[1:])):
            rows, scopes = [], {}
            for identity, video in videos.items():
                ids = event_indices[identity]
                if ids:
                    first = max(ids[0], bisect.bisect_right(video.times,lo)-1)
                    last = min(ids[-1], bisect.bisect_left(video.times,hi))
                    ids = list(range(first,last+1))
                rows.extend(_frames(video, identity, f"{event['id']}p{part}", ids, "consecutive_frames"))
                scopes[identity] = {"frames":len(ids), "interval": [video.times[ids[0]],video.times[ids[-1]]] if ids else None}
            segments.append({"id":f"{event['id']}p{part}", "event":event, "requested_interval":[lo,hi], "coverage":scopes, "rows":rows})
    return overview, segments, coverage


def prepare_plan_request(request, source, directory):
    raise ValueError('Automatic semantic interpretation was removed; freeze the original task locally')


def generate_plan(request, source, directory, model=None):
    raise ValueError('GLM-generated task interpretations are retired; use freeze_plan with the original request and evidence configuration')


def validate_observations(report, packet):
    if not isinstance(report,dict) or set(report) != {"status","observations","limitations"} or report["status"] not in {"observed","unknown"}:
        raise ValueError("Invalid event observation schema")
    refs = {e["id"]:e for e in json.loads(packet["user_text"])["evidence"]}
    if not isinstance(report["limitations"],list) or any(not isinstance(x,str) for x in report["limitations"]):
        raise ValueError("Invalid event limitations")
    if not isinstance(report["observations"],list) or (report["status"] == "observed" and not report["observations"]):
        raise ValueError("An observed event needs evidence")
    for row in report["observations"]:
        if not isinstance(row,dict) or set(row) != {"finding","evidence_refs"} or not isinstance(row["finding"],str) or not row["finding"].strip() or not isinstance(row["evidence_refs"],list) or not row["evidence_refs"] or any(i not in refs for i in row["evidence_refs"]):
            raise ValueError("Event findings must cite supplied frames")
    return report


def prepare_final(request, source, candidate, directory, *, plan=None, model=None):
    directory = Path(directory)
    frozen = profile()
    overview, segments, coverage = collect_evidence(request,source,{"candidate":candidate},directory / "evidence",plan)
    event_reports, reviewed_rows = [], []
    if model is not None:
        if plan is None:
            raise ValueError("Live final evaluation requires a frozen source-only plan; prepare it once for all methods")
        for segment in segments:
            destination = directory / "events" / segment["id"]
            visible = {"original_request":request,"task_spec":plan["task"],
                       "scope":{k:v for k,v in segment.items() if k != "rows"}}
            packet = _packet(EVENT_PROMPT,visible,segment["rows"],frozen["sha256"])
            immutable(destination / "request.json",packet)
            try:
                report, binding = call_report(destination,model,packet,[r["path"] for r in packet["images"]],validate_observations,usage="independent_final")
            except ReportUnavailable:
                report = {"status":"unknown","observations":[],"limitations":["Event review unavailable after bounded attempts"]}
                binding = None
            record = {"report":report,"answer_binding":binding,"scope":visible["scope"]}
            immutable(destination / "observation.json",record)
            event_reports.append({"id":segment["id"],**record,"request_sha256":sha(destination / "request.json")})
            if report["status"] == "observed":
                reviewed_rows.extend(segment["rows"])
    visible = {"protocol_id":PROTOCOL,"candidate_id":"candidate","original_request":request,
               "task_spec":plan["task"] if plan else None,
               "plan_sha256":plan["sha256"] if plan else None,"compare_to":None,"focus":"","extra_checks":[],
               "evidence_policy":POLICY,"coverage":coverage,"videos":coverage,
               "event_observations":[{"id":r["id"],"scope":r["scope"],"report":r["report"]} for r in event_reports],
               "evidence":[]}
    system = frozen["rubric"] + "\nThis is independent final evaluation. Event observations come from your separate reviews of native consecutive frames. Cite their frame IDs with scope. Without observed event evidence TC is unknown. The original request defines requirements. Do not add hidden goals or require a particular creative solution. No generation prompt is supplied."
    packet = _packet(system,visible,overview,frozen["sha256"])
    content = json.loads(packet["user_text"])
    content["evidence"].extend([{**r,"attachment":None,"delivery":"separate_event_review"} for r in _visible(reviewed_rows)])
    packet["user_text"] = json.dumps(content,ensure_ascii=False,indent=2)
    packet["event_records"] = event_reports
    packet["plan"] = plan
    immutable(directory / "evidence/request.json",packet)
    return packet,[r["path"] for r in packet["images"]]


def verify_event_records(directory, packet, model):
    for record in packet.get("event_records",[]):
        path = Path(directory) / "events" / record["id"]
        if sha(path / "request.json") != record["request_sha256"] or load(path / "observation.json") != {k:v for k,v in record.items() if k not in {"id","request_sha256"}}:
            raise ValueError("Cached event evidence changed")
        event_packet = load(path / "request.json")
        validate_observations(record["report"],event_packet)
        if record["answer_binding"] is not None:
            call = verify_answer(path,record["report"])
            verify_inputs(call,model,event_packet,[r["path"] for r in event_packet["images"]])
        else:
            failure = load(path / "unavailable.json")
            for attempt in failure["failures"]:
                verify_inputs(attempt["call_path"],model,event_packet,[r["path"] for r in event_packet["images"]])
                if attempt.get("response_sha256") and sha(Path(attempt["call_path"]) / "response.txt") != attempt["response_sha256"]:
                    raise ValueError("Failed event review response changed")
        if any(sha(r["path"]) != r["sha256"] for r in event_packet["images"]):
            raise ValueError("Cached event frame changed")
