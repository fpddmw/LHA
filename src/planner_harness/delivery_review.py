"""Planner-owned delivery after per-generation checking; final adds no review."""

import json
from pathlib import Path
from .common import load, sha

PROTOCOL = "creative-delivery-v6-planner-choice"


def before_finish(harness, args, event_id):
    identity = args.get("video")
    if identity not in harness.state["videos"] or identity == "source":
        raise ValueError("Choose a generated candidate")
    if not isinstance(args.get("message"), str) or not args["message"].strip():
        raise ValueError("Describe your delivery choice briefly")
    proof = {
        "protocol": PROTOCOL,
        "planner_event_id": event_id,
        "candidate_id": identity,
        "candidate_sha256": harness.state["videos"][identity]["sha256"],
        "review_mode": harness.state["config"]["execution"]["review"]["mode"],
    }
    harness.state["delivery_candidate"] = identity
    from .candidate_selection import refresh

    refresh(harness.state)
    return {"status": "confirmed", "proof": proof}


def context(state):
    return {
        "protocol": PROTOCOL,
        "candidate": state.get("delivery_candidate"),
        "use": "Choose the final candidate yourself. Final delivery reuses completed per-generation checks and submits no review.",
    }


def validated_feedback(run, state, identity, job_id):
    job = state["jobs"][job_id]
    response = load(Path(run) / "jobs" / job_id / "response.json")
    if response.get("status") != "complete" or response.get("request_sha256") != job["sha256"]:
        raise ValueError("Original review response changed")
    feedback = response["payload"]
    if feedback.get("video_id") != identity or feedback != state["evaluations"][job_id]:
        raise ValueError("Collected review changed")
    from critic_harness.qualitative import validate

    validate(feedback["report"])
    return feedback


def verify(run, state):
    from .continuation import completion_pending
    if completion_pending(state):
        raise ValueError("Fixed-budget delivery still has unused generation allowance")
    run = Path(run)
    proof = state.get("final", {}).get("delivery_review", {})
    identity = state["final"].get("video")
    if (
        proof.get("protocol") != PROTOCOL
        or proof.get("candidate_id") != identity
        or proof.get("candidate_sha256") != state["videos"][identity]["sha256"]
    ):
        raise ValueError("Delivery does not match the Planner choice")
    event = proof["planner_event_id"]
    directory = run / "calls" / event
    from .json_output import decode_object

    decision = decode_object((directory / "response.txt").read_text())
    args = decision.get("arguments", {})
    if (
        decision.get("action") != "finish"
        or args.get("video") != identity
        or args.get("stop_reason", "satisfied") != "satisfied"
    ):
        raise ValueError("Delivery is not the recorded Planner decision")
    transport = directory / "transport"
    if not (transport / "returned.json").exists():
        raise ValueError("Delivery has no returned Planner response")
    returned = load(transport / "returned.json")
    attempt = transport / "attempts" / f"{returned['attempt']:02d}" / "response.txt"
    digest = sha(directory / "response.txt")
    if (
        returned["sha256"] != digest
        or sha(transport / "response.txt") != digest
        or sha(attempt) != digest
    ):
        raise ValueError("Delivery differs from the original returned Planner response")
    prepared, sent = load(directory / "input.json"), load(transport / "input.json")
    if any(prepared[key] != sent[key] for key in ("system_prompt", "user_text")):
        raise ValueError("Delivery input differs from the actual Planner input")
    if args.get("message") != state["final"].get("message"):
        raise ValueError("Delivery explanation differs from the Planner response")
    if state.get("pending_review"):
        raise ValueError("The last generated result still needs its contextual Planner check")
    return proof
