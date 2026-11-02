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
from planner_harness.resources import ResourceExhausted, MAX_GENERATIONS, MAX_WALL_SECONDS
from planner_harness.accounting import ExternalExecutionUnknown
from evaluation.creative import JUDGES, judge_identity
from . import render_profiles

ARMS = ("direct", "full", "none")
GENERATION = render_profiles.generation("bernini")
SEEDS = {"start": 42, "step": 1}
PAIRS = (("direct", "full_first"), ("direct", "none_first"),
         ("full_first", "full_final"), ("none_first", "none_final"),
         ("none_first", "full_first"), ("none_final", "full_final"))


def prepare(root, output, **configuration):
    """Public preparation uses the current inventory and the unified task policy."""
    from .unified_benchmark import prepare as unified_prepare
    configuration.setdefault("splits", ["test"])
    configuration.setdefault("prompt_forms", ["short", "long"])
    return unified_prepare(root, output, **configuration)


def verify_batch(root, output):
    from planner_harness.creative import verify_experiment
    output = Path(output)
    batch = load(output / "batch.json")
    if batch.get("schema") == "lha-unified-benchmark-v1":
        from .unified_benchmark import verify
        return verify(root, output)
    if signature({k: v for k, v in batch.items() if k != "sha256"}) != batch["sha256"]:
        raise ValueError("Batch manifest changed")
    profile = verify_experiment(output / "profile.json", root)
    if profile["sha256"] != batch["profile_sha256"]:
        raise ValueError("Batch profile mismatch")
    if batch["generation"] != GENERATION or batch["seed_sequence"] != SEEDS or batch["arms"] != list(ARMS):
        raise ValueError("Frozen experimental conditions differ")
    if batch["judges"] != [judge_identity(j) for j in JUDGES]:
        raise ValueError("Both independent judges must retain their frozen model and effort")
    if batch.get("schema") != "creative-benchmark-three-arm-v3" or batch["completion_mode"] != "delivery":
        raise ValueError("Use a new continuous-ID v3 cohort; historical snapshots are not resumed by this entry point")
    if type(batch["max_generations"]) is not int or batch["max_generations"] < 1:
        raise ValueError("The cohort requires finite generation and turn submission guards")
    for topic in batch["topics"]:
        if sha(Path(root) / topic["source"]) != topic["source_sha256"]:
            raise ValueError("Source changed after preparation")
    return batch


def task_spec(topic, arm, batch, profile_path):
    if arm not in {"full", "none"}:
        raise ValueError("Direct is a renderer job, not a Planner task")
    spec = {"id": topic["id"] + "__" + arm, "workflow": "creative_loop_v1",
            "source": topic["source"], "source_sha256": topic["source_sha256"], "request": topic["request"],
            "completion_mode": "delivery", "max_generations": batch["max_generations"], "max_turns": batch["max_turns"],
            "max_context_chars": 180000,
            "execution": {"mode": "live", "experience_mode": arm, "task_track": topic.get("track", topic.get("prompt_form", "long")), "benchmark_metadata":{"split":topic.get("split","train"),"sample_id":topic.get("sample_id",topic["id"]),"seed":batch["seed_sequence"]["start"]}, "experiment_profile": str(profile_path),
                "seed_sequence": batch["seed_sequence"], "renderer": renderer_spec(topic, batch)},
            "run_instructions": "Complete the user's video task using the limited budget deliberately. "
                "Choose prompts, input candidates, review focus and delivery. Every successful generation is automatically reviewed before your next decision. "
                "Use optional generate justification to record what an attempt aims to improve or compare. "
                "Complete the configured per-generation review, then select a reviewed candidate for delivery. "
                + render_profiles.prompt_guidance(render_profiles.backend(batch)) + " " +
                "The rendering seed sequence is fixed by the experiment. A blocked or interrupted task remains incomplete."}
    if batch.get("resource_policy"):
        spec["execution"]["resource_policy"] = batch["resource_policy"]
    spec["execution"]["review"] = copy.deepcopy(batch.get("review", {"mode":"critic"}))
    return spec


def renderer_spec(topic, batch):
    return render_profiles.renderer_spec(topic, batch)


def direct_request(root, topic, batch, *, accounting_scope=None):
    body = {"id": topic["id"] + "-direct", "kind": "generate", "mode": "live", "payload": {
        "input_id": "source", "input": {**topic["source_info"], "path": str((Path(root) / topic["source"]).resolve())},
        "prompt": topic["request"], "renderer": renderer_spec(topic, batch)}}
    if accounting_scope is not None:
        body["accounting_scope"] = accounting_scope
    return {**body, "sha256": signature(body)}


_WORKER = None
_WORKER_ARGS = None


def init_worker(device, root, output, host):
    # Each process owns one visible physical GPU. Model and pipeline persist across topics.
    global _WORKER_ARGS
    if _WORKER is not None and _WORKER_ARGS != (device, root, output, host):
        raise RuntimeError("This process already owns a frozen worker; use a new process for another cohort")
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
    batch=load(Path(output)/"batch.json")
    from planner_harness.creative import role_settings
    cfg = {"workflow": "creative_loop_v1", "planner": batch.get("planner") or role_settings(host,"planner"),
           "critic": batch.get("critic") or role_settings(host,"online_critic"), "review":copy.deepcopy(batch.get("review",{"mode":"critic"})), "enable_final_evaluation": False,
           "experiment_profile": str(Path(output) / "profile.json"),
           "accounting_root":str(Path(output) / "accounting"), "budget":host.get("budget"),
           "renderer": {**host["renderer"], "backend": render_profiles.backend(batch), "generation": batch["generation"],
                        "gpu_lock": str(Path(host.get("lock_directory", "/tmp")) / ("lha-bernini-device-" + str(device)))}}
    if batch.get("models") or host.get("models"):
        cfg["models"] = copy.deepcopy(batch.get("models") or host["models"])
    queue = Queue(directory / "queue.sqlite3", {"gpu": 1, "llm": 1, "cpu": 1})
    service = ResidentService(queue, directory, root, cfg)
    atexit.register(Service.close, service)
    _WORKER = (Path(root), Path(output), queue, service, directory)
    return _WORKER


def run_arm(topic, arm):
    from planner_harness.delivery import verify_settlement
    from planner_harness.video import Video
    from server_runtime.engine import Engine
    root, output, queue, service, directory = worker_state()
    batch = verify_batch(root, output)
    from planner_harness.accounting import topic_scope,admit_topic
    budget_scope = topic_scope(output,topic["id"],lane=arm)
    admit_topic(budget_scope)
    service.ensure_ready()
    from planner_harness.accounting import start_task
    start_task(budget_scope, wall_seconds=batch.get("resource_policy",{}).get("max_wall_seconds",MAX_WALL_SECONDS))
    os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(output / "topics" / topic["id"] / (arm + "-model-usage.jsonl"))
    if arm == "direct":
        jobdir = directory / "direct" / topic["id"]
        job = direct_request(root, topic, batch,accounting_scope=budget_scope)
        immutable(jobdir / "request.json", job)
        queue.enqueue(topic["id"] + "/direct", "tool", "gpu",
                      {"request": str(jobdir / "request.json"), "request_sha256": job["sha256"]})
        Engine(queue, directory, service, service.expand).run(once=True)
        response = load(jobdir / "response.json")
        if response["request_sha256"] != job["sha256"]:
            raise ValueError("Direct response identity mismatch")
        if response["status"] == "complete":
            video = response["payload"]["video"]
            info = Video(video["path"], jobdir).info
            result = {"arm": arm, "selected": "v1", "first": "v1", "outcome": "delivered", "successful": True,
                      "record_directory": str(jobdir),
                      "videos": {"v1": {**info, "execution": response["payload"].get("execution", {})}}}
        elif response["status"] == "failed":
            result = {"arm": arm, "selected": None, "first": None, "successful": False,
                      "outcome": "execution_unknown" if response.get("outcome_unknown") else "execution_failed",
                      "record_directory": str(jobdir), "videos": {}}
        else:
            raise ValueError("Direct render has no final outcome")
        completion_record = jobdir / "response.json"
    else:
        task = task_spec(topic, arm, batch, output / "profile.json")
        from .unified_benchmark import task_conditions
        conditions=task_conditions(root,output,topic,arm,batch)
        if conditions.get('experience_snapshot'):
            task['execution'].update(experience_snapshot=conditions['experience_snapshot'],experience_snapshot_sha256=conditions['actual_knowledge_sha256'])
        task["budget_topic"] = topic["id"]
        task["budget_lane"] = arm
        service.submit(task)
        Engine(queue, directory, service, service.expand).run(once=True)
        run = directory / "tasks" / task["id"] / "run"
        settlement = verify_settlement(run)
        state = load(run / "state.json")
        videos = {k: v for k, v in state["videos"].items() if k != "source" and not v.get("imported")}
        result = {"arm": arm, **settlement, "first": next(iter(videos), None),
                  "review":copy.deepcopy(state['config'].get('execution',{}).get('review',batch.get('review',{'mode':'critic'}))),
                  "reviews":state.get('reviews',{}),
                  "delivery_review":state.get("final", {}).get("delivery_review"),
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
    if result["arm"] != arm or any(result[k] is not None and result[k] not in result["videos"] for k in ("selected", "first")):
        raise ValueError("Arm receipt is incomplete")
    outcome = result.get("outcome", "delivered")
    if (outcome in {"delivered","deadline_delivery"}) != (result["selected"] is not None):
        raise ValueError("Successful and unsuccessful arm selection semantics differ")
    expected = {"topic": topic["id"], "source": topic["source_sha256"],
                "request": signature({"text": topic["request"]}), "profile": profile_hash}
    if result.get("binding") != expected or signature({k:v for k,v in result.items() if k != "sha256"}) != result.get("sha256"):
        raise ValueError("Arm receipt does not match the frozen topic and configuration")
    record = result["completion_record"]
    if sha(record["path"]) != record["sha256"]:
        raise ValueError("Delivery record changed after completion")
    if result.get("supervisor_settlement"):
        record=load(result["completion_record"]["path"])
        if record["topic"]!=topic["id"] or record["arm"]!=arm or record["outcome"]!=outcome or result["videos"]:
            raise ValueError("Supervisor settlement changed")
        return
    if arm != 'direct':
        from planner_harness.delivery import verify_settlement
        run = Path(result['record_directory'])
        state = load(run/'state.json')
        if state['config'].get('workflow')!='creative_loop_v1' or state['request']['text']!=topic['request'] or state['videos']['source']['sha256']!=topic['source_sha256']:
            raise ValueError('Loop receipt does not have the matching creative task state')
        settlement = verify_settlement(run)
        actual_first = next((k for k,v in state['videos'].items() if k != 'source' and not v.get('imported')),None)
        if actual_first != result['first']:
            raise ValueError('Arm first output differs from generation order')
        if settlement['selected']!=result['selected'] or settlement['outcome'] != result.get('outcome', 'delivered') or result.get('delivery_review')!=state.get('final',{}).get('delivery_review'):
            raise ValueError('Loop receipt differs from the actual settled delivery')
    for video in result["videos"].values():
        if sha(video["path"]) != video["sha256"]:
            raise ValueError("Arm video changed")


def copy_verified(source, target, expected=None, *, link=False):
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
        if link:
            try:os.link(source,temporary)
            except OSError:shutil.copyfile(source,temporary)
        else:shutil.copyfile(source, temporary)
        if sha(temporary) != digest:
            raise ValueError("Artifact copy failed verification")
        temporary.replace(target)
    return digest


def shared_source_plan(root, output, topic, *, model=None):
    """Freeze original spans locally. The optional reviewed body stays on the evaluator side."""
    from evaluation.low_high import profile as final_profile, freeze_plan, check_plan
    from planner_harness.video import Video
    output = Path(output)
    source_path = output / "media" / (topic["source_sha256"] + ".mp4")
    copy_verified(Path(root) / topic["source"], source_path, topic["source_sha256"])
    source = Video(source_path, output / "source-info").info
    body = {"track":topic.get("track",topic.get("prompt_form","long"))}
    # Evaluator-private inputs, never copied into a generation task/knowledge manifest.
    reviewed = output / "evaluation-inputs" / (topic["id"] + ".json")
    if reviewed.exists():
        supplied=load(reviewed)
        if supplied.get('source_sha256')!=source['sha256'] or supplied.get('request_sha256')!=signature({'text':topic['request']}):
            raise ValueError('Reviewed evaluation input belongs to a different source/task')
        body.update(supplied['body'])
    identity = {"source":topic["source_sha256"],"request":topic["request"],
                "protocol":final_profile()["sha256"],"body":body}
    plan_dir = output / "final-plans" / signature(identity)
    with RunLock(plan_dir,timeout=7200):
        immutable(plan_dir / "identity.json",identity)
        plan=freeze_plan(body,topic["request"],source,plan_dir)
        check_plan(plan,topic["request"],source)
        record=plan_dir/'plan.json'
        immutable(output / "topics" / topic["id"] / "source-plan.json",
                  {"directory":str(plan_dir),"identity_sha256":signature(identity),
                   "record_path":str(record),"record_sha256":sha(record),"status":"complete"})
    return source, plan


def cache_judgment(root, output, topic, video, *, name="glm5.3flash", judge=None, source_plan=None):
    from evaluation.low_high import profile as final_profile, verify_event_records
    from evaluation.creative import judge_candidate, make_judge
    from planner_harness.video import Video
    output = Path(output)
    source, plan = source_plan or shared_source_plan(root,output,topic,model=judge if name=="glm5.3flash" else None)
    binding = {"request": topic["request"], "source": topic["source_sha256"], "candidate": video["sha256"],
               "protocol": final_profile()["sha256"], "plan_sha256":plan["sha256"], **judge_identity(name),
               "adapter": sha(Path(root) / "src/evaluation/creative.py")}
    key = signature(binding)
    directory = output / "final-judge" / key
    from planner_harness.accounting import topic_scope,bind,attach
    budget_scope = topic_scope(output,topic["id"])
    bind(directory,budget_scope)
    if judge is not None:judge = attach(judge,budget_scope)
    with RunLock(directory):
        immutable(directory / "identity.json", binding)
        # Canonical paths make a resumed identical call byte-for-byte stable across arms.
        source_path = output / "media" / (binding["source"] + ".mp4")
        candidate_path = output / "media" / (binding["candidate"] + ".mp4")
        copy_verified(Path(root) / topic["source"], source_path, binding["source"])
        copy_verified(video["path"], candidate_path, binding["candidate"])
        if plan.get("status") == "missing":
            if plan.get("sha256") != signature({k:v for k,v in plan.items() if k != "sha256"}) or plan.get("source_sha256") != topic["source_sha256"] or plan.get("request_sha256") != signature({"text":topic["request"]}) or sha(plan["unavailable_path"]) != plan["unavailable_sha256"]:
                raise ValueError("Missing source-plan binding changed")
            result = {"usage":"independent_final", **judge_identity(name), "report":None,
                      "status":"missing", "reason":plan.get("reason","source_plan_unavailable"), "plan_sha256":plan["sha256"],
                      "profile_sha256":binding["protocol"], "source_sha256":binding["source"],
                      "output_sha256":binding["candidate"], "attempt_records":[plan["unavailable_path"]]}
            result_path = directory / "missing.json"
            immutable(result_path,result)
            return {"key":key,"path":str(result_path),"sha256":sha(result_path),"result":result}
        result_path = directory / "judgment.json"
        if (directory / "missing.json").exists():
            result_path = directory / "missing.json"
            result = load(result_path)
            receipt=load(directory/"missing-binding.json")
            if receipt!={"identity_sha256":signature(binding),"result_sha256":sha(result_path)} or result.get("status")!="missing":
                raise ValueError("Cached missing assessment changed")
        elif result_path.exists():
            result = load(result_path)
            if result["output_sha256"] != binding["candidate"] or result["source_sha256"] != binding["source"] or result["profile_sha256"] != binding["protocol"] or any(result.get(k) != v for k, v in judge_identity(name).items()):
                raise ValueError("Cached independent judgment identity mismatch")
            # Retain and verify the report against the exact original evidence packet.
            from evaluation.validation import validate_report
            packet = load(directory / "evidence/request.json")
            validate_report(result["report"], packet)
            if result.get("plan_sha256") != plan["sha256"] or packet.get("plan") != plan:
                raise ValueError("Cached judgment used a different shared interpretation")
            from types import SimpleNamespace
            verify_event_records(directory,packet,SimpleNamespace(model=name,reasoning_effort=judge_identity(name)["reasoning_effort"]))
            from evaluation.task_metrics import verify as verify_metrics
            if verify_metrics(directory / "task-metrics",SimpleNamespace(model=name,reasoning_effort=judge_identity(name)["reasoning_effort"])) != result["task_metrics"]:
                raise ValueError("Cached task diagnostics changed")
            from planner_harness.report_call import verify_answer,verify_inputs
            verifier=SimpleNamespace(model=name,reasoning_effort=judge_identity(name)['reasoning_effort'])
            if 'main_projection' in result:
                from evaluation.final_projection import verify as verify_main
                call=verify_main(directory,result,packet,verifier)
            else:
                call=verify_answer(directory,result['report'])
                verify_inputs(call,verifier,packet,[r['path'] for r in packet['images']])
            for frame in load(directory / "evidence/request.json")["images"]:
                if sha(frame["path"]) != frame["sha256"]:
                    raise ValueError("Cached judge evidence changed")
        else:
            source = Video(source_path, directory / "source-info").info
            candidate = Video(candidate_path, directory / "candidate-info").info
            from planner_harness.report_call import ReportUnavailable
            try:
                result = judge_candidate(topic["request"], source, candidate, directory, model=judge or make_judge(name), plan=plan)
            except (ReportUnavailable, ResourceExhausted,
                    ExternalExecutionUnknown) as exc:
                result = {"usage": "independent_final", **judge_identity(name), "report": None,
                          "status": "missing", "reason": "evaluation_execution_unknown" if getattr(exc,"outcome_unknown",False) else "evaluation_budget_exhausted" if getattr(exc,"failure_kind",None)=="resource_exhausted" else "report_recovery_exhausted",
                          "profile_sha256":binding["protocol"], "plan_sha256":plan["sha256"],
                          "source_sha256": source["sha256"], "output_sha256": candidate["sha256"],
                          "attempt_records": [str(p) for p in sorted(directory.rglob("unavailable.json"))]}
                result_path = directory / "missing.json"
                immutable(result_path, result)
                immutable(directory/"missing-binding.json",{"identity_sha256":signature(binding),"result_sha256":sha(result_path)})
        from evaluation.final_suite import automatic
        measured=automatic(source, Video(candidate_path,directory/'candidate-info').info, plan,
                           output/'automatic-metrics',accounting_scope=budget_scope)
        combined={**result,'automatic':measured,'track':plan['task']['track']}
        suite_path=directory/'suite.json';immutable(suite_path,combined)
        return {"key": key, "path": str(suite_path), "sha256": sha(suite_path), "result": combined}


def missing_judgment(reason):
    return {"status": "missing", "reason": reason, "result": {"report": None, "status": "missing", "reason": reason}}


def topic_summary(topic, arms, judgments):
    from evaluation.creative import paired_summary
    judging = {}
    for name, rows in judgments.items():
        positions = {"direct": rows["direct"].get(arms["direct"]["first"], missing_judgment("no_candidate"))}
        for arm in ("full", "none"):
            for point in ("first", "final"):
                identity = arms[arm]["first" if point == "first" else "selected"]
                positions[arm + "_" + point] = rows[arm].get(identity, missing_judgment("no_delivery" if point == "final" else "no_candidate"))
        scores = {k: v["result"]["report"] for k, v in positions.items()}
        comparisons = {a + "__to__" + b: paired_summary([(scores[a], scores[b])]) for a, b in PAIRS}
        from evaluation.final_suite import metric_pairs
        judging[name] = {"positions": positions, "comparisons": comparisons,
            "all_metric_comparisons":{a+"__to__"+b:metric_pairs([(positions[a]['result'],positions[b]['result'])]) for a,b in PAIRS}}
    from critic_harness.one_shot import DIMENSIONS
    disagreement = {}
    for position in judging[JUDGES[0]]["positions"]:
        reports = [judging[j]["positions"][position]["result"]["report"] for j in JUDGES]
        disagreement[position] = {key: {"scores": {j: reports[n]["main_scores"][key]["score"] if reports[n] else None for n, j in enumerate(JUDGES)},
            "statuses": {j: reports[n]["main_scores"][key]["status"] if reports[n] else "missing" for n, j in enumerate(JUDGES)},
            "score_difference_sonnet_minus_glm": (reports[1]["main_scores"][key]["score"] - reports[0]["main_scores"][key]["score"])
                if all(r and r["main_scores"][key]["status"] == "scored" for r in reports) else None}
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
    return {"topic": topic["id"], "source_id":topic["source_sha256"], "request": topic["request"], "data_role": "development_regression",
            "track": topic.get("track",topic.get("prompt_form","long")), "judges": judging, "judge_disagreement": disagreement, "costs": costs,
            "outcomes": {arm:r.get("outcome", "delivered") for arm,r in arms.items()}}


def seal_topic(root, output, topic, arms, judgments):
    directory = Path(output) / "topics" / topic["id"]
    archive = directory / "archive"
    summary = topic_summary(topic, arms, judgments)
    if (directory/'blind.json').exists():summary['blind']=load(directory/'blind.json')
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
        auto=item.get('result',{}).get('automatic',{}).get('directory')
        if auto:
            for file in sorted(Path(auto).glob('*.json')):
                copy_verified(file,archive/'automatic-metrics'/Path(auto).name/file.name)
        path = Path(item["path"]).parent
        for file in sorted(path.rglob("*")):
            if file.is_file() and file.name != ".run.lock":
                copy_verified(file, archive / "judgments" / item["key"] / file.relative_to(path))
    for file in sorted((Path(output)/'blind-judge').rglob('*')):
        if file.is_file() and file.name!='.run.lock':
            # Only this topic's source/plan; shared caches retain candidate anonymity.
            parent=file
            while parent.parent != Path(output)/'blind-judge' and parent!=parent.parent:parent=parent.parent
            if (parent/'identity.json').exists() and load(parent/'identity.json')['source']==topic['source_sha256']:
                copy_verified(file,archive/'blind'/file.relative_to(Path(output)/'blind-judge'))
    source_plan_link = directory / "source-plan.json"
    if source_plan_link.exists():
        link = load(source_plan_link)
        if sha(link["record_path"]) != link["record_sha256"]:
            raise ValueError("Shared source-plan record changed before archival")
        plan_directory = Path(link["directory"])
        for file in sorted(plan_directory.rglob("*")):
            if file.is_file() and file.name != ".run.lock":
                copy_verified(file,archive / "source-plans" / link["identity_sha256"] / file.relative_to(plan_directory))
        copy_verified(source_plan_link,archive / "source-plan.json")
    for name in ("batch.json", "profile.json"):
        copy_verified(Path(output) / name, archive / name)
    immutable(archive / "summary.json", summary)
    body = ["<!doctype html><meta charset=utf-8><title>" + topic["id"] + " comparison</title>",
            "<h1>" + topic["id"] + "</h1><p>" + html.escape(topic["request"]) + "</p>",
            '<h2>Source</h2><video controls src="videos/source.mp4"></video>']
    for arm, result in arms.items():
        body.append("<h2>" + arm + "</h2><p>First: " + str(result["first"]) + "; selected: " + str(result["selected"]) + "</p>")
        for identity in result["videos"]:
            body.append(f'<h3>{identity}</h3><video controls src="videos/{arm}/{identity}.mp4"></video>')
            for name in JUDGES:
                from evaluation.final_suite import ratings
                current=judgments[name][arm][identity]['result']
                score=ratings(current) or {'status':'missing'}
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
        source_plan = shared_source_plan(root,output,topic,model=judges["glm5.3flash"] if judges else None)
        def score_with(name):
            client = judges[name] if judges else None
            return {arm: {v: cache_judgment(root, output, topic, info, name=name, judge=client, source_plan=source_plan)
                          for v, info in result["videos"].items()} for arm, result in arms.items()}
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = {name: pool.submit(score_with, name) for name in JUDGES}
            judgments = {name: job.result() for name, job in jobs.items()}
        summaries.append(seal_topic(root, output, topic, arms, judgments))
        save(output / "checkpoint.json", {"status": "running", "topic": topic["id"], "stage": "archived"})
    combined = {name: {a + "__to__" + b: paired_summary([(s["judges"][name]["positions"][a]["result"]["report"], s["judges"][name]["positions"][b]["result"]["report"]) for s in summaries]) for a, b in PAIRS} for name in JUDGES}
    result = {"status": "complete", "topics": summaries, "comparisons": combined, "data_role": "development_regression",
              "planned_topics": len(batch["topics"]), "outcome_counts": outcome_counts(summaries)}
    from evaluation.final_suite import aggregate
    result['metrics']=aggregate(summaries)
    immutable(output / "results.json", result)
    save(output / "checkpoint.json", {"status": "complete", "topics": len(summaries)})
    return result


def outcome_counts(summaries):
    from collections import Counter
    return {arm:dict(Counter(s.get("outcomes",{}).get(arm,"delivered") for s in summaries)) for arm in ARMS}


def run(root, output, host):
    """Canonical public execution entry: early judging at the five reporting positions."""
    if load(Path(output) / "batch.json").get("schema") == "lha-unified-benchmark-v1":
        from .unified_benchmark import run as unified_run
        return unified_run(root, output, host)
    import sys
    scripts = str(Path(root) / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from creative_benchmark_schedule import run as scheduled_run
    return scheduled_run(root, output, host)


def isolated_arm(output,topic,arm,profile_hash,*,reason,outcome,evidence):
    """Explicit supervisor settlement for arms without an inspectable task state."""
    directory=Path(output)/"topics"/topic["id"]/"supervisor-settlements"/arm
    record={"topic":topic["id"],"arm":arm,"outcome":outcome,"reason":reason,"evidence":evidence,
            "selected":None,"external_result":"unknown" if outcome=="execution_unknown" else "not_dispatched"}
    immutable(directory/"settlement.json",record)
    result={"arm":arm,"selected":None,"first":None,"successful":False,"outcome":outcome,"videos":{},
        "record_directory":str(directory),"supervisor_settlement":True,"generation_requests":[],
        "binding":{"topic":topic["id"],"source":topic["source_sha256"],"request":signature({"text":topic["request"]}),"profile":profile_hash},
        "completion_record":{"path":str(directory/"settlement.json"),"sha256":sha(directory/"settlement.json")}}
    return {**result,"sha256":signature(result)}
