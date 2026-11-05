"""Small shared tool reference and meaning-preserving argument normalization."""

import copy

SIGNATURES = {
    "browse": '{id?}',
    "search": '{query, scope?:"style"|"experience"|"all", limit?}',
    "read": '{targets:[{id,section?,start_line?,start_char?,max_chars?}]} (1-4 targets; a single id or string target is accepted)',
    "view_reference": '{id}',
    "video": '{id? | ids:[id,...], raw?, compare_prompts?} (prompt, input and saved review together)',
    "observe": '{video:id|[id,...], mode?,start?,end?,count?,page?,crop?} or {observation:id}',
    "history": '{event_id? | feedback? | review? | catalog? | video? | videos?, start_line?,start_char?,raw?}; review/feedback may be an ID list',
    "note": '{text, append?}',
    "workspace": '{summary?,nodes?,remove_nodes?}',
    "delivery_candidate": '{video}',
    "generate": '{input_video,prompt,justification?,review_focus?:{focus?,extra_checks?,events?,compare_to?}}',
    "review": '{video_id,summary,findings?} (Planner review mode)',
    "finish": '{video,message,stop_reason?}',
}

# These are consumed by the current actions, including historical aliases.
# Explicit unsupported fields are errors, never silently discarded defaults.
PARAMETERS = {
    "browse": {"id"},
    "search": {"query", "scope", "limit"},
    "read": {"targets", "id", "section", "start_line", "start_char", "max_chars"},
    "view_reference": {"id"},
    "video": {"id", "ids", "video", "videos", "raw", "compare_prompts"},
    "observe": {"video", "videos", "video_id", "observation", "mode", "start", "end", "count", "page", "crop", "indices"},
    "history": {"event_id", "feedback", "review", "catalog", "video", "videos", "start_line", "start_char", "raw", "result_only", "compare_prompts"},
    "note": {"text", "append"},
    "workspace": {"summary", "nodes", "remove_nodes"},
    "delivery_candidate": {"video", "video_id", "id"},
    "generate": {"input_video", "input_id", "prompt", "seed", "justification", "review_focus"},
    "review": {"video_id", "summary", "findings"},
    "finish": {"video", "video_id", "id", "message", "stop_reason"},
}


def reference():
    return "Use one JSON operation `{action, arguments}`. Available actions:\n" + "\n".join(
        f"- `{name} {signature}`" for name, signature in SIGNATURES.items()
    ) + ("\n\nAction parameters may also be supplied directly beside `action`; equivalent flat/nested forms are accepted. "
         "Conflicting duplicate values and unsupported parameter names return a specific error. "
         "Optional top-level `note` and `workspace` updates can accompany an action. "
         "`extra_checks` accepts text or a list of texts; `focus` accepts text or a list "
         "of texts joined in the supplied order. These forms have the same meaning.")


def _alias(args, source, target):
    if source not in args:
        return
    if target in args and args[target] != args[source]:
        raise ValueError(f"Conflicting {source}/{target}; supply one intended value")
    args[target] = args.pop(source)


def normalize_focus(value):
    value = copy.deepcopy(value)
    if isinstance(value, str):
        return {"focus": value}
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return {"focus": "\n".join(value)}
    if isinstance(value, dict):
        if isinstance(value.get("focus"), list) and all(isinstance(v, str) for v in value["focus"]):
            value["focus"] = "\n".join(value["focus"])
        if isinstance(value.get("extra_checks"), str):
            value["extra_checks"] = [value["extra_checks"]]
    return value


def normalize(response):
    """Never invent a target, action, prompt, decision or review."""
    if not isinstance(response, dict):
        raise ValueError("Return an object with action and arguments")
    result = copy.deepcopy(response)
    action = result.get("action", result.get("tool"))
    if action not in SIGNATURES:
        raise ValueError("Unknown action; available: " + ", ".join(SIGNATURES))
    if action == "read" and isinstance(result.get("arguments"), (str, list)):
        result["arguments"] = {"targets": result["arguments"]}
    from .json_output import action_envelope
    metadata = {"purpose", "note", "workspace", "review"}
    # A history review ID is a retrieval argument; an attached review object is
    # a Planner self-review and retains its original top-level meaning.
    if action == "history" and isinstance(result.get("review"), (str, list)):
        metadata.remove("review")
    result = action_envelope(result, metadata=metadata)
    args = result["arguments"]
    unknown = set(args) - PARAMETERS[action]
    if unknown:
        raise ValueError(f"{action} unsupported parameters: {', '.join(sorted(unknown))}; use {SIGNATURES[action]}")
    if action == "read":
        if "targets" not in args and "id" in args:
            args = {"targets": [args]}
            result["arguments"] = args
        if "targets" in args and set(args) != {"targets"}:
            raise ValueError("Put read pagination and section inside each target")
        targets = args.get("targets", [])
        if isinstance(targets, (str, dict)):
            targets = [targets]
        if isinstance(targets, list):
            args["targets"] = [{"id": t} if isinstance(t, str) else t for t in targets]
            for target in args["targets"]:
                if isinstance(target, dict) and set(target) - {"id", "section", "start_line", "start_char", "max_chars"}:
                    raise ValueError("Unsupported read target parameter; use id, section, start_line, start_char, max_chars")
    if action == "video":
        _alias(args, "video", "id")
        _alias(args, "videos", "ids")
    if action == "observe":
        _alias(args, "videos", "video")
        _alias(args, "video_id", "video")
    if action in {"finish", "delivery_candidate"}:
        _alias(args, "id", "video")
        _alias(args, "video_id", "video")
    if action == "generate":
        _alias(args, "input_id", "input_video")
        if "review_focus" in args:
            args["review_focus"] = normalize_focus(args["review_focus"])
    required = {"search": ("query",), "generate": ("input_video", "prompt"),
                "view_reference": ("id",)}.get(action, ())
    missing = [name for name in required if name not in args]
    if missing:
        raise ValueError(f"{action} missing {', '.join(missing)}; use {SIGNATURES[action]}")
    return result
