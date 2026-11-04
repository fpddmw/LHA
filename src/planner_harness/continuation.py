"""Approximate resource awareness without favoring continuation or delivery."""

from __future__ import annotations

import copy
import math

from .common import load, sha
from .execution import immutable, signature
from .resources import MAX_GENERATIONS

VERSION = "creative-continuation-v5"
FIXED_BUDGET = "fixed_generation_budget"
PRESSURE = {
    "exploration": "There is room to develop and evaluate your proposal within the task budget.",
    "continuation": "Some of the task budget has been used. Further attempts remain available.",
    "deliberate": "The task budget is more limited. Choose your next action using the task requirements and the results so far.",
    "strong": "The task budget is getting tight. Focus the available resources on the changes or comparisons that matter most to the task.",
    "frozen": "Further generation is unavailable. You can still inspect and compare the existing candidates and choose the task outcome.",
}


def configure(state, supplied=None):
    resource_limit = (
        state["config"].get("resource_policy", {}).get("max_generations", MAX_GENERATIONS)
    )
    policy = {
        "version": VERSION,
        "hard_generation_limit": resource_limit,
        "phase_fractions": [0.4, 0.6, 0.8],
        "completion_policy": "model_choice",
    }
    supplied = copy.deepcopy(supplied or {})
    if set(supplied) - set(policy):
        raise ValueError("Unknown operator continuation policy setting")
    if supplied.get("hard_generation_limit", "missing") is None:
        supplied.pop("hard_generation_limit")
    policy.update(supplied)
    if policy["completion_policy"] not in {"model_choice", FIXED_BUDGET}:
        raise ValueError("Unknown Planner completion policy")
    if policy["version"] != VERSION or policy["phase_fractions"] != [0.4, 0.6, 0.8]:
        raise ValueError("Use the approved fractional continuation schedule")
    explicit = policy["hard_generation_limit"]
    if type(explicit) is not int or explicit < 1 or explicit != resource_limit:
        raise ValueError("Conflicting operator generation limits")
    state["config"]["continuation_policy"] = policy
    state["config"]["max_generations"] = None
    return policy


def usage(state):
    generated = {
        v.get("job_id"): v
        for k, v in state["videos"].items()
        if k != "source" and not v.get("imported")
    }
    requests = {
        k: j
        for k, j in state.get("jobs", {}).items()
        if j["kind"] == "generate"
        and (
            state["config"].get("resource_policy", {}).get("version") != "creative-resources-v2"
            or k in state.get("submitted_generation_ids", [])
        )
    }
    outcomes = state.get("render_outcomes", {})
    failures = [
        k
        for k, v in outcomes.items()
        if k in requests and v["status"] == "failed" and not v.get("uncertain")
    ]
    uncertain = {k for k, v in state.get("unresolved_jobs", {}).items() if k in requests}
    uncertain.update(k for k, v in outcomes.items() if k in requests and v.get("uncertain"))
    times = []
    for video in generated.values():
        value = video.get("execution", {}).get("generation_seconds")
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        ):
            times.append(value)
    for key in failures:
        value = outcomes[key].get("generation_seconds")
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        ):
            times.append(value)
    return {
        "generated_candidates": len(generated),
        "submitted_render_requests": len(requests),
        "failed_render_attempts": len(failures),
        "uncertain_render_attempts": len(uncertain),
        "pending_or_uncollected_render_requests": max(
            0, len(requests) - len(generated) - len(failures) - len(uncertain)
        ),
        "known_rendering_elapsed_seconds": sum(times),
        "render_cost_records_missing": len(generated) + len(failures) + len(uncertain) - len(times),
        "elapsed_time_scope": "Known rendering wall time from receipts; failed/uncertain costs may be unknown. This is not exact GPU compute time or monetary cost.",
    }


def phase(state):
    policy = state["config"]["continuation_policy"]
    n = usage(state)["submitted_render_requests"]
    if n >= policy["hard_generation_limit"]:
        return "frozen"
    p = n / policy["hard_generation_limit"]
    return (
        "exploration"
        if p < 0.4
        else "continuation"
        if p < 0.6
        else "deliberate"
        if p < 0.8
        else "strong"
    )


def view(state):
    policy = state["config"]["continuation_policy"]
    facts = usage(state)
    available = (
        not state.get("unresolved_jobs")
        and facts["submitted_render_requests"] < policy["hard_generation_limit"]
    )
    awareness = PRESSURE[phase(state)]
    if policy.get("completion_policy") == FIXED_BUDGET:
        awareness += (
            " This experiment uses the complete generation allowance before final selection. "
            "The fixed-budget policy takes precedence over experience advice to finish early. "
            "Choose each attempt's prompt and input, retaining useful earlier candidates while exploring alternatives; finish is not yet available."
            if completion_pending(state) else
            " The generation allowance has been used. Complete the configured review, compare candidates and select your final result; an earlier candidate is eligible."
        )
    return {
        "stage": phase(state),
        "budget_awareness": awareness,
        "justification_required": False,
        "continuation_questions": [],
        "generation_available": available,
    }


def completion_pending(state):
    policy = state["config"].get("continuation_policy", {})
    return (policy.get("completion_policy") == FIXED_BUDGET
            and usage(state)["submitted_render_requests"] < policy["hard_generation_limit"])


def authorize_finish(state):
    if completion_pending(state):
        return {
            "status": "generation_budget_remaining",
            "message": "This experiment requires using the remaining generation allowance before final selection. Keep useful candidates and choose a further attempt. Observation, knowledge reading and review remain available.",
            "continuation": view(state),
        }
    return None


def record_input(harness, event_id, call_dir):
    if (call_dir/'continuation-policy.json').exists():
        return load(call_dir/'continuation-policy.json')
    saved = load(call_dir / "input.json")
    import json

    actual = json.loads(saved["user_text"]).get("continuation")
    # Historical prompts retain their actual visible fields, including absence.
    if actual is not None and not isinstance(actual, dict):
        raise ValueError("Saved continuation context is malformed")
    record = {
        "event_id": event_id,
        "model_input_sha256": sha(call_dir / "input.json"),
        "policy": copy.deepcopy(harness.state["config"]["continuation_policy"]),
        "stage": (actual or {}).get("stage", "historical_unrecorded"),
        "trigger_state": usage(harness.state),
        "visible": actual,
    }
    immutable(call_dir / "continuation-policy.json", record)


def authorize(state, args, event_id):
    existing = state.get("generation_decisions", {}).get(event_id + "-generate")
    if existing:
        if existing["arguments"] != args:
            raise ValueError("Recovered generation explanation or arguments changed")
        return None
    visible = view(state)
    if not visible["generation_available"]:
        return {
            "status": "generation_unavailable",
            "message": "Additional generation is unavailable under the current resource policy. Observation, reading, review and delivery remain available.",
            "continuation": visible,
        }
    explanation = args.get("justification")
    if explanation is not None and not isinstance(explanation, str):
        raise ValueError("justification must be free text")
    return None


def record_dispatch(harness, job, args, event_id):
    state = harness.state
    key = job["id"]
    record = {
        "event_id": event_id,
        "job_id": key,
        "request_sha256": job["sha256"],
        "arguments": copy.deepcopy(args),
        "justification": args.get("justification"),
        "policy_version": VERSION,
        "stage": phase(state),
        "visible": view(state),
        "input_id": job["payload"]["input_id"],
        "input_sha256": job["payload"]["input"]["sha256"],
        "prompt": job["payload"]["prompt"],
        "prompt_sha256": signature({"text": job["payload"]["prompt"]}),
        "model_input_path": str(harness.output / "calls" / event_id / "input.json"),
    }
    prior = state.setdefault("generation_decisions", {}).get(key)
    if prior:
        if prior["arguments"] != args or prior["request_sha256"] != job["sha256"]:
            raise ValueError("Recovered generation decision changed")
        return
    # Capture the pre-dispatch view: adding the signed job has not yet spent its slot here.
    immutable(harness.output / "jobs" / key / "continuation.json", record)
    state["generation_decisions"][key] = record


def record_outcome(state, job, response):
    if job["kind"] != "generate":
        return
    execution = response.get("payload", {}).get("execution", {})
    state.setdefault("render_outcomes", {})[job["id"]] = {
        "status": response["status"],
        "uncertain": bool(response.get("outcome_unknown")),
        "generation_seconds": execution.get("generation_seconds"),
        "request_sha256": job["sha256"],
    }


def index(run, state):
    """Passive operator navigation, never a model-side usefulness grade."""
    run = str(run)
    return {
        "policy_version": VERSION,
        "scope": "Raw continuation explanations and actual outcomes; no usefulness grading or causal attribution.",
        "spent_resources": usage(state),
        "generations": [
            {
                **copy.deepcopy(record),
                "request_path": run + "/jobs/" + key + "/request.json",
                "response_path": run + "/jobs/" + key + "/response.json",
                "outcome": copy.deepcopy(state.get("render_outcomes", {}).get(key)),
                "candidate_ids": [i for i, v in state["videos"].items() if v.get("job_id") == key],
            }
            for key, record in state.get("generation_decisions", {}).items()
        ],
    }
