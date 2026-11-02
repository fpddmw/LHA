"""Passive lineage/score/cost analysis and unsubmitted matched control plans."""
import copy
from collections import defaultdict
import math

from .execution import signature


def _reports(state, identity):
    """Keep historical qualitative feedback in its original scale and schema."""
    rows = []
    for key, value in state.get("evaluations", {}).items():
        if value.get("video_id") != identity:
            continue
        report = value.get("report", value.get("outcome"))
        if not isinstance(report, dict):
            continue
        rows.append({"job_id": key, "protocol": value.get("protocol"),
                     "profile_sha256": value.get("profile_sha256"),
                     "format": "scored" if "main_scores" in report else "historical_qualitative",
                     "report": copy.deepcopy(report)})
    return rows


def _seconds(video):
    value = (video.get("execution") or {}).get("generation_seconds")
    return value if type(value) in {int, float} and math.isfinite(value) and value >= 0 else None


def _difference(left, right):
    """Report paired observations, without converting old verdicts into scores."""
    if len(left) != 1 or len(right) != 1:
        return {"status": "unavailable", "reason": "Exactly one assessment per candidate is required"}
    a, b = left[0], right[0]
    if (a["protocol"], a["profile_sha256"], a["format"]) != (b["protocol"], b["profile_sha256"], b["format"]):
        return {"status": "unavailable", "reason": "Assessment protocols/profiles differ"}
    result = {"status": "descriptive", "left_job": a["job_id"], "right_job": b["job_id"],
              "protocol": a["protocol"], "profile_sha256": a["profile_sha256"],
              "score_deltas": {}, "requirement_transitions": [],
              "interpretation": "Right minus left within recorded assessments; prompts, evidence coverage and selection can differ."}
    if a["format"] == "scored":
        if not a["profile_sha256"]:
            return {"status": "unavailable", "reason": "Scoring profile identity is missing"}
        for key, value in a["report"]["main_scores"].items():
            other = b["report"]["main_scores"].get(key, {})
            if value.get("status") == other.get("status") == "scored":
                result["score_deltas"][key] = {"left": value["score"], "right": other["score"],
                    "delta": other["score"] - value["score"],
                    "left_evidence_refs": value.get("evidence_refs", []),
                    "right_evidence_refs": other.get("evidence_refs", [])}
    else:
        version = a["report"].get("requirements_sha256")
        if version and version == b["report"].get("requirements_sha256"):
            right_items = {r["id"]: r for r in b["report"].get("requirement_verdicts", [])}
            for row in a["report"].get("requirement_verdicts", []):
                other = right_items.get(row["id"])
                if other:
                    result["requirement_transitions"].append({"id": row["id"],
                        "left": row["verdict"], "right": other["verdict"],
                        "left_evidence": row.get("evidence"), "right_evidence": other.get("evidence"),
                        "left_scope": row.get("claim_scope"), "right_scope": other.get("claim_scope"),
                        "left_coverage": row.get("temporal_coverage"), "right_coverage": other.get("temporal_coverage")})
        result["qualitative_summaries"] = {"left": a["report"].get("summary"), "right": b["report"].get("summary")}
        result["historical_scope"] = "Original online feedback and original evidence; no rescoring under the current rubric."
    return result


def analyze(state):
    videos = state["videos"]
    depths = {"source": 0}
    def depth(identity, seen=()):
        if identity in depths:
            return depths[identity]
        if identity in seen or identity not in videos:
            raise ValueError("Invalid candidate lineage")
        parent = videos[identity].get("parent")
        if parent is None:
            return None
        value = depth(parent, (*seen, identity))
        depths[identity] = None if value is None else value + 1
        return depths[identity]
    rows, by_depth, controls = [], defaultdict(list), []
    for identity, video in videos.items():
        if identity == "source" or video.get("imported"):
            continue
        d = depth(identity)
        job = state.get("jobs", {}).get(video.get("job_id"), {})
        payload = job.get("payload", {})
        if payload and payload.get("input_id") != video.get("parent"):
            raise ValueError("Candidate parent differs from its signed generation input")
        reports = _reports(state, identity)
        ancestors = []
        ancestor = identity
        while ancestor != "source" and ancestor is not None:
            ancestors.append(ancestor)
            ancestor = videos[ancestor].get("parent")
        costs = [_seconds(videos[k]) for k in ancestors]
        row = {"candidate":identity, "parent":video.get("parent"), "depth":d,
               "input_strategy":"source_restart" if video.get("parent") == "source" else "chain",
               "generation_seconds":_seconds(video),
               "ancestry_cost": {"candidates": list(reversed(ancestors)),
                   "known_generation_seconds": sum(t for t in costs if t is not None),
                   "unknown_generations": sum(t is None for t in costs),
                   "scope": "Sum of generation wall times on this ancestry, not monetary cost or total search cost."},
               "reports":reports, "qualitative_evidence":"Follow report evidence_refs and the original online-review packet.",
               "metrics_scope":"Instruction adherence measures intended edits; source content preservation and temporal consistency use the task rubric. Parent changes require explicit parent comparisons."}
        rows.append(row)
        by_depth[str(d)].append(identity)
        if video.get("parent") in {None, "source"}:
            continue
        if not payload.get("prompt") or type(payload.get("renderer", {}).get("seed")) is not int:
            continue
        settings = {k:payload.get(k) for k in ("prompt", "renderer")}
        for other, output in videos.items():
            other_payload = state.get("jobs",{}).get(output.get("job_id"),{}).get("payload",{})
            if output.get("parent") == "source" and settings == {k:other_payload.get(k) for k in settings}:
                controls.append({"chain":identity, "source_restart":other, "matched_fields":list(settings),
                                 "settings_sha256": signature(settings),
                                 "assessment_difference": _difference(_reports(state, other), reports),
                                 "scope": "Recorded prompt, seed and complete renderer configuration match. Verify receipt/effective prompt and media before treating this as an executed control.",
                                 "budget":"one render each; upstream chain cost remains reported separately"})
    aggregates = {}
    for d, identities in by_depth.items():
        subset = [r for r in rows if r["candidate"] in identities]
        score_groups = defaultdict(lambda: defaultdict(list))
        for row in subset:
            # The one-main-review policy prevents selection among alternative scores.
            if len(row["reports"]) == 1 and row["reports"][0]["format"] == "scored":
                assessment = row["reports"][0]
                group = signature({k: assessment[k] for k in ("protocol", "profile_sha256")})
                for name, value in assessment["report"]["main_scores"].items():
                    if value["status"] == "scored":
                        score_groups[group][name].append(value["score"])
        groups = {g:{k:{"n":len(v),"mean":sum(v)/len(v)} for k,v in scores.items()} for g,scores in score_groups.items()}
        aggregates[d] = {"candidates":identities, "scores":next(iter(groups.values())) if len(groups) == 1 else {},
                         "score_groups": groups,
                         "known_generation_seconds":sum(r["generation_seconds"] for r in subset if r["generation_seconds"] is not None),
                         "unknown_costs":sum(r["generation_seconds"] is None for r in subset)}
    edges = [{"parent": row["parent"], "child": row["candidate"], "depth": row["depth"],
              "assessment_difference": _difference(_reports(state, row["parent"]), row["reports"])}
             for row in rows if row["parent"] not in {None, "source"}]
    return {"version":"lineage-analysis-v2", "candidates":rows, "by_depth":aggregates,
            "parent_child_changes": edges, "matched_restart_controls":controls,
            "limits":"Observational trajectories confound prompts, inputs and selection. No degradation effect is inferred without target-aware assessment and matched controls."}


def control_plan(state, candidate):
    video = state["videos"][candidate]
    if video.get("parent") in {None, "source"}:
        raise ValueError("Choose a chained candidate with a recorded generation job")
    payload = state["jobs"][video["job_id"]]["payload"]
    if not payload.get("prompt") or type(payload.get("renderer", {}).get("seed")) is not int:
        raise ValueError("Matched controls need a recorded prompt and explicit renderer seed")
    requests = []
    for label, identity in (("chain", video["parent"]), ("source_restart", "source")):
        request = {"id":"lineage-control-" + signature({"candidate":candidate,"label":label,"payload":payload})[:16],
                   "kind":"generate", "mode":"live", "payload":{
            **copy.deepcopy(payload), "input_id":identity, "input":copy.deepcopy(state["videos"][identity])}}
        digest = signature(request)
        requests.append({"label":label, "request":{**request,"sha256":digest}, "sha256":digest})
    return {"version":"lineage-control-plan-v2", "status":"not_submitted", "candidate":candidate,
            "request":state["request"]["text"], "requests":requests,
             "matching": {"fields": ["prompt", "renderer"], "seed": payload["renderer"]["seed"],
                          "settings_sha256": signature({k:payload[k] for k in ("prompt", "renderer")})},
             "required_preflight": ["Verify local input paths and media hashes", "Bind a new execution/budget scope",
                                    "Verify renderer assets and effective prompts", "Use the same frozen assessment and intended-edit/preservation questions"],
            "assessment":"Blind source/candidate instruction and preservation/temporal reports plus explicit parent comparison; retain intended changes and damage findings separately.",
            "execution":"Requires separately authorized equal-cost rendering; analysis never dispatches these plans."}
