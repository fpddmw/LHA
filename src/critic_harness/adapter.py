"""Explicit opt-in integration with durable Planner tool jobs."""
from pathlib import Path

from planner_harness.common import load, save


PLANNER_MANUAL = """
## Optional active Critic

This task has an active, evidence-seeking Critic. `critique` takes `video`, optional
`compare_to` (another available ID) and `question` (what the feedback should help clarify).
It inspects the original task and actual input as well as the candidate. It can obtain
local or continuous evidence, consult knowledge and return strengths, problems,
comparison tradeoffs and unknowns. Its report is online feedback, not independent
benchmark scoring. You retain the choice of input, prompt, next tool and when to finish.
The runtime waits for the Critic and then resumes this task; do not poll.
Imported Critic feedback has an identity map and a verifiable report path. Treat it
as external evidence with its stated scope. You can inspect its unresolved questions
or act on supported findings; no fixed sequence or acceptance threshold is imposed.
"""


def critique(job, directory, root, model=None):
    if job["payload"].get("critic", {}).get("protocol") == "lha-creative-review-v1":
        from .one_shot import run_review
        return run_review(job["payload"], directory, model=model)
    from .runner import CriticHarness, load_feedback
    from vlm.codex_vlm import CodexVisionModel
    payload = job["payload"]
    directory = Path(directory) / "active-critic"
    spec = {"request": payload["request"], "candidate": payload["video_id"],
            "compare_to": payload.get("compare_to"),
            "question": payload.get("question", ""), "videos": payload["videos"],
            "duration_seconds": payload["critic"].get("duration_seconds", payload["original"]["duration_seconds"])}
    for key in ("requirements", "frozen_critic"):
        if key in payload:
            spec[key] = payload[key]
    if model is None:
        model = CodexVisionModel(role="online_critic")
        for key in ("model", "reasoning_effort"):
            if key in payload["critic"]:
                setattr(model, key, payload["critic"][key])
    harness = CriticHarness(directory, model, root=root)
    if (directory / "state.json").exists():
        state = harness.resume()
    else:
        state = harness.start(spec, max_turns=payload["critic"].get("max_turns", 18))
    if state["status"] != "complete":
        raise RuntimeError(f"Critic stopped with {state['status']}; review trace retained at {directory}")
    return load_feedback(directory / "feedback.json", payload["request"], payload["videos"])
