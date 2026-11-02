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
    # CreativeKnowledge verifies the reviewed catalog and its document hashes.
    # Check its actual membership so authorized additions need no count migration.
    if not entries or not (entries | resources) <= set(full.items) or (entries | resources) & set(none.items):
        raise ValueError("Experience catalog or isolation is incomplete")
    forbidden = ("knowledge/experience/", "knowledge/staged/", "knowledge/wiki/", "knowledge/model-experience/", "out/", "_deprecated/")
    if any(p.startswith(forbidden) for p in none.paths):
        raise ValueError("No-experience scope exposes excluded material")
    for mode, knowledge in (("full", full), ("none", none)):
        for identity in ("map", "manual", "understand-and-design", "understand-and-revise", "meaning", "design-expression"):
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
    from .creative_benchmark import GENERATION
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
        counts = {row["sample_id"]: len(tokenizer(prefix + _prompt_clean(row["instruction"]), truncation=False, add_special_tokens=True)["input_ids"])
                  for row in load(root / "benchmark_data/benchmark.json") if row["split"] == "train"}
        if any(not 0 < n <= 512 for n in counts.values()):
            raise ValueError("An exact Direct prompt exceeds Bernini's encoder capacity; do not truncate it")
    else:
        counts = None
    models = api_model_preflight(host, require_credentials=execute)
    return {"status": "passed", "asset_manifest_sha256": cfg["asset_manifest_sha256"], "direct_prompt_tokens": counts, "api_models":models,"gpu_jobs": 0,"model_calls":0}


def api_model_preflight(host, *, require_credentials=False):
    """Inspect declared API configuration without CLI/login probes or network calls."""
    from planner_harness.creative import role_settings
    rows={}
    roles=['planner']
    if host.get('review',{}).get('mode','critic')=='critic' or 'direct-best-of-n' in host.get('methods',[]):roles.append('online_critic')
    for role in roles:
        spec=host.get('models',{}).get(role,{})
        factory=spec.get('factory','vlm.openrouter:OpenRouterVisionModel')
        if 'codex' in factory.lower():raise ValueError('Current experiments require API vision factories')
        settings=role_settings(host,role)
        configured=None
        if factory=='vlm.chatgpt_subscription:ChatGPTSubscriptionVisionModel':
            from vlm.chatgpt_auth import credential_status
            options=spec.get('options',{})
            state=credential_status(options.get('credential_file')) if not options.get('relay_url') else None
            configured=bool(options.get('relay_url')) or (state['configured'] and state['plan_usage_granted'])
            if require_credentials and not configured:
                raise ValueError('Authorize ChatGPT plan usage with scripts/chatgpt_subscription.py login')
        if factory=='vlm.openrouter:OpenRouterVisionModel':
            from vlm.openrouter import load_credentials
            load_credentials(spec.get('options',{}).get('credential_file'))
            configured=bool(os.environ.get(spec.get('options',{}).get('api_key_env','OPENROUTER_API_KEY')))
            if require_credentials and not configured:raise ValueError('API credentials are not configured; no model request made')
        rows[role]={'factory':factory,**settings,'credential_configured':configured,'network_checked':False}
    return rows


def provider_identity(name=None):
    from evaluation.low_high import profile as final_profile
    from evaluation.providers import JUDGES,judge_identity
    name=name or JUDGES[0]
    root = Path(__file__).resolve().parents[2]
    return {**judge_identity(name), "rubric_sha256": final_profile()["sha256"],
            "adapter_sha256": sha(root / "src/evaluation/creative.py")}


def provider_directory(output, name=None):
    from evaluation.providers import JUDGES
    name=name or JUDGES[0]
    return Path(output) if name == JUDGES[0] else Path(output) / name


def provider_preflight(output, *, model=None, name=None):
    """One real synthetic-media contract check, stored outside all benchmark judgments."""
    import av
    import numpy as np
    from planner_harness.video import Video
    from evaluation.creative import make_judge, judge_candidate
    from evaluation.providers import JUDGES
    name=name or JUDGES[0]
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
        request = "Change the moving red square to blue. Retain its shape, motion and pale background."
        source = Video(media_directory/'source.mp4',directory).info
        from evaluation.low_high import freeze_plan
        plan = freeze_plan({'track':'long','events':[],
            'motion_preservation':{'required':True,'reason':'Explicit synthetic motion retention','regions':[]}},
            request,source,directory/'source-plan')
        result = judge_candidate(request,source,Video(media_directory/'candidate.mp4',directory).info,
            directory/'contract',model=client,plan=plan)
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


def verify_provider_receipt(output, name=None):
    from evaluation.providers import JUDGES
    name=name or JUDGES[0]
    receipt = load(provider_directory(output, name) / "provider-preflight.json")
    if receipt["status"] != "passed" or receipt["identity"] != provider_identity(name) or receipt["base_url"] == "software-fixture":
        raise ValueError("A successful exact-model real-provider capability check is required")
    if sha(receipt["judgment_path"]) != receipt["judgment_sha256"]:
        raise ValueError("Provider capability evidence changed")
    from evaluation.creative import make_judge
    if make_judge(name).base_url != receipt["base_url"]:
        raise ValueError("Provider endpoint differs from its successful preflight")
    return receipt
