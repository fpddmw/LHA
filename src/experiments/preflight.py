"""Offline and bounded provider checks; never rents hardware or renders with Bernini."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from planner_harness.common import load, save, sha
from planner_harness.execution import signature


def local_preflight(root, output):
    from planner_harness.creative_knowledge import CreativeKnowledge
    from planner_harness.creative import experiment_profile
    from critic_harness.one_shot import frozen_profile
    root, output = Path(root).resolve(), Path(output).resolve()
    full = CreativeKnowledge(root, experience_mode="full")
    none = CreativeKnowledge(root, experience_mode="none")
    entries = {r["id"] for r in full.curated_catalog["entries"]}
    resources = {r["id"] for r in full.curated_catalog["resources"]}
    if len(entries) != 14 or (entries | resources) & set(none.items):
        raise ValueError("Experience catalog or isolation is incomplete")
    forbidden = ("knowledge/experience/", "knowledge/staged/", "knowledge/wiki/", "knowledge/model-experience/", "out/", "_deprecated/")
    if any(p.startswith(forbidden) for p in none.paths):
        raise ValueError("No-experience scope exposes excluded material")
    for mode, knowledge in (("full", full), ("none", none)):
        for identity in ("map", "manual", "understand-and-design", "understand-and-revise", "meaning", "design-expression", "score-definitions"):
            knowledge.read(identity)
        if not knowledge.search("watercolor")["matches"]:
            raise ValueError("Style search missing")
        # Check local links in model-facing prose, not copied immutable source records.
        import re
        for path in knowledge.paths:
            if not path.startswith(("knowledge/creative-loop/", "knowledge/experience/curated/entries/")) or not path.endswith(".md"):
                continue
            text = (root / path).read_text()
            for link in re.findall(r"\]\(([^\s)]+)\)", text):
                target = link.split("#", 1)[0]
                if target and not target.startswith(("https:", "http:")) and not (root / path).parent.joinpath(target).exists():
                    raise ValueError("Broken active manual/entry link: " + path + " -> " + target)
    result = {"status": "passed", "full_curated_entries": len(entries), "full_curated_resources": len(resources),
              "none_curated_entries": len(none.curated_catalog["entries"]), "style_entries_each": len(full.manifest["entries"]),
              "same_critic": frozen_profile()["sha256"], "experiment_profile_sha256": experiment_profile(root)["sha256"],
              "live_model_calls": 0, "gpu_jobs": 0}
    save(output / "local-preflight.json", result)
    return result


def host_preflight(root, host, *, execute=False):
    """Run on the opened host; verify assets/devices without loading a GPU model."""
    root = Path(root)
    from .creative_fewshot import GENERATION
    if not host:
        return {"status": "awaiting_open_host", "gpu_jobs": 0}
    cfg = host.get("renderer", {})
    if cfg.get("generation", GENERATION) != GENERATION:
        raise ValueError("Host rendering settings differ from the experiment")
    path = root / cfg["asset_manifest"]
    if sha(path) != cfg["asset_manifest_sha256"]:
        raise ValueError("Asset manifest hash mismatch")
    assets = load(path)
    for row in assets["files"]:
        file = root / row["path"]
        if not file.is_file() or file.stat().st_size != row["bytes"] or sha(file) != row["sha256"]:
            raise ValueError("Missing or changed renderer asset: " + row["path"])
    if not shutil.which("ffprobe"):
        raise ValueError("ffprobe is required for the renderer's native-time checks")
    if execute:
        command = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid,name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, check=True)
        devices = {line.split(",", 1)[0].strip() for line in command.stdout.splitlines()}
        if not set(map(str, host["devices"])) <= devices:
            raise ValueError("Requested GPU is absent")
        # Check exact Direct prompts on CPU before loading a resident GPU pipeline.
        import sys
        import argparse
        sys.path.insert(0, str(root / assets["code_dir"]))
        from transformers import AutoTokenizer
        from bernini.cli import add_common_args, resolve_system_prompt
        from bernini.pipeline import _prompt_clean
        model_dir = root / assets["model_dir"]
        args = add_common_args(argparse.ArgumentParser()).parse_args(["--config", str(model_dir), "--task_type", "v2v"])
        prefix = resolve_system_prompt({"task_type": "v2v"}, args)
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir), subfolder="tokenizer", local_files_only=True)
        counts = {row["sample_id"]: len(tokenizer(prefix + _prompt_clean(row["prompt_long"]), truncation=False, add_special_tokens=True)["input_ids"])
                  for row in load(root / "benchmark_data/fewshot_index.json")}
        if any(not 0 < n <= 512 for n in counts.values()):
            raise ValueError("An exact Direct prompt exceeds Bernini's encoder capacity; do not truncate it")
        executable = os.environ.get("LOW_HIGH_CODEX_BIN") or shutil.which("codex")
        if not executable:
            raise ValueError("Install and authenticate the host Codex transport before rendering")
        login = subprocess.run([executable, "login", "status"], capture_output=True, timeout=30)
        if login.returncode:
            raise ValueError("Host Codex authentication is not ready")
    else:
        counts = None
    return {"status": "passed", "asset_manifest_sha256": cfg["asset_manifest_sha256"], "direct_prompt_tokens": counts, "gpu_jobs": 0}


def provider_identity(name="glm5.3flash"):
    from critic_harness.one_shot import frozen_profile
    from evaluation.creative import judge_identity
    root = Path(__file__).resolve().parents[2]
    return {**judge_identity(name), "rubric_sha256": frozen_profile()["sha256"],
            "adapter_sha256": sha(root / "src/evaluation/creative.py")}


def provider_directory(output, name):
    return Path(output) if name == "glm5.3flash" else Path(output) / name


def provider_preflight(output, *, model=None, name="glm5.3flash"):
    """One real synthetic-media contract check, stored outside all benchmark judgments."""
    import av
    import numpy as np
    from planner_harness.video import Video
    from evaluation.creative import make_judge, judge_candidate
    batch_output = Path(output)
    output = provider_directory(output, name)
    directory = output / "provider-capability"
    media_directory = batch_output / "provider-capability"
    directory.mkdir(parents=True, exist_ok=True)
    media_directory.mkdir(parents=True, exist_ok=True)
    identity = provider_identity(name)
    existing = output / "provider-preflight.json"
    if existing.exists():
        return verify_provider_receipt(batch_output, name)
    for media_name, color in (("source", (220, 30, 30)), ("candidate", (30, 60, 220))):
        path = media_directory / (media_name + ".mp4")
        if not path.exists():
            with av.open(str(path), "w") as container:
                stream = container.add_stream("libx264", rate=12)
                stream.width = stream.height = 128
                stream.pix_fmt = "yuv420p"
                for i in range(49):
                    frame = np.full((128, 128, 3), 235, dtype=np.uint8)
                    frame[32:96, 24 + i // 4:72 + i // 4] = color
                    for packet in stream.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")):
                        container.mux(packet)
                for packet in stream.encode():
                    container.mux(packet)
    try:
        client = model or make_judge(name)
        if client.model != name:
            raise ValueError("Provider preflight model does not match its named slot")
        result = judge_candidate("Change the moving red square to blue. Retain its shape, motion and pale background.",
            Video(media_directory / "source.mp4", directory).info, Video(media_directory / "candidate.mp4", directory).info,
            directory / "contract", model=client)
        report = result["report"]
        adherence = report["main_scores"]["instruction_adherence"]
        if adherence["status"] != "scored" or adherence["score"] < 3:
            raise ValueError("Synthetic visible color change was not recognized; inspect provider capability")
        receipt = {"status": "passed", "identity": identity, "synthetic_only": True,
                   "base_url": client.base_url if hasattr(client, "base_url") else "software-fixture",
                   "judgment_path": str(directory / "contract/judgment.json"),
                   "judgment_sha256": sha(directory / "contract/judgment.json"),
                   "evidence_image_count": len(load(directory / "contract/evidence/request.json")["images"])}
        save(existing, receipt)
        return receipt
    except Exception as exc:
        save(output / "provider-preflight-failure.json", {"status": "blocked", "identity": identity,
             "error_type": type(exc).__name__, "error": str(exc), "synthetic_only": True})
        raise


def verify_provider_receipt(output, name="glm5.3flash"):
    receipt = load(provider_directory(output, name) / "provider-preflight.json")
    if receipt["status"] != "passed" or receipt["identity"] != provider_identity(name) or receipt["base_url"] == "software-fixture":
        raise ValueError("A successful exact-model real-provider capability check is required")
    if sha(receipt["judgment_path"]) != receipt["judgment_sha256"]:
        raise ValueError("Provider capability evidence changed")
    from evaluation.creative import make_judge
    if make_judge(name).base_url != receipt["base_url"]:
        raise ValueError("Provider endpoint differs from its successful preflight")
    return receipt
