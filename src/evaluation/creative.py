"""Independent final evaluation orchestration; never an online Planner tool."""

from __future__ import annotations

import json
from pathlib import Path

from planner_harness.execution import immutable
from .low_high import prepare_final
from .providers import JUDGES as JUDGES, OpenRouterJudge as OpenRouterJudge
from .providers import MODEL, judge_identity, make_judge


def __getattr__(name):
    # Old explicit imports remain usable without loading old providers in current runs.
    if name in {"API_MODEL", "ParateraJudge", "SonnetJudge", "ProviderHTTPError", "NoRedirect"}:
        from . import legacy_providers

        return getattr(legacy_providers, name)
    raise AttributeError(name)


def prepare_final_request(request, source, candidate, directory, *, plan=None):
    """Export overview evidence without making model calls; temporal score is unknown."""
    return prepare_final(request, source, candidate, directory, plan=plan)


def judge_candidate(request, source, candidate, directory, *, model=None, plan=None):
    directory = Path(directory)
    if (directory/'judgment.json').exists():
        from planner_harness.common import load
        saved = load(directory/'judgment.json')
        if saved['source_sha256'] != source['sha256'] or saved['output_sha256'] != candidate['sha256']:
            raise ValueError('Saved judgment belongs to another video')
        return saved
    if plan is None:
        raise ValueError("Independent final scoring requires a shared frozen source-only plan")
    client = model or make_judge(MODEL)
    identity = getattr(client, "frozen_identity", None) or judge_identity(client.model)
    if getattr(client, "reasoning_effort", None) != identity["reasoning_effort"]:
        raise ValueError(
            "Independent judge reasoning configuration differs from the frozen identity"
        )
    packet, images = prepare_final(request, source, candidate, directory, plan=plan, model=client)
    from .final_projection import evaluate as evaluate_main

    report, answer, projection = evaluate_main(directory, client, packet, images)
    result = {
        "usage": "independent_final",
        **identity,
        "source_sha256": source["sha256"],
        "output_sha256": candidate["sha256"],
        "plan_sha256": plan["sha256"],
        "profile_sha256": packet["profile_sha256"],
        "report": report,
        "answer_binding": answer,
        "main_projection": projection,
        "coverage": json.loads(packet["user_text"])["coverage"],
        "event_reviews": len(packet["event_records"]),
        "request_path": str(directory / "evidence/request.json"),
    }
    from .task_metrics import evaluate

    result["task_metrics"] = evaluate(packet, directory / "task-metrics", client)
    immutable(directory / "judgment.json", result)
    return result


def paired_summary(pairs):
    """Summarize valid per-dimension pairs; missing scores never become zeros."""
    from .validation import DIMENSIONS

    result = {}
    for key in DIMENSIONS:
        deltas = [
            b["main_scores"][key]["score"] - a["main_scores"][key]["score"]
            for a, b in pairs
            if a is not None
            and b is not None
            and a["main_scores"][key]["status"] == b["main_scores"][key]["status"] == "scored"
        ]
        result[key] = {
            "planned": len(pairs),
            "valid": len(deltas),
            "missing": len(pairs) - len(deltas),
            "mean_delta": sum(deltas) / len(deltas) if deltas else None,
            "improved": sum(d > 0 for d in deltas),
            "tied": deltas.count(0),
            "worsened": sum(d < 0 for d in deltas),
        }
    return result


def frozen_judge(identity):
    """Keep the original judge slot/provider when configuration changes."""
    try:
        unchanged = judge_identity(identity['model']) == identity
    except ValueError:
        unchanged = False
    if unchanged:
        return make_judge(identity['model'])
    from .providers import make_frozen_judge
    return make_frozen_judge(identity)
