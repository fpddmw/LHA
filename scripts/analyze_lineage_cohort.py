"""Read saved runs, verify local artifacts and export descriptive lineage evidence.

No model, render, network request or historical state mutation is performed.
The manifest lists repository-relative run directories under the `runs` key.
"""
import argparse
import copy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from planner_harness.lineage import analyze, control_plan


def local_media(root, run, identity, video, index):
    recorded = Path(video["path"])
    candidates = [recorded, run / "videos" / identity / recorded.name]
    candidates.extend(index.get(video["sha256"], []))
    for path in candidates:
        # Remote /root or /output paths are historical identity, not local I/O targets.
        if not path.is_absolute():
            path = root / path
        if not path.is_relative_to(root):
            continue
        try:
            if path.resolve().is_relative_to(root) and path.is_file() and sha(path) == video["sha256"]:
                return path.resolve()
        except OSError:
            continue
    return None


def analyze_cohort(root, manifest, output, *, media_roots=()):
    root, output = Path(root).resolve(), Path(output).resolve()
    # Sources may have moved in an authorized benchmark reorganization.
    index = {}
    for directory in [root / "benchmark_data", *map(Path, media_roots)]:
        directory = directory.resolve()
        if not directory.is_relative_to(root):
            raise ValueError("Additional media roots must stay inside the repository")
        for path in sorted(directory.rglob("*.mp4")):
            index.setdefault(sha(path), []).append(path)
    rows = []
    for entry in load(manifest)["runs"]:
        run = (root / entry["run"]).resolve()
        if not run.is_relative_to(root):
            raise ValueError("Run directory must stay inside the repository")
        original = load(run / "state.json")
        state_hash = sha(run / "state.json")
        if original.get("config", {}).get("execution", {}).get("mode") != "live":
            raise ValueError("Historical empirical cohort requires recorded live-mode runs")
        analysis = analyze(original)
        rebased = copy.deepcopy(original)
        media, receipts = {}, []
        for identity, video in original["videos"].items():
            path = local_media(root, run, identity, video, index)
            media[identity] = {"expected_sha256": video["sha256"],
                "local_path": str(path) if path else None, "status": "verified" if path else "unavailable"}
            if path:
                rebased["videos"][identity]["path"] = str(path)
            if video.get("imported") or not video.get("job_id"):
                continue
            job_id = video["job_id"]; job = original["jobs"][job_id]
            if signature({k:v for k,v in job.items() if k != "sha256"}) != job["sha256"]:
                raise ValueError("Historical generation job signature changed")
            response_path = run / "jobs" / job_id / "response.json"
            response = load(response_path)
            if response["request_sha256"] != job["sha256"] or response["status"] != "complete" or response["payload"]["video"]["sha256"] != video["sha256"]:
                raise ValueError("Historical generation receipt does not bind its candidate")
            receipts.append({"job_id": job_id, "response_sha256": sha(response_path)})
        controls = []
        for edge in analysis["parent_child_changes"]:
            candidate = edge["child"]
            plan = control_plan(rebased, candidate)
            inputs = ["source", original["videos"][candidate]["parent"]]
            plan["local_inputs_verified"] = all(media[k]["status"] == "verified" for k in inputs)
            plan["historical_state_sha256"] = state_hash
            plan["historical_generation_receipt"] = next(r for r in receipts if r["job_id"] == original["videos"][candidate]["job_id"])
            controls.append(plan)
        identity = signature({"run": entry["run"], "state_sha256": state_hash})[:16]
        detail = {"run": entry["run"], "state_sha256": state_hash, "media": media,
                  "verified_generation_receipts": receipts, "analysis": analysis, "control_plans": controls,
                  "assessment_scope": "Reanalysis of saved historical online findings. No current-rubric rescoring or causal degradation estimate."}
        target = output / "runs" / (identity + ".json")
        save(target, detail)
        assert sha(run / "state.json") == state_hash
        rows.append({"run": entry["run"], "detail_path": str(target), "detail_sha256": sha(target),
            "candidates": len(analysis["candidates"]), "chain_edges": len(analysis["parent_child_changes"]),
            "matched_controls": len(analysis["matched_restart_controls"]),
            "verified_candidate_media": sum(v["status"] == "verified" for k,v in media.items() if k != "source"),
            "verified_sources": int(media["source"]["status"] == "verified"),
            "control_plans": len(controls),
            "known_generation_seconds": sum(v["known_generation_seconds"] for v in analysis["by_depth"].values()),
            "unknown_generation_costs": sum(v["unknown_costs"] for v in analysis["by_depth"].values())})
    result = {"version": "historical-lineage-cohort-v1", "runs": rows,
              "totals": {k: sum(row[k] for row in rows) for k in ["candidates", "chain_edges", "matched_controls", "verified_candidate_media", "verified_sources", "control_plans", "known_generation_seconds", "unknown_generation_costs"]},
              "interpretation": "Depth and parent/child findings are descriptive. Matched prompt/seed/source-restart controls and the current frozen assessment are required to estimate accumulated damage.",
              "model_calls": 0, "renders": 0}
    save(output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, action="append", default=[],
                        help="Additional explicitly selected local recovery media directory")
    args = parser.parse_args()
    result = analyze_cohort(ROOT, args.manifest, args.output, media_roots=args.media_root)
    print(result["totals"])


if __name__ == "__main__":
    main()
