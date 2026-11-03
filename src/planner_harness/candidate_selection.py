"""Precommitted deterministic selection; unknown dimensions remain explicit."""

import copy, time
from .execution import signature
from .integrity import IntegrityError

DEADLINE = "planner-choice-then-latest-generated-v2"


def _projection(state):
    candidates = []
    for identity, video in state.get("videos", {}).items():
        if identity == "source" or video.get("imported"):
            continue
        review = state.get("reviews", {}).get(identity, {})
        candidates.append(
            {
                "id": identity,
                "video_sha256": video["sha256"],
                "review_status": review.get("status", "pending"),
                "review_mode": review.get(
                    "mode", state["config"]["execution"].get("review", {}).get("mode", "critic")
                ),
            }
        )
    preferred = state.get("delivery_candidate")
    selected = next((r["id"] for r in candidates if r["id"] == preferred), None)
    origin = "planner_choice" if selected else "latest_generated_fallback"
    if selected is None and candidates:
        selected = candidates[-1]["id"]
    return {
        "policy": DEADLINE,
        "candidates": candidates,
        "preferred": preferred,
        "selected": selected,
        "origin": origin,
        "review_completed": next(
            (r["review_status"] == "complete" for r in candidates if r["id"] == selected), False
        ),
    }


def refresh(state):
    clock = state.get("online_clock", {})
    if clock and (clock.get("frozen_unix") or time.time() >= clock["deadline_unix"]):
        return
    projection = _projection(state)
    body = {**projection, "recorded_unix": time.time()}
    state["deadline_selection"] = {**body, "sha256": signature(body)}


def deadline_choice(state):
    clock = state.get("online_clock", {})
    if clock.get("frozen_unix") is None or clock["frozen_unix"] < clock.get(
        "deadline_unix", float("inf")
    ):
        raise IntegrityError(
            "Deadline delivery requires a persisted freeze at or after the original deadline"
        )
    return recorded_choice(state)


def recorded_choice(state):
    """Read the committed candidate choice, retaining its original provenance."""
    record = state.get("deadline_selection")
    if not record or not record.get("selected"):
        return None
    body = {k: v for k, v in record.items() if k != "sha256"}
    if signature(body) != record["sha256"] or {
        k: v for k, v in body.items() if k != "recorded_unix"
    } != _projection(state):
        raise IntegrityError("Precommitted deadline selection changed")
    if body["recorded_unix"] > state.get("online_clock", {}).get("deadline_unix", float("inf")):
        raise IntegrityError("Deadline selection was not committed before the deadline")
    return copy.deepcopy(record)
