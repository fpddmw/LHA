"""Compute controls share seeds, automatic reviews and the declared final selector."""
from pathlib import Path
import json
from .common import load, save
from .ledger import english
from .rsi_data import sealed
from .rsi_validation import verify_manifest, runtime_hashes, common_selection, require_resolved_tool
from .lock import RunLock
from .runner import PlannerHarness
from .execution import immutable


class FixedPromptControl:
    model = "deterministic-fixed-prompt-control"
    reasoning_effort = "none"

    def __init__(self, requirements, prompt, limit):
        self.requirements, self.prompt, self.limit = requirements, prompt, limit

    def predict_text(self, *, user_text, **kwargs):
        context = json.loads(user_text)
        if not context.get("task_memory", {}).get("requirements"):
            return json.dumps({"action": "requirements", "arguments": {"items": self.requirements}})
        count = context["resource_status"]["generation_requests"]
        if count < self.limit:
            return json.dumps({"action": "generate", "arguments": {"input_video": "source", "prompt": self.prompt,
                "intent": {"targets": [r["id"] for r in self.requirements], "change": "Fixed-prompt sampling control.",
                           "expect": "Sample the same requested realization with the next paired seed."}}})
        # Selection is applied by the same declared common selector after the run.
        return json.dumps({"action": "finish", "arguments": {"video": None, "stop_reason": "budget", "message": "Sampling complete; use the frozen common selector."}})


def run_control(manifest_path, task_id, kind, singlepass_run, output, *, worker=None, root):
    manifest = verify_manifest(manifest_path)
    if manifest["runtime"] != runtime_hashes():
        raise ValueError("Runtime changed after the control protocol was frozen")
    if kind not in {"direct", "best-of-3"}:
        raise ValueError("Use direct or best-of-3")
    if len(manifest["protocol"]["seed_schedule"]) < 3 and kind == "best-of-3":
        raise ValueError("Best-of-3 requires three paired seeds")
    if kind == "best-of-3" and manifest["protocol"]["generation_budget"] < 3:
        raise ValueError("Best-of-3 needs an experiment budget of at least three attempts")
    task = next(t for t in manifest["tasks"] if t["id"] == task_id)
    previous = load(Path(singlepass_run) / "state.json")
    binding = load(Path(singlepass_run) / "validation-binding.json")
    if binding != {"manifest_sha256": manifest["sha256"], "task": task_id, "arm": "singlepass"}:
        raise ValueError("Use the matching single-pass Planner run")
    if previous["status"] != "complete":
        raise ValueError("Complete the single-pass control before sharing its first sample")
    job = next(j for j in previous["jobs"].values() if j["kind"] == "generate")
    if job["payload"]["input_id"] != "source":
        raise ValueError("Control prompt must have been planned for the source")
    prompt = task["request"] if kind == "direct" else job["payload"]["prompt"]
    english(prompt)
    items = job["payload"]["requirements"]["items"]
    model = FixedPromptControl(items, prompt, 1 if kind == "direct" else 3)
    output = Path(output).resolve()
    frozen = manifest["frozen"]
    with RunLock(output):
        sealed(output / "validation-binding.json", {"manifest_sha256": manifest["sha256"], "task": task_id, "arm": kind})
        sealed(output / "control-origin.json", {"singlepass_job_sha256": job["sha256"], "prompt": prompt, "scope": "Deterministic sampling control; not adaptive Planner behavior."})
        harness = PlannerHarness(output, model, root=root)
        require_resolved_tool(output, manifest["protocol"])
        state = harness.resume() if (output / "state.json").exists() else harness.start(task["source"], task["request"],
            target=task["renderer"], mode="loop", execution=manifest["protocol"]["execution"], max_generations=model.limit,
            rsi={"task_card": task.get("card"), "seed_schedule": manifest["protocol"]["seed_schedule"], "knowledge_snapshot": frozen["base-knowledge.json"],
                 "frozen_critic": {"knowledge": frozen["critic-knowledge.json"], "instructions": frozen["critic-instructions.json"]}})
        while state["status"] == "waiting_tool":
            directory = output / "jobs" / state["pending_tool"]
            pending = state["jobs"][state["pending_tool"]]
            if kind == "best-of-3" and pending["kind"] == "generate" and state["generation_requests"] == 1:
                # Share the actual first sample, not another nominally identical seed run.
                a, b = pending["payload"], job["payload"]
                if a["prompt"] != b["prompt"] or a["input"]["sha256"] != b["input"]["sha256"] or a["renderer"] != b["renderer"]:
                    raise ValueError("First-sample reuse requires the identical rendering recipe")
                first = next(v for v in previous["videos"].values() if v.get("job_id") == job["id"])
                response = load(Path(singlepass_run) / "jobs" / job["id"] / "response.json")
                if response["status"] != "complete":
                    raise ValueError("First sample is unavailable")
                import copy
                response = copy.deepcopy(response)
                response["request_sha256"] = pending["sha256"]
                response["payload"]["video"] = {"path": first["path"], "sha256": first["sha256"]}
                response["payload"]["reuse_provenance"] = {"run": str(Path(singlepass_run).resolve()), "request_sha256": job["sha256"],
                    "output_sha256": first["sha256"], "scope": "Shared first sample; no additional renderer call."}
                immutable(directory / "response.json", response)
            elif worker:
                worker(directory / "request.json", directory / "response.json")
            else:
                break
            if not (directory / "response.json").exists():
                break
            require_resolved_tool(output, manifest["protocol"])
            state = harness.resume()
        if state["status"] == "complete":
            save(output / "common-selection.json", {"video": common_selection(state, manifest["protocol"]["selector"]), "selector": manifest["protocol"]["selector"]})
    return state
