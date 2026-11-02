"""Native presentation timestamps and sequential decode identity for video evidence."""
from __future__ import annotations

import bisect
import math
from pathlib import Path

from .common import sha

DECODER = "native-pts-v1"


class Video:
    def __init__(self, source, output):
        from critic_harness.evidence import metadata
        self.source = Path(source).resolve()
        self.output = Path(output)
        meta = metadata(self.source)
        self.times = meta.pop("times")
        self.pts = meta.pop("native_pts")
        self.time_bases = meta.pop("time_bases")
        self.info = {"path": str(self.source), "sha256": sha(self.source), **meta,
                     "decoder": DECODER}

    def observe(self, identity, start=0, end=None, count=6, crop=None, *, indices=None):
        import av
        duration = self.info["duration_seconds"]
        end = duration if end is None else float(end)
        start = float(start)
        if not math.isfinite(start + end) or not 0 <= start <= end <= duration or type(count) is not int or not 1 <= count <= 16:
            raise ValueError("Use a valid time interval and 1 to 16 frames per observation")
        if start > self.times[-1]:
            raise ValueError("Interval begins after the last decoded frame")
        if crop is not None and (not isinstance(crop, list) or len(crop) != 4 or not 0 <= crop[0] < crop[2] <= 1 or not 0 <= crop[1] < crop[3] <= 1):
            raise ValueError("crop must be normalized [left, top, right, bottom] within [0,1]")
        if indices is None:
            stop = min(end, self.times[-1])
            targets = [start + (stop - start) * i / max(1, count - 1) for i in range(count)]
            indices = sorted({min(range(max(0, bisect.bisect_left(self.times, t) - 1),
                                       min(len(self.times), bisect.bisect_left(self.times, t) + 1)),
                                  key=lambda i: abs(self.times[i] - t)) for t in targets})
        if not isinstance(indices, list) or not 1 <= len(indices) <= 16 or indices != sorted(set(indices)) or any(type(i) is not int or not 0 <= i < len(self.times) for i in indices):
            raise ValueError("Choose ordered unique decoded indices")
        directory = self.output / "observations" / identity
        directory.mkdir(parents=True, exist_ok=True)
        frames = []
        wanted = set(indices)
        # No seek: ordinal, native PTS and supplied pixels refer to this decode.
        with av.open(str(self.source)) as container:
            for index, frame in enumerate(container.decode(video=0)):
                if index > indices[-1]:
                    break
                if index not in wanted:
                    continue
                if frame.pts != self.pts[index] or str(frame.time_base) != self.time_bases[index]:
                    raise ValueError("Decoded frame identity changed")
                image = frame.to_image().convert("RGB")
                if crop:
                    w, h = image.size
                    image = image.crop((int(crop[0]*w), int(crop[1]*h), int(crop[2]*w), int(crop[3]*h)))
                image.thumbnail((960, 960))
                path = directory / f"{index:06d}.jpg"
                image.save(path, quality=90)
                frames.append({"frame_index": index, "timestamp_seconds": self.times[index],
                               "native_pts": frame.pts, "time_base": str(frame.time_base),
                               "pts_origin_seconds": self.info["pts_origin"], "decoder": DECODER,
                               "path": str(path.resolve()), "sha256": sha(path), "crop": crop})
        if len(frames) != len(indices):
            raise ValueError("Not all requested decoded frames were supplied")
        return {"observation_id": identity, "requested_interval": [start, end], "frames": frames,
                "consecutive_decoded_frames": indices == list(range(indices[0], indices[-1] + 1)),
                "scope": "Native PTS sampled frames; continuity applies only to recorded adjacent decoded ordinals."}
