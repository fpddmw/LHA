"""Durable tool jobs. Models supply tool arguments; bookkeeping stays here."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import copy

from .common import load, save, sha, stamp
from .video import Video


def prepare_profile(profile, root, request):
    profile = copy.deepcopy(profile or {})
    if profile.get("mode", "live") not in {"live", "replay"}:
        raise ValueError("Execution mode must be live or replay")
    if profile.get("evaluation"):
        from evaluation.protocol import validate_card
        cfg = profile["evaluation"]
        card = validate_card(cfg.get("card_data") or load(Path(root) / cfg["card"]))
        if card["source_sha256"] != request["source"]["sha256"] or card["requirement"] != request["text"]:
            raise ValueError("Evaluation card must match the original source and exact user request")
        cfg.update(card_data=card, card_sha256=card["card_sha256"])
    return profile


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def immutable(path, value):
    path = Path(path)
    if path.exists():
        if load(path) != value:
            raise ValueError(f"Job record changed: {path}")
    else:
        save(path, value)


def request_job(harness, kind, args, event_id):
    state = harness.state
    if state["config"].get("mode", "plan") != "loop":
        raise ValueError("This planning-only run has no execution tools")
    identity = args.get("input_video" if kind == "generate" else "video", "source")
    if identity not in state["videos"]:
        raise ValueError("Choose a video ID present in this task")
    profile = state["config"].get("execution", {})
    if kind == "generate":
        if state["generation_requests"] >= state["config"]["max_generations"]:
            return {"status": "limit_reached", "message": "Generation budget exhausted. Inspect existing results or finish with an accurate outcome."}
        prompt = args.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("generate needs a nonempty English prompt")
        if any("\u3400" <= c <= "\u9fff" for c in prompt):
            raise ValueError("Use English for the execution prompt")
        payload = {"input_id": identity, "input": state["videos"][identity], "prompt": prompt,
                   "renderer": profile.get("renderer", {})}
        if "seed" in args:
            if type(args["seed"]) is not int:
                raise ValueError("seed must be an integer")
            payload["renderer"] = {**payload["renderer"], "seed": args["seed"]}
    else:
        if not profile.get("evaluation"):
            return {"status": "unavailable", "message": "No external evaluator is configured. You can inspect the videos directly; do not invent a metric result."}
        payload = {"video_id": identity, "video": state["videos"][identity], "original": state["videos"]["source"],
                   "request": state["request"]["text"], "question": args.get("question", ""), "evaluation": profile["evaluation"]}
    body = {"id": event_id + "-" + kind, "kind": kind,
            "mode": profile.get("mode", "live"), "payload": payload}
    job = {**body, "sha256": signature(body)}
    # Same event after interruption reuses the same identity and budget charge.
    directory = harness.output / "jobs" / job["id"]
    immutable(directory / "request.json", job)
    if job["id"] not in state["jobs"]:
        state["jobs"][job["id"]] = job
        if kind == "generate":
            state["generation_requests"] += 1
    state.update(status="waiting_tool", pending_tool=job["id"])
    if kind == "generate":
        state["renderer_submission"] = {"status": "pending", "job_id": job["id"]}
    return {"status": "pending", "job_id": job["id"], "input_video": identity,
            "message": "The runtime will return the tool result here; no polling action is needed."}


def collect(harness):
    state = harness.state
    job = state["jobs"][state["pending_tool"]]
    path = harness.output / "jobs" / job["id"] / "response.json"
    if not path.exists():
        return False
    response = load(path)
    if response.get("request_sha256") != job["sha256"] or response.get("mode") != job["mode"]:
        raise ValueError("Tool response does not match the pending job")
    if response.get("status") not in {"complete", "failed"}:
        raise ValueError("Only final worker responses can be collected")
    result = response
    if response["status"] == "complete" and job["kind"] == "generate":
        p = response["payload"]
        receipt = p["execution"]
        if receipt.get("requested_prompt") != job["payload"]["prompt"] or receipt.get("input_sha256") != job["payload"]["input"]["sha256"]:
            raise ValueError("Generation input/prompt receipt mismatch")
        if not receipt.get("effective_prompt"):
            raise ValueError("Missing effective renderer text")
        if job["mode"] == "live":
            if receipt["effective_prompt"] != job["payload"]["prompt"]:
                raise ValueError("Effective renderer text differs from the submitted prompt")
            expected_settings = job["payload"]["renderer"].get("generation", {})
            if any(receipt.get("settings", {}).get(k) != v for k, v in expected_settings.items()):
                raise ValueError("Renderer settings differ from the signed job")
            expected_seed = job["payload"]["renderer"].get("seed")
            if expected_seed is not None and receipt.get("seed") != expected_seed:
                raise ValueError("Renderer seed differs from the signed job")
            if receipt.get("preflight") != "passed" or not receipt.get("model_revision") or not receipt.get("code_revision"):
                raise ValueError("Live generation requires model/code provenance and successful preflight")
            n, limit = receipt.get("token_count"), receipt.get("token_limit")
            if type(n) is not int or type(limit) is not int or not 0 < n <= limit:
                raise ValueError("Missing or invalid tokenizer preflight")
        elif not p.get("replay_provenance"):
            raise ValueError("Replay response needs provenance")
        supplied = p["video"]
        if sha(supplied["path"]) != supplied["sha256"]:
            raise ValueError("Generated video hash mismatch")
        video_id = "v" + str(1 + sum(k != "source" and not v.get("imported") for k, v in state["videos"].items()))
        # Stable identity after a crash before the collection checkpoint.
        video_id = next((k for k, v in state["videos"].items() if v.get("job_id") == job["id"]), video_id)
        directory = harness.output / "videos" / video_id
        directory.mkdir(parents=True, exist_ok=True)
        video = Video(supplied["path"], directory)
        expected = job["payload"]["renderer"].get("output", {})
        if expected.get("frames") and expected["frames"] != video.info["frames"]:
            raise ValueError("Generated frame count differs from configured output")
        if expected.get("fps") and abs(expected["fps"] - video.info["fps"]) > .001:
            raise ValueError("Generated FPS differs from configured output")
        for field in ("width", "height"):
            if expected.get(field) and expected[field] != video.info[field]:
                raise ValueError(f"Generated {field} differs from configured output")
        video.observe("decode-check", count=2)
        target = directory / ("video" + Path(supplied["path"]).suffix)
        if target.exists():
            if sha(target) != supplied["sha256"]:
                raise ValueError("Collected video differs from saved output")
        else:
            temporary = target.with_suffix(target.suffix + ".part")
            shutil.copyfile(supplied["path"], temporary)
            if sha(temporary) != supplied["sha256"]:
                raise ValueError("Output changed during collection")
            os.replace(temporary, target)
        info = {**video.info, "path": str(target), "parent": job["payload"]["input_id"],
                "prompt": job["payload"]["prompt"], "job_id": job["id"], "execution": receipt,
                "replay_provenance": p.get("replay_provenance")}
        # This records conditioning ancestry, not a claim that generated motion is aligned.
        indices = receipt.get("conditioning_source_indices")
        parent = state["videos"][info["parent"]]
        parent_times = parent.get("time_mapping", {}).get("source_times_seconds")
        if info["parent"] == "source":
            parent_times = [i / parent["fps"] for i in range(parent["frames"])]
        if job["mode"] == "live" and indices is not None and parent_times is not None:
            if len(indices) != info["frames"] or any(type(i) is not int or not 0 <= i < len(parent_times) for i in indices):
                raise ValueError("Invalid conditioning ancestry indices")
            info["time_mapping"] = {"source_sha256": state["videos"]["source"]["sha256"],
                "output_sha256": info["sha256"], "source_times_seconds": [parent_times[i] for i in indices],
                "basis": "Composed conditioning frame indices; generated motion correspondence remains to be evaluated."}
        state["videos"][video_id] = info
        state["renderer_submission"] = {"status": "complete", "job_id": job["id"], "video_id": video_id}
        observation = Video(target, harness.output).observe("result-" + video_id)
        observation.update(video_id=video_id, scope="Generated candidate overview; sparse samples do not establish precise continuous motion.")
        state["observations"].append(observation)
        result = {"status": "complete", "video_id": video_id, "video": info,
                  "mode": job["mode"], "observation": observation}
    elif response["status"] == "complete":
        # Metric ownership stays in the configured evaluator. Preserve its complete response.
        state["evaluations"][job["id"]] = {"video_id": job["payload"]["video_id"], **response["payload"]}
    elif job["kind"] == "generate":
        state["renderer_submission"] = {"status": "failed", "job_id": job["id"], "error": response.get("error")}
    immutable(path.with_name("collected.json"), response)
    event = {"event_id": job["id"] + "-result", "at": stamp(), "status": "ok",
             "request": {"action": "tool_result", "arguments": {"job_id": job["id"]}}, "result": result}
    state["events"].append(event)
    save(harness.output / "events" / (event["event_id"] + ".json"), event)
    state.update(pending_tool=None, status="running")
    harness.checkpoint()
    return True
