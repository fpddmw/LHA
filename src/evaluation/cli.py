"""CLI for annotation, evidence, independent judging, reports and loop analysis."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import PROTOCOL
from .aggregate import export_report, paired_difference
from .judges import ANNOTATE, cached_call, client_from_factory, judge, pairwise, plan_diagnostics, unknown_judgment
from .media import decode, prepare
from .protocol import file_hash, freeze, read, require, validate_card, validate_judgment, write
from .scoring import score, error_result


def scaffold(index):
    """Create task entries, not fabricated source annotations or frozen cards."""
    result = []
    for sample in index:
        for track in ("short", "long"):
            requirement = sample.get(f"prompt_{track}")
            if not requirement:
                continue
            result.append({"protocol": PROTOCOL, "task_id": f"{sample['sample_id']}__{track}",
                           "source_id": sample["sample_id"], "split": sample["split"], "track": track,
                           "source_video": sample["source_video"], "source_sha256": sample["source_video_sha256"],
                           "requirement": requirement, "benchmark_version": sample.get("benchmark_version"),
                           "status": "draft"})
    return result


def annotate(entry, client, destination, root, duration=None):
    require(file_hash(root / entry["source_video"]) == entry["source_sha256"], "Source hash mismatch")
    decoded = decode(root / entry["source_video"])
    duration = min(5.0, decoded["duration"]) if duration is None else duration
    require(0 < duration <= decoded["duration"] + 0.08, "Annotation interval outside source")
    indices = [i for i, t in enumerate(decoded["times"]) if t < duration]
    chosen = sorted({indices[round(j * (len(indices) - 1) / 11)] for j in range(12)})
    destination.mkdir(parents=True, exist_ok=True)
    images = []
    for i in chosen:
        path = destination / f"source_{i:05d}.jpg"
        decoded["frames"][i].save(path, quality=95)
        images.append(str(path.resolve()))
    response = cached_call(client, ANNOTATE, {"requirement": entry["requirement"], "track": entry["track"],
                           "source_times": [decoded["times"][i] for i in chosen]}, images, destination / "annotation.raw.json")
    card = {**response, **entry, "duration_seconds": duration, "source_start_seconds": 0,
            "status": "draft", "reviewed_by": None}
    validate_card(card, frozen=False)
    write(destination / "card.draft.json", card)
    return card


def load_records(path):
    path = Path(path)
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    value = read(path)
    return value["cases"] if isinstance(value, dict) else value


def evaluate_manifest(cases, destination, root, client, *, frame_count=12, dense_ranges=()):
    destination.mkdir(parents=True, exist_ok=True)
    ids = [row["case_id"] for row in cases]
    require(len(ids) == len(set(ids)), "Duplicate case_id")
    require(all(i and all(c.isalnum() or c in "_-" for c in i) for i in ids), "case_id must be a safe basename")
    records = []
    for case in cases:
        card = validate_card(read(root / case["card"]))
        directory = destination / case["case_id"]
        output = root / case["output_video"]
        row = {"case_id": case["case_id"], "method": case["method"], "seed": case["seed"], "output_video": str(output)}
        row["evaluation_role"] = "final"
        evidence = None
        try:
            if not output.exists():
                row.update(status="missing_output", result=error_result(card, {"status": "invalid"}, "No output video", status="missing_output"))
            else:
                evidence = prepare(card, output, directory / "evidence", root=root, frame_count=frame_count,
                                   dense_ranges=dense_ranges, mapping=read(root / case["mapping"]) if case.get("mapping") else None)
                refs = read(root / case["references"]) if case.get("references") else None
                judgment = judge(card, evidence, client, directory, references=refs)
                write(directory / "judgment.json", judgment)
                row.update(status="complete", result=score(card, judgment, role="final"))
        except Exception as exc:
            # An evaluator failure remains unresolved, never a failed generation or an omitted case.
            message = f"{type(exc).__name__}: {exc}"
            status = "invalid_delivery" if evidence and evidence["delivery"]["status"] == "invalid" else "evaluation_error"
            row["delivery_error" if status == "invalid_delivery" else "evaluation_error"] = message
            row["status"] = status
            row["result"] = error_result(card, evidence["delivery"] if evidence else {"status": "unknown"}, message, status=status)
            write(directory / "evaluation_error.json", row)
        if case.get("features"):
            try:
                automatic = read(root / case["features"])
                require(output.exists() and automatic["output_sha256"] == file_hash(output), "Feature/output mismatch")
                require(automatic["protocol"] == "lha-output-consistency-v1", "Feature protocol mismatch")
                row["result"]["automatic"] = automatic
            except Exception as exc:
                row["feature_error"] = f"{type(exc).__name__}: {exc}"
        from .compat import canonical_record
        row = canonical_record(row)
        records.append(row)
        write(destination / "records.json", records)
        print(json.dumps({"case_id": case["case_id"], "success": row["result"]["success"], "error": row.get("evaluation_error")}, ensure_ascii=False), flush=True)
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name, model=False):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, required=True)
        if model:
            p.add_argument("--factory", required=True, help="module:class implementing predict_json")
            p.add_argument("--client-options", default='{"role":"benchmark_final"}', help="JSON constructor kwargs; keep keys in environment")
        return p

    p = command("scaffold"); p.add_argument("--index", type=Path, required=True)
    p = command("annotate", True); p.add_argument("--index", type=Path, required=True); p.add_argument("--task", required=True)
    p.add_argument("--root", type=Path, default=Path(".")); p.add_argument("--duration", type=float)
    p = command("freeze"); p.add_argument("--card", type=Path, required=True); p.add_argument("--reviewer", required=True)
    p = command("prepare"); p.add_argument("--card", type=Path, required=True); p.add_argument("--video", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path(".")); p.add_argument("--frames", type=int, default=12)
    p.add_argument("--dense", nargs=2, type=float, action="append", default=[]); p.add_argument("--mapping", type=Path)
    p = command("judge", True); p.add_argument("--card", type=Path, required=True); p.add_argument("--evidence", type=Path, required=True); p.add_argument("--references", type=Path)
    p = command("score"); p.add_argument("--card", type=Path, required=True); p.add_argument("--judgment", type=Path, required=True)
    p = command("evaluate", True); p.add_argument("--manifest", type=Path, required=True); p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--frames", type=int, default=12); p.add_argument("--dense", nargs=2, type=float, action="append", default=[])
    p = command("report"); p.add_argument("--records", type=Path, required=True); p.add_argument("--bootstrap", type=int, default=2000)
    p = command("compare"); p.add_argument("--records", type=Path, required=True); p.add_argument("--a", required=True); p.add_argument("--b", required=True); p.add_argument("--metric", required=True)
    p = command("agreement"); p.add_argument("--pairs", type=Path, required=True)
    p = command("preferences"); p.add_argument("--pairs", type=Path, required=True)
    p = command("loop"); p.add_argument("--card", type=Path, required=True); p.add_argument("--rounds", type=Path, required=True)
    p = command("pairwise", True); p.add_argument("--card", type=Path, required=True); p.add_argument("--a", type=Path, required=True); p.add_argument("--b", type=Path, required=True)
    p = command("plan", True); p.add_argument("--card", type=Path, required=True); p.add_argument("--plan", type=Path, required=True); p.add_argument("--evidence", type=Path, required=True)
    p = command("features"); p.add_argument("--video", type=Path, required=True); p.add_argument("--device", default="cpu")
    p.add_argument("--sample-fps", type=float, default=4.0); p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--clip-model", default="openai/clip-vit-large-patch14"); p.add_argument("--dino-model", default="facebook/dinov2-large")
    p.add_argument("--clip-revision", default="main"); p.add_argument("--dino-revision", default="main")
    args = parser.parse_args(argv)
    client = client_from_factory(args.factory, json.loads(args.client_options)) if hasattr(args, "factory") else None
    if args.command == "scaffold":
        write(args.out, scaffold(read(args.index)))
    elif args.command == "annotate":
        matches = [r for r in read(args.index) if r["task_id"] == args.task]
        require(len(matches) == 1, "Task id must occur exactly once")
        annotate(matches[0], client, args.out, args.root, args.duration)
    elif args.command == "freeze":
        write(args.out, freeze(read(args.card), args.reviewer))
    elif args.command == "prepare":
        prepare(read(args.card), args.video, args.out, root=args.root, frame_count=args.frames,
                dense_ranges=args.dense, mapping=read(args.mapping) if args.mapping else None)
    elif args.command == "judge":
        result = judge(read(args.card), read(args.evidence), client, args.out,
                       references=read(args.references) if args.references else None)
        write(args.out / "judgment.json", result)
    elif args.command == "score":
        write(args.out, score(read(args.card), read(args.judgment)))
    elif args.command == "evaluate":
        records = evaluate_manifest(load_records(args.manifest), args.out, args.root, client,
                                    frame_count=args.frames, dense_ranges=args.dense)
        export_report(records, args.out / "report")
        return int(any(r.get("evaluation_error") or r.get("feature_error") for r in records))
    elif args.command == "report":
        export_report(load_records(args.records), args.out, repeats=args.bootstrap)
    elif args.command == "compare":
        from .reporting import VERSION, difference_spec, normalized_records
        panels = paired_difference(normalized_records(load_records(args.records)), args.a, args.b, args.metric, include_overall=True)
        write(args.out, [{**p, "reporting_version": VERSION, "metadata": difference_spec(args.metric)} for p in panels])
    elif args.command == "agreement":
        from .reliability import agreement
        write(args.out, agreement(read(args.pairs)))
    elif args.command == "preferences":
        from .reliability import preferences
        write(args.out, preferences(read(args.pairs)))
    elif args.command == "loop":
        from .loop import analyze
        write(args.out, analyze(read(args.card), read(args.rounds)))
    elif args.command == "pairwise":
        write(args.out / "pairwise.json", pairwise(read(args.card), read(args.a), read(args.b), client, args.out))
    elif args.command == "plan":
        write(args.out / "plan_diagnostics.json", plan_diagnostics(read(args.card), read(args.plan), read(args.evidence), client, args.out / "plan.raw.json"))
    elif args.command == "features":
        from .features import compute
        write(args.out, compute(args.video, clip_model=args.clip_model, dino_model=args.dino_model,
                               clip_revision=args.clip_revision, dino_revision=args.dino_revision,
                               sample_fps=args.sample_fps, device=args.device, batch_size=args.batch_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
