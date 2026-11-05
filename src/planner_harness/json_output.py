"""One bounded JSON envelope shared by Planner, Critic and final judges."""
import json
import re
import copy


def action_envelope(value, *, default_action=None, metadata=()):
    """Accept equivalent flat/nested actions without discarding supplied fields.

    Meaning and supported parameters are checked by the receiving tool. A
    conflicting duplicate is ambiguous and must never select a default target.
    The original model response is left untouched.
    """
    if not isinstance(value, dict):
        raise ValueError("Return one action object")
    result = copy.deepcopy(value)
    if "tool" in result:
        tool = result.pop("tool")
        if "action" in result and result["action"] != tool:
            raise ValueError("Conflicting action/tool values")
        result["action"] = tool
    if "action" not in result and default_action is not None:
        result["action"] = default_action
    args = result.get("arguments")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ValueError("arguments must be an object")
    reserved = {"action", "arguments", *metadata}
    for key in list(result):
        if key in reserved:
            continue
        value = result.pop(key)
        if key in args and args[key] != value:
            raise ValueError(f"Conflicting top-level and arguments.{key}; supply one intended value")
        args[key] = value
    result["arguments"] = args
    return result


def decode_object(raw, *, allow_prose=False):
    if not isinstance(raw, str):
        raise ValueError("Response must be text containing one JSON object")
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```", text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as original:
        if not allow_prose:
            raise
        # Accept one complete JSON object surrounded by prose/fences. Multiple
        # objects are ambiguous; malformed objects are never invented/repaired.
        decoder, objects, position = json.JSONDecoder(), [], 0
        while position < len(text):
            start = text.find("{", position)
            if start < 0:
                break
            try:
                item, end = decoder.raw_decode(text, start)
            except json.JSONDecodeError:
                # A malformed leading object must not expose one of its nested
                # objects as the intended operation.
                raise original
            objects.append(item)
            position = end
        if len(objects) != 1:
            raise original
        value = objects[0]
    if not isinstance(value, dict):
        raise ValueError("Response must be one JSON object")
    return value
