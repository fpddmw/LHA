"""Output-only adjacent-frame CLIP/DINO cosine metrics, protocol v1."""
from __future__ import annotations

import math
from statistics import mean

from .media import decode, nearest
from .protocol import file_hash, require


def adjacent_cosine(features):
    require(len(features) >= 2, "Need two feature vectors")
    normalized = []
    width = len(features[0])
    for row in features:
        require(len(row) == width and all(math.isfinite(float(v)) for v in row), "Invalid feature matrix")
        norm = math.sqrt(sum(float(v) ** 2 for v in row))
        require(norm > 0, "Zero feature vector")
        normalized.append([float(v) / norm for v in row])
    return mean(sum(a * b for a, b in zip(x, y)) for x, y in zip(normalized, normalized[1:]))


def compute(video, *, clip_model="openai/clip-vit-large-patch14", dino_model="facebook/dinov2-large",
            clip_revision="main", dino_revision="main", sample_fps=4.0, device="cpu", batch_size=8):
    import torch
    from transformers import AutoImageProcessor, AutoModel, CLIPModel, CLIPProcessor
    require(sample_fps > 0 and batch_size > 0, "Invalid feature sampling config")
    decoded = decode(video)
    indices = sorted({nearest(decoded["times"], k / sample_fps, decoded["step"])
                      for k in range(math.floor(decoded["times"][-1] * sample_fps) + 1)})
    require(len(indices) >= 2, "Too few distinct sampled frames")
    frames = [decoded["frames"][i] for i in indices]
    result = {"protocol": "lha-output-consistency-v1", "output_sha256": file_hash(video),
              "sample_fps": sample_fps, "indices": indices,
              "timestamps": [decoded["times"][i] for i in indices], "scale": "raw_cosine", "encoders": {}}
    for name, model_id, revision in (("clip_f", clip_model, clip_revision), ("dino_f", dino_model, dino_revision)):
        if name == "clip_f":
            processor = CLIPProcessor.from_pretrained(model_id, revision=revision)
            model = CLIPModel.from_pretrained(model_id, revision=revision).to(device).eval()
        else:
            processor = AutoImageProcessor.from_pretrained(model_id, revision=revision)
            model = AutoModel.from_pretrained(model_id, revision=revision).to(device).eval()
        vectors = []
        with torch.inference_mode():
            for start in range(0, len(frames), batch_size):
                inputs = processor(images=frames[start:start + batch_size], return_tensors="pt").to(device)
                if name == "clip_f":
                    output = model.get_image_features(**inputs)
                else:
                    output = model(**inputs).last_hidden_state[:, 0]
                vectors.extend(output.float().cpu().tolist())
        result[name] = adjacent_cosine(vectors)
        result["encoders"][name] = {"model": model_id, "requested_revision": revision,
                                     "resolved_revision": getattr(model.config, "_commit_hash", None),
                                     "processor": processor.to_dict() if hasattr(processor, "to_dict") else str(type(processor)),
                                     "torch": torch.__version__}
        del model
    return result
