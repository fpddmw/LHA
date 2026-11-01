"""Deterministic development counts with explicit denominators and missing evidence."""
from collections import Counter, defaultdict
from .ledger import VALUES


def independent(attempt):
    rows = attempt.get("independent_evaluations", [])
    if len(rows) != 1:
        return {}  # Multiple protocols are not silently averaged or selected.
    raw = rows[0]["result"]
    return raw.get("score", raw.get("result", raw))


def rate(values):
    known = [v for v in values if v is not None]
    return {"numerator": sum(known), "known": len(known), "planned": len(values), "unknown": len(values)-len(known),
            "rate": sum(known)/len(known) if known else None}


def aggregate(records, *, alignment=None):
    routes, repairs, first, predictions, damage_agreement = defaultdict(list), defaultdict(list), [], [], []
    evidence_ids, first_ids, aligned_pairs = defaultdict(list), [], []
    prediction_bases, categorical, declared_cards = defaultdict(list), [], defaultdict(list)
    if alignment and (not alignment.get("reviewed_by") or not alignment.get("reason") or not isinstance(alignment.get("mappings"), list)):
        raise ValueError("Criterion alignment needs a reviewer, reason and explicit version-bound mappings")
    for record in records:
        attempts = record.get("attempts", [])
        by_id = {a["candidate"]: a for a in attempts if a.get("candidate")}
        memory = record.get("task_memory") or {}
        memory_attempts = {a["job"]: a for a in memory.get("attempts", [])}
        for i, a in enumerate(attempts):
            score = independent(a)
            success = score.get("success")
            success = success if type(success) is bool else True if success == "pass" else False if success == "fail" else None
            route = "source" if a["input"] == "source" else "candidate"
            route_key = str(record.get("renderer", "unspecified")) + "/" + route
            routes[route_key].append(success)
            evidence_ids[route_key].append(record["id"] + "/" + a["job"])
            if i == 0:
                first.append(success)
                first_ids.append(record["id"] + "/" + a["job"])
            before_id = a.get("baseline", a.get("intent", {}).get("baseline") if a.get("intent") else None) or a["input"]
            def verdicts(attempt):
                reviews = list(attempt.get("evaluations", {}).values())
                outcome = reviews[-1].get("outcome", {}) if reviews else {}
                return outcome.get("requirements_sha256"), {v["id"]: v["verdict"] for v in outcome.get("requirement_verdicts", [])}
            before_version, before = verdicts(by_id.get(before_id, {}))
            after_version, after = verdicts(a)
            if not before_version or before_version != after_version:
                before = {}  # Identical IDs are not enough when the requirement text changed.
            intent = a.get("intent") or {}
            for target in intent.get("targets", []):
                types = intent.get("failure_types", intent.get("failure_type", {})).get(target, ["unclassified"])
                types = [types] if isinstance(types, str) else types
                old, new = VALUES.get(before.get(target)), VALUES.get(after.get(target))
                for category in types:
                    repairs[category].append(None if old is None or new is None else new > old)
            predictions.append(memory_attempts.get(a["job"], {}).get("prediction", {}).get("outcome", "historically_missing"))
            attempt_memory = memory_attempts.get(a["job"], {})
            basis = attempt_memory.get("prediction", {}).get("basis", "historically_missing")
            prediction_bases[basis.split(";")[0]].append(predictions[-1])
            categorical.extend(attempt_memory.get("categorical_prediction", {}).get("results", {}).values())
            for card in intent.get("cards", []):
                declared_cards[card].append(success)
            reviews = list(a.get("evaluations", {}).values())
            online = reviews[-1].get("outcome", {}).get("major_damage") if reviews else None
            final = score.get("major_damage")
            damage_agreement.append(online == final if type(online) is bool and type(final) is bool else None)
            if alignment and reviews and len(a.get("independent_evaluations", [])) == 1:
                outcome = reviews[-1].get("outcome", {})
                judged = a["independent_evaluations"][0].get("judgment", {})
                for mapping in alignment["mappings"]:
                    if mapping.get("requirements_sha256") != outcome.get("requirements_sha256") or mapping.get("card_sha256") != judged.get("card_sha256"):
                        continue
                    if not mapping.get("requirements_sha256") or not mapping.get("card_sha256"):
                        raise ValueError("Align exact requirement and independent-card versions")
                    left = {r["id"]:r["verdict"] for r in outcome.get("requirement_verdicts", [])}
                    right = {r["id"]:r.get("label", r.get("verdict")) for r in judged.get("items", [])}
                    for pair in mapping["pairs"]:
                        l, r = left.get(pair["requirement_id"]), right.get(pair["item_id"])
                        aligned_pairs.append({"run":record["id"], "job":a["job"], **pair, "online":l, "independent":r,
                                              "agreement": l == r if l in {"pass","partial","fail"} and r in {"pass","partial","fail"} else None})
    known_predictions = [p for p in predictions if p in {"hit", "partial", "miss"}]
    return {"runs": len(records), "sources": len({r["source_sha256"] for r in records}),
            "first_attempt_success": {**rate(first), "evidence": first_ids},
            "route_success": {k: {**rate(v), "evidence": evidence_ids[k]} for k, v in routes.items()},
            "repair_improvement_by_hypothesis": {k: rate(v) for k, v in repairs.items()},
            "predictions": {"counts": dict(Counter(predictions)), "strict_hit_rate": rate([p == "hit" for p in known_predictions]),
                            "scope": "Legacy pooled accounting only; use by_basis for interpretation",
                            "by_basis": {k: {"counts": dict(Counter(v)), "hit_rate": rate([x == "hit" if x in {"hit", "partial", "miss"} else None for x in v])} for k,v in prediction_bases.items()},
                            "categorical_accuracy": rate([v == "hit" if v != "unknown" else None for v in categorical]),
                            "determinable": len(known_predictions), "planned": len(predictions)},
            "declared_skill_use": {k: {**rate(v), "scope": "Declared use associated with observed outcomes; not causal attribution"} for k,v in declared_cards.items()},
            "critic_independent_agreement": {"major_damage": rate(damage_agreement),
                "itemwise": {"status": "aligned" if alignment else "unavailable_without_reviewed_criterion_alignment",
                             **rate([p["agreement"] for p in aligned_pairs]), "pairs": aligned_pairs}},
            "scope": "Route outcomes are observational run/attempt counts. Missing intent is not reconstructed. Rates retain denominators; repeated sources are not independent trials. Source-clustered quality comparisons are computed separately from paired experiment receipts."}
