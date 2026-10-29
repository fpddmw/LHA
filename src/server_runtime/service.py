"""Connect the unchanged model-led task semantics to the durable resource queue."""
from __future__ import annotations

import copy
import importlib
from pathlib import Path
import re
import sys

from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock
from .media_cache import DecodeCache


def artifact(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


class Service:
    def __init__(self, queue, directory, root, config, *, model_factory=None, renderer=None):
        self.queue, self.directory, self.root = queue, Path(directory).resolve(), Path(root).resolve()
        if self.root != Path(__file__).resolve().parents[2]:
            raise ValueError("Run the service from the same checkout whose code is being fingerprinted")
        self.config = copy.deepcopy(config)
        self.runtime_sources = self.source_inventory()
        with RunLock(self.directory / "configuration"):
            immutable(self.directory / "config.json", self.config)
            immutable(self.directory / "runtime-sources.json", self.runtime_sources)
        self.model_factory = model_factory or self.client
        self.renderer = renderer
        self.decode = DecodeCache(config.get("decode_cache_bytes", 512 * 1024 * 1024))

    def source_inventory(self):
        sources = {}
        for package in ("server_runtime", "planner_harness", "critic_harness", "evaluation", "vlm"):
            for path in sorted((self.root / "src" / package).rglob("*")):
                if path.is_file() and path.suffix in {".py", ".md"}:
                    sources[str(path.relative_to(self.root)).replace("\\", "/")] = sha(path)
        worker = self.root / "scripts/run_planner_worker.py"
        if worker.exists():
            sources["scripts/run_planner_worker.py"] = sha(worker)
        return sources

    def client(self, role):
        spec = self.config.get("models", {}).get(role, {})
        factory = spec.get("factory", "vlm.codex_vlm:CodexVisionModel")
        module, name = factory.split(":")
        client = getattr(importlib.import_module(module), name)(**{"role": role, **spec.get("options", {})})
        if getattr(client, "model", None) != self.config.get("model", "gpt-6.1-sol"):
            raise ValueError("Backend resolved a different model from the frozen service configuration")
        if getattr(client, "reasoning_effort", None) != self.config.get("reasoning_effort", "xhigh"):
            raise ValueError("Backend resolved a different reasoning effort")
        if not callable(getattr(client, "predict_json", None)) or (role != "benchmark_final" and not callable(getattr(client, "predict_text", None))):
            raise ValueError("Backend does not implement the required vision interface")
        return client

    def close(self):
        if self.renderer is not None and hasattr(self.renderer, "close"):
            self.renderer.close()

    def recover(self, job, directory):
        # This path reads an already committed tool response; it must never issue a new call.
        if job["kind"] == "tool" and Path(job["payload"]["request"]).with_name("response.json").exists():
            return self(job, directory)
        return None

    def submit(self, task):
        task = copy.deepcopy(task)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", task["id"]):
            raise ValueError("Task id must be a safe path component")
        source = (self.root / task["source"]).resolve()
        if sha(source) != task["source_sha256"]:
            raise ValueError("Source hash mismatch")
        if not task.get("request") or task.get("max_generations", 3) < 0:
            raise ValueError("Task request and generation budget required")
        execution = task.get("execution", {})
        if "renderer" not in execution:
            raise ValueError("Task requires an explicit renderer profile")
        if execution.get("mode", "live") != "live":
            raise ValueError("Server tasks use live execution; replay belongs to separate validation runs")
        if self.renderer is None:
            resident = self.config.get("renderer", {})
            if resident.get("backend") != "bernini" or execution["renderer"].get("backend") != resident["backend"] or execution["renderer"].get("generation") != resident.get("generation"):
                raise ValueError("Configure the same supported resident renderer before submitting")
        # Final benchmark configuration is deliberately absent from the Planner execution profile.
        if task.get("final_evaluation"):
            if not self.config.get("enable_final_evaluation", False):
                raise ValueError("Final evaluation is disabled for this service")
            cfg = task["final_evaluation"]
            cfg["card_data"] = self.card(cfg.get("card_data") or cfg["card"], task)
            if isinstance(cfg.get("references"), str):
                cfg["references"] = load(self.root / cfg["references"])
        task["source"] = str(source)
        directory = self.directory / "tasks" / task["id"]
        immutable(directory / "task.json", task)
        return self.queue.enqueue(task["id"] + "/planner/start", "planner", "llm", {"task": task, "run": str(directory / "run")})

    def card(self, path, task=None):
        from evaluation.protocol import validate_card
        card = validate_card(copy.deepcopy(path) if isinstance(path, dict) else load(self.root / path))
        if task and (card["source_sha256"] != task["source_sha256"] or card["requirement"] != task["request"]):
            raise ValueError("Final evaluation card must match exact original task")
        return card

    def submit_evaluation(self, case, *, parents=()):
        if not self.config.get("enable_final_evaluation", False):
            raise ValueError("Final evaluation is disabled for this service")
        case = copy.deepcopy(case)
        card = self.card(case.get("card_data") or case["card"])
        source = self.root / card["source_video"]
        output = self.root / case["output_video"]
        if sha(source) != card["source_sha256"] or sha(output) != case["output_sha256"]:
            raise ValueError("Evaluation media hash mismatch")
        case["card_data"] = card
        if case.get("mapping") and isinstance(case["mapping"], str):
            case["mapping"] = load(self.root / case["mapping"])
        if case.get("references") and isinstance(case["references"], str):
            case["references"] = load(self.root / case["references"])
        case["output_video"] = str(output.resolve())
        key = "final/" + case["case_id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", case["case_id"]):
            raise ValueError("Unsafe evaluation case id")
        path = self.directory / "evaluations" / case["case_id"]
        payload = {"case": case, "directory": str(path)}
        prep = self.queue.enqueue(key + "/evidence", "prepare", "cpu", payload, parents=parents, priority=30)
        return self.queue.enqueue(key + "/judge", "judge", "llm", payload, parents=[prep], priority=30)

    def __call__(self, job, directory):
        if self.source_inventory() != self.runtime_sources:
            raise ValueError("Runtime code/manual changed; use a frozen checkout and a new service revision")
        kind, payload = job["kind"], job["payload"]
        if kind == "planner":
            from planner_harness import PlannerHarness
            task, run = payload["task"], Path(payload["run"])
            with RunLock(run):
                harness = PlannerHarness(run, self.model_factory("planner"), root=self.root)
                if (run / "state.json").exists():
                    state = harness.resume()
                else:
                    if sha(task["source"]) != task["source_sha256"]:
                        raise ValueError("Task source changed before planning")
                    state = harness.start(task["source"], task["request"], mode="loop",
                        target=task["execution"].get("renderer", {}).get("backend", "unspecified"),
                        execution=task["execution"], max_turns=task.get("max_turns", 24),
                        max_context_chars=task.get("max_context_chars", 180000), max_generations=task.get("max_generations", 3))
            snapshot = directory / "planner-state.json"
            save(snapshot, state)
            return {"state": state, "artifacts": [artifact(snapshot)]}
        if kind == "tool":
            path = Path(payload["request"])
            request = load(path)
            if request["sha256"] != payload["request_sha256"] or signature({k: v for k, v in request.items() if k != "sha256"}) != request["sha256"]:
                raise ValueError("Signed tool request changed")
            response_path = path.with_name("response.json")
            with RunLock(path.parent / "worker"):
                if response_path.exists():
                    response = load(response_path)
                    if response.get("request_sha256") != request["sha256"] or response.get("mode") != request["mode"]:
                        raise ValueError("Existing tool response mismatch")
                    if response.get("status") not in {"complete", "failed"}:
                        raise ValueError("Tool response is not final")
                else:
                    response = {"request_sha256": request["sha256"], "mode": request["mode"], "status": "complete"}
                    try:
                        if request["kind"] == "generate":
                            if self.renderer is None:
                                from .renderers import PersistentRenderer
                                self.renderer = PersistentRenderer(self.root, self.config["renderer"], self.directory / "gpu")
                            response["payload"] = self.renderer(request, path.parent)
                        elif request["kind"] == "critique":
                            from critic_harness.adapter import critique
                            response["payload"] = critique(request, path.parent, self.root, model=self.model_factory("online_critic"))
                        elif request["kind"] == "evaluate":
                            sys.path.insert(0, str(self.root / "scripts"))
                            from run_planner_worker import evaluate
                            response["payload"] = evaluate(request, path.parent, self.root, model=self.model_factory("online_feedback"))
                        else:
                            raise ValueError("Unknown tool")
                    except Exception as exc:
                        # A definite tool failure is evidence for the Planner, charged to its existing action.
                        response.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                    save(response_path, response)
            artifacts = [artifact(response_path)]
            if request["kind"] == "generate" and response["status"] == "complete":
                video = response["payload"]["video"]
                if sha(video["path"]) != video["sha256"]:
                    raise ValueError("Generated artifact changed")
                artifacts.append(video)
            return {"response": response, "artifacts": artifacts}
        if kind in {"prepare", "judge"}:
            from evaluation.media import prepare
            from evaluation.judges import judge, verify_evidence
            from evaluation.scoring import score
            case, output = payload["case"], Path(payload["directory"])
            card = case["card_data"]
            if sha(case["output_video"]) != case["output_sha256"]:
                raise ValueError("Evaluation output changed")
            evidence_path = output / "evidence/evidence.json"
            if kind == "prepare":
                if evidence_path.exists():
                    evidence = load(evidence_path)
                    verify_evidence(card, evidence)
                    if evidence["output_sha256"] != case["output_sha256"]:
                        raise ValueError("Evidence belongs to another output")
                else:
                    prepare(card, Path(case["output_video"]), evidence_path.parent, root=self.root,
                            dense_ranges=[[0, card["duration_seconds"]]], mapping=case.get("mapping"), decoder=self.decode)
                return {"artifacts": [artifact(evidence_path)]}
            judgment = judge(card, load(evidence_path), self.model_factory("benchmark_final"), output / "judge",
                             references=case.get("references"), creativity_overview=True, creativity_exclude_self=True)
            save(output / "judgment.json", judgment)
            result = {"case_id": case["case_id"], "method": case["method"], "seed": case["seed"],
                      "status": "complete", "result": score(card, judgment)}
            save(output / "record.json", result)
            return {"record": result, "artifacts": [artifact(output / "record.json"), artifact(output / "judgment.json")]}
        raise ValueError("Unknown server job kind")

    def expand(self, job):
        if job["kind"] != "planner":
            return
        state, payload = job["result"]["state"], job["payload"]
        task, run = payload["task"], Path(payload["run"])
        if state["status"] == "waiting_tool":
            identity = state["pending_tool"]
            request = run / "jobs" / identity / "request.json"
            tool = load(request)
            key = task["id"] + "/" + identity
            tool_id = self.queue.enqueue(key, "tool", "gpu" if tool["kind"] == "generate" else "llm",
                {"request": str(request), "request_sha256": tool["sha256"]}, parents=[job["id"]])
            self.queue.enqueue(task["id"] + "/planner/after-" + identity, "planner", "llm", payload, parents=[tool_id])
        elif state["status"] == "complete" and task.get("final_evaluation"):
            cfg = task["final_evaluation"]
            selected = state.get("final", {}).get("video")
            videos = {k: v for k, v in state["videos"].items() if (cfg.get("all_generated", True) and k != "source" and not v.get("imported")) or k == selected}
            for identity, video in videos.items():
                self.submit_evaluation({"case_id": task["id"] + "__" + identity,
                    "method": task.get("method", "continuous_loop") + "__" + identity,
                    "seed": video.get("execution", {}).get("seed", task["execution"].get("renderer", {}).get("seed", 42)), "card_data": cfg["card_data"],
                    "output_video": video["path"], "output_sha256": video["sha256"],
                    "mapping": video.get("time_mapping"), "references": cfg.get("references")}, parents=[job["id"]])
