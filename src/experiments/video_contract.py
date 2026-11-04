"""Deterministic CPU preparation shared by every experiment arm."""
from fractions import Fraction
from pathlib import Path
import shutil

from planner_harness.common import load, save, sha
from planner_harness.lock import RunLock

POLICY = "uniform-full-span-117-at-24fps-v1"
FRAMES = 117
FPS = 24


def sample_indices(count):
    if type(count) is not int or count < 1:
        raise ValueError("Source must contain at least one decoded frame")
    # Integer nearest-neighbour rounding, including the first and last frames.
    return [(i * (count - 1) * 2 + FRAMES - 1) // (2 * (FRAMES - 1))
            for i in range(FRAMES)]


def normalize(source, directory, info):
    """Retain originals; reuse only a hash-verified normalized input and receipt."""
    import av
    source, directory = Path(source), Path(directory)
    source_hash = sha(source)
    directory = directory / source_hash
    video, receipt = directory / "source.mp4", directory / "normalization.json"
    indices = sample_indices(info["frames"])
    expected = {"policy": POLICY, "original_sha256": source_hash,
                "original_info": info, "source_indices": indices,
                "frames": FRAMES, "fps": FPS}
    with RunLock(directory / "owner"):
        if receipt.exists():
            saved = load(receipt)
            if any(saved.get(k) != v for k, v in expected.items()) or sha(video) != saved["normalized_sha256"]:
                raise ValueError("Normalized source or its frozen provenance changed")
            return video, saved
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / "source.tmp.mp4"
        if info["frames"] == FRAMES and abs(info["fps"] - FPS) < 1e-6:
            shutil.copyfile(source, temporary)
        else:
            # Lossless H.264 avoids an additional lossy generation. yuv444p
            # also supports odd source dimensions without crop or padding.
            with av.open(str(source)) as decoder, av.open(str(temporary), "w") as encoder:
                stream = encoder.add_stream("libx264", rate=FPS)
                stream.width, stream.height = info["width"], info["height"]
                stream.pix_fmt = "yuv444p"
                stream.options = {"crf": "0", "preset": "fast", "threads": "1"}
                position = 0
                for number, decoded in enumerate(decoder.decode(video=0)):
                    while position < FRAMES and indices[position] == number:
                        frame = av.VideoFrame.from_ndarray(decoded.to_ndarray(format="rgb24"), format="rgb24")
                        frame.pts, frame.time_base = position, Fraction(1, FPS)
                        for packet in stream.encode(frame):
                            encoder.mux(packet)
                        position += 1
                    if position == FRAMES:
                        break
                if position != FRAMES:
                    raise ValueError("Decoded source does not match the recorded frame count")
                for packet in stream.encode():
                    encoder.mux(packet)
        with av.open(str(temporary)) as check:
            count = sum(1 for _ in check.decode(video=0))
            rate = float(check.streams.video[0].average_rate)
        if count != FRAMES or abs(rate - FPS) > 1e-6:
            raise ValueError("Normalized source failed the 117-frame/24-fps contract")
        temporary.replace(video)
        saved = {**expected, "normalized_sha256": sha(video)}
        save(receipt, saved)
        return video, saved
