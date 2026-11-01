"""RSI experiment arms on the existing durable GPU/LLM/CPU resource queue."""
from pathlib import Path
import copy

from .common import ROOT, load, save, sha
from .ledger import digest
from .rsi_data import sealed
from .rsi_validation import verify_manifest, run_task, record_arm
from .rsi_controls import run_control


class Batch:
    def __init__(self, queue, directory, manifest_path, service, *, root=ROOT, judge_factory=None):
        self.queue, self.directory = queue, Path(directory).resolve()
        self.manifest_path, self.root, self.service = str(Path(manifest_path).resolve()), Path(root), service
        self.manifest = verify_manifest(manifest_path)
        self.judge_factory = judge_factory
        sealed(self.directory / "experiment.json", {"manifest": self.manifest_path, "sha256": self.manifest["sha256"]})

    def _run(self, task, arm):
        return self.directory / "runs" / task / arm

    def submit(self, arms=("base", "candidate"), *, score=True):
        allowed = {"base", "candidate", "singlepass", "direct", "best-of-3"}
        if not arms or not set(arms) <= allowed:
            raise ValueError("Choose declared experiment arms")
        arms = list(dict.fromkeys(arms))
        if any(a in arms for a in ("direct", "best-of-3")) and "singlepass" not in arms:
            arms.insert(0, "singlepass")
        sealed(self.directory / "batch-config.json", {"arms": arms, "score": score})
        ids = []
        for task in self.manifest["tasks"]:
            for arm in arms:
                payload = {"task": task["id"], "arm": arm, "score": score}
                if arm in {"direct", "best-of-3"}:
                    # Deferred until singlepass completion, not merely its first queue segment.
                    continue
                ids.append(self.queue.enqueue(task["id"] + "/" + arm + "/start", "rsi_planner", "llm", payload))
        return ids

    def __call__(self, job, directory):
        if verify_manifest(self.manifest_path)["sha256"] != self.manifest["sha256"]:
            raise ValueError("Batch manifest changed")
        kind, p = job["kind"], job["payload"]
        if kind == "tool":
            result = self.service(job, directory)
            response_path = Path(p["request"]).with_name("response.json")
            if response_path.exists():
                response = load(response_path)
                if response["status"] == "failed":
                    raise RuntimeError("Tool outcome is incomplete/uncertain; quarantine this task and reconcile the same job")
            return result
        run = self._run(p["task"], p["arm"])
        if kind == "rsi_planner":
            if p["arm"] in {"direct", "best-of-3"}:
                state = run_control(self.manifest_path, p["task"], p["arm"], self._run(p["task"], "singlepass"), run, root=self.root)
            else:
                state = run_task(self.manifest_path, p["task"], p["arm"], run, self.service.model_factory("planner"), root=self.root)
            if state["status"] not in {"waiting_tool", "complete"}:
                raise RuntimeError("Planner stopped without a complete decision: " + state["status"])
            snapshot = Path(directory) / "planner-state.json"
            save(snapshot, state)
            return {"state": state, "artifacts": [{"path": str(snapshot), "sha256": sha(snapshot)}]}
        if kind == "rsi_judge":
            from .rsi_judge import judge_run
            from evaluation.backends import OpenAICompatibleJudge
            profile = self.manifest["protocol"]["judge"]
            client = self.judge_factory(profile) if self.judge_factory else OpenAICompatibleJudge(model=profile["model"], reasoning_effort=profile.get("reasoning_effort"))
            destination = self.directory / "scores" / p["task"] / p["arm"]
            from .lock import RunLock
            with RunLock(destination):
                judge_run(self.manifest_path, run, destination, client, root=self.root)
            path = destination / "scores.json"
            return {"scores": str(path), "artifacts": [{"path": str(path), "sha256": sha(path)}]}
        if kind == "rsi_record":
            path = self.directory / "receipts" / p["task"] / (p["arm"] + ".json")
            record_arm(self.manifest_path, run, load(p["scores"]), path)
            return {"receipt": str(path), "artifacts": [{"path": str(path), "sha256": sha(path)}]}
        raise ValueError("Unsupported RSI batch job")

    def expand(self, job):
        p, result = job["payload"], job["result"]
        if job["kind"] == "rsi_judge":
            self.queue.enqueue(p["task"] + "/" + p["arm"] + "/record", "rsi_record", "cpu", {**p, "scores": result["scores"]}, parents=[job["id"]])
        if job["kind"] != "rsi_planner":
            return
        state, run = result["state"], self._run(p["task"], p["arm"])
        key = p["task"] + "/" + p["arm"]
        if state["status"] == "waiting_tool":
            identity = state["pending_tool"]
            request = run / "jobs" / identity / "request.json"
            tool = load(request)
            tool_id = self.queue.enqueue(key + "/" + identity, "tool", "gpu" if tool["kind"] == "generate" else "llm",
                                         {"request": str(request), "request_sha256": tool["sha256"]}, parents=[job["id"]])
            self.queue.enqueue(key + "/after-" + identity, "rsi_planner", "llm", p, parents=[tool_id])
        elif state["status"] == "complete":
            if p["score"]:
                self.queue.enqueue(key + "/judge", "rsi_judge", "llm", p, parents=[job["id"]], priority=30)
            if p["arm"] == "singlepass":
                for arm in load(self.directory / "batch-config.json")["arms"]:
                    if arm in {"direct", "best-of-3"}:
                        self.queue.enqueue(p["task"] + "/" + arm + "/start", "rsi_planner", "llm", {**p, "arm": arm}, parents=[job["id"]])
        self.status()

    def recover(self, job, directory):
        if job["kind"] in {"rsi_planner", "rsi_judge", "rsi_record"}:
            return self(job, directory)  # Durable bounded calls/accepted actions resume in place.
        if job["kind"] == "tool" and Path(job["payload"]["request"]).with_name("response.json").exists():
            return self(job, directory)  # Apply the same uncertainty/quarantine checks on recovery.
        return None

    def close(self):
        self.status()
        from .rsi_reporting import health
        runs = [p.parent for p in (self.directory / "runs").glob("*/*/state.json")]
        if runs:
            revision = digest({str(p): sha(p / "state.json") for p in runs})[:20]
            path = self.directory / "health" / (revision + ".json")
            result = health(runs, path, thresholds=self.manifest["protocol"].get("health_thresholds"))
            save(self.directory / "health-latest.json", {"path": str(path), "sha256": sha(path)})
            if result["status"] == "needs_review":
                self.queue.dispatch("drain")
        self.service.close()

    def status(self):
        rows = self.queue.rows()
        states = {r["state"] for r in rows}
        result = {"counts": {s: sum(r["state"] == s for r in rows) for s in states},
                  "quarantined": [{"job": r["id"], "key": r["key"], "error": r.get("error")} for r in rows if r["state"] in {"failed", "needs_review"}],
                  "generation_slots": self.queue.limits["gpu"], "llm_slots": self.queue.limits["llm"], "manifest_sha256": self.manifest["sha256"]}
        save(self.directory / "batch-status.json", result)
        return result
