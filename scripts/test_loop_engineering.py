"""Current loop/Service regressions; scripted APIs and renderers, no paid calls or GPUs."""

import copy, json, sys, threading, time, unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import test_planner_harness as legacy
import test_review_modes as review
from planner_harness.common import load, save, sha
from planner_harness import accounting as a
from planner_harness.delivery import verify_delivery
from planner_harness.model_call import ModelTransportError
from server_runtime.service import Service
from server_runtime.queue import Queue
from server_runtime.engine import Engine


class APIPlanner(review.Planner):
    is_live_api = True
    requires_live_budget = False

    def predict_text(self, **kwargs):
        self.last_usage = {"total_tokens": 50001, "provider_responses": 1}
        return super().predict_text(**kwargs)


class Renderer:
    def __init__(self, source):
        self.source = Path(source)
        self.calls = []
        self.closed = False

    def __call__(self, job, directory):
        self.calls.append(job["id"])
        p = job["payload"]
        return {
            "video": {"path": str(self.source), "sha256": sha(self.source)},
            "execution": {
                "requested_prompt": p["prompt"],
                "effective_prompt": p["prompt"],
                "input_sha256": p["input"]["sha256"],
                "seed": p["renderer"]["seed"],
                "settings": p["renderer"].get("generation", {}),
                "preflight": "passed",
                "model_revision": "software-fixture",
                "code_revision": "software-fixture",
                "token_count": 1,
                "token_limit": 512,
            },
        }

    def close(self):
        self.closed = True


class ProbeService(Service):
    def __call__(self, job, directory):
        if job["kind"] == "probe":
            return {"topic": job["payload"]["task"]["id"]}
        return super().__call__(job, directory)


class Engineering(unittest.TestCase):
    setUp, tearDown = legacy.Tests.setUp, legacy.Tests.tearDown
    start = review.ReviewModes.start
    render = review.ReviewModes.render
    resume = review.ReviewModes.resume
    check = review.ReviewModes.check

    def service(
        self, actions, *, mode="critic", critic=None, directory=None, config=None, kind=Service
    ):
        folder = directory or self.root / "service"
        queue = Queue(folder / "queue.sqlite3")
        renderer = Renderer(self.source)
        planner = APIPlanner(actions)
        critic = critic or review.Reviewer()
        factory = lambda role: planner if role == "planner" else critic
        settings = {
            "workflow": "creative_loop_v1",
            "review": {"mode": mode},
            "planner": {"model": planner.model, "reasoning_effort": planner.reasoning_effort},
            "critic": {"model": critic.model, "reasoning_effort": critic.reasoning_effort},
            **(config or {}),
        }
        service = kind(queue, folder, ROOT, settings, model_factory=factory, renderer=renderer)
        return service, queue, renderer, planner

    def task(self, identity="topic", n=5, execution=None):
        return {
            "id": identity,
            "source": str(self.source),
            "source_sha256": sha(self.source),
            "request": "Make the scene blue.",
            "max_generations": n,
            "max_turns": 1,
            "execution": {
                "mode": "live",
                "renderer": {"backend": "bernini", "generation": {}, "seed": 42},
                **(execution or {}),
            },
        }

    def test_planner_overload_retries_same_event_without_repeating_render(self):
        from vlm.chatgpt_subscription import SubscriptionAPIError

        service, queue, renderer, planner = self.service([
            review.action("generate", input_video="source", prompt="Make blue."),
            SubscriptionAPIError(503, "server_is_overloaded", retry_after=0),
            review.action("finish", video="v1", message="Select the reviewed result."),
        ])
        service.submit(self.task())
        Engine(queue, service.directory, service, service.expand, interval=0.005).run(once=True)
        run = service.directory / "tasks/topic/run"
        self.assertEqual(verify_delivery(run)["selected"], "v1")
        self.assertEqual(len(renderer.calls), 1)
        self.assertEqual(planner.inputs[-2], planner.inputs[-1])
        self.assertEqual(load(run / "calls/event-0002/transport/returned.json")["attempt"], 2)

    def test_known_critic_transport_failure_resumes_dependent_planner(self):
        critic = review.Reviewer(
            [ModelTransportError("Known rejected fixture API request", retryable=False)]
        )
        service, queue, renderer, planner = self.service(
            [
                review.action("generate", input_video="source", prompt="Make blue."),
                review.action(
                    "finish",
                    video="v1",
                    message="I choose this result after inspecting the review.",
                ),
            ],
            critic=critic,
        )
        service.submit(self.task())
        Engine(queue, service.directory, service, service.expand, interval=0.005).run(once=True)
        state = load(service.directory / "tasks/topic/run/state.json")
        self.assertEqual(state['status'],'waiting_tool')
        self.assertFalse(state.get('final'))
        self.assertEqual(len(planner.inputs),1)
        critic.actions.extend(review.Reviewer().actions)
        run = service.directory / "tasks/topic/run"
        call = next((run / 'jobs' / state['pending_tool']).rglob('allowance.json')).parent
        from planner_harness.model_call import reopen_call
        reopen_call(call, 'Critic provider access restored.', 1)
        Engine(queue, service.directory, service, service.expand, interval=0.005).run(once=True)
        state = load(service.directory / "tasks/topic/run/state.json")
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["reviews"]["v1"]["status"], "complete")
        self.assertEqual({r["state"] for r in queue.rows()}, {"complete"})
        self.assertEqual(len(critic.inputs), 2)
        self.assertNotIn('Known rejected fixture API request',json.dumps(planner.inputs))
        self.assertEqual(len(planner.inputs), 2)
        self.assertEqual(len(renderer.calls), 1)
        self.assertEqual(verify_delivery(service.directory / "tasks/topic/run")["selected"], "v1")

    def test_default_service_crosses_old_model_caps_and_honors_task_n(self):
        actions = [
            review.action("note", text="A bounded scripted planning observation.")
            for _ in range(101)
        ]
        actions.append(
            review.action(
                "finish",
                stop_reason="no_promising_attempt",
                message="Software fixture completed without rendering.",
            )
        )
        service, queue, renderer, planner = self.service(actions, mode="planner")
        service.submit(self.task(n=9))
        Engine(queue, service.directory, service, service.expand, interval=0.005).run(once=True)
        run = service.directory / "tasks/topic/run"
        state = load(run / "state.json")
        binding = load(run / "budget-scope.json")
        policy = load(Path(binding["root"]) / "policy.json")
        totals = a.summary(binding["root"])["reserved_or_settled_totals"]
        self.assertEqual(state["status"], "delivery_blocked")
        self.assertEqual(len(planner.inputs), 102)
        self.assertGreater(totals["model_calls"], 96)
        self.assertGreater(totals["tokens"], 4000000)
        self.assertEqual(policy["mode"], "live")
        self.assertEqual(policy["online_task_budget"]["max_generations"], 9)
        self.assertIsNone(policy["online_task_budget"]["wall_seconds"])
        self.assertEqual(binding["topic"], "topic")
        self.assertFalse((service.directory / "accounting/ledger.json").exists())
        self.assertFalse(renderer.calls)

    def test_critic_reuses_shorter_frozen_task_clock(self):
        from planner_harness.video import Video
        from critic_harness.one_shot import frozen_profile, run_review

        directory = self.root / "short"
        model = review.Reviewer()
        model.is_live_api = True
        binding = a.default_api_scope(directory, model, wall_seconds=2)
        a.start_task(binding)
        model = a.attach(model, binding)
        info = Video(self.source, self.root / "video").info
        result = run_review(
            {
                "request": "Make blue.",
                "video_id": "v1",
                "videos": {"source": info, "v1": info},
                "critic": {"frozen_profile": frozen_profile(model.model, model.reasoning_effort)},
            },
            directory,
            model,
        )
        self.assertEqual(
            result["report"]["summary"],
            "The actual visible result serves the requested blue treatment.",
        )
        clock = a.start_task(binding)
        self.assertEqual(clock, a.start_task(binding))
        self.assertAlmostEqual(clock["deadline_unix"] - clock["started_unix"], 2)

    def unknown(self, service, root, kind, topic):
        binding = a.scope(root, topic, "full")
        a.start_task(binding)
        release = threading.Event()
        done = threading.Event()

        def work():
            release.wait(10)
            done.set()
            return {"late": True}

        with self.assertRaises(a.ResourceExhausted):
            a.invoke(
                binding, topic + "-" + kind, kind, "fixture", work, owner=str(service.directory)
            )
        self.addCleanup(release.set)

        def cleanup():
            release.set()
            done.wait(3)
            until = time.monotonic() + 3
            while a.active(root) and time.monotonic() < until:
                time.sleep(0.01)

        self.addCleanup(cleanup)
        return release

    def test_unknown_llm_does_not_quarantine_recoverable_text_work(self):
        policy = a.default_online_policy(wall_seconds=1, lanes=("full",))
        service, queue, renderer, _ = self.service([], kind=ProbeService, config={"budget": policy})
        self.unknown(service, service.accounting_root, "model", "held")
        first = queue.enqueue("held", "probe", "gpu", {"task": {"id": "held"}})
        second = queue.enqueue("healthy", "probe", "gpu", {"task": {"id": "healthy"}})
        engine = Engine(queue, service.directory, service, service.expand, interval=0.005)
        engine.run(once=True)
        rows = {r["id"]: r for r in queue.rows()}
        self.assertEqual(rows[first]["state"], "complete")
        self.assertEqual(rows[second]["state"], "complete")
        self.assertFalse(engine.stop.is_set())
        self.assertTrue(renderer.closed)

    def test_unknown_gpu_blocks_this_owner_but_other_worker_with_shared_ledger_runs(self):
        policy = a.default_online_policy(wall_seconds=1, lanes=("full",))
        shared = self.root / "shared-accounting"
        a.install(shared, policy)
        first, q1, r1, _ = self.service(
            [],
            directory=self.root / "worker1",
            kind=ProbeService,
            config={"budget": policy, "accounting_root": str(shared)},
        )
        second, q2, r2, _ = self.service(
            [],
            directory=self.root / "worker2",
            kind=ProbeService,
            config={"budget": policy, "accounting_root": str(shared)},
        )
        self.unknown(first, shared, "render", "held-gpu")
        q1.enqueue("next1", "probe", "gpu", {"task": {"id": "healthy1"}})
        q2.enqueue("next2", "probe", "gpu", {"task": {"id": "healthy2"}})
        Engine(q1, first.directory, first, first.expand, interval=0.005).run(once=True)
        Engine(q2, second.directory, second, second.expand, interval=0.005).run(once=True)
        self.assertEqual(q1.rows()[0]["state"], "queued")
        self.assertEqual(q2.rows()[0]["state"], "complete")
        self.assertFalse(r1.closed)
        self.assertTrue(r2.closed)
        self.assertTrue(first.gpu_unknown())
        self.assertFalse(second.gpu_unknown())

    def test_modern_planner_transport_recovery_uses_original_answer_once(self):
        finish = review.action(
            "finish", video="v1", message="Accept the result after its contextual check."
        )
        finish["review"] = {
            "video_id": "v1",
            "summary": "I checked the generated software-fixture result.",
        }
        service, queue, renderer, planner = self.service(
            [review.action("generate", input_video="source", prompt="Make blue."), finish],
            mode="planner",
        )
        service.submit(self.task())
        job = queue.claim("llm", "interrupted-owner")
        engine = Engine(queue, service.directory, service, service.expand, interval=0.005)
        with patch("planner_harness.runner.PlannerHarness.operate", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                engine.execute(job)
        run = service.directory / "tasks/topic/run"
        before = load(run / "state.json")
        self.assertIsNotNone(before["pending_event"])
        self.assertEqual(len(planner.inputs), 1)
        Engine(queue, service.directory, service, service.expand, interval=0.005).run(once=True)
        self.assertEqual(load(run / "state.json")["status"], "complete")
        self.assertEqual(len(planner.inputs), 2)
        self.assertEqual(len(renderer.calls), 1)
        self.assertEqual(verify_delivery(run)["selected"], "v1")

    def test_valid_self_review_survives_invalid_next_action(self):
        self.start(mode="planner")
        self.render()
        invalid = review.action(
            "generate", input_video="missing", prompt="Make another blue result."
        )
        invalid["review"] = self.check(
            summary="A useful completed check survives the next input correction."
        )
        state = self.resume(
            [invalid, review.action("finish", video="v1", message="Deliver the checked result.")]
        )
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["reviews"]["v1"]["event_id"], "event-0002")
        self.assertEqual(state["generation_requests"], 1)
        self.assertTrue(any(e["status"] == "operation_error" for e in state["events"]))
        self.assertEqual(verify_delivery(self.h.output)["selected"], "v1")

    def test_review_action_in_critic_mode_returns_normal_correction(self):
        self.model = review.Planner(
            [
                review.action("review", summary="An early check without a candidate."),
                review.action("generate", input_video="source", prompt="Make blue."),
            ]
        )
        from planner_harness import PlannerHarness

        self.h = PlannerHarness(self.root / "run", self.model)
        state = self.h.start(
            self.source,
            "Make blue.",
            workflow="creative_loop_v1",
            mode="loop",
            execution={"mode": "replay"},
        )
        self.assertEqual(state["status"], "waiting_tool")
        self.assertEqual(state["events"][0]["status"], "operation_error")
        self.assertEqual(len(self.model.inputs), 2)

    def test_delivery_mutable_copies_cannot_replace_original_transport_answer(self):
        self.start(mode="planner")
        self.render()
        finish = {
            **review.action("finish", video="v1", message="Original choice."),
            "review": self.check(),
        }
        self.resume([finish])
        state = load(self.h.output / "state.json")
        event = state["final"]["delivery_review"]["planner_event_id"]
        call = self.h.output / "calls" / event
        changed = load(call / "transport/input.json")
        response = json.loads((call / "response.txt").read_text())
        response["arguments"]["message"] = "A fabricated replacement."
        text = json.dumps(response)
        (call / "response.txt").write_text(text)
        (call / "transport/response.txt").write_text(text)
        returned = load(call / "transport/returned.json")
        returned["sha256"] = sha(call / "response.txt")
        save(call / "transport/returned.json", returned)
        state["final"]["message"] = response["arguments"]["message"]
        save(self.h.output / "state.json", state)
        save(self.h.output / "final.json", state["final"])
        with self.assertRaisesRegex(ValueError, "original returned"):
            verify_delivery(self.h.output)

    def test_online_service_renderer_imports_do_not_load_formal_evaluation(self):
        import subprocess

        code = "import sys; from server_runtime.service import Service; from server_runtime.renderers import ProcessRenderer; assert not any(k=='evaluation' or k.startswith('evaluation.') for k in sys.modules)"
        env = __import__("os").environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-B", "-c", code], env=env, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
