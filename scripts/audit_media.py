"""Non-destructive tracked media/source/reference inventory and active denominator check."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.common import load, save, sha
from planner_harness.execution import signature


def audit(root=ROOT):
    root = Path(root)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    tracked = [p for p in tracked if p]
    others = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
    entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root).decode().split("\0")
    objects = {}
    for entry in filter(None, entries):
        metadata, name = entry.split("\t", 1)
        mode, oid, stage = metadata.split()
        if stage == "0":
            objects[name] = oid
    object_ids = sorted(set(objects.values()))
    checked = subprocess.run(["git", "cat-file", "--batch-check"], cwd=root,
                             input="\n".join(object_ids) + "\n", text=True, capture_output=True, check=True)
    available = {}
    for line in checked.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[1] == "blob":
            available[fields[0]] = int(fields[2])
    media = sorted({p for p in tracked + others if p and Path(p).suffix.lower() in {".mp4", ".jpg", ".jpeg", ".png", ".webp"}})
    refs = defaultdict(set)
    for name in sorted(set(tracked + [p for p in others if p])):
        path = root / name
        if path.suffix.lower() not in {".md", ".json", ".jsonl", ".py", ".txt", ".html", ".yaml", ".yml"} or not path.is_file() or path.stat().st_size > 10000000:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").replace("\\\\", "/").replace("\\", "/")
        for token in re.findall(r"[^\s\"'<>\[\](){}]+\.(?:mp4|jpg|jpeg|png|webp)", text, re.I):
            refs[token.lstrip("./")].add(name)
    all_rows = load(root / "benchmark_data/benchmark.json")
    known = defaultdict(list)
    for row in all_rows:
        for field in ('source_video','prompt_file','prompt_short_file'):
            known[row[field+'_sha256']].append({'record':'benchmark_data/benchmark.json','package_path':row[field]})
    rows = []
    for name in media:
        path = root / name
        digest = sha(path) if path.is_file() else None
        role = "active_or_imported_input" if name.startswith("benchmark_data/") else "knowledge_reference" if name.startswith("knowledge/") else "historical_archive" if name.startswith("归档_extract/") else "historical_or_unclassified_media"
        rows.append({"path":name, "bytes":path.stat().st_size if path.exists() else None, "sha256":digest,
                     "tracking_status":"tracked" if name in tracked else "untracked",
                     "working_tree_status":"present" if path.is_file() else "removed_from_working_tree",
                     "role":role, "source_evidence":known.get(digest, []),
                     "license_status":"unverified", "redistribution_permission":"unknown",
                     "direct_references":sorted(refs.get(name, [])),
                     "recovery": {"git_index_object": objects.get(name),
                                  "object_bytes": available.get(objects.get(name)),
                                  "status": "git_object_available" if objects.get(name) in available else "no_index_blob",
                                  "scope": "Indexed historical bytes; restoring them is separate from the active working file and benchmark."},
                     "reference_scope":"Exact repository-relative references in tracked and nonignored untracked text; dynamic, encoded and external paths require separate review."})
    ids = [r['sample_id'] for r in all_rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate active benchmark ID')
    for row in all_rows:
        for field in ('source_video','prompt_file','prompt_short_file'):
            if sha(root/row[field])!=row[field+'_sha256']:raise ValueError('Benchmark artifact changed')
    counts = dict(Counter(r['split'] for r in all_rows))
    counts.update(all=len(all_rows), canonical_requests=len(all_rows))
    active={'version':all_rows[0]['benchmark_version'],'counts':counts,'ids':ids,
            'index_sha256':{'benchmark.json':sha(root/'benchmark_data/benchmark.json')},'subset_sha256':signature(ids)}
    residuals = [{"path":name, "exists":(root / name).exists(), "tracked_paths":sum(p == name or p.startswith(name + "/") for p in tracked)}
                 for name in ("_wtest", "_wtest2", "_wtest3", "_trash", "归档_extract", "2026-10-26_09-31-33_ivebench.log")]
    removed = [row for row in rows if row["working_tree_status"] == "removed_from_working_tree"]
    return {"version":"media-audit-v2", "tracked_media":sum(row["tracking_status"]=="tracked" for row in rows),
            "working_media":sum(row["working_tree_status"]=="present" for row in rows),
            "untracked_media":sum(row["tracking_status"]=="untracked" for row in rows), "by_suffix":dict(Counter(Path(p).suffix.lower() for p in media)),
            "missing_media":sum(r["sha256"] is None for r in rows), "rows":rows, "residuals":residuals,
            "active_subset":active,
            "removed_media_recovery": {"total": len(removed),
                "git_object_available": sum(row["recovery"]["status"] == "git_object_available" for row in removed),
                "unavailable": [row["path"] for row in removed if row["recovery"]["status"] != "git_object_available"],
                "scope": "Object existence and type verified; git fsck evidence and an actual historical restore are recorded separately."},
            "cleanup_status":"benchmark_cleanup_authorized_and_completed; audit_itself_is_read_only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    save(args.output / "media-inventory.json", result)
    save(args.output / "active-subset.json", result["active_subset"])
    print(json.dumps({k:result[k] for k in ("tracked_media", "working_media", "untracked_media", "by_suffix", "missing_media", "cleanup_status")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
