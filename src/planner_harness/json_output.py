"""One bounded JSON envelope shared by Planner, Critic and final judges."""
import json
import re


def decode_object(raw):
    if not isinstance(raw, str):
        raise ValueError("Response must be text containing one JSON object")
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```", text)
    if fenced:
        text = fenced.group(1).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Response must be one JSON object")
    return value
