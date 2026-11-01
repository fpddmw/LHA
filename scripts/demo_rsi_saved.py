"""Read saved development traces, collect evidence, and demonstrate prefix-only replay.

The replay decisions below are explicitly scripted API fixtures. No model or GPU is called.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness.common import load, save, sha
from planner_harness.ledger import digest
from planner_harness.rsi_data import local_path, split_manifest, collect
from planner_harness.rsi_replay import replay, prefix


class DemonstrationModel:
    model = "scripted-interface-demonstration"
    reasoning_effort = "none"
    def __init__(self):
        self.calls = 0
    def predict_text(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return json.dumps({"action": "read", "arguments": {"targets": [{"id": "choose-editing-input", "section": "I3"}, {"id": "express-edits", "section": "X6"}]}})
        return json.dumps({"action": "finish", "arguments": {"video": "v2", "stop_reason": "no_promising_attempt",
            "message": "Scripted interface fixture only; this is not a new model judgment or a measured policy improvement."}})


def main():
    base = ROOT / "out/agent_loop_live/20261030"
    destination = ROOT / "out/rsi_implementation/20261030/saved-demo"
    states = sorted(base.glob("phase2/completed-*/tasks/*/run/state.json")) + sorted(base.glob("ditto-phase2/completed-*/tasks/*/run/state.json"))
    excluded = {"completed-027-full", "completed-041-full", "completed-shutdown-final-checkpoint", "completed-shutdown-pending-snapshot"}
    states = [p for p in states if not any(part in excluded for part in p.parts)]
    tasks, output_hashes = {}, set()
    for path in states:
        state = load(path)
        task = state["request"]
        source = local_path(task["source"]["path"])
        if sha(source) != task["source"]["sha256"]:
            raise ValueError("Archived source changed")
        identity = "dev-" + digest({"source": task["source"]["sha256"], "request": task["text"]})[:16]
        tasks[identity] = {"id": identity, "source": str(source), "source_sha256": task["source"]["sha256"],
                           "source_group": source.parent.name if "fewshot" not in str(source) else "fewshot-" + source.parent.name,
                           "split": "D", "request": task["text"], "renderer": "historical_development"}
        output_hashes.update(v["sha256"] for v in state["videos"].values() if v.get("job_id"))
    split_manifest(list(tasks.values()), destination / "development-sources.json", exposed_sources={t["source_sha256"] for t in tasks.values()})
    score_paths = []
    for folder in ("independent-evaluation", "independent-evaluation-027", "independent-evaluation-024-fewshot", "ditto-independent-evaluation"):
        for path in (base / folder).rglob("record.json"):
            judgment = path.with_name("judgment.json")
            if judgment.exists() and load(judgment).get("output_sha256") in output_hashes:
                score_paths.append(path)
    collection = collect([p.parent for p in states], destination / "development-sources.json", destination / "development.json", independent_records=score_paths)
    input_path = base / "phase2/completed-024-pair/tasks/024__long__full_knowledge/run/calls/event-0009/input.json"
    _, payload, state, _ = prefix(input_path)
    save(destination / "original-prefix.json", {"input_sha256": sha(input_path), "payload": payload, "available_videos": list(state["videos"]),
                                               "scope": "Actual pre-v3 context; no final state was loaded by replay."})
    result = replay(input_path, "knowledge/staged/e1-20261030/catalog.json", destination / "replay-calibrated", DemonstrationModel())
    save(destination / "summary.json", {"historical_collection": collection["counts"], "development_task_variants": len(tasks),
        "replay": {"status": result["status"], "actual_model_calls": 0, "scripted_calls": result["model_calls"], "renderer_calls": 0},
        "scope": "Evidence reuse and software demonstration. Not a new experiment, preference result or quality improvement."})
    print(json.dumps(load(destination / "summary.json"), indent=2))


if __name__ == "__main__":
    main()
