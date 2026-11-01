"""Delivery-only seven-task RSI run on the authorized single Bernini GPU."""
from pathlib import Path
import copy
import json
import os
import sys
import time
import argparse

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/deploy")]
from planner_harness.common import load, save, sha
from planner_harness.execution import immutable
from planner_harness.delivery import verify_delivery as verify_task_delivery
from planner_harness.knowledge import Knowledge
from server_runtime.queue import Queue
from server_runtime.service import Service
from server_runtime.engine import Engine
from run_prompt_probe import inspect_video

OUT = ROOT / "out/fewshot-delivery"
GENERATION = dict(num_inference_steps=40, guidance_mode="v2v_apg", max_image_size=848,
                  negative_prompt="", prompt_enhancer=False)


class DeliveryService(Service):
    def __call__(self, job, directory):
        result = super().__call__(job, directory)
        if job["kind"] == "tool" and result["response"]["status"] != "complete":
            raise RuntimeError("Tool failed; reconcile the existing request before resuming: " + result["response"].get("error", ""))
        if job["kind"] == "planner" and result["state"]["status"] not in {"complete", "waiting_tool"}:
            raise RuntimeError("Planner requires review: " + result["state"]["status"])
        return result

    def recover(self, job, directory):
        if job["kind"] == "planner":
            return self(job, directory)
        if job["kind"] == "tool" and Path(job["payload"]["request"]).with_name("response.json").exists():
            return self(job, directory)
        return None

    def close(self):
        # Keep the resident renderer across the first-task admission gate.
        pass


def freeze_materials():
    folder = OUT / "frozen"
    if not (folder / "materials.json").exists():
        Knowledge(ROOT).freeze(folder / "planner-knowledge.json")
        snapshot = copy.deepcopy(load(folder / "planner-knowledge.json"))
        paths = {r["path"] for r in snapshot["experiences"]}
        ids = {r["id"] for r in snapshot["experiences"]}
        snapshot["experiences"] = []
        snapshot["entrances"] = {k: v for k, v in snapshot["entrances"].items() if k not in ids}
        for key in ("documents", "asset_hashes"):
            snapshot[key] = {p: d for p, d in snapshot[key].items() if p not in paths}
        save(folder / "critic-knowledge.json", snapshot)
        package = ROOT / "src/critic_harness"
        save(folder / "critic-instructions.json", {p.relative_to(package).as_posix(): p.read_text() for p in package.rglob("*.md")})
        immutable(folder / "materials.json", {key: {"path": str(folder / name), "sha256": sha(folder / name)}
                  for key, name in (("planner", "planner-knowledge.json"), ("knowledge", "critic-knowledge.json"), ("instructions", "critic-instructions.json"))})
    frozen = load(folder / "materials.json")
    for item in frozen.values():
        assert sha(item["path"]) == item["sha256"], "Frozen material changed"
    return frozen


def verify_delivery(identity):
    return {"id": identity, **verify_task_delivery(OUT / "service/tasks" / identity / "run")}


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New isolated delivery run; never overwrite an archived batch")
    parser.add_argument("--task-cards", required=True, help="Directory of reviewed independent cards named by sample ID")
    args = parser.parse_args()
    OUT = Path(args.output).resolve()
    frozen = freeze_materials()
    assets = ROOT / "deployment/bernini-assets.json"
    config = {"model": "gpt-6.1-sol", "reasoning_effort": "high", "enable_final_evaluation": False,
              "renderer": {"backend": "bernini", "asset_manifest": str(assets), "asset_manifest_sha256": sha(assets),
                           "gpu_lock": "/root/lha-runtime/gpu0", "generation": GENERATION}}
    queue = Queue(OUT / "queue.sqlite", {"gpu": 1, "llm": 2, "cpu": 2})
    directory = OUT / "service"
    service = DeliveryService(queue, directory, ROOT, config)
    rows = load(ROOT / "benchmark_data/fewshot_index.json")
    tasks = []
    for row in rows:
        info = inspect_video(ROOT / row["source_video"])
        count = ((info["frames"] - 1) // 4) * 4 + 1
        task = {"id": row["sample_id"], "source": row["source_video"], "source_sha256": row["source_video_sha256"],
                "request": row["instruction"], "completion_mode": "delivery", "max_generations": None, "max_turns": None, "max_context_chars": 180000,
                "execution": {"mode": "live", "renderer": {"backend": "bernini", "seed": 42,
                    "output": {"frames": count, "fps": info["fps"]}, "generation": GENERATION},
                    "critic": {"model": "gpt-6.1-sol", "reasoning_effort": "high", "max_turns": 12}},
                "rsi": {"seed_sequence": {"start": 42, "step": 1}, "knowledge_snapshot": frozen["planner"],
                        "task_card": str((Path(args.task_cards) / (row["sample_id"] + ".json")).resolve()),
                        "frozen_critic": {k: frozen[k] for k in ("knowledge", "instructions")}},
                "run_instructions": "Work toward delivery of a suitable video for the original request. There is no fixed generation count. You choose the input, prompt, further attempts and delivery judgment. A resource limit, failed operation or lack of a promising repair leaves the task incomplete; retain the best candidate and report the blockage. Report unresolved requirements and delivery tradeoffs honestly. Automatic frozen Critic feedback follows each generation and informs your judgment. Independent benchmark evaluation is not available. The Bernini encoder allows 512 tokens including its official prefix; use concise concrete English prompts that fit this limit."}
        tasks.append(task)
    immutable(OUT / "tasks.json", tasks)
    try:
        service.submit(tasks[0])
        Engine(queue, directory, service, service.expand).run(once=True)
        first = verify_delivery(tasks[0]["id"])
        immutable(OUT / "first-task-passed.json", first)
        for task in tasks[1:]:
            service.submit(task)
        Engine(queue, directory, service, service.expand).run(once=True)
        results = [verify_delivery(t["id"]) for t in tasks]
        save(OUT / "deliveries.json", {"status": "complete", "results": results, "independent_evaluation": "not_requested"})
        print(json.dumps({"status": "complete", "deliveries": len(results)}), flush=True)
    finally:
        Service.close(service)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        save(OUT / "failure.json", {"at": time.time(), "type": type(exc).__name__, "error": str(exc)})
        raise
