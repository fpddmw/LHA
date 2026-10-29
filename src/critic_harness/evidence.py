"""Bounded native-PTS observations; no dependency on the formal evaluation worker."""
from __future__ import annotations

import bisect
import math
from pathlib import Path

from planner_harness.common import sha


def metadata(path):
    import av
    times, duration = [], None
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate) if stream.average_rate else None
        width, height = stream.width, stream.height
        for frame in container.decode(video=0):
            if frame.time is None:
                raise ValueError("Missing native presentation timestamp")
            times.append(float(frame.time))
            duration = float(frame.duration * frame.time_base) if getattr(frame, "duration", None) else None
    if len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Need strictly increasing native PTS and at least two frames")
    origin = times[0]
    times = [t - origin for t in times]
    tail = duration or (1 / fps if fps else times[-1] - times[-2])
    return {"times": times, "duration_seconds": times[-1] + tail, "width": width, "height": height,
            "frames": len(times), "pts_origin": origin, "timing_basis": "Decoded native PTS"}


def covered(ranges, interval, tolerance=1e-6):
    position = interval[0]
    for start, end in sorted(ranges):
        if end < position - tolerance:
            continue
        if start > position + tolerance:
            break
        position = max(position, end)
        if position >= interval[1] - tolerance:
            return True
    return False


class Evidence:
    def __init__(self, videos, output):
        self.videos, self.output = videos, Path(output)

    def observe(self, identity, videos, start=0, end=None, count=6, dense=False, crop=None):
        import av
        if not isinstance(videos, list) or not 1 <= len(videos) <= 4 or len(set(videos)) != len(videos):
            raise ValueError("Choose 1-4 distinct video IDs")
        if any(v not in self.videos for v in videos):
            raise ValueError("Unknown video ID")
        if crop is not None and (len(crop) != 4 or not 0 <= crop[0] < crop[2] <= 1 or not 0 <= crop[1] < crop[3] <= 1):
            raise ValueError("Invalid normalized crop")
        if type(dense) is not bool or type(count) is not int or not 2 <= count <= 12:
            raise ValueError("dense must be boolean; sparse count must be 2-12")
        end = min(self.videos[v]["duration_seconds"] for v in videos) if end is None else float(end)
        start = float(start)
        if not math.isfinite(start + end) or not 0 <= start < end:
            raise ValueError("Invalid time interval")
        result = {"observation_id": identity, "dense": dense, "requested_interval": [start, end],
                  "crop": crop, "videos": {}, "frames": [],
                  "scope": "Native continuous frames within recorded coverage." if dense else "Sparse samples; unseen motion remains unresolved."}
        for video_id in videos:
            info = self.videos[video_id]
            if sha(info["path"]) != info["sha256"]:
                raise ValueError("Video changed")
            times = info["times"]
            if end > info["duration_seconds"] + 1e-6 or start >= info["duration_seconds"]:
                raise ValueError("Requested interval extends beyond available media; no tail padding")
            first = max(0, bisect.bisect_right(times, start) - 1)
            last = max(first, bisect.bisect_left(times, end) - 1)
            indices = list(range(first, last + 1)) if dense else sorted({round(first + i * (last-first) / (count-1)) for i in range(count)})
            if dense:
                indices = indices[:24]  # Up to 96 images across four videos per observation.
            coverage_end = times[indices[-1] + 1] if indices[-1] + 1 < len(times) else info["duration_seconds"]
            more = dense and indices[-1] < last
            result["videos"][video_id] = {"sha256": info["sha256"], "actual_interval": [times[indices[0]], min(end, coverage_end)],
                "next_start": coverage_end if more else None, "continuous": dense, "crop": crop}
            directory = self.output / "observations" / identity / video_id
            directory.mkdir(parents=True, exist_ok=True)
            wanted = set(indices)
            with av.open(info["path"]) as container:
                for i, frame in enumerate(container.decode(video=0)):
                    if i > indices[-1]:
                        break
                    if i not in wanted:
                        continue
                    image = frame.to_image().convert("RGB")
                    if crop:
                        w, h = image.size
                        image = image.crop((round(crop[0]*w), round(crop[1]*h), round(crop[2]*w), round(crop[3]*h)))
                    image.thumbnail((1024, 1024))
                    path = directory / f"{i:06d}.jpg"
                    image.save(path, quality=95)
                    result["frames"].append({"video": video_id, "index": i, "time_seconds": times[i],
                                             "path": str(path.resolve()), "sha256": sha(path), "crop": crop})
        result["scope"] += " Cropped evidence applies only to the inspected region." if crop else " Full-frame view."
        return result


def validate_assessment(report, observations, videos, candidate, duration):
    if not isinstance(report.get("summary"), str) or not report["summary"].strip():
        raise ValueError("Assessment needs a summary")
    if not isinstance(report.get("findings"), list) or not report["findings"]:
        raise ValueError("Assessment needs grounded findings")
    def references(refs):
        if not isinstance(refs, list):
            raise ValueError("Evidence must be a list of observation/video references")
        found = []
        for ref in refs:
            obs = observations.get(ref["observation_id"])
            if not obs or ref["video"] not in obs["videos"]:
                raise ValueError("Evidence reference was not observed")
            found.append((ref["video"], obs["videos"][ref["video"]]))
        return found
    ids = set()
    for item in report["findings"]:
        if not item.get("id") or item["id"] in ids:
            raise ValueError("Finding IDs must be unique")
        ids.add(item["id"])
        if item.get("dimension") not in {"edit", "preservation", "style", "design", "temporal", "creativity"}:
            raise ValueError("Unknown finding dimension")
        if item.get("origin") not in {"user_requirement", "preservation", "design_quality"}:
            raise ValueError("Outcome findings use original task/observations, not optional Planner choices")
        if item.get("importance") not in {"core", "detail", "design"}:
            raise ValueError("Unknown importance")
        verdict = item.get("verdict")
        if verdict not in {"pass", "partial", "fail", "unknown", "not_applicable"} or not item.get("claim"):
            raise ValueError("Invalid finding")
        refs = references(item.get("evidence", []))
        known = verdict not in {"unknown", "not_applicable"}
        if known and candidate not in [v for v, _ in refs]:
            raise ValueError("A determined finding needs candidate evidence")
        if known and item["dimension"] == "preservation" and "source" not in [v for v, _ in refs]:
            raise ValueError("Preservation needs original-source evidence")
        if verdict == "partial" and not item.get("partial_boundary"):
            raise ValueError("Explain the task-specific partial boundary")
        if known and item["dimension"] == "temporal" and not item.get("requires_sequence"):
            raise ValueError("Determined temporal findings require explicit continuous evidence and scope")
        if known and item.get("requires_sequence"):
            interval = item.get("interval_seconds", [])
            required = item.get("sequence_videos", [])
            if len(interval) != 2 or not 0 <= interval[0] < interval[1] <= duration + 1e-6 or candidate not in required or not item.get("scope"):
                raise ValueError("Sequence claims need a valid interval, spatial scope and video IDs")
            if item["dimension"] == "preservation" and "source" not in required:
                raise ValueError("Motion preservation needs source and candidate continuous evidence")
            for video in required:
                ranges = [o["actual_interval"] for v, o in refs if v == video and o["continuous"]
                          and (item["scope"] != "whole frame" or o["crop"] is None)]
                if not covered(ranges, interval):
                    raise ValueError("Sequence claim exceeds supplied continuous evidence")
    for dimension, rating in report.get("ratings", {}).items():
        if dimension not in {"style", "design", "temporal", "scene_specific_design", "narrative_emotional_fit",
                             "style_world_consistency", "composition_lighting", "color_texture", "hierarchy_readability", "temporal_coherence"}:
            raise ValueError("Unsupported online rating; no mixed overall or unanchored originality score")
        refs = references(rating.get("evidence", []))
        score = rating.get("score")
        if score is not None:
            if type(score) not in {int, float} or not math.isfinite(score) or not 1 <= score <= 4 or abs(score*10-round(score*10)) > 1e-6:
                raise ValueError("Ratings use 1-4 in 0.1 steps or null")
            if candidate not in [v for v, _ in refs] or not rating.get("reason"):
                raise ValueError("Scored ratings need candidate evidence and reasons")
            if dimension in {"temporal", "temporal_coherence"} and not covered([o["actual_interval"] for v, o in refs if v == candidate and o["continuous"] and o["crop"] is None], [0, duration]):
                raise ValueError("Whole-clip temporal score needs whole-frame continuous coverage")
    for comparison in report.get("comparisons", []):
        against = comparison.get("against")
        if against not in videos or against == candidate:
            raise ValueError("Invalid comparison video")
        seen = {v for v, _ in references(comparison.get("evidence", []))}
        if not {candidate, against} <= seen:
            raise ValueError("Comparison needs evidence from both videos")
        comparison["relationship"] = "actual_input" if videos[candidate].get("parent") == against else "original_source" if against == "source" else "alternative"
    return report
