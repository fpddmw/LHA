"""Hierarchical fact scores and strict success; never mix aesthetics into semantics."""
from __future__ import annotations

from statistics import mean

from . import PROTOCOL
from .protocol import AESTHETICS, LABELS, RATINGS, validate_judgment


def semantic_score(card, judgment, kinds, temporal_only=False):
    labels = {r["id"]: LABELS[r["label"]] for r in judgment["items"]}
    groups = []
    for group in card["groups"]:
        selected = [i for i in group["items"] if not temporal_only or i["temporal"]]
        if group["kind"] not in kinds or not selected:
            continue
        values = [labels[i["id"]] for i in selected]
        n = len(values)
        groups.append({
            "lower": sum(v or 0 for v in values) / n,
            "upper": sum(1 if v is None else v for v in values) / n,
            "complete_lower": sum(v == 1 for v in values) / n,
            "coverage": sum(v is not None for v in values) / n,
            "items": n, "unknown": values.count(None),
        })
    if not groups:
        return {"score": None, "lower": None, "upper": None, "complete_rate": None,
                "coverage": None, "items": 0, "unknown": 0, "status": "not_applicable"}
    lower = 100 * mean(g["lower"] for g in groups)
    upper = 100 * mean(g["upper"] for g in groups)
    unknown = sum(g["unknown"] for g in groups)
    return {"score": lower if unknown == 0 else None, "lower": lower, "upper": upper,
            "complete_rate": 100 * mean(g["complete_lower"] for g in groups) if unknown == 0 else None,
            "coverage": 100 * mean(g["coverage"] for g in groups),
            "items": sum(g["items"] for g in groups), "unknown": unknown,
            "status": "complete" if unknown == 0 else "unresolved"}


def score(card, judgment):
    validate_judgment(card, judgment)
    semantic = {"edit": semantic_score(card, judgment, {"edit"}),
                "preserve_core": semantic_score(card, judgment, {"preserve_core"}),
                "preserve_detail": semantic_score(card, judgment, {"preserve_detail"}),
                "preserve_time": semantic_score(card, judgment, {"preserve_core", "preserve_detail"}, True)}
    values = {name: r["score"] for name, r in judgment["ratings"].items()}
    aesthetic = [values[name] for name in AESTHETICS]
    values["aesthetic_mean"] = mean(aesthetic) if all(v is not None for v in aesthetic) else None
    by_id = {r["id"]: r["label"] for r in judgment["items"]}
    mandatory = [by_id[i["id"]] for g in card["groups"] for i in g["items"] if i["mandatory"]]
    # All core facts are hard constraints even if an annotation accidentally marked one optional.
    mandatory += [by_id[i["id"]] for g in card["groups"] if g["kind"] == "preserve_core" for i in g["items"]]
    failures = []
    if judgment["delivery"]["status"] == "invalid":
        failures.append("invalid_delivery")
    if any(v in {"partial", "fail"} for v in mandatory):
        failures.append("mandatory_semantics")
    major = any(d["severity"] == "major" for d in judgment.get("damages", []))
    if major:
        failures.append("major_unrequested_damage")
    if card["style_required"] and values["style"] is not None and values["style"] < 3.0:
        failures.append("style_below_3.0")
    unresolved = ("unknown" in mandatory or judgment["delivery"]["status"] == "unknown"
                  or judgment["damage_review"] == "unknown"
                  or (card["style_required"] and values["style"] is None))
    success = "fail" if failures else "unresolved" if unresolved else "pass"
    damage = bool(judgment.get("damages"))
    return {"protocol": PROTOCOL, "card_sha256": card["card_sha256"], "task_id": card["task_id"], "source_id": card["source_id"],
            "track": card["track"], "split": card["split"], "style_family": card["style_family"],
            "creativity": card["creativity"], "semantic": semantic, "ratings": values,
            "success": success, "failure_reasons": failures, "delivery": judgment["delivery"]["status"],
            "unrequested_damage": damage if damage or judgment["damage_review"] == "complete" else None,
            "major_damage": major if major or judgment["damage_review"] == "complete" else None}


def flat_metrics(result):
    metrics = dict(result["ratings"])
    for name in ("clip_f", "dino_f"):
        metrics[name] = result.get("automatic", {}).get(name)
    for name, part in result["semantic"].items():
        metrics[name] = part["score"]
        for field in ("lower", "upper", "coverage", "complete_rate"):
            metrics[f"{name}_{field}"] = part[field]
    # Confirmed success is a lower bound when there are unresolved tasks.
    metrics.update(success_confirmed=100.0 if result["success"] == "pass" else 0.0,
                   success_possible=0.0 if result["success"] == "fail" else 100.0,
                   success_unresolved=100.0 if result["success"] == "unresolved" else 0.0,
                   delivery_valid=100.0 if result["delivery"] == "valid" else 0.0)
    for name in ("unrequested_damage", "major_damage"):
        metrics[name] = None if result[name] is None else 100.0 * result[name]
    return metrics
