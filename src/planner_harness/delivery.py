"""Separate model-led delivery from a bounded experimental run's termination."""
from pathlib import Path
import copy

from .common import load, sha


def completion_mode(limit, mode=None):
    if limit is not None and (type(limit) is not int or limit < 0):
        raise ValueError("Generation limit must be a nonnegative integer or null")
    mode = mode or ("delivery" if limit is None else "bounded_experiment")
    if mode not in {"delivery", "bounded_experiment"}:
        raise ValueError("Choose delivery or bounded_experiment completion mode")
    if mode == "bounded_experiment" and limit is None:
        raise ValueError("A bounded experiment needs an explicit generation limit")
    return mode


def is_delivery(state):
    # Existing immutable experiment snapshots retain their original semantics.
    return (state["config"].get("workflow") == "creative_loop_v1"
            or state["config"].get("completion_mode") == "delivery")


def finish_status(state, reason, video):
    if not is_delivery(state):
        return "complete"
    if reason == "budget":
        return "budget_exhausted"
    if reason == "execution_failure":
        return "execution_failed"
    if reason == "no_promising_attempt" or video in {None, "source"}:
        return "delivery_blocked"
    if reason != "satisfied":
        raise ValueError("Delivery finish needs an explicit stopping reason")
    return "complete"


def continue_budget_stop(state):
    """Explicit operator correction; preserve past calls, candidates and frozen Critic."""
    if state["config"].get("workflow") == "creative_loop_v1":
        if (state.get("status") != "budget_exhausted" and state.get("final", {}).get("stop_reason") != "budget") or state.get("pending_event") or state.get("pending_tool"):
            raise ValueError("Continue a resource pause only after pending work is resolved")
        previous = copy.deepcopy(state["config"])
        state["config"].update(completion_mode="delivery", max_generations=None, max_turns=None)
        state.setdefault("delivery_continuations", []).append({"previous_config": previous,
            "next_config": copy.deepcopy(state["config"]), "reason": "Operator explicitly reopened the resource pause."})
        state["status"] = "budget_exhausted"
        return
    if state.get("final", {}).get("stop_reason") != "budget" or state.get("pending_event") or state.get("pending_tool"):
        raise ValueError("Continue only a resolved budget stop with no pending work")
    config = state["config"]
    rsi = config.get("rsi", {})
    if rsi.get("cycle") or rsi.get("cycle_sha256"):
        raise ValueError("A frozen experimental cycle cannot be converted to a delivery run")
    seeds = rsi.get("seed_schedule")
    sequence = None
    if seeds is not None:
        if len(seeds) < 2 or any(type(s) is not int for s in seeds):
            raise ValueError("The finite seed schedule needs an explicit continuation policy")
        step = seeds[1] - seeds[0]
        if step < 0 or seeds != [seeds[0] + step * i for i in range(len(seeds))]:
            raise ValueError("The recorded seeds do not define an arithmetic continuation")
        sequence = {"start": seeds[0], "step": step}
    previous = copy.deepcopy(config)
    config.update(completion_mode="delivery", max_generations=None, max_turns=None)
    if sequence is not None:
        rsi.pop("seed_schedule")
        rsi["seed_sequence"] = sequence
    config["run_instructions"] = (
        "Operator correction: continue the original task toward a suitable delivery. "
        "The previous budget stop was not delivery. There is no fixed "
        "generation or turn count. Use the retained candidates, observations and reviews. "
        "Choose input, prompt, further work and delivery yourself. If the task is blocked, "
        "retain a provisional candidate and report it as incomplete. The original request, "
        "renderer settings and frozen Critic remain unchanged."
    )
    state.setdefault("delivery_continuations", []).append({"previous_config": previous,
        "next_config": copy.deepcopy(config), "reason": "User required delivery rather than a three-generation stop."})
    state["status"] = "budget_exhausted"


def verify_delivery(run):
    """Verify a delivery claim and its artifacts, without imposing a Critic score gate."""
    run = Path(run)
    state = load(run / "state.json")
    final = state.get("final", {})
    if state["status"] != "complete" or final.get("stop_reason") != "satisfied":
        raise ValueError("Task has not reached model-led delivery: " + str(final.get("stop_reason", state["status"])))
    selected = final.get("video")
    videos = state.get("videos", {})
    if selected not in videos or selected == "source":
        raise ValueError("Delivery needs a selected generated candidate")
    candidates = {k: v for k, v in videos.items() if k != "source"}
    for video in candidates.values():
        if sha(video["path"]) != video["sha256"]:
            raise ValueError("Candidate artifact changed")
    if state["config"].get("rsi"):
        reviewed = set()
        for identity, job in state.get("jobs", {}).items():
            if job["kind"] != "critique":
                continue
            response_path = run / "jobs" / identity / "response.json"
            if response_path.exists():
                response = load(response_path)
                if response.get("status") == "complete" and response.get("request_sha256") == job["sha256"]:
                    reviewed.add(job["payload"]["video_id"])
        if not set(candidates) <= reviewed:
            raise ValueError("Generated candidates still need completed automatic reviews")
    return {"status": "delivered", "selected": selected, "candidates": list(candidates),
            "selected_video": videos[selected], "final": final,
            "scope": "Planner delivery judgment; unresolved Critic verdicts remain explicit."}
