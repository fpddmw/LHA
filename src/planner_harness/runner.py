from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from .common import ROOT, load, page, save, sha, stamp
from .knowledge import Knowledge
from .video import Video


class PlannerHarness:
    def __init__(self, output, model, *, root=ROOT):
        self.output = Path(output).resolve()
        self.model = model
        self.root = Path(root).resolve()
        self.knowledge = Knowledge(root)
        self.state = None
        self.video = None

    def checkpoint(self):
        self.state["updated_at"] = stamp()
        save(self.output / "state.json", self.state)

    def start(self, source, request, *, target="unspecified", max_turns=None, max_context_chars=180000, label="",
              mode="plan", execution=None, max_generations=None, imported=None, feedback_files=None,
              run_instructions="", rsi=None, completion_mode=None):
        if (self.output / "state.json").exists():
            raise ValueError("Run already exists. Use resume or a new output directory.")
        if mode not in {"plan", "loop"}:
            raise ValueError("Use plan/loop mode")
        from .delivery import completion_mode as resolve_completion_mode
        completion_mode = resolve_completion_mode(max_generations, completion_mode)
        if mode == "plan" and max_turns is None:
            max_turns = 24
        if max_turns is not None and (type(max_turns) is not int or max_turns < 0):
            raise ValueError("Turn limit must be a nonnegative integer or null")
        if not isinstance(run_instructions, str):
            raise ValueError("Run instructions must be plain text")
        self.video = Video(source, self.output)
        self.state = {
            "schema_version": 1, "status": "running", "created_at": stamp(), "label": label,
            "request": {"text": request, "source": self.video.info, "target_model": target},
            "config": {"max_turns": max_turns, "max_context_chars": max_context_chars, "context_version": 2,
                       "mode": mode, "execution": execution or {}, "max_generations": max_generations,
                       "completion_mode": completion_mode,
                       "run_instructions": run_instructions,
                       "backend": type(self.model).__name__, "model": getattr(self.model, "model", "unknown"),
                       "reasoning_effort": getattr(self.model, "reasoning_effort", "unknown")},
            "knowledge_manifest_sha256": sha(self.root / "knowledge/source-map.json"),
            "runtime_sources": {p.name: sha(p) for p in Path(__file__).parent.iterdir() if p.suffix in {".py", ".md"}},
            "workspace": {"summary": "", "nodes": {}}, "events": [], "reads": {},
            "observations": [], "attempts": 0, "submission_attempts": [], "pending_event": None,
            "notes": "", "videos": {"source": self.video.info}, "jobs": {}, "evaluations": {},
            "generation_requests": 0, "pending_tool": None,
            "renderer_submission": {"status": "not_requested", "reason": "No generation requested yet." if mode == "loop" else "Planner-only validation; no generation operation is available."},
        }
        self.output.mkdir(parents=True, exist_ok=True)
        from .execution import prepare_profile
        self.state["config"]["execution"] = prepare_profile(execution, self.root, self.state["request"])
        if rsi is not None and rsi is not False:
            if mode != "loop":
                raise ValueError("RSI is enabled only for continuous loop tasks")
            from .rsi_support import configure
            configure(self, rsi)
        self.knowledge.freeze(self.output / "knowledge-snapshot.json")
        self.state["knowledge_snapshot_sha256"] = sha(self.output / "knowledge-snapshot.json")
        operations = (Path(__file__).parent / "OPERATIONS.md").read_text(encoding="utf-8")
        manual = (self.root / "knowledge/READING.md").read_text(encoding="utf-8")
        self.system = operations + "\n\n# Current knowledge reading manual\n\n" + manual
        if self.state["config"]["execution"].get("critic") or feedback_files:
            from critic_harness.adapter import PLANNER_MANUAL
            self.system += "\n\n" + PLANNER_MANUAL
        if self.state["config"].get("rsi"):
            self.system += "\n\n" + (Path(__file__).parent / "RSI.md").read_text(encoding="utf-8")
        (self.output / "system-prompt.txt").write_text(self.system, encoding="utf-8")
        self.state["system_prompt_sha256"] = sha(self.output / "system-prompt.txt")
        overview = self.video.observe("overview")
        overview["video_id"] = "source"
        self.state["observations"].append(overview)
        for index, item in enumerate(imported or []):
            identity = f"prior{index + 1}"
            if not item.get("provenance"):
                raise ValueError("Imported videos need truthful provenance")
            video = Video(item["path"], self.output)
            if item.get("parent") and item["parent"] not in self.state["videos"]:
                raise ValueError("Import actual parents before their children")
            if item.get("sha256", video.info["sha256"]) != video.info["sha256"]:
                raise ValueError("Imported video hash mismatch")
            self.state["videos"][identity] = {**video.info, "imported": True, "provenance": item["provenance"],
                **{k: item[k] for k in ("parent", "prompt", "time_mapping") if k in item}}
            observation = video.observe("import-" + identity)
            observation.update(video_id=identity, scope="Imported historical result; not generated by this run.")
            self.state["observations"].append(observation)
        for path in feedback_files or []:
            from critic_harness.runner import load_feedback
            feedback = load_feedback(path, request, self.state["videos"])
            self.state["evaluations"]["imported-critic-" + str(len(self.state["evaluations"]) + 1)] = feedback
        self.checkpoint()
        return self.run()

    def resume(self, *, additional_turns=0, execution=None, continue_delivery=False):
        self.state = load(self.output / "state.json")
        from .task_criteria import verify_state
        verify_state(self.state)
        if self.state["status"] == "complete" and not continue_delivery:
            return self.state
        config = self.state["config"]
        if getattr(self.model, "model", "unknown") != config["model"] or getattr(self.model, "reasoning_effort", "unknown") != config["reasoning_effort"] or type(self.model).__name__ != config["backend"]:
            raise ValueError("Resume must use the recorded backend, model and reasoning effort")
        self.video = Video(self.state["request"]["source"]["path"], self.output)
        if self.video.info["sha256"] != self.state["request"]["source"]["sha256"]:
            raise ValueError("Source video changed; use a new run")
        if self.state.get("knowledge_snapshot_sha256"):
            if sha(self.output / "knowledge-snapshot.json") != self.state["knowledge_snapshot_sha256"]:
                raise ValueError("Run knowledge snapshot changed")
            self.knowledge = Knowledge(self.root, self.output / "knowledge-snapshot.json")
        elif sha(self.root / "knowledge/source-map.json") != self.state["knowledge_manifest_sha256"]:
            raise ValueError("Knowledge manifest changed; use a new run")
        if sha(self.output / "system-prompt.txt") != self.state["system_prompt_sha256"]:
            raise ValueError("Recorded operating instructions changed")
        self.system = (self.output / "system-prompt.txt").read_text(encoding="utf-8")
        if execution is not None:
            from .execution import prepare_profile
            profile = prepare_profile(execution, self.root, self.state["request"])
            if profile != config.get("execution"):
                if config.get("rsi"):
                    raise ValueError("RSI execution profiles are frozen; start a new run to change them")
                event = {"event_id": "runtime-config-" + str(len(self.state["events"]) + 1), "at": stamp(), "status": "ok",
                         "request": {"action": "configure_execution", "origin": "operator CLI"},
                         "result": {"previous": config.get("execution"), "next": profile,
                                    "scope": "Future tool requests; outstanding signed jobs are unchanged."}}
                self.state["events"].append(event)
                save(self.output / "events" / (event["event_id"] + ".json"), event)
                config["execution"] = profile
        if continue_delivery:
            if (self.output / "validation-binding.json").exists():
                raise ValueError("Keep a frozen validation run unchanged")
            from .delivery import continue_budget_stop
            continue_budget_stop(self.state)
            self.state["delivery_continuations"][-1].update(at=stamp(), runtime_sources={
                p.name: sha(p) for p in Path(__file__).parent.iterdir() if p.suffix in {".py", ".md"}})
        if self.state["config"]["max_turns"] is not None:
            self.state["config"]["max_turns"] += max(0, int(additional_turns))
        if self.state.get("final") and self.state["status"] != "complete":
            self.state.setdefault("interruption_history", []).append(self.state.pop("final"))
            save(self.output / "interruptions" / f"{len(self.state['interruption_history']):04d}.json", self.state["interruption_history"][-1])
            (self.output / "final.json").unlink(missing_ok=True)
        self.state["status"] = "running"
        self.checkpoint()
        return self.run()

    def context(self):
        text, images, mapping = self._legacy_context()
        if self.state["config"].get("context_version", 1) < 2:
            return text, images, mapping
        from .context import attachments, present
        payload = present(json.loads(text), self.state, self.knowledge)
        images, mapping = attachments(self.state)
        payload["attached_images_in_order"] = mapping
        if self.state["config"].get("rsi"):
            from .rsi_support import context
            payload = context(self, payload)
        return json.dumps(payload, ensure_ascii=False, indent=2), images, mapping

    def _legacy_context(self):
        events = self.state["events"]
        # Complete logs stay on disk. The archive index makes context selection explicit.
        recent = copy.deepcopy(events[-10:])
        evaluations = self.state.get("evaluations", {})
        for event in recent:
            request = event.get("request", {})
            job_id = request.get("arguments", {}).get("job_id")
            result = event.get("result", {})
            evaluation = evaluations.get(job_id)
            if request.get("action") == "tool_result" and result.get("status") == "complete" and evaluation is not None:
                payload = result.get("payload")
                # Inline every evaluation once, without shortening any finding.
                # Only exact duplicates are replaced; unusual responses stay whole.
                if isinstance(payload, dict) and evaluation == {"video_id": evaluation.get("video_id"), **payload}:
                    result.pop("payload")
                    result["payload_reference"] = {"context_field": "evaluations", "key": job_id,
                        "note": "The complete returned payload is present there; video_id is added by collection."}
        archived = [{"event_id": e["event_id"], "action": e.get("request", {}).get("action"),
                     "purpose": e.get("request", {}).get("purpose"), "result_status": e["status"],
                     "restore": {"action": "history", "arguments": {"event_id": e["event_id"]}}} for e in events[:-10]]
        observations = self.state["observations"]
        selected = observations[:1] + observations[-1:] if len(observations) > 1 else observations
        images, mapping = [], []
        for observation in selected:
            for frame in observation["frames"]:
                if frame["path"] not in images:
                    images.append(frame["path"])
                    mapping.append({"attachment": len(images), "observation_id": observation["observation_id"], **frame})
        for reference in self.state.get("reference_images", [self.state["reference_image"]] if self.state.get("reference_image") else []):
            images.append(reference["path"])
            mapping.append({"attachment": len(images), "kind": "knowledge reference, not source-video evidence", **reference})
        payload = {"task": self.state["request"], "workspace": self.state["workspace"],
                   "mode": self.state["config"].get("mode", "plan"), "notes": self.state.get("notes", ""),
                   "videos": {k: {key: value for key, value in v.items() if key not in {"execution"}}
                              for k, v in self.state.get("videos", {}).items()},
                   "evaluations": evaluations,
                   "execution_profile": {key: ({k: v for k, v in value.items() if k != "card_data"} if key == "evaluation" else value)
                                         for key, value in self.state["config"].get("execution", {}).items()},
                   "knowledge_entrances": self.knowledge.browse(), "read_receipts": self.state["reads"],
                   "attached_images_in_order": mapping, "recent_operations": recent,
                   "archived_operation_index": archived,
                   "context_policy": "Latest 10 operation results are present. Exact duplicate evaluation payloads reference the complete evaluations entry in this same context; no feedback is shortened. Older results can be restored with history. Initial overview and latest observation images are attached. All original exchanges are retained on disk.",
                   "resource_status": {"turns_used": self.state["attempts"], "turn_limit": self.state["config"]["max_turns"],
                                       "generation_requests": self.state.get("generation_requests", 0),
                                       "generation_limit": self.state["config"].get("max_generations"),
                                       "completion_mode": self.state["config"].get("completion_mode", "bounded_experiment"),
                                       "limit_meaning": "A null limit has no fixed count. In delivery mode, resource exhaustion leaves the task incomplete."}}
        if self.state["config"].get("run_instructions"):
            payload["run_instructions"] = self.state["config"]["run_instructions"]
        video_labels = {o["observation_id"]: o.get("video_id", "source") for o in observations}
        for item in mapping:
            if "observation_id" in item:
                item["video_id"] = video_labels[item["observation_id"]]
        return json.dumps(payload, ensure_ascii=False, indent=2), images, mapping

    def update_workspace(self, update):
        if not isinstance(update, dict):
            raise ValueError("workspace must be an object")
        new = copy.deepcopy(self.state["workspace"])
        if "summary" in update:
            if not isinstance(update["summary"], str):
                raise ValueError("workspace.summary must be text")
            new["summary"] = update["summary"]
        for node in update.get("nodes", []):
            if not isinstance(node, dict) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", str(node.get("id", ""))):
                raise ValueError("Node IDs must be short stable identifiers")
            new["nodes"][node["id"]] = {**new["nodes"].get(node["id"], {}), **node}
        for identity in update.get("remove_nodes", []):
            new["nodes"].pop(identity, None)
        for identity, node in new["nodes"].items():
            parent = node.get("parent")
            if parent and parent not in new["nodes"]:
                raise ValueError(f"Unknown parent: {parent}")
            visited = {identity}
            while parent:
                if parent in visited:
                    raise ValueError("Workspace parent cycle; use links for cross-references")
                visited.add(parent)
                parent = new["nodes"][parent].get("parent")
            if any(link not in new["nodes"] for link in node.get("links", [])):
                raise ValueError("Workspace links must name existing nodes")
        if re.search(r"[\u3400-\u9fff]", json.dumps(new, ensure_ascii=False)):
            raise ValueError("Use English for working notes")
        self.state["workspace"] = new

    def operate(self, response, event_id):
        action, args = response.get("action", response.get("tool")), response.get("arguments", {})
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        if "note" in response:
            self.remember(response["note"])
        if "workspace" in response:
            self.update_workspace(response["workspace"])
        if action == "browse":
            return self.knowledge.browse(args.get("id", "map"))
        if action == "search":
            return self.knowledge.search(args["query"], args.get("limit", 8))
        if action == "read":
            targets = args.get("targets", [])
            if not isinstance(targets, list) or not 1 <= len(targets) <= 4:
                raise ValueError("read accepts 1 to 4 targets")
            results = []
            for target in targets:
                try:
                    result = self.knowledge.read(target["id"], target.get("start_line", 1), target.get("section"))
                    read_id = f"read-{len(self.state['reads']) + 1:04d}"
                    result["read_id"] = read_id
                    self.state["reads"][read_id] = {k: result[k] for k in ("id", "path", "sha256", "start_line", "end_line", "next_line")}
                    self.state["reads"][read_id]["event_id"] = event_id
                    results.append(result)
                except (ValueError, KeyError, OSError) as exc:
                    results.append({"target": target, "error": str(exc)})
            return {"materials": results}
        if action == "observe":
            return self.observe(args, event_id)
        if action == "view_reference":
            references = self.knowledge.references(args["id"])
            self.state["reference_images"] = references
            self.state["reference_image"] = references[-1]
            return references[0] if len(references) == 1 else {"images": references}
        if action == "workspace":
            return {"saved": True, "workspace": self.state["workspace"]}
        if action == "note":
            self.remember(args.get("text", ""), append=args.get("append", True))
            return {"saved": True}
        if action == "lesson":
            self.remember(args.get("text", ""), append=args.get("append", True))
            return {"saved": True, "scope": "Optional task-local working judgment"}
        if action == "requirements":
            if not self.state["config"].get("rsi"):
                raise ValueError("Requirements operation needs an RSI run")
            from .ledger import set_requirements
            return set_requirements(self.state, args.get("items"), args.get("reason", ""))
        if action == "video":
            identity = args.get("id", "source")
            if identity not in self.state.get("videos", {}):
                raise ValueError("Unknown video ID")
            return self.state["videos"][identity]
        if action == "criteria_objection":
            from .task_criteria import objection
            return objection(self.state, args.get("text"), args.get("evidence"))
        if action == "delivery_candidate":
            identity = args.get("id", "source")
            if identity not in self.state.get("videos", {}):
                raise ValueError("Unknown video ID")
            self.state["delivery_candidate"] = identity
            return {"video": identity, "scope": "Current intended delivery; does not select render input or finish the task"}
        if action in {"generate", "evaluate", "critique"}:
            from .execution import request_job
            return request_job(self, action, args, event_id)
        if action == "finish":
            if self.state["config"].get("mode", "plan") != "loop":
                raise ValueError("Use submit with an English prompt to finish a planning-only run")
            identity = args.get("video")
            if identity is not None and identity not in self.state["videos"]:
                raise ValueError("Choose an existing video ID, or omit it when no result is ready")
            if re.search(r"[\u3400-\u9fff]", json.dumps(args, ensure_ascii=False)):
                raise ValueError("Use English for working output")
            reason = args.get("stop_reason", "satisfied" if identity not in {None, "source"} else "no_promising_attempt")
            extra = {"stop_reason": reason}
            if self.state["config"].get("rsi"):
                from .ledger import build
                if args.get("stop_reason") not in {"satisfied", "no_promising_attempt", "budget", "execution_failure"}:
                    raise ValueError("RSI finish needs stop_reason: satisfied/no_promising_attempt/budget/execution_failure")
                memory = build(self.state)
                rows = memory.get("candidates", {}).get(identity, {}).get("verdicts", {})
                unmet = [r["id"] for r in self.state.get("requirements", {}).get("items", []) if rows.get(r["id"], "unknown") != "pass"]
                extra = {"stop_reason": args["stop_reason"], "unmet": unmet,
                         "delivery_status": "budget_limited" if args["stop_reason"] == "budget" else
                            "execution_failed" if args["stop_reason"] == "execution_failure" else
                            "selected_with_unresolved_requirements" if unmet else "criteria_satisfied",
                         "added_requirement_suggestions": memory.get("candidates", {}).get(identity, {}).get("added_requirements", []),
                         "scope": "Planner stop reason; measured unresolved items are retained separately."}
            from .delivery import finish_status
            status = finish_status(self.state, reason, identity)
            self.state.update(status=status, final={"video": identity, "message": args.get("message", ""),
                                                       "outcome": "selected_video" if identity else "stopped_without_video", **extra})
            save(self.output / "final.json", self.state["final"])
            return self.state["final"]
        if action == "history":
            if "feedback" in args:
                if "event_id" in args:
                    raise ValueError("Choose feedback or event_id")
                feedback = self.state.get("evaluations", {}).get(args["feedback"])
                if feedback is None:
                    raise ValueError("Unknown feedback ID")
                return page(json.dumps(feedback, ensure_ascii=False, indent=2), args.get("start_line", 1))
            matches = [e for e in self.state["events"] if e["event_id"] == args.get("event_id")]
            if not matches:
                raise ValueError("Unknown event ID")
            return page(json.dumps(matches[0], ensure_ascii=False, indent=2), args.get("start_line", 1))
        if action == "submit":
            return self.submit(args)
        raise ValueError(f"Unknown operation: {action}")

    def remember(self, text, append=True):
        if not isinstance(text, str) or re.search(r"[\u3400-\u9fff]", text):
            raise ValueError("Write notes in English")
        self.state["notes"] = (self.state.get("notes", "") + "\n" + text).strip() if append else text

    def observe(self, arguments, event_id):
        args = dict(arguments)
        if "observation" in args:
            requested = args.pop("observation")
            if args:
                raise ValueError("Reopen an observation without changing its sampling arguments")
            ids = requested if isinstance(requested, list) else [requested]
            lookup = {o["observation_id"]: o for o in self.state["observations"]}
            if not 1 <= len(ids) <= 4 or any(not isinstance(i, str) or i not in lookup for i in ids):
                raise ValueError("Choose 1 to 4 recorded observation IDs")
            results = [lookup[i] for i in dict.fromkeys(ids)]
            for result in results:
                if any(sha(f["path"]) != f["sha256"] for f in result["frames"]):
                    raise ValueError("Recorded observation changed")
        else:
            requested = args.pop("video", args.pop("video_id", "source"))
            ids = requested if isinstance(requested, list) else [requested]
            videos = self.state.get("videos", {"source": self.video.info})
            if not 1 <= len(ids) <= 4 or any(not isinstance(i, str) or i not in videos for i in ids):
                raise ValueError("Choose 1 to 4 available video IDs")
            ids = list(dict.fromkeys(ids))
            for identity in ids:
                if sha(videos[identity]["path"]) != videos[identity]["sha256"]:
                    raise ValueError("Task video changed")
            results = []
            for index, identity in enumerate(ids):
                observation_id = event_id if len(ids) == 1 else f"{event_id}-{index + 1}"
                result = Video(videos[identity]["path"], self.output).observe(observation_id, **args)
                result.update(video_id=identity, scope="Sampled frames from " + identity + "; precise motion needs suitable temporal evidence.")
                results.append(result)
            self.state["observations"].extend(results)
        self.state["observation_focus"] = {"ids": [r["observation_id"] for r in results],
                                           "observations_count": len(self.state["observations"])}
        if len(results) == 1:
            return results[0]
        return {"observations": results,
                "scope": "Sampled comparisons at each video's own timestamps; matching times do not establish motion alignment."}

    def submit(self, proposal):
        proposal = {"understanding": "", "proposal": "", "self_review": "", "sources": [], "unresolved": [], **proposal}
        issues = []
        for field in ("prompt",):
            if not isinstance(proposal.get(field), str) or not proposal[field].strip():
                issues.append(f"Provide nonempty English {field}")
        if re.search(r"[\u3400-\u9fff]", json.dumps(proposal, ensure_ascii=False)):
            issues.append("Use English for the planning output")
        if not isinstance(proposal.get("sources"), list) or not isinstance(proposal.get("unresolved"), list):
            issues.append("sources and unresolved must be arrays")
        for citation in proposal.get("sources", []) if isinstance(proposal.get("sources"), list) else []:
            receipt = self.state["reads"].get(citation.get("read_id")) if isinstance(citation, dict) else None
            if not receipt or not isinstance(citation.get("use"), str) or not citation["use"].strip():
                issues.append("Citations need an actual returned read_id and a description of use")
            elif self.knowledge.read(receipt["id"])["sha256"] != receipt["sha256"]:
                issues.append(f"Cited source changed since reading: {receipt['path']}")
        version = len(self.state["submission_attempts"]) + 1
        result = {"version": version, "accepted": not issues, "issues": issues,
                  "renderer_preflight": "pending: no renderer tokenizer/configuration is loaded in this Planner-only run",
                  "renderer_submission": "not performed"}
        save(self.output / "proposals" / f"{version:03d}.json", {"proposal": proposal, "validation": result})
        self.state["submission_attempts"].append(result)
        if not issues:
            self.state["proposal"] = proposal
            self.state["status"] = "complete" if self.state["config"].get("mode", "plan") == "plan" else "running"
            save(self.output / "proposal.json", proposal)
            (self.output / "prompt.txt").write_text(proposal["prompt"], encoding="utf-8")
            save(self.output / "handoff.json", {"source": self.state["request"]["source"],
                 "target_model": self.state["request"]["target_model"], "prompt": proposal["prompt"],
                 "prompt_sha256": sha(self.output / "prompt.txt"), "validation": result})
        return result

    def run(self):
        from .report import report
        try:
            if self.state.get("pending_tool"):
                from .execution import collect
                if not collect(self):
                    self.state["status"] = "waiting_tool"
                    return self.state
            if self.state["config"].get("rsi"):
                from .rsi_support import auto_review
                if auto_review(self):
                    return self.state
            while self.state["status"] == "running" and (self.state.get("pending_event") or self.state["config"]["max_turns"] is None or self.state["attempts"] < self.state["config"]["max_turns"]):
                if self.state.get("pending_event"):
                    event_id = self.state["pending_event"]
                    call_dir = self.output / "calls" / event_id
                    saved = load(call_dir / "input.json")
                    user_text, mapping = saved["user_text"], saved["images"]
                    images = [item["path"] for item in mapping]
                    if saved["system_prompt"] != self.system or any(sha(item["path"]) != item["sha256"] for item in mapping):
                        raise ValueError("Pending call inputs changed")
                else:
                    user_text, images, mapping = self.context()
                    if len(self.system) + len(user_text) > self.state["config"]["max_context_chars"]:
                        self.state["status"] = "context_limit"
                        self.state["last_error"] = "Context exceeds the configured character budget; no text was silently truncated."
                        break
                    self.state["attempts"] += 1
                    event_id = f"event-{self.state['attempts']:04d}"
                    call_dir = self.output / "calls" / event_id
                    save(call_dir / "input.json", {"system_prompt": self.system, "user_text": user_text, "images": mapping, "created_at": stamp()})
                    if self.state["config"].get("rsi"):
                        save(call_dir / "decision-state.json", self.state)
                    self.state["pending_event"] = event_id
                    self.checkpoint()
                print(f"[{self.output.name}] {event_id}: model call, {len(images)} images", flush=True)
                raw_path = call_dir / "response.txt"
                try:
                    if raw_path.exists():
                        raw = raw_path.read_text(encoding="utf-8")
                    else:
                        if self.state["config"].get("rsi"):
                            from .rsi_calls import call_once
                            raw = call_once(call_dir, self.model, self.system, user_text, images)
                        else:
                            raw = self.model.predict_text(system_prompt=self.system, user_text=user_text, image_paths=images, max_new_tokens=7000)
                        raw_path.write_text(raw, encoding="utf-8")
                    # Strict response parsing keeps malformed actions visible for correction.
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        if raw.lstrip().startswith(("{", "[", "```")):
                            raise
                        parsed = {"action": "note", "arguments": {"text": raw}}
                    if not isinstance(parsed, dict):
                        raise ValueError("Response must be one JSON object")
                    event = {"event_id": event_id, "at": stamp(), "request": parsed, "status": "ok"}
                    try:
                        event["result"] = self.operate(parsed, event_id)
                    except (ValueError, KeyError, TypeError, OSError) as exc:
                        event.update(status="operation_error", result={"error": str(exc)})
                except (json.JSONDecodeError, ValueError) as exc:
                    event = {"event_id": event_id, "at": stamp(), "status": "response_error", "result": {"error": str(exc), "instruction": "Return a valid JSON operation envelope."}}
                self.state["events"].append(event)
                save(self.output / "events" / f"{event_id}.json", event)
                self.state["pending_event"] = None
                self.checkpoint()
                print(f"[{self.output.name}] {event_id}: {event.get('request', {}).get('action')} / {event['status']}", flush=True)
            if self.state["status"] == "running":
                self.state["status"] = "budget_exhausted"
        except KeyboardInterrupt:
            self.state["status"] = "interrupted"
            self.checkpoint()
            raise
        except Exception as exc:
            self.state["status"] = "transport_or_runtime_error"
            self.state["last_error"] = f"{type(exc).__name__}: {exc}"
            self.checkpoint()
            raise
        finally:
            self.checkpoint()
            report(self.output)
        return self.state
