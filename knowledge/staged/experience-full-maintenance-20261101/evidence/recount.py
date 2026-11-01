"""Reproduce this review's descriptive counts from preserved development extracts."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    rows = []
    temporal = Counter()
    prediction = Counter()
    all_targets = 0
    collateral = []
    for i in range(1, 8):
        d = json.loads((ROOT / f"F{i:03}.json").read_text())
        req = {x["id"]: x for x in d["requirements"]["items"]}
        reviews = {x["video_id"]: x["outcome"] for x in d["evaluations"].values()}
        attempts = {x["video"]: x for x in d["task_memory"]["attempts"]}
        for vid in ("v1", "v2", "v3"):
            video, review, attempt = d["videos"][vid], reviews[vid], attempts[vid]
            all_targets += set(attempt["intent"]["targets"]) == set(req)
            for item in review["requirement_verdicts"]:
                if req.get(item["id"], {}).get("temporal"):
                    temporal[item["verdict"]] += 1
            prediction.update(attempt.get("prediction", {}).get("checks", {}).values())
            if vid != "v1" and attempt.get("collateral_regressions"):
                collateral.append([f"F{i:03}", vid, attempt["collateral_regressions"]])
            before = {x["id"]: x["verdict"] for x in reviews.get("v2", {}).get("requirement_verdicts", [])}
            # Local ordinal change is descriptive, never a quality/causal score.
            order = {"fail": 0, "partial": 1, "pass": 2}
            gains = [x["id"] for x in review["requirement_verdicts"]
                     if vid == "v3" and x["verdict"] in order and before.get(x["id"]) in order
                     and order[x["verdict"]] > order[before[x["id"]]]]
            rows.append({"task": f"F{i:03}", "video": vid, "input": video["parent"],
                         "job": video["job_id"], "major_damage": review.get("major_damage"),
                         "selected": d["final"]["video"] == vid,
                         "stop_reason": d["final"].get("stop_reason"),
                         "generation_seconds": video["execution"].get("generation_seconds"),
                         "ordinal_gains_vs_v2": gains})
    third = [x for x in rows if x["video"] == "v3"]
    routes = {}
    for route in ("source", "v2"):
        group = [x for x in third if x["input"] == route]
        routes[route] = {"attempts": len(group), "no_major_damage": sum(x["major_damage"] is False for x in group),
                         "at_least_one_known_ordinal_gain": sum(bool(x["ordinal_gains_vs_v2"]) for x in group),
                         "tasks": [x["task"] for x in group]}
    report = {"basis": "Saved online RSI protocol; descriptive ordinal gains are not overall improvement.",
              "tasks": 7, "candidates": len(rows), "online_reviews": len(rows),
              "all_requirements_targeted": all_targets,
              "temporal_requirement_verdicts": dict(temporal),
              "item_prediction_checks": dict(prediction),
              "later_attempts_with_collateral_regressions": collateral,
              "third_attempt_routes": routes,
              "earlier_candidate_selected_tasks": [x["task"] for x in rows if x["selected"] and x["video"] != "v3"],
              "known_generation_seconds": sum(x["generation_seconds"] or 0 for x in rows),
              "known_generation_count": sum(x["generation_seconds"] is not None for x in rows),
              "rows": rows}
    (ROOT / "batch-facts.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
