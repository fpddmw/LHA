"""Schemas and validation. Core evaluation has no third-party dependencies."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from . import PROTOCOL

from .registry import AESTHETICS, LABELS, RATINGS, RATING_SCALE, RATING_STEP, applicable
KINDS = ("edit", "preserve_core", "preserve_detail")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def items(card):
    return {item["id"]: (group, item) for group in card["groups"] for item in group["items"]}


def validate_card(card, *, frozen=True):
    require(card.get("protocol") == PROTOCOL, "Unsupported card protocol")
    for key in ("task_id", "source_id", "source_video", "source_sha256", "requirement", "style_family"):
        require(isinstance(card.get(key), str) and card[key].strip(), f"Missing card {key}")
    require(len(card["source_sha256"]) == 64, "source_sha256 must be SHA-256")
    require(card.get("track") in {"short", "long"}, "track must be short or long")
    require(card.get("split") in {"main", "fewshot", "development"}, "Invalid split")
    require(card.get("creativity") in {"open", "bounded", "none"}, "Invalid creativity scope")
    require(isinstance(card.get("allowed_changes"), list), "allowed_changes must be explicit")
    require(isinstance(card.get("style_required"), bool), "style_required must be boolean")
    require(number(card.get("duration_seconds")) and card["duration_seconds"] > 0, "Positive expected duration required")
    require(number(card.get("source_start_seconds", 0)) and card.get("source_start_seconds", 0) >= 0, "Invalid source start")
    require(card.get("status") in {"draft", "frozen"}, "Card status must be draft/frozen")
    if frozen:
        require(card["status"] == "frozen" and bool(card.get("reviewed_by")), "Review and freeze card before scoring")
        require(card.get("card_sha256") == signature({k: v for k, v in card.items() if k != "card_sha256"}), "Frozen card changed")
    seen = set()
    groups = card.get("groups", [])
    require(groups and any(g.get("kind") == "edit" for g in groups), "Card needs edit groups")
    require(any(g.get("kind") == "preserve_core" for g in groups), "Card needs source-specific core preservation")
    for group in groups:
        require(group.get("kind") in KINDS, "Invalid group kind")
        require(group.get("id") and group["id"] not in seen, "Duplicate/missing group id")
        seen.add(group["id"])
        require(group.get("items"), "Empty group")
        for item in group["items"]:
            require(item.get("id") and item["id"] not in seen, "Duplicate/missing item id")
            seen.add(item["id"])
            require(bool(item.get("text")), "Empty item")
            require(isinstance(item.get("mandatory"), bool), "mandatory must be decided before generation")
            require(item.get("evidence") in {"frames", "sequence"}, "Evidence must be frames/sequence")
            require(isinstance(item.get("temporal"), bool), "temporal must be explicit")
            require(bool(item.get("partial_rule")), "Define partial or say not allowed")
            if "interval_seconds" in item:
                interval = item["interval_seconds"]
                require(isinstance(interval, list) and len(interval) == 2 and all(number(v) for v in interval)
                        and 0 <= interval[0] < interval[1] <= card["duration_seconds"], "Invalid item evidence interval")
    return card


def freeze(card, reviewer):
    require(bool(reviewer.strip()), "Reviewer identity required")
    card = {k: v for k, v in card.items() if k != "card_sha256"}
    card.update(status="frozen", reviewed_by=reviewer)
    validate_card(card, frozen=False)
    card["card_sha256"] = signature(card)
    return card


def validate_rating(rating, name):
    require(isinstance(rating, dict), f"Missing rating {name}")
    require(rating.get("status") in {"scored", "unknown", "not_applicable"}, f"Invalid {name} status")
    require(bool(rating.get("evidence")), f"{name} needs evidence or reason")
    value = rating.get("score")
    if rating["status"] == "scored":
        require(number(value) and RATING_SCALE[0] <= value <= RATING_SCALE[1], f"{name} outside {RATING_SCALE}")
        require(abs(value / RATING_STEP - round(value / RATING_STEP)) < 1e-8, f"{name} must use {RATING_STEP} increments")
    else:
        require(value is None, f"Unscored {name} must be null")


def validate_judgment(card, judgment):
    validate_card(card)
    require(judgment.get("protocol") == PROTOCOL, "Judgment protocol mismatch")
    require(judgment.get("card_sha256") == card["card_sha256"], "Judgment/card signature mismatch")
    delivery = judgment.get("delivery", {})
    require(delivery.get("status") in {"valid", "invalid", "unknown"}, "Invalid delivery status")
    require(bool(delivery.get("reason")), "Delivery evidence required")
    expected = items(card)
    rows = judgment.get("items", [])
    require(len(rows) == len(expected) and {r.get("id") for r in rows} == set(expected), "Every item must occur exactly once")
    for row in rows:
        require(row.get("label") in LABELS, "Invalid fact label")
        require(bool(row.get("evidence")), "Fact needs evidence")
        require(row.get("evidence_kind") in {"frames", "sequence", "none"}, "Invalid evidence kind")
        times = row.get("times_seconds", [])
        require(isinstance(times, list) and all(number(t) and 0 <= t <= card["duration_seconds"] + 0.1 for t in times), "Invalid evidence timestamps")
        if row["label"] != "unknown":
            require(times and row["evidence_kind"] != "none", "Known fact needs timestamped visual evidence")
            if expected[row["id"]][1]["evidence"] == "sequence":
                require(row["evidence_kind"] == "sequence", "Sparse frames cannot establish a sequence claim")
            if row["label"] == "partial":
                require(expected[row["id"]][1]["partial_rule"] != "not allowed", "Partial forbidden for this item")
    require(set(judgment.get("ratings", {})) == set(RATINGS), "All rating fields required")
    for name in RATINGS:
        rating = judgment["ratings"][name]
        validate_rating(rating, name)
        na = not applicable(name, card)
        require((rating["status"] == "not_applicable") == na, f"Incorrect applicability for {name}")
    originality = judgment["ratings"]["relative_originality"]
    if originality["status"] == "scored":
        require(bool(judgment.get("comparison_set_sha256")), "Originality needs a frozen comparison set")
    require(judgment.get("damage_review") in {"complete", "unknown"}, "Damage review status required")
    for damage in judgment.get("damages", []):
        require(damage.get("severity") in {"minor", "major"} and bool(damage.get("evidence")), "Invalid damage")
        linked = damage.get("related_item_ids")
        require(isinstance(linked, list) and set(linked).issubset(expected), "Damage needs valid related_item_ids (empty for unlisted issues)")
        if damage["severity"] == "major" and linked:
            require(any(expected[i][0]["kind"] == "preserve_core" or expected[i][1]["mandatory"] for i in linked), "Optional-detail damage cannot become a major failure")
    return judgment
