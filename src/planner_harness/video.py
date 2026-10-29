from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from .common import sha


class Video:
    def __init__(self, source, output):
        self.source = Path(source).resolve()
        self.output = Path(output)
        cap = cv2.VideoCapture(str(self.source))
        try:
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {self.source}")
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fps <= 0 or count <= 0:
                raise ValueError("Video has no usable frame/timing metadata")
            self.info = {"path": str(self.source), "sha256": sha(self.source), "fps": fps, "frames": count,
                         "duration_seconds": count / fps, "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                         "timing_basis": "decoder frame index and reported FPS; sampled observations, not a continuous-motion verification"}
        finally:
            cap.release()

    def observe(self, identity, start=0, end=None, count=6, crop=None):
        duration = self.info["duration_seconds"]
        end = duration if end is None else float(end)
        start, count = float(start), int(count)
        if not (0 <= start <= end <= duration) or not 1 <= count <= 16:
            raise ValueError("Use a valid time interval and 1 to 16 frames per observation")
        last_time = (self.info["frames"] - 1) / self.info["fps"]
        if start > last_time:
            raise ValueError(f"The last decodable frame begins at {last_time:.6f} seconds")
        if crop is not None and (not isinstance(crop, list) or len(crop) != 4 or not 0 <= crop[0] < crop[2] <= 1 or not 0 <= crop[1] < crop[3] <= 1):
            raise ValueError("crop must be normalized [left, top, right, bottom] within [0,1]")
        indices = sorted(set(int(round(t * self.info["fps"])) for t in np.linspace(start, min(end, (self.info["frames"] - 1) / self.info["fps"]), count)))
        directory = self.output / "observations" / identity
        directory.mkdir(parents=True, exist_ok=True)
        frames = []
        cap = cv2.VideoCapture(str(self.source))
        try:
            for index in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, pixels = cap.read()
                if not ok:
                    raise ValueError(f"Failed to decode source frame {index}")
                image = Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB))
                if crop:
                    w, h = image.size
                    image = image.crop((int(crop[0]*w), int(crop[1]*h), int(crop[2]*w), int(crop[3]*h)))
                image.thumbnail((960, 960))
                path = directory / f"{index:06d}.jpg"
                image.save(path, quality=90)
                frames.append({"frame_index": index, "timestamp_seconds": round(index/self.info["fps"], 6), "path": str(path.resolve()), "sha256": sha(path), "crop": crop})
        finally:
            cap.release()
        return {"observation_id": identity, "requested_interval": [start, end], "frames": frames,
                "scope": "Source-video sampled frames. Unseen intervals, exact trajectories, and social intentions require appropriate evidence."}
