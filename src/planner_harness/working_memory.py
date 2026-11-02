"""Keep read pages across actions; fit their display only at actual context capacity."""
import copy
import json
import math

POLICY = {"version": "creative-memory-v2", "notes_chars": 12000,
          "max_input_tokens": 100000,
          "image_tokens": 1600, "reserve_tokens": 8192,
          "eviction": "No read-page eviction; deduplicate rereads and shorten displayed excerpts only at total context capacity"}

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
    retained = [
        {**copy.deepcopy(row), "material": compact(row["material"])}
        for row in state.get("knowledge_memory", [])
    ]
    payload["working_memory"] = {"policy": {k:POLICY[k] for k in ("version","eviction")}, "retained_reads": retained,
        "evicted_fragment_count": sum(len(r["read_ids"]) for r in state.get("memory_evictions", [])),
        "scope": "Previously read pages remain available here across actions. Exact complete read results open through their history links."}
    # The newest tool result and memory otherwise repeat the same page verbatim.
    retained_ids = {r["material"]["read_id"] for r in retained}
    for event in payload.get("recent_operations", []):
        for material in event.get("result", {}).get("materials", []):
            if material.get("read_id") in retained_ids:
                material.pop("text", None)
                material["text_location"] = "working_memory.retained_reads"


def fit_display(payload, limit, system_chars):
    """Fit all remembered sources together; never delete state or a source's pointer.

    A shared excerpt length gives every read a visible place under real pressure.
    Short pages remain complete. The original full pages stay in state/history.
    """
    memory = payload.get("working_memory", {})
    rows = memory.get("retained_reads", [])
    if not rows:
        return
    # Preserve useful prose before repeated hashes, page receipts and link lists.
    # The event link opens all of that metadata with the exact original page.
    for row in rows:
        row.pop("fragment_key", None)
        row["material"] = {
            k: row["material"][k]
            for k in ("id", "title", "read_id", "text", "start_line", "start_char")
            if k in row["material"]
        }
    texts = [r["material"].get("text", "") for r in rows]

    def project(size):
        for row, text in zip(rows, texts):
            row["material"]["text"] = text[:size]
            row["material"]["text_is_complete"] = len(text) <= size
        return system_chars + len(json.dumps(payload, ensure_ascii=False, indent=2))

    # Binary search uses the actual serialized size, including image metadata.
    low, high = 0, max(map(len, texts), default=0)
    while low < high:
        middle = (low + high + 1) // 2
        if project(middle) <= limit:
            low = middle
        else:
            high = middle - 1
    project(low)


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
