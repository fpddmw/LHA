"""Source-clustered macro averages and paired differences with missingness exposed."""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .protocol import require, write
from .scoring import flat_metrics
from .reporting import METRICS, VERSION, display, metric_spec, normalized_records


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
    seen = set()
    cards = {}
    encoders = set()
    scales = set()
    for row in records:
        require(all(k in row for k in ("method", "seed", "result")), "Record needs method, seed, result")
        r = row["result"]
        scales.add(r.get("reporting", {}).get("semantic_score_scale", "legacy_0_100"))
        key = (row["method"], r["task_id"], row["seed"])
        require(key not in seen, f"Duplicate evaluation: {key}")
        seen.add(key)
        task = r["task_id"]
        require(task not in cards or cards[task] == r["card_sha256"], "Methods/seeds must share the same frozen task card")
        cards[task] = r["card_sha256"]
        automatic = r.get("automatic")
        if automatic:
            from .protocol import number, signature
            require(automatic.get("protocol") == "lha-output-consistency-v1" and automatic.get("scale") == "raw_cosine", "Incompatible automatic metrics")
            require(all(number(automatic.get(n)) and -1.000001 <= automatic[n] <= 1.000001 for n in ("clip_f", "dino_f")), "Invalid cosine score")
            encoders.add(signature({"sample_fps": automatic["sample_fps"], "encoders": automatic["encoders"]}))
    require(len(encoders) <= 1, "Do not pool different encoders/revisions/sampling protocols")
    require(len(scales) <= 1, "Normalize mixed semantic scales before aggregation")
    require(scales <= {"legacy_0_100", "unit_interval"}, "Unknown semantic scale")


def summarize(records, *, repeats=2000, include_overall=False, cohort=None):
    validate_records(records)
    panels = defaultdict(list)
    for row in records:
        r = row["result"]
        panels[(row["method"], r["split"], r["track"])].append(row)
        if include_overall:
            panels[(row["method"], r["split"], "all")].append(row)
    planned = defaultdict(list)
    for item in cohort or []:
        planned[(item["method"], item["split"], item["track"])].append(item)
        if include_overall:
            planned[(item["method"], item["split"], "all")].append(item)
    for key in planned:
        panels[key]  # Include predeclared methods even when no result has arrived.
    report = []
    for (method, split, track), panel in sorted(panels.items()):
        plan = planned.get((method, split, track)) or [dict(row["result"], seed=row["seed"]) for row in panel]
        all_sources = {row["source_id"] for row in plan}
        expected = {(r["source_id"], r["task_id"], r["seed"]) for r in plan}
        observed = {(r["result"]["source_id"], r["result"]["task_id"], r["seed"]) for r in panel}
        require(observed <= expected, "Observed results outside declared cohort")
        metrics = sorted({k for row in records for k in flat_metrics(row["result"])} or METRICS)
        summary = {}
        for metric in metrics:
            per_task = defaultdict(list)
            for row in panel:
                value = flat_metrics(row["result"])[metric]
                per_task[(row["result"]["source_id"], row["result"]["task_id"])].append(value)
            for source, task, seed in expected - observed:
                per_task[(source, task)].append(None)
            per_source = defaultdict(list)
            for (source, task), values in per_task.items():
                per_source[source].append(mean(values) if all(x is not None for x in values) else None)
            # A missing seed is not silently removed from the source mean.
            complete = [mean(v) for v in per_source.values() if all(x is not None for x in v)]
            summary[metric] = {**estimate(complete, repeats=repeats),
                               "total_sources": len(all_sources), "missing_sources": len(all_sources) - len(complete)}
        models = {r.get("renderer") for r in panel + plan if r.get("renderer")}
        report.append({"method": method, "model": next(iter(models)) if len(models) == 1 else None,
                       "split": split, "track": track, "original_tracks": sorted({r["track"] for r in plan}),
                       "track_task_counts": {t: len({r["task_id"] for r in plan if r["track"] == t}) for t in sorted({r["track"] for r in plan})},
                       "task_ids": sorted({r["task_id"] for r in plan}), "source_ids": sorted(all_sources),
                       "n_tasks": len({r["task_id"] for r in plan}), "n_records": len(panel), "expected_records": len(expected),
                       "missing_records": len(expected - observed), "metrics": summary})
    return report


def paired_difference(records, method_a, method_b, metric, *, repeats=2000, include_overall=False, cohort=None):
    validate_records(records)
    lookup = defaultdict(dict)
    for r in cohort or []:
        if r["method"] in {method_a, method_b}:
            lookup[(r["split"], r["track"], r["source_id"], r["task_id"], r["seed"])]
    for row in records:
        if row["method"] not in {method_a, method_b}:
            continue
        r = row["result"]
        lookup[(r["split"], r["track"], r["source_id"], r["task_id"], row["seed"])][row["method"]] = flat_metrics(r)[metric]
    tasks = defaultdict(list)
    for (split, track, source, task, seed), values in lookup.items():
        a, b = values.get(method_a), values.get(method_b)
        tasks[(split, track, source, task)].append(None if a is None or b is None else a - b)
    panels = defaultdict(lambda: defaultdict(list))
    for (split, track, source, task), values in tasks.items():
        delta = mean(values) if all(v is not None for v in values) else None
        panels[(split, track)][source].append(delta)
        if include_overall:
            panels[(split, "all")][source].append(delta)
    return [{"split": split, "track": track, "metric": metric, "difference": f"{method_a} - {method_b}",
             **estimate([mean(v) for v in sources.values() if all(x is not None for x in v)], repeats=repeats),
             "total_sources": len(sources), "missing_sources": sum(any(x is None for x in v) for v in sources.values())}
            for (split, track), sources in sorted(panels.items())]


def export_report(records, destination, *, repeats=2000, include_overall=True, cohort=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    records = normalized_records(records)
    summary = summarize(records, repeats=repeats, include_overall=include_overall, cohort=cohort)
    write(destination / "summary.json", summary)
    specs = {k: metric_spec(k) for p in summary for k in p["metrics"]}
    write(destination / "metadata.json", {"version": VERSION, "metrics": specs,
          "aggregation": "seed mean within task, equal task mean within source, equal source macro; missing planned observations retained",
          "precision": "JSON/CSV preserve full precision; rating means displayed to one decimal; normalized semantic scores to two",
          "cohort": cohort, "overall": include_overall})
    write(destination / "records.normalized.json", records)
    lines = ["# 视频编辑评价（展示口径 v2）", "", "语义为 0–1 分（分组加权计算分），完整完成比例、成功比例与覆盖率为 %。VLM 原始评分为 1–4、0.1 步长；下表 VLM 列均为计算均值，显示一位小数。美学计算均值先平均五项原始评分。JSON/CSV 保留完整计算精度。", "", "每题先汇总 seed，同源多题先等权合并，再按源宏平均；预定缺项保留分母。短/长沿原始任务卡，Planner 扩写不改变 track。未知保留界限和覆盖率，分项分别解释。", ""]
    with (destination / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["method", "model", "split", "track", "metric", "unit", "aggregation", "mean", "display_mean", "ci95_low", "ci95_high", "n_sources", "total_sources", "missing_sources"])
        for panel in summary:
            lines += [f"## {panel['method']} / {panel['split']} / {panel['track']}", "", f"预定 {panel['n_tasks']} 题；记录 {panel['n_records']}/{panel['expected_records']}；原始轨道 {panel['track_task_counts']}。", "", "| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |", "|---|---|---:|---|---:|"]
            for name, value in panel["metrics"].items():
                spec = specs[name]
                digits = spec["display_decimals"]
                displayed = display(value["mean"], name)
                ci = value["ci95"]
                ci_text = "N/A" if ci is None else f"[{ci[0]:.{digits}f}, {ci[1]:.{digits}f}]"
                lines.append(f"| {spec['label']} ({name}) | {spec['unit']} | {displayed} | {ci_text} | {value['n_sources']}/{value['total_sources']} |")
                writer.writerow([panel["method"], panel["model"], panel["split"], panel["track"], name, spec["unit"], spec["aggregation"],
                                 value["mean"], displayed, "" if ci is None else ci[0], "" if ci is None else ci[1],
                                 value["n_sources"], value["total_sources"], value["missing_sources"]])
            lines.append("")
    (destination / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary
