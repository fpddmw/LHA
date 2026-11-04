"""Two independent randomized/swapped blind comparisons; no absolute score inputs."""
import json
import random
from pathlib import Path
from collections import defaultdict
from statistics import mean

from planner_harness.execution import immutable
from planner_harness.common import sha, load
from planner_harness.report_call import call_report, ReportUnavailable
from .low_high import collect_evidence, check_plan, profile, _packet, _visible, EVENT_PROMPT, validate_observations

PROTOCOL = "lha-low-high-blind-v2"
QUESTIONS = ("task_completion", "production_quality")
PROMPT = """Compare anonymized A and B against the original request, source and shared
interpretation. You have no generation prompts, method names, iteration, online scores
or costs. Return JSON with exactly protocol_id and judgments. judgments contains exactly
task_completion and production_quality; each has winner (A, B, tie, unknown), reason
(nonempty text), evidence_refs (supplied frame IDs), limitations (list of text).
task_completion asks which output better recasts this moment into the requested world
or medium while keeping the moment recognizable: coverage of the medium across scene and
duration, central requested elements, and recognizable roles, beats and interactions.
Closeness to the source beyond recognizability is not an advantage; cosmetic advantage
does not offset a central failure. production_quality asks which output is the more
stable, clean and integrated sequence: temporal stability (medium switching, boiling,
popping, drift, end-of-clip collapse), structural integrity of faces, hands, props and
contacts, figure/background separation, and aesthetic integration. Unconverted but stable
regions count as stable here; an unrequested live-action/stylized mixture counts as an
integration defect. Authorized behavior reinterpretation is not a preservation error.
Answer the two questions independently. Prefer tie for supported equivalence,
unknown for insufficient evidence. The relative winner may still fail the absolute task.
Cite both outputs for every supported choice/tie, and source evidence for task_completion.
Temporal statements need event observations; do not infer motion from overview alone.
Use the common scoring definitions below as concepts, but return relative choices only.
"""


def validate_comparison(report, packet):
    visible = json.loads(packet["user_text"])
    if not isinstance(report,dict) or set(report) != {"protocol_id","judgments"} or report["protocol_id"] != visible["protocol_id"]:
        raise ValueError("Blind comparison protocol mismatch")
    if not isinstance(report["judgments"],dict) or set(report["judgments"]) != set(QUESTIONS):
        raise ValueError("Two blind questions are required")
    refs = {e["id"]:e for e in visible["evidence"]}
    for question,row in report["judgments"].items():
        if not isinstance(row,dict) or set(row) != {"winner","reason","evidence_refs","limitations"} or row["winner"] not in {"A","B","tie","unknown"}:
            raise ValueError("Invalid blind judgment")
        if not isinstance(row["reason"],str) or not row["reason"].strip() or not isinstance(row["limitations"],list) or any(not isinstance(x,str) for x in row["limitations"]):
            raise ValueError("Explain the choice and evidence limits")
        ids = row["evidence_refs"]
        if not isinstance(ids,list) or any(not isinstance(i,str) or i not in refs for i in ids):
            raise ValueError("Unknown blind evidence reference")
        required = {"A","B","source"} if question == "task_completion" else {"A","B"}
        if row["winner"] != "unknown" and not required <= {refs[i]["video_id"] for i in ids}:
            raise ValueError("Supported blind judgment needs both outputs and relevant source")
    return report


def reconcile(first, second, first_order):
    results = {}
    orders = [first_order, first_order[::-1]]
    for question in QUESTIONS:
        mapped = []
        for report,order in zip((first,second),orders):
            value = report["judgments"][question]["winner"] if report else "unknown"
            mapped.append(order[0 if value == "A" else 1] if value in {"A","B"} else value)
        status = "unknown" if "unknown" in mapped else (mapped[0] if mapped[0] == mapped[1] else "order_unstable")
        results[question] = {"outcome":status,"mapped_orders":mapped}
    return results


def compare(request, source, left, right, directory, *, plan, seed, model=None):
    directory = Path(directory)
    if (directory/"result.json").exists():return load(directory/"result.json")
    check_plan(plan,request,source)
    from planner_harness.upgrade import retain
    order = ["left","right"]
    random.Random(str(seed) + source["sha256"] + ''.join(sorted([left["sha256"],right["sha256"]]))).shuffle(order)
    frozen = profile()
    definitions = Path(__file__).parents[1].joinpath("critic_harness/SCORE_DEFINITIONS.md").read_text(encoding="utf-8")
    binding = {"protocol_id":PROTOCOL,"final_profile_sha256":frozen["sha256"],"implementation_sha256":sha(__file__),
               "source_sha256":source["sha256"],"left_sha256":left["sha256"],"right_sha256":right["sha256"],
               "plan_sha256":plan["sha256"],"seed":seed,"first_order":order,
               "judge":getattr(model,"model",None),"reasoning_effort":getattr(model,"reasoning_effort",None)}
    binding = retain(directory / "binding.json",binding)
    order = binding["first_order"]
    reports = []
    for number,labels in enumerate((order,order[::-1]),1):
        path = directory / f"order-{number}"
        info = {"left":left,"right":right}
        overview, segments, coverage = collect_evidence(request,source,{"A":info[labels[0]],"B":info[labels[1]]},path / "evidence",plan)
        observations, reviewed = [], []
        if model is not None:
            for segment in segments:
                target = path / "events" / segment["id"]
                packet = _packet(EVENT_PROMPT.replace("source/candidate", "source and anonymized A/B"),
                    {"original_request":request,"task_spec":plan["task"],"scope":{k:v for k,v in segment.items() if k != "rows"}},segment["rows"],frozen["sha256"])
                packet = retain(target / "request.json",packet)
                try:
                    report,answer = call_report(target,model,packet,[r["path"] for r in packet["images"]],validate_observations,usage="independent_final")
                except ReportUnavailable:
                    report={"status":"unknown","observations":[],"limitations":["Event review unavailable after bounded attempts"]}
                    answer=None
                immutable(target / "observation.json",{"report":report,"answer_binding":answer})
                observations.append({"scope":{k:v for k,v in segment.items() if k != "rows"},"report":report})
                if report["status"] == "observed":
                    reviewed.extend(segment["rows"])
        packet = _packet(PROMPT + definitions,{"protocol_id":PROTOCOL,"original_request":request,
            "task_spec":plan["task"],"coverage":coverage,"event_observations":observations},overview,frozen["sha256"])
        visible = json.loads(packet["user_text"])
        visible["evidence"].extend([{**r,"attachment":None,"delivery":"separate_event_review"} for r in _visible(reviewed)])
        packet["user_text"] = json.dumps(visible,ensure_ascii=False,indent=2)
        packet = retain(path / "request.json",packet)
        if model is not None:
            try:
                report,answer = call_report(path,model,packet,[r["path"] for r in packet["images"]],validate_comparison,usage="independent_final")
            except ReportUnavailable:
                report,answer=None,None
            immutable(path / "comparison.json",{"report":report,"answer_binding":answer})
            reports.append(report)
    result = {**binding,"status":("scored" if all(r is not None for r in reports) else "partial") if model is not None else "request_export_only",
              "judge":getattr(model,"model",None),"reasoning_effort":getattr(model,"reasoning_effort",None),
              "judgments":reconcile(*reports,order) if reports else None}
    immutable(directory / ("result.json" if model else "export.json"),result)
    return result


def summary(rows):
    """One row per planned comparison: source_id, length, judge, result (or null)."""
    groups = defaultdict(list)
    profiles={row["result"]["final_profile_sha256"] for row in rows if row.get("result")}
    comparisons={row.get("comparison","pair") for row in rows}
    if len(profiles)>1 or len(comparisons)>1:
        raise ValueError("Summarize one frozen protocol and one method comparison at a time")
    seen=set()
    for row in rows:
        if row.get("sample_id") is not None:
            key=(row.get("source_id"),row["sample_id"],row.get("judge"),row.get("length"))
            if key in seen:raise ValueError("Duplicate planned blind pair")
            seen.add(key)
        if row["length"] not in {"short","long"} or not row.get("source_id") or not row.get("judge"):
            raise ValueError("Every planned comparison needs source_id, short/long and judge")
        for scope in (row["length"],"all"):
            groups[(row["judge"],scope)].append(row)
    output = {}
    for (judge,scope),group in groups.items():
        columns = {}
        for question in QUESTIONS:
            counts = {key:0 for key in ("left","right","tie","unknown","order_unstable","missing")}
            sources = defaultdict(list)
            for row in group:
                result = row.get("result")
                if result and result.get("judge") != judge:
                    raise ValueError("Do not merge judges")
                outcome = result["judgments"][question]["outcome"] if result and result.get("judgments") else "missing"
                counts[outcome] += 1
                if outcome in {"left","right","tie"}:
                    sources[row["source_id"]].append({"left":1,"right":0,"tie":0.5}[outcome])
            valid = counts["left"] + counts["right"] + counts["tie"]
            columns[question] = {"planned":len(group),"valid":valid,**counts,
                "planned_sources":len({r["source_id"] for r in group}),"valid_sources":len(sources),
                "left_preference_micro":(counts["left"]+0.5*counts["tie"])/valid if valid else None,
                "left_preference_source_macro":mean(mean(v) for v in sources.values()) if sources else None}
        output.setdefault(judge,{})[scope] = columns
    return output
