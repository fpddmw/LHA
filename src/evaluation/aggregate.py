"""Source-clustered macro averages and paired differences with missingness exposed."""
from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .protocol import require, write
from .scoring import flat_metrics
from .reporting import METRICS, VERSION, display, metric_spec, normalized_records
from .registry import snapshot, fingerprint, judgment_fingerprint, scoring_fingerprint, overview, STATE_LABELS, SEMANTIC


def estimate(values, *, repeats=2000, seed=20261029):
    """values are one aggregated observation per source, never individual frames/items."""
    if not values:
        return {"mean": None, "ci95": None, "n_sources": 0}
    center = mean(values)
    if len(values) == 1 or repeats < 2:
        return {"mean": center, "ci95": None, "n_sources": len(values)}
    rng = random.Random(seed)
    boot = sorted(mean(rng.choices(values, k=len(values))) for _ in range(repeats))
    return {"mean": center, "ci95": [boot[int((repeats - 1) * 0.025)], boot[int((repeats - 1) * 0.975)]], "n_sources": len(values)}


def validate_records(records):
    seen, cards, encoders, eligibility = set(), {}, set(), {}
    for row in records:
        require(all(k in row for k in ("method", "seed", "result")), "Record needs method, seed, result")
        r = row["result"]
        if not r.get("legacy_origin"):
            expected = scoring_fingerprint() if r.get("scoring_contract_sha256") else fingerprint()
            require(r.get("scoring_contract_sha256", r.get("metric_registry_sha256", expected)) == expected, "Score uses another metric registry revision")
        require(row.get("evaluation_role", r.get("evaluation_role")) not in {"online_critic", "online_feedback"}, "Online diagnostics cannot enter final reports")
        key = (row["method"], r["task_id"], row["seed"])
        require(key not in seen, f"Duplicate evaluation: {key}")
        seen.add(key)
        require(r["task_id"] not in cards or cards[r["task_id"]] == r["card_sha256"], "Methods/seeds must share the same frozen task card")
        cards[r["task_id"]] = r["card_sha256"]
        for name, status in r["metric_status"].items():
            if status == "legacy_status_unavailable": continue
            require(name not in r.get("applicability", {}) or r["applicability"][name] == (status != "not_applicable"), "Applicability differs from the frozen card declaration")
            k = (r["card_sha256"], name)
            applies = status != "not_applicable"
            require(k not in eligibility or eligibility[k] == applies, "Applicability must be fixed by the shared card")
            eligibility[k] = applies
        automatic = r.get("automatic")
        if automatic:
            from .protocol import number, signature
            require(automatic.get("protocol") == "lha-output-consistency-v1" and automatic.get("scale") == "raw_cosine", "Incompatible automatic metrics")
            require(all(number(automatic.get(n)) and -1.000001 <= automatic[n] <= 1.000001 for n in ("clip_f", "dino_f")), "Invalid cosine score")
            encoders.add(signature({"sample_fps": automatic["sample_fps"], "encoders": automatic["encoders"]}))
    require(len(encoders) <= 1, "Do not pool different encoders/revisions/sampling protocols")


def cells(row):
    from .registry import SEMANTIC
    values = flat_metrics(row["result"])
    result = {}
    for name, value in values.items():
        status = row["result"]["metric_status"][name]
        require(status != "scored" or value is not None, f"Scored metric {name} has no value")
        cell = {"value": value if status == "scored" else None, "status": status}
        if name in SEMANTIC:
            part = row["result"]["semantic"][name]
            cell.update(lower=part["lower"] if part["lower"] is not None else 0.0,
                        upper=part["upper"] if part["upper"] is not None else 1.0)
        result[name] = cell
    return result


def missing_cell(item, metric):
    status = "not_applicable" if item.get("applicability", {}).get(metric) is False else "missing_record"
    result = {"value": None, "status": status}
    if metric in SEMANTIC:
        result.update(lower=0.0, upper=1.0)
    return result


def fold(observations):
    eligible = [c for c in observations if c["status"] != "not_applicable"]
    if not eligible: return {"value": None, "status": "not_applicable"}
    priority = ("missing_output", "invalid_delivery", "evaluation_error", "missing_record", "unknown", "legacy_status_unavailable", "not_measured")
    states = {c["status"] for c in eligible}
    status = next((s for s in priority if s in states), "scored")
    result = {"value": mean(c["value"] for c in eligible) if status == "scored" else None, "status": status}
    if all("lower" in c for c in eligible):
        result.update(lower=mean(c["lower"] for c in eligible), upper=mean(c["upper"] for c in eligible))
    return result


def clustered(observations, *, repeats=2000):
    from .registry import STATES
    tasks = defaultdict(list)
    for source, task, cell in observations:
        tasks[(source, task)].append(cell)
    sources = defaultdict(list)
    for (source, task), entries in tasks.items(): sources[source].append(fold(entries))
    source_values = [fold(entries) for entries in sources.values()]
    applicable = [c for c in source_values if c["status"] != "not_applicable"]
    valid = [c["value"] for c in applicable if c["status"] == "scored"]
    result = {**estimate(valid, repeats=repeats), "total_sources": len(sources), "applicable_sources": len(applicable),
              "not_applicable_sources": len(sources) - len(applicable), "missing_sources": len(applicable) - len(valid),
              "coverage_percent": 100 * len(valid) / len(applicable) if applicable else None,
              "mean_scope": "complete_applicable_sources",
              "observation_counts": {s: sum(c["status"] == s for _, _, c in observations) for s in STATES},
              "source_counts": {s: sum(c["status"] == s for c in source_values) for s in STATES}}
    if applicable and all("lower" in c for c in applicable):
        result.update(population_lower=mean(c["lower"] for c in applicable), population_upper=mean(c["upper"] for c in applicable))
    return result


def summarize(records, *, repeats=2000, include_overall=False, cohort=None):
    records = normalized_records(records)
    validate_records(records)
    panels, planned = defaultdict(list), defaultdict(list)
    lookup_cells = {id(r): cells(r) for r in records}
    for row in records:
        r = row["result"]
        panels[(row["method"], r["split"], r["track"])].append(row)
        if include_overall: panels[(row["method"], r["split"], "all")].append(row)
    for item in cohort or []:
        planned[(item["method"], item["split"], item["track"])].append(item)
        if include_overall: planned[(item["method"], item["split"], "all")].append(item)
    for key in planned: panels[key]
    report = []
    for (method, split, track), panel in sorted(panels.items()):
        plan = planned.get((method, split, track)) or [dict(row["result"], seed=row["seed"]) for row in panel]
        expected = {(r["source_id"], r["task_id"], r["seed"]): r for r in plan}
        observed = {(r["result"]["source_id"], r["result"]["task_id"], r["seed"]): r for r in panel}
        require(set(observed) <= set(expected), "Observed results outside declared cohort")
        summary = {}
        for metric in METRICS:
            entries = [(source, task, lookup_cells[id(observed[key])][metric] if key in observed else missing_cell(item, metric))
                       for key, item in expected.items() for source, task, seed in [key]]
            summary[metric] = clustered(entries, repeats=repeats)
        models = {r.get("renderer") for r in panel + plan if r.get("renderer")}
        report.append({"method": method, "model": next(iter(models)) if len(models) == 1 else None,
            "split": split, "track": track, "original_tracks": sorted({r["track"] for r in plan}),
            "track_task_counts": {t: len({r["task_id"] for r in plan if r["track"] == t}) for t in sorted({r["track"] for r in plan})},
            "task_ids": sorted({r["task_id"] for r in plan}), "source_ids": sorted({r["source_id"] for r in plan}),
            "n_tasks": len({r["task_id"] for r in plan}), "n_records": len(panel), "expected_records": len(expected),
            "missing_records": len(set(expected) - set(observed)), "metrics": summary})
    return report


def paired_difference(records, method_a, method_b, metric, *, repeats=2000, include_overall=False, cohort=None):
    records = normalized_records(records)
    validate_records(records)
    lookup, plans = defaultdict(dict), {}
    for row in records:
        if row["method"] not in {method_a, method_b}: continue
        r = row["result"]
        key = (r["split"], r["track"], r["source_id"], r["task_id"], row["seed"])
        lookup[key][row["method"]] = cells(row)[metric]
    for r in cohort or []:
        if r["method"] in {method_a, method_b}:
            key = (r["split"], r["track"], r["source_id"], r["task_id"], r["seed"])
            lookup[key]; plans[key] = r
    panels = defaultdict(list)
    for key, values in lookup.items():
        split, track, source, task, seed = key
        a, b = (values.get(m, missing_cell(plans.get(key, {}), metric)) for m in (method_a, method_b))
        require((a["status"] == "not_applicable") == (b["status"] == "not_applicable"), "Paired applicability mismatch")
        cell = fold([a, b])
        if cell["status"] == "scored": cell["value"] = a["value"] - b["value"]
        if "lower" in a and "lower" in b: cell.update(lower=a["lower"] - b["upper"], upper=a["upper"] - b["lower"])
        panels[(split, track)].append((source, task, cell))
        if include_overall: panels[(split, "all")].append((source, task, cell))
    return [{"split": split, "track": track, "metric": metric, "difference": f"{method_a} - {method_b}",
             **clustered(entries, repeats=repeats)} for (split, track), entries in sorted(panels.items())]


def export_report(records, destination, *, repeats=2000, include_overall=True, cohort=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    records = normalized_records(records)
    summary = summarize(records, repeats=repeats, include_overall=include_overall, cohort=cohort)
    write(destination / "summary.json", summary)
    specs = {k: metric_spec(k) for p in summary for k in p["metrics"]}
    write(destination / "metadata.json", {"version": VERSION, "metrics": specs,
          "registry": snapshot(), "registry_sha256": fingerprint(), "judgment_contract_sha256": judgment_fingerprint(), "scoring_contract_sha256": scoring_fingerprint(),
          "aggregation": "seed mean within task, equal task mean within source, equal source macro; missing planned observations retained",
          "precision": "JSON/CSV preserve full precision; rating means displayed to one decimal; normalized semantic scores to two",
          "cohort": cohort, "overall": include_overall})
    write(destination / "records.normalized.json", records)
    lines = [f"# 视频编辑评价（{VERSION}）", "", overview(), "", "表中评分均值针对完整的适用源，注明有效/适用/预定源数。语义全体上下界沿相同层次汇总，包括未知及执行缺项；bootstrap 区间仅针对有效源均值。", "", "先在同题 seed 内平均，再同源任务等权，最后源等权。短/长沿原始任务卡，Planner 扩写不改变 track。五项美学先求计算均值；评价器原始判断与计算分保留关联。", ""]
    with (destination / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["method", "model", "split", "track", "metric", "unit", "aggregation", "mean", "display_mean", "ci95_low", "ci95_high", "n_sources", "total_sources", "applicable_sources", "missing_sources", "coverage_percent", "status_counts", "population_lower", "population_upper"])
        for panel in summary:
            lines += [f"## {panel['method']} / {panel['split']} / {panel['track']}", "", f"预定 {panel['n_tasks']} 题；记录 {panel['n_records']}/{panel['expected_records']}；原始轨道 {panel['track_task_counts']}。", "", "| 指标 | 单位 | 有效源分数或均值 | 95% CI | 有效/适用/预定源数 | 状态计数 | 全体适用源证据界限 |", "|---|---|---:|---|---|---|---|"]
            for name, value in panel["metrics"].items():
                spec = specs[name]
                digits = spec["display_decimals"]
                displayed = display(value["mean"], name)
                ci = value["ci95"]
                ci_text = "N/A" if ci is None else f"[{ci[0]:.{digits}f}, {ci[1]:.{digits}f}]"
                counts = {STATE_LABELS[s]: n for s, n in value["observation_counts"].items() if n}
                bounds = f"[{display(value['population_lower'], name)}, {display(value['population_upper'], name)}]" if "population_lower" in value else "—"
                lines.append(f"| {spec['label']} ({name}) | {spec['unit']} | {displayed} | {ci_text} | {value['n_sources']}/{value['applicable_sources']}/{value['total_sources']} | {counts} | {bounds} |")
                writer.writerow([panel["method"], panel["model"], panel["split"], panel["track"], name, spec["unit"], spec["aggregation"],
                                 value["mean"], displayed, "" if ci is None else ci[0], "" if ci is None else ci[1],
                                 value["n_sources"], value["total_sources"], value["applicable_sources"], value["missing_sources"], value["coverage_percent"],
                                 json.dumps(value["observation_counts"], ensure_ascii=False, sort_keys=True), value.get("population_lower"), value.get("population_upper")])
            lines.append("")
    (destination / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary
