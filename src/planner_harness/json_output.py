"""One bounded JSON envelope shared by Planner, Critic and final judges."""
import json
import re


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
