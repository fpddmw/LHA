"""Inspect or resume a PE tokenizer refusal using its original budget and videos."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def retry_render(output, topic, device, failed_slot, reason, *, execute=False):
    """Retry an inspected pre-dispatch failure with the already saved prompt."""
    from experiments.recovery import pe_prompt_recovery_plan
    from experiments.unified_benchmark import Runtime
    from experiments.render_profiles import renderer_spec
    from planner_harness import accounting
    from planner_harness.common import load, save, sha
    from planner_harness.execution import immutable, signature
    from planner_harness.lock import RunLock
    from planner_harness.resources import ResourceExhausted
    from server_runtime.queue import Queue
    from server_runtime.service import Service

    output = Path(output).resolve()
    match = re.fullmatch(r"(\d+)-prompt-([12])", failed_slot)
    if not match or not reason.strip():
        raise ValueError("Specify the inspected prompt-revision render and recovery reason")
    plan = pe_prompt_recovery_plan(output, topic, device)
    if plan["status"] == "complete":
        return plan
    number, revision = map(int, match.groups())
    directory = output / "methods" / topic / "pe-loop"
    worker = Path(plan["worker"])
    slot = worker / "baselines" / topic / "pe-loop" / failed_slot
    request, response = load(slot / "request.json"), load(slot / "response.json")
    if (request["sha256"] != signature({k: v for k, v in request.items() if k != "sha256"})
            or response.get("request_sha256") != request["sha256"]
            or response.get("status") != "failed" or response.get("outcome_unknown")
            or request.get("accounting_scope") != plan["scope"]
            or (slot / "render-started.json").exists() or (slot / "renderer-input.json").exists()):
        raise ValueError("Retry requires an inspected failure before render dispatch")
    operation = accounting.operation(plan["scope"], request["sha256"])
    if operation and operation["status"] != "not_submitted":
        raise ValueError("Original render has a recorded submission")
    compact = load(slot.parent / str(number) / "prompt-revisions" / str(revision) / "prompt.json")
    prompt = request["payload"]["prompt"]
    if signature(compact["value"]) != compact["sha256"] or compact["value"] != prompt:
        raise ValueError("Use the original saved compact prompt")
    batch = load(output / "batch.json")
    if number >= batch["max_generations"]:
        raise ValueError("Retry must belong to a configured PE round")
    task = next(t for t in batch["topics"] if t["id"] == topic)
    seed = request["payload"]["renderer"]["seed"]
    expected = {"input_id": "source", "input": task["source_info"], "prompt": prompt,
                "renderer": renderer_spec(task, batch, seed)}
    if request["payload"] != expected:
        raise ValueError("Retry must retain the original input and generation settings")
    retry_slot = failed_slot + "-retry-1"
    record = {"failed_request_sha256": request["sha256"], "failed_response_sha256": sha(slot / "response.json"),
              "retry_slot": retry_slot, "reason": reason, "prompt_sha256": compact["sha256"],
              "seed": seed, "scope": plan["scope"], "script_sha256": sha(__file__)}
    if not execute:
        return {"status": "retry_ready", **record, "clock": plan["clock"], "model_calls": 0}
    with RunLock(output / "unified-owner"), RunLock(output / "batch-owner"), RunLock(directory / "loop-owner"):
        candidate_path = directory / "rounds" / f"{number + 1:04d}" / "candidate.json"
        if candidate_path.exists():
            saved = load(candidate_path)
            if signature(saved["value"]) != saved["sha256"]:
                raise ValueError("Saved candidate changed")
            return {"status": "candidate_ready", "model_calls": 0}
        try:
            accounting.check_task(plan["scope"])
        except ResourceExhausted:
            return {"status": "deadline_settlement", "model_calls": 0}
        repair = directory / "prompt-length-recovery" / retry_slot
        immutable(repair / "execution.json", record)
        config = copy.deepcopy(load(directory / "prompt-length-recovery/service/config.json"))
        queue = Queue(repair / "service/queue.sqlite3", {"gpu": 1, "llm": 1, "cpu": 1})
        os.environ["CUDA_VISIBLE_DEVICES"] = str(device)
        service = Service(queue, repair / "service", ROOT, config)
        runtime = Runtime.__new__(Runtime)
        runtime.root, runtime.output, runtime.batch = ROOT, output, batch
        runtime.directory, runtime.queue, runtime.service = worker, queue, service
        try:
            try:
                value = runtime._render(task, "pe-loop", prompt, seed, retry_slot, plan["scope"])
            except ResourceExhausted:
                return {"status": "deadline_settlement", "model_calls": 0}
            original = load(candidate_path.with_name("prompt.json"))["value"]
            value.update(id="v" + str(number + 1), prompt=prompt, original_prompt=original,
                         prompt_revisions=revision, render_recovery=record)
            immutable(candidate_path, {"value": value, "sha256": signature(value)})
            result = {"status": "candidate_ready", "candidate": str(candidate_path), "model_calls": 0}
            save(repair / "result.json", result)
            return result
        finally:
            runtime.close()


def main():
    from experiments.recovery import recover_pe_prompt
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--device", required=True, help="Original worker directory ID")
    parser.add_argument("--reason", default="Inspected tokenizer refusal before GPU generation")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--retry-render", help="Inspected unsubmitted revision render, e.g. 1-prompt-1")
    args = parser.parse_args()
    if args.retry_render:
        from planner_harness.common import load
        result = retry_render(args.output, args.topic, args.device, args.retry_render, args.reason, execute=args.execute)
        if not args.execute or result["status"] == "complete":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        args.reason = load(args.output / "methods" / args.topic / "pe-loop/prompt-length-recovery/execution.json")["reason"]
    print(json.dumps(recover_pe_prompt(args.output, args.topic, args.device, args.reason,
                                      execute=args.execute), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
