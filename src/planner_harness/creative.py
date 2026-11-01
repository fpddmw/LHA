"""Small profile integration for a model-led, non-learning creative loop."""
from __future__ import annotations

import copy
from pathlib import Path

from .common import save

WORKFLOW = "creative_loop_v1"


def role_settings(config, role):
    """One explicit model policy for CLI, service and one-shot construction."""
    if role not in {"planner", "online_critic"}:
        raise ValueError("Creative service supports Planner and online Critic roles only")
    key = "planner" if role == "planner" else "critic"
    expected = {"model": "gpt-6.1-sol", "reasoning_effort": "high"}
    nested = config.get(key, {})
    options = config.get("models", {}).get(role, {}).get("options", {})
    for setting, value in expected.items():
        for supplied in (config, nested, options):
            if setting in supplied and supplied[setting] != value:
                raise ValueError(f"Creative {role} requires {setting}={value}")
    return expected


def active(state):
    return state.get("config", {}).get("workflow") == WORKFLOW


def configure(harness, execution):
    from critic_harness.one_shot import frozen_profile, verify_profile
    from .creative_knowledge import CreativeKnowledge
    profile = copy.deepcopy(execution or {})
    from .continuation import configure as configure_continuation
    configure_continuation(harness.state, profile.pop('continuation_policy', None))
    if any(key in profile for key in ("evaluation", "rsi", "task_card")):
        raise ValueError("Creative loop excludes task cards, RSI and online independent evaluation")
    if profile.get("experiment_profile"):
        verify_experiment(profile["experiment_profile"], harness.root)
    mode = profile.setdefault("experience_mode", "full")
    if mode not in {"full", "none"}:
        raise ValueError("Experience mode must be full or none")
    supplied = profile.get("critic")
    frozen = frozen_profile()
    if supplied:
        if supplied.get("protocol", frozen["protocol_id"]) != frozen["protocol_id"]:
            raise ValueError("Legacy Critic protocol cannot be mixed with creative loop")
        if supplied.get("frozen_profile"):
            verify_profile(supplied["frozen_profile"])
        if supplied.get("model", frozen["model"]) != frozen["model"] or supplied.get("reasoning_effort", "high") != "high":
            raise ValueError("Creative Critic is fixed to gpt-6.1-sol/high")
        if set(supplied) - {"model", "reasoning_effort", "frozen_profile", "protocol"}:
            raise ValueError("Legacy Critic configuration is not valid in creative loop")
    profile["critic"] = {"protocol": frozen["protocol_id"], "frozen_profile": frozen}
    harness.knowledge = CreativeKnowledge(harness.root, experience_mode=profile.get("experience_mode", "full"))
    harness.state["config"]["execution"] = profile
    from .delivery_review import PROTOCOL as DELIVERY_REVIEW
    harness.state["config"]["delivery_review_protocol"] = DELIVERY_REVIEW
    save(harness.output / "critic-profile.json", frozen)


def experiment_profile(root):
    """Optional shared cohort identity; no jobs, data splits or learning cycle."""
    from .common import sha
    from .execution import signature
    from .creative_knowledge import CreativeKnowledge
    from critic_harness.one_shot import frozen_profile
    from evaluation.creative import JUDGES, judge_identity
    root = Path(root).resolve()
    files = {}
    for package in ("planner_harness", "critic_harness", "server_runtime", "evaluation", "vlm", "experiments"):
        for path in sorted((root / "src" / package).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".md"}:
                files[path.relative_to(root).as_posix()] = sha(path)
    scopes = {}
    paths = set()
    for mode in ("full", "none"):
        knowledge = CreativeKnowledge(root, experience_mode=mode)
        scopes[mode] = {identity: {"path": row["path"], "sha256": sha(root / row["path"])}
                        for identity, row in knowledge.items.items() if (root / row["path"]).is_file()}
        paths.update(knowledge.paths)
        paths.add(knowledge.allowlist.get("operations_manual", "src/planner_harness/CREATIVE_LOOP.md"))
    for relative in sorted(paths):
        path = root / relative
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".py", ".html", ".txt", ".jpg", ".jpeg", ".png", ".webp"}:
            files[relative] = sha(path)
    for relative in ("knowledge/creative-loop/manifest.json", "knowledge/source-map.json", knowledge.allowlist.get("curated_catalog")):
        if relative is None:
            continue
        files[relative] = sha(root / relative)
    for relative in ("scripts/run_creative_fewshot.py", "scripts/run_creative_judge.py", "scripts/run_planner_worker.py",
                     "scripts/manage_creative_run.py", "scripts/deploy/run_prompt_probe.py", "configs/creative-loop-v1.json"):
        files[relative] = sha(root / relative)
    from .continuation import VERSION as CONTINUATION
    from .delivery_review import PROTOCOL as DELIVERY_REVIEW
    body = {"protocol": "creative-experiment-v1", "runtime_policy":{'continuation':CONTINUATION,'delivery_review':DELIVERY_REVIEW}, "critic": frozen_profile(),
            "planner": role_settings({}, "planner"), "independent_judges": [judge_identity(j) for j in JUDGES],
            "files": files, "knowledge_scopes": scopes}
    return {**body, "sha256": signature(body)}


def verify_experiment(path, root):
    from .common import load
    binding = load(path)
    if binding != experiment_profile(root):
        raise ValueError("This runtime/knowledge differs from the shared experimental profile")
    return binding


def system_prompt(harness):
    operations = (harness.root / harness.knowledge.allowlist.get("operations_manual", "src/planner_harness/CREATIVE_LOOP.md")).read_text(encoding="utf-8")
    row = harness.knowledge.items["manual"]
    return operations + "\n\n" + harness.knowledge.document(row)["text"]


def review_payload(harness, args):
    from critic_harness.one_shot import validate_focus
    state = harness.state
    if set(args) - {"video", "compare_to", "focus", "extra_checks"}:
        raise ValueError("Critique accepts video, compare_to, focus and extra_checks only")
    identity, comparison = args.get("video"), args.get("compare_to")
    if identity not in state["videos"] or identity == "source":
        raise ValueError("Review an available candidate")
    if comparison is not None and (not isinstance(comparison, str) or comparison not in state["videos"] or comparison == identity):
        raise ValueError("Choose one different available comparison video")
    focus, checks = args.get("focus", ""), args.get("extra_checks", [])
    if not isinstance(focus, str) or not isinstance(checks, list) or any(not isinstance(c, str) or not c.strip() for c in checks):
        raise ValueError("focus is text; extra_checks is a list of nonempty text")
    validate_focus(focus, checks)
    for key, feedback in state["evaluations"].items():
        if feedback.get("video_id") == identity:
            return None, {"status": "complete", "cached": True, "feedback_id": key, "feedback": feedback}
    for key, job in state["jobs"].items():
        if job["kind"] == "critique" and job["payload"]["video_id"] == identity:
            return None, {"status": "unavailable", "job_id": key,
                          "message": "This candidate already has a review request. Inspect its recorded outcome and the video; no follow-up review is created."}
    selected = list(dict.fromkeys(["source", identity] + ([comparison] if comparison else [])))
    # Persist only media identity/metadata, never generation prompts or Planner intent.
    allowed = {"path", "sha256", "fps", "frames", "duration_seconds", "width", "height"}
    videos = {i: {k: v for k, v in state["videos"][i].items() if k in allowed} for i in selected}
    return {"video_id": identity, "videos": videos, "original": videos["source"],
            "request": state["request"]["text"], "compare_to": comparison,
            "focus": focus, "extra_checks": checks,
            "critic": copy.deepcopy(state["config"]["execution"]["critic"])}, None
