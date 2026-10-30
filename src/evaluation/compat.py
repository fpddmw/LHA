"""Explicit legacy read adapter. Never rewrites original records or guesses score scales."""
from __future__ import annotations
import copy
from .protocol import require
from .registry import METRICS, SCORE_VERSION, STATES


def canonical_result(result):
    out = copy.deepcopy(result)
    version = out.get("scoring_version")
    if version is not None:
        require(version == SCORE_VERSION and out.get("semantic_scale") == "unit_interval", "Unsupported score version/scale")
        factor = 1
    else:
        declared = out.get("semantic_scale")
        reported = out.get("reporting", {}).get("semantic_score_scale")
        require(not declared or not reported or declared == reported, "Conflicting semantic scale declarations")
        scale = declared or reported or "legacy_0_100"
        require(scale in {"legacy_0_100", "unit_interval"}, "Unknown semantic score scale")
        require(out.get("protocol") == "lha-evaluation-v1", "Unversioned results must use the known legacy protocol")
        factor = 100 if scale == "legacy_0_100" else 1
        out["legacy_origin"] = {"semantic_scale": scale, "status_policy": "unrecoverable legacy null statuses remain explicit",
                                "source_reporting": out.pop("reporting", None)}
    for part in out["semantic"].values():
        for key in ("score", "lower", "upper"):
            if part[key] is not None:
                require(0 <= part[key] <= factor, "Semantic score outside declared scale")
                part[key] /= factor
        part["status"] = {"complete": "scored", "unresolved": "unknown"}.get(part["status"], part["status"])
    states = out.setdefault("metric_status", {})
    ratings = out.setdefault("rating_status", {})
    for name, value in out["ratings"].items():
        ratings.setdefault(name, "scored" if value is not None else "not_applicable" if name in {"scene_specific_design", "relative_originality"} and out.get("creativity") == "none" else "legacy_status_unavailable")
        states.setdefault(name, ratings[name])
    for name, part in out["semantic"].items():
        states.setdefault(name, part["status"])
        for field in ("lower", "upper", "coverage", "complete_rate"):
            states.setdefault(name + "_" + field, "scored" if part[field] is not None else part["status"])
    for name in ("success_confirmed", "success_possible", "success_unresolved", "delivery_valid"):
        states.setdefault(name, "scored")
    for name in ("major_damage", "unrequested_damage"):
        states.setdefault(name, "scored" if out[name] is not None else "legacy_status_unavailable")
    for name in ("clip_f", "dino_f"):
        states[name] = "scored" if out.get("automatic", {}).get(name) is not None else states.get(name, "not_measured")
    require(all(states.get(n) in STATES for n in METRICS), "Missing/invalid metric status")
    out.update(scoring_version=SCORE_VERSION, semantic_scale="unit_interval", rate_scale="percent")
    out.setdefault("evaluation_status", "complete")
    return out


def canonical_record(row):
    out = copy.deepcopy(row)
    out["result"] = canonical_result(row["result"])
    r = out["result"]
    failure = "evaluation_error" if row.get("evaluation_error") or row.get("status") == "evaluation_error" else row.get("status") if row.get("status") in {"missing_output", "invalid_delivery"} else None
    if failure:
        r["evaluation_status"] = failure
        for n in METRICS:
            if n not in {"success_confirmed", "success_possible", "success_unresolved", "delivery_valid"} and r["metric_status"][n] != "not_applicable":
                r["metric_status"][n] = failure
        for part in r["semantic"].values():
            if part["status"] != "not_applicable":
                part.update(score=None, lower=None, upper=None, coverage=None, complete_rate=None, status=failure)
        for name in r["ratings"]:
            if r["metric_status"][name] != "not_applicable":
                r["ratings"][name], r["rating_status"][name] = None, failure
        r["success"] = "fail" if failure in {"missing_output", "invalid_delivery"} or r["delivery"] == "invalid" else "unresolved"
        r["failure_reasons"] = [failure] if r["success"] == "fail" else []
    if row.get("feature_error"):
        for n in ("clip_f", "dino_f"): r["metric_status"][n] = "evaluation_error"
    return out
