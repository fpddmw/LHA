"""Object-oriented retrieval of saved facts, without ranking or interpretation."""

import copy
import difflib


def candidate(state, identity, *, raw=False, review=True):
    videos = state.get("videos", {})
    if identity not in videos:
        raise ValueError(f"Unknown video {identity!r}; available: {', '.join(videos)}")
    if raw:
        return copy.deepcopy(videos[identity])
    source = videos[identity]
    row = {"id": identity, **{k: copy.deepcopy(source[k]) for k in
           ("parent", "prompt", "frames", "fps", "duration_seconds", "width", "height", "imported") if k in source}}
    effective = source.get("execution", {}).get("effective_prompt")
    if effective and effective != source.get("prompt"):
        row["effective_prompt"] = effective
    if review:
        saved = state.get("reviews", {}).get(identity)
        if saved:
            row["review"] = {k: copy.deepcopy(saved[k]) for k in ("mode", "status", "report", "error") if k in saved}
        else:
            feedback = next((v for v in reversed(list(state.get("evaluations", {}).values()))
                             if v.get("video_id") == identity), None)
            if feedback:
                row["review"] = {"report": copy.deepcopy(feedback.get("report")), "status": "complete"}
    row["raw"] = {"action": "video", "arguments": {"id": identity, "raw": True}}
    return row


def select(state, args):
    if "id" in args and "ids" in args:
        raise ValueError("Choose id or ids for video retrieval")
    identities = args.get("ids", args.get("id", "source"))
    many = isinstance(identities, list)
    if not many:
        identities = [identities]
    if not identities or any(not isinstance(i, str) for i in identities):
        raise ValueError("video accepts id or a nonempty list of IDs; available: " + ", ".join(state["videos"]))
    rows = []
    for identity in dict.fromkeys(identities):
        try:
            rows.append(candidate(state, identity, raw=args.get("raw", False)))
        except ValueError as exc:
            if not many:
                raise
            rows.append({"id": identity, "error": str(exc)})
    if not many:
        return rows[0]
    result = {"candidates": rows}
    if args.get("compare_prompts") and len(rows) == 2 and all("error" not in row for row in rows):
        result["prompt_diff"] = "\n".join(difflib.unified_diff(
            rows[0].get("prompt", "").splitlines(), rows[1].get("prompt", "").splitlines(),
            fromfile=identities[0], tofile=identities[1], lineterm=""))
        result["diff_scope"] = "Exact submitted text; no judgment about the change."
    return result
