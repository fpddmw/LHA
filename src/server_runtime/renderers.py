"""Resident Bernini and Ditto adapters with owned process/device lifetimes."""

import argparse
from pathlib import Path
import sys
import time

from planner_harness.common import sha as file_hash
from planner_harness.common import load, save
from planner_harness.lock import RunLock


class PersistentRenderer:
    requires_live_budget = True

    def __init__(self, root, config, directory):
        self.root, self.config, self.directory = Path(root), config, Path(directory)
        self.pipeline = None
        self.lock = None
        self.ready = False
        if config.get("backend") != "bernini":
            raise ValueError(
                "Resident service currently supports Bernini; keep Ditto on its existing batch launcher"
            )

    def initialize(self):
        cfg = self.config
        manifest = self.root / cfg["asset_manifest"]
        if file_hash(manifest) != cfg["asset_manifest_sha256"]:
            raise ValueError("Renderer asset manifest changed")
        assets = load(manifest)
        model_dir, code_dir = self.root / assets["model_dir"], self.root / assets["code_dir"]
        expected = {
            str(p.resolve())
            for p in model_dir.rglob("*")
            if p.is_file() and not any(x.startswith(".") for x in p.relative_to(model_dir).parts)
        }
        expected |= {str(p.resolve()) for p in code_dir.rglob("*.py")}
        recorded = {str((self.root / f["path"]).resolve()) for f in assets["files"]}
        if expected != recorded:
            raise ValueError("Renderer asset inventory differs from frozen manifest")
        for row in assets["files"]:
            path = self.root / row["path"]
            if path.stat().st_size != row["bytes"] or file_hash(path) != row["sha256"]:
                raise ValueError("Renderer asset changed: " + row["path"])
        self.assets = assets
        # Operators must use the same host-local device lock path for every service on this GPU.
        self.lock = RunLock(cfg["gpu_lock"])
        self.lock.__enter__()
        try:
            sys.path.insert(0, str(code_dir))
            import torch
            from transformers import AutoTokenizer
            from bernini.cli import (
                add_common_args,
                build_pipeline,
                generation_kwargs,
                resolve_system_prompt,
            )
            from bernini.pipeline import _prompt_clean
            from bernini.data_utils import VideoFrameReader, smart_video_nframes

            self.torch, self.build, self.kwargs = torch, build_pipeline, generation_kwargs
            import os, socket

            properties = torch.cuda.get_device_properties(0)
            self.hardware = {
                "gpu": properties.name,
                "total_memory_bytes": properties.total_memory,
                "cuda": torch.version.cuda,
                "torch": torch.__version__,
                "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                "hostname": socket.gethostname(),
                "renders_per_device": 1,
            }
            self.clean, self.reader, self.indices = (
                _prompt_clean,
                VideoFrameReader,
                smart_video_nframes,
            )
            g = cfg["generation"]
            if (
                set(g)
                != {
                    "num_inference_steps",
                    "guidance_mode",
                    "max_image_size",
                    "negative_prompt",
                    "prompt_enhancer",
                }
                or g["prompt_enhancer"]
            ):
                raise ValueError(
                    "Unsupported Bernini generation profile; no settings may be silently ignored"
                )
            self.cli = add_common_args(argparse.ArgumentParser()).parse_args(
                [
                    "--config",
                    str(model_dir),
                    "--task_type",
                    "v2v",
                    "--guidance_mode",
                    g["guidance_mode"],
                    "--num_inference_steps",
                    str(g["num_inference_steps"]),
                    "--max_image_size",
                    str(g["max_image_size"]),
                    "--neg_prompt",
                    g["negative_prompt"],
                ]
            )
            self.prefix = resolve_system_prompt({"task_type": "v2v"}, self.cli)
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(model_dir), subfolder="tokenizer", local_files_only=True
            )
            self.ready = True
        except BaseException:
            self.close()
            raise

    def prepare(self, job, directory):
        payload, directory = job["payload"], Path(directory)
        cfg = payload["renderer"]
        if cfg["backend"] != "bernini" or cfg["generation"] != self.config["generation"]:
            raise ValueError("Task generation profile differs from resident model")
        source = Path(payload["input"]["path"])
        if file_hash(source) != payload["input"]["sha256"]:
            raise ValueError("Conditioning video changed")
        if not self.ready:
            self.initialize()
        sys.path.insert(0, str(self.root / "scripts/deploy"))
        from run_prompt_probe import inspect_video

        info, output = inspect_video(source), cfg["output"]
        count, fps = output["frames"], output["fps"]
        if type(cfg.get("seed")) is not int or count < 1 or count % 4 != 1 or fps <= 0:
            raise ValueError("Explicit seed and valid native frame configuration required")
        encoded_text = self.prefix + self.clean(payload["prompt"])
        tokens = len(
            self.tokenizer(encoded_text, truncation=False, add_special_tokens=True)["input_ids"]
        )
        if not 0 < tokens <= 512:
            save(directory / "prompt-length.json", {
                "request_sha256": job.get("sha256"), "token_count": tokens,
                "token_limit": 512, "includes_official_prefix": True,
            })
            raise ValueError("Prompt exceeds tokenizer limit; automatic truncation is disabled")
        reader = self.reader(str(source))
        indices = [
            int(i)
            for i in self.indices(
                reader.length, reader.fps, fps, frame_factor=4, max_frames=count, add_one=True
            )
        ]
        if len(indices) != count or min(indices) < 0 or max(indices) >= info["frames"]:
            raise ValueError("Conditioning time axis does not fit the requested native frames")
        if payload["input_id"] != "source" and (
            indices != list(range(count))
            or info["frames"] != count
            or abs(info["fps"] - fps) > 0.001
        ):
            raise ValueError("Iterative editing must preserve the native time axis")
        save(
            directory / "renderer-input.json",
            {
                "request": job,
                "encoded_text": encoded_text,
                "system_prompt": self.prefix,
                "token_count": tokens,
                "conditioning_source_indices": indices,
            },
        )
        if self.pipeline is None:
            self.pipeline = self.build(self.cli, self.torch.device("cuda:0"))
            save(
                self.directory / "model-loaded.json",
                {
                    "at": time.time(),
                    "asset_manifest_sha256": self.config["asset_manifest_sha256"],
                    "torch": self.torch.__version__,
                    "cuda": self.torch.version.cuda,
                },
            )
        return info, indices, tokens

    def __call__(self, job, directory):
        info, indices, tokens = self.prepare(job, directory)
        payload, directory = job["payload"], Path(directory)
        cfg = payload["renderer"]
        source, output = Path(payload["input"]["path"]), cfg["output"]
        count, fps = output["frames"], output["fps"]
        encoded_text = self.prefix + self.clean(payload["prompt"])
        started = time.time()
        options = self.kwargs(self.cli)
        options.update(num_frames=count, fps=fps, seed=cfg["seed"])
        native = directory / "native.mp4"
        self.pipeline(
            payload["prompt"],
            video=str(source),
            output_path=str(native),
            system_prompt=self.prefix,
            **options,
        )
        sys.path.insert(0, str(self.root / "scripts/deploy"))
        from run_prompt_probe import inspect_video

        actual = inspect_video(native)
        if (
            actual["frames"] != count
            or abs(actual["fps"] - fps) > 0.001
            or any(actual[k] != output[k] for k in ("width", "height") if k in output)
        ):
            raise ValueError("Rendered dimensions/time axis differ from signed job")
        return {
            "video": {"path": str(native), "sha256": file_hash(native)},
            "execution": {
                "backend": "bernini",
                "requested_prompt": payload["prompt"],
                "effective_prompt": payload["prompt"],
                "encoded_text": encoded_text,
                "system_prompt": self.prefix,
                "prompt_transforms": ["official Bernini prefix + _prompt_clean at encoder"],
                "input_sha256": payload["input"]["sha256"],
                "conditioning_source_indices": indices,
                "input_fps": info["fps"],
                "output_fps": fps,
                "settings": cfg["generation"],
                "seed": cfg["seed"],
                "model_revision": self.assets["model_revision"],
                "code_revision": self.assets["code_revision"],
                "asset_manifest_sha256": self.config["asset_manifest_sha256"],
                "tokenizer_revision": self.assets["model_revision"],
                "token_count": tokens,
                "token_limit": 512,
                "preflight": "passed",
                "generation_seconds": time.time() - started,
                "hardware": getattr(self, "hardware", None),
            },
        }

    def close(self):
        self.pipeline = None
        self.ready = False
        if self.lock:
            self.lock.__exit__(None, None, None)
            self.lock = None


def _renderer_process(root, config, directory, connection):
    """This process exclusively owns its pipeline and device lock."""
    import os

    renderer = None
    try:
        try:
            os.setsid()
            if config.get("backend") == "ditto":
                from .ditto import PersistentDittoRenderer

                renderer = PersistentDittoRenderer(root, config, directory)
            elif config.get("backend") == "bernini":
                renderer = PersistentRenderer(root, config, directory)
            else:
                raise ValueError("Unsupported resident renderer backend")
            renderer.initialize()
            if config["backend"] == "ditto":
                renderer.load_pipeline()
            else:
                renderer.pipeline = renderer.build(renderer.cli, renderer.torch.device("cuda:0"))
            save(
                Path(directory) / "model-loaded.json",
                {
                    "at": time.time(),
                    "asset_manifest_sha256": config["asset_manifest_sha256"],
                    "hardware": getattr(renderer, "hardware", None),
                },
            )
        except Exception as exc:
            connection.send({"status": "failed", "error_type": type(exc).__name__,
                             "error": f"Renderer initialization failed: {type(exc).__name__}: {exc}"})
            return
        connection.send({"status": "ready"})
        while True:
            action, job, folder = connection.recv()
            if action == "close":
                return
            try:
                value = (
                    renderer.prepare(job, folder) if action == "prepare" else renderer(job, folder)
                )
                connection.send(
                    {"status": "complete", "payload": None if action == "prepare" else value}
                )
            except Exception as exc:
                connection.send(
                    {"status": "failed", "error_type": type(exc).__name__, "error": str(exc)}
                )
    finally:
        try:
            if renderer is not None:
                renderer.close()
        finally:
            connection.close()


class ProcessRenderer:
    """Resident pipeline with a verifiable, service-owned cancellation boundary."""

    requires_live_budget = True

    def __init__(self, root, config, directory):
        self.arguments = (str(root), config, str(directory))
        self.process = None
        self.connection = None

    def initialize(self):
        if self.process is not None and self.process.is_alive():
            if self.connection.closed:
                raise RuntimeError("Failed renderer initialization is still shutting down")
            return
        import multiprocessing

        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        self.connection = parent
        self.process = context.Process(
            target=_renderer_process, args=(*self.arguments, child), daemon=True
        )
        self.process.start()
        child.close()
        from planner_harness.owned_process import birth

        self.birth = birth(self.process.pid)
        try:
            self._receive()
        except Exception:
            parent.close()
            self.process.join(timeout=2)
            raise

    def _receive(self):
        while not self.connection.poll(0.1):
            if not self.process.is_alive():
                from planner_harness.accounting import ExternalExecutionUnknown

                raise ExternalExecutionUnknown("Owned renderer exited without its original receipt")
        try:
            result = self.connection.recv()
        except EOFError as exc:
            from planner_harness.accounting import ExternalExecutionUnknown

            raise ExternalExecutionUnknown("Owned renderer pipe closed without its original receipt") from exc
        if result["status"] == "failed":
            raise ValueError(result["error"])
        return result.get("payload")

    def prepare(self, job, directory):
        from planner_harness.accounting import register_cancel, submission_guard

        with submission_guard():
            self.initialize()
            remove = register_cancel(self.cancel)
            self.connection.send(("prepare", job, str(directory)))
        try:
            self._receive()
        finally:
            remove()

    def __call__(self, job, directory):
        from planner_harness.accounting import register_cancel, submission_guard

        with submission_guard():
            remove = register_cancel(self.cancel)
            self.connection.send(("render", job, str(directory)))
        try:
            return self._receive()
        finally:
            remove()

    def cancel(self):
        from planner_harness.owned_process import birth

        proc = self.process
        if proc is None:
            return {"local_stopped": True, "resource_released": True}
        identity = self.birth is not None and birth(proc.pid) == self.birth
        if proc.is_alive() and identity:
            import os, signal

            if os.getpgid(proc.pid) != proc.pid:
                return {
                    "pid": proc.pid,
                    "local_stopped": False,
                    "resource_released": False,
                    "reason": "Owned process-group identity unavailable",
                }
            os.killpg(proc.pid, signal.SIGTERM)
            proc.join(timeout=2)
            if proc.is_alive():
                os.killpg(proc.pid, signal.SIGKILL)
                proc.join(timeout=2)
        stopped = not proc.is_alive()
        return {
            "pid": proc.pid,
            "birth": self.birth,
            "identity_verified": identity,
            "local_stopped": stopped,
            "resource_released": stopped,
            "scope": "Only this dedicated renderer process and its CUDA context",
        }

    def close(self):
        if self.process is None:
            return
        if self.process.is_alive() and not self.connection.closed:
            try:
                self.connection.send(("close", None, None))
            except OSError:
                pass
            self.process.join(timeout=2)
        if self.process.is_alive():
            return self.cancel()
        return {"local_stopped": True}
