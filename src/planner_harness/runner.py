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
        self.knowledge = None
        self.state = None
        self.video = None

    def checkpoint(self):
        self.state["updated_at"] = stamp()
        save(self.output / "state.json", self.state)

    def start(
        self,
        source,
        request,
        *,
        target="unspecified",
        max_turns=None,
        max_context_chars=180000,
        label="",
        mode="plan",
        execution=None,
        max_generations=None,
        imported=None,
        feedback_files=None,
        run_instructions="",
        rsi=None,
        completion_mode=None,
        workflow="legacy",
    ):
        if workflow not in {"legacy", "creative_loop_v1"}:
            raise ValueError("Unknown Planner workflow")
        if workflow == "creative_loop_v1":
            if rsi is not None and rsi is not False:
                raise ValueError("Creative loop cannot be mixed with RSI")
            if mode != "loop" or feedback_files:
                raise ValueError(
                    "Creative loop requires loop mode and excludes imported legacy feedback"
                )
        if (self.output / "state.json").exists():
            raise ValueError("Run already exists. Use resume or a new output directory.")
        if mode not in {"plan", "loop"}:
            raise ValueError("Use plan/loop mode")
        from .delivery import completion_mode as resolve_completion_mode

        if workflow == "creative_loop_v1" and completion_mode is None:
            completion_mode = "delivery"
        completion_mode = resolve_completion_mode(max_generations, completion_mode)
        if mode == "plan" and max_turns is None:
            max_turns = 24
        if max_turns is not None and (type(max_turns) is not int or max_turns < 0):
            raise ValueError("Turn limit must be a nonnegative integer or null")
        if not isinstance(run_instructions, str):
            raise ValueError("Run instructions must be plain text")
        self.video = Video(source, self.output)
        self.state = {
            "schema_version": 1,
            "status": "running",
            "created_at": stamp(),
            "label": label,
            "request": {"text": request, "source": self.video.info, "target_model": target},
            "config": {
                "max_turns": max_turns,
                "max_context_chars": max_context_chars,
                "context_version": 2,
                "mode": mode,
                "workflow": workflow,
                "execution": execution or {},
                "max_generations": max_generations,
                "completion_mode": completion_mode,
                "run_instructions": run_instructions,
                "backend": type(self.model).__name__,
                "model": getattr(self.model, "model", "unknown"),
                "reasoning_effort": getattr(self.model, "reasoning_effort", "unknown"),
            },
            "knowledge_manifest_sha256": sha(self.root / "knowledge/source-map.json"),
            "runtime_sources": (
                __import__(
                    "planner_harness.protocol_sources", fromlist=["protocol_inventory"]
                ).protocol_inventory(ROOT)
                if workflow == "creative_loop_v1"
                else {
                    p.relative_to(Path(__file__).parent).as_posix(): sha(p)
                    for p in Path(__file__).parent.rglob("*")
                    if p.is_file() and p.suffix in {".py", ".md"}
                }
            ),
            "workspace": {"summary": "", "nodes": {}},
            "events": [],
            "reads": {},
            "observations": [],
            "attempts": 0,
            "submission_attempts": [],
            "pending_event": None,
            "notes": "",
            "videos": {"source": self.video.info},
            "jobs": {},
            "evaluations": {},
            "generation_requests": 0,
            "pending_tool": None,
            "renderer_submission": {
                "status": "not_requested",
                "reason": "No generation requested yet."
                if mode == "loop"
                else "Planner-only validation; no generation operation is available.",
            },
        }
        self.output.mkdir(parents=True, exist_ok=True)
        from .execution import prepare_profile

        if workflow == "creative_loop_v1":
            from .creative import configure

            configure(self, execution)
            prepare_profile(self.state["config"]["execution"], self.root, self.state["request"])
        else:
            from .compat.legacy.runtime import configure

            configure(self, execution, rsi, mode)
        self.knowledge.freeze(self.output / "knowledge-snapshot.json")
        self.state["knowledge_snapshot_sha256"] = sha(self.output / "knowledge-snapshot.json")
        if workflow == "creative_loop_v1":
            from .creative import system_prompt

            self.system = system_prompt(self)
        else:
            from .compat.legacy.runtime import system_prompt

            self.system = system_prompt(self, feedback_files)
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
            self.state["videos"][identity] = {
                **video.info,
                "imported": True,
                "provenance": item["provenance"],
                **{k: item[k] for k in ("parent", "prompt", "time_mapping") if k in item},
            }
            observation = video.observe("import-" + identity)
            observation.update(
                video_id=identity, scope="Imported historical result; not generated by this run."
            )
            self.state["observations"].append(observation)
        for path in feedback_files or []:
            from critic_harness.runner import load_feedback

            feedback = load_feedback(path, request, self.state["videos"])
            self.state["evaluations"][
                "imported-critic-" + str(len(self.state["evaluations"]) + 1)
            ] = feedback
        if workflow == "creative_loop_v1":
            from .resources import start_clock

            scope = (
                load(self.output / "budget-scope.json")
                if (self.output / "budget-scope.json").exists()
                else getattr(self.model, "lha_accounting_scope", None)
            )
            if scope is None and getattr(self.model, "is_live_api", False):
                from .accounting import default_api_scope

                scope = default_api_scope(
                    self.output,
                    self.model,
                    max_generations=self.state["config"]["resource_policy"]["max_generations"],
                    wall_seconds=self.state["config"]["resource_policy"]["max_wall_seconds"],
                    lane=self.state["config"]["execution"]["experience_mode"],
                )
            start_clock(self.state, scope)
        self.checkpoint()
        return self.run()

    def resume(
        self, *, additional_turns=0, execution=None, continue_delivery=False, max_context_chars=None
    ):
        self.state = load(self.output / "state.json")
        from .creative import active

        if not active(self.state):
            from .compat.legacy.runtime import verify_state

            verify_state(self)
        else:
            from critic_harness.one_shot import verify_profile

            verify_profile(self.state["config"]["execution"]["critic"]["frozen_profile"])
            if self.state["config"]["execution"].get("experiment_profile"):
                from .creative import verify_experiment

                verify_experiment(
                    self.state["config"]["execution"]["experiment_profile"], self.root
                )
            from .delivery_review import PROTOCOL as DELIVERY_REVIEW
            from .continuation import VERSION as CONTINUATION

            if (
                self.state["config"].get("delivery_review_protocol") != DELIVERY_REVIEW
                or self.state["config"].get("continuation_policy", {}).get("version")
                != CONTINUATION
            ):
                raise ValueError(
                    "Record an explicit creative protocol migration before resuming this run"
                )
        if (
            active(self.state)
            and self.state.get("online_clock")
            and self.state.get("final")
            and self.state.get("status")
            in {"complete", "budget_exhausted", "delivery_blocked", "execution_failed"}
        ):
            # Verify saved evidence before preserving an immutable settlement.
            if sha(self.output / "system-prompt.txt") != self.state["system_prompt_sha256"]:
                raise ValueError("Recorded operating instructions changed")
            if (
                sha(self.output / "knowledge-snapshot.json")
                != self.state["knowledge_snapshot_sha256"]
            ):
                raise ValueError("Run knowledge snapshot changed")
            if (
                sha(self.state["request"]["source"]["path"])
                != self.state["request"]["source"]["sha256"]
            ):
                raise ValueError("Settled source video changed")
            if load(self.output / "final.json") != self.state["final"]:
                raise ValueError("Settled final record changed")
            from .delivery import verify_settlement

            verify_settlement(self.output)
            return self.state
        if (
            active(self.state)
            and self.state["status"]
            in {"budget_exhausted", "execution_failed", "delivery_blocked", "context_limit"}
            and not continue_delivery
            and not additional_turns
            and max_context_chars is None
        ):
            return self.state
        if self.state["status"] == "complete" and not continue_delivery:
            if active(self.state):
                from .delivery import verify_delivery

                verify_delivery(self.output)
            return self.state
        if active(self.state) and self.state.get("online_clock"):
            from .resources import check_wall, ResourceExhausted

            try:
                check_wall(self.state)
            except ResourceExhausted:
                # An expired result is immutable even with an explicit continuation.
                if self.state.get("final"):
                    return self.state
                from .resources import settle

                settle(self.state, "Task wall-time submission budget exhausted")
                save(self.output / "final.json", self.state["final"])
                self.checkpoint()
                return self.state
        config = self.state["config"]
        if max_context_chars is not None:
            if type(max_context_chars) is not int or max_context_chars < 8192:
                raise ValueError("Context capacity must be at least 8192 characters")
            if self.state.get("pending_event"):
                raise ValueError("Resolve the existing model call before changing context capacity")
            self.state.setdefault("resource_changes", []).append(
                {
                    "at": stamp(),
                    "field": "max_context_chars",
                    "previous": config["max_context_chars"],
                    "next": max_context_chars,
                }
            )
            config["max_context_chars"] = max_context_chars
        if (
            getattr(self.model, "model", "unknown") != config["model"]
            or getattr(self.model, "reasoning_effort", "unknown") != config["reasoning_effort"]
            or type(self.model).__name__ != config["backend"]
        ):
            raise ValueError("Resume must use the recorded backend, model and reasoning effort")
        self.video = Video(self.state["request"]["source"]["path"], self.output)
        if self.video.info["sha256"] != self.state["request"]["source"]["sha256"]:
            raise ValueError("Source video changed; use a new run")
        if self.state.get("knowledge_snapshot_sha256"):
            if (
                sha(self.output / "knowledge-snapshot.json")
                != self.state["knowledge_snapshot_sha256"]
            ):
                raise ValueError("Run knowledge snapshot changed")
            if active(self.state):
                from .creative_knowledge import CreativeKnowledge

                self.knowledge = CreativeKnowledge(
                    self.root, self.output / "knowledge-snapshot.json"
                )
            else:
                self.knowledge = Knowledge(self.root, self.output / "knowledge-snapshot.json")
        elif (
            sha(self.root / "knowledge/source-map.json") != self.state["knowledge_manifest_sha256"]
        ):
            raise ValueError("Knowledge manifest changed; use a new run")
        else:
            self.knowledge = Knowledge(self.root)
        if sha(self.output / "system-prompt.txt") != self.state["system_prompt_sha256"]:
            raise ValueError("Recorded operating instructions changed")
        self.system = (self.output / "system-prompt.txt").read_text(encoding="utf-8")
        if execution is not None:
            from .execution import prepare_profile

            profile = prepare_profile(execution, self.root, self.state["request"])
            if profile != config.get("execution"):
                if config.get("rsi") or active(self.state):
                    raise ValueError(
                        "This workflow freezes execution profiles; start a new run to change them"
                    )
                event = {
                    "event_id": "runtime-config-" + str(len(self.state["events"]) + 1),
                    "at": stamp(),
                    "status": "ok",
                    "request": {"action": "configure_execution", "origin": "operator CLI"},
                    "result": {
                        "previous": config.get("execution"),
                        "next": profile,
                        "scope": "Future tool requests; outstanding signed jobs are unchanged.",
                    },
                }
                self.state["events"].append(event)
                save(self.output / "events" / (event["event_id"] + ".json"), event)
                config["execution"] = profile
        if continue_delivery:
            if (self.output / "validation-binding.json").exists():
                raise ValueError("Keep a frozen validation run unchanged")
            from .delivery import continue_budget_stop

            continue_budget_stop(self.state)
            self.state["delivery_continuations"][-1].update(
                at=stamp(),
                runtime_sources={
                    p.name: sha(p)
                    for p in Path(__file__).parent.iterdir()
                    if p.suffix in {".py", ".md"}
                },
            )
        if self.state["config"]["max_turns"] is not None:
            extra_turns = max(0, int(additional_turns))
            previous_limit = self.state["config"]["max_turns"]
            self.state["config"]["max_turns"] += extra_turns
            if self.state["config"].get("resource_policy"):
                self.state["config"]["resource_policy"]["max_turns"] = self.state["config"][
                    "max_turns"
                ]
                if extra_turns:
                    self.state.setdefault("resource_changes", []).append(
                        {
                            "at": stamp(),
                            "field": "max_turns",
                            "previous": previous_limit,
                            "next": self.state["config"]["max_turns"],
                            "origin": "explicit additional_turns",
                        }
                    )
        if self.state.get("final") and self.state["status"] != "complete":
            self.state.setdefault("interruption_history", []).append(self.state.pop("final"))
            save(
                self.output
                / "interruptions"
                / f"{len(self.state['interruption_history']):04d}.json",
                self.state["interruption_history"][-1],
            )
            (self.output / "final.json").unlink(missing_ok=True)
        self.state["status"] = "running"
        self.checkpoint()
        return self.run()

    def context(self):
        from .creative import active

        if not active(self.state):
            from .compat.legacy.runtime import context

            return context(self)
        from .context import attachments, present, fit_creative, base_context

        text, _, _ = base_context(self)
        payload = present(json.loads(text), self.state, self.knowledge)
        images, mapping = attachments(self.state)
        payload["attached_images_in_order"] = mapping
        from .working_memory import visible

        visible(payload, self.state)
        from .context import fit_multimodal

        payload, images, mapping = fit_multimodal(payload, self.state, self.system, images, mapping)
        return json.dumps(payload, ensure_ascii=False, indent=2), images, mapping

    def _legacy_context(self):
        """Compatibility facade for callers of the archived raw context API."""
        from .compat.legacy.runtime import raw_context

        return raw_context(self)

    def update_workspace(self, update):
        if not isinstance(update, dict):
            raise ValueError("workspace must be an object")
        new = copy.deepcopy(self.state["workspace"])
        if "summary" in update:
            if not isinstance(update["summary"], str):
                raise ValueError("workspace.summary must be text")
            new["summary"] = update["summary"]
        for node in update.get("nodes", []):
            if not isinstance(node, dict) or not re.fullmatch(
                r"[A-Za-z0-9_.-]{1,80}", str(node.get("id", ""))
            ):
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
        # A completed self-check survives a correctable error in the next action.
        # Other action changes remain transactional until that action succeeds.
        original = self.state
        self.state = copy.deepcopy(original)
        review = None
        review_selection = None
        try:
            from .creative import active

            if active(self.state):
                from .automatic_review import capture

                review = capture(self, response, event_id)
                if review and review.get("status") == "review_required":
                    result = review
                    review = None
                else:
                    if review:
                        review_selection = copy.deepcopy(self.state.get("deadline_selection"))
                    result = self._operate(response, event_id)
            else:
                result = self._operate(response, event_id)
        except Exception as exc:
            self.state = original
            if review and isinstance(exc, (ValueError, KeyError, TypeError, OSError)):
                original.setdefault("reviews", {})[review["video_id"]] = review
                if original.get("pending_review", {}).get("video_id") == review["video_id"]:
                    original.pop("pending_review", None)
                if review_selection is not None:
                    original["deadline_selection"] = review_selection
            raise
        staged = self.state
        self.state = original
        original.clear()
        original.update(staged)
        return result

    def _operate(self, response, event_id):
        from .creative import active

        if active(self.state):
            from .creative_actions import operate
        else:
            from .compat.legacy.actions import operate
        return operate(self, response, event_id)

    def remember(self, text, append=True):
        if not isinstance(text, str) or re.search(r"[\u3400-\u9fff]", text):
            raise ValueError("Write notes in English")
        value = (self.state.get("notes", "") + "\n" + text).strip() if append else text
        if self.state["config"].get("workflow") == "creative_loop_v1":
            from .working_memory import POLICY

            if len(value) > POLICY["notes_chars"]:
                raise ValueError(
                    "Working notes exceed their budget; replace with a concise note. Original successful notes and this raw response remain in history."
                )
        self.state["notes"] = value

    def observe(self, arguments, event_id):
        from .event_observation import observe_videos

        return observe_videos(self.state, self.output, arguments, event_id)

    def submit(self, proposal):
        from .compat.legacy.actions import submit

        return submit(self, proposal)

    def run(self):
        from .report import report
        from .resources import ResourceExhausted, check_wall, settle
        from .model_call import ModelTransportError
        from .accounting import ExternalExecutionUnknown

        if self.state["config"].get("resource_policy"):
            self.model.lha_resource_budget = {
                "root": str(self.output),
                "policy": self.state["config"]["resource_policy"],
            }
        try:
            check_wall(self.state)
            if self.state.get("pending_tool"):
                from .execution import collect

                if not collect(self):
                    if self.state["status"] != "needs_reconciliation":
                        self.state["status"] = "waiting_tool"
                    return self.state
            if self.state["config"].get("workflow") != "creative_loop_v1":
                from .compat.legacy.runtime import before_run

                if before_run(self):
                    return self.state
            while self.state["status"] == "running" and (
                self.state.get("pending_event")
                or self.state["config"]["max_turns"] is None
                or self.state["attempts"] < self.state["config"]["max_turns"]
            ):
                check_wall(self.state)
                if self.state.get("pending_event"):
                    event_id = self.state["pending_event"]
                    call_dir = self.output / "calls" / event_id
                    saved = load(call_dir / "input.json")
                    user_text, mapping = saved["user_text"], saved["images"]
                    images = [item["path"] for item in mapping]
                    if saved["system_prompt"] != self.system or any(
                        sha(item["path"]) != item["sha256"] for item in mapping
                    ):
                        raise ValueError("Pending call inputs changed")
                else:
                    user_text, images, mapping = self.context()
                    from .working_memory import estimate

                    estimate_record = estimate(self.system, user_text, len(images))
                    if (
                        len(self.system) + len(user_text)
                        > self.state["config"]["max_context_chars"]
                        or estimate_record["total_estimated"] > estimate_record["limit"]
                    ):
                        # A context capacity issue is an execution/configuration error,
                        # never a task budget. fit_creative deterministically pages archives.
                        raise ValueError(
                            "Configured input capacity is smaller than the task and current decision view"
                        )
                    self.state["attempts"] += 1
                    event_id = f"event-{self.state['attempts']:04d}"
                    call_dir = self.output / "calls" / event_id
                    save(
                        call_dir / "input.json",
                        {
                            "system_prompt": self.system,
                            "user_text": user_text,
                            "images": mapping,
                            "created_at": stamp(),
                        },
                    )
                    save(call_dir / "context-budget.json", estimate_record)
                    if self.state["config"].get("workflow") != "creative_loop_v1":
                        from .compat.legacy.runtime import record_decision

                        record_decision(self, call_dir)
                    self.state["pending_event"] = event_id
                    self.checkpoint()
                if self.state["config"].get("workflow") == "creative_loop_v1":
                    from .continuation import record_input as record_continuation_input

                    record_continuation_input(self, event_id, call_dir)
                    from .experience_usage import record_exposure

                    try:
                        record_exposure(
                            call_dir,
                            self.knowledge.usage_index(),
                            self.state.get("knowledge_snapshot_sha256"),
                        )
                    except (OSError, ValueError, KeyError, TypeError) as exc:
                        # Telemetry must not turn a valid creative operation into a retry.
                        warning = {"event_id": event_id, "error_type": type(exc).__name__}
                        warnings = self.state.setdefault("experience_recording_warnings", [])
                        if warning not in warnings:
                            warnings.append(warning)
                print(
                    f"[{self.output.name}] {event_id}: model call, {len(images)} images", flush=True
                )
                raw_path = call_dir / "response.txt"
                try:
                    if raw_path.exists():
                        raw = raw_path.read_text(encoding="utf-8")
                    else:
                        if self.state["config"].get("workflow") == "creative_loop_v1":
                            from .model_call import call_text

                            raw = call_text(
                                call_dir / "transport", self.model, self.system, user_text, images
                            )
                        else:
                            from .compat.legacy.runtime import call_model

                            raw = call_model(self, call_dir, user_text, images)
                        raw_path.write_text(raw, encoding="utf-8")
                    check_wall(self.state)
                    from .json_output import decode_object

                    parsed = decode_object(raw)
                    event = {"event_id": event_id, "at": stamp(), "request": parsed, "status": "ok"}
                    try:
                        event["result"] = self.operate(parsed, event_id)
                    except ResourceExhausted:
                        raise
                    except (ValueError, KeyError, TypeError, OSError) as exc:
                        event.update(status="operation_error", result={"error": str(exc)})
                except ResourceExhausted:
                    raise
                except (json.JSONDecodeError, ValueError) as exc:
                    event = {
                        "event_id": event_id,
                        "at": stamp(),
                        "status": "response_error",
                        "result": {
                            "error": str(exc),
                            "instruction": "Return a valid JSON operation envelope.",
                        },
                    }
                self.state["events"].append(event)
                save(self.output / "events" / f"{event_id}.json", event)
                self.state["pending_event"] = None
                self.checkpoint()
                print(
                    f"[{self.output.name}] {event_id}: {event.get('request', {}).get('action')} / {event['status']}",
                    flush=True,
                )
            if self.state["status"] == "running":
                settle(self.state, "Planner turn submission budget exhausted")
                save(self.output / "final.json", self.state["final"])
        except ResourceExhausted as exc:
            if self.state.get("online_clock"):
                from .accounting import freeze_task

                marker = self.output / "budget-scope.json"
                if marker.exists():
                    self.state["deadline_cleanup"] = freeze_task(load(marker), reason=str(exc))
            settle(self.state, str(exc))
            self.state["pending_event"] = None
            save(self.output / "final.json", self.state["final"])
        except ExternalExecutionUnknown as exc:
            event_id = self.state.get("pending_event")
            self.state.setdefault("unresolved_calls", {})[event_id or "unknown-call"] = {
                "event_id": event_id,
                "failure_kind": exc.failure_kind,
                "error": str(exc),
                "scope": "Retain original call and unified reservation; no automatic resubmission",
            }
            self.state["status"] = "needs_reconciliation"
        except ModelTransportError as exc:
            settle(self.state, str(exc), status="execution_failed")
            self.state["pending_event"] = None
            save(self.output / "final.json", self.state["final"])
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
