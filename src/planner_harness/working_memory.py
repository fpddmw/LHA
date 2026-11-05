"""Project current reading and concise older references; keep raw pages on disk."""
import copy
import json
import math
import re

POLICY = {"version": "creative-memory-v3-local-archive", "notes_chars": 12000,
          "max_input_tokens": 100000,
          "image_tokens": 1600, "reserve_tokens": 8192,
          "read_display_chars": 24000,
          "eviction": "Current reads stay complete; older pages use approved summaries and exact archive links under a soft display allowance"}

MATERIAL_FIELDS = (
    "id", "path", "title", "kind", "sha256", "version", "read_id", "text",
    "summary", "start_line", "start_char", "end_line", "end_char", "total_lines",
    "next_line", "next_char", "links",
)


def compact(material):
    # Directory inventories and repeated catalog metadata stay in the read event.
    # Preserve the exact page text, its identity, and usable navigation links.
    return {k: copy.deepcopy(material[k]) for k in MATERIAL_FIELDS if k in material}


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
                       "material": compact(material),
                       "open": {"action": "history", "arguments": {"event_id": event_id}}})


def visible(payload, state):
    memory = state.get("knowledge_memory", [])
    latest = (state.get("events") or [{}])[-1].get("event_id")
    selected, archived, seen, used = [], {}, set(), 0
    for row in reversed(memory):
        original = row["material"]
        material = {k: copy.deepcopy(original[k]) for k in
                    ("id", "title", "read_id", "text", "start_line", "start_char", "end_line", "end_char", "next_line", "next_char") if k in original}
        text = material.get("text", "")
        current = row["event_id"] == latest
        if not current and used + len(text) > POLICY["read_display_chars"]:
            identity = original.get("id", original.get("path", row["event_id"]))
            archived.setdefault(identity, {k: copy.deepcopy(original[k]) for k in ("id", "title", "summary") if k in original})
            archived[identity].setdefault("open", {"action": "read", "arguments": {
                "id": identity, "start_line": original.get("start_line", 1), "start_char": original.get("start_char", 0)}})
            archived[identity].setdefault("raw", {"action": "history", "arguments": {"event_id": row["event_id"]}})
            continue
        # Repeated complete source lines from overlapping pages need only one
        # display copy. Character-sliced boundary lines remain verbatim.
        lines, fresh = text.splitlines(keepends=True), []
        for n, line in enumerate(lines):
            match = re.match(r"(\d+): ", line)
            boundary = (n == 0 and original.get("start_char", 0)) or (n == len(lines)-1 and original.get("next_char", 0))
            key = (original.get("sha256"), original.get("id"), line)
            if match and not boundary and key in seen and not current:
                continue
            if match and not boundary:
                seen.add(key)
            fresh.append(line)
        material["text"] = "".join(fresh)
        if not material["text"] and text:
            continue
        material["text_is_complete"] = material["text"] == text
        if material["text"] != text:
            material["display_note"] = "Repeated source lines appear once in these read materials; raw pages are unchanged."
        used += len(material["text"])
        selected.append({"event_id": row["event_id"], "material": material,
                         "open": {"action": "history", "arguments": {"event_id": row["event_id"]}}})
    retained = list(reversed(selected))
    payload["working_memory"] = {"policy": {k:POLICY[k] for k in ("version","eviction")},
        "retained_reads": retained, "archived_reads": list(archived.values()),
        "scope": "Full read pages and complete operation history remain on disk and can be reopened. No additional memory action is required."}
    # The newest tool result and memory otherwise repeat the same page verbatim.
    retained_ids = {r["material"]["read_id"] for r in retained}
    for event in payload.get("recent_operations", []):
        materials = event.get("result", {}).get("materials", [])
        for material in materials:
            if material.get("read_id") in retained_ids:
                brief = {k: material[k] for k in ("id", "read_id", "title") if k in material}
                material.clear()
                material.update(brief, text_location="working_memory.retained_reads")


def fit_display(payload, limit, system_chars):
    """Archive whole older pages, preserving conclusions and conditions together."""
    memory = payload.get("working_memory", {})
    rows = memory.get("retained_reads", [])
    if not rows:
        return
    newest = (payload.get("recent_operations") or [{}])[-1].get("event_id")
    for row in list(rows):
        if system_chars + len(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))) <= limit:
            break
        if row["event_id"] == newest:
            continue
        rows.remove(row)
        material = row["material"]
        memory.setdefault("archived_reads", []).append({
            **{k: material[k] for k in ("id", "title") if k in material}, "open": row["open"]})


def component_sizes(system, user, images):
    """Local diagnostic only; characters are not claimed to be tokenizer counts."""
    try:
        payload = json.loads(user)
    except (ValueError, TypeError):
        payload = {}
    return {"version": POLICY["version"], "system_chars": len(system), "user_chars": len(user),
            "images": images, "component_chars": {k: len(json.dumps(v, ensure_ascii=False, separators=(",", ":")))
                                                    for k, v in payload.items()} if isinstance(payload, dict) else {}}


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
