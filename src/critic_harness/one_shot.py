"""Frozen descriptive review: deterministic evidence, one response, no agent loop."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from planner_harness.common import load, save, sha
from planner_harness.execution import signature, immutable
from planner_harness.video import Video

PROTOCOL = "lha-creative-review-v1"
DIMENSIONS = ("instruction_adherence", "content_preservation", "temporal_consistency",
              "visual_integrity", "aesthetic_coherence")
POLICY = {"overview_frames": 8, "dense_windows": 3, "dense_frames": 6,
          "scope": "Full-clip overview plus three consecutive-frame windows; unsampled motion remains uncertain."}


def frozen_profile():
    body = {"protocol_id": PROTOCOL, "rubric": Path(__file__).with_name("CREATIVE_RUBRIC.md").read_text(encoding="utf-8"),
            "dimensions": list(DIMENSIONS), "evidence_policy": POLICY,
            "model": "gpt-6.1-sol", "reasoning_effort": "high", "schema_version": 1,
            "implementation_sha256": {"review": sha(__file__),
                "video": sha(Path(__file__).parents[1] / "planner_harness/video.py"),
                "transport": sha(Path(__file__).parents[1] / "planner_harness/model_call.py")}}
    return {**body, "sha256": signature(body)}


def verify_profile(profile):
    if profile.get("sha256") != signature({k: v for k, v in profile.items() if k != "sha256"}):
        raise ValueError("Frozen review profile hash mismatch")
    if profile != frozen_profile():
        raise ValueError("This runtime differs from the frozen review profile; use the recorded code snapshot")


def prepare_request(request, candidate_id, videos, directory, profile, *, compare_to=None, focus="", extra_checks=None):
    """Only whitelisted fields reach the model. Prompts/ancestry/preferences stay out."""
    verify_profile(profile)
    if not isinstance(focus, str) or not isinstance(extra_checks or [], list) or any(
            not isinstance(c, str) or not c.strip() for c in (extra_checks or [])):
        raise ValueError("focus is text; extra_checks is a list of nonempty text")
    ids = list(dict.fromkeys(["source", candidate_id] + ([compare_to] if compare_to else [])))
    if candidate_id == "source" or any(i not in videos for i in ids):
        raise ValueError("Review a candidate with the original source and an available comparison")
    images, evidence, video_meta = [], [], {}
    directory = Path(directory)
    for identity in ids:
        info = videos[identity]
        if sha(info["path"]) != info["sha256"]:
            raise ValueError("Review video changed")
        video = Video(info["path"], directory / identity)
        video_meta[identity] = {k: video.info[k] for k in ("sha256", "fps", "frames", "duration_seconds", "width", "height")}
        groups = [("overview", video.observe("overview", count=POLICY["overview_frames"]))]
        count = min(POLICY["dense_frames"], video.info["frames"])
        last_start = video.info["frames"] - count
        for number, start in enumerate(sorted({0, last_start // 2, last_start})):
            groups.append(("consecutive_frames", video.observe("dense-" + str(number),
                start=start / video.info["fps"], end=(start + count - 1) / video.info["fps"], count=count)))
        for group, observation in groups:
            for frame in observation["frames"]:
                evidence_id = f"{identity}:{observation['observation_id']}:{frame['frame_index']}"
                images.append(frame["path"])
                evidence.append({"id": evidence_id, "video_id": identity, "kind": group,
                                 "attachment": len(images), **frame})
    checks = [{"id": f"check-{i + 1}", "text": c} for i, c in enumerate(extra_checks or [])]
    visible = {"protocol_id": profile["protocol_id"], "candidate_id": candidate_id,
               "original_request": request, "videos": video_meta, "compare_to": compare_to,
               "focus": focus, "extra_checks": checks, "evidence_policy": profile["evidence_policy"],
               "evidence": [{k: v for k, v in e.items() if k != "path"} for e in evidence]}
    packet = {"system_prompt": profile["rubric"], "user_text": json.dumps(visible, ensure_ascii=False, indent=2),
              "images": evidence, "profile_sha256": profile["sha256"]}
    immutable(directory / "request.json", packet)
    return packet, images


def _keys(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError("Unexpected review fields; use the frozen descriptive schema")


def validate_report(report, packet):
    visible = json.loads(packet["user_text"])
    _keys(report, ("protocol_id", "candidate_id", "main_scores", "comparisons", "extra_checks", "unassessed"))
    if report["protocol_id"] != PROTOCOL or report["candidate_id"] != visible["candidate_id"]:
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
            if key in row and (not isinstance(row[key], list) or any(not isinstance(v, str) for v in row[key])):
                raise ValueError("Limitations must be text entries")
        return [refs[i] for i in ids]

    for dimension, row in report["main_scores"].items():
        _keys(row, ("status", "score", "reason", "evidence_refs", "limitations"))
        if row["status"] == "scored":
            if type(row["score"]) is not int or not 0 <= row["score"] <= 4:
                raise ValueError("Scores are integers from 0 through 4")
        elif row["status"] not in {"unknown", "not_assessed", "not_applicable"} or row["score"] is not None:
            raise ValueError("Unassessed scores must remain null with an explicit status")
        cited = evidence(row, row["status"] == "scored")
        if row["status"] == "scored":
            if visible["candidate_id"] not in {e["video_id"] for e in cited}:
                raise ValueError("A score must cite the candidate")
            if dimension == "content_preservation" and "source" not in {e["video_id"] for e in cited}:
                raise ValueError("Preservation needs source and candidate evidence")
            if dimension == "temporal_consistency":
                indices = sorted({e["frame_index"] for e in cited if e["kind"] == "consecutive_frames"
                                  and e["video_id"] == visible["candidate_id"]})
                if not any(b == a + 1 for a, b in zip(indices, indices[1:])):
                    raise ValueError("Temporal scores need consecutive candidate evidence")
    if not isinstance(report["comparisons"], list) or not isinstance(report["extra_checks"], list):
        raise ValueError("Comparisons and supplemental checks must be lists")
    for row in report["comparisons"]:
        _keys(row, ("against", "dimension", "change", "reason", "evidence_refs"))
        if not visible["compare_to"] or row["against"] != visible["compare_to"] or row["dimension"] not in DIMENSIONS:
            raise ValueError("Comparison is outside the requested evidence")
        if row["change"] not in {"better", "same", "worse", "unknown"}:
            raise ValueError("Invalid descriptive comparison")
        cited = evidence(row, row["change"] != "unknown")
        if row["change"] != "unknown" and not {visible["candidate_id"], row["against"]} <= {e["video_id"] for e in cited}:
            raise ValueError("Comparison needs evidence from both videos")
    expected = [c["id"] for c in visible["extra_checks"]]
    if [c.get("id") for c in report["extra_checks"]] != expected:
        raise ValueError("Supplemental checks must match the request")
    for row in report["extra_checks"]:
        _keys(row, ("id", "status", "reason", "evidence_refs", "limitations"))
        if row["status"] not in {"pass", "partial", "fail", "unknown"}:
            raise ValueError("Invalid supplemental check status")
        evidence(row, row["status"] != "unknown")
    if not isinstance(report["unassessed"], list) or any(not isinstance(s, str) for s in report["unassessed"]):
        raise ValueError("unassessed must contain text limitations")
    # Fail obvious advice rather than forwarding it or asking a second model to repair it.
    prose = " ".join([r["reason"] + " " + " ".join(r.get("limitations", []))
                      for r in list(report["main_scores"].values()) + report["comparisons"] + report["extra_checks"]]
                     + report["unassessed"])
    if re.search(r"\b(should|recommend(?:ed|ation|ations)?|next (?:step|attempt|generation)|try (?:to|a|another)|"
                 r"(?:rewrite|revise|change) the prompt|(?:choose|select|deliver) (?:v\d+|candidate|the)|"
                 r"(?:restart|regenerate|stop generating|continue editing))\b", prose, re.I):
        raise ValueError("Critic output contains prohibited action guidance")
    return report


def run_review(payload, directory, model=None):
    from planner_harness.model_call import call_text
    directory = Path(directory) / "one-shot-critic"
    profile = payload["critic"]["frozen_profile"]
    packet, images = prepare_request(payload["request"], payload["video_id"], payload["videos"],
        directory, profile, compare_to=payload.get("compare_to"), focus=payload.get("focus", ""),
        extra_checks=payload.get("extra_checks", []))
    if model is None:
        from vlm.codex_vlm import CodexVisionModel
        model = CodexVisionModel(role="online_critic")
        model.model, model.reasoning_effort = profile["model"], profile["reasoning_effort"]
    if model.model != profile["model"] or model.reasoning_effort != profile["reasoning_effort"]:
        raise ValueError("Critic model differs from frozen profile")
    try:
        raw = call_text(directory / "call", model, packet["system_prompt"], packet["user_text"], images)
        stripped = raw.strip()
        if stripped.startswith("```json\n") and stripped.endswith("```"):
            stripped = stripped[8:-3].strip()
        report = validate_report(json.loads(stripped), packet)
    except (ValueError, TypeError, KeyError) as exc:
        save(directory / "invalid-report.json", {"error": str(exc), "semantic_retry": False})
        raise
    result = {"protocol": PROTOCOL, "usage": "online_feedback", "video_id": payload["video_id"],
              "profile_sha256": profile["sha256"], "report": report,
              "evidence": packet["images"], "request_path": str(directory / "request.json")}
    immutable(directory / "feedback.json", result)
    return result
