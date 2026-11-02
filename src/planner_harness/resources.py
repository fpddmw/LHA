"""Finite submission guards; unknown charges and in-flight overruns stay explicit."""

from datetime import datetime, timezone
from pathlib import Path
import math
import time

from .common import load, save
from .lock import RunLock

MAX_GENERATIONS = 5
DEFAULTS = {
    "version": "creative-resources-v2",
    "max_turns": None,
    "max_generations": MAX_GENERATIONS,
    "max_model_calls": None,
    "max_total_tokens": None,
    "max_wall_seconds": 3600,
    "max_cost": None,
    "token_price_per_million": None,
}


class ResourceExhausted(ValueError):
    failure_kind = "resource_exhausted"


class TaskDeadline(ResourceExhausted):
    task_deadline = True

    def __init__(self, message, cleanup=None):
        super().__init__(message)
        self.cleanup = cleanup


def configure(state, supplied=None, *, continuation=None):
    if (
        (continuation or {}).get("hard_generation_limit") is not None
        and state["config"].get("max_generations") is None
        and not (supplied or {}).get("max_generations")
    ):
        supplied = {**(supplied or {}), "max_generations": continuation["hard_generation_limit"]}
    policy = {**DEFAULTS, **(supplied or {})}
    for field in ("max_generations",):
        top = state["config"].get(field)
        if top is not None:
            if field in (supplied or {}) and policy[field] != top:
                raise ValueError("Conflicting top-level and resource policy " + field)
            policy[field] = top
    if set(policy) != set(DEFAULTS) or policy["version"] != DEFAULTS["version"]:
        raise ValueError("Unknown resource policy")
    for key in ("max_generations", "max_wall_seconds"):
        if type(policy[key]) is not int or policy[key] <= 0:
            raise ValueError("Generation and wall guards require positive integer limits")
    if policy["max_wall_seconds"] > 3600:
        raise ValueError("Online tasks have a hard maximum of one hour")
    # These fields remain in records for compatibility, with no task stop semantics.
    for key in ("max_turns", "max_model_calls", "max_total_tokens"):
        policy[key] = None
    state["config"]["max_turns"] = None
    for key in ("max_cost", "token_price_per_million"):
        value = policy[key]
        if value is not None and (
            type(value) not in {int, float} or not math.isfinite(value) or value < 0
        ):
            raise ValueError("Invalid optional price or cost limit")
    if policy["max_cost"] is not None and policy["token_price_per_million"] is None:
        raise ValueError(
            "A monetary cap needs an explicit conservative token price; unknown price is not zero"
        )
    state["config"]["resource_policy"] = policy
    if state["config"].get("max_turns") is None:
        state["config"]["max_turns"] = policy["max_turns"]
    return policy


def elapsed(state):
    if state.get("online_clock"):
        return max(0, time.time() - state["online_clock"]["started_unix"])
    return max(
        0,
        time.time()
        - datetime.fromisoformat(state["created_at"].replace("Z", "+00:00"))
        .replace(tzinfo=timezone.utc)
        .timestamp(),
    )


def check_wall(state):
    policy = state["config"].get("resource_policy")
    if policy and elapsed(state) >= policy["max_wall_seconds"]:
        raise TaskDeadline("Task wall-time submission budget exhausted")


def reserve(root, call, policy, tokens):
    root = Path(root)
    with RunLock(root / "resource-accounting"):
        path = root / "resource-ledger.json"
        ledger = load(path) if path.exists() else {"version": DEFAULTS["version"], "calls": {}}
        calls = ledger["calls"]
        key = str(Path(call).resolve())
        if key in calls:
            return
        spent = sum(r["charged_tokens"] for r in calls.values())
        if (
            policy["max_cost"] is not None
            and (spent + tokens) * policy["token_price_per_million"] / 1000000 > policy["max_cost"]
        ):
            raise ResourceExhausted("Explicitly configured task model-cost allowance exhausted")
        calls[key] = {
            "reserved_tokens": tokens,
            "charged_tokens": tokens,
            "usage_status": "unknown_reserved",
            "at_unix": time.time(),
        }
        ledger["cost_scope"] = (
            "Model token allowance only; renderer and unpriced provider charges remain unknown. Limits are checked before submission; an in-flight call may overrun estimates."
        )
        save(path, ledger)


def reconcile(root, call, usage):
    with RunLock(Path(root) / "resource-accounting"):
        path = Path(root) / "resource-ledger.json"
        ledger = load(path)
        record = ledger["calls"][str(Path(call).resolve())]
        total = usage.get("total_tokens")
        if total is None:
            a = usage.get("input_tokens", usage.get("prompt_tokens"))
            b = usage.get("output_tokens", usage.get("completion_tokens"))
            if type(a) is int and type(b) is int:
                total = a + b
        if type(total) is int and total >= 0:
            record.update(charged_tokens=total, usage_status="provider_reported", usage=usage)
        save(path, ledger)


def settle(state, reason, *, status="budget_exhausted"):
    if state.get("online_clock") and status == "budget_exhausted":
        state["online_clock"].setdefault("frozen_unix", time.time())
    proof = None
    if (
        status == "budget_exhausted"
        and state.get("online_clock")
        and time.time() >= state["online_clock"]["deadline_unix"]
    ):
        from .candidate_selection import deadline_choice

        proof = deadline_choice(state)
    if proof:
        state.update(
            status=status,
            final={
                "video": proof["selected"],
                "stop_reason": "deadline",
                "outcome": "deadline_delivery",
                "planner_confirmed": False,
                "selection": proof,
                "message": reason,
            },
        )
    else:
        state.update(
            status=status,
            final={
                "video": None,
                "stop_reason": "budget" if status == "budget_exhausted" else "execution_failure",
                "outcome": "incomplete",
                "message": reason,
            },
        )


def start_clock(state, binding=None):
    """Call only when the worker and resources are ready; resume never renews it."""
    if state.get("online_clock"):
        return state["online_clock"]
    now = time.time()
    limit = state["config"]["resource_policy"]["max_wall_seconds"]
    if binding:
        from .accounting import start_task

        clock = start_task(binding, wall_seconds=limit)
    else:
        clock = {"started_unix": now, "deadline_unix": now + limit}
    state["online_clock"] = clock
    return clock
