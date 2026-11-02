"""Independent final main dimensions: deterministic evidence-preserving projection."""

import copy
import json
from pathlib import Path
from .validation import DIMENSIONS, validate_report
from planner_harness.common import load
from planner_harness.execution import immutable
from planner_harness.report_call import call_report, verify_answer, verify_inputs

VERSION = "final-main-field-evidence-v1"


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
    errors = []
    for dimension, row in report["main_scores"].items():
        trial = copy.deepcopy(baseline)
        trial["main_scores"][dimension] = row
        try:
            validate_report(trial, packet)
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
                    "original": copy.deepcopy(row),
                    "replacement": replacement,
                }
            )
    validate_report(result, packet)
    return result, errors


def evaluate(directory, model, packet, images):
    errors = []

    def accept(value, packet):
        projected, invalid = project(value, packet)
        errors[:] = invalid
        value.clear()
        value.update(projected)

    report, binding = call_report(
        directory, model, packet, images, accept, usage="independent_final"
    )
    projection = {"version": VERSION, "answer_binding": binding, "errors": errors}
    immutable(Path(directory) / "final-main-projection.json", projection)
    return report, binding, projection


def verify(directory, result, packet, model):
    directory = Path(directory)
    projection = load(directory / "final-main-projection.json")
    call = verify_answer(
        directory, result["report"], project=lambda value: project(value, packet)[0]
    )
    from planner_harness.json_output import decode_object

    _, errors = project(decode_object((call / "response.txt").read_text()), packet)
    expected = {
        "version": VERSION,
        "answer_binding": load(directory / "selected-answer.json"),
        "errors": errors,
    }
    if (
        projection != expected
        or result.get("main_projection") != expected
        or result["answer_binding"] != expected["answer_binding"]
    ):
        raise ValueError("Final main projection binding changed")
    verify_inputs(call, model, packet, [r["path"] for r in packet["images"]])
    return call
