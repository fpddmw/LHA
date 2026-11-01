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


def request_job(harness, kind, args, event_id, *, internal=False):
    state = harness.state
    from .creative import active
    creative = active(state)
    if creative:
        if state.get("unresolved_jobs"):
            raise ValueError("An existing tool outcome needs reconciliation; no replacement job was submitted")
        allowed = {"generate": {"input_video", "prompt", "seed"},
                   "critique": {"video", "compare_to", "focus", "extra_checks"}}
        if kind not in allowed or set(args) - allowed[kind]:
            raise ValueError("Unsupported creative-loop execution arguments")
    if state["config"].get("mode", "plan") != "loop":
        raise ValueError("This planning-only run has no execution tools")
    identity = args.get("input_video" if kind == "generate" else "video", "source")
    if identity not in state["videos"]:
        raise ValueError("Choose a video ID present in this task")
    profile = state["config"].get("execution", {})
    if kind == "generate":
        limit = state["config"].get("max_generations")
        if limit is not None and state["generation_requests"] >= limit:
            from .delivery import is_delivery
            if is_delivery(state):
                state["status"] = "budget_exhausted"
            return {"status": "limit_reached", "message": "Generation resource limit reached. A resource stop leaves a delivery task incomplete; existing candidates remain available."}
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
        if creative and profile.get("seed_sequence") is not None:
            sequence = profile["seed_sequence"]
            if set(sequence) != {"start", "step"} or any(type(v) is not int for v in sequence.values()):
                raise ValueError("Use an explicit integer seed start and step")
            # Failed attempts do not advance the paired successful-generation index.
            completed = sum(1 for v in state["videos"].values() if v.get("parent") and not v.get("imported"))
            seed = sequence["start"] + sequence["step"] * completed
            if "seed" in args and args["seed"] != seed:
                raise ValueError("This experiment freezes the seed sequence; input and prompt remain your choices")
            payload["renderer"] = {**payload["renderer"], "seed": seed}
        if state["config"].get("rsi"):
            from .ledger import intent, resolve_baseline
            if not state.get("requirements"):
                raise ValueError("Define requirements before the first RSI generation")
            wanted = intent(args.get("intent"), state["requirements"])
            from .task_criteria import verify_state
            verify_state(state)
            known_cards = {c["id"] for topic in harness.knowledge.experiences for c in topic.get("cards", [])}
            if not set(wanted.get("cards", [])) <= known_cards:
                raise ValueError("Declared skill IDs must exist in this frozen knowledge version")
            baseline = resolve_baseline(state, wanted)
            contenders = args.get("contenders", [])
            if not isinstance(contenders, list) or any(c not in state["videos"] for c in contenders) or len(set(contenders) | {"source", identity}) + 1 > 4:
                raise ValueError("Source, generated output, input and contenders must fit four distinct videos")
            payload.update(intent=intent(args.get("intent"), state["requirements"]),
                           requirements=copy.deepcopy(state["requirements"]), contenders=contenders,
                           comparison_baseline=baseline, logical_attempt=state["generation_requests"] + 1)
            if len(set(contenders) | {"source", identity, baseline}) + 1 > 4:
                raise ValueError("Source, output, input, baseline and contenders must fit four videos; choose fewer optional contenders")
            seeds = state["config"]["rsi"].get("seed_schedule")
            if seeds is not None:
                seed = seeds[state["generation_requests"]]
                if "seed" in args and args["seed"] != seed:
                    raise ValueError("Paired seed schedule cannot be overridden")
                payload["renderer"] = {**payload["renderer"], "seed": seed}
            sequence = state["config"]["rsi"].get("seed_sequence")
            if sequence is not None:
                seed = sequence["start"] + sequence["step"] * state["generation_requests"]
                if "seed" in args and args["seed"] != seed:
                    raise ValueError("Recorded seed sequence cannot be overridden")
                payload["renderer"] = {**payload["renderer"], "seed": seed}
    elif kind == "critique" and creative:
        from .creative import review_payload
        payload, cached = review_payload(harness, args)
        if cached is not None:
            return cached
    elif kind == "critique":
        if not profile.get("critic"):
            return {"status": "unavailable", "message": "The active Critic is not configured for this task."}
        if state["config"].get("rsi"):
            # A failed worker envelope can still hide an ambiguous provider outcome.
            # Changing the job ID must not silently bypass that dispatch marker.
            for prior_id, prior in state["jobs"].items():
                if prior["kind"] != "critique" or prior["payload"]["video_id"] != identity:
                    continue
                calls = harness.output / "jobs" / prior_id / "active-critic/calls"
                unresolved = [p for p in calls.glob("*/submitted.json") if not p.with_name("response.txt").exists()]
                if unresolved:
                    return {"status": "requires_reconciliation", "job_id": prior_id,
                            "message": "An earlier review of this candidate has an uncertain model call. Reconcile it before requesting another review; no new call was dispatched."}
        comparison = args.get("compare_to")
        comparisons = comparison if isinstance(comparison, list) else [comparison] if comparison is not None else []
        if any(c not in state["videos"] for c in comparisons):
            raise ValueError("Unknown comparison video")
        selected = {"source", identity}
        selected.update(comparisons)
        # The immediate input, root and alternative are the relevant visual comparisons.
        # Distant ancestry stays provenance rather than growing every review's image set.
        parent = state["videos"][identity].get("parent")
        if parent:
            selected.add(parent)
        if len(selected) > 4:
            raise ValueError("Review at most four distinct videos including source and actual input")
        review_videos = {k: copy.deepcopy(v) for k, v in state["videos"].items() if k in selected}
        for video in review_videos.values():
            if video.get("parent") and video["parent"] not in selected:
                video["recorded_parent_not_in_review"] = video.pop("parent")
        payload = {"video_id": identity, "original": state["videos"]["source"],
                   "videos": review_videos,
                   "request": state["request"]["text"], "question": args.get("question", ""),
                   "compare_to": comparison, "critic": profile["critic"]}
        if state["config"].get("rsi"):
            from .ledger import digest
            config = state["config"]["rsi"]
            if digest(profile["critic"]) != config["critic_profile_sha256"]:
                raise ValueError("Frozen RSI Critic profile changed")
            if "requirements" in args and not internal:
                raise ValueError("Use the requirements operation to revise the task; critique cannot replace its goal")
            req = args.get("requirements") if internal else state.get("requirements")
            if not req:
                raise ValueError("Define requirements before RSI review")
            payload.update(requirements=copy.deepcopy(req), frozen_critic=copy.deepcopy(config["critic_materials"]))
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
    if state["config"].get("workflow") == "creative_loop_v1" and response["status"] == "failed" and (response.get("outcome_unknown") or response.get("failure_kind") == "model_transport"):
        detail = {"job_id": job["id"], "outcome_unknown": response.get("outcome_unknown", False),
                  "failure_kind": response.get("failure_kind", "render_outcome"), "error": response.get("error")}
        state.setdefault("unresolved_jobs", {})[job["id"]] = detail
        state["status"] = "needs_reconciliation"
        if job["kind"] == "generate":
            state["renderer_submission"] = {"status": "outcome_unknown", **detail}
        harness.checkpoint()
        return False
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
        if p.get("reuse_provenance"):
            info["reuse_provenance"] = p["reuse_provenance"]
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
        if state["config"].get("workflow") == "creative_loop_v1":
            from critic_harness.one_shot import validate_report, PROTOCOL
            feedback = response["payload"]
            if feedback.get("protocol") != PROTOCOL or feedback.get("profile_sha256") != job["payload"]["critic"]["frozen_profile"]["sha256"]:
                raise ValueError("Unexpected creative Critic protocol")
            packet = load(feedback["request_path"])
            visible = json.loads(packet["user_text"])
            frozen = job["payload"]["critic"]["frozen_profile"]
            if packet.get("profile_sha256") != frozen["sha256"] or packet.get("system_prompt") != frozen["rubric"]:
                raise ValueError("Critic request differs from frozen instructions")
            if visible["candidate_id"] != job["payload"]["video_id"] or visible["original_request"] != job["payload"]["request"]:
                raise ValueError("Critic task binding mismatch")
            if set(visible["videos"]) != set(job["payload"]["videos"]) or any(v["sha256"] != job["payload"]["videos"][i]["sha256"] for i, v in visible["videos"].items()):
                raise ValueError("Critic video binding mismatch")
            if visible.get("focus") != job["payload"].get("focus", "") or visible.get("compare_to") != job["payload"].get("compare_to") or [c["text"] for c in visible["extra_checks"]] != job["payload"].get("extra_checks", []):
                raise ValueError("Critic focus/checks differ from signed request")
            if any(sha(e["path"]) != e["sha256"] for e in packet["images"]):
                raise ValueError("Critic evidence changed before collection")
            validate_report(feedback["report"], packet)
        if job["kind"] == "critique" and job["payload"].get("requirements"):
            if response["payload"].get("outcome", {}).get("requirements_sha256") != job["payload"]["requirements"]["sha256"]:
                raise ValueError("Critic requirement version differs from signed job")
        state["evaluations"][job["id"]] = {"video_id": job["payload"]["video_id"], **response["payload"]}
    elif job["kind"] == "generate":
        state["renderer_submission"] = {"status": "failed", "job_id": job["id"], "error": response.get("error")}
    immutable(path.with_name("collected.json"), response)
    event = {"event_id": job["id"] + "-result", "at": stamp(), "status": "ok",
             "request": {"action": "tool_result", "arguments": {"job_id": job["id"]}}, "result": result}
    state["events"].append(event)
    save(harness.output / "events" / (event["event_id"] + ".json"), event)
    state.update(pending_tool=None, status="running")
    if state["config"].get("rsi"):
        from .ledger import build
        state["task_memory"] = build(state)
    harness.checkpoint()
    return True
