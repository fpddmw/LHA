"""Grounded Wiki reading and replay feedback for bounded knowledge revision."""
from pathlib import Path

from .common import load, sha
from .ledger import digest


def evidence_images(packet, args, root):
    """Read only images actually available at a recorded development decision."""
    from .rsi_data import local_path
    from .rsi_replay import prefix
    record = next((r for r in packet["development"]["records"] if r["id"] == args.get("id")), None)
    if not record:
        raise ValueError("Choose a collected development run")
    decision = next((d for d in record.get("decisions", []) if d["id"] == args.get("decision")), None)
    if not decision:
        raise ValueError("Choose a decision ID listed in this run")
    path = local_path(decision["input"], root)
    if sha(path) != decision["input_sha256"]:
        raise ValueError("Development decision changed")
    saved, _, _, _ = prefix(path, root)
    requested = args.get("videos", ["source"])
    if not isinstance(requested, list) or not 1 <= len(requested) <= 2:
        raise ValueError("Choose one or two videos for a recorded frame comparison")
    limit = args.get("frames_per_video", 3)
    if type(limit) is not int or not 1 <= limit <= 4:
        raise ValueError("Choose one to four recorded frames per video")
    images = []
    available = sorted({i.get("video_id", "source") for i in saved["images"]})
    for video in requested:
        frames = [i for i in saved["images"] if i.get("video_id", "source") == video]
        indices = sorted({round(i*(len(frames)-1)/max(1, limit-1)) for i in range(min(limit, len(frames)))})
        for index in indices:
            frame = frames[index]
            if sha(frame["path"]) != frame["sha256"]:
                raise ValueError("Recorded frame changed")
            images.append({**frame, "run_id": record["id"], "decision_id": decision["id"],
                           "video_id": video, "attachment": len(images)+1})
    return {"images": images, "available_videos": available,
            "missing_videos": [v for v in requested if v not in available],
            "scope": "Recorded sampled frames, not continuous motion evidence or a newly observed outcome."}


def replay_feedback(result_path, proposal, *, root):
    """Bind actual reads and terminal decisions to the exact tested version."""
    from .rsi_data import verify_seal
    path = Path(result_path)
    result = verify_seal(load(path))
    rows = []
    for sample in result.get("samples", []):
        trace_path = path.parent / digest(sample["decision_id"])[:16] / str(sample["sample"]) / sample["arm"] / "result.json"
        trace = load(trace_path)
        if digest(trace.get("decision")) != sample["decision_sha256"]:
            raise ValueError("Replay feedback decision differs from its sample")
        rows.append({"id": sample["id"], "arm": sample["arm"], "decision_id": sample["decision_id"],
                     "decision": trace.get("decision"), "requirements": trace.get("requirements"),
                     "operations": trace.get("operations", []), "trace": str(trace_path), "trace_sha256": sha(trace_path)})
    return {"proposal": proposal, "replay": str(path), "replay_sha256": sha(path),
            "status": result["status"], "comparisons": result.get("comparisons", []), "samples": rows,
            "scope": "Behavioral diagnostic on exposed decisions. A missed directional target is not proof the decision is wrong. No new video outcome."}


def feedback_view(feedback):
    """Compact initial feedback; full returned reads remain available on demand."""
    return [{"index": i, "status": f["status"], "comparisons": f.get("comparisons", []),
             "proposal_summary": f.get("proposal", {}).get("summary"),
             "samples": [{k: s[k] for k in ("id", "arm", "decision_id", "decision")} for s in f.get("samples", [])],
             "read": {"action": "read_feedback", "arguments": {"index": i}}} for i, f in enumerate(feedback)]
