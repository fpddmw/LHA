"""Formal final-score schema and evidence validation; never an online rubric."""

import json
import re

DIMENSIONS = (
    "instruction_adherence",
    "content_preservation",
    "temporal_consistency",
    "visual_integrity",
    "aesthetic_coherence",
)


def _keys(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError("Unexpected review fields; use the frozen descriptive schema")


def validate_report(report, packet):
    visible = json.loads(packet["user_text"])
    fields = (
        "protocol_id",
        "candidate_id",
        "main_scores",
        "comparisons",
        "extra_checks",
        "unassessed",
    )
    _keys(report, fields)
    if (
        visible["protocol_id"] != "lha-low-high-final-v3"
        or report["protocol_id"] != visible["protocol_id"]
        or report["candidate_id"] != visible["candidate_id"]
    ):
        raise ValueError("Review identity mismatch")
    _keys(report["main_scores"], DIMENSIONS)
    refs = {e["id"]: e for e in visible["evidence"]}

    def evidence(row, required=False):
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            raise ValueError("Review needs an observable reason")
        ids = row.get("evidence_refs")
        if not isinstance(ids, list) or any(not isinstance(i, str) or i not in refs for i in ids):
            raise ValueError("Unknown evidence reference")
        if required and not ids:
            raise ValueError("An assessed finding needs visual evidence")
        for key in ("limitations",):
            if key in row and (
                not isinstance(row[key], list) or any(not isinstance(v, str) for v in row[key])
            ):
                raise ValueError("Limitations must be text entries")
        return [refs[i] for i in ids]

    for dimension, row in report["main_scores"].items():
        _keys(row, ("status", "score", "reason", "evidence_refs", "limitations"))
        if row["status"] == "scored":
            if type(row["score"]) is not int or not 0 <= row["score"] <= 4:
                raise ValueError("Scores are integers from 0 through 4")
        elif (
            row["status"] not in {"unknown", "not_assessed", "not_applicable"}
            or row["score"] is not None
        ):
            raise ValueError("Unassessed scores must remain null with an explicit status")
        cited = evidence(row, row["status"] == "scored")
        if row["status"] == "scored":
            if visible["candidate_id"] not in {e["video_id"] for e in cited}:
                raise ValueError("A score must cite the candidate")
            if dimension == "content_preservation" and "source" not in {
                e["video_id"] for e in cited
            }:
                raise ValueError("Preservation needs source and candidate evidence")
            if dimension == "temporal_consistency":
                dense = [
                    e
                    for e in cited
                    if e["kind"] == "consecutive_frames"
                    and e["video_id"] == visible["candidate_id"]
                ]
                # Window endpoints identify continuous evidence only when every
                # intervening frame was supplied in that same dense window.
                supported = False
                for first in dense:
                    window = first["id"].rsplit(":", 1)[0]
                    available = {
                        e["frame_index"]
                        for e in refs.values()
                        if e["kind"] == "consecutive_frames"
                        and e["video_id"] == visible["candidate_id"]
                        and e["id"].rsplit(":", 1)[0] == window
                    }
                    for last in dense:
                        if (
                            last["id"].rsplit(":", 1)[0] == window
                            and last["frame_index"] > first["frame_index"]
                        ):
                            supported |= (
                                set(range(first["frame_index"], last["frame_index"] + 1))
                                <= available
                            )
                if not supported:
                    raise ValueError("Temporal scores need consecutive candidate evidence")
    if not isinstance(report["comparisons"], list) or not isinstance(report["extra_checks"], list):
        raise ValueError("Comparisons and supplemental checks must be lists")
    for row in report["comparisons"]:
        _keys(row, ("against", "dimension", "change", "reason", "evidence_refs"))
        if (
            not visible["compare_to"]
            or row["against"] != visible["compare_to"]
            or row["dimension"] not in DIMENSIONS
        ):
            raise ValueError("Comparison is outside the requested evidence")
        if row["change"] not in {"better", "same", "worse", "unknown"}:
            raise ValueError("Invalid descriptive comparison")
        cited = evidence(row, row["change"] != "unknown")
        if row["change"] != "unknown" and not {visible["candidate_id"], row["against"]} <= {
            e["video_id"] for e in cited
        }:
            raise ValueError("Comparison needs evidence from both videos")
    if visible["compare_to"] and not report["comparisons"]:
        raise ValueError(
            "A requested comparison needs descriptive findings or an explicit unknown comparison"
        )
    expected = [c["id"] for c in visible["extra_checks"]]
    if any(not isinstance(c, dict) for c in report["extra_checks"]):
        raise ValueError("Each supplemental check must be an object")
    if [c.get("id") for c in report["extra_checks"]] != expected:
        raise ValueError("Supplemental checks must match the request")
    for row in report["extra_checks"]:
        fields = ("id", "status", "reason", "evidence_refs", "limitations")
        _keys(row, fields)
        # The signed request owns the question text; copying is not a score criterion.
        question = next(c["text"] for c in visible["extra_checks"] if c["id"] == row["id"])
        if row["status"] not in {"pass", "partial", "fail", "unknown"}:
            raise ValueError("Invalid supplemental check status")
        cited = evidence(row, row["status"] != "unknown")
        if row["status"] != "unknown":
            identities = {e["video_id"] for e in cited}
            if visible["candidate_id"] not in identities:
                raise ValueError("A supplemental candidate finding must cite the candidate")
            question = next(c["text"] for c in visible["extra_checks"] if c["id"] == row["id"])
            if (
                re.search(
                    r"\b(source|original|preserv\w*|retain\w*|unchanged|same as)\b", question, re.I
                )
                and "source" not in identities
            ):
                raise ValueError("A supplemental source-relative finding must cite the source")
            if (
                visible["compare_to"]
                and re.search(r"\b(compare\w*|better|worse|improv\w*)\b", question, re.I)
                and visible["compare_to"] not in identities
            ):
                raise ValueError("A relative supplemental finding must cite the comparison")
    if not isinstance(report["unassessed"], list) or any(
        not isinstance(s, str) for s in report["unassessed"]
    ):
        raise ValueError("unassessed must contain text limitations")
    return report
