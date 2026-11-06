"""Recoverable qualitative review using the Planner's native-frame observer."""

import copy, json
from pathlib import Path
from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature

PROTOCOL = "lha-qualitative-review-v1"


def instructions():
    root = Path(__file__).resolve().parents[2]
    return (root / ".agents/skills/lha-video-review/SKILL.md").read_text()


def profile(model=None, reasoning_effort="__configured_default__"):
    from planner_harness.creative import role_settings

    settings = role_settings({}, "online_critic")
    body = {
        "protocol_id": PROTOCOL,
        "rubric": instructions(),
        "model": model or settings["model"],
        "reasoning_effort": settings["reasoning_effort"]
        if reasoning_effort == "__configured_default__"
        else reasoning_effort,
        "schema_version": 1,
    }
    return {**body, "sha256": signature(body)}


def validate(report, packet=None):
    if (
        not isinstance(report, dict)
        or not isinstance(report.get("summary"), str)
        or not report["summary"].strip()
    ):
        raise ValueError("Review needs a useful text summary")
    if "findings" in report and (
        not isinstance(report["findings"], list)
        or any(not isinstance(v, (str, dict)) for v in report["findings"])
    ):
        raise ValueError("Optional findings are text or evidence-bearing objects")
    return report


def normalize_action(value):
    """Accept the Critic's named report wrapper without changing its contents."""
    from planner_harness.json_output import action_envelope

    normalized = action_envelope(value, default_action='review', metadata={'note', 'purpose'})
    args = normalized['arguments']
    if normalized['action'] in {'review', 'finish'} and 'review' in args:
        if set(args) != {'review'} or not isinstance(args['review'], dict):
            raise ValueError('Supply one review report object with summary and optional findings')
        normalized['arguments'] = args['review']
    return normalized


def observe(state, directory, args, identity):
    from planner_harness.event_observation import observe_videos

    return observe_videos(state, Path(directory), args, identity)


def frames(state):
    observations = state["observations"]
    if not observations:
        return []
    focus = state.get("observation_focus", {}).get("ids", [])
    selected = [o for o in observations if o["observation_id"] in focus] or observations[-1:]
    # Retain the initial comparison while the requested close-up is visible.
    first = [o for o in observations if o["observation_id"].startswith("overview")]
    selected = list({o["observation_id"]: o for o in first + selected}.values())
    rows = []
    for observation in selected:
        for f in observation["frames"]:
            rows.append(
                {
                    **f,
                    "id": observation["video_id"]
                    + ":"
                    + observation["observation_id"]
                    + ":"
                    + str(f["frame_index"]),
                    "video_id": observation["video_id"],
                    "kind": observation.get("mode", "sampled"),
                    "observation_id": observation["observation_id"],
                    "attachment": len(rows) + 1,
                }
            )
    return rows


def packet(payload, state, profile):
    rows = frames(state)
    visible = {
        "protocol_id": PROTOCOL,
        "candidate_id": payload["video_id"],
        "original_request": payload["request"],
        "submitted_prompt": payload.get("submitted_prompt", payload.get("actual_prompt", "")),
        "actual_prompt": payload.get("actual_prompt", ""),
        "input_id": payload.get("input_id", "source"),
        "track": payload.get("track", "long"),
        "focus": payload.get("focus", ""),
        "extra_checks": payload.get("extra_checks", []),
        "requested_events": payload.get("events", []),
        "compare_to": payload.get("compare_to"),
        "videos": {
            k: {
                f: v.get(f)
                for f in ("duration_seconds", "frames", "fps", "width", "height", "parent")
            }
            for k, v in payload["videos"].items()
        },
        "evidence": [
            {
                k: v
                for k, v in row.items()
                if k
                not in {
                    "path",
                    "sha256",
                    "decoder",
                    "native_pts",
                    "time_base",
                    "pts_origin_seconds",
                }
            }
            for row in rows
        ],
        "observations": [
            {k: v for k, v in o.items() if k != "frames"} for o in state["observations"][-12:]
        ],
        "notes": state.get("notes", [])[-12:],
        "last_result": state.get("last_result"),
        "actions": {
            "observe": "Shared Planner observer: video ID or list, mode sampled/continuous, start/end/count/page/crop; observation reopens saved IDs.",
            "review": "arguments: summary plus optional findings; return descriptive evaluation and evidence, no next-action advice.",
        },
    }
    refs = []
    for ref in payload.get("references", []):
        if not ref.get("path"):
            continue
        if sha(ref["path"]) != ref["sha256"]:
            raise ValueError("Reference image changed")
        refs.append({**ref, "attachment": len(rows) + len(refs) + 1, "kind": "reference"})
    visible["references"] = [
        {k: v for k, v in ref.items() if k not in {"path", "sha256"}} for ref in refs
    ]
    return {
        "system_prompt": profile["rubric"],
        "user_text": json.dumps(visible, ensure_ascii=False, separators=(",", ":")),
        "images": rows + refs,
        "profile_sha256": profile["sha256"],
    }


def run(payload, directory, model=None):
    from planner_harness.model_answers import call_object

    directory = Path(directory) / "one-shot-critic"
    if (directory / 'feedback.json').exists():
        return load(directory / 'feedback.json')
    from planner_harness.upgrade import retain
    payload = retain(directory / 'review-request.json', payload)
    frozen = payload.get("critic", {}).get("frozen_profile") or profile(
        getattr(model, "model", None), getattr(model, "reasoning_effort", None)
    )
    if model is None:
        from vlm.openrouter import OpenRouterVisionModel

        model = OpenRouterVisionModel(
            role="online_critic", model=frozen["model"], reasoning_effort=frozen["reasoning_effort"]
        )
    if (
        model.model != frozen["model"]
        or getattr(model, "reasoning_effort", None) != frozen["reasoning_effort"]
    ):
        raise ValueError("Configured Critic model differs from its request")
    from planner_harness.accounting import discover, bind, start_task

    binding = discover(directory, model)
    bind(directory, binding)
    if getattr(model, "is_live_api", False):
        start_task(binding)
    immutable(directory / "review-request.json", payload)
    if (directory / "feedback.json").exists():
        return load(directory / "feedback.json")
    state_path = directory / "state.json"
    if state_path.exists():
        state = load(state_path)
    else:
        state = {
            "videos": copy.deepcopy(payload["videos"]),
            "observations": [],
            "notes": [],
            "events": [],
            "attempts": 0,
        }
        ids = list(
            dict.fromkeys(
                ["source", payload.get("input_id", "source"), payload["video_id"]]
                + ([payload["compare_to"]] if payload.get("compare_to") else [])
            )
        )
        observe(state, directory, {"video": ids, "count": 6}, "overview")
        save(state_path, state)
    while True:
        number = state["attempts"] + 1
        identity = f"review-{number:04d}"
        request = retain(directory / "calls" / identity / "request.json", packet(payload, state, frozen))
        if number == 1:
            immutable(directory / "request.json", request)
        def validate_action(value):
            normalized = normalize_action(value)
            action, args = normalized['action'], normalized['arguments']
            if action in {'review', 'finish'}:
                validate(args, request)
            elif action == 'observe':
                from planner_harness.tool_interface import normalize
                normalize(normalized)
            elif action == 'note':
                if not isinstance(args.get('text'), str):
                    raise ValueError('note requires text')
            else:
                raise ValueError('Choose observe, note or review')
        response, selection = call_object(
            directory / "calls" / identity / "call",
            model,
            request["system_prompt"],
            request["user_text"],
            [r["path"] for r in request["images"]],
            validate=validate_action,
        )
        status = 'ok'
        try:
            normalized = normalize_action(response)
            if normalized != response:
                save(directory / "calls" / identity / "normalization.json", {"original": response, "normalized": normalized})
            action, args = normalized["action"], normalized["arguments"]
            if response.get("note"):
                state["notes"].append(response["note"])
            if action == "observe":
                from planner_harness.tool_interface import normalize
                args = normalize({"action": "observe", "arguments": args})["arguments"]
                result = observe(state, directory, args, identity)
                state["last_result"] = {
                    k: v for k, v in result.items() if k not in {"frames", "observations"}
                }
            elif action == "note":
                state["notes"].append(args["text"])
                state["last_result"] = {"saved": True}
            elif action in {"review", "finish"}:
                report = validate(copy.deepcopy(args), request)
                result = {
                    "protocol": PROTOCOL,
                    "mode": "critic",
                    "usage": "online_feedback",
                    "video_id": payload["video_id"],
                    "profile_sha256": frozen["sha256"],
                    "report": report,
                    "model": model.model,
                    "reasoning_effort": getattr(model, "reasoning_effort", None),
                    "request_path": str(directory / "review-request.json"),
                    "evidence": frames(state),
                    "observations": state["observations"],
                    "review_call": selection['call_path'],
                }
                immutable(directory / "feedback.json", result)
                return result
            else:
                raise ValueError("Choose observe, note or review")
        except (ValueError, KeyError, TypeError, OSError) as exc:
            status = 'response_error' if response is None else 'operation_error'
            state["last_result"] = {"error_type": type(exc).__name__, "error": str(exc)}
        state["events"].append(
            {"id": identity, "status": status, "response": response, "result": state["last_result"]}
        )
        state["attempts"] = number
        save(state_path, state)
