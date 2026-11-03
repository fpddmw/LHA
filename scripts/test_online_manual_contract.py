"""Exercise shipped instructions/configuration against the offline creative runtime."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness import PlannerHarness
from planner_harness.common import load, save, sha
from planner_harness.creative_knowledge import CreativeKnowledge
from critic_harness.adapter import critique
from critic_harness import one_shot
from evaluation import registry
import test_creative_loop as fixtures
from test_low_high import video


class ManualContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.avi"
        video(self.source)
        self.profile = load(ROOT / "configs/creative-loop-v1.json")
        self.guide = ROOT / "knowledge/creative-loop/OBSERVE_EVENTS.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_shipped_profile_and_documented_operations_in_both_scopes(self):
        examples = [json.loads(text) for text in re.findall(r"```json\s*(.*?)```", self.guide.read_text(), re.S)]
        self.assertEqual([e["action"] for e in examples], ["observe", "generate"])
        systems = []
        for mode in ("full", "none"):
            with self.subTest(mode=mode):
                model = fixtures.Scripted([
                    fixtures.action("read", targets=[{"id": "observe-events", "max_chars": 8000}]),
                    fixtures.action("generate", input_video="source", prompt="Make the scene blue."),
                ])
                h = PlannerHarness(self.root / mode, model)
                h.start(self.source, "Make the scene blue.", mode="loop", workflow=self.profile["workflow"],
                        execution={"mode": "replay", "experience_mode": mode, "critic": self.profile["critic"]})
                self.assertEqual(h.state["config"]["execution"]["critic"]["protocol"], one_shot.PROTOCOL)
                systems.append(h.system)
                frozen = load(h.output / "knowledge-snapshot.json")
                doc = frozen["documents"][str(self.guide.relative_to(ROOT))]
                self.assertEqual(doc["sha256"], sha(self.guide))
                def visible_strings(value):
                    if isinstance(value, str):
                        yield value.strip()
                    elif isinstance(value, dict):
                        for child in value.values():
                            yield from visible_strings(child)
                    elif isinstance(value, list):
                        for child in value:
                            yield from visible_strings(child)
                self.assertIn(h.knowledge.read("observe-events", max_chars=8000)["text"].strip(), list(visible_strings(json.loads(model.inputs[1]["user_text"]))))
                job = h.state["jobs"][h.state["pending_tool"]]
                save(h.output / "jobs" / job["id"] / "response.json", {
                    "request_sha256": job["sha256"], "mode": "replay", "status": "complete",
                    "payload": {"video": {"path": str(self.source), "sha256": sha(self.source)},
                        "replay_provenance": "Synthetic software fixture; no rendering.",
                        "execution": {"requested_prompt": job["payload"]["prompt"],
                            "effective_prompt": job["payload"]["prompt"],
                            "input_sha256": job["payload"]["input"]["sha256"]}}})
                fixtures.drain_review(h)
                model = fixtures.Scripted(examples)
                h = PlannerHarness(h.output, model)
                h.resume()
                observed = [o for o in h.state["observations"] if o.get("mode") == "continuous"][-1]
                self.assertEqual(observed["video_id"], "v1")
                self.assertTrue(observed["next_arguments"])
                self.assertFalse(observed["coverage"]["complete"])
                attached = json.loads(model.inputs[1]["user_text"])["attached_images_in_order"]
                self.assertTrue({f["sha256"] for f in observed["frames"]} <= {f["sha256"] for f in attached})
                # New generate carries review_focus; the next successful render queues the focused review.
                fixture=type('Fixture',(),{})();fixture.h=h;fixture.source=self.source
                fixtures.CreativeTests.respond(fixture,review=False)
                from planner_harness.execution import collect
                collect(h)
                job = h.state["jobs"][h.state["pending_tool"]]
                self.assertEqual(job["payload"]["events"], examples[1]["arguments"]["review_focus"]["events"])
                critic = fixtures.ScriptedCritic()
                result = critique(job, h.output / "jobs" / job["id"], ROOT, model=critic)
                requested = json.loads(critic.inputs[0]["user_text"])["requested_events"]
                self.assertEqual(requested, examples[1]["arguments"]["review_focus"]["events"])
                self.assertEqual(result["protocol"], one_shot.PROTOCOL)
                self.assertTrue(result["report"]["summary"])
        # Scopes differ in knowledge, while model-visible operation contracts match.
        def common(text):
            return re.findall(r"^- `.*$", text, re.M)
        self.assertEqual(common(systems[0]), common(systems[1]))

    def test_guide_is_discoverable_and_snapshot_readable_without_experience(self):
        paths = []
        for mode in ("full", "none"):
            with self.subTest(mode=mode):
                knowledge = CreativeKnowledge(ROOT, experience_mode=mode)
                self.assertIn("observe-events", knowledge.read("map")["text"])
                paths.append(knowledge.resolve("observe-events")[1])
                snapshot = self.root / (mode + ".json")
                knowledge.freeze(snapshot)
                resumed = CreativeKnowledge(ROOT, snapshot)
                text = resumed.read("observe-events", max_chars=8000)["text"]
                self.assertEqual(re.sub(r"^\d+: ?", "", text, flags=re.M).strip(), self.guide.read_text().strip())
                if mode == "none":
                    self.assertEqual(resumed.curated_catalog["entries"], [])
        self.assertEqual(paths[0], paths[1])

    def test_prompt_writing_reaches_generate_with_reads_and_review_in_existing_calls(self):
        """Check instruction/evidence delivery and dispatch, not model writing quality."""
        guide = ROOT / "knowledge/creative-loop/PROMPT_WRITING.md"
        for mode in ("full", "none"):
            with self.subTest(mode=mode):
                ids = ["theme"] + (["EX-P-medium-logic"] if mode == "full" else [])
                model = fixtures.Scripted([
                    fixtures.action("read", targets=[{"id": identity} for identity in ids]),
                    fixtures.action("generate", input_video="source", prompt="Blue light falls across the scene."),
                ])
                h = PlannerHarness(self.root / ("writing-" + mode), model)
                h.start(self.source, "Make the scene blue.", mode="loop", workflow="creative_loop_v1",
                        execution={"mode": "replay", "experience_mode": mode})
                frozen_system = h.system
                self.assertEqual(len(model.inputs), 2)
                self.assertEqual(frozen_system.count(guide.read_text()), 1)
                snapshot = load(h.output / "knowledge-snapshot.json")
                self.assertEqual(snapshot["documents"][str(guide.relative_to(ROOT))]["text"], guide.read_text())
                self.assertIn("prompt-writing", h.knowledge.items)

                fixture = type("Fixture", (), {"h": h, "source": self.source})()
                fixtures.CreativeTests.respond(fixture)
                revised = "Soft blue light grazes the foreground; deeper blue shadows separate the background."
                model = fixtures.Scripted([fixtures.action("generate", input_video="v1", prompt=revised)])
                h = PlannerHarness(h.output, model)
                h.resume()
                self.assertEqual(len(model.inputs), 1)
                self.assertEqual(model.inputs[0]["system_prompt"], frozen_system)
                context = json.loads(model.inputs[0]["user_text"])
                self.assertEqual([r["material"]["id"] for r in context["working_memory"]["retained_reads"]], ids)
                latest = next(reversed(h.state["evaluations"]))
                self.assertEqual(context["evaluations"][latest]["report"], h.state["evaluations"][latest]["report"])
                job = h.state["jobs"][h.state["pending_tool"]]
                self.assertEqual(job["payload"]["prompt"], revised)
                self.assertEqual(job["payload"]["input_id"], "v1")

                fixture.h = h
                fixtures.CreativeTests.respond(fixture)
                jobs_before_delivery = len(h.state["jobs"])
                model = fixtures.Scripted([fixtures.action("finish", video="v2", message="Use the revised lighting.")])
                h = PlannerHarness(h.output, model)
                h.resume()
                self.assertEqual(len(model.inputs), 1)
                self.assertEqual(len(h.state["jobs"]), jobs_before_delivery)
                self.assertEqual(h.state["status"], "complete")

    def test_generated_legacy_metric_reference_matches_source(self):
        self.assertEqual((ROOT / "docs/evaluation-metrics.md").read_text(), registry.markdown())


if __name__ == "__main__":
    unittest.main()
