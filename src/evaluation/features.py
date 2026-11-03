"""Output consistency and recast extent with exact CLIP text input provenance."""
from __future__ import annotations

import hashlib
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


def _unit(row):
    require(all(math.isfinite(float(v)) for v in row), "Invalid feature vector")
    norm = math.sqrt(sum(float(v) ** 2 for v in row))
    require(norm > 0, "Zero feature vector")
    return [float(v) / norm for v in row]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def paired_cosine(left, right):
    """Mean cosine of time-aligned source/output vectors; 1 means visually unchanged."""
    require(len(left) == len(right) and len(left) >= 1, "Need aligned feature pairs")
    return mean(_dot(_unit(a), _unit(b)) for a, b in zip(left, right))


def text_gain(source, output, text):
    """Mean output-to-request minus source-to-request image-text cosine."""
    require(len(source) == len(output) and source, "Need aligned feature pairs")
    target = _unit(text)
    return mean(_dot(_unit(b), target) - _dot(_unit(a), target) for a, b in zip(source, output))


def _sampled(decoded, sample_fps):
    return sorted({nearest(decoded["times"], k / sample_fps, decoded["step"])
                   for k in range(math.floor(decoded["times"][-1] * sample_fps) + 1)})


def clip_text_record(request, tokenizer, tokens, *, model_max_positions=None):
    """Describe the actual encoded token sequence, without changing truncation policy.

    Decoded text is tokenizer-normalized text, not a claimed character slice of the
    original. Token spans exclude special tokens; full input IDs/mask are retained.
    """
    def values(value):
        return value.tolist() if hasattr(value, "tolist") else list(value)

    original = values(tokenizer(request, add_special_tokens=True, truncation=False)["input_ids"])
    ids = values(tokens["input_ids"][0])
    mask = values(tokens["attention_mask"][0]) if "attention_mask" in tokens else [1] * len(ids)
    require(len(ids) == len(mask), "CLIP text mask length differs")
    active = [i for i, keep in zip(ids, mask) if keep]
    special = set(tokenizer.all_special_ids)
    full_content = [i for i in original if i not in special]
    used_content = [i for i in active if i not in special]
    n, kept = len(full_content), len(used_content)
    side = getattr(tokenizer, "truncation_side", "right")
    if used_content == full_content:
        scope, span = "full_request", [0, n]
    elif side == "right" and kept < n and used_content == full_content[:kept]:
        scope, span = "request_prefix", [0, kept]
    elif side == "left" and kept < n and used_content == full_content[n - kept:]:
        scope, span = "request_suffix", [n - kept, n]
    else:
        scope, span = "encoded_tokens_only", None
    return {
        "version": "clip-text-input-v1", "original_request": request,
        "request_sha256": hashlib.sha256(request.encode("utf-8")).hexdigest(),
        "original_input_ids": original, "input_ids": ids, "attention_mask": mask,
        "original_tokens_with_specials": len(original), "encoded_tokens_with_specials": len(active),
        "original_content_tokens": n, "encoded_content_tokens": kept,
        "truncated": kept < n, "truncation_side": side,
        "tokenizer_max_length": getattr(tokenizer, "model_max_length", None),
        "model_max_positions": model_max_positions,
        "scope": scope, "content_token_span": span,
        "content_token_coverage": kept / n if n and span is not None else 1.0 if n == kept == 0 else None,
        "encoded_text": tokenizer.decode(active, skip_special_tokens=True, clean_up_tokenization_spaces=False),
        "text_representation": "Tokenizer-normalized decoded input; token span is not a source character span.",
    }


def _compute(video, *, clip_model="openai/clip-vit-large-patch14", dino_model="facebook/dinov2-large",
            clip_revision="main", dino_revision="main", sample_fps=4.0, device="cpu", batch_size=8,
            source=None, request=None):
    import torch
    from transformers import AutoImageProcessor, AutoModel, CLIPModel, CLIPProcessor
    require(sample_fps > 0 and batch_size > 0, "Invalid feature sampling config")
    decoded = decode(video)
    indices = _sampled(decoded, sample_fps)
    require(len(indices) >= 2, "Too few distinct sampled frames")
    frames = [decoded["frames"][i] for i in indices]
    result = {"protocol": "lha-output-consistency-v3", "output_sha256": file_hash(video),
              "sample_fps": sample_fps, "indices": indices,
              "timestamps": [decoded["times"][i] for i in indices], "scale": "raw_cosine", "encoders": {}}
    # Recast extent compares time-aligned source/output samples over their shared span.
    aligned = None
    if source is not None:
        original = decode(source)
        shared = min(original["times"][-1], decoded["times"][-1])
        pairs = [(nearest(original["times"], t, original["step"]), nearest(decoded["times"], t, decoded["step"]))
                 for t in (k / sample_fps for k in range(math.floor(shared * sample_fps) + 1))]
        aligned = {"source_frames": [original["frames"][i] for i, _ in pairs],
                   "output_frames": [decoded["frames"][j] for _, j in pairs],
                   "source_indices": [i for i, _ in pairs], "output_indices": [j for _, j in pairs]}
        result["recast_extent"] = {"source_sha256": file_hash(source), "pairs": len(pairs),
                                   "source_indices": aligned["source_indices"],
                                   "output_indices": aligned["output_indices"],
                                   "request_sha256": None if request is None else
                                   hashlib.sha256(request.encode("utf-8")).hexdigest()}

    def embed(name, model, processor, images):
        vectors = []
        with torch.inference_mode():
            for start in range(0, len(images), batch_size):
                inputs = processor(images=images[start:start + batch_size], return_tensors="pt").to(device)
                if name == "clip_f":
                    output = model.get_image_features(**inputs)
                else:
                    output = model(**inputs).last_hidden_state[:, 0]
                vectors.extend(output.float().cpu().tolist())
        return vectors

    for name, model_id, revision in (("clip_f", clip_model, clip_revision), ("dino_f", dino_model, dino_revision)):
        if name == "clip_f":
            processor = CLIPProcessor.from_pretrained(model_id, revision=revision)
            model = CLIPModel.from_pretrained(model_id, revision=revision).to(device).eval()
        else:
            processor = AutoImageProcessor.from_pretrained(model_id, revision=revision)
            model = AutoModel.from_pretrained(model_id, revision=revision).to(device).eval()
        result[name] = adjacent_cosine(embed(name, model, processor, frames))
        if aligned is not None:
            before = embed(name, model, processor, aligned["source_frames"])
            after = embed(name, model, processor, aligned["output_frames"])
            if name == "dino_f":
                result["source_similarity_dino"] = paired_cosine(before, after)
            elif request:
                with torch.inference_mode():
                    tokens = processor(text=[request], return_tensors="pt", padding=True, truncation=True).to(device)
                    result["clip_text_input"] = clip_text_record(
                        request, processor.tokenizer, tokens,
                        model_max_positions=getattr(getattr(model.config, "text_config", None), "max_position_embeddings", None),
                    )
                    text = model.get_text_features(**tokens).float().cpu().tolist()[0]
                result["target_text_gain_clip"] = text_gain(before, after, text)
        result["encoders"][name] = {"model": model_id, "requested_revision": revision,
                                     "resolved_revision": getattr(model.config, "_commit_hash", None),
                                     "processor": processor.to_dict() if hasattr(processor, "to_dict") else str(type(processor)),
                                     "torch": torch.__version__}
        del model
    if aligned is not None:
        result.setdefault("source_similarity_dino", None)
        result.setdefault("target_text_gain_clip", None)
    return result


def compute(video, *, clip_model='openai/clip-vit-large-patch14', dino_model='facebook/dinov2-large',
            clip_revision='main',dino_revision='main',sample_fps=4.0,device='cpu',batch_size=8,accounting_scope=None,
            source=None,request=None):
    from planner_harness.accounting import run_compute
    from planner_harness.common import sha
    inputs = {'video':str(video),'sha256':sha(video),'clip_model':clip_model,'dino_model':dino_model,
              'clip_revision':clip_revision,'dino_revision':dino_revision,'sample_fps':sample_fps,
              'device':device,'batch_size':batch_size,'implementation':sha(__file__),
              'source_sha256':None if source is None else sha(source),'request':request}
    return run_compute('compute:features',inputs,lambda:_compute(video,clip_model=clip_model,dino_model=dino_model,
        clip_revision=clip_revision,dino_revision=dino_revision,sample_fps=sample_fps,device=device,batch_size=batch_size,
        source=source,request=request),
        binding=accounting_scope,requires_live=True)
