"""Prepare/verify a frozen preview cohort; run existing scoring CLI only with --execute."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.common import load, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock
from evaluation.low_high import profile, freeze_plan, PROTOCOL
from evaluation.providers import judge_identity


def cohort(selection, snapshot, media):
    samples = {s["sample_id"]: s for s in selection["samples"]}
    records = {}
    for host, data in snapshot["hosts"].items():
        for row in data["samples"]:
            sample = samples[row["sample_id"]]
            track = row.get("prompt_form", "long")
            if track not in {"short", "long"}:
                raise ValueError("Unknown original prompt form")
            for method, result in row["methods"].items():
                candidates = list(result.get("all_completed_rounds", result.get("rounds", [])))
                if result.get("delivery"):
                    candidates.append(result["delivery"])
                for candidate in candidates:
                    digest = candidate["video_sha256"]
                    if not re.fullmatch(r"[0-9a-f]{64}", digest):
                        raise ValueError("Invalid media SHA256")
                    key = (row["sample_id"], track, digest)
                    record = records.setdefault(key, {
                        "sample_id": row["sample_id"], "track": track,
                        "source": str(Path(sample["source_video"]).resolve()),
                        "source_sha256": sample["source_sha256"],
                        "request": sample["original_" + track + "_request"],
                        "candidate": str((Path(media) / (digest + ".mp4")).resolve()),
                        "candidate_sha256": digest, "positions": [],
                    })
                    position = {"host": host, "method": method, "candidate_id": candidate.get("id"),
                                "first": candidate == result.get("first"),
                                "delivery": candidate == result.get("delivery")}
                    if position not in record["positions"]:
                        record["positions"].append(position)
    if not records:
        raise ValueError("No completed videos in the preview snapshot")
    return [records[k] for k in sorted(records)]


def prepare(selection_path, snapshot_path, media, output, judge="glm5.3flash"):
    from planner_harness.video import Video
    frozen = profile()
    if PROTOCOL != "lha-low-high-final-v5":
        raise ValueError("This entry prepares the approved v5 standard")
    records = cohort(load(selection_path), load(snapshot_path), media)
    # Verify all inputs before creating a new namespace. No credential/model loading.
    checked = set()
    for record in records:
        for field in ("source", "candidate"):
            key = (record[field], record[field + "_sha256"])
            if key not in checked:
                if sha(record[field]) != key[1]:
                    raise ValueError("Preview video hash mismatch: " + field)
                checked.add(key)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    immutable(output / "frozen-profile.json", frozen)
    plans = {}
    files = {}
    for record in records:
        task_key = signature({k: record[k] for k in ("sample_id", "track", "source_sha256", "request")})
        directory = output / "tasks" / task_key
        if task_key not in plans:
            info = Video(record["source"], directory / "source-info").info
            freeze_plan({"track": record["track"]}, record["request"], info, directory)
            (directory / "request.txt").write_text(record["request"], encoding="utf-8")
            for name in ("plan.json", "request.txt"):
                files[str((directory / name).relative_to(output))] = sha(directory / name)
            plans[task_key] = directory
        record["task_key"] = task_key
        record["job_id"] = signature({k: record[k] for k in ("sample_id", "track", "source_sha256", "request", "candidate_sha256")})
    body = {"schema": "preview-reevaluation-v1", "protocol_id": PROTOCOL,
            "profile_sha256": frozen["sha256"], "judge": judge_identity(judge),
            "judge_alias": judge, "records": records, "files": files,
            "inputs": {"selection_sha256": sha(selection_path), "snapshot_sha256": sha(snapshot_path)},
            "entry_sha256": sha(__file__), "scoring_cli_sha256": sha(ROOT / "scripts/run_low_high_eval.py"),
            "scope": "All completed saved preview candidates, deduplicated within each original task. No new generation or blind comparisons."}
    immutable(output / "manifest.json", {**body, "sha256": signature(body)})
    return verify(output)


def verify(output):
    output = Path(output).resolve()
    manifest = load(output / "manifest.json")
    if manifest.get("sha256") != signature({k: v for k, v in manifest.items() if k != "sha256"}):
        raise ValueError("Re-evaluation manifest changed")
    frozen = load(output / "frozen-profile.json")
    if frozen != profile() or frozen["sha256"] != manifest["profile_sha256"]:
        raise ValueError("Scoring implementation/profile changed; prepare a new namespace")
    if manifest["entry_sha256"] != sha(__file__) or manifest["scoring_cli_sha256"] != sha(ROOT / "scripts/run_low_high_eval.py"):
        raise ValueError("Re-evaluation entry changed")
    if manifest["judge"] != judge_identity(manifest["judge_alias"]):
        raise ValueError("Judge configuration changed")
    for relative, digest in manifest["files"].items():
        path = (output / relative).resolve()
        if not path.is_relative_to(output) or sha(path) != digest:
            raise ValueError("Frozen request or plan changed")
    checked = set()
    for row in manifest["records"]:
        for field in ("source", "candidate"):
            key = (row[field], row[field + "_sha256"])
            if key not in checked:
                if sha(row[field]) != key[1]:
                    raise ValueError("Frozen video changed")
                checked.add(key)
    return manifest


def run(output, *, execute=False, budget_config=None, credentials=None):
    if not execute:
        raise ValueError("Scoring requires explicit --execute; preparation makes no model calls")
    if budget_config is None:
        raise ValueError("Provide the existing compute budget config for feature/flow jobs")
    missing = [n for n in ("torch", "transformers", "cv2", "av") if importlib.util.find_spec(n) is None]
    if missing:
        raise ValueError("Scoring environment lacks: " + ", ".join(missing))
    output = Path(output).resolve()
    manifest = verify(output)
    if credentials:
        from vlm.settings import load_credentials
        load_credentials(str(credentials))
    with RunLock(output / "evaluation-owner"), RunLock(ROOT / "out/provider-locks" / manifest["judge_alias"], timeout=7200):
        for row in manifest["records"]:
            if profile()["sha256"] != manifest["profile_sha256"]:
                raise ValueError("Scoring profile changed during the run")
            task = output / "tasks" / row["task_key"]
            # Existing scorer owns transport recovery, cached answers, event reviews and metrics.
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts/run_low_high_eval.py"), "score",
                            "--source", row["source"], "--candidate", row["candidate"],
                            "--request-file", str(task / "request.txt"), "--plan", str(task / "plan.json"),
                            "--judge", manifest["judge_alias"], "--output", str(output / "scores" / row["job_id"]),
                            "--budget-config", str(Path(budget_config).resolve()), "--execute"], check=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "run"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--media", type=Path)
    parser.add_argument("--judge", choices=("glm5.3flash", "sonnet-5.5high"), default="glm5.3flash")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--budget-config", type=Path)
    parser.add_argument("--credentials", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        if not all((args.selection, args.snapshot, args.media)):
            parser.error("prepare requires --selection, --snapshot and --media")
        manifest = prepare(args.selection, args.snapshot, args.media, args.output, args.judge)
    elif args.command == "verify":
        manifest = verify(args.output)
    else:
        manifest = run(args.output, execute=args.execute, budget_config=args.budget_config, credentials=args.credentials)
    print(json.dumps({"command": args.command, "videos": len(manifest["records"]),
                      "tasks": len({r["task_key"] for r in manifest["records"]}),
                      "profile_sha256": manifest["profile_sha256"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
