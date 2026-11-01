"""Multi-arm evidence reports, operational health and reviewed rollback suggestions."""
from collections import Counter
from pathlib import Path
from statistics import mean
from .common import load, sha
from .ledger import digest
from .rsi_data import sealed, verify_seal
from .rsi_validation import verify_manifest


def records(manifest, paths):
    rows, seen = [], set()
    tasks = {t["id"] for t in manifest["tasks"]}
    for path in paths:
        row = verify_seal(load(path))
        key = row["task"], row["arm"]
        if key in seen or row["task"] not in tasks or row["manifest_sha256"] != manifest["sha256"] or row["protocol_sha256"] != manifest["protocol_sha256"]:
            raise ValueError("Duplicate, foreign or changed experiment receipt")
        if sha(Path(row["run"]) / "state.json") != row["state_sha256"]:
            raise ValueError("Reported run changed")
        for score in row["candidates"]:
            if sha(score["raw"]) != score["raw_sha256"]:
                raise ValueError("Reported independent score changed")
        seen.add(key)
        rows.append(row)
    return rows


def report(manifest_path, paths, output, *, arms=("direct", "singlepass", "best-of-3", "base", "candidate")):
    manifest = verify_manifest(manifest_path)
    rows = records(manifest, paths)
    tasks = {t["id"]: t for t in manifest["tasks"]}
    panels = []
    metrics = ("success", "core", "utility", "selection_regret", "non_improving_generations", "success_at_budget",
               "delivered_success", "selected_utility", "candidate_set_success", "major_damage")
    for track in sorted({"all"} | {t.get("track", "unspecified") for t in tasks.values()}):
        planned = {k for k, t in tasks.items() if track == "all" or t.get("track", "unspecified") == track}
        for arm in arms:
            found = [r for r in rows if r["arm"] == arm and r["task"] in planned]
            values = {}
            for metric in metrics:
                known = [r for r in found if (r.get("metrics") or {}).get(metric) is not None]
                groups = {}
                for r in known:
                    source = tasks[r["task"]].get("source_group", r["source_sha256"])
                    groups.setdefault(source, []).append(r["metrics"][metric])
                values[metric] = {"source_macro_mean": mean(mean(v) for v in groups.values()) if groups else None,
                                  "planned": len(planned), "received": len(found), "valid": len(known),
                                  "unknown": len(found)-len(known), "known_sources": len(groups)}
            deltas = [r["metrics"]["utility"] - r["first_candidate_metrics"]["utility"] for r in found
                      if (r.get("metrics") or {}).get("utility") is not None and (r.get("first_candidate_metrics") or {}).get("utility") is not None]
            costs = {k: {"sum_known": sum(r["cost"][k] for r in found if r["cost"].get(k) is not None),
                         "known": sum(r["cost"].get(k) is not None for r in found), "received": len(found)}
                     for k in ("generation_requests", "successful_outputs", "new_generation_requests", "new_generation_seconds", "planner_calls", "critic_model_calls")}
            components = {}
            selected_scores = []
            for row in found:
                chosen = next((c for c in row["candidates"] if c["id"] == row["selected"]), None)
                selected_scores.append(load(chosen["raw"]).get("score", {}) if chosen else {})
            names = {k for score in selected_scores for k in score.get("semantic", {})}
            for name in sorted(names):
                parts = [s.get("semantic", {}).get(name, {}) for s in selected_scores]
                known = [p["score"] for p in parts if p.get("score") is not None]
                na = sum(p.get("status") == "not_applicable" for p in parts)
                specified = sum(p.get("status") is not None for p in parts)
                components[name] = {"mean": mean(known) if known else None, "planned": len(planned), "received": len(parts),
                                    "applicable": specified-na, "not_applicable": na, "unspecified_applicability": len(parts)-specified,
                                    "valid": len(known), "unknown": specified-na-len(known)}
            panels.append({"track": track, "arm": arm, "metrics": values, "cost": costs,
                           "common_selector": {metric: {"mean": mean(v) if v else None, "valid": len(v), "received": len(found)}
                               for metric in ("success", "core", "utility")
                               for v in [[r["common_selection_metrics"][metric] for r in found if (r.get("common_selection_metrics") or {}).get(metric) is not None]]},
                           "selected_visual_components": {name: {"mean": mean(v) if v else None, "valid": len(v), "received": len(found)}
                               for name in sorted({k for s in selected_scores for k in s.get("ratings", {})})
                               for v in [[s["ratings"][name] for s in selected_scores if s.get("ratings", {}).get(name) is not None]]},
                           "selected_semantic_components": components,
                           "selected_minus_first_utility": {"mean": mean(deltas) if deltas else None, "valid": len(deltas), "improved": sum(d > 0 for d in deltas)},
                           "missing_tasks": sorted(planned-{r["task"] for r in found})})
    index = {(r["task"], r["arm"]): r for r in rows}
    paired = []
    for task in tasks:
        a, b = index.get((task, "base")), index.get((task, "candidate"))
        if not a or not b:
            continue
        paired.append({"task": task, "track": tasks[task].get("track"), "deltas": {
            k: b["metrics"][k]-a["metrics"][k] if (a.get("metrics") or {}).get(k) is not None and (b.get("metrics") or {}).get(k) is not None else None for k in metrics}})
    body = {"schema": "lha-rsi-experiment-report-v1", "manifest_sha256": manifest["sha256"], "split": manifest.get("split", "V"),
            "cycle_sha256":(manifest.get("cycle") or {}).get("sha256"),
            "panels": panels, "paired_experience_differences": paired,
            "curves": [{"task": r["task"], "arm": r["arm"], "best_so_far": (r.get("metrics") or {}).get("best_so_far_bounds")} for r in rows],
            "receipts": [{"path": str(Path(p).resolve()), "sha256": sha(p)} for p in paths],
            "scope": "All declared arms; missing and unknown evidence retained. Paired base/candidate means experience-version comparison, not an assumed knowledge/no-knowledge ablation."}
    return sealed(output, {**body, "sha256": digest(body)})


def health(runs, output, *, thresholds=None):
    thresholds = thresholds or {}
    if not set(thresholds) <= {"min_prediction_known_rate", "min_declared_prediction_known_rate", "min_critic_completion_rate", "max_unknown_rate", "max_context_chars"}:
        raise ValueError("Unsupported health threshold")
    counts = Counter(); calls = []; lengths = []; prediction_routes = {}
    for run in map(Path, runs):
        state = load(run / "state.json"); counts["runs"] += 1
        counts["requirements_defined"] += bool(state.get("requirements"))
        from .ledger import build
        memory = build(state)
        for a in memory.get("attempts", []):
            counts["attempts"] += 1
            counts["intent_complete"] += all(a["intent"].get(k) for k in ("targets", "change", "expect"))
            known = a["prediction"]["outcome"] in {"hit", "partial", "miss"}
            counts["prediction_known"] += known
            declared = a["prediction"].get("basis") == "planner_declared"
            counts["declared_predictions"] += declared
            counts["declared_prediction_known"] += declared and known
            counts["derived_checks"] += not declared
            route = "source" if a["input"] == "source" else "candidate"
            bucket = prediction_routes.setdefault(route, {"known": 0, "planned": 0})
            bucket["known"] += known; bucket["planned"] += 1
        for c in memory.get("candidates", {}).values():
            counts["verdicts"] += len(c["verdicts"])
            counts["unknown_verdicts"] += sum(v == "unknown" for v in c["verdicts"].values())
        for identity, job in state.get("jobs", {}).items():
            if job["kind"] != "critique":
                continue
            counts["critic_jobs"] += 1
            path = run / "jobs" / identity / "active-critic/state.json"
            if path.exists():
                critic = load(path)
                counts["critic_complete"] += critic["status"] == "complete"
                calls.append(critic["attempts"])
        for path in (run / "calls").glob("*/input.json"):
            value = load(path)
            lengths.append(len(value.get("system_prompt", "")) + len(value.get("user_text", "")))
    ratio = lambda a, b: counts[a]/counts[b] if counts[b] else None
    measures = {"prediction_known_rate": ratio("prediction_known", "attempts"), "critic_completion_rate": ratio("critic_complete", "critic_jobs"),
                "declared_prediction_known_rate": ratio("declared_prediction_known", "declared_predictions"),
                "unknown_rate": ratio("unknown_verdicts", "verdicts"), "max_context_chars": max(lengths, default=0),
                "mean_critic_calls": mean(calls) if calls else None}
    alerts = []
    for key, limit in thresholds.items():
        metric = key[4:] if key.startswith(("min_", "max_")) and key != "max_context_chars" else key
        value = measures[metric]
        if value is None or (value < limit if key.startswith("min_") else value > limit):
            alerts.append({"measure": metric, "value": value, "threshold": limit})
    body = {"schema": "lha-rsi-health-v1", "counts": dict(counts), "measures": measures, "prediction_routes": prediction_routes,
            "alerts": alerts, "status": "needs_review" if alerts else "observed", "thresholds": thresholds,
            "scope": "Operational diagnostics; targets do not authorize replacing unknown judgments or changing model reasoning."}
    return sealed(output, {**body, "sha256": digest(body)})


def canary(report_path, output, *, max_core_drop, max_success_drop, minimum_pairs, journal=None):
    report = verify_seal(load(report_path))
    if report["split"] != "D" or minimum_pairs < 1 or min(max_core_drop, max_success_drop) < 0:
        raise ValueError("Canary uses development pairs and declared nonnegative tolerances")
    pairs = report["paired_experience_differences"]
    known = [r for r in pairs if all(r["deltas"][k] is not None for k in ("core", "success"))]
    regression = len(known) >= minimum_pairs and (mean(r["deltas"]["core"] for r in known) < -max_core_drop or mean(r["deltas"]["success"] for r in known) < -max_success_drop)
    body = {"schema": "lha-rsi-canary-v1", "report_sha256": report["sha256"], "known_pairs": len(known),
            "thresholds": {"max_core_drop": max_core_drop, "max_success_drop": max_success_drop, "minimum_pairs": minimum_pairs},
            "status": "propose_reviewed_rollback" if regression else "insufficient_evidence" if len(known) < minimum_pairs else "no_threshold_regression",
            "journal": journal, "automatic_publication": False}
    return sealed(output, {**body, "sha256": digest(body)})


def drift(reference_path, current_path, output, *, max_mean_absolute_difference, minimum_pairs):
    a, b = verify_seal(load(reference_path)), verify_seal(load(current_path))
    if a["profile_sha256"] != b["profile_sha256"]:
        raise ValueError("Judge profile changed; use calibration rather than within-profile drift")
    if minimum_pairs < 1 or max_mean_absolute_difference < 0:
        raise ValueError("Declare an anchor sample minimum and nonnegative drift tolerance")
    old = {r["output_sha256"]: r for r in a["rows"]}
    values = []
    for row in b["rows"]:
        prior = old.get(row["output_sha256"])
        if prior is None:
            continue
        for r in (row, prior):
            if sha(r["score"]["raw"]) != r["score"]["raw_sha256"]:
                raise ValueError("Anchor judgment changed")
        x, y = load(prior["score"]["raw"])["score"], load(row["score"]["raw"])["score"]
        for metric in x["semantic"].keys() & y["semantic"].keys():
            left, right = x["semantic"][metric]["score"], y["semantic"][metric]["score"]
            values.append({"output_sha256": row["output_sha256"], "metric": metric,
                           "absolute_difference": abs(left-right) if left is not None and right is not None else None})
    known = [v["absolute_difference"] for v in values if v["absolute_difference"] is not None]
    n = len({v["output_sha256"] for v in values if v["absolute_difference"] is not None})
    average = mean(known) if known else None
    body = {"schema": "lha-rsi-drift-v1", "reference_sha256": a["sha256"], "current_sha256": b["sha256"], "pairs": values,
            "known_videos": n, "mean_absolute_difference": average,
            "thresholds": {"max_mean_absolute_difference": max_mean_absolute_difference, "minimum_pairs": minimum_pairs},
            "status": "insufficient_evidence" if n < minimum_pairs else "needs_review" if average > max_mean_absolute_difference else "within_declared_tolerance",
            "scope": "Stability on fixed saved videos; agreement does not establish correctness. No automatic protocol change."}
    return sealed(output, {**body, "sha256": digest(body)})
