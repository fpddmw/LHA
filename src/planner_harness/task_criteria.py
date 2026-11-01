"""Source-only criteria shared by planning and independent outcome judgment."""
from __future__ import annotations
import copy
import math
from pathlib import Path
from .common import load, save, sha
from .ledger import digest, english, requirements

CONTRACT = "lha-task-criteria-v2"
AUTHORING = """
Build criteria from the request and SOURCE only, before planning. Do not prescribe a
creative realization. Broad storybook requests permit coherent watercolor, pencil,
cut-paper or other illustration. No particular medium or palette is mandatory.
Keep explicit location/property bindings. Separate authorized changes, task-defining
source relations and incidental details. Implicit core relations need a task-identity
rationale, not mere visibility. Record ambiguity. Include stylization in pass boundaries.
Add ambiguities (array). Each group has a positive weight per original user goal.
Each item additionally has origin (user_requirement or source_relation), importance_reason,
source_evidence (request excerpt or source observation), pass_rule, fail_rule,
allowed_variation (array), and partial_rule (a boundary or exactly 'not allowed').
Splitting observations does not increase a goal's weight. Sampled frames cannot establish
exact motion. The card is a draft for source-grounded review, not a creative template.
"""


def validate(card, *, frozen=True):
    from evaluation.protocol import validate_card
    validate_card(card, frozen=frozen)
    if card.get("criteria_contract") != CONTRACT:
        raise ValueError("Use independent v2 task criteria; legacy cards need reviewed migration")
    author = card.get("authoring", {})
    if author.get("scope") != "request_and_source_only" or author.get("role") not in {"independent_builder", "human_reviewed_source"}:
        raise ValueError("Criteria must originate outside Planner from request/source evidence")
    if not author.get("evidence_sha256") or not isinstance(card.get("ambiguities"), list):
        raise ValueError("Bind source-only evidence and record ambiguity")
    for group in card["groups"]:
        weight = group.get("weight")
        if type(weight) not in {int, float} or not math.isfinite(weight) or weight <= 0:
            raise ValueError("Freeze a positive original-goal group weight")
        for item in group["items"]:
            if item.get("origin") not in {"user_requirement", "source_relation"}:
                raise ValueError("Authored design choices cannot become evaluation requirements")
            for key in ("importance_reason", "source_evidence", "pass_rule", "fail_rule"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError("Criteria need " + key)
            if not isinstance(item.get("allowed_variation"), list):
                raise ValueError("Specify allowed variation, including an explicit empty list")
    english({k: card[k] for k in ("requirement", "allowed_changes", "groups", "ambiguities")})
    return card


def draft(entry, client, output, *, root, duration=None):
    from evaluation.cli import annotate
    from evaluation.judges import ANNOTATE
    # Benchmark metadata is allowed; previous criteria, prompts and scores are not.
    entry = {k:entry[k] for k in ("protocol","task_id","source_id","source_video","source_sha256",
             "requirement","style_family","track","split","creativity","style_required") if k in entry}
    if sha(Path(root)/entry["source_video"]) != entry["source_sha256"]:
        raise ValueError("Source changed before independent criteria authoring")
    if duration is None:
        from evaluation.media import decode
        duration = decode(Path(root) / entry["source_video"])["duration"]
    card = annotate(entry, client, Path(output), Path(root), duration, instruction=ANNOTATE + AUTHORING)
    card.update(criteria_contract=CONTRACT, authoring={"role": "independent_builder",
        "scope": "request_and_source_only", "evidence_sha256": sha(Path(output) / "annotation.raw.json")})
    validate(card, frozen=False)
    save(Path(output) / "card.draft.json", card)
    return card


def freeze(draft_path, output, reviewed_by, reason):
    from evaluation.protocol import signature
    if not reviewed_by.strip() or not reason.strip():
        raise ValueError("Source-grounded review is required before freezing criteria")
    card = copy.deepcopy(validate(load(draft_path), frozen=False))
    card.pop("card_sha256", None)
    card.update(status="frozen", reviewed_by=reviewed_by, review_reason=reason)
    card["card_sha256"] = signature(card)
    validate(card)
    from .rsi_data import sealed
    return sealed(output, card)


def install(state, card):
    card = validate(copy.deepcopy(card))
    source = state["request"]["source"]
    if card["source_sha256"] != source["sha256"] or card["requirement"] != state["request"]["text"]:
        raise ValueError("Task criteria do not match the source/request")
    if abs(card["duration_seconds"] - source["duration_seconds"]) > .1:
        raise ValueError("Task criteria and Planner must use the same source interval")
    if card.get("source_start_seconds",0) != 0:
        raise ValueError("Provide the actual cropped source for a nonzero task interval")
    items = []
    for group in card["groups"]:
        for item in group["items"]:
            items.append({**item, "kind": "edit" if group["kind"] == "edit" else "preserve",
                "priority": "core" if group["kind"] == "preserve_core" or group["kind"] == "edit" and item["mandatory"] else "detail",
                "group": group["id"], "group_weight": group["weight"]})
    req = requirements(items)
    req.update(criteria_contract=CONTRACT, card_sha256=card["card_sha256"],
               allowed_changes=card["allowed_changes"], ambiguities=card["ambiguities"])
    req["sha256"] = digest({k: v for k, v in req.items() if k != "sha256"})
    state.update(requirements=req, requirement_versions=[copy.deepcopy(req)], task_card=card,
                 criteria_authority="independent_frozen", criteria_objections=[])
    return req


def verify_state(state):
    if state.get("criteria_authority") == "independent_frozen":
        expected = install({"request": state["request"]}, state["task_card"])
        if expected != state.get("requirements") or state.get("requirement_versions") != [expected]:
            raise ValueError("Frozen criteria changed; correct the card in a new comparison run")


def objection(state, text, evidence):
    if not state.get("task_card") or not isinstance(text, str) or not text.strip() or not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("An objection needs frozen criteria, a reason and request/source evidence")
    english([text, evidence])
    row = {"text": text, "evidence": evidence, "card_sha256": state["task_card"]["card_sha256"],
           "status": "recorded_for_review; current criteria unchanged"}
    state.setdefault("criteria_objections", []).append(row)
    return row
