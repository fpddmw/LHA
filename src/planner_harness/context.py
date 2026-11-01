"""Presentation only: retain raw state and expose exact retrieval paths."""
from __future__ import annotations

import copy
import json


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
        from .continuation import view as continuation_view
        payload['continuation'] = continuation_view(state)
        payload.pop('resource_status', None)
        execution = state['config']['execution']
        renderer = execution.get('renderer', {})
        # Explicit operational projection: never dump operator limits or pressure settings.
        payload['execution_profile'] = {k: copy.deepcopy(execution[k]) for k in ('mode','experience_mode','seed_sequence') if k in execution}
        payload['execution_profile']['renderer'] = {k:copy.deepcopy(renderer[k]) for k in ('backend','seed','output') if k in renderer}
        payload['execution_profile']['renderer']['generation'] = {k:copy.deepcopy(v) for k,v in renderer.get('generation',{}).items()
            if k in {'num_inference_steps','guidance_mode','max_image_size','negative_prompt','prompt_enhancer'}}
        payload["workflow"] = "creative_loop_v1"
        payload["delivery_candidate"] = state.get("delivery_candidate")
        profile = state["config"]["execution"]["critic"]["frozen_profile"]
        payload["execution_profile"]["critic"] = {
            "protocol": profile["protocol_id"], "profile_sha256": profile["sha256"],
            "dimensions": profile["dimensions"], "scale": "0-4 integers; unknown is null",
            "definitions": {"action": "read", "arguments": {"targets": [{"id": "score-definitions"}]}},
            "use": "Optional work review. A satisfied finish proposes delivery with a reused valid matching report, or one review if absent. A later Planner finish after the full report for that proposal confirms without a grade threshold."}
        from .delivery_review import context as delivery_context
        payload['delivery_review'] = delivery_context(state)
        for identity, value in payload["evaluations"].items():
            if value.get("protocol") != "lha-creative-review-v1":
                raise ValueError("Non-creative evaluation in creative-loop context")
            # Keep the full report; media transport paths stay in the retrievable record.
            if "evidence" in value:
                value["evidence"] = [{k: e[k] for k in ("id", "video_id", "timestamp_seconds", "kind")}
                                     for e in value["evidence"]]
            value["open"] = {"action": "history", "arguments": {"feedback": identity}}
        creative_view(payload, state)
    payload["context_policy"] = (
        "Original task, optional notes and latest review remain available. Earlier online reviews are attributed summaries "
        "with unknowns and history links; raw findings are unchanged. Video provenance opens through video. "
        "Creative tasks show the newest result and compact prior operations with explicit archive access. "
        "Source overview and the latest observation group are attached; observe can reopen saved observations. "
        "Same video times do not establish motion alignment."
    )
    return payload


def creative_view(payload, state):
    """A bounded working view; archive bytes and model-owned notes stay untouched."""
    events = state.get("events", [])
    recent = payload["recent_operations"]
    for event in recent[:-1]:
        event_id = event["event_id"]
        request = event.get("request", {})
        event.clear()
        event.update(event_id=event_id, action=request.get("action"),
                     open={"action": "history", "arguments": {"event_id": event_id}})
    payload["read_receipts"] = {"count": len(state["reads"]),
        "recent": dict(list(state["reads"].items())[-8:]),
        "open": {"action": "history", "arguments": {"catalog": "reads"}}}
    payload["archived_operation_index"] = {
        "count": max(0, len(events) - len(recent)),
        "open": {"action": "history", "arguments": {"catalog": "events"}}}
    latest = next(reversed(state.get("evaluations", {})), None)
    for key, value in list(payload["evaluations"].items()):
        if key == latest:
            continue
        report = state["evaluations"][key]["report"]
        payload["evaluations"][key] = {
            "video_id": state["evaluations"][key]["video_id"],
            "main_scores": {d: {"status": r["status"], "score": r["score"],
                "evidence_refs": r["evidence_refs"], "reason_excerpt": r["reason"][:240],
                "reason_excerpt_is_complete": len(r["reason"]) <= 240,
                "limitations": r["limitations"]}
                for d, r in report["main_scores"].items()},
            "unassessed": report["unassessed"],
            "open": {"action": "history", "arguments": {"feedback": key}},
            "view": "Attributed excerpts; full reasons and limitations remain in the original report."}
    # Keep the just-returned result within its share of the context budget. The
    # exact result is retrievable by event ID, with explicit pagination.
    if recent:
        newest = recent[-1]
        result = newest.get("result", {})
        limit = max(2048, state["config"]["max_context_chars"] // 4)
        if "materials" not in result and len(json.dumps(result, ensure_ascii=False)) > limit:
            from .common import page
            newest["result"] = {"view": "First page of a large result; omitted content has not been supplied.",
                "page": page(json.dumps(result, ensure_ascii=False, indent=2), max_chars=min(limit // 2, 12000), split_long_lines=True),
                "open": {"action": "history", "arguments": {"event_id": newest["event_id"], "result_only": True}}}
    payload["history_catalogs"] = ["events", "reads", "observations", "evaluations", "videos"]


def fit_creative(payload, state, system_chars):
    """Remove older view entries, never the latest report/task/notes or raw data."""
    limit = state["config"]["max_context_chars"]
    payload["archive_access"] = {"note": "Older view entries may be omitted to fit capacity; exact records remain available.",
        "counts": {"videos": len(state["videos"]), "evaluations": len(state["evaluations"]),
                   "observations": len(state["observations"]), "events": len(state["events"])},
        "open": {"action": "history", "arguments": {"catalog": "events"}}}
    def fits():
        return system_chars + len(json.dumps(payload, ensure_ascii=False, indent=2)) <= limit
    for field in ("recent_operations", "available_observations"):
        while not fits() and len(payload.get(field, [])) > 1:
            payload[field].pop(0)
    evaluations = payload.get("evaluations", {})
    while not fits() and len(evaluations) > 1:
        del evaluations[next(iter(evaluations))]
    videos = payload.get("videos", {})
    protected = {"source", state.get("delivery_candidate"), state.get("final", {}).get("video")}
    if videos:
        protected.add(next(reversed(videos)))
    for key in list(videos):
        if fits():
            break
        if key not in protected:
            del videos[key]
    return payload


def history_catalog(state, name):
    if name == "reads":
        return state["reads"]
    if name == "events":
        return [{"event_id": e["event_id"], "action": e.get("request", {}).get("action"),
                 "status": e["status"], "open": {"action": "history", "arguments": {"event_id": e["event_id"]}}}
                for e in state["events"]]
    if name == "videos":
        return {k: {**video_brief(v), "open": {"action": "video", "arguments": {"id": k}}} for k, v in state["videos"].items()}
    if name == "observations":
        return [{"id": o["observation_id"], "video": o.get("video_id", "source"),
                 "interval": o.get("requested_interval"), "open": {"action": "observe", "arguments": {"observation": o["observation_id"]}}}
                for o in state["observations"]]
    if name == "evaluations":
        return {k: feedback_summary(k, v) for k, v in state["evaluations"].items()}
    raise ValueError("Choose events, reads, videos, observations or evaluations")


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
