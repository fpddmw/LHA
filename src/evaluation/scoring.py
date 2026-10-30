"""Deterministic canonical scores from frozen-card judgments; semantic scale is 0–1."""
from __future__ import annotations
from statistics import mean
from . import PROTOCOL
from .protocol import validate_card, validate_judgment, signature, require
from .registry import (AESTHETICS, DEFINITIONS, LABELS, METRICS, RATINGS, SEMANTIC, SCORE_VERSION,
                       SUCCESS, VERSION, applicable, fingerprint)
from .registry import judgment_fingerprint, scoring_fingerprint


def base_result(card, role="unspecified"):
    return {"protocol": PROTOCOL, "scoring_version": SCORE_VERSION, "metric_registry_version": VERSION,
            "metric_registry_sha256": fingerprint(), "evaluation_role": role,
            "scoring_contract_sha256": scoring_fingerprint(),
            "applicability": {n: applicable(n, card) for n in METRICS},
            **{k: card[k] for k in ("card_sha256", "task_id", "source_id", "track", "split", "style_family", "creativity")},
            "semantic_scale": "unit_interval", "rate_scale": "percent"}


def semantic_score(card, judgment, kinds, temporal_only=False):
    labels = {r["id"]: LABELS[r["label"]] for r in judgment["items"]}
    groups = []
    for group in card["groups"]:
        selected = [i for i in group["items"] if not temporal_only or i["temporal"]]
        if group["kind"] not in kinds or not selected:
            continue
        values = [labels[i["id"]] for i in selected]
        groups.append({"lower": sum(v or 0 for v in values) / len(values),
            "upper": sum(1 if v is None else v for v in values) / len(values),
            "complete": sum(v == 1 for v in values) / len(values),
            "coverage": sum(v is not None for v in values) / len(values),
            "items": len(values), "unknown": values.count(None)})
    if not groups:
        return dict(score=None, lower=None, upper=None, complete_rate=None, coverage=None,
                    items=0, unknown=0, status="not_applicable")
    lower, upper = mean(g["lower"] for g in groups), mean(g["upper"] for g in groups)
    unknown = sum(g["unknown"] for g in groups)
    return {"score": lower if not unknown else None, "lower": lower, "upper": upper,
            "complete_rate": 100 * mean(g["complete"] for g in groups) if not unknown else None,
            "coverage": 100 * mean(g["coverage"] for g in groups), "items": sum(g["items"] for g in groups),
            "unknown": unknown, "status": "scored" if not unknown else "unknown"}


def metric_states(result, rating_states):
    states = dict(rating_states)
    for name, part in result["semantic"].items():
        states[name] = part["status"]
        for suffix in ("lower", "upper", "complete_rate", "coverage"):
            states[name + "_" + suffix] = "scored" if part[suffix] is not None else part["status"]
    states.update({n: "scored" for n in ("success_confirmed", "success_possible", "success_unresolved", "delivery_valid")})
    for n in ("major_damage", "unrequested_damage"):
        states[n] = "scored" if result[n] is not None else result.get("evaluation_status", "unknown")
        if states[n] == "complete": states[n] = "unknown"
    states.update(clip_f="not_measured", dino_f="not_measured")
    return states


def error_result(card, delivery, reason, *, status="evaluation_error", role="final"):
    """Record an execution outcome without inventing an evidence-insufficient judgment."""
    validate_card(card)
    if status not in {"evaluation_error", "missing_output", "invalid_delivery"}:
        raise ValueError("Invalid execution failure category")
    semantic = {}
    for name in SEMANTIC:
        d = DEFINITIONS[name]
        n = sum(sum(not d["temporal_only"] or i["temporal"] for i in g["items"])
                for g in card["groups"] if g["kind"] in d["kinds"])
        semantic[name] = dict(score=None, lower=None, upper=None, complete_rate=None, coverage=None,
                              items=n, unknown=0, unassessed_items=n, status=status if n else "not_applicable")
    failed = status in {"missing_output", "invalid_delivery"} or delivery["status"] == "invalid"
    result = {**base_result(card, role), "evaluation_status": status, "outcome_reason": reason,
              "semantic": semantic, "ratings": {n: None for n in (*RATINGS, "aesthetic_mean")},
              "rating_status": {n: status if applicable(n, card) else "not_applicable" for n in (*RATINGS, "aesthetic_mean")},
              "success": "fail" if failed else "unresolved", "failure_reasons": [status] if failed else [],
              "delivery": delivery["status"], "unrequested_damage": None, "major_damage": None}
    result["metric_status"] = metric_states(result, result["rating_status"])
    return result


def score(card, judgment, *, role="unspecified"):
    validate_judgment(card, judgment)
    if judgment.get("judgment_contract_sha256"):
        require(judgment["judgment_contract_sha256"] == judgment_fingerprint(), "Judgment uses another metric registry revision")
    else:
        require(not judgment.get("metric_registry_sha256") or judgment["metric_registry_sha256"] == fingerprint(), "Judgment uses another metric registry revision")
    if judgment["delivery"]["status"] == "invalid":
        return error_result(card, judgment["delivery"], "Invalid delivery; content was not assessed", status="invalid_delivery", role=role)
    semantic = {name: semantic_score(card, judgment, set(DEFINITIONS[name]["kinds"]), DEFINITIONS[name]["temporal_only"]) for name in SEMANTIC}
    values = {name: r["score"] for name, r in judgment["ratings"].items()}
    states = {name: r["status"] for name, r in judgment["ratings"].items()}
    components = DEFINITIONS["aesthetic_mean"]["components"]
    values["aesthetic_mean"] = mean(values[n] for n in components) if all(states[n] == "scored" for n in components) else None
    states["aesthetic_mean"] = "scored" if values["aesthetic_mean"] is not None else "unknown"
    by_id = {r["id"]: r["label"] for r in judgment["items"]}
    mandatory = [by_id[i["id"]] for g in card["groups"] for i in g["items"] if i["mandatory"] or g["kind"] == "preserve_core"]
    failures = []
    if any(v in {"partial", "fail"} for v in mandatory): failures.append("mandatory_semantics")
    major = any(d["severity"] == "major" for d in judgment.get("damages", []))
    if major: failures.append("major_unrequested_damage")
    threshold = SUCCESS["style_threshold"]
    if card["style_required"] and values["style"] is not None and values["style"] < threshold:
        failures.append(f"style_below_{threshold:.1f}")
    unresolved = ("unknown" in mandatory or judgment["delivery"]["status"] == "unknown" or judgment["damage_review"] == "unknown"
                  or (card["style_required"] and values["style"] is None))
    damage = bool(judgment.get("damages"))
    result = {**base_result(card, role), "evaluation_status": "complete", "semantic": semantic, "ratings": values,
        "rating_status": states, "success": "fail" if failures else "unresolved" if unresolved else "pass",
        "failure_reasons": failures, "delivery": judgment["delivery"]["status"],
        "unrequested_damage": damage if damage or judgment["damage_review"] == "complete" else None,
        "major_damage": major if major or judgment["damage_review"] == "complete" else None,
        "judgment_sha256": signature(judgment),
        "evaluation_versions": {"card": card["card_sha256"], "evidence": judgment.get("evidence_sha256"),
             "reference_set": judgment.get("comparison_set_sha256"), "evaluator": judgment.get("evaluator"),
             "raw_metric_contract": judgment.get("metric_registry_version", "legacy-judgment-v1")}}
    result["metric_status"] = metric_states(result, states)
    return result


def flat_metrics(result):
    from .compat import canonical_result
    result = canonical_result(result)
    metrics = dict(result["ratings"])
    metrics.update({n: result.get("automatic", {}).get(n) for n in ("clip_f", "dino_f")})
    for name, part in result["semantic"].items():
        metrics[name] = part["score"]
        for field in ("lower", "upper", "coverage", "complete_rate"):
            metrics[f"{name}_{field}"] = part[field]
    metrics.update(success_confirmed=100.0 if result["success"] == "pass" else 0.0,
                   success_possible=0.0 if result["success"] == "fail" else 100.0,
                   success_unresolved=100.0 if result["success"] == "unresolved" else 0.0,
                   delivery_valid=100.0 if result["delivery"] == "valid" else 0.0)
    for name in ("unrequested_damage", "major_damage"):
        metrics[name] = None if result[name] is None else 100.0 * result[name]
    return metrics
