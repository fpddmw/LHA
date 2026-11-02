"""Identical finite memory mechanics for full/none, with exact archive pointers."""
import copy
import json
import math

POLICY = {"version": "creative-memory-v1", "notes_chars": 12000,
          "knowledge_chars": 18000, "max_input_tokens": 100000,
          "image_tokens": 1600, "reserve_tokens": 8192,
          "eviction": "oldest read fragment first; repeated exact fragments refresh recency"}


def retain(state, materials, event_id):
    memory = state.setdefault("knowledge_memory", [])
    for material in materials:
        if "read_id" not in material or "error" in material:
            continue
        key = [material.get(k) for k in ("sha256", "start_line", "end_line", "start_char", "end_char")]
        reread = [r for r in memory if r["fragment_key"] == key]
        memory[:] = [r for r in memory if r["fragment_key"] != key]
        memory.append({"fragment_key": key, "event_id": event_id,
                       "reread_of": [r["material"]["read_id"] for r in reread],
                       "material": copy.deepcopy(material),
                       "open": {"action": "history", "arguments": {"event_id": event_id}}})
    evicted = []
    while memory and len(json.dumps(memory, ensure_ascii=False)) > POLICY["knowledge_chars"]:
        evicted.append(memory.pop(0)["material"]["read_id"])
    if evicted:
        state.setdefault("memory_evictions", []).append({"event_id": event_id, "read_ids": evicted,
                                                         "reason": "knowledge fragment budget"})


def visible(payload, state):
    payload["working_memory"] = {"policy": {k:POLICY[k] for k in ("version","eviction")}, "retained_reads": copy.deepcopy(state.get("knowledge_memory", [])),
        "evicted_fragment_count": sum(len(r["read_ids"]) for r in state.get("memory_evictions", [])),
        "scope": "Read/exposure/retention/note evidence is observable; downstream action causality requires a controlled comparison."}


def estimate(system, user, images):
    # A conservative planning estimate, calibrated against saved provider usage.
    text = math.ceil((len(system) + len(user)) / 3)
    return {"version": POLICY["version"], "text_tokens_estimated": text,
            "image_tokens_estimated": images * POLICY["image_tokens"],
            "images": images, "reserve_tokens": POLICY["reserve_tokens"],
            "total_estimated": text + images * POLICY["image_tokens"] + POLICY["reserve_tokens"],
            "limit": POLICY["max_input_tokens"], "actual_usage": "See transport attempts/*/result.json; model-dependent estimate."}


def timeline(run, state):
    from pathlib import Path
    from .common import load
    from .execution import signature
    events = {e["event_id"]: e for e in state.get("events", [])}
    rows = []
    for path in sorted((Path(run) / "calls").glob("*/input.json")):
        saved = load(path)
        visible = json.loads(saved["user_text"])
        retained = visible.get("working_memory", {}).get("retained_reads", [])
        event = events.get(path.parent.name, {})
        rows.append({"event_id":path.parent.name, "input_path":str(path),
                     "memory_policy":visible.get("working_memory", {}).get("policy"),
                     "retained_read_ids":[r["material"]["read_id"] for r in retained],
                     "rereads":[r for r in retained if r.get("reread_of")],
                     "notes_sha256":signature({"text":visible.get("notes", "")}),
                     "notes_chars":len(visible.get("notes", "")),
                     "action":event.get("request", {}).get("action"),
                     "action_status":event.get("status")})
    return {"version":"memory-analysis-v1", "experience_mode":state["config"].get("execution",{}).get("experience_mode"),
            "policy":POLICY, "calls":rows, "evictions":state.get("memory_evictions", []),
            "interpretation":"Saved inputs reconstruct visibility, recency, rereading and explicit notes. Temporal association with later actions is descriptive; memory-policy effects require full/none runs with the same policy and budget."}
