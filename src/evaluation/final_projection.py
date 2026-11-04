"""Independent final main dimensions: deterministic evidence-preserving projection."""

import copy
import json
from pathlib import Path
from .validation import DIMENSIONS, validate_report
from planner_harness.common import load
from planner_harness.execution import immutable
from planner_harness.report_call import call_report, verify_answer, verify_inputs

VERSION = "final-main-field-evidence-v3"
STATUSES = {"scored", "unknown", "not_assessed", "not_applicable"}


def normalize_row(row, refs):
    """Repair only unambiguous format slips; every change is recorded with the original.

    Only the observed alias with a numeric score is mapped to scored. Missing,
    unknown and other status words retain normal validation. Invalid frame IDs are dropped;
    the remaining citations must still satisfy the validator on their own.
    """
    if not isinstance(row, dict):
        return row, []
    fixed, notes = copy.deepcopy(row), []
    if fixed.get("status") == "observed" and type(fixed.get("score")) in (int, float):
        notes.append({"field": "status", "from": fixed.get("status"), "to": "scored"})
        fixed["status"] = "scored"
    ids = fixed.get("evidence_refs")
    if isinstance(ids, list):
        kept = [i for i in ids if isinstance(i, str) and i in refs]
        if len(kept) != len(ids):
            notes.append({"field": "evidence_refs", "dropped": [i for i in ids if i not in kept]})
            fixed["evidence_refs"] = kept
    return fixed, notes


def project(report, packet):
    visible = json.loads(packet["user_text"])
    fields = {
        "protocol_id",
        "candidate_id",
        "main_scores",
        "comparisons",
        "extra_checks",
        "unassessed",
    }
    if (
        not isinstance(report, dict)
        or set(report) != fields
        or report["protocol_id"] != visible["protocol_id"]
        or report["candidate_id"] != visible["candidate_id"]
    ):
        raise ValueError("Independent main report identity/schema mismatch")
    if not isinstance(report["main_scores"], dict) or set(report["main_scores"]) != set(DIMENSIONS):
        raise ValueError("Five named main dimensions are required")
    baseline = copy.deepcopy(report)
    baseline["main_scores"] = {
        d: {
            "status": "unknown",
            "score": None,
            "reason": "Unassessed field",
            "evidence_refs": [],
            "limitations": [],
        }
        for d in DIMENSIONS
    }
    validate_report(baseline, packet)
    result = copy.deepcopy(report)
    errors, normalized = [], []
    refs = {e["id"] for e in visible["evidence"]}
    for dimension, original in report["main_scores"].items():
        row, notes = normalize_row(original, refs)
        trial = copy.deepcopy(baseline)
        trial["main_scores"][dimension] = row
        try:
            validate_report(trial, packet)
            if notes:
                result["main_scores"][dimension] = row
                normalized.append({"path": ["main_scores", dimension], "changes": notes,
                                   "original": copy.deepcopy(original)})
        except (ValueError, TypeError, KeyError) as exc:
            replacement = copy.deepcopy(baseline["main_scores"][dimension])
            replacement["reason"] = "Unassessed after field validation: " + str(exc)
            replacement["limitations"] = [
                "Original field and validation error retained in final-main-projection.json"
            ]
            result["main_scores"][dimension] = replacement
            errors.append(
                {
                    "path": ["main_scores", dimension],
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "original": copy.deepcopy(original),
                    "replacement": replacement,
                }
            )
    validate_report(result, packet)
    return result, errors, normalized


def evaluate(directory, model, packet, images):
    directory = Path(directory)
    if (directory / "final-main-projection.json").exists():
        projection = load(directory / "final-main-projection.json")
        binding = projection["answer_binding"]
        if binding != load(directory / 'selected-answer.json'):
            raise ValueError('Final main projection binding changed')
        from planner_harness.json_output import decode_object
        call = Path(binding["call_path"])
        raw = decode_object((call / "response.txt").read_text(encoding="utf-8"))
        verify_answer(directory, raw)
        verify_inputs(call, model, packet, images)
        # Reconstruct the already accepted projection from its recorded edits.
        # Never retry a completed main judgment under a new validator.
        report = copy.deepcopy(raw)
        for row in projection.get("normalized", []):
            refs = {e['id'] for e in json.loads(packet['user_text'])['evidence']}
            replacement, notes = normalize_row(row['original'], refs)
            if notes != row['changes']:
                raise ValueError('Saved normalization requires its original adapter; main judgment was retained')
            report[row['path'][0]][row['path'][1]] = replacement
        for row in projection.get('errors', []):
            report[row['path'][0]][row['path'][1]] = row['replacement']
        return report, binding, projection
    errors, normalized = [], []

    def accept(value, packet):
        projected, invalid, repaired = project(value, packet)
        errors[:] = invalid
        normalized[:] = repaired
        value.clear()
        value.update(projected)

    report, binding = call_report(
        directory, model, packet, images, accept, usage="independent_final"
    )
    projection = {"version": VERSION, "answer_binding": binding, "errors": errors,
                  "normalized": normalized}
    immutable(Path(directory) / "final-main-projection.json", projection)
    return report, binding, projection


def verify(directory, result, packet, model):
    directory = Path(directory)
    if not (directory / "final-main-projection.json").exists():
        raise ValueError('Saved main projection is missing')
    report, binding, projection = evaluate(directory, model, packet, [r['path'] for r in packet['images']])
    if (result.get('report') != report or result.get('main_projection') != projection
            or result.get('answer_binding') != binding):
        raise ValueError('Final main projection binding changed')
    return Path(binding['call_path'])
