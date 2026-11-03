"""Current creative actions; legacy/RSI actions remain in runner's compatibility path."""

import json
import re

from .common import page, save

ACTIONS = {
    "browse",
    "search",
    "read",
    "observe",
    "view_reference",
    "video",
    "history",
    "note",
    "workspace",
    "generate",
    "delivery_candidate",
    "review",
    "finish",
}


def read(harness, args, event_id):
    targets = args.get("targets", [])
    if (
        not isinstance(targets, list)
        or not 1 <= len(targets) <= 4
        or any(not isinstance(t, dict) for t in targets)
    ):
        raise ValueError("read accepts 1 to 4 target objects")
    results = []
    for target in targets:
        try:
            result = harness.knowledge.read(
                target["id"],
                target.get("start_line", 1),
                target.get("section"),
                start_char=target.get("start_char", 0),
                max_chars=target.get("max_chars", 6000),
            )
            identity = f"read-{len(harness.state['reads']) + 1:04d}"
            result["read_id"] = identity
            harness.state["reads"][identity] = {
                k: result[k]
                for k in (
                    "id",
                    "path",
                    "sha256",
                    "start_line",
                    "end_line",
                    "next_line",
                    "start_char",
                    "end_char",
                    "next_char",
                )
                if k in result
            }
            harness.state["reads"][identity]["event_id"] = event_id
            results.append(result)
        except (ValueError, KeyError, OSError) as exc:
            results.append({"target": target, "error": str(exc)})
    from .working_memory import retain

    retain(harness.state, results, event_id)
    return {"materials": results}


def history(harness, args):
    from .context import history_catalog

    if "catalog" in args:
        value = history_catalog(harness.state, args["catalog"])
    elif "review" in args:
        value = harness.state["reviews"][args["review"]]
    elif "feedback" in args:
        if "event_id" in args:
            raise ValueError("Choose feedback or event_id")
        value = harness.state["evaluations"][args["feedback"]]
    else:
        event = next(
            (e for e in harness.state["events"] if e["event_id"] == args.get("event_id")), None
        )
        if event is None:
            raise ValueError("Unknown event ID")
        value = event.get("result", {}) if args.get("result_only") else event
    return page(
        json.dumps(value, ensure_ascii=False, indent=2),
        args.get("start_line", 1),
        max_chars=8000,
        start_char=args.get("start_char", 0),
        split_long_lines=True,
    )


def finish(harness, args, event_id):
    state = harness.state
    identity = args.get("video")
    if identity is not None and identity not in state["videos"]:
        raise ValueError("Choose an existing video ID")
    if state.get("unresolved_jobs"):
        raise ValueError("Resolve the outstanding external outcome before finishing")
    reason = args.get(
        "stop_reason", "satisfied" if identity not in {None, "source"} else "no_promising_attempt"
    )
    if reason not in {"satisfied", "no_promising_attempt", "budget", "execution_failure"}:
        raise ValueError("Unknown finish stop_reason")
    if re.search(r"[\u3400-\u9fff]", json.dumps(args, ensure_ascii=False)):
        raise ValueError("Use English for working output")
    from .continuation import authorize_finish

    pending = authorize_finish(state)
    if pending is not None:
        return pending
    from .delivery_review import before_finish

    extra = {"stop_reason": reason}
    if reason == "satisfied":
        result = before_finish(harness, args, event_id)
        if result["status"] != "confirmed":
            return result
        extra["delivery_review"] = result["proof"]
    from .delivery import finish_status

    state.update(
        status=finish_status(state, reason, identity),
        final={
            "video": identity,
            "message": args.get("message", ""),
            "outcome": "selected_video" if identity else "stopped_without_video",
            **extra,
        },
    )
    save(harness.output / "final.json", state["final"])
    return state["final"]


def operate(harness, response, event_id):
    action = response.get("action", response.get("tool"))
    args = response.get("arguments", {})
    if action not in ACTIONS or not isinstance(args, dict):
        raise ValueError("Use one available creative action and an arguments object")
    if action == "review":
        if harness.state["config"]["execution"]["review"]["mode"] != "planner":
            raise ValueError(
                "This task uses automatic Critic review; choose your next action from its result"
            )
        identity = args.get("video_id")
        if identity is None:
            identity = next(
                (
                    key
                    for key, value in reversed(harness.state["reviews"].items())
                    if value.get("event_id") == event_id
                ),
                None,
            )
        return {"status": "complete", "review": harness.state["reviews"][identity]}
    if "note" in response:
        harness.remember(response["note"])
    if "workspace" in response:
        harness.update_workspace(response["workspace"])
    if action == "browse":
        return harness.knowledge.browse(args.get("id", "map"))
    if action == "search":
        return harness.knowledge.search(args["query"], args.get("limit", 8), args.get("scope", "all"))
    if action == "read":
        return read(harness, args, event_id)
    if action == "observe":
        return harness.observe(args, event_id)
    if action == "view_reference":
        refs = harness.knowledge.references(args["id"])
        harness.state.update(reference_images=refs, reference_image=refs[-1])
        return refs[0] if len(refs) == 1 else {"images": refs}
    if action == "video":
        return harness.state["videos"][args.get("id", "source")]
    if action == "workspace":
        if args:
            harness.update_workspace(args)
        return {"saved": True, "workspace": harness.state["workspace"]}
    if action == "note":
        harness.remember(args.get("text", ""), append=args.get("append", True))
        return {"saved": True}
    if action == "history":
        return history(harness, args)
    if action == "delivery_candidate":
        identity = args.get("video", args.get("id", "source"))
        if identity not in harness.state["videos"]:
            raise ValueError("Unknown video ID")
        harness.state["delivery_candidate"] = identity
        from .candidate_selection import refresh

        refresh(harness.state)
        return {
            "video": identity,
            "scope": "Current intended delivery; does not select render input or finish the task",
        }
    if action == "generate":
        from .execution import request_job

        return request_job(harness, action, args, event_id)
    return finish(harness, args, event_id)
