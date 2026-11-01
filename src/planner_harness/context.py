"""Presentation only: retain raw state and expose exact retrieval paths."""
from __future__ import annotations

import copy


def video_brief(video):
    return {key: video[key] for key in
            ("parent", "duration_seconds", "fps", "frames", "width", "height", "imported", "replay_provenance")
            if key in video}


def feedback_summary(identity, value):
    """Older online feedback is quoted, never rejudged or ranked."""
    if value.get("protocol") == "lha-creative-review-v1":
        report = value["report"]
        return {"video_id": value["video_id"], "protocol": value["protocol"], "usage": value["usage"],
                "main_scores": report["main_scores"], "comparisons": report["comparisons"],
                "unassessed": report["unassessed"],
                "open": {"action": "history", "arguments": {"feedback": identity}}}
    outcome, feedback = value.get("outcome", {}), value.get("feedback", {})
    return {
        "video_id": value.get("video_id", value.get("candidate")),
        "protocol": value["protocol"], "usage": value.get("usage"),
        "question": value.get("question", ""), "identity_map": copy.deepcopy(value.get("identity_map", {})),
        "view": "Earlier feedback summary; detailed findings remain available through history.",
        "summary": feedback.get("summary", outcome.get("summary", "")),
        "unresolved": copy.deepcopy(outcome.get("unresolved", [])),
        "unknown_findings": [copy.deepcopy(f) for f in outcome.get("findings", []) if f.get("verdict") == "unknown"],
        "comparison_unknowns": [{"against": c.get("against"), "unknowns": copy.deepcopy(c["unknowns"])}
                                for c in outcome.get("comparisons", []) if c.get("unknowns")],
        "open": {"action": "history", "arguments": {"feedback": identity}},
    }


def present(payload, state, knowledge):
    """Compact a copied legacy payload without modifying evidence or raw history."""
    payload["task"] = {**payload["task"], "source": video_brief(payload["task"]["source"])}
    payload["videos"] = {identity: {**video_brief(video),
                                  "open": {"action": "video", "arguments": {"id": identity}}}
                         for identity, video in state.get("videos", {}).items()}
    evaluations = state.get("evaluations", {})
    latest = next(reversed(evaluations), None)
    payload["evaluations"] = {
        identity: feedback_summary(identity, value)
        if identity != latest and value.get("protocol") in {"lha-online-critic-v1", "lha-online-critic-rsi-v1", "lha-creative-review-v1"}
        else copy.deepcopy(value)
        for identity, value in evaluations.items()
    }
    for event in payload["recent_operations"]:
        result = event.get("result", {})
        if event.get("request", {}).get("action") == "tool_result" and result.get("status") == "complete":
            identity = result.get("video_id")
            if identity in state.get("videos", {}) and result.get("video") == state["videos"][identity]:
                result["video"] = copy.deepcopy(payload["videos"][identity])
            reference = result.get("payload_reference")
            if reference and reference.get("key") in payload["evaluations"]:
                reference["note"] = "See evaluations; older online reviews have an explicit history link for all findings."
    if not state.get("workspace", {}).get("summary") and not state.get("workspace", {}).get("nodes"):
        payload.pop("workspace", None)
    payload["knowledge_entrances"] = knowledge.overview()
    payload["available_observations"] = [
        {"id": o["observation_id"], "video": o.get("video_id", "source"),
         "interval": o.get("requested_interval"), "crop": o["frames"][0].get("crop") if o.get("frames") else None}
        for o in state.get("observations", [])
    ]
    if state["config"].get("workflow") == "creative_loop_v1":
        payload["workflow"] = "creative_loop_v1"
        payload["delivery_candidate"] = state.get("delivery_candidate")
        profile = state["config"]["execution"]["critic"]["frozen_profile"]
        payload["execution_profile"]["critic"] = {
            "protocol": profile["protocol_id"], "profile_sha256": profile["sha256"],
            "dimensions": profile["dimensions"], "scale": "0-4 integers; unknown is null",
            "use": "Optional single report per candidate; inspect video evidence yourself for further questions."}
        for identity, value in payload["evaluations"].items():
            if value.get("protocol") != "lha-creative-review-v1":
                raise ValueError("Non-creative evaluation in creative-loop context")
            # Keep the full report; media transport paths stay in the retrievable record.
            if "evidence" in value:
                value["evidence"] = [{k: e[k] for k in ("id", "video_id", "timestamp_seconds", "kind")}
                                     for e in value["evidence"]]
            value["open"] = {"action": "history", "arguments": {"feedback": identity}}
    payload["context_policy"] = (
        "Original task, optional notes and latest review remain available. Earlier online reviews are attributed summaries "
        "with unknowns and history links; raw findings are unchanged. Video provenance opens through video. "
        "Latest 10 operations remain visible, with repeated video metadata referenced. "
        "Source overview and the latest observation group are attached; observe can reopen saved observations. "
        "Same video times do not establish motion alignment."
    )
    return payload


def attachments(state):
    observations = state.get("observations", [])
    focus = state.get("observation_focus", {})
    lookup = {o["observation_id"]: o for o in observations}
    if focus.get("observations_count") == len(observations) and all(i in lookup for i in focus.get("ids", [])):
        selected = observations[:1] + [lookup[i] for i in focus.get("ids", [])]
    else:
        selected = observations[:1] + observations[-1:]
    images, mapping = [], []
    for observation in selected:
        for frame in observation["frames"]:
            if frame["path"] not in images:
                images.append(frame["path"])
                mapping.append({"attachment": len(images), "observation_id": observation["observation_id"],
                                "video_id": observation.get("video_id", "source"), **frame})
    references = state.get("reference_images", [state["reference_image"]] if state.get("reference_image") else [])
    for reference in references:
        if reference["path"] not in images:
            images.append(reference["path"])
            mapping.append({"attachment": len(images), "kind": "knowledge reference, not source-video evidence", **reference})
    return images, mapping
