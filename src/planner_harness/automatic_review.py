"""One durable Critic review or contextual Planner check per generated candidate."""

import copy
from .common import load
from .execution import immutable, signature


def validate_focus(value, state):
    from .tool_interface import normalize_focus
    value = normalize_focus(value)
    if value is None:
        value = {}
    if isinstance(value, str):
        value = {"focus": value}
    if not isinstance(value, dict) or set(value) - {
        "focus",
        "extra_checks",
        "events",
        "compare_to",
    }:
        raise ValueError("Review focus is text or focus/checks/events/compare_to")
    if not isinstance(value.get("focus", ""), str) or not isinstance(
        value.get("extra_checks", []), list
    ):
        raise ValueError("review_focus.focus must be text; extra_checks accepts text or a list of texts")
    if any(not isinstance(v, str) for v in value.get("extra_checks", [])):
        raise ValueError("review_focus.extra_checks must contain texts, for example ['Check hand contact']")
    comparison = value.get("compare_to")
    if comparison is not None and comparison not in state["videos"]:
        raise ValueError("Unknown compare_to; available videos: " + ", ".join(state["videos"]))
    return copy.deepcopy(
        {
            "focus": value.get("focus", ""),
            "extra_checks": value.get("extra_checks", []),
            "events": value.get("events", []),
            "compare_to": comparison,
        }
    )


def enqueue(harness, candidate, generation):
    state = harness.state
    folder = harness.output / "jobs" / generation["id"]
    focus = load(folder / "review-focus.json")
    if signature(focus) != generation.get("review_focus_sha256"):
        raise ValueError("Recorded review focus changed")
    mode = state["config"]["execution"]["review"]["mode"]
    expected = {
        "generation_sha256": generation["sha256"],
        "candidate": candidate,
        "candidate_sha256": state["videos"][candidate]["sha256"],
        "focus_sha256": signature(focus),
        "mode": mode,
    }
    immutable(folder / "automatic-review.json", expected)
    current = state.setdefault("reviews", {}).get(candidate)
    if current and current["status"] in {"complete", "failed"}:
        return current
    state["pending_review"] = {
        "video_id": candidate,
        "mode": mode,
        "generation": generation["id"],
        "focus": focus,
    }
    state["reviews"][candidate] = {"video_id": candidate, "mode": mode, "status": "pending"}
    if mode == "planner":
        return {"status": "awaiting_planner_review", "video_id": candidate}
    from .execution import request_job

    result = request_job(
        harness,
        "critique",
        {"video": candidate, **focus},
        generation["id"] + "-automatic",
        internal=True,
    )
    state["videos"][candidate]["automatic_review"] = result.get("job_id") or result.get(
        "feedback_id"
    )
    return result


def collected(harness, job, response):
    identity = job["payload"]["video_id"]
    value = {
        "mode": "critic",
        "video_id": identity,
        "status": response["status"],
        "job_id": job["id"],
        "event_id": job["id"] + "-result",
    }
    if response["status"] == "complete":
        value["report"] = copy.deepcopy(response["payload"]["report"])
    else:
        value["error"] = response.get("error")
        value["report"] = None
    harness.state.setdefault("reviews", {})[identity] = value
    if harness.state.get("pending_review", {}).get("video_id") == identity:
        harness.state.pop("pending_review", None)


def capture(harness, response, event_id):
    state = harness.state
    value = response.get("review")
    record = None
    if response.get("action") == "review":
        value = response.get("arguments", {})
    if value is not None and state["config"]["execution"]["review"]["mode"] == "planner":
        if not isinstance(value, dict):
            raise ValueError("Planner review is a text summary with its video_id")
        identity = value.get("video_id", state.get("pending_review", {}).get("video_id"))
        if identity not in state["videos"] or identity == "source":
            raise ValueError("Review an available generated candidate")
        from critic_harness.qualitative import validate

        report = validate({k: copy.deepcopy(v) for k, v in value.items() if k != "video_id"})
        record = {
            "video_id": identity,
            "mode": "planner",
            "status": "complete",
            "report": report,
            "event_id": event_id,
        }
        state.setdefault("reviews", {})[identity] = record
        if state.get("pending_review", {}).get("video_id") == identity:
            state.pop("pending_review", None)
        from .candidate_selection import refresh

        refresh(state)
    if state.get("pending_review", {}).get("mode") == "planner" and response.get("action") in {
        "generate",
        "finish",
    }:
        return {
            "status": "review_required",
            "video_id": state["pending_review"]["video_id"],
            "message": "Check this generated result before continuing. Include review beside this action, or inspect with observe first.",
        }
    return record
