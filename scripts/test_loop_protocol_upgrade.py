"""Zero-provider contracts for the next online task protocol."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness import accounting as a
from planner_harness import resources as r, continuation as c
from planner_harness.common import load


def fake_renderer_owner(connection, lock):
    import os
    from planner_harness.lock import RunLock

    os.setsid()
    with RunLock(lock):
        connection.send({"status": "ready"})
        connection.recv()
        time.sleep(20)


class ProtocolTests(unittest.TestCase):
    def state(self, n=5, used=0, fraction=0):
        now = time.time()
        s = {
            "created_at": "2026-11-02T00:00:00Z",
            "config": {"max_generations": n},
            "jobs": {},
            "videos": {},
            "submitted_generation_ids": [],
            "online_clock": {
                "started_unix": now - 3600 * fraction,
                "deadline_unix": now + 3600 * (1 - fraction),
            },
        }
        r.configure(s)
        c.configure(s)
        for i in range(used):
            key = str(i)
            s["jobs"][key] = {"kind": "generate"}
            s["submitted_generation_ids"].append(key)
        return s

    def test_n_and_time_phase_do_not_disclose_limits(self):
        for n in (1, 3, 5, 9):
            for fraction, stage in (
                (0, "exploration"),
                (0.41, "continuation"),
                (0.61, "deliberate"),
                (0.81, "strong"),
            ):
                s = self.state(n, fraction=fraction)
                v = c.view(s)
                self.assertEqual(v["stage"], stage)
                self.assertEqual(
                    set(v),
                    {
                        "stage",
                        "budget_awareness",
                        "justification_required",
                        "continuation_questions",
                        "generation_available",
                    },
                )
            s = self.state(n, used=n)
            self.assertFalse(c.view(s)["generation_available"])
            r.check_wall(s)  # N locks generation; reading/delivery still admitted.
        self.assertEqual(c.phase(self.state(9, used=6)), "deliberate")

    def test_prepared_jobs_do_not_count_and_legacy_caps_are_metering(self):
        s = self.state(1)
        s["jobs"]["not-dispatched"] = {"kind": "generate"}
        self.assertEqual(c.usage(s)["submitted_render_requests"], 0)
        self.assertIsNone(s["config"]["max_turns"])
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(101):
                r.reserve(tmp, str(i), s["config"]["resource_policy"], 50000)
            ledger = load(Path(tmp) / "resource-ledger.json")
            self.assertEqual(len(ledger["calls"]), 101)
            self.assertGreater(sum(v["charged_tokens"] for v in ledger["calls"].values()), 4000000)

    def binding(self, tmp, n=9, wall=3600):
        p = {
            "version": a.VERSION,
            "mode": "offline",
            "max_call_seconds": 0.01,
            "online_task_budget": {
                "version": "online-task-v2",
                "lanes": ["full", "none"],
                "max_generations": n,
                "wall_seconds": wall,
            },
        }
        root = a.install(Path(tmp) / "accounting", p)
        b = a.scope(root, "sample__short", "full")
        a.start_task(b, wall_seconds=wall)
        return b

    def test_metered_calls_and_per_method_clock_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = self.binding(tmp)
            for i in range(101):
                a.invoke(b, str(i), "model", "fixture", lambda: {}, tokens=50000)
            other = a.scope(b["root"], b["topic"], "none")
            clock = a.start_task(other)
            self.assertGreater(clock["deadline_unix"], time.time() + 3590)
            self.assertEqual(a.summary(b["root"])["reserved_or_settled_totals"]["model_calls"], 101)
            a.invoke(
                b, "longer-than-old-call-timeout", "model", "fixture", lambda: time.sleep(0.03)
            )

    def test_deadline_cancels_only_owned_process_and_blocks_late_submission(self):
        import subprocess

        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(5)"])
        try:
            with tempfile.TemporaryDirectory() as tmp:
                b = self.binding(tmp, wall=1)
                root = Path(b["root"])
                # Existing clock is durable; force a small fixture deadline using its first start.
                other = a.scope(root, "short-task", "full")
                a.start_task(other, wall_seconds=1)
                launched = []

                def call():
                    child, remove = a.launch_owned(
                        [sys.executable, "-c", "import time;time.sleep(5)"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    launched.append(child)
                    try:
                        child.process.communicate()
                    finally:
                        remove()
                    return {"late": True}

                with self.assertRaises(r.ResourceExhausted):
                    a.invoke(other, "owned", "model", "fixture", call)
                self.assertIsNotNone(launched[0].process.poll())
                self.assertIsNone(unrelated.poll())
                self.assertTrue(a.start_task(other, wall_seconds=1)["frozen_unix"])
                with self.assertRaises(r.ResourceExhausted):
                    a.invoke(other, "new", "model", "fixture", lambda: self.fail("late submit"))
                end = time.monotonic() + 2
                while a.active(root) and time.monotonic() < end:
                    time.sleep(0.01)
                record = a.operation(other, "owned")
                self.assertIn(record["status"], {"late_complete", "failed_unknown_cost"})
                self.assertEqual(a.summary(root)["reserved_or_settled_totals"]["model_calls"], 1)
        finally:
            unrelated.terminate()
            unrelated.wait()

    def test_generation_failures_occupy_and_before_submit_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = self.binding(tmp, 1)
            with self.assertRaises(ValueError):
                a.invoke(
                    b,
                    "invalid",
                    "render",
                    "fixture",
                    lambda: None,
                    before_submit=lambda: (_ for _ in ()).throw(ValueError("validation")),
                )
            with self.assertRaises(ValueError):
                a.invoke(
                    b,
                    "failed",
                    "render",
                    "fixture",
                    lambda: (_ for _ in ()).throw(ValueError("execution")),
                )
            with self.assertRaises(a.SubmissionRefused):
                a.invoke(b, "extra", "render", "fixture", lambda: None)
            self.assertEqual(
                a.summary(b["root"])["reserved_or_settled_totals"]["render_requests"], 1
            )


class IntegrationTests(unittest.TestCase):
    def test_full_renderer_call_receipt_without_gpu(self):
        from server_runtime.renderers import PersistentRenderer
        from types import SimpleNamespace
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            native = folder / "native.mp4"
            renderer = object.__new__(PersistentRenderer)
            renderer.root = ROOT
            renderer.prefix = "prefix "
            renderer.clean = lambda x: x
            renderer.kwargs = lambda x: {}
            renderer.cli = None
            renderer.assets = {"model_revision": "fixture-model", "code_revision": "fixture-code"}
            renderer.config = {"asset_manifest_sha256": "fixture-assets"}
            renderer.prepare = lambda job, directory: ({"frames": 1, "fps": 1}, [0], 4)
            renderer.pipeline = lambda *args, **kwargs: Path(kwargs["output_path"]).write_bytes(
                b"fixture-video"
            )
            job = {
                "payload": {
                    "input": {"path": str(folder / "input.mp4"), "sha256": "input-hash"},
                    "prompt": "Make blue.",
                    "renderer": {"seed": 1, "output": {"frames": 1, "fps": 1}, "generation": {}},
                }
            }
            with patch.dict(
                sys.modules,
                {
                    "run_prompt_probe": SimpleNamespace(
                        inspect_video=lambda path: {"frames": 1, "fps": 1}
                    )
                },
            ):
                value = renderer(job, folder)
            self.assertEqual(value["execution"]["preflight"], "passed")
            self.assertEqual(value["execution"]["input_sha256"], "input-hash")
            self.assertEqual(value["execution"]["token_count"], 4)
            self.assertTrue(native.is_file())

    def test_knowledge_problem_routes_snapshot_and_none_scope(self):
        from planner_harness.creative_knowledge import CreativeKnowledge

        full = CreativeKnowledge(ROOT, experience_mode="full")
        none = CreativeKnowledge(ROOT, experience_mode="none")
        for identity in ("planning-resources", "observation-diagnosis", "generation-input"):
            self.assertTrue(full.read(identity)["links"])
            with self.assertRaises(ValueError):
                none.read(identity)
        matches = full.search("Which input can recover a lost face?")["matches"]
        self.assertTrue(any(m.get("recommendation") and m.get("renderers") for m in matches))
        self.assertFalse(
            any(
                m.get("id", "").startswith(("EX-", "EV-"))
                for m in none.search("lost face")["matches"]
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            full.freeze(path)
            self.assertEqual(
                CreativeKnowledge(ROOT, path).search("lost face"), full.search("lost face")
            )

    def run_record(self, root):
        from planner_harness.common import save, sha
        from planner_harness.creative_knowledge import CreativeKnowledge

        run = root / "run"
        run.mkdir()
        benchmark = next(
            r for r in load(ROOT / "benchmark_data/benchmark.json") if r["split"] == "train"
        )
        state = {
            "config": {
                "workflow": "creative_loop_v1",
                "execution": {
                    "experience_mode": "none",
                    "benchmark_metadata": {"split": "train", "sample_id": benchmark["sample_id"]},
                },
            },
            "source": {"sha256": benchmark["source_video_sha256"]},
            "status": "budget_exhausted",
            "request": {"text": benchmark.get("prompt_short", benchmark["instruction"])},
            "final": {"outcome": "incomplete"},
            "events": [{"event_id": "event-0001"}],
        }
        save(run / "state.json", state)
        CreativeKnowledge(ROOT, experience_mode="none").freeze(run / "knowledge-snapshot.json")
        call = run / "calls/event-0001"
        save(call / "input.json", {"system_prompt": "role", "user_text": "task", "images": []})
        save(call / "transport/input.json", {"system_prompt": "role", "user_text": "task"})
        (call / "response.txt").write_text('{"action":"note","arguments":{"text":"Task evidence"}}')
        save(call / "transport/returned.json", {"sha256": sha(call / "response.txt")})
        return run

    def test_test_only_idempotent_batch_gate_and_failure_isolation(self):
        from planner_harness import maintenance as m
        from planner_harness.common import sha

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self.run_record(root)
            before = sha(run / "state.json")
            self.assertTrue(m.eligible(run, "train"))
            self.assertFalse(m.eligible(run, "validation"))
            self.assertFalse(m.eligible(run, "test"))
            self.assertIsNone(
                m.enqueue(ROOT, root, run, split="test", topic="t", method="none", batch_sha256="b")
            )
            identity = m.enqueue(
                ROOT, root, run, split="train", topic="t", method="none", batch_sha256="b"
            )
            self.assertEqual(
                identity,
                m.enqueue(
                    ROOT, root, run, split="train", topic="t", method="none", batch_sha256="b"
                ),
            )
            with self.assertRaises(ValueError):
                m.drain(ROOT, root, {"enabled": True})
            self.assertEqual(m.drain(ROOT, root, {"enabled": False})["status"], "disabled")
            batch = {"sha256": "b", "topics": [{"id": "t"}], "arms": ["none"]}
            with self.assertRaises(ValueError):
                m.seal_batch(root, batch, [])
            m.seal_batch(root, batch, [{"topic": "t", "method": "none", "status": "failed"}])

            class Broken:
                model = "gpt-6.1-sol"
                reasoning_effort = "high"

                def predict_text(self, **kwargs):
                    raise ValueError("fixture permanent failure")

            result = m.drain(ROOT, root, {"enabled": True}, model_factory=Broken)
            self.assertEqual(result["jobs"][0]["status"], "failed")
            self.assertEqual(before, sha(run / "state.json"))

    def test_maintenance_retains_loaded_skill_and_cross_task_revision(self):
        from planner_harness import maintenance as m
        from planner_harness.common import sha

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = self.run_record(root)
            before = sha(run / "state.json")
            identity = m.enqueue(
                ROOT, root, run, split="train", topic="t", method="none", batch_sha256="b"
            )
            m.seal_batch(
                root,
                {"sha256": "b", "topics": [{"id": "t"}], "arms": ["none"]},
                [{"topic": "t", "method": "none", "status": "ready"}],
            )

            class Contributor:
                model = "gpt-6.1-sol"
                reasoning_effort = "high"

                def __init__(self):
                    self.inputs = []

                def predict_text(self, **kwargs):
                    self.inputs.append(json.loads(kwargs["user_text"]))
                    n = len(self.inputs)
                    if n == 1:
                        return json.dumps(
                            {"action": "skill", "arguments": {"id": "lha-experience-use-review"}}
                        )
                    if n == 2:
                        return json.dumps(
                            {"action": "read", "arguments": {"source": "run", "id": "state"}}
                        )
                    self.assertions = all(
                        "lha-experience-use-review" in x.get("loaded_skills", {})
                        for x in self.inputs[1:]
                    )
                    return json.dumps(
                        {
                            "action": "contribute",
                            "arguments": {
                                "text": "Keep the required relation visible when evaluating an incomplete event. The saved record leaves the unseen transition unresolved."
                            },
                        }
                    )

            clients = []

            def factory():
                c = Contributor()
                clients.append(c)
                return c

            result = m.drain(ROOT, root, {"enabled": True}, model_factory=factory)
            self.assertEqual(result["jobs"][0]["status"], "complete")
            self.assertTrue(
                all(
                    "lha-experience-use-review" in c.inputs[-1].get("loaded_skills", {})
                    for c in clients
                )
            )
            bundle = Path(result["candidate_bundle"])
            self.assertFalse((bundle.parent / "candidate-revision.md").exists())
            self.assertEqual(len(clients), 1)
            m.curate_candidate_revision(ROOT, root, bundle, m.configuration({"enabled":True}), factory)
            self.assertTrue((bundle.parent / "candidate-revision.md").exists())
            self.assertEqual(before, sha(run / "state.json"))

    def test_frozen_recovery_retains_state_and_never_reopens(self):
        from planner_harness.common import save, sha
        from planner_harness.recovery import recover_tool

        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            state = {
                "config": {"workflow": "creative_loop_v1"},
                "status": "budget_exhausted",
                "final": {"video": "v1"},
                "online_clock": {
                    "started_unix": time.time() - 3601,
                    "deadline_unix": time.time() - 1,
                },
                "jobs": {"j": {"kind": "generate", "mode": "live", "sha256": "request"}},
            }
            save(run / "state.json", state)
            before = sha(run / "state.json")
            record = recover_tool(run, "j", "not-executed", "Operator evidence after deadline")
            self.assertFalse(record["task_result_changed"])
            self.assertEqual(before, sha(run / "state.json"))
            with self.assertRaises(ValueError):
                recover_tool(run, "j", "retry-review", "Do not reopen")
            self.assertEqual(before, sha(run / "state.json"))

    def test_single_planner_real_layout_queues_once_without_knowledge_exposure(self):
        from experiments.unified_benchmark import planner_once
        from planner_harness.maintenance import enqueue_planner_once, eligible
        from planner_harness.common import load, sha
        from test_low_high import video

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            source = output / "source.avi"
            video(source)
            topic = {
                "id": "t",
                "sample_id": "fixture",
                "split": "train",
                "source": str(source),
                "source_sha256": sha(source),
                "request": "Make the room blue.",
            }
            run = output / "methods/t/planner-once/planner"

            class Model:
                model = "gpt-6.1-sol"
                reasoning_effort = "high"

                def predict_text(self, **kwargs):
                    return '{"prompt":"A blue room."}'

            planner_once(ROOT, topic, run, Model())
            settled = {"topic": "t", "method": "planner-once", "status": "failed"}
            import shutil

            for name in [
                "docs/experience-authoring-standard.md",
                "docs/experience-usage-interface.md",
                "docs/online-event-observation.md",
                *[
                    f".agents/skills/{x}/SKILL.md"
                    for x in (
                        "lha-experience-analysis",
                        "lha-experience-use-review",
                        "lha-experience-curation",
                    )
                ],
            ]:
                target = output / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            from planner_harness.common import save

            save(
                output / "benchmark_data/benchmark.json",
                [
                    {
                        "sample_id": "fixture",
                        "split": "train",
                        "source_video_sha256": sha(source),
                        "prompt_short": topic["request"],
                    }
                ],
            )
            from planner_harness.training_experience import initialize
            initialize(ROOT, output)
            identity = enqueue_planner_once(output, output, topic, settled, {"sha256": "batch"})
            self.assertTrue(identity)
            self.assertTrue(eligible(run, "train"))
            self.assertEqual(
                identity, enqueue_planner_once(output, output, topic, settled, {"sha256": "batch"})
            )
            self.assertEqual(len(list((output / "maintenance/jobs").glob("*/job.json"))), 1)
            snapshot = load(run / "knowledge-snapshot.json")
            self.assertFalse(snapshot["enabled"])
            self.assertEqual(snapshot["curated_catalog"]["entries"], [])
            self.assertTrue(load(run / "call/input.json")["images"])
            self.assertEqual(load(run / "state.json")["config"]["workflow"], "single_planner_trace")

    def test_early_settlement_resume_is_immutable_with_every_override(self):
        from planner_harness import PlannerHarness
        from planner_harness.common import sha
        from test_low_high import video
        import test_creative_loop as fixtures

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.avi"
            video(source)
            fixture = fixtures.CreativeTests(
                "test_waiting_resume_does_not_duplicate_job_or_call_model"
            )
            fixture.root = root
            fixture.source = source
            fixture.start()
            fixture.respond()
            fixture.resume(
                [
                    fixtures.action("finish", video="v1", message="Propose after report."),
                    fixtures.action(
                        "finish", video="v1", message="Confirm after the complete report."
                    ),
                ]
            )
            run = fixture.h.output
            before = sha(run / "state.json")
            state = PlannerHarness(run, None).resume(
                continue_delivery=True, additional_turns=20, max_context_chars=8192
            )
            self.assertEqual(state["status"], "complete")
            self.assertEqual(before, sha(run / "state.json"))

    def test_service_known_unsubmitted_deadline_rolls_back_planner_slot(self):
        from server_runtime.service import Service
        from server_runtime.queue import Queue
        from planner_harness.common import save
        from planner_harness.execution import signature
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            budget = {
                "version": a.VERSION,
                "mode": "offline",
                "online_task_budget": {
                    "version": "online-task-v2",
                    "lanes": ["full"],
                    "max_generations": 1,
                    "wall_seconds": 1,
                },
            }
            ar = a.install(root / "accounting", budget)
            binding = a.scope(ar, "t", "full")
            clock = a.start_task(binding, wall_seconds=1)
            run = root / "run"
            state = {
                "config": {
                    "workflow": "creative_loop_v1",
                    "resource_policy": {"version": "creative-resources-v2"},
                },
                "submitted_generation_ids": [],
                "generation_requests": 0,
                "online_clock": clock,
            }
            save(run / "state.json", state)
            body = {
                "id": "j",
                "kind": "generate",
                "mode": "live",
                "accounting_scope": binding,
                "payload": {"renderer": {"backend": "fixture"}, "input": {}, "prompt": "Blue."},
            }
            request = {**body, "sha256": signature(body)}
            path = run / "jobs/j/request.json"
            save(path, request)

            class Renderer:
                requires_live_budget = False

                def prepare(self, *args):
                    pass

                def __call__(self, *args):
                    raise AssertionError("must not render")

            service = Service(
                Queue(root / "queue.db", {"gpu": 1, "llm": 1, "cpu": 1}),
                root / "service",
                ROOT,
                {
                    "workflow": "creative_loop_v1",
                    "budget": budget,
                    "accounting_root": str(ar),
                    "renderer": {"backend": "fixture"},
                },
                renderer=Renderer(),
            )

            def slow_save(target, value):
                if Path(target).name == "render-started.json":
                    time.sleep(1.05)
                return save(target, value)

            with patch("server_runtime.service.save", side_effect=slow_save):
                result = service(
                    {
                        "kind": "tool",
                        "payload": {"request": str(path), "request_sha256": request["sha256"]},
                    },
                    root / "job",
                )
            self.assertEqual(result["response"]["status"], "failed")
            current = load(run / "state.json")
            self.assertEqual(current["generation_requests"], 0)
            self.assertEqual(current["submitted_generation_ids"], [])
            self.assertEqual(a.operation(binding, request["sha256"])["status"], "not_submitted")
            self.assertEqual(a.summary(ar)["reserved_or_settled_totals"]["render_requests"], 0)

    def test_qualitative_online_and_formal_final_schemas_remain_separate(self):
        from critic_harness.one_shot import frozen_profile, PROTOCOL, validate_report
        from evaluation.low_high import profile

        online = frozen_profile()["rubric"]
        final = profile()["rubric"]
        self.assertIn("summary", online)
        self.assertIn("observe", online)
        self.assertNotIn("task_diagnostics", online)
        self.assertNotIn("main_scores", online)
        self.assertIn("main_scores", final)
        packet = {"user_text": json.dumps({"protocol_id": PROTOCOL, "candidate_id": "v1"})}
        report = {
            "summary": "The inspected scene serves the task.",
            "findings": ["A concrete visible relationship."],
        }
        self.assertEqual(validate_report(report, packet), report)
        with self.assertRaises(ValueError):
            validate_report({"summary": ""}, packet)

    def test_renderer_process_deadline_releases_only_its_owned_lock(self):
        import multiprocessing, subprocess
        from server_runtime.renderers import ProcessRenderer
        from planner_harness.owned_process import birth
        from planner_harness.lock import RunLock

        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent, child = context.Pipe()
            proc = context.Process(target=fake_renderer_owner, args=(child, str(root / "gpu")))
            proc.start()
            parent.recv()
            renderer = object.__new__(ProcessRenderer)
            renderer.process = proc
            renderer.connection = parent
            renderer.birth = birth(proc.pid)
            unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(20)"])
            try:
                with self.assertRaises(RuntimeError):
                    with RunLock(root / "gpu"):
                        pass
                policy = {
                    "version": a.VERSION,
                    "mode": "offline",
                    "online_task_budget": {
                        "version": "online-task-v2",
                        "lanes": ["full"],
                        "max_generations": 1,
                        "wall_seconds": 1,
                    },
                }
                budget = a.install(root / "accounting", policy)
                binding = a.scope(budget, "t", "full")
                a.start_task(binding, wall_seconds=1)
                with self.assertRaises(r.ResourceExhausted):
                    a.invoke(binding, "j", "render", "fixture", lambda: renderer({}, root))
                self.assertFalse(proc.is_alive())
                self.assertIsNone(unrelated.poll())
                with RunLock(root / "gpu"):
                    pass
                end = time.monotonic() + 2
                while a.active(budget) and time.monotonic() < end:
                    time.sleep(0.01)
            finally:
                if proc.is_alive():
                    proc.kill()
                    proc.join()
                unrelated.terminate()
                unrelated.wait()

    def test_large_qualitative_review_remains_exactly_readable_and_images_reopen(self):
        import test_review_modes as fixtures
        from planner_harness.common import sha
        from planner_harness.creative_actions import history
        from planner_harness.working_memory import estimate

        case = fixtures.ReviewModes()
        case.setUp()
        try:
            case.start()
            case.render()
            report = {
                "summary": "A concrete reported observation. " * 2400,
                "findings": ["One unchanged original finding."],
            }
            _, _, feedback = case.review(
                fixtures.Reviewer([{"action": "review", "arguments": report}])
            )
            case.h.state["config"]["max_context_chars"] = 24000
            text, images, mapping = case.h.context()
            visible = json.loads(text)
            key = next(reversed(case.h.state["evaluations"]))
            self.assertIn("page", visible["evaluations"][key])
            self.assertLessEqual(len(case.h.system) + len(text), 24000)
            self.assertLessEqual(
                estimate(case.h.system, text, len(images))["total_estimated"], 100000
            )
            lines = {}
            start, char = 1, 0
            while True:
                result = history(case.h, {"feedback": key, "start_line": start, "start_char": char})
                for line in result["text"].splitlines():
                    number, fragment = line.split(": ", 1)
                    lines[int(number)] = lines.get(int(number), "") + fragment
                if result["next_line"] is None:
                    break
                start, char = result["next_line"], result["next_char"]
            self.assertEqual(json.loads("\n".join(lines[i] for i in sorted(lines))), feedback)
            observation = case.h.state["observations"][-1]
            reopened = case.h.observe(
                {"observation": observation["observation_id"]}, "reopen-review-fixture"
            )
            self.assertEqual(reopened["frames"], observation["frames"])
            self.assertTrue(all(sha(row["path"]) == row["sha256"] for row in reopened["frames"]))
        finally:
            case.tearDown()

    def test_online_engine_deadline_freezes_task_and_quarantines_only_its_owner(self):
        import test_creative_loop as fixtures
        from test_low_high import video
        from planner_harness.common import sha
        from planner_harness.delivery import verify_settlement
        from planner_harness.lock import RunLock
        from server_runtime.queue import Queue
        from server_runtime.service import Service
        from server_runtime.engine import Engine

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.avi"
            video(source)
            policy = {
                "version": a.VERSION,
                "mode": "offline",
                "online_task_budget": {
                    "version": "online-task-v2",
                    "lanes": ["full", "none"],
                    "max_generations": 1,
                    "wall_seconds": 2,
                },
            }
            ar = a.install(root / "accounting", policy)
            release = threading.Event()
            calls = []
            device = root / "owned-device"

            def stuck(job, folder):
                with RunLock(device):
                    calls.append(job["id"])
                    release.wait(12)
                return {"fixture": "late owned outcome only"}

            config = {"workflow": "creative_loop_v1", "accounting_root": str(ar), "budget": policy}
            models = [
                fixtures.Scripted(
                    [fixtures.action("generate", input_video="source", prompt="Blue.")]
                ),
                fixtures.Scripted(
                    [fixtures.action("finish", video="source", stop_reason="no_promising_attempt")]
                ),
            ]
            first = root / "worker-a"
            second = root / "worker-b"
            qa = Queue(first / "queue.db", {"gpu": 1, "llm": 1, "cpu": 1})
            qb = Queue(second / "queue.db", {"gpu": 1, "llm": 1, "cpu": 1})
            sa = Service(
                qa, first, ROOT, config, model_factory=lambda role: models[0], renderer=stuck
            )
            sb = Service(
                qb, second, ROOT, config, model_factory=lambda role: models[1], renderer=object()
            )
            base = {
                "workflow": "creative_loop_v1",
                "source": str(source),
                "source_sha256": sha(source),
                "request": "Make blue.",
                "budget_topic": "same",
                "execution": {
                    "mode": "live",
                    "renderer": {"backend": "fixture"},
                    "resource_policy": {"max_wall_seconds": 2},
                },
            }
            try:
                sa.submit({**copy.deepcopy(base), "id": "a", "budget_lane": "full"})
                started = time.monotonic()
                Engine(qa, first, sa, sa.expand, interval=0.01).run(once=True)
                self.assertLess(time.monotonic() - started, 5)
                run = first / "tasks/a/run"
                state = load(run / "state.json")
                before = sha(run / "state.json")
                self.assertEqual(verify_settlement(run)["outcome"], "budget_exhausted")
                self.assertTrue(state["pending_tool"])
                self.assertTrue(state["resource_ownership_unknown"])
                self.assertEqual(len(models[0].inputs), 1)
                self.assertEqual(len(calls), 1)
                self.assertTrue(sa.resources_unknown())
                with self.assertRaises(a.ExternalExecutionUnknown):
                    sa.ensure_ready()
                with self.assertRaises(RuntimeError):
                    with RunLock(device):
                        pass
                # Same accounting root and topic, distinct owner/lane: worker B proceeds.
                sb.submit({**copy.deepcopy(base), "id": "b", "budget_lane": "none"})
                Engine(qb, second, sb, sb.expand, interval=0.01).run(once=True)
                self.assertEqual(
                    load(second / "tasks/b/run/state.json")["status"], "delivery_blocked"
                )
                self.assertEqual(len(models[1].inputs), 1)
                self.assertFalse(sb.resources_unknown())
                self.assertFalse((second / "resources-retained.json").exists())
                self.assertEqual(sha(run / "state.json"), before)
                release.set()
                end = time.monotonic() + 3
                while a.active(ar) and time.monotonic() < end:
                    time.sleep(0.01)
                self.assertEqual(sha(run / "state.json"), before)
                self.assertEqual(verify_settlement(run)["outcome"], "budget_exhausted")
            finally:
                release.set()
                end = time.monotonic() + 3
                while a.active(ar) and time.monotonic() < end:
                    time.sleep(0.01)


if __name__ == "__main__":
    unittest.main()
