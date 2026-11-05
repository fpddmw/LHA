"""Small profile integration for a model-led, non-learning creative loop."""

from __future__ import annotations

import copy
from pathlib import Path

from .common import save
from functools import lru_cache

WORKFLOW = "creative_loop_v1"


from vlm.settings import role_settings


def active(state):
    return state.get("config", {}).get("workflow") == WORKFLOW


def configure(harness, execution):
    from critic_harness.one_shot import frozen_profile, verify_profile
    from .creative_knowledge import CreativeKnowledge

    profile = copy.deepcopy(execution or {})
    from .resources import configure as configure_resources

    resource = profile.pop("resource_policy", None)
    continuation = profile.pop("continuation_policy", None)
    configure_resources(harness.state, resource, continuation=continuation,
                        backend=profile.get("renderer", {}).get("backend", "bernini"))
    from .continuation import configure as configure_continuation

    configure_continuation(harness.state, continuation)
    if any(key in profile for key in ("evaluation", "rsi", "task_card")):
        raise ValueError("Creative loop excludes task cards, RSI and online independent evaluation")
    if profile.get("experiment_profile"):
        verify_experiment(profile["experiment_profile"], harness.root)
    track = profile.setdefault("task_track", "long")
    if track not in {"short", "long"}:
        raise ValueError("task_track must be short or long")
    mode = profile.setdefault("experience_mode", "full")
    if mode not in {"full", "none"}:
        raise ValueError("Experience mode must be full or none")
    review = profile.setdefault("review", {"mode": "critic"})
    if not isinstance(review, dict) or review.get("mode", "critic") not in {"critic", "planner"}:
        raise ValueError("review.mode is critic or planner")
    review.setdefault("mode", "critic")
    supplied = profile.get("critic", {})
    settings = role_settings(profile, "online_critic")
    frozen = supplied.get("frozen_profile") or frozen_profile(**settings)
    verify_profile(frozen)
    if supplied.get("protocol", frozen["protocol_id"]) != frozen["protocol_id"]:
        raise ValueError("Use the configured qualitative review protocol")
    profile["critic"] = {**supplied, "protocol": frozen["protocol_id"], "frozen_profile": frozen}
    profile.setdefault(
        "planner",
        {
            "model": harness.model.model,
            "reasoning_effort": getattr(harness.model, "reasoning_effort", None),
        },
    )
    snapshot = profile.get("experience_snapshot")
    if snapshot:
        from .common import sha

        if sha(snapshot) != profile.get("experience_snapshot_sha256"):
            raise ValueError("Frozen experience revision changed")
    harness.knowledge = CreativeKnowledge(harness.root, snapshot, experience_mode=mode)
    harness.state["config"]["execution"] = profile
    from .delivery_review import PROTOCOL as DELIVERY_REVIEW

    harness.state["config"]["delivery_review_protocol"] = DELIVERY_REVIEW
    save(harness.output / "critic-profile.json", frozen)


def experiment_profile(root):
    import json

    return copy.deepcopy(
        _experiment_profile(
            str(Path(root).resolve()),
            json.dumps(role_settings({}, "planner"), sort_keys=True),
            json.dumps(role_settings({}, "online_critic"), sort_keys=True),
        )
    )


@lru_cache(maxsize=8)
def _experiment_profile(root, planner_settings, critic_settings):
    import json

    """Optional shared cohort identity; no jobs, data splits or learning cycle."""
    from .common import sha
    from .execution import signature
    from .creative_knowledge import CreativeKnowledge
    from critic_harness.one_shot import frozen_profile

    root = Path(root).resolve()
    from .protocol_sources import protocol_inventory

    files = protocol_inventory(root)
    scopes = {}
    paths = set()
    for mode in ("full", "none"):
        knowledge = CreativeKnowledge(root, experience_mode=mode)
        scopes[mode] = {
            identity: {"path": row["path"], "sha256": sha(root / row["path"])}
            for identity, row in knowledge.items.items()
            if (root / row["path"]).is_file()
        }
        paths.update(knowledge.paths)
        paths.add(
            knowledge.allowlist.get("operations_manual", "src/planner_harness/CREATIVE_LOOP.md")
        )
    for relative in sorted(paths):
        path = root / relative
        if path.is_file() and path.suffix.lower() in {
            ".md",
            ".json",
            ".py",
            ".html",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }:
            files[relative] = sha(path)
    for relative in (
        "knowledge/creative-loop/manifest.json",
        "knowledge/source-map.json",
        knowledge.allowlist.get("curated_catalog"),
    ):
        if relative is None:
            continue
        files[relative] = sha(root / relative)
    for relative in (
        "scripts/run_creative_benchmark.py",
        "scripts/run_planner_worker.py",
        "scripts/manage_creative_run.py",
        "scripts/deploy/run_prompt_probe.py",
        "configs/creative-loop-v1.json",
    ):
        files[relative] = sha(root / relative)
    from .continuation import VERSION as CONTINUATION
    from .delivery_review import PROTOCOL as DELIVERY_REVIEW

    body = {
        "protocol": "creative-experiment-v2",
        "runtime_policy": {"continuation": CONTINUATION, "delivery_review": DELIVERY_REVIEW},
        "critic": frozen_profile(**json.loads(critic_settings)),
        "planner": json.loads(planner_settings),
        "files": files,
        "knowledge_scopes": scopes,
    }
    return {**body, "sha256": signature(body)}


def verify_experiment(path, root):
    """Check the saved contract, not the entire checkout before every job."""
    from .common import load
    from .execution import signature
    from critic_harness.one_shot import verify_profile

    binding = load(path)
    if binding.get("sha256") != signature({k: v for k, v in binding.items() if k != "sha256"}):
        raise ValueError("Saved experiment profile changed")
    verify_profile(binding["critic"])
    from .protocol_sources import protocol_inventory

    current = protocol_inventory(Path(__file__).resolve().parents[2])
    from .upgrade import record
    record(Path(path).parent, 'implementation', binding.get('files', {}), current)
    return binding


def system_prompt(harness):
    path = harness.knowledge.allowlist.get(
        "operations_manual", "src/planner_harness/CREATIVE_LOOP.md"
    )
    operations = (harness.knowledge.snapshot or {}).get("documents", {}).get(path, {}).get("text")
    if operations is None:
        operations = (harness.root / path).read_text(encoding="utf-8")
    from .tool_interface import reference
    start = operations.find("Use one JSON operation")
    end = operations.find("\n\nEvery successful generation", start)
    if start >= 0 and end > start:
        operations = operations[:start] + reference() + operations[end:]
    sections = [operations]
    # Older snapshots retain their original instruction set.
    if "prompt-writing" in harness.knowledge.items:
        sections.append(harness.knowledge.document(harness.knowledge.items["prompt-writing"])["text"])
    for identity in ("manual", "review"):
        sections.append(harness.knowledge.document(harness.knowledge.items[identity])["text"])
    return "\n\n".join(sections)


def review_payload(harness, args):
    state = harness.state
    identity = args.get("video")
    if identity not in state["videos"] or identity == "source":
        raise ValueError("Review an available generated candidate")
    for key, job in state["jobs"].items():
        if job["kind"] == "critique" and job["payload"]["video_id"] == identity:
            if key in state["evaluations"]:
                return None, {
                    "status": "complete",
                    "cached": True,
                    "feedback_id": key,
                    "feedback": state["evaluations"][key],
                }
            return None, {
                "status": "unavailable",
                "job_id": key,
                "message": "Original review outcome remains attached to its original request.",
            }
    candidate = state["videos"][identity]
    input_id = candidate.get("parent", "source")
    comparison = args.get("compare_to")
    selected = list(
        dict.fromkeys(["source", input_id, identity] + ([comparison] if comparison else []))
    )
    allowed = {"path", "sha256", "fps", "frames", "duration_seconds", "width", "height", "parent"}
    videos = {i: {k: v for k, v in state["videos"][i].items() if k in allowed} for i in selected}
    references = state.get("reference_images") or (
        [state["reference_image"]] if state.get("reference_image") else []
    )
    return {
        "video_id": identity,
        "input_id": input_id,
        "videos": videos,
        "original": videos["source"],
        "request": state["request"]["text"],
        "submitted_prompt": candidate.get("prompt", ""),
        "actual_prompt": candidate.get("execution", {}).get(
            "effective_prompt", candidate.get("prompt", "")
        ),
        "track": state["config"]["execution"]["task_track"],
        "compare_to": comparison,
        "focus": args.get("focus", ""),
        "extra_checks": args.get("extra_checks", []),
        "events": args.get("events", []),
        "references": copy.deepcopy(references),
        "critic": copy.deepcopy(state["config"]["execution"]["critic"]),
    }, None
