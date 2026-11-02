#!/usr/bin/env python3
"""Portable V2V benchmark runner; the colleague handoff runs official PE only.

No Planner or quality judge. This local revision requires the LHA accounting runtime
for future live runs; previously copied frozen runners are not hot-replaced.
Prepare freezes an explicit new dataset; run loads an existing Bernini install.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import hashlib
import html
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
from urllib.parse import quote, urlsplit

VERSION = "bernini-benchmark-v4-unified-accounting"
SAFE = re.compile(r"[A-Za-z0-9_-]+\Z")


def accounting():
    root = Path(__file__).resolve().parents[1]
    if str(root/'src') not in sys.path:sys.path.insert(0,str(root/'src'))
    try:
        from planner_harness import accounting as api
        return api
    except ImportError:
        raise RuntimeError('This new live runner requires its versioned accounting runtime; do not overwrite an older deployed frozen runner') from None


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def signature(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value, *, frozen=False):
    path = Path(path)
    if frozen and path.exists():
        if read(path) != value:
            raise ValueError("Existing frozen record differs: " + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def inspect_video(path):
    if not shutil.which("ffprobe"):
        # The current LHA runtime already has a native PyAV decoder. Reuse it
        # when ffprobe is absent, retaining the portable runner's CFR contract.
        accounting()
        from critic_harness.evidence import metadata
        info = metadata(path)
        step = 1 / info["fps"]
        times = info["times"]
        if any(abs((b - a) - step) > max(1e-6, step * .001) for a, b in zip(times, times[1:])):
            raise ValueError("A constant-frame-rate source is required; convert VFR explicitly first")
        return {k: info[k] for k in ("frames", "fps", "width", "height")}
    result = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate,nb_read_frames",
        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    row = json.loads(result.stdout)["streams"][0]

    def rate(text):
        a, b = text.split("/")
        return int(a) / int(b)

    fps = rate(row["avg_frame_rate"])
    if not math.isfinite(fps) or fps <= 0 or abs(fps - rate(row["r_frame_rate"])) > .001:
        raise ValueError("A constant-frame-rate source is required; convert VFR explicitly first")
    return {"frames": int(row["nb_read_frames"]), "fps": fps,
            "width": int(row["width"]), "height": int(row["height"])}


def prepare(benchmark, output, *, data_root=None, conditions=("pe",), seed=42, splits=None, prompt_forms=None, sample_ids=None):
    benchmark, output = Path(benchmark).resolve(), Path(output).resolve()
    if not conditions or len(set(conditions)) != len(conditions) or set(conditions) - {"direct", "pe"}:
        raise ValueError("Choose direct, pe, or both exactly once")
    if benchmark.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in benchmark.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    else:
        rows = read(benchmark)
        if isinstance(rows, dict):
            rows = rows.get("samples", rows.get("cases"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Benchmark must contain a nonempty samples list or JSONL rows")
    inventory_count = len(rows)
    canonical_rows = [isinstance(r, dict) and str(r.get("benchmark_version", "")).startswith("lha-benchmark-") for r in rows]
    if any(canonical_rows) and not all(canonical_rows):
        raise ValueError("Canonical release rows cannot be mixed with another benchmark format")
    canonical = all(canonical_rows)
    versions = sorted({r.get("benchmark_version", "") for r in rows if isinstance(r, dict)})
    if canonical:
        if len(versions) != 1 or not splits:
            raise ValueError("Select the canonical benchmark splits explicitly with --split train validation test")
        if not prompt_forms:
            raise ValueError("Select prompt forms explicitly with --prompt-form short long")
        if any(r.get("split") not in {"train", "validation", "test"} for r in rows):
            raise ValueError("Canonical benchmark has an unknown split")
    if splits:
        if len(set(splits)) != len(splits) or set(splits) - {"train", "validation", "test"}:
            raise ValueError("Choose each requested split once: train, validation, test")
        available_splits = {r.get("split") for r in rows if isinstance(r, dict)}
        if set(splits) - available_splits:
            raise ValueError("Requested split is absent from this benchmark inventory")
        rows = [r for r in rows if isinstance(r, dict) and r.get("split") in splits]
    if not rows:
        raise ValueError("No samples in the requested splits")
    if sample_ids is not None:
        if not sample_ids or len(set(sample_ids)) != len(sample_ids):
            raise ValueError("Select a nonempty list of unique sample IDs")
        available = {r.get("id", r.get("sample_id")) for r in rows}
        missing = set(sample_ids) - available
        if missing:
            raise ValueError("Sample IDs absent from the requested splits: " + ", ".join(sorted(missing)))
        rows = [r for r in rows if r.get("id", r.get("sample_id")) in set(sample_ids)]
    if data_root:
        root = Path(data_root).resolve()
    elif canonical and benchmark.parent.name == "benchmark_data":
        root = benchmark.parent.parent
    else:
        root = benchmark.parent
    cases, ids, absent = [], set(), []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every benchmark row must be an object")
        sample = row.get("id", row.get("sample_id"))
        if not isinstance(sample, str) or not SAFE.fullmatch(sample) or sample in ids:
            raise ValueError("Sample IDs must be unique and contain only letters, digits, _ or -")
        ids.add(sample)
        relative = row.get("source_video", row.get("video"))
        if not isinstance(relative, str) or not relative:
            raise ValueError(sample + ": source_video is required")
        source = (root / relative).resolve()
        source_sha = digest(source)
        if row.get("source_video_sha256") and row["source_video_sha256"] != source_sha:
            raise ValueError(sample + ": supplied source hash differs")
        info = inspect_video(source)
        frames = ((info["frames"] - 1) // 4) * 4 + 1
        if frames < 5:
            raise ValueError(sample + ": at least five source frames are required")
        if canonical:
            prompt = row.get("instruction")
            if not isinstance(prompt, str) or not prompt.strip() or row.get("prompt_long", prompt) != prompt:
                raise ValueError(sample + ": canonical instruction/compatibility aliases differ")
            prompt_file = root / row["prompt_file"]
            if digest(prompt_file) != row["prompt_file_sha256"] or prompt_file.read_text(encoding="utf-8").strip() != prompt:
                raise ValueError(sample + ": canonical prompt file changed")
            short = row.get("prompt_short")
            if isinstance(short, str) and short.strip():
                short_file = root / row["prompt_short_file"]
                if digest(short_file) != row["prompt_short_file_sha256"] or short_file.read_text(encoding="utf-8").strip() != short:
                    raise ValueError(sample + ": approved short prompt file changed")
            prompts = {"short": short, "long": prompt}
        else:
            prompts = row.get("prompts")
        if prompts is None:
            prompts = {k: row["prompt_" + k] for k in ("short", "long") if "prompt_" + k in row}
            if not prompts:
                prompts = {"single": row.get("prompt", row.get("instruction"))}
        if not isinstance(prompts, dict) or not prompts:
            raise ValueError(sample + ": nonempty prompts mapping is required")
        if prompt_forms:
            if len(set(prompt_forms)) != len(prompt_forms) or set(prompt_forms) - {"short", "long"}:
                raise ValueError("Choose each prompt form once: short, long")
            if set(prompt_forms) - set(prompts):
                raise ValueError(sample + ": requested prompt form is absent")
            prompts = {k: prompts[k] for k in prompt_forms}
        available = 0
        for tier, prompt in prompts.items():
            if not isinstance(tier, str) or not SAFE.fullmatch(tier):
                raise ValueError(sample + ": invalid prompt tier")
            if prompt is None or prompt == "":
                absent.append({"sample_id": sample, "tier": tier, "reason": "not supplied; not synthesized"})
                continue
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(sample + ": prompt must be nonempty text")
            available += 1
            for condition in conditions:
                cases.append({"sample_id": sample, "tier": tier, "condition": condition,
                    "case_id": f"{sample}__{tier}__{condition}",
                    "split": row.get("split", "unspecified"), "origin": row.get("origin", "unspecified"),
                    "source_group": row.get("source_group", sample), "benchmark_version": row.get("benchmark_version"),
                    "source_video": str(source),
                    "source_sha256": source_sha, "source_info": info, "prompt": prompt,
                    "num_frames": frames, "fps": info["fps"], "tail_frames_omitted": info["frames"] - frames,
                    "seed": seed})
        if not available:
            raise ValueError(sample + ": no usable prompt supplied")
    if len({r["case_id"] for r in cases}) != len(cases):
        raise ValueError("Expanded case IDs collide; rename sample IDs or tiers")
    body = {"schema": VERSION, "benchmark_file_sha256": digest(benchmark),
        "sample_count": len(rows), "conditions": list(conditions), "missing_prompts": absent,
        "inventory_count": inventory_count, "benchmark_versions": versions,
        "task_layout": "approved_short_long_prompt_forms" if canonical else "supplied_prompt_tiers",
        "requested_splits": list(splits or []),
        "requested_prompt_forms": list(prompt_forms or []),
        "split_counts": {s: sum(r.get("split", "unspecified") == s for r in rows)
                         for s in sorted({r.get("split", "unspecified") for r in rows})},
        "generation": {"task_type": "v2v", "num_inference_steps": 40, "guidance_mode": "v2v_apg",
                       "max_image_size": 848, "negative_prompt": ""},
        "quality_scoring": "disabled_pending_new_protocol", "cases": cases}
    if sample_ids is not None:
        body["requested_sample_ids"] = list(sample_ids)
    plan = {**body, "sha256": signature(body)}
    write(output / "plan.json", plan, frozen=True)
    return plan


def load_plan(path):
    plan = read(path)
    if plan.get("schema") != VERSION or signature({k: v for k, v in plan.items() if k != "sha256"}) != plan.get("sha256"):
        raise ValueError("Plan identity differs; prepare a new output directory")
    return plan


@contextmanager
def lock(path):
    import fcntl
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = path.open('a+b')
    try:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another process owns this run or GPU: '+str(path)) from None
        yield
    finally:
        try:owned = accounting().active()
        except Exception:owned = []
        if owned:
            import threading
            def release_when_done():
                while accounting().active():time.sleep(.1)
                f.close()
            threading.Thread(target=release_when_done,name='lha-retained-gpu-lock',daemon=False).start()
        else:f.close()


def inventory(directory, *, python_only=False):
    directory = Path(directory).resolve()
    rows = {}
    for p in sorted(directory.rglob("*.py" if python_only else "*")):
        if p.is_file() and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(directory).parts):
            rows[p.relative_to(directory).as_posix()] = digest(p)
    if not rows:
        raise ValueError("Empty code or model inventory: " + str(directory))
    return rows


class OfficialBackend:
    requires_live_budget = True
    def __init__(self, args, plan):
        code, model = args.bernini_code.resolve(), args.model_dir.resolve()
        if not (code / "bernini/cli.py").is_file() or not (model / "config.json").is_file():
            raise ValueError("Supply an existing official Bernini code directory and Diffusers model directory")
        if read(model / "config.json").get("model_type") == "bernini":
            raise ValueError("This runner uses renderer-only Bernini-R weights, not the full latent-planner model")
        sys.path.insert(0, str(code))
        import torch
        from transformers import AutoTokenizer
        from bernini.cli import add_common_args, build_pipeline, generation_kwargs, resolve_system_prompt
        from bernini.pipeline import _prompt_clean
        from bernini import prompt_enhancer
        from bernini.data_utils import VideoFrameReader, smart_video_nframes
        for module in [sys.modules["bernini.cli"], sys.modules["bernini.pipeline"], prompt_enhancer]:
            if not Path(module.__file__).resolve().is_relative_to(code):
                raise ValueError("A different Bernini install is already imported")
        self.torch, self.build, self.kwargs = torch, build_pipeline, generation_kwargs
        self.clean, self.pe_module = _prompt_clean, prompt_enhancer
        self.reader, self.indices = VideoFrameReader, smart_video_nframes
        g = plan["generation"]
        self.cli = add_common_args(argparse.ArgumentParser()).parse_args([
            "--config", str(model), "--task_type", g["task_type"], "--guidance_mode", g["guidance_mode"],
            "--num_inference_steps", str(g["num_inference_steps"]), "--max_image_size", str(g["max_image_size"]),
            "--neg_prompt", g["negative_prompt"]])
        self.tokenizer = AutoTokenizer.from_pretrained(str(model), subfolder="tokenizer", local_files_only=True)
        self.prefix = resolve_system_prompt({"task_type": "v2v"}, self.cli)
        self.pipeline = None
        pe = None
        if "pe" in plan["conditions"]:
            endpoint = args.pe_base_url or os.environ.get("BERNINI_PE_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
            url = urlsplit(endpoint or "")
            if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("Set an explicit PE API base URL without embedded credentials")
            self.pe_key = os.environ.get("BERNINI_PE_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if not self.pe_key and not args.preflight_only:
                raise ValueError("Set BERNINI_PE_API_KEY privately; no API request was made")
            pe = {"base_url": endpoint.rstrip("/"),
                  "model": args.pe_model or os.environ.get("BERNINI_PE_MODEL") or prompt_enhancer.DEFAULT_MODEL,
                  "video_frames": prompt_enhancer.DEFAULT_VIDEO_FRAMES, "outer_attempts": args.pe_attempts,
                  "failure_policy": "retain raw fallback, mark failed, do not render it as PE"}
        packages = {}
        for name in ("torch", "transformers", "diffusers", "openai", "decord", "Pillow", "veomni"):
            try:
                packages[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                packages[name] = "not installed as distribution"
        self.identity = {"runner": VERSION, "runner_sha256": digest(__file__),
            "bernini_sources": inventory(code / "bernini", python_only=True),
            "model_files": inventory(model), "packages": packages, "pe": pe}

    def tokens(self, prompt):
        encoded = self.prefix + self.clean(prompt)
        return len(self.tokenizer(encoded, truncation=False, add_special_tokens=True)["input_ids"]), encoded

    def enhance(self, case, directory):
        self.accounting_scope = accounting().discover(directory,self)
        config = self.identity["pe"]
        pe = self.pe_module.PromptEnhancer(api_key=self.pe_key, base_url=config["base_url"],
            model=config["model"], max_retries=config["outer_attempts"], video_frames=config["video_frames"])
        # Hidden SDK transport retries would bypass per-submission accounting.
        pe.client.max_retries = 0
        create, chat = pe.client.chat.completions.create, pe._chat
        attempts, chat_result = [], []

        def audited_create(**kwargs):
            api = accounting()
            _, policy = api.checked(self.accounting_scope)
            output_limit = next((kwargs[k] for k in ("max_completion_tokens", "max_output_tokens", "max_tokens")
                                 if type(kwargs.get(k)) is int and kwargs[k] > 0), None)
            if policy.get("hard_requirements", {}).get("output_tokens") and output_limit is None:
                raise api.BudgetConfigurationError("Official PE request has no verified hard output-token parameter; no API submission")
            folder = directory / ("attempt-%02d" % (len(attempts) + 1))
            write(folder / "input.json", kwargs, frozen=True)
            attempt = {"input_sha256": digest(folder / "input.json"), "sdk_max_retries": pe.client.max_retries,
                       "output_limit": {"requested_tokens": output_limit, "hard_enforced": output_limit is not None}}
            attempts.append(attempt)
            write(folder / "started.json", {"started_unix": time.time()}, frozen=True)
            try:
                api = accounting()
                if any(item["kind"]=="model" and item.get("topic")==self.accounting_scope["topic"] and item.get("lane")==self.accounting_scope.get("lane","independent") for item in api.active(self.accounting_scope["root"])):
                    raise api.ExternalExecutionUnknown("Original PE request remains owned; no next attempt submitted")
                captured=[]
                def send():
                    value=create(**kwargs);captured.append(value)
                    return value.model_dump(mode="json")
                wire = api.invoke(self.accounting_scope,str(folder.resolve()),"model","model:"+config["model"]+"/none",send,
                    tokens=len(json.dumps(kwargs))//3+int(kwargs.get("max_completion_tokens",kwargs.get("max_output_tokens",kwargs.get("max_tokens",7000)))),
                    usage_getter=lambda:captured[-1].usage.model_dump() if captured and captured[-1].usage else {})
                if captured:result=captured[-1]
                else:
                    from openai.types.chat import ChatCompletion
                    result=ChatCompletion.model_validate(wire)
                write(folder / "response.json", wire, frozen=True)
                attempt.update(response_sha256=digest(folder / "response.json"), usage=result.usage.model_dump() if result.usage else None)
                return result
            except Exception as exc:
                attempt.update(error_type=type(exc).__name__, http_status=getattr(exc, "status_code", None))
                raise
            finally:
                write(folder / "attempt.json", attempt, frozen=True)

        # Keep the official templates, media sampler, payload and retry loop unchanged.
        # The wrapper records success separately from the official raw-prompt fallback.
        original_client = pe.client
        pe.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=audited_create)),
                                    max_retries=original_client.max_retries)

        def audited_chat(*args, **kwargs):
            result = chat(*args, **kwargs)
            chat_result.append(result)
            return result

        pe._chat = audited_chat
        started = time.monotonic()
        try:
            effective = pe("v2v", case["prompt"], video=case["source_video"])
            ok = bool(chat_result and isinstance(chat_result[-1], str) and chat_result[-1].strip())
            record = {"status": "enhanced" if ok else "failed_raw_fallback", "original_prompt": case["prompt"],
                "returned_prompt": effective, "elapsed_seconds": time.monotonic() - started,
                "config": config, "attempts": attempts}
            write(directory / "result.json", record, frozen=True)
            if accounting().active(self.accounting_scope["root"]):
                raise accounting().ExternalExecutionUnknown("PE retained an unresolved original request; raw fallback cannot be rendered")
            if not ok:
                raise RuntimeError("Official PE failed; raw fallback retained but not rendered as an enhanced case")
            return effective, record
        finally:
            if not accounting().active(self.accounting_scope["root"]):original_client.close()

    def render(self, case, prompt, output):
        reader = self.reader(case["source_video"])
        if reader.length != case["source_info"]["frames"] or abs(reader.fps - case["fps"]) > .001:
            raise ValueError("Decoder time axis differs from the prepared source")
        indices = [int(i) for i in self.indices(reader.length, reader.fps, case["fps"], frame_factor=4,
                                              max_frames=case["num_frames"], add_one=True)]
        if indices != list(range(case["num_frames"])):
            raise ValueError("Official sampler does not preserve the prepared native-frame prefix")
        write(output.parent / "conditioning.json", {"indices": indices, "fps": reader.fps,
              "tail_frames_omitted": case["tail_frames_omitted"]}, frozen=True)
        if self.pipeline is None:
            self.torch.cuda.set_device(0)
            properties = self.torch.cuda.get_device_properties(0)
            self.hardware = {"gpu": properties.name, "total_memory_bytes": properties.total_memory,
                             "cuda": self.torch.version.cuda, "torch": self.torch.__version__,
                             "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES")}
            self.pipeline = self.build(self.cli, self.torch.device("cuda:0"))
        write(output.parent / "hardware.json", self.hardware, frozen=True)
        options = self.kwargs(self.cli)
        options.update(num_frames=case["num_frames"], fps=case["fps"], seed=case["seed"])
        write(output.parent / "render-started.json", {"started_unix": time.time(), "options": options}, frozen=True)
        started = time.monotonic()
        self.pipeline(prompt, video=case["source_video"], output_path=str(output), system_prompt=self.prefix, **options)
        return {"generation_seconds": time.monotonic() - started}


def verify_completed(directory, result, expected=None):
    directory = Path(directory).resolve()
    if expected is not None and result["input_sha256"] != expected:
        raise ValueError("Existing case identity differs: " + directory.name)
    if signature(read(directory / "input.json")) != result["input_sha256"]:
        raise ValueError("Completed input binding changed: " + directory.name)
    if digest(directory / "input.json") != result["input_file_sha256"] or digest(directory / "native.mp4") != result["output_sha256"]:
        raise ValueError("Completed input or video changed: " + directory.name)
    for name, value in result["artifact_hashes"].items():
        artifact = (directory / name).resolve()
        if not artifact.is_relative_to(directory) or digest(artifact) != value:
            raise ValueError("Completed trace changed: " + directory.name)


def execute(case, root, plan_sha, backend):
    directory = Path(root) / "cases" / case["case_id"]
    binding = {"case": case, "plan_sha256": plan_sha, "runtime_sha256": signature(backend.identity)}
    expected = signature(binding)
    result_path = directory / "result.json"
    if digest(case["source_video"]) != case["source_sha256"]:
        raise ValueError("Source video changed: " + case["case_id"])
    if result_path.exists():
        previous = read(result_path)
        if previous["input_sha256"] != expected:
            raise ValueError("Existing case identity differs: " + case["case_id"])
        if previous["status"] != "complete":
            raise RuntimeError("Prior failed/interrupted case requires inspection; no external call repeated: " + case["case_id"])
        verify_completed(directory, previous, expected)
        return previous
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError("Uncommitted case artifacts require inspection: " + case["case_id"])
    api = accounting()
    budget_root = Path(root)/"accounting"
    if not (budget_root/"policy.json").exists():
        if getattr(backend,"requires_live_budget",False):
            raise api.BudgetConfigurationError("Live Bernini execution requires an explicit priced budget before any request")
        api.install(budget_root)
    budget_scope = api.scope(budget_root,case["sample_id"],"direct")
    api.checked(budget_scope,require_live=getattr(backend,"requires_live_budget",False))
    api.bind(directory,budget_scope)
    backend.accounting_scope = budget_scope
    write(directory / "input.json", binding, frozen=True)
    record = {"case_id": case["case_id"], "input_sha256": expected,
              "input_file_sha256": digest(directory / "input.json"), "status": "running", "started_unix": time.time()}
    write(result_path, record)
    started = time.monotonic()
    try:
        prompt, pe = case["prompt"], None
        if case["condition"] == "pe":
            prompt, pe = backend.enhance(case, directory / "pe")
        count, encoded = backend.tokens(prompt)
        write(directory / "prompt.json", {"original": case["prompt"], "render_prompt": prompt,
            "encoded_text": encoded, "token_count": count, "token_limit": 512}, frozen=True)
        if not 0 < count <= 512:
            raise ValueError("Effective prompt exceeds the 512-token encoder capacity; no truncation/render")
        output = directory / "native.mp4"
        def render():
            metrics=backend.render(case,prompt,output)
            return {"metrics":metrics,"artifact_sha256":digest(output)}
        rendered = api.invoke(budget_scope,expected+"/render","render","render:bernini",render)
        if digest(output)!=rendered["artifact_sha256"]:raise ValueError("Previously rendered artifact changed")
        metrics = rendered["metrics"]
        actual = inspect_video(output)
        if actual["frames"] != case["num_frames"] or abs(actual["fps"] - case["fps"]) > .001:
            raise ValueError("Rendered frame count or fps differs from the prepared native time axis")
        traces = {p.relative_to(directory).as_posix(): digest(p) for p in sorted(directory.rglob("*"))
                  if p.is_file() and p not in (result_path, output)}
        record.update(status="complete", output_sha256=digest(output), output_info=actual,
                      elapsed_seconds=time.monotonic() - started, **metrics,
                      pe_seconds=pe["elapsed_seconds"] if pe else 0, artifact_hashes=traces)
        write(result_path, record)
        return record
    except BaseException as exc:
        record.update(status="execution_unknown" if getattr(exc,"outcome_unknown",False) else "failed" if isinstance(exc, Exception) else "interrupted",
                      error_type=type(exc).__name__, error=str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__,
                      elapsed_seconds=time.monotonic() - started)
        write(result_path, record)
        raise


def report(root):
    root = Path(root).resolve()
    plan, rows, sources = load_plan(root / "plan.json"), [], {}
    for case in plan["cases"]:
        directory = root / "cases" / case["case_id"]
        result = read(directory / "result.json") if (directory / "result.json").exists() else {"status": "not_started"}
        if result["status"] == "complete":
            try:
                if case["source_video"] not in sources:
                    sources[case["source_video"]] = digest(case["source_video"])
                binding = read(directory / "input.json")
                if sources[case["source_video"]] != case["source_sha256"] or binding["case"] != case or binding["plan_sha256"] != plan["sha256"]:
                    raise ValueError("Source or prepared position changed")
                verify_completed(directory, result)
            except (OSError, ValueError, KeyError):
                result = {"status": "integrity_failed", "error": "Saved video or trace failed hash verification"}
        prompt = read(directory / "prompt.json") if (directory / "prompt.json").exists() else {}
        rows.append({"case_id": case["case_id"], "sample_id": case["sample_id"], "tier": case["tier"],
            "split": case["split"], "origin": case["origin"], "source_group": case["source_group"],
            "condition": case["condition"], "status": result["status"], "seed": case["seed"],
            "frames": case["num_frames"], "fps": case["fps"], "tail_frames_omitted": case["tail_frames_omitted"],
            "generation_seconds": result.get("generation_seconds"), "pe_seconds": result.get("pe_seconds"),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "token_count": prompt.get("token_count"), "output_sha256": result.get("output_sha256"),
            "video": f"cases/{case['case_id']}/native.mp4" if result["status"] == "complete" else "",
            "error": result.get("error", "")})
    by_split = {}
    for split in plan["split_counts"]:
        group = [r for r in rows if r["split"] == split]
        by_split[split] = {"samples": len({r["sample_id"] for r in group}), "positions": len(group),
            "counts": {s: sum(r["status"] == s for r in group) for s in sorted({r["status"] for r in group})},
            "by_prompt_form": {tier: {"positions": sum(r["tier"] == tier for r in group),
                "counts": {s: sum(r["status"] == s and r["tier"] == tier for r in group)
                           for s in sorted({r["status"] for r in group if r["tier"] == tier})}}
                for tier in sorted({r["tier"] for r in group})},
            "by_origin": {origin: {"samples": len({r["sample_id"] for r in group if r["origin"] == origin}),
                "counts": {s: sum(r["status"] == s and r["origin"] == origin for r in group)
                           for s in sorted({r["status"] for r in group if r["origin"] == origin})}}
                for origin in sorted({r["origin"] for r in group})}}
    summary = {"plan_sha256": plan["sha256"], "samples": plan["sample_count"], "positions": len(rows),
        "benchmark_versions": plan["benchmark_versions"], "task_layout": plan["task_layout"], "by_split": by_split,
        "by_prompt_form": {tier: {"sources": len({r["sample_id"] for r in rows if r["tier"] == tier}),
            "positions": sum(r["tier"] == tier for r in rows)} for tier in sorted({r["tier"] for r in rows})},
        "counts": {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})},
        "quality_scoring": plan["quality_scoring"], "monetary_cost": "unknown; token usage retained in PE traces",
        "missing_prompts": plan["missing_prompts"], "cases": rows}
    write(root / "summary.json", summary)
    with (root / "summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    body = ['<!doctype html><meta charset="utf-8"><title>Bernini benchmark</title>',
        '<style>body{font:16px system-ui;max-width:1400px;margin:30px auto;padding:12px}section{border-top:1px solid #ccc;padding:20px 0}.grid{display:flex;gap:16px;flex-wrap:wrap}.card{flex:1;min-width:260px}video{width:100%;max-height:380px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>',
        '<h1>Bernini benchmark</h1><p>Generation comparison. Quality scoring is disabled.</p>',
        '<pre>' + html.escape(json.dumps({k: v for k, v in summary.items() if k != "cases"}, ensure_ascii=False, indent=2)) + '</pre>']
    for sample, tier in dict.fromkeys((c["sample_id"], c["tier"]) for c in plan["cases"]):
        cases = [c for c in plan["cases"] if (c["sample_id"], c["tier"]) == (sample, tier)]
        source = quote(os.path.relpath(cases[0]["source_video"], root).replace(os.sep, "/"), safe="/.")
        body.append('<section><h2>' + html.escape(sample + ' / ' + cases[0]["split"] + ' / ' + tier) + '</h2><p>' + html.escape(cases[0]["prompt"]) + '</p><div class="grid"><div class="card">Source<video controls preload="none" src="' + source + '"></video></div>')
        for c in cases:
            row = next(r for r in rows if r["case_id"] == c["case_id"])
            body.append('<div class="card"><b>' + html.escape(c["condition"] + ': ' + row["status"]) + '</b>')
            if row["video"]:
                body.append('<video controls preload="none" src="' + quote(row["video"], safe="/.") + '"></video>')
            body.append('<details><summary>Record</summary><pre>' + html.escape(json.dumps(row, ensure_ascii=False, indent=2)) + '</pre></details></div>')
        body.append('</div></section>')
    (root / "index.html").write_text("\n".join(body), encoding="utf-8")
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Freeze every supplied sample and prompt tier; no models or API")
    prep.add_argument("--benchmark", type=Path, required=True)
    prep.add_argument("--data-root", type=Path)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--conditions", nargs="+", choices=["direct", "pe"], default=["pe"],
                      help="Colleague handoff is PE only; Direct is run by the experiment owner")
    prep.add_argument("--split", nargs="+", choices=["train", "validation", "test"],
                      help="Required explicit selection for the canonical LHA release")
    prep.add_argument("--prompt-form", nargs="+", choices=["short", "long"],
                      help="Required explicit form selection for LHA releases; each source remains one source sample")
    prep.add_argument("--seed", type=int, default=42)
    run = sub.add_parser("run", help="Run or reuse completed matching cases on one GPU")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--bernini-code", type=Path, required=True)
    run.add_argument("--model-dir", type=Path, required=True)
    run.add_argument("--device", default="0", help="One physical CUDA GPU index")
    run.add_argument("--gpu-lock", type=Path, help="Use the exact same flock file as every other entry point on this GPU")
    run.add_argument("--pe-base-url")
    run.add_argument("--pe-model")
    run.add_argument("--pe-attempts", type=int, default=8, help="Official outer PE attempt bound; SDK retries also recorded")
    run.add_argument("--budget-config",type=Path,help="Required explicit currency, quotes and spending allowance for new live execution")
    run.add_argument("--preflight-only", action="store_true", help="CPU tokenizer/hash checks; no API or GPU model load")
    run.add_argument("--only", nargs="+", help="Explicit case IDs; default is the complete prepared benchmark")
    show = sub.add_parser("report", help="Rebuild CSV/JSON/HTML from saved records without models")
    show.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    if args.command == "prepare":
        plan = prepare(args.benchmark, args.output, data_root=args.data_root, conditions=args.conditions,
                       seed=args.seed, splits=args.split, prompt_forms=args.prompt_form)
        print(json.dumps({"samples": plan["sample_count"], "positions": len(plan["cases"]),
                          "split_counts": plan["split_counts"], "missing_prompts": plan["missing_prompts"]}))
        return 0
    if args.command == "report":
        print(json.dumps(report(args.output)["counts"]))
        return 0
    if not args.device.isdigit() or not 1 <= args.pe_attempts <= 8:
        raise ValueError("Choose one numeric CUDA device and 1–8 outer PE attempts")
    if not args.preflight_only:
        if not args.budget_config:raise ValueError("New live runs require --budget-config; existing deployed frozen scripts are unchanged")
        api=accounting()
        api.install(args.output/"accounting",read(args.budget_config),require_live=True,required_quotes=("render:bernini",))
        from planner_harness.supervisor import maybe_supervise_cli
        if maybe_supervise_cli(args.output,[__file__,*(sys.argv[1:] if argv is None else argv)]):return 0
    os.environ["CUDA_VISIBLE_DEVICES"] = args.device
    root = args.output.resolve()
    with lock(root / ".owner.lock"):
        plan = load_plan(root / "plan.json")
        selected = [c for c in plan["cases"] if not args.only or c["case_id"] in args.only]
        if args.only and set(args.only) - {c["case_id"] for c in selected}:
            raise ValueError("Unknown --only case ID")
        backend = OfficialBackend(args, plan)
        checks = []
        for c in selected:
            if digest(c["source_video"]) != c["source_sha256"]:
                raise ValueError("Prepared source changed: " + c["case_id"])
            count, _ = backend.tokens(c["prompt"])
            if c["condition"] == "direct" and not 0 < count <= 512:
                raise ValueError("Direct prompt exceeds 512 tokens: " + c["case_id"])
            checks.append({"case_id": c["case_id"], "original_token_count": count})
        if args.preflight_only:
            write(root / "preflight-preview.json", {"runtime": backend.identity, "selected": checks,
                "api_calls": 0, "gpu_renders": 0, "pe_output_tokens": "checked after actual enhancement"})
            print(json.dumps({"preflight": "passed", "selected": len(checks), "api_calls": 0, "gpu_renders": 0}))
            return 0
        write(root / "runtime.json", backend.identity, frozen=True)
        gpu_lock = args.gpu_lock or Path('/tmp') / ('lha-bernini-device-' + args.device) / '.run.lock'
        with lock(gpu_lock):
            try:
                for c in selected:
                    print(json.dumps({"case_id": c["case_id"], "stage": "start_or_verified_reuse"}), flush=True)
                    result = execute(c, root, plan["sha256"], backend)
                    print(json.dumps({"case_id": c["case_id"], "status": result["status"]}), flush=True)
            finally:
                summary = report(root)
        print(json.dumps(summary["counts"]))
        return 0 if summary["counts"].get("complete") == len(plan["cases"]) else 2


if __name__ == "__main__":
    try:
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
        from planner_harness.supervisor import cli_entry
        sys.exit(cli_entry(main))
    except Exception as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        sys.exit(1)
