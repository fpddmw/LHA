"""CPU-only frame, evaluation-source and count-budget regression checks."""
import sys
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from experiments import video_contract as vc, results
from planner_harness.common import sha, load, save
from planner_harness import accounting as a, resources, continuation
from planner_harness.video import Video
from test_unified_results import Fixture


def write_video(path, count, fps):
    import av
    import numpy as np
    with av.open(str(path), "w") as container:
        stream = container.add_stream("libx264", rate=fps)
        stream.width = stream.height = 32
        stream.pix_fmt = "yuv444p"
        stream.options = {"crf": "0"}
        for i in range(count):
            frame = av.VideoFrame.from_ndarray(np.full((32, 32, 3), i % 256, dtype=np.uint8), format="rgb24")
            for packet in stream.encode(frame): container.mux(packet)
        for packet in stream.encode(): container.mux(packet)


class FrameTests(unittest.TestCase):
    def test_whole_clip_endpoints_repetition_and_subsampling(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for count, fps in ((9, 10), (120, 30), (241, 24), (117, 24)):
                source = folder / f"{count}.mp4"
                write_video(source, count, fps)
                digest = sha(source)
                info = {k: Video(source, folder / "info").info[k] for k in ("frames", "fps", "width", "height")}
                output, receipt = vc.normalize(source, folder / "normalized", info)
                actual = Video(output, folder / "check").info
                self.assertEqual((actual["frames"], actual["fps"]), (117, 24))
                self.assertEqual(receipt["source_indices"], vc.sample_indices(count))
                self.assertEqual((receipt["source_indices"][0], receipt["source_indices"][-1]), (0, count-1))
                independent, _ = vc.normalize(source, folder / "independent", info)
                self.assertEqual(sha(independent), sha(output))
                self.assertEqual(sha(source), digest)
                self.assertEqual(vc.normalize(source, folder / "normalized", info), (output, receipt))
                import av
                with av.open(str(source)) as f: original = list(f.decode(video=0))
                with av.open(str(output)) as f: normalized = list(f.decode(video=0))
                for old, new in ((original[0], normalized[0]), (original[-1], normalized[-1])):
                    self.assertLessEqual(abs(float(old.to_ndarray(format="rgb24").mean()) - float(new.to_ndarray(format="rgb24").mean())), 2)


class PipelineTests(Fixture):
    def test_normalized_source_flows_through_registration_scoring_and_export(self):
        write_video(self.source, 9, 10)
        for row in self.rows: row["source_video_sha256"] = sha(self.source)
        save(self.repo / "benchmark_data/benchmark.json", self.rows)
        batch = self.prepare(methods=["direct"], splits=["train"], prompt_forms=["short"])
        topic = batch["topics"][0]
        source = (self.repo / topic["source"]).resolve()
        self.assertNotEqual(topic["source_sha256"], sha(self.source))
        entry = results.import_video(self.repo, self.registry, self.row(
            video=str(source), video_sha256=sha(source), source=str(source), source_sha256=sha(source),
            original_source_sha256=sha(self.source), normalization=topic["normalization"]))
        with self.assertRaisesRegex(ValueError, "117 frames"):
            results.import_video(self.repo, self.registry, self.row(
                source=str(source), source_sha256=sha(source), normalization=topic["normalization"],
                original_source_sha256=sha(self.source), method="pe"))
        results.prepare_evaluation(self.repo, self.registry, evaluation_id="uniform")
        from evaluation.creative import JUDGES
        from evaluation.low_high import PROTOCOL, profile
        seen = []
        def judge(request, original, candidate, directory, *, model, plan):
            seen.append((original["frames"], original["fps"], original["sha256"]))
            return {"source_sha256": original["sha256"], "output_sha256": candidate["sha256"],
                    "model": model.model, "profile_sha256": profile()["sha256"],
                    "report": {"protocol_id": PROTOCOL, "main_scores": {}}}
        models = {j: SimpleNamespace(model=j, reasoning_effort=None, requires_live_budget=False) for j in JUDGES}
        with patch("evaluation.creative.judge_candidate", side_effect=judge), patch("evaluation.final_suite.automatic", return_value={"metrics": {}}):
            results.score_evaluation(self.repo, self.registry, None, models=models)
        self.assertEqual(seen, [(117, 24, topic["source_sha256"])] * len(JUDGES))
        save(self.output / "host.json", {"devices": [0]})
        export = results.export_shard(self.repo, self.registry, self.output, self.root / "export")
        imported = results.import_manifest(self.repo, self.root / "import", export)[0]
        self.assertEqual(imported["normalization"], entry["normalization"])
        self.assertEqual(sha(self.root / "import" / imported["source"]), topic["source_sha256"])


class BudgetTests(unittest.TestCase):
    def test_elapsed_time_does_not_stop_calls_and_fifth_render_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            policy = a.default_online_policy(max_generations=4)
            self.assertIsNone(policy["max_call_seconds"])
            binding = a.scope(a.install(folder / "accounting", policy), "task", lane="full")
            clock = a.start_task(binding)
            self.assertIsNone(clock["deadline_unix"])
            with patch("time.time", return_value=clock["started_unix"] + 864000):
                a.check_task(binding)
                self.assertEqual(a.bounded_preflight(binding, "preflight", lambda: 7), 7)
                for n in range(4):
                    a.reserve(binding, f"render-{n}", "render", "render:bernini")
                with self.assertRaises(a.SubmissionRefused):
                    a.reserve(binding, "render-5", "render", "render:bernini")
                # Non-render work remains available after all render slots are used.
                model = SimpleNamespace(model="fixture", reasoning_effort=None, predict_text=lambda **kw: "{}")
                model = a.attach(model, binding)
                from planner_harness.model_call import call_text
                self.assertEqual(call_text(folder / "finish", model, "s", "u", [], attempts=1), "{}")

    def test_estimates_are_not_deadlines(self):
        from experiments import campaign
        cfg = campaign.configuration(ROOT / "configs/experiment-campaign.json")
        plan = campaign.plan(ROOT, cfg)
        self.assertEqual(plan["video_policy"]["frames"], 117)
        for backend in ("bernini", "ditto"):
            value = resources.estimate_budget(backend)
            self.assertIsNone(value["max_wall_seconds"])
            self.assertGreater(value["estimated_wall_seconds"], 0)


if __name__ == "__main__": unittest.main()
