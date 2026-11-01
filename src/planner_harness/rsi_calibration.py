"""Saved-case judge calibration with explicit review, provenance and disagreement reports."""
from pathlib import Path
import re
from .common import load, sha
from .ledger import digest
from .rsi_data import sealed, verify_seal


def profile_key(profile):
    return digest({k: v for k, v in profile.items() if k not in {"calibration", "calibration_status"}})


def prepare(cases, profile, output):
    from .rsi_judge import protocol_hash
    if not cases or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Calibration needs unique saved cases")
    if profile.get("protocol_sha256") != protocol_hash():
        raise ValueError("Calibration must use the current independent scoring protocol")
    rows = []
    for case in cases:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", case["id"]):
            raise ValueError("Calibration case ID must be a safe path component")
        card = load(case["card"])
        task = {"card": str(Path(case["card"]).resolve()), "card_file_sha256": sha(case["card"]),
                "source_sha256": card["source_sha256"], "request": card["requirement"]}
        if case.get("references"):
            task.update(references=str(Path(case["references"]).resolve()), references_sha256=sha(case["references"]))
        rows.append({"id": case["id"], "task": task,
                     "video": {"path": str(Path(case["video"]).resolve()), "sha256": sha(case["video"]), "time_mapping": case.get("time_mapping")},
                     "reference": {"path": str(Path(case["reference"]).resolve()), "sha256": sha(case["reference"])},
                     "reference_role": case.get("reference_role", "historical_model_judgment")})
    body = {"schema": "lha-rsi-calibration-v1", "profile": profile, "profile_sha256": profile_key(profile), "cases": rows,
            "scope": "Saved model judgments are comparators, not human gold. Review disagreements before approving the new judge."}
    return sealed(output, {**body, "sha256": digest(body)})


def _scores(raw):
    if "rsi_metrics" in raw:
        return raw.get("score", {})
    from evaluation.compat import canonical_record
    return canonical_record(raw)["result"]


def run(manifest_path, output, client, *, root):
    from .rsi_judge import score_case, protocol_hash
    manifest = verify_seal(load(manifest_path))
    profile = manifest["profile"]
    if client.model != profile["model"] or getattr(client, "reasoning_effort", None) != profile.get("reasoning_effort") or profile["protocol_sha256"] != protocol_hash():
        raise ValueError("Calibration client/protocol differs from its frozen profile")
    output = Path(output).resolve()
    rows = []
    for case in manifest["cases"]:
        if sha(case["reference"]["path"]) != case["reference"]["sha256"]:
            raise ValueError("Historical calibration reference changed")
        scored = score_case(case["task"], case["video"], profile, client, output / case["id"], root=root, identity=case["id"])
        a, b = _scores(load(case["reference"]["path"])), load(scored["raw"])["score"]
        comparisons = {k: {"reference": a.get("semantic", {}).get(k, {}).get("score"), "candidate": b["semantic"].get(k, {}).get("score")}
                       for k in set(a.get("semantic", {})) | set(b["semantic"])}
        rows.append({"id": case["id"], "output_sha256": case["video"]["sha256"], "score": scored,
                     "reference_role": case["reference_role"], "comparisons": comparisons,
                     "success": {"reference": a.get("success"), "candidate": b.get("success")},
                     "major_damage": {"reference": a.get("major_damage"), "candidate": b.get("major_damage")}})
    from evaluation.reliability import agreement
    metrics = sorted({k for r in rows for k in r["comparisons"]})
    body = {"schema": "lha-rsi-calibration-result-v1", "manifest": str(Path(manifest_path).resolve()), "manifest_sha256": manifest["sha256"],
            "profile_sha256": manifest["profile_sha256"], "rows": rows,
            "agreement": {k: agreement([{"case_id": r["id"], "a": r["comparisons"].get(k, {}).get("reference"),
                                        "b": r["comparisons"].get(k, {}).get("candidate")} for r in rows]) for k in metrics},
            "status": "awaiting_review"}
    return sealed(output / "comparison.json", {**body, "sha256": digest(body)})


def review(comparison, output, reviewed_by, decision, notes):
    if not reviewed_by.strip() or not notes.strip() or decision not in {"approved", "rejected"}:
        raise ValueError("Calibration review needs reviewer, decision and disagreement notes")
    result = verify_seal(load(comparison))
    if not result["rows"]:
        raise ValueError("Review requires completed calibration cases")
    body = {"schema": "lha-rsi-calibration-review-v1", "comparison": str(Path(comparison).resolve()), "comparison_sha256": result["sha256"],
            "profile_sha256": result["profile_sha256"], "reviewed_by": reviewed_by, "decision": decision, "notes": notes}
    return sealed(output, {**body, "sha256": digest(body)})


def verify_calibration(profile):
    ref = profile.get("calibration")
    if not ref or sha(ref["path"]) != ref["sha256"]:
        raise ValueError("Bind an actual reviewed calibration artifact before final scoring")
    review = verify_seal(load(ref["path"]))
    if review.get("decision") != "approved" or review.get("profile_sha256") != profile_key(profile):
        raise ValueError("Calibration is not approved for this exact judge profile")
    result = verify_seal(load(review["comparison"]))
    manifest = verify_seal(load(result["manifest"]))
    if result["sha256"] != review["comparison_sha256"] or manifest["sha256"] != result["manifest_sha256"]:
        raise ValueError("Calibration evidence changed")
    if result["profile_sha256"] != profile_key(profile) or manifest["profile_sha256"] != profile_key(profile):
        raise ValueError("Calibration profile binding changed")
    if {r["id"] for r in result["rows"]} != {c["id"] for c in manifest["cases"]}:
        raise ValueError("Calibration coverage is incomplete")
    for case in manifest["cases"]:
        if sha(case["reference"]["path"]) != case["reference"]["sha256"]:
            raise ValueError("Calibration comparator changed")
        if sha(case["video"]["path"]) != case["video"]["sha256"] or sha(case["task"]["card"]) != case["task"]["card_file_sha256"]:
            raise ValueError("Calibration video or source card changed")
    for row in result["rows"]:
        if sha(row["score"]["raw"]) != row["score"]["raw_sha256"]:
            raise ValueError("Calibration judgment changed")
    return review
