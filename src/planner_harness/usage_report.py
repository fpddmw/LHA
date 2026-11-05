"""Read-only usage summaries from durable calls and per-HTTP gateway receipts."""

import json
from collections import Counter
from pathlib import Path


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def metrics(usage):
    def first(*values):
        return next((v for v in values if isinstance(v, (int, float))), None)
    inp = first(usage.get("input_tokens"), usage.get("prompt_tokens"))
    out = first(usage.get("output_tokens"), usage.get("completion_tokens"))
    return {"input_tokens": inp, "output_tokens": out,
            "total_tokens": first(usage.get("total_tokens"), inp + out if inp is not None and out is not None else None),
            "cached_input_tokens": first((usage.get("input_tokens_details") or {}).get("cached_tokens"),
                                          (usage.get("prompt_tokens_details") or {}).get("cached_tokens")),
            "reasoning_tokens": first((usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
                                       (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")),
            "cost": first(usage.get("cost"))}


def infer_role(path, receipt=None):
    if (receipt or {}).get("role"):
        return receipt["role"]
    parts = set(path.parts)
    if "maintenance" in parts:
        return "post_task_planner"
    if "one-shot-critic" in parts:
        return "online_critic"
    if parts & {"judges", "evaluation", "evaluations", "scoring", "pairwise"}:
        return "benchmark_final"
    return "planner"


def summarize(root):
    root = Path(root).resolve()
    calls, seen = [], set()
    # Only explicit call packets qualify; state/knowledge input copies are not
    # calls. A supplied output root is never widened into a global run scan.
    for path in root.rglob("input.json"):
        packet = load(path)
        if not {"model", "system_prompt", "user_text"} <= packet.keys():
            continue
        folder = path.parent
        if "attempts" in folder.parts or folder.resolve() in seen:
            continue
        seen.add(folder.resolve())
        attempts = []
        directories = sorted((folder / "attempts").glob("*")) if (folder / "attempts").exists() else [folder]
        role = None
        for directory in directories:
            receipt = load(directory / "result.json")
            role = role or receipt.get("role")
            http = sorted((directory / "client-audit/http-attempts").glob("*.json"))
            if http:
                for p in http:
                    r = load(p)
                    role = role or r.get("role")
                    attempts.append({"path": str(p.relative_to(root)), "status": r.get("status", "unknown"),
                                     "usage": metrics(r.get("usage") or {})})
                continue  # The outer receipt aggregates these same HTTP calls.
            if not any((directory / name).exists() for name in ("submitted.json", "result.json", "failed.json", "unknown.json")):
                continue
            status = "returned" if receipt else "failed" if (directory / "failed.json").exists() else "outcome_unknown"
            attempts.append({"path": str(directory.relative_to(root)), "status": status,
                             "http_attempts": "not instrumented", "usage": metrics(receipt.get("usage") or {})})
        calls.append({"path": str(folder.relative_to(root)), "role": role or infer_role(folder),
                      "model": packet["model"], "attempts": attempts})
    groups = {}
    for role in sorted({r["role"] for r in calls}):
        selected = [r for r in calls if r["role"] == role]
        rows = [a for r in selected for a in r["attempts"]]
        aggregate = {}
        for field in metrics({}):
            values = [r["usage"][field] for r in rows]
            known = [v for v in values if v is not None]
            aggregate[field] = {"known_sum": sum(known) if known else None,
                                "known_records": len(known), "records": len(rows),
                                "complete": bool(rows) and len(known) == len(rows)}
        groups[role] = {"logical_calls": len(selected), "recorded_attempts": len(rows),
                        "instrumented_http_attempts": sum("http_attempts" not in r for r in rows),
                        "statuses": dict(Counter(r["status"] for r in rows)), "usage": aggregate}
    return {"scope": str(root), "roles": groups, "calls": calls,
            "notes": "Cache and reasoning are subsets, not additional tokens. Missing usage/cost remains unknown. Historical HTTP multiplicity may be uninstrumented."}
