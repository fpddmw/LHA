"""Inspect a local loop replay using saved 041 assets; no model inference or generation."""
import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_loop import AgentLoop
from agent_loop.core import digest, publish_response
from planner_harness.common import load, save, sha
from planner_harness.video import Video


class ReplayPlanner:
    model = "saved-proposal-replay-no-inference"
    reasoning_effort = "none"

    def __init__(self, proposal):
        self.proposal = copy.deepcopy(proposal)

    def predict_text(self, **kwargs):
        proposal = self.proposal
        proposal["sources"] = []
        proposal["self_review"] = "This scripted transition reuses a saved proposal to check feedback wiring. No new model decision or measured improvement is claimed."
        return json.dumps({"action": "submit", "purpose": "Replay a saved proposal for continuation testing.", "arguments": proposal})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--planner-run", default=str(ROOT / "out/planner_harness/20261029/041_storybook"))
    parser.add_argument("--archived-case", default=str(ROOT / "out/prompt_probe/20261029_bernini/041__long"))
    args = parser.parse_args()
    archived = Path(args.archived_case).resolve()
    run = Path(args.planner_run).resolve()
    output = Path(args.output).resolve()
    if (output / "state.json").exists():
        raise ValueError("Replay already exists; use a new output directory")
    video = Video(archived / "native.mp4", output).info
    archived_input = load(archived / "input.json")
    original = load(run / "state.json")["request"]["source"]
    if original["sha256"] != archived_input["source_video_sha256"]:
        raise ValueError("Archived video belongs to a different original")
    loop = AgentLoop(output)
    loop.initialize(run, {"backend": "archived-replay", "settings": {},
                          "output": {"frames": video["frames"], "fps": video["fps"]}}, mode="replay", max_candidates=2)

    def respond(payload):
        state = load(output / "state.json")
        publish_response(output, {"request_sha256": state["job"]["sha256"], "mode": "replay", "status": "complete", "payload": payload})
        return loop.advance()

    for iteration in range(2):
        request = loop.state["job"]["payload"]
        respond({"video": video, "replay_provenance":
                 "The archived Bernini 041 long-prompt video is reused for plumbing verification. It was generated earlier with a different prompt; neither this loop request nor its revision was rendered. Both candidates deliberately reuse the same video.",
                 "execution": {"backend": "archived-replay", "settings": {}, "preflight": "not_run",
                               "requested_prompt": request["prompt"], "effective_prompt": request["prompt"],
                               "prompt_transforms": [], "input_sha256": request["input_video"]["sha256"],
                               "archived_input_path": str(archived / "input.json"), "archived_input_sha256": sha(archived / "input.json"),
                               "archived_actual_prompt": archived_input["prompt"],
                               "archived_actual_effective_text": archived_input["effective_text"]}})
        respond({"protocol": {"id": "plumbing-replay-no-quality-evaluation", "version": "1"},
                 "findings": [], "metrics": {}, "uncertainties": ["No evaluation ran for this loop. The archived video does not test the submitted Planner prompt."]})
        evaluation = loop.state["candidates"][-1]["evaluation"]
        respond({"policy": {"id": "scripted-transition-fixture", "version": "1"},
                 "evaluation_sha256": digest(evaluation), "selection": "accept" if iteration == 0 else "reject",
                 "next_action": "revise" if iteration == 0 else "stop", "input": "original", "instruction_mode": "full",
                 "reason": "Exercise acceptance, source restart, rejection and incumbent retention; this decision does not assess video quality."})
        if iteration == 0:
            loop.revise(ReplayPlanner(load(run / "proposal.json")))
    save(output / "verification.json", {"mode": "replay", "new_model_calls": 0, "new_video_generations": 0,
                                       "candidates": len(loop.state["candidates"]), "incumbent": loop.state["incumbent"],
                                       "status": loop.state["status"], "initial_planner_run": str(run),
                                       "archived_video": str(archived / "native.mp4"),
                                       "checked": ["Exact planning handoff adoption", "Versioned adapter jobs and receipts", "Child Planner feedback context", "Original-source restart", "Rejected candidate does not replace incumbent"]})
    print(json.dumps({"status": loop.state["status"], "report": str(output / "report.md")}, indent=2))


if __name__ == "__main__":
    main()
