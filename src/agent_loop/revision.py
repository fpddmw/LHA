"""A child Planner run with attributed feedback and separately labeled videos."""
from __future__ import annotations

import json
from pathlib import Path

from planner_harness import PlannerHarness
from planner_harness.common import load, save, sha
from planner_harness.video import Video


class RevisionPlannerHarness(PlannerHarness):
    def __init__(self, output, model, context_path, **kwargs):
        super().__init__(output, model, **kwargs)
        self.context_path = Path(context_path).resolve()
        self.revision = load(self.context_path)
        self.videos = {}

    def run(self):
        context_hash = sha(self.context_path)
        if "revision_context" not in self.state:
            self.state["revision_context"] = {
                "path": str(self.context_path), "sha256": context_hash,
                "overviews": [], "mode": self.revision["mode"],
            }
            guidance = Path(__file__).with_name("REVISION.md").read_text(encoding="utf-8")
            self.system += "\n\n" + guidance
            (self.output / "system-prompt.txt").write_text(self.system, encoding="utf-8")
            self.state["system_prompt_sha256"] = sha(self.output / "system-prompt.txt")
            self.state["runtime_sources"]["outer_revision.py"] = sha(Path(__file__))
            self.state["runtime_sources"]["outer_REVISION.md"] = sha(Path(__file__).with_name("REVISION.md"))
        if self.state["revision_context"]["sha256"] != context_hash:
            raise ValueError("Revision context changed; create a new child run")
        for identity, info in self.revision["videos"].items():
            video = Video(info["path"], self.output)
            if video.info["sha256"] != info["sha256"]:
                raise ValueError(f"Revision video changed: {identity}")
            self.videos[identity] = video
            known = self.state["revision_context"]["overviews"]
            if not any(item["video_id"] == identity for item in known):
                observation = video.observe(f"revision-{identity}")
                observation.update(video_id=identity, scope="Sampled revision evidence; not automatically time-aligned with other videos.")
                known.append(observation)
        self.checkpoint()
        return super().run()

    def context(self):
        text, images, mapping = super().context()
        payload = json.loads(text)
        observed = {o["observation_id"]: o.get("video_id", "original") for o in self.state["observations"]}
        for item in mapping:
            if "observation_id" in item:
                identity = observed[item["observation_id"]]
                # The legacy revision interface names the root video "original".
                item["video_id"] = "original" if identity == "source" else identity
        for observation in self.state["revision_context"]["overviews"]:
            for frame in observation["frames"]:
                if frame["path"] not in images:
                    images.append(frame["path"])
                    mapping.append({"attachment": len(images), "video_id": observation["video_id"],
                                    "observation_id": observation["observation_id"], **frame})
        payload["attached_images_in_order"] = mapping
        payload["revision_context"] = self.revision
        payload["context_policy"] += " Revision overviews are also attached and labeled by video ID."
        return json.dumps(payload, ensure_ascii=False, indent=2), images, mapping

    def operate(self, response, event_id):
        if response.get("action") == "observe":
            args = dict(response.get("arguments", {}))
            identity = args.pop("video_id", "original")
            if identity != "original":
                if identity not in self.videos:
                    raise ValueError(f"Unknown revision video: {identity}")
                if "workspace" in response:
                    self.update_workspace(response["workspace"])
                result = self.videos[identity].observe(event_id, **args)
                result.update(video_id=identity, scope="Sampled revision evidence; exact motion requires appropriate temporal evidence.")
                self.state["observations"].append(result)
                return result
            response = {**response, "arguments": args}
        return super().operate(response, event_id)
