"""Unified batch/topic admission accounting for external models, renders and compute.

The ledger bounds declared reservations. It never turns unknown bills into zero,
and never claims an invoice ceiling when execution/quotes cannot establish one.
"""

from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation
import json
import math
import os
from pathlib import Path
import queue
import re
import threading
import time

from .common import load, save, sha, stamp
from .execution import immutable, signature
from .integrity import IntegrityError
from .lock import RunLock
from .resources import ResourceExhausted, TaskDeadline

VERSION = "lha-unified-budget-v1"
LIMITS = {
    "model_calls": 96,
    "render_requests": 8,
    "compute_requests": 64,
    "tokens": 4000000,
    "wall_seconds": 21600,
    "amount": None,
}
LANES = ("direct", "full", "none", "independent")
OPTIONAL_LANES = ("direct-best-of-n", "planner-once", "pe", "pe-loop")
REQUIRED_QUOTES = (
    "model:gpt-6.1-sol/high",
    "render:bernini",
    "compute:temporal",
    "compute:features",
)
_ACTIVE = {}
_ACTIVE_LOCK = threading.Lock()


class BudgetConfigurationError(RuntimeError):
    failure_kind = "budget_configuration"


class SubmissionRefused(ResourceExhausted):
    """The ledger proves no dispatch; replay is a terminal, known refusal."""

    outcome_unknown = False
    retryable = False


class ExternalExecutionUnknown(RuntimeError):
    failure_kind = "external_execution_unknown"
    outcome_unknown = True


def amount(value):
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError()
        result = Decimal(value)
        if not result.is_finite() or result < 0:
            raise ValueError()
        return result
    except (InvalidOperation, ValueError):
        raise BudgetConfigurationError(
            "Amounts require nonnegative decimal strings, never inferred prices"
        ) from None


def validate_policy(supplied=None, *, require_live=False, required_quotes=()):
    p = copy.deepcopy(supplied or {"version": VERSION, "mode": "offline"})
    if p.get("version") != VERSION or p.get("mode") not in {"offline", "live"}:
        raise BudgetConfigurationError("Use a versioned live/offline unified budget")
    live = p["mode"] == "live"
    online = p.get("online_task_budget")
    if online and (
        online.get("version") != "online-task-v2"
        or type(online.get("max_generations")) is not int
        or online["max_generations"] < 1
        or type(online.get("wall_seconds")) is not int
        or not 1 <= online["wall_seconds"] <= 3600
        or not set(online.get("lanes", [])) <= set(LANES + OPTIONAL_LANES)
    ):
        raise BudgetConfigurationError("Invalid per-task online generation/time policy")
    cost_control = p.get("cost_control", "quoted_allowance")
    if cost_control not in {"quoted_allowance", "count_limits_only"}:
        raise BudgetConfigurationError("Choose quoted_allowance or explicit count_limits_only")
    monetary = cost_control == "quoted_allowance"
    requirements = p.get("hard_requirements", {})
    if (
        not isinstance(requirements, dict)
        or set(requirements) - {"output_tokens", "invoice"}
        or any(type(v) is not bool for v in requirements.values())
    ):
        raise BudgetConfigurationError("hard_requirements accepts output_tokens/invoice booleans")
    if requirements.get("invoice"):
        raise BudgetConfigurationError(
            "No configured transport verifies a hard provider invoice ceiling; no execution admitted"
        )
    if require_live and not live:
        raise BudgetConfigurationError(
            "Live execution requires an explicitly supplied live budget and quotes"
        )
    if (
        live
        and monetary
        and (not re.fullmatch(r"[A-Z]{3}", p.get("currency", "")) or p.get("currency") == "XXX")
    ):
        raise BudgetConfigurationError("Live monetary budgets require an explicit currency")
    for scope in ("batch", "topic"):
        if live and (scope not in p or set(p[scope]) != set(LIMITS)):
            raise BudgetConfigurationError(
                "Live batch/topic limits must explicitly declare every resource and amount"
            )
        p[scope] = {**LIMITS, **p.get(scope, {})}
        if set(p[scope]) != set(LIMITS):
            raise BudgetConfigurationError("Unknown unified budget limit")
        for key in set(LIMITS) - {"amount"}:
            if online and key != "wall_seconds":
                p[scope][key] = None
                continue
            if type(p[scope][key]) is not int or p[scope][key] < (
                1 if key == "wall_seconds" else 0
            ):
                raise BudgetConfigurationError(
                    "Resource limits must be finite nonnegative counts and positive wall time"
                )
        if live and monetary and p[scope]["amount"] is None:
            raise BudgetConfigurationError(
                "Supply your own batch/topic spending allowance before live execution"
            )
        if not monetary and p[scope]["amount"] is not None:
            raise BudgetConfigurationError(
                "count_limits_only retains unknown monetary allowance as null"
            )
        if p[scope]["amount"] is not None:
            p[scope]["amount"] = str(amount(p[scope]["amount"]))
    if live and "max_call_seconds" not in p:
        raise BudgetConfigurationError("Live execution needs a finite per-call deadline")
    timeout = p.setdefault("max_call_seconds", 900)
    if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0:
        raise BudgetConfigurationError("Invalid external-call deadline")
    allocations = p.setdefault("allocations", {})
    lane_names = p.get("lanes", LANES)
    if (
        not isinstance(lane_names, (list, tuple))
        or len(set(lane_names)) != len(lane_names)
        or set(lane_names) - set(LANES + OPTIONAL_LANES)
    ):
        raise BudgetConfigurationError("Unknown or duplicate declared budget lanes")
    if live and set(allocations) != set(lane_names):
        raise BudgetConfigurationError(
            "Live budgets explicitly allocate every declared method/independent lane"
        )
    for lane, limits in allocations.items():
        if lane not in lane_names or set(limits) != set(LIMITS):
            raise BudgetConfigurationError(
                "Each lane allocation declares every resource and amount"
            )
        for key in set(LIMITS) - {"amount"}:
            if online and lane in online["lanes"] and key != "wall_seconds":
                limits[key] = None
                continue
            if type(limits[key]) is not int or limits[key] < (1 if key == "wall_seconds" else 0):
                raise BudgetConfigurationError("Invalid lane allowance")
        if limits["amount"] is None and live and monetary:
            raise BudgetConfigurationError(
                "Live lane monetary allowances must be supplied explicitly"
            )
        if not monetary and limits["amount"] is not None:
            raise BudgetConfigurationError("count_limits_only lane amounts must remain null")
        if limits["amount"] is not None:
            limits["amount"] = str(amount(limits["amount"]))
    if allocations:
        for key in LIMITS:
            if online and key != "amount":
                continue
            if key == "amount" and any(v[key] is None for v in allocations.values()):
                if p["topic"][key] is not None:
                    raise BudgetConfigurationError(
                        "Unpriced lanes cannot be claimed within a monetary topic cap"
                    )
                continue
            total = (
                sum((amount(v[key]) for v in allocations.values()), Decimal(0))
                if key == "amount"
                else sum(v[key] for v in allocations.values())
            )
            if p["topic"][key] is not None and total > (
                amount(p["topic"][key]) if key == "amount" else p["topic"][key]
            ):
                raise BudgetConfigurationError(
                    "Topic aggregate cannot contain declared lane allocations: " + key
                )
            if (
                p["batch"][key] is not None
                and p["topic"][key] is not None
                and (amount(p["batch"][key]) if key == "amount" else p["batch"][key])
                < (amount(p["topic"][key]) if key == "amount" else p["topic"][key])
            ):
                raise BudgetConfigurationError(
                    "Batch must admit at least one complete topic allocation"
                )
    quotes = p.setdefault("quotes", {})
    for target, q in quotes.items():
        if (
            not isinstance(q, dict)
            or not q.get("source")
            or not q.get("quoted_at")
            or q.get("currency") != p.get("currency")
        ):
            raise BudgetConfigurationError(
                "Every quote requires currency, source and quotation date"
            )
        if q.get("unit") != "request" or "max_amount" not in q:
            raise BudgetConfigurationError(
                "Quotes must declare a per-request maximum charge boundary"
            )
        q["max_amount"] = str(amount(q["max_amount"]))
        for key in ("input_per_million", "output_per_million", "per_second", "fixed_amount"):
            if key in q:
                q[key] = str(amount(q[key]))
    if live and monetary:
        for target in required_quotes:
            if target not in quotes:
                raise BudgetConfigurationError("Missing quote for " + target)
    return p


def check_model_capabilities(binding, model):
    """Refuse unsupported hard requirements before any reservation/submission."""
    _, policy = checked(binding)
    capability = getattr(model, "budget_capabilities", None)
    capabilities = (
        capability()
        if callable(capability)
        else {
            "hard_output_tokens": False,
            "hard_invoice": False,
            "reason": "Transport has no verified hard-limit contract",
        }
    )
    if policy.get("hard_requirements", {}).get("output_tokens") and not capabilities.get(
        "hard_output_tokens"
    ):
        raise BudgetConfigurationError(
            "Transport cannot enforce the required hard output-token limit; no model request submitted"
        )
    if getattr(model, "output_limit_mode", None) == "hard" and not capabilities.get(
        "hard_output_tokens"
    ):
        raise BudgetConfigurationError(
            "Transport does not support hard output-token limits; no model request submitted"
        )
    return capabilities


def install(root, policy=None, *, require_live=False, required_quotes=()):
    root = Path(root).resolve()
    p = validate_policy(policy, require_live=require_live, required_quotes=required_quotes)
    root.mkdir(parents=True, exist_ok=True)
    with RunLock(root / "accounting-lock", timeout=10):
        immutable(root / "policy.json", p)
        if not (root / "ledger.json").exists():
            save(
                root / "ledger.json",
                {
                    "version": VERSION,
                    "created_at": stamp(),
                    "started_unix": None,
                    "policy_sha256": signature(p),
                    "topics": {},
                    "operations": {},
                    "events": [],
                    "breaches": [],
                },
            )
    return root


def scope(root, topic, lane="independent"):
    root = Path(root).resolve()
    if not isinstance(topic, str) or not topic:
        raise BudgetConfigurationError("Accounting requires an explicit topic identity")
    return {
        "version": VERSION,
        "root": str(root),
        "topic": topic,
        "lane": lane,
        "policy_sha256": signature(load(root / "policy.json")),
    }


def bind(directory, binding):
    checked(binding)
    with RunLock(Path(directory) / "budget-scope-owner", timeout=10):
        immutable(Path(directory) / "budget-scope.json", binding)
    return binding


def checked(binding, *, require_live=False):
    if not isinstance(binding, dict) or binding.get("version") != VERSION:
        raise BudgetConfigurationError("Missing unified accounting scope")
    root = Path(binding["root"])
    p = validate_policy(load(root / "policy.json"), require_live=require_live)
    if binding.get("policy_sha256") != signature(p):
        raise IntegrityError("Unified accounting policy binding changed")
    return root, p


def default_online_policy(*, max_generations=5, wall_seconds=3600, lanes=("full",)):
    """Online execution meters usage; each task owns its N/time allowance."""
    limits = {key: wall_seconds if key == "wall_seconds" else None for key in LIMITS}
    return {
        "version": VERSION,
        "mode": "live",
        "cost_control": "count_limits_only",
        "max_call_seconds": wall_seconds,
        "batch": dict(limits),
        "topic": dict(limits),
        "lanes": list(lanes),
        "allocations": {lane: dict(limits) for lane in lanes},
        "online_task_budget": {
            "version": "online-task-v2",
            "lanes": list(lanes),
            "max_generations": max_generations,
            "wall_seconds": wall_seconds,
        },
    }


def default_api_scope(
    directory, model=None, *, max_generations=5, wall_seconds=3600, lane="full", topic=None
):
    directory = Path(directory).resolve()
    policy = default_online_policy(
        max_generations=max_generations, wall_seconds=wall_seconds, lanes=(lane,)
    )
    root = install(directory / "accounting", policy)
    binding = scope(root, topic or directory.name, lane)
    bind(directory, binding)
    return binding


def discover(directory, model=None):
    binding = getattr(model, "lha_accounting_scope", None)
    if binding:
        checked(binding, require_live=bool(getattr(model, "requires_live_budget", False)))
        bind(Path(directory).resolve(), binding)
        return binding
    directory = Path(directory).resolve()
    for ancestor in (directory, *directory.parents):
        marker = ancestor / "budget-scope.json"
        if marker.exists():
            binding = load(marker)
            checked(binding, require_live=bool(getattr(model, "requires_live_budget", False)))
            return binding
    if getattr(model, "requires_live_budget", False):
        raise BudgetConfigurationError("Bind a priced live budget before calling a real model")
    if getattr(model, "is_live_api", False):
        binding = default_api_scope(directory, model, lane="independent")
        start_task(binding)
        return binding
    # Isolated software fixtures remain unpriced, but still produce a real ledger.
    root = install(directory / "offline-accounting")
    return scope(root, "offline-fixture")


def topic_scope(output, topic, policy=None, *, lane="independent"):
    output = Path(output)
    root = output / "accounting"
    if not (root / "policy.json").exists():
        install(root, policy)
    binding = scope(root, topic, lane)
    bind(output / "topics" / topic / "budget-lanes" / lane, binding)
    return binding


def attach(model, binding):
    client = copy.copy(model)
    client.lha_accounting_scope = binding
    return client


def _totals(records):
    result = {
        "model_calls": 0,
        "render_requests": 0,
        "compute_requests": 0,
        "tokens": 0,
        "amount": "0",
    }
    for r in records:
        if r["status"] == "not_submitted":
            continue
        count = (
            (r.get("actual_usage") or {}).get("provider_responses")
            if r["kind"] == "model"
            else None
        )
        result[
            {"model": "model_calls", "render": "render_requests", "compute": "compute_requests"}[
                r["kind"]
            ]
        ] += count if type(count) is int and count > 0 else 1
        result["tokens"] += r["charged_tokens"]
        if r["charged_amount"] is not None:
            result["amount"] = str(amount(result["amount"]) + amount(r["charged_amount"]))
    return result


def _event(ledger, action, key, details):
    previous = ledger["events"][-1]["sha256"] if ledger["events"] else None
    body = {
        "at": stamp(),
        "action": action,
        "operation": key,
        "details": details,
        "previous": previous,
        "clocks": {
            "started_unix": ledger["started_unix"],
            "topics": copy.deepcopy(ledger["topics"]),
        },
        "breaches": copy.deepcopy(ledger["breaches"]),
    }
    ledger["events"].append({**body, "sha256": signature(body)})


def load_ledger(root, p=None):
    root = Path(root)
    p = p or load(root / "policy.json")
    ledger = load(root / "ledger.json")
    if ledger.get("version") != VERSION or ledger.get("policy_sha256") != signature(p):
        raise IntegrityError("Unified ledger policy/version changed")
    previous = None
    projected = {}
    for event in ledger["events"]:
        if (
            event["previous"] != previous
            or signature({k: v for k, v in event.items() if k != "sha256"}) != event["sha256"]
        ):
            raise IntegrityError("Unified ledger event chain changed")
        key = event["operation"]
        if event["action"] in {"topic_admit", "topic_close", "task_start", "task_freeze"}:
            pass
        elif event["action"] in {"reserve", "settle"}:
            projected[key] = copy.deepcopy(event["details"])
        else:
            projected[key].update(status=event["action"], **event["details"])
        previous = event["sha256"]
    if projected != ledger["operations"]:
        raise IntegrityError("Unified ledger balances differ from the recorded transitions")
    if ledger["events"]:
        last = ledger["events"][-1]
        if (
            last["clocks"] != {"started_unix": ledger["started_unix"], "topics": ledger["topics"]}
            or last["breaches"] != ledger["breaches"]
        ):
            raise IntegrityError("Unified ledger deadlines or breach records changed")
    return ledger


def reserve(binding, key, kind, target, tokens=0):
    root, p = checked(binding)
    if kind not in {"model", "render", "compute"} or type(tokens) is not int or tokens < 0:
        raise BudgetConfigurationError("Invalid resource reservation")
    with RunLock(root / "accounting-lock", timeout=10):
        ledger = load_ledger(root)
        existing = ledger["operations"].get(key)
        if existing:
            if (existing["kind"], existing["target"], existing["topic"], existing["lane"]) != (
                kind,
                target,
                binding["topic"],
                binding.get("lane", "independent"),
            ):
                raise IntegrityError("Resource operation identity reused with different scope")
            return existing
        if (root / "stop-submissions.json").exists():
            raise ResourceExhausted(
                "Supervisor stopped new submissions; original executions remain retained"
            )
        if ledger["breaches"]:
            raise ResourceExhausted("Recorded quote/budget breach requires explicit reconciliation")
        quote = p["quotes"].get(target)
        if (
            p["mode"] == "live"
            and p.get("cost_control", "quoted_allowance") == "quoted_allowance"
            and quote is None
        ):
            raise BudgetConfigurationError("Missing priced maximum charge quote for " + target)
        now = time.time()
        started = ledger["started_unix"] or now
        topic_started = ledger["topics"].get(binding["topic"], {}).get("started_unix", now)
        reserved = quote["max_amount"] if quote else None
        record = {
            "id": key,
            "kind": kind,
            "target": target,
            "topic": binding["topic"],
            "lane": binding.get("lane", "independent"),
            "status": "reserved",
            "reserved_tokens": tokens,
            "charged_tokens": tokens,
            "reserved_amount": reserved,
            "charged_amount": reserved,
            "settled_amount": None,
            "currency": p.get("currency"),
            "quote": copy.deepcopy(quote),
            "actual_usage": None,
            "cost_status": "reserved_unknown" if quote else "unpriced",
            "created_at": stamp(),
            "started_unix": None,
            "completion": None,
        }
        checks = [
            ("batch", list(ledger["operations"].values()), started, p["batch"]),
            (
                "topic",
                [r for r in ledger["operations"].values() if r["topic"] == binding["topic"]],
                topic_started,
                p["topic"],
            ),
        ]
        if p["allocations"]:
            lane = record["lane"]
            if lane not in p["allocations"]:
                raise BudgetConfigurationError("Unallocated budget lane")
            lane_records = [
                v
                for v in ledger["operations"].values()
                if v["topic"] == binding["topic"] and v["lane"] == lane
            ]
            lane_clock = min((v["admitted_unix"] for v in lane_records), default=now)
            checks.append(("lane:" + lane, lane_records, lane_clock, p["allocations"][lane]))
        record["admitted_unix"] = now
        online = online_limits(binding, p)
        if online:
            task = ledger["topics"].get(binding["topic"], {}).get("lanes", {}).get(record["lane"])
            if task is None:
                raise BudgetConfigurationError(
                    "Start the ready online task before external admission"
                )
            if task.get("frozen_unix") or now >= task["deadline_unix"]:
                raise TaskDeadline("Task wall-time submission budget exhausted")
            if kind == "render":
                occupied = [
                    v
                    for v in ledger["operations"].values()
                    if v["topic"] == record["topic"]
                    and v["lane"] == record["lane"]
                    and v["kind"] == "render"
                    and v["status"] != "not_submitted"
                ]
                if len(occupied) >= online["max_generations"]:
                    raise SubmissionRefused(
                        "Generation resources exhausted; reading and delivery remain available"
                    )
            for label, records, clock, limits in checks:
                if limits["amount"] is not None and amount(
                    _totals([*records, record])["amount"]
                ) > amount(limits["amount"]):
                    raise ResourceExhausted(
                        label + " explicitly configured monetary allowance exhausted"
                    )
        else:
            for label, records, clock, limits in checks:
                totals = _totals([*records, record])
                if now - clock >= limits["wall_seconds"] or any(
                    limits[k] is not None and totals[k] > limits[k]
                    for k in set(LIMITS) - {"wall_seconds", "amount"}
                ):
                    raise ResourceExhausted(label + " unified resource allowance exhausted")
                if limits["amount"] is not None and amount(totals["amount"]) > amount(
                    limits["amount"]
                ):
                    raise ResourceExhausted(
                        label + " unified monetary reservation allowance exhausted"
                    )
        ledger["started_unix"] = started
        ledger["topics"].setdefault(binding["topic"], {"started_unix": topic_started})
        ledger["operations"][key] = record
        _event(ledger, "reserve", key, record)
        save(root / "ledger.json", ledger)
        return record


def transition(binding, key, status, **changes):
    root, p = checked(binding)
    with RunLock(root / "accounting-lock", timeout=10):
        ledger = load_ledger(root)
        record = ledger["operations"][key]
        record.update(status=status, **changes)
        _event(ledger, status, key, changes)
        save(root / "ledger.json", ledger)
    return record


def settle_operation(binding, key, usage, elapsed, completion, status):
    root, p = checked(binding)
    with RunLock(root / "accounting-lock", timeout=10):
        ledger = load_ledger(root)
        r = ledger["operations"][key]
        q = r["quote"] or {}
        a = usage.get("input_tokens", usage.get("prompt_tokens"))
        b = usage.get("output_tokens", usage.get("completion_tokens"))
        tokens = usage.get("total_tokens")
        if tokens is None and type(a) is int and type(b) is int:
            tokens = a + b
        cost = None
        if (
            type(a) is int
            and type(b) is int
            and {"input_per_million", "output_per_million"} <= set(q)
        ):
            cost = (
                Decimal(a) * amount(q["input_per_million"])
                + Decimal(b) * amount(q["output_per_million"])
            ) / Decimal(1000000)
        elif "per_second" in q:
            cost = Decimal(str(elapsed)) * amount(q["per_second"])
        elif q.get("fixed_amount") is not None:
            cost = amount(q["fixed_amount"])
        r.update(
            status=status,
            actual_usage=usage,
            elapsed_seconds=elapsed,
            completion=completion,
            settled_amount=str(cost) if cost is not None else None,
            cost_status="reported_usage_at_quote"
            if cost is not None
            else "unpriced"
            if not q
            else "unknown_reservation_held",
        )
        if type(tokens) is int and tokens >= 0:
            r["charged_tokens"] = tokens
        # An observed overrun remains above the reservation; it is never clamped.
        if cost is not None:
            r["charged_amount"] = str(cost)
        breach = cost is not None and cost > amount(q["max_amount"])
        for label, records in (
            ("batch", list(ledger["operations"].values())),
            ("topic", [v for v in ledger["operations"].values() if v["topic"] == r["topic"]]),
        ):
            totals = _totals(records)
            if p[label]["amount"] is not None and amount(totals["amount"]) > amount(
                p[label]["amount"]
            ):
                breach = True
            if p[label]["tokens"] is not None and totals["tokens"] > p[label]["tokens"]:
                breach = True
        if online_limits(binding, p):
            # Count/token fields are metering; explicit quote/money overruns remain real.
            breach = cost is not None and bool(q) and cost > amount(q["max_amount"])
            for label, records in (
                ("batch", list(ledger["operations"].values())),
                ("topic", [v for v in ledger["operations"].values() if v["topic"] == r["topic"]]),
            ):
                if p[label]["amount"] is not None and amount(_totals(records)["amount"]) > amount(
                    p[label]["amount"]
                ):
                    breach = True
        if breach:
            ledger["breaches"].append(
                {
                    "operation": key,
                    "at": stamp(),
                    "observed_amount": str(cost),
                    "reserved_amount": r["reserved_amount"],
                }
            )
        _event(ledger, "settle", key, copy.deepcopy(r))
        save(root / "ledger.json", ledger)
    return r


def active(root=None):
    with _ACTIVE_LOCK:
        return [
            v for v in _ACTIVE.values() if root is None or v["root"] == str(Path(root).resolve())
        ]


def operation(binding, key):
    root, _ = checked(binding)
    return load_ledger(root)["operations"].get(key)


def run_compute(target, inputs, fn, *, binding=None, requires_live=False):
    if binding is None:
        if requires_live:
            raise BudgetConfigurationError("This compute backend needs a declared live budget")
        import tempfile

        root = install(Path(tempfile.gettempdir()) / "lha-offline-compute" / signature(inputs))
        binding = scope(root, "offline-compute")
    checked(binding, require_live=requires_live)
    return invoke(
        binding,
        signature(
            {
                "target": target,
                "inputs": inputs,
                "topic": binding["topic"],
                "lane": binding.get("lane"),
            }
        ),
        "compute",
        target,
        fn,
    )


def invoke(
    binding,
    key,
    kind,
    target,
    fn,
    *,
    tokens=0,
    before_submit=None,
    usage_getter=None,
    on_not_submitted=None,
    owner=None,
):
    root, p = checked(binding)
    record = reserve(binding, key, kind, target, tokens)
    directory = root / "operations" / signature({"id": key})
    receipt = directory / "completion.json"
    if record["completion"]:
        if sha(receipt) != record["completion"]["sha256"]:
            raise IntegrityError("Accounting completion changed")
        saved = load(receipt)
        if saved["status"] != "complete":
            raise ExternalExecutionUnknown("Recorded external failure requires explicit recovery")
        return saved["result"]
    if record["status"] == "not_submitted":
        raise SubmissionRefused(
            "Original operation was refused before dispatch; no automatic retry"
        )
    if record["status"] != "reserved":
        raise ExternalExecutionUnknown(
            "External operation already started; retain its reservation and reconcile its original outcome"
        )
    lease = RunLock(directory / "execution-owner")
    try:
        lease.__enter__()
    except RuntimeError:
        raise ExternalExecutionUnknown("External operation is still owned") from None
    # Another caller may have completed between reserve() and lease acquisition.
    # Only the record under the execution lease authorizes a dispatch.
    record = operation(binding, key)
    if record["completion"]:
        lease.__exit__(None, None, None)
        if sha(receipt) != record["completion"]["sha256"]:
            raise IntegrityError("Accounting completion changed")
        saved = load(receipt)
        if saved["status"] != "complete":
            raise ExternalExecutionUnknown("Recorded external failure requires explicit recovery")
        return saved["result"]
    if record["status"] == "not_submitted":
        lease.__exit__(None, None, None)
        raise SubmissionRefused(
            "Original operation was refused before dispatch; no automatic retry"
        )
    if record["status"] != "reserved":
        lease.__exit__(None, None, None)
        raise ExternalExecutionUnknown(
            "Original execution is already submitted or needs explicit recovery"
        )
    transition(binding, key, "started", started_unix=time.time(), owner_pid=os.getpid())
    try:
        if before_submit:
            before_submit()
    except BaseException:
        transition(
            binding,
            key,
            "not_submitted",
            charged_tokens=0,
            charged_amount="0" if record["quote"] else None,
            cost_status="definitely_not_submitted",
        )
        if on_not_submitted:
            on_not_submitted()
        lease.__exit__(None, None, None)
        raise
    output = queue.Queue(maxsize=1)
    timed_out = threading.Event()
    decision = threading.Event()
    started = time.monotonic()
    active_key = str(root) + ":" + key

    def execute():
        value = None
        error = None
        try:
            _CURRENT.binding = binding
            _CURRENT.key = key
            value = fn()
        except BaseException as exc:
            error = exc
        try:
            usage = usage_getter() if usage_getter else {}
        except Exception:
            usage = {}
        saved = {
            "status": "complete" if error is None else "failed",
            "result": value,
            "error_type": type(error).__name__ if error else None,
            "usage": usage,
        }
        try:
            save(receipt, saved)
            decision.wait()
            settle_operation(
                binding,
                key,
                usage,
                time.monotonic() - started,
                {"path": str(receipt), "sha256": sha(receipt)},
                "late_complete"
                if timed_out.is_set() and error is None
                else "failed_unknown_cost"
                if error
                else "complete",
            )
        except BaseException as settlement_error:
            error = settlement_error
        finally:
            lease.__exit__(None, None, None)
            with _ACTIVE_LOCK:
                _ACTIVE.pop(active_key, None)
            output.put((value, error))

    root_ledger = load_ledger(root)
    remaining = min(
        p["batch"]["wall_seconds"] - (time.time() - root_ledger["started_unix"]),
        p["topic"]["wall_seconds"]
        - (time.time() - root_ledger["topics"][binding["topic"]]["started_unix"]),
    )
    if p["allocations"]:
        lane_records = [
            v
            for v in root_ledger["operations"].values()
            if v["topic"] == binding["topic"] and v["lane"] == record["lane"]
        ]
        lane_started = min(v["admitted_unix"] for v in lane_records)
        remaining = min(
            remaining,
            p["allocations"][record["lane"]]["wall_seconds"] - (time.time() - lane_started),
        )
    if online_limits(binding, p):
        task = root_ledger["topics"][binding["topic"]]["lanes"][record["lane"]]
        remaining = task["deadline_unix"] - time.time()
        wait_seconds = max(0, remaining)
    else:
        wait_seconds = min(p["max_call_seconds"], max(0, remaining))
    if wait_seconds <= 0:
        transition(
            binding,
            key,
            "not_submitted",
            charged_tokens=0,
            charged_amount="0" if record["quote"] else None,
            cost_status="deadline_before_dispatch",
        )
        if on_not_submitted:
            on_not_submitted()
        lease.__exit__(None, None, None)
        raise ResourceExhausted("Unified wall budget expired before external dispatch")
    thread = threading.Thread(target=execute, name="lha-owned-external-call", daemon=False)
    with _ACTIVE_LOCK:
        _ACTIVE[active_key] = {
            "operation": key,
            "root": str(root),
            "kind": kind,
            "target": target,
            "thread": thread,
            "topic": binding["topic"],
            "lane": binding.get("lane", "independent"),
            "owner": owner,
        }
    thread.start()
    # The execution thread persists its receipt before signalling. The decision
    # event lets it know whether the caller classified the result as late.
    deadline = time.monotonic() + wait_seconds
    while not receipt.exists() and time.monotonic() < deadline:
        thread.join(min(0.01, max(0, deadline - time.monotonic())))
    if not receipt.exists():
        timed_out.set()
        transition(binding, key, "in_flight_unknown", timeout_seconds=wait_seconds)
        decision.set()
        if online_limits(binding, p):
            cleanup = freeze_task(binding, reason="online task deadline")
            raise TaskDeadline(
                "Task wall-time submission budget exhausted; original external receipt retained",
                cleanup,
            )
        raise ExternalExecutionUnknown(
            "External deadline reached; original execution and reservation remain owned, no retry is permitted"
        )
    decision.set()
    value, error = output.get(timeout=10)
    if error is not None:
        raise error
    return value


def summary(root):
    root = Path(root)
    p = load(root / "policy.json")
    ledger = load_ledger(root)
    records = list(ledger["operations"].values())
    totals = _totals(records)
    unknown = [
        r["id"] for r in records if r["settled_amount"] is None and r["status"] != "not_submitted"
    ]
    return {
        "version": VERSION,
        "mode": p["mode"],
        "cost_control": p.get("cost_control", "quoted_allowance"),
        "currency": p.get("currency"),
        "reserved_or_settled_totals": totals,
        "total_amount": None if unknown else totals["amount"],
        "unknown_cost_operations": unknown,
        "invoice_ceiling_verified": False,
        "breaches": ledger["breaches"],
        "scope": "Admission limit at declared quote bounds; unknown costs remain held. Actual invoice ceilings require provider billing/termination evidence.",
    }


def validate_cohort(policy, *, max_generations=None, max_model_calls=None, topics=()):
    """Validate explicit independent per-arm protection, without choosing money."""
    from .resources import MAX_GENERATIONS

    if max_generations is None:
        max_generations = MAX_GENERATIONS
    policy = copy.deepcopy(policy or {})
    policy["online_task_budget"] = {
        "version": "online-task-v2",
        "lanes": ["direct", "full", "none"],
        "max_generations": max_generations,
        "wall_seconds": 3600,
    }
    p = validate_policy(
        policy,
        require_live=True,
        required_quotes=tuple(
            q for q in REQUIRED_QUOTES if not q.startswith(("model:glm", "model:sonnet"))
        ),
    )
    if p["allocations"]["full"] != p["allocations"]["none"]:
        raise BudgetConfigurationError(
            "Full and none require equal independent resource allocations"
        )
    for lane in ("full", "none"):
        if (
            p["allocations"][lane]["render_requests"] is not None
            and p["allocations"][lane]["render_requests"] < max_generations
        ):
            raise BudgetConfigurationError(
                "Each Loop needs its original independent call/render allowance"
            )
    if (
        p["allocations"]["direct"]["render_requests"] is not None
        and p["allocations"]["direct"]["render_requests"] < 1
    ):
        raise BudgetConfigurationError("Explicitly provision Direct and independent assessment")
    # Independent final API calls are metered without human quotas. CPU/GPU
    # feature work retains its separately supplied compute policy.
    compute = p["allocations"]["independent"]["compute_requests"]
    if topics and compute is not None and compute < 10:
        raise BudgetConfigurationError("Five distinct candidates need up to ten feature/flow jobs")

    return p


def admit_topic(binding):
    """Require room for the full declared allocation before the first arm starts."""
    root, p = checked(binding)
    if p["mode"] != "live" or p.get("online_task_budget"):
        return
    with RunLock(root / "accounting-lock", timeout=10):
        ledger = load_ledger(root)
        if binding["topic"] in ledger["topics"]:
            return
        if any(not v.get("closed", False) for v in ledger["topics"].values()):
            raise BudgetConfigurationError(
                "This cohort uses serial topic admission; close the prior topic before admitting another"
            )
        totals = _totals(ledger["operations"].values())
        for key in set(LIMITS) - {"wall_seconds", "amount"}:
            if totals[key] + p["topic"][key] > p["batch"][key]:
                raise ResourceExhausted(
                    "Insufficient remaining batch capacity for a complete topic: " + key
                )
        if (
            p["topic"]["amount"] is not None
            and p["batch"]["amount"] is not None
            and amount(totals["amount"]) + amount(p["topic"]["amount"])
            > amount(p["batch"]["amount"])
        ):
            raise ResourceExhausted("Insufficient remaining funds to admit all planned topic lanes")
        elapsed = time.time() - (ledger["started_unix"] or time.time())
        if elapsed + p["topic"]["wall_seconds"] > p["batch"]["wall_seconds"]:
            raise ResourceExhausted(
                "Insufficient remaining batch wall allowance for a complete topic"
            )
        now = time.time()
        ledger["started_unix"] = ledger["started_unix"] or now
        ledger["topics"][binding["topic"]] = {
            "started_unix": now,
            "closed": False,
            "capacity": copy.deepcopy(p["topic"]),
        }
        _event(
            ledger,
            "topic_admit",
            binding["topic"],
            {"capacity": copy.deepcopy(p["topic"]), "concurrency": "serial topic"},
        )
        save(root / "ledger.json", ledger)


def close_topic(binding):
    root, p = checked(binding)
    if p["mode"] != "live":
        return
    with RunLock(root / "accounting-lock", timeout=10):
        ledger = load_ledger(root)
        topic = ledger["topics"].get(binding["topic"])
        if topic is None or topic.get("closed"):
            return
        topic["closed"] = True
        _event(
            ledger, "topic_close", binding["topic"], {"unused_admission_capacity_released": True}
        )
        save(root / "ledger.json", ledger)


def reconcile(binding, key, *, evidence, reason, not_executed=False):
    """Explicit evidence-bound reconciliation; never resubmit an unknown request.

    not_executed requires an operator/provider receipt asserting no dispatch. The
    original entry remains immutable history; additional work uses a new key.
    """
    evidence = Path(evidence)
    if not reason.strip() or not evidence.is_file():
        raise ValueError("Supply reconciliation evidence and reason")
    root, _ = checked(binding)
    record = operation(binding, key)
    if record is None:
        raise ValueError("Unknown operation")
    directory = root / "operations" / signature({"id": key})
    with RunLock(directory / "execution-owner"):
        record = operation(binding, key)
        receipt = directory / "completion.json"
        immutable(
            directory / "reconciliation.json",
            {
                "operation": key,
                "reason": reason,
                "evidence_path": str(evidence.resolve()),
                "evidence_sha256": sha(evidence),
                "not_executed": not_executed,
            },
        )
        if not_executed:
            if receipt.exists():
                raise IntegrityError("A completed execution cannot be asserted unsubmitted")
            transition(
                binding,
                key,
                "not_submitted",
                charged_tokens=0,
                charged_amount="0" if record["quote"] else None,
                cost_status="operator_evidence_not_submitted",
            )
        elif receipt.exists():
            saved = load(receipt)
            settle_operation(
                binding,
                key,
                saved.get("usage", {}),
                record.get("elapsed_seconds", 0),
                {"path": str(receipt), "sha256": sha(receipt)},
                "reconciled_complete" if saved["status"] == "complete" else "failed_unknown_cost",
            )
        else:
            raise ValueError("No durable original result; keep unknown costs and ownership")
    return operation(binding, key)


# Cancellation callbacks belong to one exact operation, never a service-wide PID.
_CURRENT = threading.local()
_CANCEL = {}


def online_limits(binding, policy=None):
    policy = policy or checked(binding)[1]
    value = policy.get("online_task_budget")
    return value if value and binding.get("lane") in value["lanes"] else None


def start_task(binding, *, wall_seconds=None):
    root, p = checked(binding)
    limits = online_limits(binding, p)
    if wall_seconds is None:
        wall_seconds = limits["wall_seconds"] if limits else 3600
    if limits and wall_seconds != limits["wall_seconds"]:
        raise BudgetConfigurationError("Task clock must match the frozen online wall allowance")
    if wall_seconds <= 0 or wall_seconds > 3600:
        raise BudgetConfigurationError("Online task clock must fit within one hour")
    with RunLock(root / "accounting-lock", timeout=10):
        ledger = load_ledger(root)
        now = time.time()
        topic = ledger["topics"].setdefault(binding["topic"], {"started_unix": now})
        lanes = topic.setdefault("lanes", {})
        lane = binding.get("lane", "independent")
        if lane not in lanes:
            lanes[lane] = {"started_unix": now, "deadline_unix": now + wall_seconds}
            ledger["started_unix"] = ledger["started_unix"] or now
            _event(ledger, "task_start", binding["topic"] + ":" + lane, copy.deepcopy(lanes[lane]))
            save(root / "ledger.json", ledger)
        return copy.deepcopy(lanes[lane])


def register_cancel(callback):
    """Called by an owned transport on the invoke execution thread."""
    binding = getattr(_CURRENT, "binding", None)
    if binding is None:
        return lambda: None
    key = (binding["root"], binding["topic"], binding.get("lane", "independent"), _CURRENT.key)
    root, p = checked(binding)
    if online_limits(binding, p):
        task = (
            load_ledger(root)["topics"]
            .get(binding["topic"], {})
            .get("lanes", {})
            .get(binding.get("lane", "independent"), {})
        )
        if task.get("frozen_unix") or time.time() >= task.get("deadline_unix", 0):
            callback()
            raise ResourceExhausted("Task deadline reached before owned execution registration")
    with _ACTIVE_LOCK:
        _CANCEL[key] = callback

    def remove():
        with _ACTIVE_LOCK:
            _CANCEL.pop(key, None)

    return remove


def freeze_task(binding, *, reason):
    root, _ = checked(binding)
    with RunLock(
        root
        / "task-admission"
        / signature({"topic": binding["topic"], "lane": binding.get("lane", "independent")}),
        timeout=10,
    ):
        return _freeze_task_locked(binding, reason=reason)


def _freeze_task_locked(binding, *, reason):
    root, p = checked(binding)
    lane = binding.get("lane", "independent")
    with RunLock(root / "accounting-lock", timeout=10):
        ledger = load_ledger(root)
        task = ledger["topics"].get(binding["topic"], {}).get("lanes", {}).get(lane)
        if task and not task.get("frozen_unix"):
            task.update(frozen_unix=time.time(), reason=reason)
            _event(ledger, "task_freeze", binding["topic"] + ":" + lane, copy.deepcopy(task))
            save(root / "ledger.json", ledger)
    with _ACTIVE_LOCK:
        callbacks = [
            (k, fn) for k, fn in _CANCEL.items() if k[:3] == (str(root), binding["topic"], lane)
        ]
    evidence = []
    for key, fn in callbacks:
        try:
            result = fn()
        except Exception as exc:
            result = {"local_stopped": False, "error_type": type(exc).__name__}
        evidence.append({"operation": key[-1], **result})
    owned = [
        {k: v for k, v in item.items() if k != "thread"}
        for item in active(root)
        if item.get("topic") == binding["topic"] and item.get("lane") == lane
    ]
    result = {
        "reason": reason,
        "cancellations": evidence,
        "owned_operations": owned,
        "scope": "Only registered task-owned executions were cancelled. External provider stop and invoice release require provider evidence; unresolved occupancy remains held.",
    }
    path = (
        root
        / "task-cleanup"
        / signature({"topic": binding["topic"], "lane": lane})
        / "receipt.json"
    )
    if path.exists():
        return load(path)
    save(path, result)
    return result


from contextlib import contextmanager


@contextmanager
def submission_guard():
    binding = getattr(_CURRENT, "binding", None)
    if binding is None:
        yield
        return
    root, p = checked(binding)
    with RunLock(
        root
        / "task-admission"
        / signature({"topic": binding["topic"], "lane": binding.get("lane", "independent")}),
        timeout=10,
    ):
        if online_limits(binding, p):
            task = (
                load_ledger(root)["topics"]
                .get(binding["topic"], {})
                .get("lanes", {})
                .get(binding.get("lane", "independent"), {})
            )
            if task.get("frozen_unix") or time.time() >= task.get("deadline_unix", 0):
                raise ResourceExhausted("Task deadline reached; no new execution submitted")
        yield


def launch_owned(command, **kwargs):
    from .owned_process import OwnedProcess

    with submission_guard():
        child = OwnedProcess(command, **kwargs)
        remove = register_cancel(child.cancel)
    return child, remove


def check_task(binding):
    root, p = checked(binding)
    if not online_limits(binding, p):
        return
    task = (
        load_ledger(root)["topics"]
        .get(binding["topic"], {})
        .get("lanes", {})
        .get(binding.get("lane", "independent"), {})
    )
    if task.get("frozen_unix") or time.time() >= task.get("deadline_unix", 0):
        raise TaskDeadline("Task result frozen at its original deadline")


def bounded_preflight(binding, key, fn, *, owner=None, resource_kind="gpu"):
    """Preparation is cancellable but is not an execution/generation charge."""
    root, p = checked(binding)
    if not online_limits(binding, p):
        return fn()
    check_task(binding)
    task = load_ledger(root)["topics"][binding["topic"]]["lanes"][
        binding.get("lane", "independent")
    ]
    result = queue.Queue(maxsize=1)
    active_key = str(root) + ":" + key + ":preflight"

    def run():
        _CURRENT.binding = binding
        _CURRENT.key = key + ":preflight"
        try:
            value, error = fn(), None
        except BaseException as exc:
            value, error = None, exc
        finally:
            with _ACTIVE_LOCK:
                _ACTIVE.pop(active_key, None)
        result.put((value, error))

    thread = threading.Thread(target=run, name="lha-owned-preflight", daemon=True)
    with _ACTIVE_LOCK:
        _ACTIVE[active_key] = {
            "operation": key + ":preflight",
            "root": str(root),
            "topic": binding["topic"],
            "lane": binding.get("lane", "independent"),
            "owner": owner,
            "kind": "preparation",
            "resource_kind": resource_kind,
            "target": "unsubmitted-preflight",
            "thread": thread,
        }
    thread.start()
    try:
        value, error = result.get(timeout=max(0, task["deadline_unix"] - time.time()))
    except queue.Empty:
        cleanup = freeze_task(binding, reason="online deadline during unsubmitted preparation")
        raise TaskDeadline(
            "Task deadline reached during preparation; no generation dispatched", cleanup
        ) from None
    if error:
        raise error
    check_task(binding)
    return value
