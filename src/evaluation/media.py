"""PTS-based evidence; never repeat a final frame to conceal a short output."""
from __future__ import annotations

import bisect
import statistics
from pathlib import Path

from .protocol import file_hash, require, signature, validate_card, write


def decode(path):
    import av
    frames, times, durations = [], [], []
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        fallback = 1 / float(stream.average_rate) if stream.average_rate else None
        for frame in container.decode(video=0):
            require(frame.time is not None, "Missing presentation timestamp")
            times.append(float(frame.time))
            frames.append(frame.to_image().convert("RGB"))
            duration = getattr(frame, "duration", None)
            durations.append(float(duration * frame.time_base) if duration else None)
    require(len(times) >= 2, "At least two decodable frames required")
    require(all(b > a for a, b in zip(times, times[1:])), "PTS must be strictly increasing")
    origin = times[0]
    times = [t - origin for t in times]
    step = statistics.median(b - a for a, b in zip(times, times[1:]))
    duration = times[-1] + (durations[-1] or fallback or step)
    return {"frames": frames, "times": times, "duration": duration, "step": step, "pts_origin": origin}


def delivery_status(duration, expected, step, tolerance=0.08):
    require(step > 0 and expected > 0, "Invalid timebase")
    valid = abs(duration - expected) <= tolerance
    return {"status": "valid" if valid else "invalid", "duration_seconds": duration,
            "expected_seconds": expected, "tolerance_seconds": tolerance,
            "reason": "Decoded duration within tolerance" if valid else "Duration outside task tolerance"}


def nearest(times, target, tolerance):
    pos = bisect.bisect_left(times, target)
    choices = [i for i in (pos - 1, pos) if 0 <= i < len(times)]
    idx = min(choices, key=lambda i: abs(times[i] - target))
    require(abs(times[idx] - target) <= tolerance, f"No frame near {target:.4f}s")
    return idx


def prepare(card, output, destination, *, root=Path("."), frame_count=12, dense_ranges=(), mapping=None):
    validate_card(card)
    require(frame_count >= 2, "Need at least two overview samples")
    source = root / card["source_video"]
    require(file_hash(source) == card["source_sha256"], "Source hash mismatch")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    src = decode(source)
    require(src["duration"] + 0.08 >= card.get("source_start_seconds", 0) + card["duration_seconds"], "Source does not cover task interval")
    out = decode(output)
    output_hash = file_hash(output)
    delivery = delivery_status(out["duration"], card["duration_seconds"], out["step"])
    if mapping is not None:
        require(mapping.get("source_sha256") == card["source_sha256"] and mapping.get("output_sha256") == output_hash, "Mapping hash mismatch")
        source_times = mapping["source_times_seconds"]
        require(len(source_times) == len(out["times"]), "Mapping must cover every decoded output frame")
        require(all(0 <= t <= src["times"][-1] + src["step"] for t in source_times), "Mapping outside source")
        require(all(a <= b for a, b in zip(source_times, source_times[1:])), "Mapping must preserve order")
    else:
        source_times = [t + card.get("source_start_seconds", 0) for t in out["times"]]
    valid_indices = [i for i, t in enumerate(out["times"]) if t < card["duration_seconds"] and source_times[i] <= src["times"][-1] + src["step"] / 2]
    require(len(valid_indices) >= 2, "Insufficient overlapping evidence")
    overview = sorted({valid_indices[round(j * (len(valid_indices) - 1) / (frame_count - 1))] for j in range(frame_count)})
    dense = set()
    for start, end in dense_ranges:
        require(0 <= start < end <= card["duration_seconds"], "Invalid dense interval")
        dense.update(i for i in valid_indices if start <= out["times"][i] <= end)
    indices = sorted(set(overview) | dense)
    pairs, source_images, output_images = [], [], []
    for i in indices:
        si = nearest(src["times"], source_times[i], src["step"] * 0.55 + 1e-6)
        sp, op = destination / f"source_{i:05d}.jpg", destination / f"output_{i:05d}.jpg"
        src["frames"][si].save(sp, quality=95)
        out["frames"][i].save(op, quality=95)
        source_images.append(str(sp.resolve()))
        output_images.append(str(op.resolve()))
        pairs.append({"source_index": si, "output_index": i, "source_seconds": src["times"][si],
                      "output_seconds": out["times"][i], "dense": i in dense, "overview": i in overview})
    payload = {"card_sha256": card["card_sha256"], "source_sha256": card["source_sha256"],
               "output_sha256": output_hash, "delivery": delivery, "pairs": pairs,
               "source_images": source_images, "output_images": output_images,
               "dense_ranges": list(dense_ranges), "frame_count": len(out["frames"]),
               "alignment": "explicit_mapping" if mapping else "identity_seconds",
               "mapping_sha256": signature(mapping) if mapping else None}
    payload["evidence_sha256"] = signature({**payload, "image_sha256": [file_hash(p) for p in source_images + output_images]})
    payload["image_sha256"] = [file_hash(p) for p in source_images + output_images]
    write(destination / "evidence.json", payload)
    return payload
