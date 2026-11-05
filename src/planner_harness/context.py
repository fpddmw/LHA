"""Presentation only: retain raw state and expose exact retrieval paths."""

from __future__ import annotations

import copy
import json

from critic_harness.one_shot import PROTOCOL as CREATIVE_REVIEW_PROTOCOL


def video_brief(video):
    return {
        key: video[key]
        for key in (
            "parent",
            "duration_seconds",
            "fps",
            "frames",
            "width",
            "height",
            "imported",
            "replay_provenance",
        )
        if key in video
    }


def feedback_summary(identity, value):
    """Older online feedback is quoted, never rejudged or ranked."""
    if value.get("protocol") == CREATIVE_REVIEW_PROTOCOL:
        return {
            "video_id": value["video_id"],
            "protocol": value["protocol"],
            "usage": value.get("usage"),
            "summary": value["report"]["summary"],
            "open": {"action": "history", "arguments": {"feedback": identity}},
        }
    outcome, feedback = value.get("outcome", {}), value.get("feedback", {})
    return {
        "video_id": value.get("video_id", value.get("candidate")),
        "protocol": value["protocol"],
        "usage": value.get("usage"),
        "question": value.get("question", ""),
        "identity_map": copy.deepcopy(value.get("identity_map", {})),
        "view": "Earlier feedback summary; detailed findings remain available through history.",
        "summary": feedback.get("summary", outcome.get("summary", "")),
        "unresolved": copy.deepcopy(outcome.get("unresolved", [])),
        "unknown_findings": [
            copy.deepcopy(f) for f in outcome.get("findings", []) if f.get("verdict") == "unknown"
        ],
        "comparison_unknowns": [
            {"against": c.get("against"), "unknowns": copy.deepcopy(c["unknowns"])}
            for c in outcome.get("comparisons", [])
            if c.get("unknowns")
        ],
        "open": {"action": "history", "arguments": {"feedback": identity}},
    }


def present(payload, state, knowledge):
    """Compact a copied legacy payload without modifying evidence or raw history."""
    payload["task"] = {**payload["task"], "source": video_brief(payload["task"]["source"])}
    payload["videos"] = {
        identity: {**video_brief(video), "open": {"action": "video", "arguments": {"id": identity}}}
        for identity, video in state.get("videos", {}).items()
    }
    evaluations = state.get("evaluations", {})
    latest = next(reversed(evaluations), None)
    payload["evaluations"] = {
        identity: feedback_summary(identity, value)
        if identity != latest
        and value.get("protocol")
        in {"lha-online-critic-v1", "lha-online-critic-rsi-v1", CREATIVE_REVIEW_PROTOCOL}
        else copy.deepcopy(value)
        for identity, value in evaluations.items()
    }
    if state["config"].get("workflow") == "creative_loop_v1":
        from .candidate_view import candidate
        payload["videos"] = {identity: candidate(state, identity, review=False) for identity in state["videos"]}
        for identity, feedback in payload["evaluations"].items():
            if "observations" in feedback:
                feedback["observation_archive"] = {
                    "count": len(feedback.pop("observations")),
                    "open": {"action": "history", "arguments": {"feedback": identity}},
                }
            if "evidence" in feedback:
                # Keep full findings and coverage visible; native-frame receipts live in the archive.
                feedback["evidence_archive"] = {
                    "frames": len(feedback.pop("evidence")),
                    "open": {"action": "history", "arguments": {"feedback": identity}},
                }
    for event in payload["recent_operations"]:
        result = event.get("result", {})
        if (
            event.get("request", {}).get("action") == "tool_result"
            and result.get("status") == "complete"
        ):
            identity = result.get("video_id")
            if (
                identity in state.get("videos", {})
                and result.get("video") == state["videos"][identity]
            ):
                result["video"] = {"id": identity, "context_location": "videos." + identity}
            reference = result.get("payload_reference")
            if reference and reference.get("key") in payload["evaluations"]:
                reference["note"] = (
                    "See evaluations; older online reviews have an explicit history link for all findings."
                )
    if not state.get("workspace", {}).get("summary") and not state.get("workspace", {}).get(
        "nodes"
    ):
        payload.pop("workspace", None)
    payload["knowledge_entrances"] = knowledge.overview()
    payload["available_observations"] = [
        {
            "id": o["observation_id"],
            "video": o.get("video_id", "source"),
            "interval": o.get("requested_interval"),
            "mode": o.get("mode", "sampled"),
            "coverage": o.get("coverage"),
            "next_arguments": o.get("next_arguments"),
            "crop": o["frames"][0].get("crop") if o.get("frames") else None,
        }
        for o in state.get("observations", [])
    ]
    if state["config"].get("workflow") == "creative_loop_v1":
        from .continuation import view as continuation_view

        payload["continuation"] = continuation_view(state)
        payload.pop("resource_status", None)
        execution = state["config"]["execution"]
        renderer = execution.get("renderer", {})
        # Explicit operational projection: never dump operator limits or pressure settings.
        payload["execution_profile"] = {
            k: copy.deepcopy(execution[k])
            for k in ("mode", "experience_mode", "seed_sequence", "task_track")
            if k in execution
        }
        payload["execution_profile"]["renderer"] = {
            k: copy.deepcopy(renderer[k]) for k in ("backend", "seed", "output") if k in renderer
        }
        payload["execution_profile"]["renderer"]["generation"] = {
            k: copy.deepcopy(v)
            for k, v in renderer.get("generation", {}).items()
            if k
            in {
                "num_inference_steps",
                "guidance_mode",
                "max_image_size",
                "negative_prompt",
                "prompt_enhancer",
            }
        }
        payload["workflow"] = "creative_loop_v1"
        payload["delivery_candidate"] = state.get("delivery_candidate")
        mode = execution["review"]["mode"]
        payload["execution_profile"]["review"] = {
            "mode": mode,
            "guide": {"action": "read", "arguments": {"targets": [{"id": "review"}]}},
            "use": "Every generated result is checked. Critic mode returns descriptive evidence; Planner mode includes review beside the next action. Choose delivery yourself.",
        }
        payload["reviews"] = {}
        for identity, review in state.get("reviews", {}).items():
            summary = (review.get("report") or {}).get("summary", "")
            payload["reviews"][identity] = {
                "mode": review["mode"],
                "status": review["status"],
                "summary_excerpt": summary[:240],
                "summary_is_complete": len(summary) <= 240,
                "open": {"action": "history", "arguments": {"review": identity}},
            }
        payload["pending_review"] = copy.deepcopy(state.get("pending_review"))
        from .delivery_review import context as delivery_context

        payload["delivery_review"] = delivery_context(state)
        for identity, value in payload["evaluations"].items():
            if value.get("protocol") != CREATIVE_REVIEW_PROTOCOL:
                raise ValueError("Non-creative evaluation in creative-loop context")
            # Keep the full report; media transport paths stay in the retrievable record.
            if "evidence" in value:
                value["evidence"] = [
                    {k: e[k] for k in ("id", "video_id", "timestamp_seconds", "kind")}
                    for e in value["evidence"]
                ]
            value["open"] = {"action": "history", "arguments": {"feedback": identity}}
        creative_view(payload, state)
    payload["context_policy"] = (
        "Original task, optional notes and latest review remain available. Earlier online reviews are attributed summaries "
        "with unknowns and history links; raw findings are unchanged. Video provenance opens through video. "
        "Creative tasks show the newest result and compact prior operations with explicit archive access. "
        "Source overview and the latest observation group are attached; observe can reopen saved observations. "
        "Same video times do not establish motion alignment."
    )
    return payload


def creative_view(payload, state):
    """A bounded working view; archive bytes and model-owned notes stay untouched."""
    events = state.get("events", [])
    recent = payload["recent_operations"]
    for event in recent[:-1]:
        event_id = event["event_id"]
        request = event.get("request", {})
        event.clear()
        event.update(
            event_id=event_id,
            action=request.get("action"),
            open={"action": "history", "arguments": {"event_id": event_id}},
        )
    payload["read_receipts"] = {
        "count": len(state["reads"]),
        "open": {"action": "history", "arguments": {"catalog": "reads"}},
    }
    payload["archived_operation_index"] = {
        "count": max(0, len(events) - len(recent)),
        "open": {"action": "history", "arguments": {"catalog": "events"}},
    }
    latest = next(reversed(state.get("evaluations", {})), None)
    for key, value in list(payload["evaluations"].items()):
        if key == latest:
            continue
        value = state["evaluations"][key]
        payload["evaluations"][key] = {
            "video_id": value["video_id"],
            "summary": value["report"]["summary"],
            "open": {"action": "history", "arguments": {"feedback": key}},
            "view": "Earlier review; original findings remain available.",
        }
    # Keep the just-returned result within its share of the context budget. The
    # exact result is retrievable by event ID, with explicit pagination.
    if recent:
        newest = recent[-1]
        result = newest.get("result", {})
        if newest.get("request", {}).get("action") == "observe":
            newest["result"] = result = observation_view(result)
        limit = max(2048, state["config"]["max_context_chars"] // 4)
        if "materials" not in result and len(json.dumps(result, ensure_ascii=False)) > limit:
            from .common import page

            newest["result"] = {
                "view": "First page of a large result; omitted content has not been supplied.",
                "page": page(
                    json.dumps(result, ensure_ascii=False, indent=2),
                    max_chars=min(limit // 2, 12000),
                    split_long_lines=True,
                ),
                "open": {
                    "action": "history",
                    "arguments": {"event_id": newest["event_id"], "result_only": True},
                },
            }
    payload["history_catalogs"] = ["events", "reads", "observations", "evaluations", "videos"]


def observation_view(value):
    """Strip frame transport metadata; retain sampling, coverage and navigation."""
    if isinstance(value, list):
        return [observation_view(v) for v in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key == "frames":
            result[key] = [{k: f[k] for k in ("frame_index", "timestamp_seconds", "crop") if k in f} for f in item]
        elif key not in {"path", "sha256"}:
            result[key] = observation_view(item)
    return result


def fit_creative(payload, state, system_chars):
    """Remove older view entries, never the latest report/task/notes or raw data."""
    limit = state["config"]["max_context_chars"]
    payload["archive_access"] = {
        "note": "Older view entries may be omitted to fit capacity; exact records remain available.",
        "counts": {
            "videos": len(state["videos"]),
            "evaluations": len(state["evaluations"]),
            "observations": len(state["observations"]),
            "events": len(state["events"]),
        },
        "open": {"action": "history", "arguments": {"catalog": "events"}},
    }

    def fits():
        return system_chars + len(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))) <= limit

    if not fits():
        # Transport hashes/paths and directory inventories are already saved in
        # the call and source receipts. Spend scarce input space on read content.
        payload["attached_images_in_order"] = [
            {k: frame[k] for k in ("attachment", "id", "video_id", "observation_id",
                                   "frame_index", "timestamp_seconds", "crop", "kind") if k in frame}
            for frame in payload.get("attached_images_in_order", [])
        ]
        navigation = payload.get("knowledge_entrances", {})
        if "entrances" in navigation:
            navigation["entrances"] = [
                {k: row[k] for k in ("id", "title") if k in row}
                for row in navigation["entrances"]
            ]
        payload["read_receipts"] = {
            "count": len(state["reads"]),
            "open": {"action": "history", "arguments": {"catalog": "reads"}},
        }
        if not payload.get("working_memory", {}).get("retained_reads"):
            payload.pop("working_memory", None)

    for field in ("recent_operations", "available_observations"):
        while not fits() and len(payload.get(field, [])) > 1:
            payload[field].pop(0)
    evaluations = payload.get("evaluations", {})
    while not fits() and len(evaluations) > 1:
        del evaluations[next(iter(evaluations))]
    videos = payload.get("videos", {})
    protected = {"source", state.get("delivery_candidate"), state.get("final", {}).get("video")}
    if videos:
        protected.add(next(reversed(videos)))
    for key in list(videos):
        if fits():
            break
        if key not in protected:
            del videos[key]
    reviews = payload.get("reviews", {})
    while not fits() and len(reviews) > 1:
        del reviews[next(iter(reviews))]
    # Oversized current records are exact pages, never invented summaries.
    for identity, value in list(payload.get("evaluations", {}).items()):
        if fits():
            break
        text = json.dumps(state["evaluations"][identity], ensure_ascii=False, indent=2)
        from .common import page

        payload["evaluations"][identity] = {
            "video_id": state["evaluations"][identity]["video_id"],
            "view": "Exact first page; remaining findings are available through history.",
            "page": page(text, max_chars=2048, split_long_lines=True),
            "open": {"action": "history", "arguments": {"feedback": identity}},
        }
    if not fits() and payload.get("recent_operations"):
        newest = payload["recent_operations"][-1]
        payload["recent_operations"] = [
            {
                "event_id": newest["event_id"],
                "open": {"action": "history", "arguments": {"event_id": newest["event_id"]}},
            }
        ]
    if not fits():
        # At tight capacity, directory descriptions duplicate the system reading
        # guide. Keep the browse entrance and spend the space on actual reading.
        payload["knowledge_entrances"] = {"open": {"action": "browse", "arguments": {"id": "map"}}}
        payload["context_policy"] = "Exact records and complete read pages remain available through history; visible pages are shortened only to fit capacity."
    if not fits():
        from .working_memory import fit_display

        fit_display(payload, limit, system_chars)
    return payload


def fit_multimodal(payload, state, system, images, mapping):
    from .working_memory import POLICY

    # Bound image load as part of the same capacity, retaining evenly spaced
    # evidence from each selected group. Exact saved observations can be reopened.
    text_reserve = min(
        state["config"]["max_context_chars"],
        max(24000, len(system) + len(json.dumps(payload.get("task", {}))) + 12000),
    )
    max_images = max(
        0,
        (POLICY["max_input_tokens"] - POLICY["reserve_tokens"] - (text_reserve + 2) // 3)
        // POLICY["image_tokens"],
    )
    if len(images) > max_images:
        indices = sorted(
            {round(i * (len(images) - 1) / max(1, max_images - 1)) for i in range(max_images)}
        )
        images = [images[i] for i in indices]
        mapping = [{**mapping[i], "attachment": n + 1} for n, i in enumerate(indices)]
        payload["attachment_pagination"] = {
            "supplied": len(images),
            "available": len(payload["attached_images_in_order"]),
            "scope": "Evenly spaced subset for this input capacity; reopen saved observations or request smaller intervals for the omitted evidence.",
        }
    payload["attached_images_in_order"] = [
        {k: frame[k] for k in ("attachment", "id", "video_id", "observation_id", "frame_index", "timestamp_seconds", "crop", "kind") if k in frame}
        for frame in mapping
    ]
    available_chars = max(
        8192,
        3
        * (
            POLICY["max_input_tokens"]
            - POLICY["reserve_tokens"]
            - len(images) * POLICY["image_tokens"]
        ),
    )
    working = copy.deepcopy(state)
    working["config"]["max_context_chars"] = min(
        state["config"]["max_context_chars"], available_chars
    )
    return fit_creative(payload, working, len(system)), images, mapping


def history_catalog(state, name):
    if name == "reads":
        return state["reads"]
    if name == "events":
        return [
            {
                "event_id": e["event_id"],
                "action": e.get("request", {}).get("action"),
                "status": e["status"],
                "open": {"action": "history", "arguments": {"event_id": e["event_id"]}},
            }
            for e in state["events"]
        ]
    if name == "videos":
        return {
            k: {**video_brief(v), "open": {"action": "video", "arguments": {"id": k}}}
            for k, v in state["videos"].items()
        }
    if name == "observations":
        return [
            {
                "id": o["observation_id"],
                "video": o.get("video_id", "source"),
                "interval": o.get("requested_interval"),
                "open": {"action": "observe", "arguments": {"observation": o["observation_id"]}},
            }
            for o in state["observations"]
        ]
    if name == "evaluations":
        return {k: feedback_summary(k, v) for k, v in state["evaluations"].items()}
    raise ValueError("Choose events, reads, videos, observations or evaluations")


def attachments(state):
    observations = state.get("observations", [])
    focus = state.get("observation_focus", {})
    lookup = {o["observation_id"]: o for o in observations}
    if focus.get("observations_count") == len(observations) and all(
        i in lookup for i in focus.get("ids", [])
    ):
        selected = observations[:1] + [lookup[i] for i in focus.get("ids", [])]
    else:
        selected = observations[:1] + observations[-1:]
    images, mapping = [], []
    for observation in selected:
        for frame in observation["frames"]:
            if frame["path"] not in images:
                images.append(frame["path"])
                mapping.append(
                    {
                        "attachment": len(images),
                        "observation_id": observation["observation_id"],
                        "video_id": observation.get("video_id", "source"),
                        **frame,
                    }
                )
    references = state.get(
        "reference_images", [state["reference_image"]] if state.get("reference_image") else []
    )
    for reference in references:
        if reference["path"] not in images:
            images.append(reference["path"])
            mapping.append(
                {
                    "attachment": len(images),
                    "kind": "knowledge reference, not source-video evidence",
                    **reference,
                }
            )
    return images, mapping


def base_context(self):
    events = self.state["events"]
    # Complete logs stay on disk. The archive index makes context selection explicit.
    recent = copy.deepcopy(events[-10:])
    evaluations = self.state.get("evaluations", {})
    for event in recent:
        request = event.get("request", {})
        job_id = request.get("arguments", {}).get("job_id")
        result = event.get("result", {})
        evaluation = evaluations.get(job_id)
        if (
            request.get("action") == "tool_result"
            and result.get("status") == "complete"
            and evaluation is not None
        ):
            payload = result.get("payload")
            # Inline every evaluation once, without shortening any finding.
            # Only exact duplicates are replaced; unusual responses stay whole.
            if isinstance(payload, dict) and evaluation == {
                "video_id": evaluation.get("video_id"),
                **payload,
            }:
                result.pop("payload")
                result["payload_reference"] = {
                    "context_field": "evaluations",
                    "key": job_id,
                    "note": "The complete returned payload is present there; video_id is added by collection.",
                }
    archived = [
        {
            "event_id": e["event_id"],
            "action": e.get("request", {}).get("action"),
            "purpose": e.get("request", {}).get("purpose"),
            "result_status": e["status"],
            "restore": {"action": "history", "arguments": {"event_id": e["event_id"]}},
        }
        for e in events[:-10]
    ]
    observations = self.state["observations"]
    selected = observations[:1] + observations[-1:] if len(observations) > 1 else observations
    images, mapping = [], []
    for observation in selected:
        for frame in observation["frames"]:
            if frame["path"] not in images:
                images.append(frame["path"])
                mapping.append(
                    {
                        "attachment": len(images),
                        "observation_id": observation["observation_id"],
                        **frame,
                    }
                )
    for reference in self.state.get(
        "reference_images",
        [self.state["reference_image"]] if self.state.get("reference_image") else [],
    ):
        images.append(reference["path"])
        mapping.append(
            {
                "attachment": len(images),
                "kind": "knowledge reference, not source-video evidence",
                **reference,
            }
        )
    payload = {
        "task": self.state["request"],
        "workspace": self.state["workspace"],
        "mode": self.state["config"].get("mode", "plan"),
        "notes": self.state.get("notes", ""),
        "videos": {
            k: {key: value for key, value in v.items() if key not in {"execution"}}
            for k, v in self.state.get("videos", {}).items()
        },
        "evaluations": evaluations,
        "execution_profile": {
            key: (
                {k: v for k, v in value.items() if k != "card_data"}
                if key == "evaluation"
                else value
            )
            for key, value in self.state["config"].get("execution", {}).items()
        },
        "knowledge_entrances": self.knowledge.browse(),
        "read_receipts": self.state["reads"],
        "attached_images_in_order": mapping,
        "recent_operations": recent,
        "archived_operation_index": archived,
        "context_policy": "Latest 10 operation results are present. Exact duplicate evaluation payloads reference the complete evaluations entry in this same context; no feedback is shortened. Older results can be restored with history. Initial overview and latest observation images are attached. All original exchanges are retained on disk.",
        "resource_status": {
            "turns_used": self.state["attempts"],
            "turn_limit": self.state["config"]["max_turns"],
            "generation_requests": self.state.get("generation_requests", 0),
            "generation_limit": self.state["config"].get("max_generations"),
            "completion_mode": self.state["config"].get("completion_mode", "bounded_experiment"),
            "limit_meaning": "A null limit has no fixed count. In delivery mode, resource exhaustion leaves the task incomplete.",
        },
    }
    if self.state["config"].get("run_instructions"):
        payload["run_instructions"] = self.state["config"]["run_instructions"]
    video_labels = {o["observation_id"]: o.get("video_id", "source") for o in observations}
    for item in mapping:
        if "observation_id" in item:
            item["video_id"] = video_labels[item["observation_id"]]
    return json.dumps(payload, ensure_ascii=False, indent=2), images, mapping
