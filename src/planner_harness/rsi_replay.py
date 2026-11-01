"""Decision-prefix replay with side-effect-free generation/finish interception."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from .common import ROOT, load, save, sha
from .knowledge import Knowledge
from .ledger import digest, intent
from .rsi_calls import call_once
from .rsi_data import local_path, sealed
from .rsi_support import candidate_knowledge, experience_digest
from .runner import PlannerHarness


def prefix(input_path, root=ROOT):
    """Read only artifacts named by a saved pre-decision context, never final state."""
    input_path = local_path(input_path, root)
    saved = load(input_path)
    payload = json.loads(saved["user_text"])
    run = input_path.parents[2]
    def artifact(value, expected):
        raw = str(value).replace("\\", "/")
        try:
            path = local_path(value, root)
        except (ValueError, OSError):
            if "/run/" not in raw:
                raise
            path = run / raw.rsplit("/run/", 1)[1]
        if not path.exists() or sha(path) != expected:
            raise ValueError("Prefix artifact is unavailable or changed: " + str(value))
        return str(path.resolve())
    state_file = input_path.with_name("decision-state.json")
    if state_file.exists():
        state = load(state_file)
        if set(state["videos"]) != set(payload["videos"]):
            raise ValueError("Saved prefix videos disagree with the actual model input")
    else:
        # Legacy context v2 hides provenance, but its own historical events contain it.
        recent = copy.deepcopy(payload.get("recent_operations", []))
        events = []
        for entry in payload.get("archived_operation_index", []):
            path = run / "events" / (entry["event_id"] + ".json")
            if not path.exists():
                raise ValueError("Legacy prefix is incomplete: " + str(path))
            events.append(load(path))
        events += recent
        visible = list(payload["videos"])  # Preserve the historical candidate chronology.
        task = copy.deepcopy(payload["task"])
        videos = {}
        if task["source"].get("path"):
            videos["source"] = copy.deepcopy(task["source"])
        evaluations = copy.deepcopy(payload.get("evaluations", {}))
        for event in events:
            result = event.get("result", {})
            if event.get("request", {}).get("action") == "tool_result":
                jid = event.get("request", {}).get("arguments", {}).get("job_id")
                path = run / "jobs" / str(jid) / "request.json"
                if path.exists():
                    job = load(path)
                    p = job["payload"]
                    if p.get("input_id") in visible:
                        videos.setdefault(p["input_id"], copy.deepcopy(p["input"]))
                    if "original" in p:
                        videos.setdefault("source", copy.deepcopy(p["original"]))
                    for key, value in p.get("videos", {}).items():
                        if key in visible:
                            videos[key] = copy.deepcopy(value)
                    response = path.with_name("collected.json")
                    if not response.exists():
                        response = path.with_name("response.json")
                    if response.exists() and job["kind"] != "generate":
                        returned = load(response)
                        if returned.get("status") == "complete":
                            evaluations[jid] = {"video_id": p["video_id"], **returned["payload"]}
                    if job["kind"] == "generate" and result.get("video_id") in visible:
                        v = result.get("video", {})
                        if v.get("path"):
                            videos[result["video_id"]] = copy.deepcopy(v)
                        elif response.exists():
                            response_value = load(response)
                            v = response_value.get("payload", {}).get("video")
                            if v:
                                videos[result["video_id"]] = {**v, "parent": p["input_id"], "prompt": p["prompt"]}
        if not set(visible) <= set(videos):
            raise ValueError("Cannot reconstruct legacy provenance from prefix-only evidence")
        state = {"request": {**task, "source": videos["source"]}, "videos": {k: videos[k] for k in visible},
                 "evaluations": evaluations, "events": events, "observations": [], "reads": copy.deepcopy(payload.get("read_receipts", {})),
                 "workspace": copy.deepcopy(payload.get("workspace", {"summary": "", "nodes": {}})), "notes": payload.get("notes", ""),
                 "config": {"mode": "loop", "rsi": {"enabled": True}}, "jobs": {}, "requirement_versions": [],
                 "generation_requests": payload.get("resource_status", {}).get("generation_requests", 0)}
        if payload.get("task_memory", {}).get("requirements"):
            state["requirements"] = payload["task_memory"]["requirements"]
    for identity, info in state["videos"].items():
        try:
            info["path"] = artifact(info["path"], info["sha256"])
        except (ValueError, OSError):
            # Exported runs retain the collected output at this exact identity.
            file = run / "videos" / identity / ("video" + Path(info["path"]).suffix)
            info["path"] = artifact(file, info["sha256"])
    for frame in saved["images"]:
        frame["path"] = artifact(frame["path"], frame["sha256"])
    for observation in state.get("observations", []):
        for frame in observation["frames"]:
            frame["path"] = artifact(frame["path"], frame["sha256"])
    return saved, payload, state, run


REPLAY_NOTE = """This is a saved decision-prefix replay, using a candidate experience library.
Only evidence available at this decision is visible. Historical outcomes beyond this point are unavailable.
Use the normal knowledge and observation tools. Stop at your next generate or finish operation:
the harness will record it without rendering, evaluation or publication. Tools critique/evaluate are
unavailable here. For historical runs missing requirements, define a compact faithful set if needed;
that reconstruction is new work and will not be labeled as historical intent. You may inspect,
reason, note and revise freely; no prescribed order beyond valid tool dependencies."""


def neutralize(payload, state):
    """Remove retrieved advice and derived notes symmetrically, retaining actual task evidence."""
    payload, state = copy.deepcopy(payload), copy.deepcopy(state)
    advice = {"read", "browse", "search", "lesson", "workspace", "note", "history"}
    def clean(value):
        if isinstance(value, list):
            return [clean(v) for v in value if not (isinstance(v, dict) and v.get("request", {}).get("action") in advice)]
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in {"experience_digest", "knowledge_entrances", "read_receipts", "reads", "knowledge_reads", "working_notes", "notes", "lessons", "workspace", "archived_operation_index"}}
        return value
    payload, state = clean(payload), clean(state)
    state.update(notes="", reads={}, workspace={"summary": "", "nodes": {}})
    payload["prefix_scope"] = "Knowledge-read text and derived notes removed identically in both arms. Existing prompts/videos remain historical conditioning, not knowledge-naive evidence."
    return payload, state


def replay(input_path, catalog, output, model, *, root=ROOT, max_turns=12, max_context_chars=220000, paired=False, environment_snapshot=None):
    output, root = Path(output).resolve(), Path(root).resolve()
    saved, original, state, run = prefix(input_path, root)
    if paired:
        original, state = neutralize(original, state)
    knowledge = candidate_knowledge(root, catalog)
    # A formal paired probe uses the cycle environment; diagnostics retain historical sources.
    historical = load(environment_snapshot or (run / "knowledge-snapshot.json"))
    old_paths = {r["path"] for r in historical["experiences"]}
    old_ids = {r["id"] for r in historical["experiences"]}
    historical["experiences"] = knowledge.experiences
    historical["documents"] = {p: d for p, d in historical["documents"].items()
                               if p not in old_paths}
    historical["entrances"] = {k:v for k,v in historical.get("entrances", {}).items() if k not in old_ids or k in {r["id"] for r in knowledge.experiences}}
    historical["enabled"] = True
    knowledge = Knowledge(root, historical)
    freeze = output / "knowledge-snapshot.json"
    if freeze.exists():
        pinned = load(freeze)
        if pinned["experiences"] != knowledge.experiences:
            raise ValueError("Replay candidate changed")
        knowledge = Knowledge(root, freeze)
    else:
        knowledge.freeze(freeze)
    contract = {"input": str(local_path(input_path, root)), "input_sha256": sha(local_path(input_path, root)),
                "candidate_catalog_sha256": sha(root / catalog), "knowledge_sha256": sha(freeze),
                "max_turns": max_turns, "model": getattr(model, "model", type(model).__name__),
                "reasoning_effort": getattr(model, "reasoning_effort", "unknown"), "paired_prefix": paired,
                "environment_sha256": sha(environment_snapshot) if environment_snapshot else None,
                "neutral_prefix_sha256": digest(original),
                "harness_sha256": digest({p.name: sha(p) for p in Path(__file__).parent.iterdir() if p.suffix in {".py", ".md"}})}
    sealed(output / "replay-contract.json", contract)
    if (output / "result.json").exists():
        return load(output / "result.json")
    harness = PlannerHarness(output / "workspace", model, root=root)
    harness.state, harness.knowledge = state, knowledge
    harness.state["config"]["rsi"] = {"enabled": True}
    harness.state["config"]["mode"] = "loop"
    harness.state.setdefault("observations", [])
    # Old overviews are sufficient to reopen known observations without future state.
    if not harness.state["observations"]:
        groups = {}
        for image in saved["images"]:
            if image.get("observation_id"):
                group = groups.setdefault(image["observation_id"], {"observation_id": image["observation_id"], "video_id": image.get("video_id", "source"), "frames": []})
                group["frames"].append(image)
        harness.state["observations"] = list(groups.values())
    operations, terminal = [], None
    system = ((Path(__file__).parent / "OPERATIONS.md").read_text(encoding="utf-8") + "\n\n" + knowledge.snapshot["documents"]["knowledge/READING.md"]["text"]) if paired else saved["system_prompt"]
    if paired:
        from critic_harness.adapter import PLANNER_MANUAL
        system += "\n\n" + PLANNER_MANUAL
    system += "\n\n" + (Path(__file__).parent / "RSI.md").read_text(encoding="utf-8") + "\n\n" + REPLAY_NOTE
    images = [r["path"] for r in saved["images"]]
    mapping = copy.deepcopy(saved["images"])
    for turn in range(max_turns):
        payload = copy.deepcopy(original)
        renderer = state["config"].get("execution", {}).get("renderer", {}).get("backend", original["task"].get("target_model", "unspecified"))
        payload["experience_digest"] = experience_digest(knowledge, renderer)
        payload["knowledge_entrances"] = knowledge.overview()
        payload["replay_operations"] = operations
        payload["working_notes"] = harness.state.get("notes", "")
        payload["current_requirements"] = harness.state.get("requirements")
        payload["replay_scope"] = "Decision change only; no future outcome or independent final score is available."
        payload["attached_images_in_order"] = mapping
        user = json.dumps(payload, ensure_ascii=False)
        if len(user) + len(system) > max_context_chars:
            raise ValueError("Replay context exceeded its frozen budget")
        raw = call_once(output / "calls" / f"{turn + 1:03d}", model, system, user, images)
        try:
            call = json.loads(raw)
            action = call["action"]
            args = call.get("arguments", {})
            if action in {"generate", "finish"}:
                key = "input_video" if action == "generate" else "video"
                if args.get(key) is not None and args[key] not in state["videos"]:
                    raise ValueError("Replay decision refers to an unavailable candidate")
                if action == "generate":
                    if args.get("input_video") not in state["videos"] or not args.get("prompt"):
                        raise ValueError("Generation needs an available input and English prompt")
                    if not state.get("requirements"):
                        raise ValueError("Define requirements before an RSI generation decision")
                    intent(args.get("intent"), state["requirements"])
                elif args.get("stop_reason") not in {"satisfied", "no_promising_attempt", "budget", "execution_failure"}:
                    raise ValueError("RSI finish needs a stopping reason")
                terminal = call
                operations.append({"request": call, "result": {"intercepted": True, "side_effects": False}})
                break
            if action not in {"read", "browse", "search", "observe", "video", "note", "lesson", "history", "workspace", "requirements", "view_reference", "criteria_objection", "delivery_candidate"}:
                raise ValueError("This replay tool is unavailable; decide with existing evidence")
            result = harness.operate(call, "replay-" + str(turn + 1))
            operations.append({"request": call, "result": result})
            if action == "view_reference":
                mapping = [r for r in mapping if r.get("kind") != "knowledge reference, not source-video evidence"]
                for reference in result.get("images", [result]):
                    mapping.append({**reference, "kind": "knowledge reference, not source-video evidence", "attachment": len(mapping)+1})
                images = [r["path"] for r in mapping]
            if action == "observe":
                observed = result.get("observations", [result])
                mapping = [r for r in saved["images"] if r.get("video_id", "source") == "source"]
                for observation in observed:
                    mapping.extend({**f, "video_id": observation.get("video_id", "source"), "observation_id": observation["observation_id"]} for f in observation["frames"])
                unique = {r["path"]: r for r in mapping}
                mapping = [{**r, "attachment": i+1} for i,r in enumerate(unique.values())]
                images = [r["path"] for r in mapping]
        except (ValueError, KeyError, TypeError) as exc:
            operations.append({"response": raw, "error": str(exc)})
    result = {**contract, "status": "decision_recorded" if terminal else "budget_exhausted", "decision": terminal,
              "operations": operations, "requirements": state.get("requirements"),
              "model_calls": len(operations), "renderer_calls": 0, "evaluator_calls": 0,
              "scope": "Offline policy response; quality improvement remains unmeasured."}
    save(output / "result.json", result)
    return result
