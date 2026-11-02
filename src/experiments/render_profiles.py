"""Shared, explicit renderer contracts for campaign, Planner and PE execution."""
import copy

BERNINI = {"num_inference_steps": 40, "guidance_mode": "v2v_apg", "max_image_size": 848,
           "negative_prompt": "", "prompt_enhancer": False}
DITTO = {"num_inference_steps": 50, "cfg_scale": 5.0, "lora_alpha": 1.0,
         "negative_prompt": "", "prompt_enhancer": False, "tiled": True, "precision": "bfloat16"}


def backend(batch):
    name = batch.get("backend", batch.get("renderer_identity", {}).get("backend", "bernini"))
    if name not in {"bernini", "ditto"}:
        raise ValueError("Supported rendering backends: bernini, ditto")
    return name


def generation(name):
    backend({"backend": name})
    return copy.deepcopy(BERNINI if name == "bernini" else DITTO)


def prompt_guidance(name):
    backend({"backend": name})
    return ("Bernini accepts 512 encoder tokens including its official prefix; use concise concrete English."
            if name == "bernini" else
            "Ditto accepts 512 text-encoder tokens; use concise concrete English. It has no Bernini system prefix.")


def native_output(info, frames, name, dimensions=None):
    output = {"frames": frames, "fps": info["fps"]}
    if name == "ditto":
        # Preserve aspect ratio at <=848 pixels, with native Ditto multiples of 16.
        # A host may instead explicitly freeze one common width/height.
        scale = min(1.0, 848 / max(info["width"], info["height"]))
        size = dimensions or {k: max(16, round(info[k] * scale / 16) * 16) for k in ("width", "height")}
        if set(size) != {"width", "height"} or any(type(v) is not int or v <= 0 or v % 16 for v in size.values()):
            raise ValueError("Ditto output dimensions must be positive multiples of 16")
        output.update(size)
    elif dimensions:
        raise ValueError("Bernini dimensions follow its max_image_size profile")
    return output


def renderer_spec(topic, batch, seed=None):
    name = backend(batch)
    spec = {"backend": name, "seed": batch["seed_sequence"]["start"] if seed is None else seed,
            "output": topic["native_output"], "generation": batch["generation"]}
    if name == "ditto":
        spec["conditioning_source_indices"] = topic["conditioning_source_indices"]
    return spec


def check_host(batch, host):
    name = backend(batch)
    renderer = host.get("renderer", {})
    if renderer.get("backend") != name or renderer.get("generation", generation(name)) != batch["generation"]:
        raise ValueError("Host renderer differs from the frozen batch backend/generation")
    if name == "ditto" and renderer.get("output"):
        if any(any(t["native_output"].get(k) != v for k, v in renderer["output"].items()) for t in batch["topics"]):
            raise ValueError("Host output dimensions differ from the frozen batch")
