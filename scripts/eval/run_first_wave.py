"""Resume the approved first-wave blind evaluation with bounded model concurrency."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from evaluation.aggregate import export_report, paired_difference
from evaluation.judges import client_from_factory, judge, pairwise, unknown_judgment
from evaluation.media import decode
from evaluation.protocol import file_hash, read, require, signature, validate_card, write
from evaluation.scoring import score


def overview_evidence(e):
    e = dict(e)
    selected = [i for i, p in enumerate(e["pairs"]) if p.get("overview", True)]
    e["parent_evidence_sha256"] = e.pop("evidence_sha256")
    e["pairs"] = [{**e["pairs"][i], "dense": False} for i in selected]
    for key in ("source_images", "output_images"):
        e[key] = [e[key][i] for i in selected]
    e["dense_ranges"] = []
    e["image_sha256"] = [file_hash(p) for p in e["source_images"] + e["output_images"]]
    e["evidence_scope"] = "Matched appearance/design overview; motion remains unconfirmed by this pairwise view"
    e["evidence_sha256"] = signature(e)
    return e


def references(run, manifest):
    """Independent of slow dense-evidence writes; fixed pools before any creativity scoring."""
    pools = {}
    for case in manifest:
        if case["method"] == "source_control":
            continue
        card = read(ROOT / case["card"])
        task = card["task_id"]
        dest = run / "reference_frames" / case["case_id"]
        marker = dest / "reference.json"
        if marker.exists():
            ref = read(marker)
            require(ref["output_sha256"] == file_hash(ROOT / case["output_video"]), "Reference video changed")
        else:
            video = decode(ROOT / case["output_video"])
            indices = [i for i, t in enumerate(video["times"]) if t < card["duration_seconds"]]
            selected = sorted({indices[0], indices[len(indices) // 2], indices[-1]})
            dest.mkdir(parents=True, exist_ok=True)
            images = []
            for n, i in enumerate(selected):
                path = dest / f"frame_{n}.jpg"
                video["frames"][i].save(path, quality=95)
                images.append(str(path.resolve()))
            ref = {"images": images, "image_sha256": [file_hash(p) for p in images],
                   "output_sha256": file_hash(ROOT / case["output_video"])}
            write(marker, ref)
        pools.setdefault(task, []).append({k: ref[k] for k in ("images", "image_sha256")})
    for task, candidates in pools.items():
        candidates.sort(key=lambda c: c["image_sha256"][0])
        path = run / "references_fixed" / f"{task}.json"
        value = {"task_id": task, "candidates": candidates}
        if path.exists():
            require(read(path) == value, "Reference pool changed")
        else:
            write(path, value)


def lock(run):
    path = Path(tempfile.gettempdir()) / ("lha-evaluation-" + hashlib.sha256(str(run.resolve()).encode()).hexdigest()[:16] + ".lock")
    stream = path.open("a+b")
    stream.seek(0); stream.write(b"0"); stream.flush(); stream.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    return stream


def execute(case, run, factory):
    card = validate_card(read(ROOT / case["card"]))
    directory = run / "judgments" / case["case_id"]
    evidence = read(run / "evidence" / case["case_id"] / "evidence.json")
    row = {"case_id": case["case_id"], "method": case["method"], "seed": case["seed"], "output_video": case["output_video"]}
    started = time.time()
    try:
        client = client_from_factory(factory, {"role": "benchmark_final"})
        j = judge(card, evidence, client, directory,
                  references=read(run / "references_fixed" / f"{card['task_id']}.json"), creativity_overview=True)
        write(directory / "judgment.json", j)
        row.update(status="complete", result=score(card, j))
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        row.update(status="evaluation_error", evaluation_error=error,
                   result=score(card, unknown_judgment(card, evidence["delivery"], error)))
    row["elapsed_seconds"] = time.time() - started
    write(directory / "record.json", row)
    return row


def publish(run, manifest, records):
    ready = list(records.values())
    write(run / "records.json", ready)
    write(run / "status.json", {"pid": os.getpid(), "total": len(manifest),
          "completed": sum(r["status"] == "complete" for r in ready), "errors": sum(r["status"] != "complete" for r in ready),
          "pending": [c["case_id"] for c in manifest if c["case_id"] not in records], "updated_unix": time.time(),
          "note": "Interim reports cover evaluated rows only; pending jobs are not generation failures."})
    if ready:
        export_report(ready, run / "report", repeats=1000)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--factory", default="vlm.codex_vlm:CodexVisionModel")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--poll-seconds", type=int, default=600)
    p.add_argument("--references-only", action="store_true")
    args = p.parse_args()
    run = args.run
    handle = lock(run)
    require(args.workers in {1, 2}, "Use at most two concurrent judges")
    manifest = read(run / "manifest.json")["cases"]
    primary = set(read(run / "primary_cases.json"))
    manifest.sort(key=lambda c: (c["case_id"] not in primary, "041" not in c["case_id"], c["case_id"]))
    write(run / "worker.json", {"pid": os.getpid(), "factory": args.factory, "workers": args.workers,
          "started_unix": time.time(), "evaluator_sources": {p.name: file_hash(p) for p in (ROOT / "src/evaluation").glob("*.py")},
          "script_sha256": file_hash(__file__), "scope": "Full native semantic/design evidence; overview-only creativity and pairwise design review"})
    references(run, manifest)
    if args.references_only:
        return 0
    records = {}
    for case in manifest:
        path = run / "judgments" / case["case_id"] / "record.json"
        if path.exists():
            records[case["case_id"]] = read(path)
    while len(records) < len(manifest):
        ready = [c for c in manifest if c["case_id"] not in records and (run / "evidence" / c["case_id"] / "evidence.json").exists()]
        publish(run, manifest, records)
        if not ready:
            time.sleep(args.poll_seconds)
            continue
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(execute, case, run, args.factory): case for case in ready}
            for future in as_completed(futures):
                row = future.result()
                records[row["case_id"]] = row
                publish(run, manifest, records)
                print(json.dumps({"case_id": row["case_id"], "status": row["status"], "error": row.get("evaluation_error")}, ensure_ascii=False), flush=True)
    primary_rows = []
    for row in records.values():
        if row["case_id"] in primary:
            renderer = row["case_id"].split("__")[0]
            role = "planner" if "__planner__" in row["case_id"] else "direct"
            primary_rows.append({**row, "method": renderer + "_" + role})
    write(run / "primary_records.json", primary_rows)
    export_report(primary_rows, run / "primary_report")
    diffs = []
    for renderer in ("bernini", "ditto"):
        for metric in ("edit", "preserve_core", "preserve_detail", "style", "aesthetic_mean", "scene_specific_design", "relative_originality"):
            diffs += paired_difference(primary_rows, renderer + "_planner", renderer + "_direct", metric)
    write(run / "primary_differences.json", diffs)
    by_id = {c["case_id"]: c for c in manifest}
    comparisons = []
    for planned in [c for c in manifest if "__planner__" in c["case_id"]]:
        card = read(ROOT / planned["card"])
        renderer = planned["case_id"].split("__")[0]
        baseline_id = renderer + "__baseline__" + card["source_id"] + "__" + card["track"]
        ea = overview_evidence(read(run / "evidence" / planned["case_id"] / "evidence.json"))
        eb = overview_evidence(read(run / "evidence" / baseline_id / "evidence.json"))
        destination = run / "pairwise" / (renderer + "__" + card["task_id"])
        result = pairwise(card, ea, eb, client_from_factory(args.factory, {"role": "benchmark_final_pair"}), destination)
        result.update(renderer=renderer, task_id=card["task_id"], a=planned["case_id"], b=baseline_id,
                      evidence_scope="Matched overview only; do not use this preference as proof of fine motion preservation")
        write(destination / "result.json", result)
        comparisons.append(result)
        write(run / "pairwise_results.json", comparisons)
    write(run / "completion.json", {"completed_unix": time.time(), "cases": len(records), "pairwise": len(comparisons),
          "evaluation_errors": [r["case_id"] for r in records.values() if r["status"] != "complete"]})
    handle.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
