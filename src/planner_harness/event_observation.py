"""Paged native consecutive frames and exact coverage; no final-evaluation policy."""

import bisect
import math

from .execution import signature


def interval(start, end):
    if (
        any(type(x) not in (int, float) or not math.isfinite(x) for x in (start, end))
        or not 0 <= start < end
    ):
        raise ValueError("Continuous observation needs finite 0 <= start < end")
    return [float(start), float(end)]


def merge(ranges):
    result = []
    for a, b in sorted(ranges):
        if b <= a:
            continue
        if result and a <= result[-1][1] + 1e-9:
            result[-1][1] = max(b, result[-1][1])
        else:
            result.append([a, b])
    return result


def subtract(bounds, ranges):
    lo, hi = bounds
    result = []
    cursor = lo
    for a, b in merge(ranges):
        a, b = max(lo, a), min(hi, b)
        if b <= a:
            continue
        if a > cursor:
            result.append([cursor, a])
        cursor = max(cursor, b)
    if cursor < hi:
        result.append([cursor, hi])
    return result


def indices(video, start, end):
    interval(start, end)
    if start >= video.info["duration_seconds"]:
        return []
    first = max(0, bisect.bisect_right(video.times, start) - 1)
    last = min(len(video.times) - 1, bisect.bisect_left(video.times, end))
    return list(range(first, last + 1))


def coverage(video, bounds, seen):
    seen = sorted(set(seen))
    runs = []
    for i in seen:
        if type(i) is not int or not 0 <= i < len(video.times):
            raise ValueError("Unknown native frame ordinal")
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    ranges = merge(
        [
            [
                max(bounds[0], video.times[r[0]]),
                min(
                    bounds[1],
                    video.times[r[-1] + 1]
                    if r[-1] + 1 < len(video.times)
                    else video.info["duration_seconds"],
                ),
            ]
            for r in runs
        ]
    )
    available = [bounds[0], min(bounds[1], video.info["duration_seconds"])]
    available_ranges = [available] if available[1] > available[0] else []
    missing = subtract(bounds, available_ranges)
    unreviewed = subtract(available, ranges) if available_ranges else []
    continuous = merge(
        [
            [max(bounds[0], video.times[r[0]]), min(bounds[1], video.times[r[-1]])]
            for r in runs
            if len(r) >= 2
        ]
    )
    return {
        "requested_interval": bounds,
        "observed_intervals": ranges,
        "continuous_evidence_intervals": continuous,
        "media_missing_intervals": missing,
        "unreviewed_intervals": unreviewed,
        "observed_frame_indices": seen,
        "requested_native_frames": len(indices(video, *bounds)),
        "observed_native_frames": len(seen),
        "complete": not missing and not unreviewed,
        "scope": "Decoded frame coverage; motion continuity only within adjacent observed native ordinals. No motion alignment is inferred.",
    }


def extract(video, identity, chosen):
    frames = []
    for offset in range(0, len(chosen), 16):
        part = chosen[offset : offset + 16]
        frames.extend(
            video.observe(f"{identity}-{offset}", indices=part, count=len(part))["frames"]
        )
    return frames


def observe_event(video, identity, *, start=0, end=None, count=16, page=1, crop=None, previous=()):
    bounds = interval(start, video.info["duration_seconds"] if end is None else end)
    if type(count) is not int or not 2 <= count <= 16 or type(page) is not int or page < 1:
        raise ValueError("Continuous pages use count 2..16 and page >= 1")
    if crop is not None and (
        not isinstance(crop, list)
        or len(crop) != 4
        or any(type(v) not in (int, float) or not math.isfinite(v) for v in crop)
        or not 0 <= crop[0] < crop[2] <= 1
        or not 0 <= crop[1] < crop[3] <= 1
    ):
        raise ValueError("Use a normalized crop")
    all_indices = indices(video, *bounds)
    offset = (page - 1) * (count - 1)
    chosen = all_indices[offset : offset + count]
    if all_indices and offset >= len(all_indices):
        raise ValueError("Continuous page exceeds the event; use its returned next arguments")
    key = signature({"video": video.info["sha256"], "interval": bounds, "crop": crop})
    frames = (
        video.observe(identity, indices=chosen, count=len(chosen), crop=crop)["frames"]
        if chosen
        else []
    )
    seen = set(chosen)
    prior_ids = []
    for observation in previous:
        if observation.get("event_key") == key:
            seen.update(f["frame_index"] for f in observation["frames"])
            prior_ids.append(observation["observation_id"])
    next_page = (
        {
            "mode": "continuous",
            "start": bounds[0],
            "end": bounds[1],
            "count": count,
            "page": page + 1,
            "crop": crop,
        }
        if offset + count < len(all_indices)
        else None
    )
    return {
        "observation_id": identity,
        "mode": "continuous",
        "event_key": key,
        "video_sha256": video.info["sha256"],
        "requested_interval": bounds,
        "frames": frames,
        "consecutive_decoded_frames": True,
        "page": page,
        "page_size": count,
        "overlap_frames": 1,
        "next_arguments": next_page,
        "page_coverage": coverage(video, bounds, chosen),
        "coverage": coverage(video, bounds, seen),
        "previous_observations": prior_ids,
        "scope": "This page supplies consecutive native frames. Coverage includes earlier pages; unreviewed and absent intervals remain explicit.",
    }


def segments(videos, start, end, *, size=16, limit=12):
    """Shared time boundaries, native frames in each video, overlap at boundaries."""
    bounds = interval(start, end)
    result = []
    lo = start
    while lo < end - 1e-9 and len(result) < limit:
        choices = [end]
        for video in videos.values():
            if lo >= video.info["duration_seconds"]:
                continue
            first = max(0, bisect.bisect_right(video.times, lo) - 1)
            boundary = first + size - 2
            if boundary < len(video.times) and video.times[boundary] > lo:
                choices.append(video.times[boundary])
        hi = min(choices)
        result.append(
            {
                "interval": [lo, hi],
                "indices": {key: indices(video, lo, hi) for key, video in videos.items()},
            }
        )
        lo = hi
    return result, ([lo, end] if lo < end - 1e-9 else None)


def observe_videos(state, output, arguments, event_id):
    """Observe or reopen the same native evidence in Planner and Critic sessions."""
    from .common import sha
    from .video import Video

    args = dict(arguments)
    if "observation" in args:
        requested = args.pop("observation")
        if args:
            raise ValueError("Reopen an observation without changing its sampling arguments")
        ids = requested if isinstance(requested, list) else [requested]
        lookup = {o["observation_id"]: o for o in state["observations"]}
        if not 1 <= len(ids) <= 4 or any(not isinstance(i, str) or i not in lookup for i in ids):
            raise ValueError("Choose 1 to 4 recorded observation IDs")
        results = [lookup[i] for i in dict.fromkeys(ids)]
        for result in results:
            if any(sha(f["path"]) != f["sha256"] for f in result["frames"]):
                raise ValueError("Recorded observation changed")
    else:
        requested = args.pop("video", args.pop("video_id", "source"))
        ids = requested if isinstance(requested, list) else [requested]
        videos = state.get("videos") or {"source": state["request"]["source"]}
        if not 1 <= len(ids) <= 4 or any(not isinstance(i, str) or i not in videos for i in ids):
            raise ValueError("Choose 1 to 4 available video IDs")
        ids = list(dict.fromkeys(ids))
        for identity in ids:
            if sha(videos[identity]["path"]) != videos[identity]["sha256"]:
                raise ValueError("Task video changed")
        results = []
        mode = args.pop("mode", "sampled")
        if mode not in {"sampled", "continuous"}:
            raise ValueError("Observation mode is sampled or continuous")
        if mode == "continuous":
            args.setdefault("count", min(16, 32 // len(ids)))
            if type(args["count"]) is not int or args["count"] * len(ids) > 32:
                raise ValueError(
                    "Use at most 32 continuous frames across requested videos; reduce count or request fewer videos"
                )
        for index, identity in enumerate(ids):
            observation_id = event_id if len(ids) == 1 else f"{event_id}-{index + 1}"
            video = Video(videos[identity]["path"], output)
            if mode == "continuous":
                if set(args) - {"start", "end", "count", "page", "crop"}:
                    raise ValueError("Continuous observations take start/end, count, page and crop")
                prior = [o for o in state["observations"] if o.get("video_id") == identity]
                for observation in prior:
                    if observation.get("mode") == "continuous" and any(
                        sha(f["path"]) != f["sha256"] for f in observation["frames"]
                    ):
                        raise ValueError("Prior continuous observation changed")
                result = observe_event(video, observation_id, previous=prior, **args)
                if result["next_arguments"] is not None:
                    result["next_arguments"]["video"] = identity
            else:
                result = video.observe(observation_id, **args)
                result["scope"] = (
                    "Sampled frames from "
                    + identity
                    + "; precise motion needs suitable temporal evidence."
                )
            result["video_id"] = identity
            results.append(result)
        state["observations"].extend(results)
    state["observation_focus"] = {
        "ids": [r["observation_id"] for r in results],
        "observations_count": len(state["observations"]),
    }
    if len(results) == 1:
        return results[0]
    return {
        "observations": results,
        "scope": "Sampled comparisons at each video's own timestamps; matching times do not establish motion alignment.",
    }
