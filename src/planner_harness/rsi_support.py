"""Opt-in RSI configuration, frozen evidence interfaces and compact experience."""
from __future__ import annotations

import copy
from pathlib import Path

from .common import load, save, sha
from .knowledge import Knowledge
from .ledger import build, digest


def configure(harness, config):
    if config is True:
        config = {}
    if not isinstance(config, dict):
        raise ValueError("RSI configuration must be an object")
    result = {"enabled": True, "auto_critique": True, "knowledge_enabled": True, **config}
    if result["enabled"] is not True or type(result["auto_critique"]) is not bool or type(result["knowledge_enabled"]) is not bool:
        raise ValueError("RSI flags must be boolean")
    result.pop("digest_limit", None)  # Older config accepted; summaries are never truncated.
    if not harness.state["config"]["execution"].get("critic"):
        raise ValueError("RSI runs require a configured online Critic")
    critic = harness.state["config"]["execution"]["critic"]
    critic.setdefault("model", "gpt-6.1-sol")
    critic.setdefault("reasoning_effort", "xhigh")
    critic.setdefault("max_turns", 12)
    if result.get("cycle"):
        from .rsi_cycle import verify
        cycle = verify(result["cycle"])
        if cycle["protocol"]["execution"] != harness.state["config"]["execution"]:
            raise ValueError("Execution differs from the frozen RSI cycle")
        if any(harness.state["config"].get(k) != cycle["protocol"]["planner"].get(k) for k in ("model", "reasoning_effort")):
            raise ValueError("Planner differs from the frozen RSI cycle")
        if result.get("seed_schedule", cycle["protocol"]["seed_schedule"]) != cycle["protocol"]["seed_schedule"]:
            raise ValueError("Seed schedule differs from the frozen RSI cycle")
        result.update(seed_schedule=cycle["protocol"]["seed_schedule"], frozen_critic=cycle["critic"], cycle_sha256=cycle["sha256"])
    limit = harness.state["config"]["max_generations"]
    if result.get("cycle") and limit != cycle["protocol"]["generation_budget"]:
        raise ValueError("Generation budget differs from the frozen RSI cycle")
    if result.get("seed_schedule") is not None and (limit is None or not isinstance(result["seed_schedule"], list) or len(result["seed_schedule"]) < limit or any(type(s) is not int for s in result["seed_schedule"])):
        raise ValueError("Provide one fixed integer seed per possible generation")
    sequence = result.get("seed_sequence")
    if sequence is not None:
        if result.get("seed_schedule") is not None or result.get("cycle"):
            raise ValueError("Use the frozen paired schedule or a delivery seed sequence, not both")
        if not isinstance(sequence, dict) or set(sequence) != {"start", "step"} or any(type(v) is not int or v < 0 for v in sequence.values()):
            raise ValueError("Seed sequence needs nonnegative integer start and step")
    # Freeze the Critic independently, before installing a Planner-only experience candidate.
    package = Path(__file__).parents[1] / "critic_harness"
    materials = {p.relative_to(package).as_posix(): p.read_text(encoding="utf-8") for p in package.rglob("*.md")}
    instructions = harness.output / "critic-instructions.json"
    knowledge = harness.output / "critic-knowledge-snapshot.json"
    frozen = result.get("frozen_critic")
    if frozen:
        for item in frozen.values():
            if sha(item["path"]) != item["sha256"]:
                raise ValueError("Validation Critic snapshot changed")
        materials = load(frozen["instructions"]["path"])
        save(instructions, materials)
        save(knowledge, load(frozen["knowledge"]["path"]))
    else:
        save(instructions, materials)
        Knowledge(harness.root).freeze(knowledge)
        snapshot = load(knowledge)
        paths = {r["path"] for r in snapshot.get("experiences", [])}
        ids = {r["id"] for r in snapshot.get("experiences", [])}
        snapshot["experiences"] = []
        snapshot["entrances"] = {k:v for k,v in snapshot.get("entrances", {}).items() if k not in ids}
        snapshot["documents"] = {k:v for k,v in snapshot["documents"].items() if k not in paths}
        save(knowledge, snapshot)
    result["critic_materials"] = {"instructions": str(instructions), "instructions_sha256": sha(instructions),
                                "knowledge": str(knowledge), "knowledge_sha256": sha(knowledge),
                                "evidence_cache": str(harness.output / "critic-evidence-cache")}
    result["critic_profile_sha256"] = digest(harness.state["config"]["execution"]["critic"])
    if result.get("experience_catalog"):
        harness.knowledge = candidate_knowledge(harness.root, result["experience_catalog"])
    if result.get("knowledge_snapshot"):
        item = result["knowledge_snapshot"]
        if result.get("experience_catalog") or sha(item["path"]) != item["sha256"]:
            raise ValueError("Use one unchanged Planner knowledge snapshot")
        harness.knowledge = Knowledge(harness.root, item["path"])
    harness.knowledge.enabled = result["knowledge_enabled"]
    harness.state["config"].update(context_version=3, rsi=result)
    harness.state.update(requirement_versions=[], task_memory={"status": "requirements_not_defined", "attempts": []})
    if result.get("task_card"):
        from .task_criteria import install
        card = load(Path(harness.root) / result["task_card"])
        install(harness.state, card)
        save(harness.output / "task-card.json", card)
        result["task_card_sha256"] = sha(harness.output / "task-card.json")
    elif harness.state["config"]["execution"].get("mode", "live") == "live":
        raise ValueError("New live RSI runs require a reviewed independent task_card before Planner starts")
    else:
        result["criteria_scope"] = "legacy scripted replay; Planner-authored criteria are not a live experiment"
    return result


def candidate_knowledge(root, catalog):
    """Overlay a candidate library without writing shared knowledge."""
    root = Path(root).resolve()
    raw = load(root / catalog)
    if isinstance(raw, dict) and raw.get("mode") not in {"replace_experience", "append_experience"}:
        raise ValueError("Candidate catalog mode must be append_experience or replace_experience")
    replace = isinstance(raw, dict) and raw.get("mode") == "replace_experience"
    rows = raw.get("entries") if isinstance(raw, dict) else raw
    k = Knowledge(root)
    if not isinstance(rows, list) or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Candidate catalog must contain unique topic IDs")
    if any(not (root / r["path"]).resolve().is_relative_to(root / "knowledge") for r in rows):
        raise ValueError("Experience candidate must remain inside repository knowledge")
    for row in rows:
        if row.get("sha256") and sha(root / row["path"]) != row["sha256"]:
            raise ValueError("Staged experience changed after proposal")
    ids = {r["id"] for r in rows}
    old_ids = {r["id"] for r in k.experiences}
    entrances = {key: value for key, value in k.entrances.items() if not replace or key not in old_ids or key in ids}
    snapshot = {"manifest": k.manifest, "experiences": ([] if replace else [r for r in k.experiences if r["id"] not in ids]) + rows,
                "entrances": entrances, "documents": {}, "asset_hashes": {}}
    # Knowledge accepts snapshots as objects as well as frozen paths.
    return Knowledge(root, snapshot)


def experience_digest(knowledge, target, limit=None):
    if not knowledge.enabled:
        return []
    renderer = "ditto" if "ditto" in target.lower() else "bernini" if "bernini" in target.lower() else "unspecified"
    cards = []
    for row in knowledge.experiences:
        for card in row.get("cards", []):
            cards.append({"id": card["id"], "summary": card["summary"], "status": card["status"],
                          "scope": card.get("renderer_scope", row.get("renderer_scope", "any")),
                          "applicability": "applicable" if card.get("renderer_scope", row.get("renderer_scope", "any")) in {"any", renderer}
                              else "renderer_unknown" if renderer == "unspecified" else "other_renderer_only",
                          "read": {"id": row["id"], "section": card.get("section")},
                          "priority": card.get("priority", 50)})
    cards.sort(key=lambda c: (c["priority"], c["id"]))
    return [{k: v for k, v in c.items() if k != "priority"} for c in cards]


def context(harness, payload):
    state = harness.state
    payload["task_memory"] = build(state)
    payload["rsi"] = {k: v for k, v in state["config"]["rsi"].items()
                      if k in {"enabled", "auto_critique", "knowledge_enabled", "seed_schedule", "seed_sequence"}}
    renderer = state["config"]["execution"].get("renderer", {}).get("backend", "unspecified")
    payload["experience_digest"] = experience_digest(harness.knowledge, renderer)
    payload["experience_digest_scope"] = "Complete navigation. Respect applicability and evidence status; other-renderer observations are transfer hypotheses. Defaults do not route actions."
    if state.get("criteria_authority") == "independent_frozen":
        from .task_criteria import verify_state
        verify_state(state)
        payload["task_criteria"] = {"authority": state["criteria_authority"], "requirements_location": "task_memory.requirements",
                                    "objections": state.get("criteria_objections", [])}
    return payload


def auto_review(harness):
    """Recover an unscheduled review before another Planner call, exactly once."""
    state = harness.state
    config = state["config"].get("rsi", {})
    if not config.get("auto_critique"):
        return False
    from .execution import request_job
    for identity, video in state["videos"].items():
        job_id = video.get("job_id")
        if not job_id or job_id not in state["jobs"]:
            continue
        event_id = job_id + "-auto"
        review_id = event_id + "-critique"
        if review_id in state["jobs"]:
            if not any(e.get("request", {}).get("arguments", {}).get("job_id") == review_id and e.get("request", {}).get("action") == "tool_result" for e in state["events"]):
                state.update(pending_tool=review_id, status="waiting_tool")
                harness.checkpoint()
                return True
            continue
        generated = state["jobs"][job_id]["payload"]
        comparisons = list(dict.fromkeys([generated.get("comparison_baseline", "source"), *generated.get("contenders", [])]))
        args = {"video": identity, "compare_to": comparisons,
                "question": "Assess current requirements, candidate changes and collateral damage. Keep uncertainty and do not choose the next action.",
                "requirements": generated["requirements"]}
        request_job(harness, "critique", args, event_id, internal=True)
        harness.checkpoint()
        return True
    return False
