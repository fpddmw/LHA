"""Record creative-run recovery or freeze a shared profile. Executes no model or renderer."""
import argparse
from contextlib import nullcontext
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from planner_harness.common import load, save, stamp
from planner_harness.lock import RunLock


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--service", type=Path, help="Stopped service directory; the service OS lock is required")
    p.add_argument("--queue-job", type=int, help="Existing paused/failed queue job to resume after recovery")
    sub = p.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze-profile")
    freeze.add_argument("--output", type=Path, required=True)
    for name in ("retry-planner", "recover-tool", "resources"):
        parser = sub.add_parser(name)
        parser.add_argument("--run", type=Path, required=True)
        parser.add_argument("--reason", required=True)
        if name in {"retry-planner", "recover-tool"}:
            parser.add_argument("--extra-attempts", type=int, default=1)
        if name == "recover-tool":
            parser.add_argument("--job", required=True)
            parser.add_argument("--action", choices=["receipt", "not-executed", "retry-review"], required=True)
            parser.add_argument("--receipt", type=Path)
        if name == "resources":
            parser.add_argument("--context-chars", type=int)
            parser.add_argument("--continue-delivery", action="store_true")
            parser.add_argument("--additional-turns", type=int, default=0)
    args = p.parse_args()
    if args.command == "freeze-profile":
        from planner_harness.creative import experiment_profile
        from planner_harness.execution import immutable
        immutable(args.output, experiment_profile(ROOT))
        print("Shared profile saved; no task started.")
        return
    if not args.reason.strip() or (args.queue_job is not None and not args.service):
        p.error("A reason is required; queue recovery also requires --service")
    if args.command == "resources" and args.context_chars is None and not args.continue_delivery and args.additional_turns == 0:
        p.error("Choose an explicit context or resource adjustment")
    with RunLock(args.service.resolve() / "service-owner") if args.service else nullcontext():
        queued = None
        if args.service:
            from server_runtime.queue import Queue
            q = Queue(args.service.resolve() / "queue.sqlite3")
            if args.queue_job is not None:
                queued = next((j for j in q.rows() if j["id"] == args.queue_job), None)
                if not queued or queued["state"] not in {"failed", "needs_review", "complete"}:
                    raise ValueError("Choose a stopped queue job")
                if queued["state"] == "complete" and args.command != "resources":
                    raise ValueError("Completed queue receipts cannot be retried")
                job_run = Path(queued["payload"].get("run", "")).resolve() if queued["kind"] == "planner" else Path(queued["payload"]["request"]).resolve().parents[2]
                if job_run != args.run.resolve():
                    raise ValueError("Queue job belongs to a different task")
                if args.command == "recover-tool" and Path(queued["payload"].get("request", "")).parent.name != args.job:
                    raise ValueError("Queue job does not match the tool to recover")
                if args.command != "recover-tool" and queued["kind"] != "planner":
                    raise ValueError("Choose this task's Planner queue job")
                if queued["state"] == "complete":
                    active = [j for j in q.rows() if j["kind"] == "planner" and j["payload"].get("run") == queued["payload"]["run"] and j["state"] in {"queued", "running"}]
                    if active:
                        raise ValueError("A continuation for this task is already queued")
        if args.command == "recover-tool":
            from planner_harness.recovery import recover_tool
            if args.action == "receipt" and not args.receipt:
                p.error("Receipt reconciliation needs --receipt")
            recover_tool(args.run, args.job, args.action, args.reason, response=args.receipt,
                         extra_attempts=args.extra_attempts)
        else:
            with RunLock(args.run):
                state = load(args.run / "state.json")
                if state["config"].get("workflow") != "creative_loop_v1":
                    raise ValueError("This command is for creative runs only")
                if args.command == "retry-planner":
                    event = state.get("pending_event")
                    if not event:
                        raise ValueError("There is no pending Planner call")
                    from planner_harness.model_call import reopen_call
                    reopen_call(args.run / "calls" / event / "transport", args.reason, args.extra_attempts)
                else:
                    if state.get("pending_event") or state.get("pending_tool") or state["status"] == "complete":
                        raise ValueError("Adjust resources only for an unfinished task without pending work")
                    changes = {"at": stamp(), "reason": args.reason, "before": dict(state["config"])}
                    if args.context_chars is not None:
                        if args.context_chars < 8192:
                            raise ValueError("Context capacity must be at least 8192")
                        state["config"]["max_context_chars"] = args.context_chars
                    if args.continue_delivery:
                        from planner_harness.delivery import continue_budget_stop
                        continue_budget_stop(state)
                    if args.additional_turns < 0:
                        raise ValueError("Additional turns must be nonnegative")
                    if state["config"]["max_turns"] is not None:
                        state["config"]["max_turns"] += args.additional_turns
                    changes["after"] = dict(state["config"])
                    state.setdefault("resource_changes", []).append(changes)
                    save(args.run / "state.json", state)
        if queued:
            if queued["state"] == "complete":
                q.enqueue(queued["key"] + "/resource-resume-" + str(len(q.rows())), "planner", "llm", queued["payload"])
            else:
                q.retry(queued["id"], args.reason)
        print("Recovery recorded; no model or renderer invoked. Resume the same task/service when ready.")


if __name__ == "__main__":
    main()
