"""Passive provenance and offline projections. Standard library only; no model calls."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def walk(value, pointer=""):
    if isinstance(value, dict):
        yield pointer, value
        for key, child in value.items():
            yield from walk(child, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk(child, pointer + "/" + str(i))


def record_exposure(directory, index, snapshot_sha256):
    """Bind to the final saved input, after context fitting; never alter that input."""
    directory = Path(directory)
    input_file, receipt = directory / "input.json", directory / "experience-exposure.json"
    binding = digest(input_file)
    if receipt.exists():
        previous = read_json(receipt)
        if previous["input_sha256"] != binding or previous.get("knowledge_snapshot_sha256") != snapshot_sha256:
            raise ValueError("Exposure receipt belongs to different call input")
        return
    saved = read_json(input_file)
    payload = json.loads(saved["user_text"])
    items = index["items"]
    by_path = {r["path"]: r for r in items.values()}
    surfaces, unresolved = [], []
    # Task text, Planner notes and receipt metadata are not actual source-page exposure.
    roots = {"knowledge_entrances": payload.get("knowledge_entrances", {})}
    for i, event in enumerate(payload.get("recent_operations", [])):
        roots[f"recent_operations/{i}/result"] = event.get("result", {})
    for name, value in roots.items():
        for pointer, row in walk(value, "/" + name):
            source = items.get(row.get("id")) or by_path.get(row.get("path"))
            if source is None:
                if isinstance(row.get("text"), str) and "start_line" in row:
                    unresolved.append(pointer)
                continue
            if isinstance(row.get("text"), str) and "start_line" in row:
                form = "text_page"
            elif isinstance(row.get("matches"), list):
                form = "search_excerpt"
            elif row.get("summary"):
                form = "summary"
            else:
                form = "catalog_reference"
            surfaces.append({**source, "surface": form, "pointer": pointer,
                "visible_fields": sorted(row),
                **{k: row[k] for k in ("read_id", "start_line", "end_line", "start_char", "end_char", "next_line", "next_char") if k in row},
                "visible_payload_sha256": hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()})
    for i, attachment in enumerate(saved.get("images", [])):
        source = items.get(attachment.get("id"))
        if source and Path(source["path"]).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            if source["sha256"] != attachment.get("sha256"):
                raise ValueError("Attached experience image does not match the frozen source")
            surfaces.append({**source, "surface": "image_attachment", "pointer": "/images/" + str(i),
                             "visible_fields": sorted(attachment)})
    write_json(receipt, {"schema": "experience-exposure-v1", "call_id": directory.name,
        "input_sha256": binding, "knowledge_snapshot_sha256": snapshot_sha256,
        "catalog_revision": index["catalog_revision"], "surfaces": surfaces,
        "unresolved_page_pointers": unresolved,
        "meaning": "Content in a prepared request. Transport/response records determine dispatch status; exposure is not attention or adoption."})


def call_status(directory):
    directory = Path(directory)
    if (directory / "response.txt").exists() or (directory / "transport/response.txt").exists():
        return "response_recorded"
    if list((directory / "transport/attempts").glob("*/submitted.json")):
        return "submitted_without_saved_response"
    if (directory / "input.json").exists():
        return "prepared_dispatch_unconfirmed"
    return "input_missing"


def snapshot_index(snapshot):
    """Use the run's library, never today's catalog, when reading old records."""
    result = {}
    history = [r for r in snapshot.get("manifest", {}).get("guides", []) if r.get("id") == "experience"]
    for row in snapshot.get("experiences", []) + snapshot.get("manifest", {}).get("model_experience", []) + history:
        result[row["id"]] = {k: row.get(k) for k in ("id", "path", "title", "version")}
    curated = snapshot.get("curated_catalog", {})
    for row in curated.get("entries", []) + curated.get("resources", []):
        result[row["id"]] = {k: row.get(k) for k in ("id", "path", "title", "version", "sha256")}
    for row in result.values():
        row["sha256"] = row.get("sha256") or snapshot.get("documents", {}).get(row["path"], {}).get("sha256")
    return result


def authored_texts(request):
    """Only model-authored locations; never classify an ID mention as adoption."""
    if isinstance(request.get("note"), str):
        yield "/note", request["note"]
    if isinstance(request.get("purpose"), str):
        yield "/purpose", request["purpose"]
    for name, value in (("/workspace", request.get("workspace")),
                        ("/arguments", request.get("arguments") if request.get("action") in {"note", "workspace", "finish"} else None)):
        if isinstance(value, dict):
            for pointer, row in walk(value, name):
                for key, text in row.items():
                    if isinstance(text, str):
                        yield pointer + "/" + key, text


def project_run(run):
    """Read-only, deterministic facts; missing historical fields stay unknown."""
    run = Path(run).resolve()
    state_file = run / "state.json"
    state = read_json(state_file)
    issues = []
    snapshot_path = run / "knowledge-snapshot.json"
    snapshot = read_json(snapshot_path) if snapshot_path.exists() else {}
    if snapshot and state.get("knowledge_snapshot_sha256") and state["knowledge_snapshot_sha256"] != digest(snapshot_path):
        issues.append("Knowledge snapshot differs from the state's binding; source attribution disabled.")
        snapshot = {}
    if not snapshot:
        issues.append("Knowledge snapshot missing; experience attribution is incomplete.")
    index = snapshot_index(snapshot)
    calls, surfaces, mentions = [], [], []
    for directory in sorted((run / "calls").glob("*")):
        if not directory.is_dir():
            continue
        status = call_status(directory)
        record = {"call_id": directory.name, "status": status, "input_path": str(directory / "input.json"),
                  "exposure_recorded": False}
        receipt_path = directory / "experience-exposure.json"
        if receipt_path.exists():
            try:
                receipt = read_json(receipt_path)
                if receipt["input_sha256"] != digest(directory / "input.json"):
                    raise ValueError("Input hash mismatch")
                if not snapshot_path.exists() or receipt["knowledge_snapshot_sha256"] != digest(snapshot_path):
                    raise ValueError("Knowledge snapshot hash mismatch")
                record["exposure_recorded"] = True
                record["receipt_path"] = str(receipt_path)
                record["unresolved_page_pointers"] = receipt.get("unresolved_page_pointers", [])
                surfaces.extend({**r, "call_id": directory.name, "call_status": status} for r in receipt["surfaces"])
            except (ValueError, KeyError, TypeError, OSError) as exc:
                record["receipt_error"] = type(exc).__name__
                issues.append("Unusable exposure receipt: " + directory.name)
        calls.append(record)
    reads = []
    for identity, row in state.get("reads", {}).items():
        source = index.get(row.get("id"))
        if source is not None:
            reads.append({"read_id": identity, **row, "version": source.get("version"),
                          "meaning": "Returned read; presentation to a later model call is tracked separately."})
    actions = []
    for event in state.get("events", []):
        request = event.get("request", {})
        identity = event["event_id"]
        for pointer, text in authored_texts(request):
            ids = [key for key in index if re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(key) + r"(?![A-Za-z0-9_.-])", text)]
            if ids:
                mentions.append({"event_id": identity, "pointer": "/request" + pointer,
                    "experience_ids": ids, "text": text, "basis": "literal_model_reference",
                    "interpretation": "unclassified; a mention is not acceptance, rejection or causal use"})
        if request.get("action") in {"generate", "observe", "critique", "delivery_candidate", "finish"}:
            actions.append({"event_id": identity, "action": request["action"], "status": event.get("status"),
                            "arguments": request.get("arguments", {}), "purpose": request.get("purpose"),
                            "event_path": str(run / "events" / (identity + ".json"))})
    videos = {}
    for identity, video in state.get("videos", {}).items():
        execution = video.get("execution", {})
        # Keep unknowns; elapsed includes other overhead and is not a substitute.
        seconds = execution.get("generation_seconds")
        if seconds is None and isinstance(execution.get("receipt"), dict):
            seconds = execution["receipt"].get("generation_seconds")
        videos[identity] = {k: video.get(k) for k in ("parent", "prompt", "sha256", "job_id", "duration_seconds", "path", "imported")}
        videos[identity]["generation_seconds"] = seconds
    feedback = []
    for identity, value in state.get("evaluations", {}).items():
        feedback.append({"id": identity, "video_id": value.get("video_id"), "protocol": value.get("protocol"),
                         "state_pointer": "/evaluations/" + identity,
                         "main_scores": value.get("report", {}).get("main_scores"),
                         "historical_outcome": value.get("outcome"),
                         "scope": "Saved online judgment; not independent final scoring."})
    if any(not c["exposure_recorded"] for c in calls):
        issues.append("Some calls have no bound exposure receipt; no retrospective claim of visibility/adoption is made.")
    config = state.get("config", {})
    generated = list({v["job_id"]: v for k, v in videos.items()
                      if k != "source" and v.get("job_id") and not v.get("imported")}.values())
    known_costs = [v["generation_seconds"] for v in generated
                   if type(v.get("generation_seconds")) in {int, float} and v["generation_seconds"] >= 0]
    return {"schema": "experience-use-v1", "run": str(run), "state_sha256": digest(state_file),
        "status": state.get("status"), "final": state.get("final"), "delivery_candidate": state.get("delivery_candidate"),
        "request": state.get("request", {}).get("text"), "knowledge_snapshot_sha256": digest(snapshot_path) if snapshot_path.exists() else None,
        "knowledge_index": index, "calls": calls, "surfaces": surfaces, "reads": reads, "model_references": mentions,
        "actions": actions, "videos": videos, "online_feedback": feedback,
        "counts": {"planner_generate_operations": sum(a["action"] == "generate" for a in actions),
                   "accepted_generation_requests": state.get("generation_requests"),
                   "returned_generated_candidates": len(generated), "saved_online_reviews": len(feedback)},
        "generation_cost": {"known_seconds": sum(known_costs), "known_candidates": len(known_costs),
                            "unknown_candidates": len(generated) - len(known_costs),
                            "scope": "Returned candidates with recorded generation time; failed jobs and LLM cost are not inferred."},
        "cohort": {"workflow": config.get("workflow", "historical"), "planner_model": config.get("model"),
                   "reasoning_effort": config.get("reasoning_effort"),
                   "catalog_revision": snapshot.get("curated_catalog", {}).get("revision"),
                   "online_protocols": sorted({v["protocol"] for v in feedback if v.get("protocol")})},
        "working_material": {"state_path": str(state_file), "pointers": ["/notes", "/workspace"]},
        "issues": issues, "recording_warnings": state.get("experience_recording_warnings", []),
        "scope": "Factual links and attributed judgments. Effectiveness and causal credit require semantic review and suitable comparisons."}


def export_batch(manifest_path, output):
    manifest_path, output = Path(manifest_path).resolve(), Path(output).resolve()
    manifest = read_json(manifest_path)
    if manifest.get("purpose") != "development_maintenance" or not isinstance(manifest.get("runs"), list):
        raise ValueError("Use an explicit development_maintenance manifest with a runs list")
    for row in manifest["runs"]:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", str(row.get("id", ""))):
            raise ValueError("Each run needs a safe ID and an explicit directory path")
    run_paths = [(manifest_path.parent / r["path"]).resolve() for r in manifest["runs"]]
    if len({r["id"] for r in manifest["runs"]}) != len(run_paths) or len(set(run_paths)) != len(run_paths):
        raise ValueError("Duplicate run ID or directory")
    if any(output == p or output.is_relative_to(p) or p.is_relative_to(output) for p in run_paths):
        raise ValueError("Export output must be separate from every source run")
    if output.exists():
        raise ValueError("Choose a new output directory; prior maintenance records are preserved")
    output.mkdir(parents=True)
    records, per_entry = [], {}
    for row, path in zip(manifest["runs"], run_paths):
        base = {"id": row["id"], "run": str(path), "data_role": row.get("data_role", "unspecified")}
        if row.get("data_role") != "development":
            records.append({**base, "status": "excluded", "reason": "Only explicitly development-authorized material enters maintenance."})
            continue
        try:
            report = project_run(path)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            records.append({**base, "status": "unavailable", "reason": type(exc).__name__})
            continue
        report["run_id"] = row["id"]
        write_json(output / "runs" / (row["id"] + ".json"), report)
        records.append({**base, "status": "included", "run_status": report["status"], "report": "runs/" + row["id"] + ".json",
                        "knowledge_snapshot_sha256": report["knowledge_snapshot_sha256"], "cohort": report["cohort"],
                        "counts": report["counts"], "generation_cost": report["generation_cost"], "issues": report["issues"]})
        for identity, entry in report["knowledge_index"].items():
            content_key = entry.get("sha256") or ("unknown-in-" + row["id"])
            key = identity + "@" + content_key + "@" + str(entry.get("version"))
            stats = per_entry.setdefault(key, {"id": identity, "sha256": entry.get("sha256"), "version": entry.get("version"),
                "available_in_runs": [], "read_events": 0, "answered_calls_with_exposure": 0,
                "prepared_or_uncertain_calls_with_exposure": 0, "literal_reference_events": 0})
            stats["available_in_runs"].append(row["id"])
            stats["read_events"] += sum(r.get("id") == identity for r in report["reads"])
            exposed = {(r["call_id"], r["call_status"]) for r in report["surfaces"] if r["id"] == identity}
            stats["answered_calls_with_exposure"] += sum(status == "response_recorded" for _, status in exposed)
            stats["prepared_or_uncertain_calls_with_exposure"] += sum(status != "response_recorded" for _, status in exposed)
            stats["literal_reference_events"] += len({r["event_id"] for r in report["model_references"] if identity in r["experience_ids"]})
    summary = {"schema": "experience-batch-v1", "batch_id": manifest.get("batch_id"),
        "manifest_sha256": digest(manifest_path), "manifest_path": str(manifest_path),
        "exporter_sha256": digest(__file__), "specified_runs": len(records),
        "record_counts": dict(Counter(r["status"] for r in records)),
        "run_status_counts": dict(Counter(r.get("run_status") for r in records if r["status"] == "included")),
        "runs": records, "experience_usage": list(per_entry.values()),
        "limits": ["Counts are exposure/read/reference events, not effectiveness scores.",
                   "Absent historical receipts are missing evidence, not zero actual attention.",
                   "Scores remain in per-run protocol/version cohorts; no pooled quality estimate is computed.",
                   "No independent scoring, semantic inference, rendering or publication was executed."]}
    write_json(output / "batch.json", summary)
    lines = ["# Experience maintenance batch", "", f"Specified runs: {len(records)}. Records: {summary['record_counts']}.", "",
             "| Run | Inclusion | Recorded state | Detail |", "|---|---|---|---|"]
    for r in records:
        link = f"[Record]({r['report']})" if r.get("report") else r.get("reason", "")
        lines.append(f"| {r['id']} | {r['status']} | {r.get('run_status', 'unknown')} | {link} |")
    lines += ["", "[Full factual summary](batch.json)", "", *summary["limits"], "",
              "Review model references in context; they have not been classified as adoption. Record any retrospective interpretation separately, with source events and author identity. Stage proposed content edits for user review."]
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
