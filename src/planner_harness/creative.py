"""Small profile integration for a model-led, non-learning creative loop."""
from __future__ import annotations

import copy
from pathlib import Path

from .common import save

WORKFLOW = "creative_loop_v1"


def active(state):
    return state.get("config", {}).get("workflow") == WORKFLOW


def configure(harness, execution):
    from critic_harness.one_shot import frozen_profile, verify_profile
    from .creative_knowledge import CreativeKnowledge
    profile = copy.deepcopy(execution or {})
    if any(key in profile for key in ("evaluation", "rsi", "task_card")):
        raise ValueError("Creative loop excludes task cards, RSI and online independent evaluation")
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
    harness.knowledge = CreativeKnowledge(harness.root)
    harness.state["config"]["execution"] = profile
    save(harness.output / "critic-profile.json", frozen)


def system_prompt(harness):
    operations = Path(__file__).with_name("CREATIVE_LOOP.md").read_text(encoding="utf-8")
    row = harness.knowledge.items["manual"]
    return operations + "\n\n" + harness.knowledge.document(row)["text"]


def review_payload(harness, args):
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
