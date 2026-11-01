"""Requirement-linked evidence and predictions; never a candidate selector."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re

VALUES = {"pass": 1.0, "partial": .5, "fail": 0.0, "unknown": None}
TYPES = {"omitted", "explicit-unrealized", "inherited", "introduced", "capability-suspected", "unknown"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def english(value):
    if re.search(r"[\u3400-\u9fff]", json.dumps(value, ensure_ascii=False)):
        raise ValueError("Use English for RSI working material")


def requirements(items, version=1):
    if not isinstance(items, list) or not items:
        raise ValueError("Provide a nonempty requirement list")
    seen = set()
    for row in items:
        if not isinstance(row, dict) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,59}", str(row.get("id", ""))):
            raise ValueError("Requirements need stable short IDs")
        if row["id"] in seen or not isinstance(row.get("text"), str) or not row["text"].strip():
            raise ValueError("Requirement IDs must be unique and text nonempty")
        if row.get("kind") not in {"edit", "preserve"} or row.get("priority") not in {"core", "detail"}:
            raise ValueError("Use kind edit/preserve and priority core/detail")
        if row.get("origin", "user_requirement") not in {"user_requirement", "source_relation"}:
            raise ValueError("Authored design choices belong in intent, not requirements")
        if "temporal" in row and type(row["temporal"]) is not bool:
            raise ValueError("Optional temporal flag must be boolean")
        interval = row.get("interval_seconds")
        if interval is not None and (not isinstance(interval, list) or len(interval) != 2 or any(type(x) not in {int, float} or not math.isfinite(x) for x in interval) or not 0 <= interval[0] < interval[1]):
            raise ValueError("Temporal interval must be an increasing nonnegative pair")
        seen.add(row["id"])
    english(items)
    body = {"version": version, "items": copy.deepcopy(items)}
    return {**body, "sha256": digest(body)}


def set_requirements(state, items, reason=""):
    if state.get("criteria_authority") == "independent_frozen":
        raise ValueError("Task criteria are independently frozen. Use criteria_objection; design choices belong in the plan.")
    history = state.setdefault("requirement_versions", [])
    if history and not reason.strip():
        raise ValueError("Explain a requirement revision; older judgments remain tied to their version")
    current = requirements(items, len(history) + 1)
    current["reason"] = reason
    history.append(current)
    state["requirements"] = current
    state["task_memory"] = build(state)
    return current


def intent(value, requirement_set):
    if not isinstance(value, dict):
        raise ValueError("RSI generation needs intent with targets, change and expect")
    ids = {r["id"] for r in requirement_set["items"]}
    targets = value.get("targets")
    if not isinstance(targets, list) or not targets or len(set(targets)) != len(targets) or any(t not in ids for t in targets):
        raise ValueError("Intent targets must name current requirement IDs")
    for field in ("change", "expect"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError("Intent change and expect must be brief nonempty text")
    checks = value.get("checks", {})
    expected = value.get("expected_verdicts", {})
    if not isinstance(expected, dict) or any(k not in ids or v not in {"pass", "partial", "fail"} for k, v in expected.items()):
        raise ValueError("Optional expected_verdicts names explicit pass/partial/fail predictions")
    cards = value.get("cards", [])
    if not isinstance(cards, list) or any(not isinstance(c, str) or not c for c in cards) or len(cards) != len(set(cards)):
        raise ValueError("Optional cards contains unique declared skill IDs; it does not imply causal credit")
    if not isinstance(checks, dict) or any(k not in ids or v not in {"improve", "pass", "same_or_better"} for k, v in checks.items()):
        raise ValueError("Optional checks map requirement IDs to improve/pass/same_or_better")
    types = value.get("failure_types", value.get("failure_type", {}))
    if not isinstance(types, dict):
        raise ValueError("Optional failure_types maps IDs to one or more hypotheses")
    for k, v in types.items():
        tags = v if isinstance(v, list) else [v]
        if k not in ids or not tags or any(t not in TYPES for t in tags):
            raise ValueError("Unknown failure hypothesis")
    english(value)
    return copy.deepcopy(value)


def resolve_baseline(state, wanted):
    """An evaluation reference is independent of the renderer's conditioning input."""
    explicit = wanted.get("baseline")
    if explicit is not None:
        if explicit not in state["videos"]:
            raise ValueError("Intent baseline must name an available video")
        return explicit
    current = state["requirements"]["sha256"]
    reviewed = [f.get("video_id", f.get("candidate")) for f in state.get("evaluations", {}).values()
                if f.get("outcome", {}).get("requirements_sha256") == current]
    return next((v for v in reversed(reviewed) if v in state["videos"] and v != "source"), "source")


def resolved_checks(wanted, before):
    """Default target checks are bookkeeping, not a paraphrase of a prose hypothesis."""
    if "checks" in wanted:
        return wanted["checks"], "planner_declared"
    checks = {k: "same_or_better" if before.get(k) == "pass" else "improve"
              if before.get(k) in {"partial", "fail"} else "pass" for k in wanted.get("targets", [])}
    return checks, "derived_target_attainment; free-text expectation remains unscored"


def temporal_coverage(interval, ranges):
    merged = []
    for start, end in sorted((max(interval[0], a), min(interval[1], b)) for a, b in ranges):
        if end <= start:
            continue
        if merged and start <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return {"intervals": merged, "fraction": min(1.0, sum(b-a for a, b in merged) / (interval[1]-interval[0]))}


def validate_review(report, requirement_set, candidate, videos, observations):
    """Validate structured outcome claims, anchored to actual observations."""
    rows = report.get("requirement_verdicts")
    ids = {r["id"] for r in requirement_set["items"]}
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows) or len(rows) != len(ids) or {r.get("id") for r in rows} != ids:
        raise ValueError("Assess every current requirement, including unknowns")
    for row in rows:
        rule = next(r for r in requirement_set["items"] if r["id"] == row["id"])
        if row.get("verdict") == "partial" and rule.get("partial_rule") == "not allowed":
            raise ValueError("This frozen criterion does not allow a partial verdict")
        if row.get("verdict") not in VALUES or not isinstance(row.get("evidence"), str) or not row["evidence"].strip():
            raise ValueError("Each requirement needs a verdict and evidence explanation")
        refs = row.get("observations", [])
        if not isinstance(refs, list) or any(r not in observations for r in refs):
            raise ValueError("Use actual observation IDs")
        if row["verdict"] != "unknown" and (not refs or not any(any(f["video"] == candidate for f in observations[r]["frames"]) for r in refs)):
            raise ValueError("A known requirement verdict needs candidate observation evidence")
        deltas = row.get("delta_vs", {})
        if not isinstance(deltas, dict) or any(k not in videos or k == candidate or v not in {"improved", "same", "worse", "unknown"} for k, v in deltas.items()):
            raise ValueError("Comparison deltas must name available other videos")
        observed = {f["video"] for ref in refs for f in observations[ref]["frames"]}
        if any(delta != "unknown" and not {candidate, other} <= observed for other, delta in deltas.items()):
            raise ValueError("Known comparison deltas need both videos in observed evidence")
        requirement = next(r for r in requirement_set["items"] if r["id"] == row["id"])
        if requirement["kind"] == "preserve" and row["verdict"] != "unknown" and "source" not in observed:
            raise ValueError("Known preservation verdicts require original source evidence")
        if requirement.get("temporal"):
            from critic_harness.evidence import covered
            interval = requirement.get("interval_seconds", [0, videos[candidate]["duration_seconds"]])
            counterexample = row.get("counterexample_interval")
            if counterexample is not None and (row["verdict"] != "fail" or not isinstance(counterexample, list) or len(counterexample) != 2
                    or any(type(v) not in {int, float} or not math.isfinite(v) for v in counterexample)
                    or not interval[0] <= counterexample[0] < counterexample[1] <= interval[1]):
                raise ValueError("A temporal counterexample must be a failed requirement with a valid observed interval")
            evidence_interval = counterexample or interval
            coverage, sufficient = {}, True
            for identity in ({candidate, "source"} if requirement["kind"] == "preserve" else {candidate}):
                ranges = [observations[ref]["videos"][identity]["actual_interval"] for ref in refs
                          if identity in observations[ref].get("videos", {}) and observations[ref]["videos"][identity]["continuous"]
                          and observations[ref]["videos"][identity]["crop"] is None]
                coverage[identity] = temporal_coverage(interval, ranges)
                sufficient = sufficient and covered(ranges, evidence_interval)
            row["temporal_coverage"] = coverage
            row["claim_scope"] = "local_counterexample" if counterexample else "whole_interval" if sufficient else "observed_intervals_only"
            if counterexample and not sufficient:
                raise ValueError("Temporal counterexample exceeds observed continuous evidence")
            if not sufficient and row["verdict"] != "unknown":
                row["observed_interval_verdict"] = row["verdict"]
                row["verdict"] = "unknown"
                row["delta_vs"] = {k: "unknown" for k in deltas}
                row["scope_note"] = "Sampled-interval finding retained; the whole requirement remains unresolved."
    added = report.get("added_requirements", [])
    if not isinstance(added, list) or any(not isinstance(r, dict) or not r.get("text") or not r.get("evidence") for r in added):
        raise ValueError("Added requirement suggestions need text and evidence")
    if "major_damage" not in report or (report["major_damage"] is not None and type(report["major_damage"]) is not bool):
        raise ValueError("major_damage must be true, false or null")
    report["requirements_sha256"] = requirement_set["sha256"]
    report["requirements_version"] = requirement_set["version"]
    if requirement_set.get("criteria_contract") and report["major_damage"] is True:
        damages = report.get("damages", [])
        if not damages:
            raise ValueError("Major damage requires evidence and a task-identity rationale")
        for damage in damages:
            linked = damage.get("requirement_ids", [])
            if not isinstance(linked, list) or not set(linked) <= ids or not damage.get("evidence") or not damage.get("reason"):
                raise ValueError("Damage must link valid criteria and explain observed consequence")
            if linked and not any(r["priority"] == "core" for r in requirement_set["items"] if r["id"] in linked):
                raise ValueError("Detail-only damage cannot be promoted to major")
            if linked and all(r["verdict"] == "pass" for r in rows if r["id"] in linked):
                raise ValueError("Major damage contradicts passing linked criteria; clarify the actual failed relation")
            if not linked and not damage.get("unlisted_task_identity_relation"):
                raise ValueError("Unlisted major damage must identify the task-defining relation")
            refs = damage.get("observations", [])
            observed = {f["video"] for ref in refs if ref in observations for f in observations[ref]["frames"]}
            if not {candidate, "source"} <= observed:
                raise ValueError("Major damage requires actual source/candidate observations")
    english(report)
    return report


def scores(items, verdicts):
    result = {}
    for kind in ("edit", "preserve"):
        for priority in (None, "core", "detail"):
            selected = [i for i in items if i["kind"] == kind and (priority is None or i["priority"] == priority)]
            vals = [VALUES[verdicts.get(i["id"], "unknown")] for i in selected]
            key = kind + ("_" + priority if priority else "")
            n = len(vals)
            groups = {}
            for item, value in zip(selected, vals):
                group = groups.setdefault(item.get("group", item["id"]), {"weight": item.get("group_weight", 1), "values": []})
                group["values"].append(value)
            total = sum(g["weight"] for g in groups.values())
            lower = sum(g["weight"] * sum(v or 0 for v in g["values"]) / len(g["values"]) for g in groups.values()) / total if total else None
            upper = sum(g["weight"] * sum(1 if v is None else v for v in g["values"]) / len(g["values"]) for g in groups.values()) / total if total else None
            result[key] = {"score": lower if n and None not in vals else None, "lower": lower, "upper": upper,
                           "items": n, "groups": len(groups), "aggregation": "fixed_goal_weight_then_item_mean", "known": sum(v is not None for v in vals), "unknown": vals.count(None),
                           "status": "not_applicable" if not n else "unknown" if None in vals else "scored"}
    return result


def project_findings(report, requirement_set, candidate, observations, duration):
    """Reuse a single model-authored verdict list in the existing evidence validator."""
    if report.get("findings"):
        return report
    lookup = {r["id"]: r for r in requirement_set["items"]}
    findings = []
    for row in report["requirement_verdicts"]:
        req = lookup[row["id"]]
        needed = [candidate, "source"] if req["kind"] == "preserve" else [candidate]
        refs = [{"observation_id": ref, "video": video} for ref in row.get("observations", []) for video in needed
                if video in observations[ref].get("videos", {})]
        finding = {"id": "requirement-" + row["id"], "dimension": "preservation" if req["kind"] == "preserve" else "edit",
                   "origin": "preservation" if req["kind"] == "preserve" else "user_requirement", "importance": req["priority"],
                   "verdict": row["verdict"], "claim": row["evidence"], "evidence": refs, "projection": "requirement_verdicts"}
        if row["verdict"] == "partial":
            finding["partial_boundary"] = row["evidence"]
        if req.get("temporal"):
            finding.update(requires_sequence=True, interval_seconds=row.get("counterexample_interval", req.get("interval_seconds", [0, duration])),
                           sequence_videos=needed, scope="whole frame")
        findings.append(finding)
    report["findings"] = findings
    return report


def prediction(wanted, before, after):
    results = {}
    for identity, op in wanted.get("checks", {}).items():
        a, b = VALUES.get(before.get(identity, "unknown")), VALUES.get(after.get(identity, "unknown"))
        if b is None or (op != "pass" and a is None):
            results[identity] = "unknown"
        else:
            results[identity] = "hit" if (b == 1 if op == "pass" else b > a if op == "improve" else b >= a) else "miss"
    if not results:
        outcome = "unscored_text_prediction"
    elif "unknown" in results.values():
        outcome = "unknown"
    elif all(v == "hit" for v in results.values()):
        outcome = "hit"
    elif "hit" in results.values():
        outcome = "partial"
    else:
        outcome = "miss"
    return {"outcome": outcome, "checks": results, "expect": wanted.get("expect")}


def build(state):
    current = state.get("requirements")
    if not current:
        return {"status": "requirements_not_defined", "attempts": []}
    candidates, attempts = {}, []
    for feedback_id, feedback in state.get("evaluations", {}).items():
        out = feedback.get("outcome", {})
        if out.get("requirements_sha256") != current["sha256"]:
            continue
        video = feedback.get("video_id", feedback.get("candidate"))
        verdicts = {r["id"]: r["verdict"] for r in out.get("requirement_verdicts", [])}
        candidates[video] = {"verdicts": verdicts, "scores": scores(current["items"], verdicts),
                             "evidence_scopes": {r["id"]: {k: r[k] for k in ("claim_scope", "temporal_coverage", "observed_interval_verdict", "scope_note") if k in r}
                                                 for r in out.get("requirement_verdicts", [])},
                             "failure_types": feedback.get("feedback", {}).get("failure_types", {}),
                             "major_damage": out.get("major_damage"), "added_requirements": out.get("added_requirements", []),
                             "feedback": feedback_id, "sha256": feedback.get("sha256")}
    streaks = {r["id"]: 0 for r in current["items"]}
    unknown_targets = {r["id"]: 0 for r in current["items"]}
    repairs = []
    for job_id, job in state.get("jobs", {}).items():
        if job["kind"] != "generate":
            continue
        payload = job["payload"]
        if payload.get("requirements", {}).get("sha256") != current["sha256"]:
            continue
        video = next((k for k, v in state.get("videos", {}).items() if v.get("job_id") == job_id), None)
        after = candidates.get(video, {}).get("verdicts", {})
        baseline = payload.get("comparison_baseline", payload["input_id"])
        before = candidates.get(baseline, {}).get("verdicts", {})
        wanted = payload.get("intent", {})
        regressions = [k for k, v in after.items() if VALUES[v] is not None and VALUES.get(before.get(k)) is not None and VALUES[v] < VALUES[before[k]]]
        for k in streaks:
            if after.get(k) == "pass":
                streaks[k] = 0
            elif k in wanted.get("targets", []) and after.get(k) in {"partial", "fail"}:
                streaks[k] += 1
            elif k in wanted.get("targets", []) and video:
                unknown_targets[k] += 1
        for k in wanted.get("targets", []):
            earlier = VALUES.get(before.get(k))
            later = VALUES.get(after.get(k))
            repairs.append({"job": job_id, "requirement": k,
                            "failure_hypotheses_before": wanted.get("failure_types", wanted.get("failure_type", {})).get(k, []),
                            "result": "unknown" if earlier is None or later is None else "improved" if later > earlier else "regressed" if later < earlier else "unchanged"})
        checks, basis = resolved_checks(wanted, before)
        categorical = {k: "unknown" if after.get(k) in {None, "unknown"} else "hit" if after[k] == v else "miss"
                       for k, v in wanted.get("expected_verdicts", {}).items()}
        attempts.append({"job": job_id, "video": video, "input": payload["input_id"], "baseline": baseline,
                         "baseline_status": "reviewed" if baseline in candidates else "unreviewed_reference",
                         "intent": wanted, "prediction": {**prediction({**wanted, "checks": checks}, before, after), "basis": basis},
                         "categorical_prediction": {"expected": wanted.get("expected_verdicts", {}), "results": categorical,
                                                    "basis": "planner_declared; categorical accuracy, not probability calibration"},
                         "collateral_regressions": regressions,
                         "review_status": "reviewed" if video in candidates else "pending_or_unavailable"})
    return {"requirements": current, "candidates": candidates, "attempts": attempts,
            "delivery_candidate": state.get("delivery_candidate", state.get("final", {}).get("video")),
            "targeted_nonachievement_counts": streaks, "targeted_unknown_counts": unknown_targets,
            "repair_observations": repairs,
            "scope": "Online evidence only. Unknown bounds are logical ranges. No automatic ranking or stopping policy."}
