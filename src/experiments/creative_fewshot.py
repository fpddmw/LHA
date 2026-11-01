"""Topic-at-a-time Direct/full/no-experience comparison using existing runtime jobs."""
from __future__ import annotations

import atexit
import copy
import html
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import uuid

from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock
from evaluation.creative import JUDGES, judge_identity

ARMS = ("direct", "full", "none")
GENERATION = {"num_inference_steps": 40, "guidance_mode": "v2v_apg", "max_image_size": 848,
              "negative_prompt": "", "prompt_enhancer": False}
SEEDS = {"start": 42, "step": 1}
PAIRS = (("direct", "full_first"), ("direct", "none_first"),
         ("full_first", "full_final"), ("none_first", "none_final"),
         ("none_first", "full_first"), ("none_final", "full_final"))


def prepare(root, output):
    from planner_harness.creative import experiment_profile
    from planner_harness.video import Video
    root, output = Path(root).resolve(), Path(output).resolve()
    with RunLock(output / "batch-owner"):
        rows = load(root / "benchmark_data/fewshot_index.json")
        if len(rows) != 7 or len({r["sample_id"] for r in rows}) != 7:
            raise ValueError("This cohort contains exactly seven distinct fewshot tasks")
        topics = []
        for r in rows:
            source, prompt = root / r["source_video"], root / r["prompt_file"]
            if sha(source) != r["source_video_sha256"] or sha(prompt) != r["prompt_file_sha256"]:
                raise ValueError("Benchmark source or prompt changed")
            if r["prompt_long"] != r["instruction"] or prompt.read_text().strip() != r["prompt_long"].strip():
                raise ValueError("Direct and both Loops must receive the exact same long request")
            info = Video(source, output / "source-info" / r["sample_id"]).info
            frames = ((info["frames"] - 1) // 4) * 4 + 1
            topics.append({"id": r["sample_id"], "source": r["source_video"], "source_sha256": r["source_video_sha256"],
                "request": r["prompt_long"], "source_info": info, "native_output": {"frames": frames, "fps": info["fps"]},
                "tail_frames_omitted": info["frames"] - frames})
        profile = experiment_profile(root)
        immutable(output / "profile.json", profile)
        body = {"schema": "creative-fewshot-three-arm-v1", "data_role": "development_regression",
                "arms": list(ARMS), "topics": topics, "generation": GENERATION, "seed_sequence": SEEDS,
                "completion_mode": "delivery", "max_generations": None, "max_turns": None,
                "profile_sha256": profile["sha256"], "judges": [judge_identity(j) for j in JUDGES]}
        immutable(output / "batch.json", {**body, "sha256": signature(body)})
        return body


def verify_batch(root, output):
    from planner_harness.creative import verify_experiment
    output = Path(output)
    batch = load(output / "batch.json")
    if signature({k: v for k, v in batch.items() if k != "sha256"}) != batch["sha256"]:
        raise ValueError("Batch manifest changed")
    profile = verify_experiment(output / "profile.json", root)
    if profile["sha256"] != batch["profile_sha256"]:
        raise ValueError("Batch profile mismatch")
    if batch["generation"] != GENERATION or batch["seed_sequence"] != SEEDS or batch["arms"] != list(ARMS):
        raise ValueError("Frozen experimental conditions differ")
    if batch["judges"] != [judge_identity(j) for j in JUDGES]:
        raise ValueError("Both independent judges must retain their frozen model and effort")
    if batch["max_generations"] is not None or batch["max_turns"] is not None or batch["completion_mode"] != "delivery":
        raise ValueError("This cohort ends at delivery, with no fixed generation or turn count")
    for topic in batch["topics"]:
        if sha(Path(root) / topic["source"]) != topic["source_sha256"]:
            raise ValueError("Source changed after preparation")
    return batch


def task_spec(topic, arm, batch, profile_path):
    if arm not in {"full", "none"}:
        raise ValueError("Direct is a renderer job, not a Planner task")
    return {"id": topic["id"] + "__" + arm, "workflow": "creative_loop_v1",
            "source": topic["source"], "source_sha256": topic["source_sha256"], "request": topic["request"],
            "completion_mode": "delivery", "max_generations": None, "max_turns": None,
            "max_context_chars": 180000,
            "execution": {"mode": "live", "experience_mode": arm, "experiment_profile": str(profile_path),
                "seed_sequence": batch["seed_sequence"], "renderer": renderer_spec(topic, batch)},
            "run_instructions": "Complete the user's video task using the limited budget deliberately. "
                "Choose prompts, input candidates, optional independent review and delivery yourself. "
                "Answer continuation questions in the generate justification when requested. "
                "A satisfied finish proposes delivery; inspect the complete reused or newly requested report in the next input, then confirm or continue. "
                "Bernini accepts 512 encoder tokens including its official prefix; use concrete English that fits. "
                "The rendering seed sequence is fixed by the experiment. A blocked or interrupted task remains incomplete."}


def renderer_spec(topic, batch):
    return {"backend": "bernini", "seed": batch["seed_sequence"]["start"],
            "output": topic["native_output"], "generation": batch["generation"]}


def direct_request(root, topic, batch):
    body = {"id": topic["id"] + "-direct", "kind": "generate", "mode": "live", "payload": {
        "input_id": "source", "input": {**topic["source_info"], "path": str((Path(root) / topic["source"]).resolve())},
        "prompt": topic["request"], "renderer": renderer_spec(topic, batch)}}
    return {**body, "sha256": signature(body)}


_WORKER = None
_WORKER_ARGS = None


def init_worker(device, root, output, host):
    # Each process owns one visible physical GPU. Model and pipeline persist across topics.
    global _WORKER_ARGS
    os.environ["CUDA_VISIBLE_DEVICES"] = str(device)
    _WORKER_ARGS = (device, root, output, host)


def worker_state():
    global _WORKER
    if _WORKER is not None:
        return _WORKER
    device, root, output, host = _WORKER_ARGS
    from server_runtime.queue import Queue
    from server_runtime.service import Service
    class ResidentService(Service):
        def close(self):
            pass
    directory = Path(output) / "workers" / str(device)
    cfg = {"workflow": "creative_loop_v1", "planner": {"model": "gpt-6.1-sol", "reasoning_effort": "high"},
           "critic": {"model": "gpt-6.1-sol", "reasoning_effort": "high"}, "enable_final_evaluation": False,
           "experiment_profile": str(Path(output) / "profile.json"),
           "renderer": {**host["renderer"], "backend": "bernini", "generation": GENERATION,
                        "gpu_lock": str(Path(host.get("lock_directory", "/tmp")) / ("lha-bernini-device-" + str(device)))}}
    if host.get("models"):
        cfg["models"] = host["models"]
    queue = Queue(directory / "queue.sqlite3", {"gpu": 1, "llm": 1, "cpu": 1})
    service = ResidentService(queue, directory, root, cfg)
    atexit.register(Service.close, service)
    _WORKER = (Path(root), Path(output), queue, service, directory)
    return _WORKER


def run_arm(topic, arm):
    from planner_harness.delivery import verify_delivery
    from planner_harness.video import Video
    from server_runtime.engine import Engine
    root, output, queue, service, directory = worker_state()
    batch = verify_batch(root, output)
    os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(output / "topics" / topic["id"] / (arm + "-model-usage.jsonl"))
    if arm == "direct":
        jobdir = directory / "direct" / topic["id"]
        job = direct_request(root, topic, batch)
        immutable(jobdir / "request.json", job)
        queue.enqueue(topic["id"] + "/direct", "tool", "gpu",
                      {"request": str(jobdir / "request.json"), "request_sha256": job["sha256"]})
        Engine(queue, directory, service, service.expand).run(once=True)
        response = load(jobdir / "response.json")
        if response["status"] != "complete" or response["request_sha256"] != job["sha256"]:
            raise RuntimeError("Direct render is incomplete; recover its existing job")
        video = response["payload"]["video"]
        info = Video(video["path"], jobdir).info
        result = {"arm": arm, "selected": "v1", "first": "v1", "record_directory": str(jobdir),
                  "videos": {"v1": {**info, "execution": response["payload"].get("execution", {})}}}
        completion_record = jobdir / "response.json"
    else:
        task = task_spec(topic, arm, batch, output / "profile.json")
        service.submit(task)
        Engine(queue, directory, service, service.expand).run(once=True)
        run = directory / "tasks" / task["id"] / "run"
        delivery = verify_delivery(run)
        state = load(run / "state.json")
        videos = {k: v for k, v in state["videos"].items() if k != "source" and not v.get("imported")}
        result = {"arm": arm, "selected": delivery["selected"], "first": next(iter(videos)),
                  "delivery_review":state['final']['delivery_review'],
                  "record_directory": str(run), "videos": videos}
        completion_record = run / "state.json"
    result["queue_jobs"] = [r for r in queue.rows() if r["key"].startswith(topic["id"])]
    folders = [Path(result["record_directory"])] if arm == "direct" else [run / "jobs" / k for k,j in state["jobs"].items() if j["kind"] == "generate"]
    result["generation_requests"] = [{"request_sha256": load(folder / "request.json")["sha256"],
        "response": load(folder / "response.json") if (folder / "response.json").exists() else None} for folder in folders]
    result["binding"] = {"topic": topic["id"], "source": topic["source_sha256"],
        "request": signature({"text": topic["request"]}), "profile": batch["profile_sha256"]}
    result["completion_record"] = {"path": str(completion_record), "sha256": sha(completion_record)}
    result["sha256"] = signature(result)
    immutable(output / "topics" / topic["id"] / (arm + ".json"), result)
    return result


def verify_arm(topic, arm, result, profile_hash):
    if result["arm"] != arm or result["selected"] not in result["videos"] or result["first"] not in result["videos"]:
        raise ValueError("Arm receipt is incomplete")
    expected = {"topic": topic["id"], "source": topic["source_sha256"],
                "request": signature({"text": topic["request"]}), "profile": profile_hash}
    if result.get("binding") != expected or signature({k:v for k,v in result.items() if k != "sha256"}) != result.get("sha256"):
        raise ValueError("Arm receipt does not match the frozen topic and configuration")
    record = result["completion_record"]
    if sha(record["path"]) != record["sha256"]:
        raise ValueError("Delivery record changed after completion")
    if arm != 'direct':
        from planner_harness.delivery import verify_delivery
        run = Path(result['record_directory'])
        state = load(run/'state.json')
        if state['config'].get('workflow')!='creative_loop_v1' or state['request']['text']!=topic['request'] or state['videos']['source']['sha256']!=topic['source_sha256']:
            raise ValueError('Loop receipt does not have the matching creative task state')
        delivery = verify_delivery(run)
        if delivery['selected']!=result['selected'] or result.get('delivery_review')!=state['final'].get('delivery_review'):
            raise ValueError('Loop receipt lacks the verified report-informed confirmation')
    for video in result["videos"].values():
        if sha(video["path"]) != video["sha256"]:
            raise ValueError("Arm video changed")


def copy_verified(source, target, expected=None):
    source, target = Path(source), Path(target)
    digest = sha(source)
    if expected and digest != expected:
        raise ValueError("Artifact hash changed before archival")
    if target.exists():
        if sha(target) != digest:
            raise ValueError("Existing archive artifact differs")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".partial")
        shutil.copyfile(source, temporary)
        if sha(temporary) != digest:
            raise ValueError("Artifact copy failed verification")
        temporary.replace(target)
    return digest


def cache_judgment(root, output, topic, video, *, name="glm5.3flash", judge=None):
    from critic_harness.one_shot import frozen_profile
    from evaluation.creative import judge_candidate, make_judge
    from planner_harness.video import Video
    output = Path(output)
    binding = {"request": topic["request"], "source": topic["source_sha256"], "candidate": video["sha256"],
               "protocol": frozen_profile()["sha256"], **judge_identity(name),
               "adapter": sha(Path(root) / "src/evaluation/creative.py")}
    key = signature(binding)
    directory = output / "final-judge" / key
    with RunLock(directory):
        immutable(directory / "identity.json", binding)
        # Canonical paths make a resumed identical call byte-for-byte stable across arms.
        source_path = output / "media" / (binding["source"] + ".mp4")
        candidate_path = output / "media" / (binding["candidate"] + ".mp4")
        copy_verified(Path(root) / topic["source"], source_path, binding["source"])
        copy_verified(video["path"], candidate_path, binding["candidate"])
        result_path = directory / "judgment.json"
        if result_path.exists():
            result = load(result_path)
            if result["output_sha256"] != binding["candidate"] or result["source_sha256"] != binding["source"] or result["profile_sha256"] != binding["protocol"] or any(result.get(k) != v for k, v in judge_identity(name).items()):
                raise ValueError("Cached independent judgment identity mismatch")
            # Retain and verify the report against the exact original evidence packet.
            from critic_harness.one_shot import validate_report
            validate_report(result["report"], load(directory / "evidence/request.json"))
            for frame in load(directory / "evidence/request.json")["images"]:
                if sha(frame["path"]) != frame["sha256"]:
                    raise ValueError("Cached judge evidence changed")
        else:
            source = Video(source_path, directory / "source-info").info
            candidate = Video(candidate_path, directory / "candidate-info").info
            result = judge_candidate(topic["request"], source, candidate, directory, model=judge or make_judge(name))
        return {"key": key, "path": str(result_path), "sha256": sha(result_path), "result": result}


def topic_summary(topic, arms, judgments):
    from evaluation.creative import paired_summary
    judging = {}
    for name, rows in judgments.items():
        positions = {"direct": rows["direct"][arms["direct"]["first"]]}
        for arm in ("full", "none"):
            for point in ("first", "final"):
                identity = arms[arm]["first" if point == "first" else "selected"]
                positions[arm + "_" + point] = rows[arm][identity]
        scores = {k: v["result"]["report"] for k, v in positions.items()}
        comparisons = {a + "__to__" + b: paired_summary([(scores[a], scores[b])]) for a, b in PAIRS}
        judging[name] = {"positions": positions, "comparisons": comparisons}
    from critic_harness.one_shot import DIMENSIONS
    disagreement = {}
    for position in judging[JUDGES[0]]["positions"]:
        reports = [judging[j]["positions"][position]["result"]["report"] for j in JUDGES]
        disagreement[position] = {key: {"scores": {j: reports[n]["main_scores"][key]["score"] for n, j in enumerate(JUDGES)},
            "statuses": {j: reports[n]["main_scores"][key]["status"] for n, j in enumerate(JUDGES)},
            "score_difference_sonnet_minus_glm": (reports[1]["main_scores"][key]["score"] - reports[0]["main_scores"][key]["score"])
                if all(r["main_scores"][key]["status"] == "scored" for r in reports) else None}
            for key in DIMENSIONS}
    costs = {}
    for arm, r in arms.items():
        times = [v.get("execution", {}).get("generation_seconds") for v in r["videos"].values()]
        costs[arm] = {"generations": len(times), "known_generation_seconds": sum(t for t in times if t is not None),
                      "unknown_generation_costs": times.count(None), "first": r["first"], "selected": r["selected"]}
        requests = r.get("generation_requests", [])
        failed = [x for x in requests if (x.get("response") or {}).get("status") != "complete"]
        costs[arm].update(render_requests=len(requests), failed_or_unresolved_requests=len(failed),
            unknown_failed_request_costs=len(failed),
            cost_scope="Successful render time is measured; failed request GPU time remains unknown. Raw attempts and model usage are archived.")
    return {"topic": topic["id"], "request": topic["request"], "data_role": "development_regression",
            "judges": judging, "judge_disagreement": disagreement, "costs": costs}


def seal_topic(root, output, topic, arms, judgments):
    directory = Path(output) / "topics" / topic["id"]
    archive = directory / "archive"
    summary = topic_summary(topic, arms, judgments)
    for arm, result in arms.items():
        record = Path(result["record_directory"])
        for file in sorted(record.rglob("*")):
            if file.is_file() and file.name not in {".run.lock"} and not file.name.endswith(".partial"):
                copy_verified(file, archive / "runs" / arm / file.relative_to(record))
        for identity, video in result["videos"].items():
            copy_verified(video["path"], archive / "videos" / arm / (identity + ".mp4"), video["sha256"])
        immutable(archive / (arm + "-record.json"), result)
        usage = directory / (arm + "-model-usage.jsonl")
        if usage.exists():
            copy_verified(usage, archive / usage.name)
        state_file = record / "state.json"
        if state_file.exists():
            from planner_harness.creative_report import report
            view = copy.deepcopy(load(state_file))
            projection = archive / "views" / arm
            for identity, video in view["videos"].items():
                video["path"] = str((archive / "videos" / ("source.mp4" if identity == "source" else arm + "/" + identity + ".mp4")).resolve())
            def relocate(value):
                if isinstance(value, dict):
                    return {k: relocate(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [relocate(v) for v in value]
                if isinstance(value, str) and value.startswith(str(record)):
                    return str(archive / "runs" / arm) + value[len(str(record)):]
                return value
            projection.mkdir(parents=True, exist_ok=True)
            report(projection, relocate(view), record_directory=archive / "runs" / arm)
            for filename in ("report.html", "report.md"):
                page = projection / filename
                text = page.read_text()
                for folder in ("events", "calls", "jobs"):
                    text = text.replace('href="' + folder + '/', 'href="../../runs/' + arm + '/' + folder + '/')
                    text = text.replace('](' + folder + '/', '](../../runs/' + arm + '/' + folder + '/')
                page.write_text(text)
            if (record / "experience-usage.json").exists():
                with (projection / "report.html").open("a") as stream:
                    stream.write('<p><a href="../../runs/' + arm + '/experience-usage.json">Original experience exposure and use record</a></p>')
    copy_verified(Path(root) / topic["source"], archive / "videos/source.mp4", topic["source_sha256"])
    for item in {j["key"]: j for by_arm in judgments.values() for group in by_arm.values() for j in group.values()}.values():
        path = Path(item["path"]).parent
        for file in sorted(path.rglob("*")):
            if file.is_file() and file.name != ".run.lock":
                copy_verified(file, archive / "judgments" / item["key"] / file.relative_to(path))
    for name in ("batch.json", "profile.json"):
        copy_verified(Path(output) / name, archive / name)
    immutable(archive / "summary.json", summary)
    body = ["<!doctype html><meta charset=utf-8><title>" + topic["id"] + " comparison</title>",
            "<h1>" + topic["id"] + "</h1><p>" + html.escape(topic["request"]) + "</p>",
            '<h2>Source</h2><video controls src="videos/source.mp4"></video>']
    for arm, result in arms.items():
        body.append("<h2>" + arm + "</h2><p>First: " + result["first"] + "; selected: " + result["selected"] + "</p>")
        for identity in result["videos"]:
            body.append(f'<h3>{identity}</h3><video controls src="videos/{arm}/{identity}.mp4"></video>')
            for name in JUDGES:
                score = judgments[name][arm][identity]["result"]["report"]["main_scores"]
                body.append("<h4>" + name + "</h4><pre>" + html.escape(json.dumps(score, indent=2)) + "</pre>")
        body.append(f'<a href="{arm}-record.json">Exact candidate identities and runtime record location</a>')
        if (archive / "views" / arm / "report.html").exists():
            body.append(f'<p><a href="views/{arm}/report.html">Complete prompts, reads, observations, online reviews and decisions</a></p>')
            body.append(f'<p><a href="views/{arm}/continuation-index.json">Continuation explanations, pressure, actual inputs/prompts and outcomes</a></p>')
    body.append('<p><a href="summary.json">All paired deltas, unknowns and generation costs</a></p>')
    (archive / "index.html").write_text("\n".join(body), encoding="utf-8")
    files = {p.relative_to(archive).as_posix(): sha(p) for p in sorted(archive.rglob("*")) if p.is_file()}
    immutable(directory / "archive-manifest.json", {"topic": topic["id"], "files": files,
              "summary_sha256": sha(archive / "summary.json"), "sha256": signature(files)})
    verify_archive(directory)
    return summary


def verify_archive(directory):
    directory = Path(directory)
    manifest = load(directory / "archive-manifest.json")
    if signature(manifest["files"]) != manifest["sha256"]:
        raise ValueError("Archive manifest changed")
    for name, digest in manifest["files"].items():
        path = (directory / "archive" / name).resolve()
        if not path.is_relative_to((directory / "archive").resolve()) or sha(path) != digest:
            raise ValueError("Archive is incomplete or changed")
    return load(directory / "archive/summary.json")


def advance(root, output, *, execute_arm, judges=None, execute_arms=None):
    """Single coordinator gate; dependency injection permits GPU-free end-to-end tests."""
    output = Path(output)
    from evaluation.creative import paired_summary
    summaries = []
    batch = verify_batch(root, output)
    for topic in batch["topics"]:
        directory = output / "topics" / topic["id"]
        if (directory / "archive-manifest.json").exists():
            summaries.append(verify_archive(directory))
            continue
        save(output / "checkpoint.json", {"status": "running", "topic": topic["id"], "stage": "generation"})
        arms = {}
        missing = [arm for arm in ARMS if not (directory / (arm + ".json")).exists()]
        fresh = execute_arms(topic, missing) if execute_arms and missing else {}
        for arm in ARMS:
            receipt = directory / (arm + ".json")
            arms[arm] = load(receipt) if receipt.exists() else fresh[arm] if arm in fresh else execute_arm(topic, arm)
            verify_arm(topic, arm, arms[arm], batch["profile_sha256"])
            immutable(receipt, arms[arm])
        save(output / "checkpoint.json", {"status": "running", "topic": topic["id"], "stage": "independent_judging"})
        # Separate records and calls; neither judge receives the other's report.
        from concurrent.futures import ThreadPoolExecutor
        def score_with(name):
            client = judges[name] if judges else None
            return {arm: {v: cache_judgment(root, output, topic, info, name=name, judge=client)
                          for v, info in result["videos"].items()} for arm, result in arms.items()}
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = {name: pool.submit(score_with, name) for name in JUDGES}
            judgments = {name: job.result() for name, job in jobs.items()}
        summaries.append(seal_topic(root, output, topic, arms, judgments))
        save(output / "checkpoint.json", {"status": "running", "topic": topic["id"], "stage": "archived"})
    combined = {name: {a + "__to__" + b: paired_summary([(s["judges"][name]["positions"][a]["result"]["report"], s["judges"][name]["positions"][b]["result"]["report"]) for s in summaries]) for a, b in PAIRS} for name in JUDGES}
    result = {"status": "complete", "topics": summaries, "comparisons": combined, "data_role": "development_regression"}
    immutable(output / "results.json", result)
    save(output / "checkpoint.json", {"status": "complete", "topics": len(summaries)})
    return result


def run(root, output, host):
    """No GPU is acquired here; only explicitly supplied devices are used."""
    output = Path(output).resolve()
    with RunLock(output / "batch-owner"):
        verify_batch(root, output)
        devices = host.get("devices", [])
        if not 1 <= len(devices) <= 2 or len(set(map(str, devices))) != len(devices):
            raise ValueError("Supply one or two distinct existing devices; never acquire a new instance")
        from .preflight import verify_provider_receipt, host_preflight
        for name in JUDGES:
            verify_provider_receipt(output, name)
        host_preflight(root, host, execute=True)
        immutable(output / "host.json", host)
        context = multiprocessing.get_context("spawn")
        pools = [context.Pool(1, initializer=init_worker, initargs=(device, str(root), str(output), host)) for device in devices]
        try:
            def execute(topic, arm):
                slot = 1 if arm == "none" and len(pools) > 1 else 0
                return pools[slot].apply(run_arm, (topic, arm))
            def execute_topic(topic, missing):
                results = {}
                if "direct" in missing:
                    results["direct"] = execute(topic, "direct")
                pending = {arm: pools[1 if arm == "none" and len(pools) > 1 else 0].apply_async(run_arm, (topic, arm))
                           for arm in ("full", "none") if arm in missing}
                results.update({arm: job.get() for arm, job in pending.items()})
                return results
            return advance(root, output, execute_arm=execute, execute_arms=execute_topic)
        except BaseException as exc:
            current = load(output / "checkpoint.json") if (output / "checkpoint.json").exists() else {}
            save(output / "checkpoint.json", {**current, "status": "blocked", "error_type": type(exc).__name__, "error": str(exc)})
            raise
        finally:
            for pool in pools:
                pool.close()
            for pool in pools:
                pool.join()
