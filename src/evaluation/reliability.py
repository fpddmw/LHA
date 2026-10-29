"""Transparent rater agreement and preference summaries; unknown is not a tie."""
from statistics import mean

from .protocol import number, require


def agreement(pairs):
    require(len({p["case_id"] for p in pairs}) == len(pairs), "Agreement input needs unique case ids per metric")
    usable = []
    for p in pairs:
        if p.get("a") is None or p.get("b") is None:
            continue
        require(number(p["a"]) and number(p["b"]), "Agreement values must be numeric or null")
        usable.append((p["a"], p["b"]))
    if not usable:
        return {"n": 0, "total": len(pairs), "mean_absolute_difference": None, "signed_bias_a_minus_b": None, "within_0_5_rate": None}
    return {"n": len(usable), "total": len(pairs),
            "mean_absolute_difference": mean(abs(a - b) for a, b in usable),
            "signed_bias_a_minus_b": mean(a - b for a, b in usable),
            "within_0_5_rate": 100 * mean(abs(a - b) <= .5 for a, b in usable)}


def preferences(rows):
    result = {}
    for dimension in ("semantics", "design", "creativity"):
        values = [r["result"][dimension]["verdict"] for r in rows]
        require(all(v in {"A", "B", "tie", "unknown", "not_applicable"} for v in values), "Invalid preference verdict")
        n = sum(v in {"A", "B", "tie"} for v in values)
        result[dimension] = {"a_wins": values.count("A"), "b_wins": values.count("B"), "ties": values.count("tie"),
                             "unknown": values.count("unknown"), "not_applicable": values.count("not_applicable"),
                             "a_preference_percent": 100 * (values.count("A") + .5 * values.count("tie")) / n if n else None,
                             "order_disagreements": sum(r["result"][dimension]["order_disagreement"] for r in rows)}
    return result
