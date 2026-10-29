"""Compare candidates to the previous accepted version, always using the same source card."""
from __future__ import annotations

from .protocol import LABELS, items, require
from .scoring import flat_metrics, score


def transition(card, before, after):
    score(card, before)
    score(card, after)
    old = {r["id"]: r["label"] for r in before["items"]}
    new = {r["id"]: r["label"] for r in after["items"]}
    output = {}
    for name, kind, eligible, event in (
        ("repair", {"edit"}, {"partial", "fail"}, {"pass"}),
        ("new_damage", {"preserve_core", "preserve_detail"}, {"pass"}, {"partial", "fail"}),
        ("regression", {"edit"}, {"pass"}, {"partial", "fail"}),
    ):
        ids = [i for i, (g, _) in items(card).items() if g["kind"] in kind and old[i] in eligible]
        events = [i for i in ids if new[i] in event]
        unknown = [i for i in ids if new[i] == "unknown"]
        output[name] = {"events": events, "eligible": ids, "unknown": unknown,
                        "rate": 100 * len(events) / len(ids) if ids and not unknown else None,
                        "lower": 100 * len(events) / len(ids) if ids else None,
                        "upper": 100 * (len(events) + len(unknown)) / len(ids) if ids else None}
    return output


def analyze(card, rounds):
    """Round 1 is the shared incumbent. Every later candidate declares its input and decision."""
    require(rounds and rounds[0].get("accepted") is True, "First round must establish incumbent")
    lookup, transitions, curve = {}, [], []
    incumbent = rounds[0]["id"]
    first = score(card, rounds[0]["judgment"])
    cost = 0.0
    accepts = errors = unknown_accepts = 0
    for index, row in enumerate(rounds):
        require(row.get("id") and row["id"] not in lookup, "Duplicate round id")
        current = score(card, row["judgment"])
        require(row.get("final_judge_independent") is True, "Loop analysis requires independent final judgments")
        require(isinstance(row.get("accepted"), bool), "Acceptance decision must be boolean")
        require(row.get("input_version") in {"source", *lookup.keys()}, "Unknown actual input version")
        require(row.get("prompt") and row.get("decision_reason"), "Log prompt and acceptance reason")
        seconds = row.get("generation_seconds")
        require(isinstance(seconds, (int, float)) and seconds >= 0, "Actual generation cost required")
        cost += seconds
        if index:
            require(row.get("previous_accepted") == incumbent, "Incorrect previous accepted version")
            diff = transition(card, lookup[incumbent]["judgment"], row["judgment"])
            old = {r["id"]: LABELS[r["label"]] for r in lookup[incumbent]["judgment"]["items"]}
            new = {r["id"]: LABELS[r["label"]] for r in row["judgment"]["items"]}
            decreases = [i for i in old if old[i] is not None and new[i] is not None and new[i] < old[i]]
            improves = any(old[i] is not None and new[i] is not None and new[i] > old[i] for i in old)
            previous = score(card, lookup[incumbent]["judgment"])
            improves |= any(previous["ratings"][k] is not None and current["ratings"][k] is not None
                            and current["ratings"][k] > previous["ratings"][k] for k in current["ratings"])
            uncertain = any(v is None for v in new.values()) or current["major_damage"] is None
            new_major = current["major_damage"] is True and previous["major_damage"] is False
            uncertain |= current["major_damage"] is True and previous["major_damage"] is None
            bad = bool(decreases) or new_major or current["delivery"] == "invalid" or (not improves and not uncertain)
            if row["accepted"]:
                accepts += 1
                errors += int(bad)
                unknown_accepts += int(uncertain and not bad)
            transitions.append({"id": row["id"], "previous_accepted": incumbent, "accepted": row["accepted"],
                                "false_accept": bad if row["accepted"] and (bad or not uncertain) else None,
                                "fact_decreases": decreases, "observed_improvement": improves, **diff})
            if row["accepted"]:
                incumbent = row["id"]
        lookup[row["id"]] = row
        curve.append({"generation_count": index + 1, "generation_seconds": cost, "accepted_version": incumbent,
                      "metrics": flat_metrics(score(card, lookup[incumbent]["judgment"]))})
    final = score(card, lookup[incumbent]["judgment"])
    a, b = flat_metrics(first), flat_metrics(final)
    return {"acceptance_policy": "no_fact_decrease_no_new_major_damage_valid_delivery_and_observed_improvement",
            "first": first, "final": final, "final_version": incumbent, "transitions": transitions, "accepted_curve": curve,
            "net_change": {k: b[k] - a[k] if a[k] is not None and b[k] is not None else None for k in a},
            "generation_count": len(rounds), "generation_seconds": cost, "accepted_candidates": accepts,
            "false_accept_rate": 100 * errors / accepts if accepts and not unknown_accepts else None,
            "false_accept_lower": 100 * errors / accepts if accepts else None,
            "false_accept_upper": 100 * (errors + unknown_accepts) / accepts if accepts else None,
            "unresolved_accepts": unknown_accepts}
