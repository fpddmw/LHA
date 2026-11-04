"""Connect the unchanged model-led task semantics to the durable resource queue."""

from __future__ import annotations

import copy
from pathlib import Path
import re
import sys

from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock
from .media_cache import DecodeCache


def artifact(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


class Service:
    def __init__(self, queue, directory, root, config, *, model_factory=None, renderer=None):
        self.queue, self.directory, self.root = (
            queue,
            Path(directory).resolve(),
            Path(root).resolve(),
        )
        if self.root != Path(__file__).resolve().parents[2]:
            raise ValueError(
                "Run the service from the same checkout whose code is being fingerprinted"
            )
        self.config = copy.deepcopy(config)
        from planner_harness.accounting import install

        self.accounting_root = Path(
            self.config.get("accounting_root", self.directory / "accounting")
        ).resolve()
        policy = self.config.get("budget")
        existing = self.accounting_root / "policy.json"
        self.default_task_accounting = (
            self.config.get("workflow") == "creative_loop_v1"
            and policy is None
            and not ("accounting_root" in self.config and existing.exists())
        )
        if not self.default_task_accounting:
            if policy is None and existing.exists():
                policy = load(existing)
            self.accounting_root = install(self.accounting_root, policy)
        if self.config.get("workflow") == "creative_loop_v1":
            from planner_harness.creative import role_settings

            for role in ("planner", "online_critic"):
                role_settings(self.config, role)
            if (
                "rsi" in self.config
                or "task_card" in self.config
                or self.config.get("enable_final_evaluation")
            ):
                raise ValueError(
                    "Creative services exclude RSI, task cards and the legacy final-evaluation queue"
                )
        self.runtime_sources = self.source_inventory()
        with RunLock(self.directory / "configuration"):
            from experiments.resumption import bind_deployment
            self.config = bind_deployment(self.directory / "config.json", self.config)
            from planner_harness.upgrade import retain
            retain(self.directory / "runtime-sources.json", self.runtime_sources)
            if self.config.get("workflow") == "creative_loop_v1":
                from planner_harness.creative import role_settings, verify_experiment
                from critic_harness.one_shot import frozen_profile

                for role in ("planner", "online_critic"):
                    role_settings(self.config, role)
                retain(
                    self.directory / "critic-profile.json",
                    frozen_profile(**role_settings(self.config, "online_critic")),
                )
                if self.config.get("experiment_profile"):
                    immutable(
                        self.directory / "experiment-profile.json",
                        verify_experiment(self.config["experiment_profile"], self.root),
                    )
        self.model_factory = model_factory or self.client
        self.renderer = renderer
        self.decode = DecodeCache(config.get("decode_cache_bytes", 512 * 1024 * 1024))

    def source_inventory(self):
        if self.config.get("workflow") == "creative_loop_v1":
            from planner_harness.protocol_sources import protocol_inventory

            return protocol_inventory(self.root)
        sources = {}
        for package in ("server_runtime", "planner_harness", "critic_harness", "evaluation", "vlm"):
            for path in sorted((self.root / "src" / package).rglob("*")):
                if path.is_file() and path.suffix in {".py", ".md"}:
                    sources[str(path.relative_to(self.root)).replace("\\", "/")] = sha(path)
        worker = self.root / "scripts/run_planner_worker.py"
        if worker.exists():
            sources["scripts/run_planner_worker.py"] = sha(worker)
        return sources

    def client(self, role):
        from vlm.settings import create_client

        client = create_client(self.config, role)
        client.lha_service_owner = str(self.directory)
        return client

    def owned_external(self):
        from planner_harness.accounting import active

        return [item for item in active() if item.get("owner") == str(self.directory)]

    def unresolved_resources(self):
        from planner_harness.execution import signature

        rows = []
        for item in self.owned_external():
            marker = (
                Path(item["root"])
                / "task-cleanup"
                / signature({"topic": item["topic"], "lane": item["lane"]})
                / "receipt.json"
            )
            cleanup = load(marker) if marker.exists() else {}
            stopped = any(
                c.get("operation") == item["operation"] and c.get("resource_released") is True
                for c in cleanup.get("cancellations", [])
            )
            if not stopped:
                rows.append(
                    {
                        **item,
                        "resource": "gpu"
                        if item["kind"] == "render"
                        or (
                            item["kind"] == "preparation"
                            and item.get("resource_kind", "gpu") == "gpu"
                        )
                        else "llm",
                    }
                )
        return rows

    def resources_unknown(self):
        return bool(self.unresolved_resources())

    def gpu_unknown(self):
        return any(r["resource"] == "gpu" for r in self.unresolved_resources())

    def blocks_dispatch(self, job):
        # An old unknown model request quarantines its topic, not this GPU.
        if getattr(self, 'admitted_topic', None):
            payload = job.get('payload', {})
            task = load(payload['request']).get('accounting_scope', {}) if 'request' in payload else payload.get('task', {})
            topic = task.get('topic', task.get('budget_topic'))
            lane = task.get('lane', task.get('budget_lane'))
            if topic != self.admitted_topic or lane != self.admitted_lane:
                return True
        rows = self.unresolved_resources()
        if any(r["resource"] == "gpu" for r in rows):
            return True
        payload = job.get("payload", {})
        if "request" in payload:
            if not rows:
                return False
            try:
                scope = load(payload["request"]).get("accounting_scope", {})
            except (OSError, ValueError, TypeError, AttributeError):
                return False
            topic = scope.get("topic")
        else:
            task = payload.get("task", {})
            topic = task.get("budget_topic", task.get("id"))
        return any(r["topic"] == topic for r in rows)

    def task_scope(self, task, run):
        """Use explicit batch accounting, or the same per-task defaults as standalone runs."""
        from planner_harness.accounting import scope, default_api_scope

        if not self.default_task_accounting:
            return scope(
                self.accounting_root,
                task.get("budget_topic", task["id"]),
                task.get("budget_lane", "independent"),
            )
        from planner_harness.resources import configure

        execution = task["execution"]
        policy = configure(
            {"config": {"max_generations": task.get("max_generations")}},
            execution.get("resource_policy"),
            continuation=execution.get("continuation_policy"),
            backend=execution.get("renderer", {}).get("backend", "bernini"),
        )
        return default_api_scope(
            run,
            max_generations=policy["max_generations"],
            wall_seconds=policy["max_wall_seconds"],
            lane=task.get("budget_lane", execution.get("experience_mode", "full")),
            topic=task.get("budget_topic", task["id"]),
        )

    def ensure_ready(self):
        if self.gpu_unknown():
            from planner_harness.accounting import ExternalExecutionUnknown

            raise ExternalExecutionUnknown(
                "This worker retains an unresolved owned execution; no new task or GPU dispatch"
            )
        if self.renderer is None:
            from .renderers import ProcessRenderer

            self.renderer = ProcessRenderer(
                self.root, self.config["renderer"], self.directory / "gpu"
            )
        if hasattr(self.renderer, "initialize"):
            self.renderer.initialize()

    def close(self):
        from planner_harness.accounting import active

        if self.gpu_unknown():
            save(
                self.directory / "resources-retained.json",
                {
                    "status": "in_flight_unknown",
                    "operations": [
                        {k: v for k, v in item.items() if k != "thread"}
                        for item in self.owned_external()
                    ],
                    "note": "Renderer/device ownership retained; not released by supervisor timeout.",
                },
            )
            return
        if self.renderer is not None and hasattr(self.renderer, "close"):
            self.renderer.close()

    def recover(self, job, directory):
        # Replay committed responses first. Unsubmitted work and remaining transport
        # attempts may resume only under their original request identity and allowance.
        if (
            job["kind"] == "tool"
            and Path(job["payload"]["request"]).with_name("response.json").exists()
        ):
            return self(job, directory)
        if job["kind"] == "planner":
            run = Path(job["payload"]["run"])
            completed_response = False
            with RunLock(run):
                state_path = run / "state.json"
                if state_path.exists():
                    state = load(state_path)
                    from planner_harness.resumption import reopen_interrupted_state
                    state = reopen_interrupted_state(run,state)
                    if not state.get("pending_event") and state.get("status") in {
                        "waiting_tool",
                        "complete",
                        "delivery_blocked",
                        "budget_exhausted",
                        "context_limit",
                        "execution_failed",
                    }:
                        snapshot = directory / "planner-state.json"
                        save(snapshot, state)
                        return {"state": state, "artifacts": [artifact(snapshot)]}
                    event = state.get("pending_event")
                    if event:
                        call = run / "calls" / event
                        transport = call / "transport"
                        returned = transport / "returned.json"
                        response = transport / "response.txt"
                        if returned.exists() and response.exists():
                            sent = load(transport / "input.json")
                            prepared = load(call / "input.json")
                            completed_response = (
                                load(returned).get("sha256") == sha(response)
                                and sent["user_text"] == prepared["user_text"]
                                and sent["system_prompt"] == prepared["system_prompt"]
                            )
            from planner_harness.resumption import planner_ready
            if completed_response or ("task" in job["payload"] and planner_ready(run)):
                return self(job, directory)
        if job['kind'] == 'tool':
            from planner_harness.resumption import calls_ready
            request_path = Path(job['payload']['request'])
            request = load(request_path)
            if request['kind'] == 'generate':
                from planner_harness.accounting import operation
                scope = request.get('accounting_scope')
                record = operation(scope,request['sha256']) if scope else None
                if not request_path.with_name('render-started.json').exists() and (record is None or record['status']=='reserved'):
                    return self(job,directory)
            elif calls_ready(request_path.parent):
                return self(job,directory)
        return None

    def reconcile_queue(self):
        """Repair original queue receipts, leaving ambiguous external calls blocked."""
        from planner_harness.resumption import (reconcile_accounting, recover_texts,
            repair_render_response, planner_ready, calls_ready, archive_remove)
        reconcile_accounting(self.accounting_root)
        recover_texts(self.directory,self.accounting_root)
        rows = self.queue.rows()
        latest = {}
        for row in rows:
            if row['kind']=='planner':latest[row['payload']['run']] = row['id']
        for row in rows:
            if self.blocks_dispatch(row):continue
            ready = False
            if row['kind']=='planner':
                run = Path(row['payload']['run'])
                if row['id'] != latest[str(run)]:continue
                state = load(run/'state.json') if (run/'state.json').exists() else {}
                from planner_harness.resumption import reopen_interrupted_state
                state = reopen_interrupted_state(run,state)
                interrupted = state.get('status') in {'running','interrupted','model_unavailable','needs_reconciliation','transport_or_runtime_error'}
                ready = planner_ready(run) and (row['state'] in {'failed','needs_review'} or (row['state']=='complete' and interrupted))
            elif row['kind']=='tool':
                path = Path(row['payload']['request'])
                repair_render_response(path)
                response = path.with_name('response.json')
                ready = (response.exists() and not load(response).get('outcome_unknown')) or (
                    not response.exists() and not path.with_name('render-started.json').exists() and calls_ready(path.parent))
                ready = ready and row['state'] in {'failed','needs_review'}
            if ready:
                folder = self.directory/'jobs'/str(row['id'])
                history = folder/'recovery-history'
                immutable(history/(signature(row)+'.json'),row)
                archive_remove(folder/'receipt.json',history)
                with self.queue.transaction() as db:
                    db.execute('UPDATE jobs SET state="queued",owner=NULL,result=NULL,finished=NULL,expanded=0 WHERE id=? AND state=?', (row['id'],row['state']))

    def submit(self, task):
        task = copy.deepcopy(task)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", task["id"]):
            raise ValueError("Task id must be a safe path component")
        # Recover the original task before processing new launch defaults.
        saved = self.directory/'tasks'/task['id']/'task.json'
        if saved.exists():
            from planner_harness.upgrade import retain
            task = retain(saved, task)
            return self.queue.enqueue(task['id']+'/planner/start', 'planner', 'llm',
                {'task':task, 'run':str(saved.parent/'run')})
        source = (self.root / task["source"]).resolve()
        if sha(source) != task["source_sha256"]:
            raise ValueError("Source hash mismatch")
        if not task.get("request"):
            raise ValueError("Task request required")
        from planner_harness.delivery import completion_mode

        task["workflow"] = task.get("workflow", self.config.get("workflow", "legacy"))
        if (
            self.config.get("workflow") == "creative_loop_v1"
            and task["workflow"] != "creative_loop_v1"
        ):
            raise ValueError("Keep legacy tasks on a separate legacy service")
        if task["workflow"] == "creative_loop_v1":
            if self.config.get("workflow") != "creative_loop_v1":
                raise ValueError("Creative tasks need an explicitly configured creative service")
            from planner_harness.creative import role_settings

            for role in ("planner", "online_critic"):
                role_settings(self.config, role)
            if task.get("rsi") is not None or "task_card" in task or task.get("final_evaluation"):
                raise ValueError("Creative tasks exclude RSI and legacy final-evaluation cards")
            task.setdefault("completion_mode", "delivery")
        task["completion_mode"] = completion_mode(
            task.get("max_generations"), task.get("completion_mode")
        )
        execution = task.get("execution", {})
        if task["workflow"] == "creative_loop_v1":
            for field in ("review", "planner", "critic", "models"):
                if field in self.config:
                    execution.setdefault(field, copy.deepcopy(self.config[field]))
        if (
            task["workflow"] == "creative_loop_v1"
            and self.config.get("continuation_policy")
            and "continuation_policy" not in execution
        ):
            execution["continuation_policy"] = copy.deepcopy(self.config["continuation_policy"])
        task["execution"] = execution
        if self.config.get("experiment_profile"):
            from planner_harness.creative import verify_experiment

            verify_experiment(self.config["experiment_profile"], self.root)
            if (
                execution.get("experiment_profile", self.config["experiment_profile"])
                != self.config["experiment_profile"]
            ):
                raise ValueError("Task experiment identity differs from the service")
            execution["experiment_profile"] = self.config["experiment_profile"]
        if "renderer" not in execution:
            raise ValueError("Task requires an explicit renderer profile")
        if execution.get("mode", "live") != "live":
            raise ValueError(
                "Server tasks use live execution; replay belongs to separate validation runs"
            )
        if self.renderer is None:
            resident = self.config.get("renderer", {})
            if (
                resident.get("backend") not in {"bernini", "ditto"}
                or execution["renderer"].get("backend") != resident["backend"]
                or execution["renderer"].get("generation") != resident.get("generation")
            ):
                raise ValueError("Configure the same supported resident renderer before submitting")
        # Final benchmark configuration is deliberately absent from the Planner execution profile.
        if task.get("final_evaluation"):
            if not self.config.get("enable_final_evaluation", False):
                raise ValueError("Final evaluation is disabled for this service")
            cfg = task["final_evaluation"]
            cfg["card_data"] = self.card(cfg.get("card_data") or cfg["card"], task)
            if isinstance(cfg.get("references"), str):
                cfg["references"] = load(self.root / cfg["references"])
        task["source"] = str(source)
        directory = self.directory / "tasks" / task["id"]
        immutable(directory / "task.json", task)
        return self.queue.enqueue(
            task["id"] + "/planner/start",
            "planner",
            "llm",
            {"task": task, "run": str(directory / "run")},
        )

    def card(self, path, task=None):
        from evaluation.protocol import validate_card

        card = validate_card(
            copy.deepcopy(path) if isinstance(path, dict) else load(self.root / path)
        )
        if task and (
            card["source_sha256"] != task["source_sha256"] or card["requirement"] != task["request"]
        ):
            raise ValueError("Final evaluation card must match exact original task")
        return card

    def submit_evaluation(self, case, *, parents=()):
        if not self.config.get("enable_final_evaluation", False):
            raise ValueError("Final evaluation is disabled for this service")
        case = copy.deepcopy(case)
        card = self.card(case.get("card_data") or case["card"])
        source = self.root / card["source_video"]
        output = self.root / case["output_video"]
        if sha(source) != card["source_sha256"] or sha(output) != case["output_sha256"]:
            raise ValueError("Evaluation media hash mismatch")
        case["card_data"] = card
        if case.get("mapping") and isinstance(case["mapping"], str):
            case["mapping"] = load(self.root / case["mapping"])
        if case.get("references") and isinstance(case["references"], str):
            case["references"] = load(self.root / case["references"])
        case["output_video"] = str(output.resolve())
        key = "final/" + case["case_id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", case["case_id"]):
            raise ValueError("Unsafe evaluation case id")
        path = self.directory / "evaluations" / case["case_id"]
        payload = {"case": case, "directory": str(path)}
        prep = self.queue.enqueue(
            key + "/evidence", "prepare", "cpu", payload, parents=parents, priority=30
        )
        return self.queue.enqueue(
            key + "/judge", "judge", "llm", payload, parents=[prep], priority=30
        )

    def __call__(self, job, directory):
        kind, payload = job["kind"], job["payload"]
        if kind == "planner":
            from planner_harness import PlannerHarness

            task, run = payload["task"], Path(payload["run"])
            with RunLock(run):
                from planner_harness.accounting import scope, bind, attach

                budget_scope = self.task_scope(task, run)
                bind(run, budget_scope)
                if task.get("workflow") == "creative_loop_v1":
                    self.ensure_ready()
                client = attach(self.model_factory("planner"), budget_scope)
                client.lha_service_owner = str(self.directory)
                harness = PlannerHarness(run, client, root=self.root)
                if (run / "state.json").exists():
                    state = harness.resume()
                else:
                    if sha(task["source"]) != task["source_sha256"]:
                        raise ValueError("Task source changed before planning")
                    state = harness.start(
                        task["source"],
                        task["request"],
                        mode="loop",
                        target=task["execution"].get("renderer", {}).get("backend", "unspecified"),
                        execution=task["execution"],
                        max_turns=task.get("max_turns"),
                        max_context_chars=task.get("max_context_chars", 180000),
                        max_generations=task.get("max_generations"),
                        completion_mode=task.get("completion_mode"),
                        run_instructions=task.get("run_instructions", ""),
                        rsi=task.get("rsi"),
                        workflow=task.get("workflow", "legacy"),
                    )
            snapshot = directory / "planner-state.json"
            save(snapshot, state)
            return {"state": state, "artifacts": [artifact(snapshot)]}
        if kind == "tool":
            path = Path(payload["request"])
            request = load(path)
            if (
                request["sha256"] != payload["request_sha256"]
                or signature({k: v for k, v in request.items() if k != "sha256"})
                != request["sha256"]
            ):
                raise ValueError("Signed tool request changed")
            response_path = path.with_name("response.json")
            with RunLock(path.parent / "worker"):
                if response_path.exists():
                    response = load(response_path)
                    if (
                        response.get("request_sha256") != request["sha256"]
                        or response.get("mode") != request["mode"]
                    ):
                        raise ValueError("Existing tool response mismatch")
                    if response.get("status") not in {"complete", "failed"}:
                        raise ValueError("Tool response is not final")
                else:
                    response = {
                        "request_sha256": request["sha256"],
                        "mode": request["mode"],
                        "status": "complete",
                    }
                    try:
                        if request["kind"] == "generate":
                            started = path.with_name("render-started.json")
                            from planner_harness.accounting import (
                                invoke,
                                scope,
                                operation,
                                SubmissionRefused,
                            )

                            budget_scope = request.get("accounting_scope")
                            state_scope = path.parents[2] / "budget-scope.json"
                            if budget_scope is None and state_scope.exists():
                                budget_scope = load(state_scope)
                            if budget_scope is None:
                                budget_scope = scope(
                                    self.accounting_root, request.get("budget_topic", request["id"])
                                )
                            if started.exists():
                                previous = operation(budget_scope, request["sha256"])
                                if previous is not None and previous["status"] == "not_submitted":
                                    raise SubmissionRefused(
                                        "Original render was refused before dispatch; no automatic retry"
                                    )
                                from planner_harness.recovery import UncertainRender

                                raise UncertainRender(
                                    "A render was already dispatched; recover its receipt before retrying"
                                )
                            from planner_harness.resources import ResourceExhausted

                            self.ensure_ready()
                            # Token/source/time-axis validation precedes actual dispatch.
                            if hasattr(self.renderer, "prepare"):
                                from planner_harness.accounting import bounded_preflight

                                bounded_preflight(
                                    budget_scope,
                                    request["sha256"],
                                    lambda: self.renderer.prepare(request, path.parent),
                                    owner=str(self.directory),
                                )

                            def submitted():
                                save(
                                    started,
                                    {
                                        "request_sha256": request["sha256"],
                                        "seed": request["payload"].get("renderer", {}).get("seed"),
                                    },
                                )
                                run = path.parents[2]
                                if (run / "state.json").exists():
                                    with RunLock(run):
                                        current = load(run / "state.json")
                                        if (
                                            current.get("config", {})
                                            .get("resource_policy", {})
                                            .get("version")
                                            == "creative-resources-v2"
                                        ):
                                            ids = current.setdefault("submitted_generation_ids", [])
                                            if request["id"] not in ids:
                                                ids.append(request["id"])
                                            current["generation_requests"] = len(ids)
                                            save(run / "state.json", current)

                            def unsubmitted():
                                save(
                                    path.with_name("render-not-submitted.json"),
                                    {
                                        "request_sha256": request["sha256"],
                                        "reason": "Known refusal before execution",
                                    },
                                )
                                run = path.parents[2]
                                if (run / "state.json").exists():
                                    with RunLock(run):
                                        current = load(run / "state.json")
                                        ids = current.get("submitted_generation_ids", [])
                                        if request["id"] in ids:
                                            ids.remove(request["id"])
                                        if (
                                            current.get("config", {})
                                            .get("resource_policy", {})
                                            .get("version")
                                            == "creative-resources-v2"
                                        ):
                                            current["generation_requests"] = len(ids)
                                        save(run / "state.json", current)

                            def render():
                                try:
                                    return self.renderer(request, path.parent)
                                except ResourceExhausted:
                                    # ProcessRenderer's guarded send proves no render dispatch.
                                    from .renderers import ProcessRenderer

                                    if isinstance(self.renderer, ProcessRenderer):
                                        unsubmitted()
                                    raise

                            requires_live = self.renderer is None or getattr(
                                self.renderer, "requires_live_budget", False
                            )
                            from planner_harness.accounting import checked

                            checked(budget_scope, require_live=requires_live)
                            response["payload"] = invoke(
                                budget_scope,
                                request["sha256"],
                                "render",
                                "render:"
                                + request["payload"].get("renderer", {}).get("backend", "unknown"),
                                render,
                                before_submit=submitted,
                                on_not_submitted=unsubmitted,
                                owner=str(self.directory),
                            )
                        elif request["kind"] == "critique":
                            from critic_harness.adapter import critique

                            client = self.model_factory("online_critic")
                            from planner_harness.accounting import attach, discover

                            client = attach(client, discover(path.parent, client))
                            client.lha_service_owner = str(self.directory)
                            state_path = path.parents[2] / "state.json"
                            if state_path.exists():
                                state = load(state_path)
                                if state["config"].get("resource_policy"):
                                    client.lha_resource_budget = {
                                        "root": str(state_path.parent),
                                        "policy": state["config"]["resource_policy"],
                                    }
                            response["payload"] = critique(
                                request, path.parent, self.root, model=client
                            )
                        elif request["kind"] == "evaluate":
                            sys.path.insert(0, str(self.root / "scripts"))
                            from run_planner_worker import evaluate

                            response["payload"] = evaluate(
                                request,
                                path.parent,
                                self.root,
                                model=self.model_factory("online_feedback"),
                            )
                        else:
                            raise ValueError("Unknown tool")
                    except Exception as exc:
                        from planner_harness.integrity import IntegrityError

                        if isinstance(exc, IntegrityError):
                            raise
                        # A definite tool failure is evidence for the Planner, charged to its existing action.
                        response.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                        if getattr(exc, "task_deadline", False):
                            response["task_deadline"] = True
                            response["deadline_cleanup"] = getattr(exc, "cleanup", None)
                            response["resource_ownership_unknown"] = self.resources_unknown()
                            response["outcome_unknown"] = response["resource_ownership_unknown"]
                        from planner_harness.accounting import SubmissionRefused

                        if isinstance(exc, SubmissionRefused):
                            response.update(outcome_unknown=False, retryable=False)
                        if getattr(exc, "outcome_unknown", False):
                            response["outcome_unknown"] = True
                        if getattr(exc, "failure_kind", None) in {
                            "report_unavailable",
                            "resource_exhausted",
                        }:
                            response["failure_kind"] = exc.failure_kind
                        if getattr(exc, "failure_kind", None) == "model_transport":
                            response["failure_kind"] = "model_transport"
                            response["retryable"] = exc.retryable
                    save(response_path, response)
            if self.config.get("workflow") == "creative_loop_v1":
                if response.get("task_deadline"):
                    self.freeze_task_result(path, request, response)
                    if response.get("resource_ownership_unknown"):
                        from planner_harness.accounting import ExternalExecutionUnknown

                        raise ExternalExecutionUnknown(
                            "Task result froze at deadline; this worker retains unresolved resource ownership"
                        )
                elif response.get("outcome_unknown"):
                    # A needs_review queue job deliberately blocks its dependent
                    # Planner. Account for quarantine directly, without invoking
                    # that Planner or issuing another render. The worker lock has
                    # been released before acquiring the run lock.
                    self.quarantine_tool_outcome(path, request)
                    from planner_harness.recovery import UncertainRender

                    raise UncertainRender(
                        "Tool outcome is unknown; reconcile the same job before continuing"
                    )
            artifacts = [artifact(response_path)]
            if request["kind"] == "generate" and response["status"] == "complete":
                video = response["payload"]["video"]
                if sha(video["path"]) != video["sha256"]:
                    raise ValueError("Generated artifact changed")
                artifacts.append(video)
            return {"response": response, "artifacts": artifacts}
        if kind in {"prepare", "judge"}:
            from evaluation.media import prepare
            from evaluation.judges import judge, verify_evidence
            from evaluation.scoring import score

            case, output = payload["case"], Path(payload["directory"])
            card = case["card_data"]
            if sha(case["output_video"]) != case["output_sha256"]:
                raise ValueError("Evaluation output changed")
            evidence_path = output / "evidence/evidence.json"
            if kind == "prepare":
                if evidence_path.exists():
                    evidence = load(evidence_path)
                    verify_evidence(card, evidence)
                    if evidence["output_sha256"] != case["output_sha256"]:
                        raise ValueError("Evidence belongs to another output")
                else:
                    prepare(
                        card,
                        Path(case["output_video"]),
                        evidence_path.parent,
                        root=self.root,
                        dense_ranges=[[0, card["duration_seconds"]]],
                        mapping=case.get("mapping"),
                        decoder=self.decode,
                    )
                return {"artifacts": [artifact(evidence_path)]}
            judgment = judge(
                card,
                load(evidence_path),
                self.model_factory("benchmark_final"),
                output / "judge",
                references=case.get("references"),
                creativity_overview=True,
                creativity_exclude_self=True,
            )
            save(output / "judgment.json", judgment)
            result = {
                "case_id": case["case_id"],
                "method": case["method"],
                "seed": case["seed"],
                "status": "complete",
                "result": score(card, judgment),
            }
            save(output / "record.json", result)
            return {
                "record": result,
                "artifacts": [artifact(output / "record.json"), artifact(output / "judgment.json")],
            }
        raise ValueError("Unknown server job kind")

    def freeze_task_result(self, path, request, response):
        run = Path(path).parents[2]
        if not (run / "state.json").exists():
            return
        with RunLock(run):
            state = load(run / "state.json")
            if state.get("final") and state.get("online_clock", {}).get("frozen_unix"):
                return
            if (
                state.get("pending_tool") != request["id"]
                or state.get("jobs", {}).get(request["id"]) != request
            ):
                raise ValueError("Deadline response differs from its owning task")
            from planner_harness.resources import settle

            settle(
                state, "Online task deadline reached; pending original execution remains auditable"
            )
            state["deadline_cleanup"] = response.get("deadline_cleanup")
            state["resource_ownership_unknown"] = response.get("resource_ownership_unknown", False)
            save(run / "final.json", state["final"])
            save(run / "state.json", state)

    def quarantine_tool_outcome(self, request_path, request):
        run = Path(request_path).parents[2]
        state_path = run / "state.json"
        # Direct renders have no Planner state; run_arm accounts for their own
        # signed response separately.
        if not state_path.exists():
            return
        with RunLock(run):
            from planner_harness import PlannerHarness
            from planner_harness.execution import collect
            from planner_harness.integrity import IntegrityError

            state = load(state_path)
            if (
                state.get("pending_tool") != request["id"]
                or state.get("jobs", {}).get(request["id"]) != request
            ):
                raise IntegrityError("Unknown tool outcome does not match its owning pending task")
            harness = PlannerHarness(run, None, root=self.root)
            harness.state = state
            collect(harness)
            if harness.state["status"] != "needs_reconciliation":
                raise IntegrityError("Unknown tool response was not quarantined")

    def expand(self, job):
        if job["kind"] != "planner":
            return
        state, payload = job["result"]["state"], job["payload"]
        task, run = payload["task"], Path(payload["run"])
        if state["status"] == "waiting_tool":
            identity = state["pending_tool"]
            request = run / "jobs" / identity / "request.json"
            tool = load(request)
            key = task["id"] + "/" + identity
            tool_id = self.queue.enqueue(
                key,
                "tool",
                "gpu" if tool["kind"] == "generate" else "llm",
                {"request": str(request), "request_sha256": tool["sha256"]},
                parents=[job["id"]],
            )
            self.queue.enqueue(
                task["id"] + "/planner/after-" + identity,
                "planner",
                "llm",
                payload,
                parents=[tool_id],
            )
        elif state["status"] == "complete" and task.get("final_evaluation"):
            cfg = task["final_evaluation"]
            selected = state.get("final", {}).get("video")
            videos = {
                k: v
                for k, v in state["videos"].items()
                if (cfg.get("all_generated", True) and k != "source" and not v.get("imported"))
                or k == selected
            }
            for identity, video in videos.items():
                self.submit_evaluation(
                    {
                        "case_id": task["id"] + "__" + identity,
                        "method": task.get("method", "continuous_loop") + "__" + identity,
                        "seed": video.get("execution", {}).get(
                            "seed", task["execution"].get("renderer", {}).get("seed", 42)
                        ),
                        "card_data": cfg["card_data"],
                        "output_video": video["path"],
                        "output_sha256": video["sha256"],
                        "mapping": video.get("time_mapping"),
                        "references": cfg.get("references"),
                    },
                    parents=[job["id"]],
                )
