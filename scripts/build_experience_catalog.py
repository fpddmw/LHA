"""Assemble the curated experience catalog from entry front matter and verify its evidence.

Each entry file begins with a ``<!-- meta {...} -->`` comment naming its identity and
placement. The builder hashes every entry and resource, checks that every cited
evidence file exists, and refuses evidence tied to a benchmark test-split source
video so the shared library cannot carry held-out observations.
Offline only: no model, renderer or network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "knowledge/experience/curated"
META = re.compile(r"\A<!-- meta (\{.*?\}) -->\n", re.S)
SCHEMA = "creative-experience-catalog-v2"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def heldout_hashes():
    benchmark = json.loads((ROOT / "benchmark_data/benchmark.json").read_text())
    return {r["source_video_sha256"]: r["sample_id"] for r in benchmark if r["split"] != "train"}


def hashes_in(value, found):
    if isinstance(value, dict):
        for item in value.values():
            hashes_in(item, found)
    elif isinstance(value, list):
        for item in value:
            hashes_in(item, found)
    elif isinstance(value, str):
        found.update(re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", value))


def check_evidence(path, blocked):
    if path.suffix.lower() not in {".json", ".md", ".txt"}:
        return
    text = path.read_text()
    found = set()
    value = json.loads(text) if path.suffix.lower() == ".json" else text
    hashes_in(value, found)
    leaked = sorted(blocked[h] for h in found if h in blocked)
    if leaked:
        raise SystemExit(f"{path.name} cites held-out sample(s) {leaked}; the shared library may use train evidence only")
    def check_split(node):
        if isinstance(node, dict):
            if node.get("split") in ("test", "validation", "heldout"):
                raise SystemExit(f"{path.name} declares held-out evidence")
            if "sample_id" in node and str(node["sample_id"]).zfill(3) in set(blocked.values()):
                raise SystemExit(f"{path.name} cites a held-out sample_id")
            for item in node.values():
                check_split(item)
        elif isinstance(node, list):
            for item in node:
                check_split(item)
        elif isinstance(node, str):
            if re.search(r"benchmark_data[/\\](?:test|validation)[/\\]", node):
                raise SystemExit(f"{path.name} cites a held-out benchmark path")
            for identity in re.findall(r"\bsample_id\s*[:=]\s*[\"']?(\d+)\b", node):
                if identity.zfill(3) in set(blocked.values()):
                    raise SystemExit(f"{path.name} declares a held-out sample_id")
    check_split(value)


def check_links(path):
    """Validate local reading links; code/log paths in prose are not navigation."""
    if path.suffix.lower() != ".md":
        return
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
        if re.match(r"^[a-zA-Z]+:|^#", target):
            continue
        target = target.split("#", 1)[0]
        if not (path.parent / target).resolve().is_file():
            raise SystemExit(f"{path}: broken local reading link {target}")


def build(write=True):
    sys.path.insert(0, str(ROOT / "src"))
    from planner_harness.creative_knowledge import layered_fields
    from planner_harness.experience_contributions import navigation_documents
    blocked = heldout_hashes()
    previous = json.loads((CURATED / "catalog.json").read_text())
    resources = []
    for row in previous["resources"]:
        file = ROOT / row["path"]
        if row["id"] == "EX-renderer-profiles":
            continue
        check_evidence(file, blocked)
        check_links(file)
        resources.append({**row, "sha256": sha(file)})
    entries, problems = [], []
    ids = set()
    for file in sorted((CURATED / "entries").glob("*.md")):
        text = file.read_text()
        match = META.match(text)
        if not match:
            problems.append(f"{file.name}: missing meta comment")
            continue
        meta = json.loads(match.group(1))
        missing = {"id", "title", "summary", "questions", "renderers", "layer", "evidence_ids", "review_reference"} - set(meta)
        if missing:
            problems.append(f"{file.name}: meta lacks {sorted(missing)}")
            continue
        try:
            layered_fields(meta)
            for key in ("id", "title", "summary", "review_reference"):
                if not isinstance(meta[key], str) or not meta[key].strip():
                    raise ValueError(f"{key} needs nonempty text")
            for key in ("questions", "renderers", "evidence_ids"):
                if not isinstance(meta[key], list) or any(not isinstance(v, str) or not v.strip() for v in meta[key]):
                    raise ValueError(f"{key} needs a list of nonempty strings")
            if meta["layer"] == "renderer" and not meta["renderers"]:
                raise ValueError("Renderer-layer entries must name their renderer")
        except ValueError as error:
            problems.append(f"{file.name}: {error}")
            continue
        check_evidence(file, blocked)
        check_links(file)
        if meta["id"] in ids:
            problems.append(f"{file.name}: duplicate id")
        ids.add(meta["id"])
        known = {r["id"] for r in resources}
        bad = [e for e in meta["evidence_ids"] if e not in known]
        if bad:
            problems.append(f"{file.name}: unknown evidence {bad}")
        row = {k: meta[k] for k in ("id", "title", "summary", "questions", "renderers", "layer", "evidence_ids")}
        for key in ("tracks", "families", "stages"):
            if key in meta:
                row[key] = meta[key]
        row.update(path="knowledge/experience/curated/entries/" + file.name, version=str(meta.get("version", "1")),
                   sha256=sha(file), review_status="approved", review_reference=meta["review_reference"],
                   aliases=[meta["title"], *meta["questions"]], applicability=meta["summary"],
                   recommendation=meta["summary"])
        entries.append(row)
    if problems:
        raise SystemExit("\n".join(problems))
    order = {"principle": 0, "renderer": 1, "condition": 2}
    entries.sort(key=lambda r: (order[r["layer"]], r["id"]))
    catalog = {"schema": SCHEMA, "revision": "layered-" + hashlib.sha256(
        json.dumps([[e["id"], e["sha256"]] for e in entries], sort_keys=True).encode()).hexdigest()[:16],
        "entries": entries, "resources": resources}
    # Derived navigation resources are generated from entry metadata.
    navigation = navigation_documents(catalog)
    for path, text in navigation.items():
        digest = hashlib.sha256(text.encode()).hexdigest()
        # README.md is the static `experience-map` topic; only renderers.md is a catalog resource.
        if path.endswith("renderers.md"):
            resources.append({"id": "EX-renderer-profiles", "title": "Renderer entrances",
                              "path": path, "version": "derived-" + digest[:16], "sha256": digest,
                              "review_status": "approved",
                              "review_reference": "Derived from canonical entry metadata"})
        if write:
            (ROOT / path).write_text(text)
    if write:
        (CURATED / "catalog.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    else:
        if catalog != previous:
            raise SystemExit("Catalog differs from entry/resource sources; rebuild before using the library")
        for path, text in navigation.items():
            if not (ROOT / path).is_file() or (ROOT / path).read_text() != text:
                raise SystemExit(f"Generated navigation is stale: {path}")
    return catalog


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without writing")
    args = parser.parse_args()
    result = build(write=not args.check)
    print(json.dumps({"entries": len(result["entries"]), "resources": len(result["resources"]),
                      "revision": result["revision"]}))
