"""Source-clustered macro averages and paired differences with missingness exposed."""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .protocol import require, write
from .scoring import flat_metrics


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
    for row in records:
        require(all(k in row for k in ("method", "seed", "result")), "Record needs method, seed, result")
        r = row["result"]
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


def summarize(records, *, repeats=2000):
    validate_records(records)
    panels = defaultdict(list)
    for row in records:
        r = row["result"]
        panels[(row["method"], r["split"], r["track"])].append(row)
    report = []
    for (method, split, track), panel in sorted(panels.items()):
        all_sources = {row["result"]["source_id"] for row in panel}
        metrics = sorted({k for row in panel for k in flat_metrics(row["result"])})
        summary = {}
        for metric in metrics:
            per_source = defaultdict(list)
            for row in panel:
                value = flat_metrics(row["result"])[metric]
                per_source[row["result"]["source_id"]].append(value)
            # A missing seed is not silently removed from the source mean.
            complete = [mean(v) for v in per_source.values() if all(x is not None for x in v)]
            summary[metric] = {**estimate(complete, repeats=repeats),
                               "total_sources": len(all_sources), "missing_sources": len(all_sources) - len(complete)}
        report.append({"method": method, "split": split, "track": track, "metrics": summary})
    return report


def paired_difference(records, method_a, method_b, metric, *, repeats=2000):
    validate_records(records)
    lookup = defaultdict(dict)
    for row in records:
        if row["method"] not in {method_a, method_b}:
            continue
        r = row["result"]
        lookup[(r["split"], r["track"], r["source_id"], r["task_id"], row["seed"])][row["method"]] = flat_metrics(r)[metric]
    panels = defaultdict(lambda: defaultdict(list))
    for (split, track, source, task, seed), values in lookup.items():
        a, b = values.get(method_a), values.get(method_b)
        panels[(split, track)][source].append(None if a is None or b is None else a - b)
    return [{"split": split, "track": track, "metric": metric, "difference": f"{method_a} - {method_b}",
             **estimate([mean(v) for v in sources.values() if all(x is not None for x in v)], repeats=repeats),
             "total_sources": len(sources), "missing_sources": sum(any(x is None for x in v) for v in sources.values())}
            for (split, track), sources in sorted(panels.items())]


def export_report(records, destination, *, repeats=2000):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    summary = summarize(records, repeats=repeats)
    write(destination / "summary.json", summary)
    lines = ["# Video editing evaluation", "", "All rates are percentages. Unknowns retain bounds and coverage; no combined semantic/aesthetic total.", ""]
    with (destination / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["method", "split", "track", "metric", "mean", "ci95_low", "ci95_high", "n_sources", "total_sources"])
        for panel in summary:
            lines += [f"## {panel['method']} / {panel['split']} / {panel['track']}", "", "| Metric | Mean | 95% CI | Sources |", "|---|---:|---|---:|"]
            for name, value in panel["metrics"].items():
                digits = 4 if name in {"clip_f", "dino_f"} else 2
                displayed = "N/A" if value["mean"] is None else f"{value['mean']:.{digits}f}"
                ci = value["ci95"]
                ci_text = "N/A" if ci is None else f"[{ci[0]:.{digits}f}, {ci[1]:.{digits}f}]"
                lines.append(f"| {name} | {displayed} | {ci_text} | {value['n_sources']}/{value['total_sources']} |")
                writer.writerow([panel["method"], panel["split"], panel["track"], name, displayed,
                                 "" if ci is None else ci[0], "" if ci is None else ci[1], value["n_sources"], value["total_sources"]])
            lines.append("")
    (destination / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary
