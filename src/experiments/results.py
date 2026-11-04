"""One video registry, with evaluation identities independent of render provenance.

Imports never consume old scores. A source/request match is checked against the
current inventory before a video is given its current sample/form/method/seed key.
"""
from __future__ import annotations

import copy

import html
import json
from pathlib import Path
import re
import uuid
from urllib.parse import quote

from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock

VERSION = "lha-video-results-v1"
SAFE = re.compile(r"[A-Za-z0-9_-]+\Z")
METHODS = ("direct", "direct-best-of-n", "planner-once", "pe", "full", "none", "pre-experience",
           "pe-loop", "lineage-chain", "lineage-source-restart")
RUN_METHODS = tuple(m for m in METHODS if not m.startswith("lineage-"))
DEFAULT_TEST_METHODS = ("direct", "pe-loop", "none", "full")
TRAJECTORY_METHODS = {"full", "none", "pre-experience", "pe-loop"}
REVIEW_METHODS = {"full", "none", "pre-experience"}
REVIEW_MODES = ("critic", "planner")


def normalize_review_mode(method, mode=None):
    """Shared baselines have one video; previous Loop entries retain legacy identity."""
    if method not in REVIEW_METHODS:
        if mode not in {None, "shared"}:
            raise ValueError("Baseline results are shared across Loop review modes")
        return "shared"
    if mode is None:
        return "legacy"
    if mode not in {*REVIEW_MODES, "legacy"}:
        raise ValueError("Loop review mode must be critic or planner")
    return mode


def entry_files(root):
    return sorted((Path(root) / "entries").rglob("seed-*.json"))


def result_variant(method, mode):
    return method + "/" + mode if method in REVIEW_METHODS else method


def comparison_pairs(*, pre_experience=False):
    from .creative_benchmark import PAIRS
    pairs = PAIRS + (("direct", "planner-once"), ("direct", "pe"),
        ("direct", "direct-best-of-n"), ("direct-best-of-n", "full_final"), ("direct-best-of-n", "none_final"),
        ("planner-once", "none_first"), ("planner-once", "full_first"), ("pe", "planner-once"),
        ("lineage-source-restart", "lineage-chain"),
        ("direct", "pe-loop_first"), ("direct", "pe-loop_final"),
        ("pe-loop_first", "pe-loop_final"), ("pe-loop_final", "none_final"),
        ("pe-loop_final", "full_final"), ("pe-loop_first", "none_first"),
        ("full_final@critic", "full_final@planner"), ("none_final@critic", "none_final@planner"))
    return [list(pair) for pair in pairs] + [
        [label.replace("none_", "pre-experience_") for label in pair]
        for pair in pairs if pre_experience and any(label.startswith("none_") for label in pair)
    ]


def inventory(repository):
    root = Path(repository).resolve()
    result = {}
    for row in load(root / "benchmark_data/benchmark.json"):
        sample = row["sample_id"]
        if not SAFE.fullmatch(sample):
            raise ValueError("Unsafe benchmark sample ID")
        for form in ("short", "long"):
            text = row.get("prompt_" + form, row.get("instruction") if form == "long" else None)
            if not isinstance(text, str) or not text.strip():
                continue
            result[sample, form] = {"sample_id": sample, "prompt_form": form,
                "source_sha256": row["source_video_sha256"], "request": text,
                "request_sha256": signature({"text": text}), "source": row["source_video"],
                "split": row["split"], "source_group": row.get("source_group", sample)}
    return result


def entry_path(root, sample, form, method, seed, review_mode=None):
    if not isinstance(sample, str) or not SAFE.fullmatch(sample) or form not in {"short", "long"}:
        raise ValueError("A current sample and short/long prompt form are required")
    if method not in METHODS or type(seed) is not int or seed < 0:
        raise ValueError("Unknown method or invalid seed")
    mode = normalize_review_mode(method, review_mode)
    directory = Path(root) / "entries" / sample / form / method
    if mode in REVIEW_MODES:
        directory /= "review-" + mode
    return directory / ("seed-" + str(seed) + ".json")


def _copy(source, target, expected):
    from .creative_benchmark import copy_verified
    # Content-addressed libraries on the same filesystem share verified bytes.
    # Raw render paths still copy once into the immutable media library.
    shared = Path(source).parent.name == Path(target).parent.name == 'media'
    return copy_verified(source, target, expected, link=shared)


def import_video(repository, root, row):
    """Import one verified local output. Repeated identical imports are idempotent."""
    root = Path(root).resolve()
    index = inventory(repository)
    row = dict(row)
    request_hash = row.get("request_sha256")
    if "request" in row:
        actual = signature({"text": row["request"]})
        if request_hash and request_hash != actual:
            raise ValueError("Import request text/hash differ")
        request_hash = actual
    matches = [r for r in index.values() if r["source_sha256"] == row.get("original_source_sha256", row.get("source_sha256"))
               and r["request_sha256"] == request_hash
               and (not row.get("prompt_form") or r["prompt_form"] == row["prompt_form"])]
    if row.get("sample_id"):
        matches = [r for r in matches if r["sample_id"] == row["sample_id"]]
    if len(matches) != 1:
        raise ValueError("Import must match exactly one current source, prompt and sample")
    task = dict(matches[0])
    normalized_copy = None
    if row.get("normalization"):
        from .video_contract import POLICY, FRAMES, FPS, sample_indices
        from planner_harness.video import Video
        record = row["normalization"]
        normalized = Path(row["source"])
        info = Video(normalized, root / "source-info").info
        if (record.get("policy") != POLICY or record.get("original_sha256") != task["source_sha256"]
                or record.get("normalized_sha256") != row["source_sha256"] or info["sha256"] != row["source_sha256"]
                or info["frames"] != FRAMES or abs(info["fps"] - FPS) > .001
                or record.get("source_indices") != sample_indices(record["original_info"]["frames"])):
            raise ValueError("Normalized source provenance or time axis differs")
        portable = "media/" + row["source_sha256"] + ".mp4"
        normalized_copy = normalized, root / portable, row["source_sha256"]
        task.update(original_source=task["source"], original_source_sha256=task["source_sha256"],
                    source=portable, source_sha256=row["source_sha256"], normalization=record)
    elif row.get("original_source_sha256"):
        raise ValueError("Original source identity requires normalization evidence")
    method, seed = row.get("method"), row.get("seed")
    mode = normalize_review_mode(method, row.get("review_mode"))
    path = entry_path(root, task["sample_id"], task["prompt_form"], method, seed, mode)
    source = Path(row["video"]).resolve()
    digest = sha(source)
    if row.get("normalization"):
        from .video_contract import FRAMES, FPS
        from planner_harness.video import Video
        for item in [row, *row.get("candidates", [])]:
            actual = Video(item["video"], root / "candidate-info").info
            if actual["frames"] != FRAMES or abs(actual["fps"] - FPS) > .001:
                raise ValueError("Every uniform-protocol candidate requires 117 frames at 24 fps")
    if row.get("video_sha256") and row["video_sha256"] != digest:
        raise ValueError("Imported video hash differs")
    if not isinstance(row.get("generation"), dict) or not row["generation"]:
        raise ValueError("Retain the actual generation conditions with each video")
    if not isinstance(row.get("evidence"), dict) or not row["evidence"]:
        raise ValueError("Retain the original render evidence with each video")
    evidence = copy.deepcopy(row["evidence"])
    receipt_copy = None
    if evidence.get("receipt_sha256"):
        receipt = Path(evidence["receipt"])
        if not receipt.is_file() or sha(receipt) != evidence["receipt_sha256"]:
            raise ValueError("Original render receipt is unavailable or changed")
        destination=root/"receipts"/(evidence["receipt_sha256"]+".json")
        receipt_copy = (receipt, destination, evidence["receipt_sha256"])
        evidence.setdefault("original_receipt",str(receipt))
        evidence["receipt"]=str(destination)
    # Scores and stale judging artifacts deliberately have no import field.
    body = {"schema": VERSION, **task, "method": method, "seed": seed, "review_mode": mode,
            "video": "media/" + digest + ".mp4", "video_sha256": digest,
            "generation": row["generation"], "evidence": evidence,
            "evaluation_status": "pending"}
    candidates = []
    for candidate in row.get("candidates", []):
        if not isinstance(candidate.get("id"), str) or not SAFE.fullmatch(candidate["id"]) or type(candidate.get("seed")) is not int or set(candidate.get("roles", [])) - {"first", "last", "selected"}:
            raise ValueError("Invalid generated candidate identity/seed/roles")
        native = Path(candidate["video"]).resolve()
        native_sha = sha(native)
        if native_sha != candidate["video_sha256"]:
            raise ValueError("Candidate video changed")
        candidates.append({"id": candidate["id"], "seed": candidate["seed"], "roles": candidate["roles"],
            "video": "media/" + native_sha + ".mp4", "video_sha256": native_sha, "_source": native})
    if candidates:
        if len({c["id"] for c in candidates}) != len(candidates) or sum("first" in c["roles"] for c in candidates) != 1 or sum("selected" in c["roles"] for c in candidates) != 1:
            raise ValueError("Candidate set needs unique IDs and one first/selected identity")
        if next(c["video_sha256"] for c in candidates if "selected" in c["roles"]) != digest:
            raise ValueError("Selected candidate differs from the primary result")
        if method == "pe-loop" and sum("last" in c["roles"] for c in candidates) != 1:
            raise ValueError("PE Loop needs one last candidate identity")
        body["candidates"] = [{k: v for k, v in c.items() if k != "_source"} for c in candidates]
    with RunLock(root / "registry-owner", timeout=120):
        if path.exists():
            old = verify_entry(root, path)
            identity = ("source_sha256", "request_sha256", "video_sha256", "generation")
            if any(old[k] != body[k] for k in identity) or (method!="direct" and old["evidence"].get("method_identity")!=body["evidence"].get("method_identity")):
                raise ValueError("This result key already names different video/conditions; inspect the conflict")
            return old
        if normalized_copy:
            _copy(*normalized_copy)
        if receipt_copy:
            _copy(*receipt_copy)
        _copy(source, root / body["video"], digest)
        for candidate in candidates:
            _copy(candidate["_source"], root / candidate["video"], candidate["video_sha256"])
        immutable(path, {**body, "sha256": signature(body)})
    return load(path)


def verify_entry(root, path):
    row = load(path)
    if row.get("schema") != VERSION or row.get("sha256") != signature({k: v for k, v in row.items() if k != "sha256"}):
        raise ValueError("Result entry identity changed")
    expected = entry_path(root, row["sample_id"], row["prompt_form"], row["method"], row["seed"], row.get("review_mode"))
    if expected.resolve() != Path(path).resolve():
        raise ValueError("Result stored under the wrong key")
    video = (Path(root) / row["video"]).resolve()
    if not video.is_relative_to(Path(root).resolve()) or sha(video) != row["video_sha256"]:
        raise ValueError("Result video is missing or changed")
    if row.get("normalization"):
        source_path = (Path(root) / row["source"]).resolve()
        if not source_path.is_relative_to(Path(root).resolve()) or sha(source_path) != row["source_sha256"]:
            raise ValueError("Normalized evaluation source is missing or changed")
    for candidate in row.get("candidates", []):
        candidate_path = (Path(root) / candidate["video"]).resolve()
        if not candidate_path.is_relative_to(Path(root).resolve()) or sha(candidate_path) != candidate["video_sha256"]:
            raise ValueError("Trajectory candidate is missing or changed")
    return row


def find(root, sample, form, method, seed, review_mode=None):
    if review_mode is None and method in REVIEW_METHODS:
        default = entry_path(root,sample,form,method,seed,'critic')
        if default.exists():return verify_entry(root,default)
    path = entry_path(root, sample, form, method, seed, review_mode)
    return verify_entry(root, path) if path.exists() else None


def import_manifest(repository, root, manifest):
    path = Path(manifest)
    if path.suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    else:
        rows = load(path)
        if isinstance(rows, dict):
            rows = rows["results"]
    if not isinstance(rows, list):
        raise ValueError("Use an array, {results: [...]} or JSONL")
    document=load(path) if path.suffix!='.jsonl' else None
    if isinstance(document,dict) and document.get('schema')=='lha-shard-export-v1':
        if signature({k:v for k,v in document.items() if k!='sha256'})!=document.get('sha256'):raise ValueError('Shard export changed')
        for row in rows:
            original=verify_entry(path.parent,path.parent/row['export_entry'])
            if original['sha256']!=row['export_entry_sha256'] or original['video_sha256']!=row['video_sha256']:
                raise ValueError('Imported shard differs from its original signed entry')
        planned={'schema':VERSION,'positions':document['planned_positions']}
        immutable(Path(root)/'plans'/(signature(planned)+'.json'),{**planned,'sha256':signature(planned)})
    relocated=[]
    for row in rows:
        row=copy.deepcopy(row)
        if row.get('normalization') and not Path(row['source']).is_absolute():row['source']=str((path.parent/row['source']).resolve())
        receipt=row.get('evidence',{}).get('receipt')
        if receipt and not Path(receipt).is_absolute():row['evidence']['receipt']=str((path.parent/receipt).resolve())
        for item in [row,*row.get('candidates',[])]:
            if not Path(item['video']).is_absolute():item['video']=str((path.parent/item['video']).resolve())
        relocated.append(import_video(repository,root,row))
    return relocated


def import_bernini(repository, root, run):
    """Read completed direct/official-PE cases from an existing frozen runner."""
    import sys
    scripts = str(Path(repository) / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from run_bernini_benchmark import read, verify_completed
    run = Path(run).resolve()
    plan = read(run / "plan.json")
    if signature({k: v for k, v in plan.items() if k != "sha256"}) != plan["sha256"]:
        raise ValueError("Bernini plan identity changed")
    result = []
    for case in plan["cases"]:
        directory = run / "cases" / case["case_id"]
        receipt = directory / "result.json"
        if not receipt.exists() or read(receipt).get("status") != "complete":
            continue
        complete = read(receipt)
        verify_completed(directory, complete)
        binding = read(directory / "input.json")
        if binding["case"] != case or binding["plan_sha256"] != plan["sha256"]:
            raise ValueError("Bernini case does not match its frozen plan")
        result.append(import_video(repository, root, {
            "prompt_form": case["tier"], "method": case["condition"], "seed": case["seed"],
            "source_sha256": case["source_sha256"], "request": case["prompt"],
            **({"normalization":case["normalization"], "original_source_sha256":case["original_source_sha256"],
                "source":case["source_video"]} if case.get("normalization") else {}),
            "video": str(directory / "native.mp4"), "video_sha256": complete["output_sha256"],
            "generation": plan["generation"], "evidence": {"receipt": str(receipt),
                "receipt_sha256": sha(receipt), "input_sha256": complete["input_sha256"],
                "runtime_sha256": binding["runtime_sha256"], "original_sample_id": case["sample_id"]}}))
    return result


def task_for_entry(task, entry, root):
    from planner_harness.upgrade import record
    if task:
        record(Path(root)/'reuse', entry['sample_id']+'-'+entry['prompt_form']+'-evaluation-source',
               {'source':entry['source_sha256'],'request':entry['request_sha256']},
               {'source':task['source_sha256'],'request':task['request_sha256']})
    saved = {k:entry[k] for k in ('sample_id','prompt_form','request','request_sha256','source','source_sha256','split','source_group') if k in entry}
    if task and entry.get('original_source_sha256',entry['source_sha256'])==task['source_sha256'] and entry['request_sha256']==task['request_sha256']:
        saved = {**task, **saved}
    if 'request' not in saved or 'source' not in saved:
        raise ValueError('Original evaluation request/source record is missing; restore it without regeneration')
    if entry.get('normalization'):
        saved.update(source=str((Path(root)/entry['source']).resolve()), normalization=entry['normalization'])
    return saved


def _evaluation_positions(repository, root):
    positions = []
    tasks = inventory(repository)
    for path in entry_files(root):
        entry = verify_entry(root, path)
        current = tasks.get((entry["sample_id"], entry["prompt_form"]))
        task_for_entry(current, entry, root)
        base = {"review_mode":normalize_review_mode(entry["method"],entry.get("review_mode")),"execution":entry.get("evidence",{}), **{k: entry[k] for k in ("original_source_sha256", "normalization", "source") if k in entry},**{k: entry[k] for k in ("sample_id", "prompt_form", "method", "seed", "source_sha256", "request_sha256", "video", "video_sha256")}}
        positions.append({**base, "position": "final"})
        if entry["method"] in TRAJECTORY_METHODS:
            first = next((c for c in entry.get("candidates", []) if "first" in c["roles"]), None)
            if first:
                positions.append({**base, "position": "first", "video": first["video"], "video_sha256": first["video_sha256"]})
            last = next((c for c in entry.get("candidates", []) if "last" in c["roles"]), None)
            if last:
                positions.append({**base, "position": "last", "video": last["video"], "video_sha256": last["video_sha256"]})
    return positions


def prepare_evaluation(repository, root, *, evaluation_id=None):
    """Start a fresh scoring namespace. No historical score/cache is imported."""
    from evaluation.low_high import profile
    from evaluation.creative import JUDGES, judge_identity
    root = Path(root).resolve()
    evaluation_id = evaluation_id or uuid.uuid4().hex
    if not SAFE.fullmatch(evaluation_id):
        raise ValueError("Evaluation ID must be one safe path component")
    directory = root / "evaluations" / evaluation_id
    if directory.exists():
        raise ValueError("A fresh evaluation requires a new ID; use score-evaluation to resume the current one")
    positions = _evaluation_positions(repository, root)
    pre_experience = any(p["method"] == "pre-experience" for p in positions) or any(
        p["method"] == "pre-experience"
        for path in (root / "plans").glob("*.json") for p in load(path)["positions"]
    )
    population_path=root/'analysis-population.json'
    body = {"schema": "lha-result-evaluation-v1", "evaluation_id": evaluation_id,
        "analysis_population":load(population_path) if population_path.exists() else None,
        "analysis_population_sha256":sha(population_path) if population_path.exists() else None,
        "protocol_sha256": profile()["sha256"], "judges": [judge_identity(j) for j in JUDGES],
        "positions": positions, "source_task": "original request and source video under the shared scoring handbook",
        "adapter_sha256": sha(Path(__file__).parents[1] / "evaluation/creative.py"),
        "comparison_pairs": comparison_pairs(pre_experience=pre_experience),
        "cache_scope": "this fresh evaluation only; bound additions retain the same rules"}
    with RunLock(root / "registry-owner"):
        immutable(directory / "profile.json", profile())
        immutable(directory / "evaluation.json", {**body, "sha256": signature(body)})
        save(root / "current-evaluation.json", {"path": str((directory / "evaluation.json").relative_to(root)),
            "sha256": sha(directory / "evaluation.json")})
    return load(directory / "evaluation.json")


def current_evaluation(root):
    from evaluation.low_high import profile
    from evaluation.creative import JUDGES, judge_identity
    root = Path(root).resolve()
    marker = root / "current-evaluation.json"
    if not marker.exists():
        return None
    pointer = load(marker)
    path = (root / pointer["path"]).resolve()
    if not path.is_relative_to(root / "evaluations") or sha(path) != pointer["sha256"]:
        raise ValueError("Current evaluation pointer changed")
    plan = load(path)
    if plan.get("schema") != "lha-result-evaluation-v1" or plan.get("sha256") != signature({k: v for k, v in plan.items() if k != "sha256"}):
        raise ValueError("Current evaluation identity changed")
    from planner_harness.upgrade import record
    record(path.parent, 'evaluation_defaults',
           {k:plan.get(k) for k in ('protocol_sha256','judges','adapter_sha256')},
           {'protocol_sha256':profile()['sha256'], 'judges':[judge_identity(j) for j in JUDGES],
            'adapter_sha256':sha(Path(__file__).parents[1]/'evaluation/creative.py')})
    if plan.get('analysis_population_sha256'):
        population_path=root/'analysis-population.json'
        if not population_path.exists() or sha(population_path)!=plan['analysis_population_sha256']:
            raise ValueError('Frozen evaluation population changed')
    positions = list(plan["positions"])
    for addition in sorted((path.parent / "additions").glob("*.json")):
        body = load(addition)
        if body.get("session_sha256") != plan["sha256"] or body.get("sha256") != signature({k: v for k, v in body.items() if k != "sha256"}):
            raise ValueError("Evaluation addition identity changed")
        positions.extend(body["positions"])
    keys = [(p["sample_id"], p["prompt_form"], p["method"], p["seed"], p.get("review_mode", "legacy" if p["method"] in REVIEW_METHODS else "shared"), p.get("position", "final")) for p in positions]
    if len(keys) != len(set(keys)):
        raise ValueError("Evaluation additions contain repeated positions")
    plan = {**plan, "positions": positions}
    return path.parent, plan


def append_evaluation(repository, root):
    """Append newly collected videos under the unchanged evaluation rules."""
    root = Path(root).resolve()
    with RunLock(root / "registry-owner"):
        active = current_evaluation(root)
        if active is None:
            raise ValueError("There is no active evaluation with the current protocol")
        directory, plan = active
        key = lambda p: (p["sample_id"], p["prompt_form"], p["method"], p["seed"], p.get("review_mode", "legacy" if p["method"] in REVIEW_METHODS else "shared"), p.get("position", "final"))
        previous = {key(p): p for p in plan["positions"]}
        new = []
        for position in _evaluation_positions(repository, root):
            if key(position) in previous:
                if previous[key(position)] != position:
                    raise ValueError("An existing evaluation position changed")
            else:
                new.append(position)
        if new:
            body = {"session_sha256": plan["sha256"], "positions": new}
            immutable(directory / "additions" / (signature(body) + ".json"), {**body, "sha256": signature(body)})
        return {"added": len(new), "positions": len(previous) + len(new), "evaluation_id": plan["evaluation_id"]}


def _score_key(position, judge):
    return signature({"source": position["source_sha256"], "request": position["request_sha256"],
                      "track": position["prompt_form"], "candidate": position["video_sha256"], "judge": judge})


def ensure_evaluation(repository, root, *, evaluation_id=None):
    """Use the current protocol session, or prepare one for the collected videos."""
    active = current_evaluation(root)
    if active is not None:
        return active
    root = Path(root).resolve()
    candidates = ([root/'evaluations'/evaluation_id/'evaluation.json'] if evaluation_id
                  else list((root/'evaluations').glob('*/evaluation.json')))
    candidates = [p for p in candidates if p.exists()]
    if len(candidates) > 1:
        raise ValueError('Several saved evaluations lack a current pointer; select the original evaluation ID, without rescoring')
    if candidates:
        path = candidates[0]
        with RunLock(root/'registry-owner'):
            save(root/'current-evaluation.json', {'path':str(path.relative_to(root)), 'sha256':sha(path)})
        return current_evaluation(root)
    prepare_evaluation(repository, root, evaluation_id=evaluation_id)
    return current_evaluation(root)


def score_evaluation(repository, root, budget=None, *, models=None):
    """Continue the saved evaluation; current defaults apply only to a new session."""
    from evaluation.creative import JUDGES, judge_identity, make_judge, judge_candidate
    from evaluation.low_high import freeze_plan
    from planner_harness.video import Video
    from planner_harness import accounting
    from planner_harness.report_call import ReportUnavailable
    repository, root = Path(repository).resolve(), Path(root).resolve()
    ensure_evaluation(repository, root)
    append_evaluation(repository, root)
    active = current_evaluation(root)
    if active is None:
        raise ValueError("Prepare a fresh evaluation for the current protocol first")
    directory, evaluation = active
    live = models is None or any(getattr(m, "requires_live_budget", False) for m in models.values())
    required = tuple("model:" + j + "/" + str(judge_identity(j)["reasoning_effort"] or "none") for j in JUDGES) + ("compute:features","compute:temporal")
    if budget is not None:accounting.install(directory / "accounting", budget, require_live=live, required_quotes=("compute:features","compute:temporal"))
    tasks = inventory(repository)
    with RunLock(directory / "evaluation-owner"):
        from planner_harness.resumption import reconcile_accounting, recover_texts
        reconcile_accounting(directory/'accounting')
        recover_texts(directory,directory/'accounting')
        for position in evaluation["positions"]:
            score_links = [directory/'scores'/(_score_key(position, j['model'])+'.json') for j in evaluation['judges']]
            if score_links and all(p.exists() for p in score_links):
                for link in score_links:_read_score(directory, link, evaluation)
                continue
            entry = find(root, position["sample_id"], position["prompt_form"], position["method"], position["seed"], position.get("review_mode"))
            available = [entry] + entry.get("candidates", []) if entry else []
            if not any(v["video_sha256"] == position["video_sha256"] for v in available):
                raise ValueError("Frozen evaluation candidate changed")
            task = task_for_entry(tasks.get((position["sample_id"], position["prompt_form"])), entry, root)
            topic = position["sample_id"] + "__" + position["prompt_form"]
            source = Video(repository / task["source"], directory / "tasks" / topic).info
            if source["sha256"] != position["source_sha256"] or task["request_sha256"] != position["request_sha256"]:
                raise ValueError("Frozen evaluation source/request changed")
            body={"track":position["prompt_form"]}
            reviewed=directory/'evaluation-inputs'/(topic+'.json')
            if reviewed.exists():
                supplement=load(reviewed)
                if supplement.get('source_sha256')!=source['sha256'] or supplement.get('request_sha256')!=task['request_sha256']:
                    raise ValueError('Reviewed task input differs from registered source/request')
                body.update(supplement['body'])
                if body['track']!=position['prompt_form']:raise ValueError('Reviewed input cannot change the registered task track')
            task_plan = freeze_plan(body, task["request"], source, directory / "tasks" / topic)
            candidate = Video(root / position["video"], directory / "tasks" / topic).info
            scope = accounting.scope(directory / "accounting", topic, "independent") if budget is not None else None
            from evaluation.final_suite import automatic
            measured=automatic(source,candidate,task_plan,directory/'automatic-metrics',accounting_scope=scope)
            for name in (row["model"] for row in evaluation["judges"]):
                key = _score_key(position, name)
                link = directory / "scores" / (key + ".json")
                if link.exists():
                    _read_score(directory, link, evaluation)
                    continue
                call = directory / "calls" / key
                if scope:accounting.bind(call, scope)
                from evaluation.creative import frozen_judge
                model = models[name] if models else frozen_judge(next(j for j in evaluation['judges'] if j['model']==name))
                try:
                    result = judge_candidate(task["request"], source, candidate, call, model=model, plan=task_plan)
                except ReportUnavailable:
                    result = {"status": "missing", "reason": "report_recovery_exhausted", "report": None,
                        "source_sha256": source["sha256"], "output_sha256": candidate["sha256"]}
                result={**result,'automatic':measured,'track':position['prompt_form']}
                result_path = call / "current-result.json"
                immutable(result_path, result)
                immutable(link, {"evaluation_sha256": evaluation["sha256"], "key": key,
                    "position": position, "judge": name, "result_path": str(result_path.relative_to(directory)),
                    "result_sha256": sha(result_path)})
    compare_evaluation(repository, root, models=models)
    return report(repository, root)


def compare_evaluation(repository, root, *, models=None):
    """Adapt registered positions to the existing randomized/swapped blind suite."""
    from collections import defaultdict
    from evaluation.final_suite import blind_pairs
    from evaluation.low_high import check_plan, freeze_plan, profile
    from evaluation.creative import JUDGES
    from planner_harness.video import Video
    root, repository = Path(root).resolve(), Path(repository).resolve()
    active = current_evaluation(root)
    if active is None:
        raise ValueError("Prepare the current evaluation before comparing")
    directory, evaluation = active
    groups, shared = defaultdict(dict), defaultdict(dict)
    def include(position, actual):
        label = position["method"]
        if label in TRAJECTORY_METHODS:
            label += "_" + position.get("position", "final")
        key = (position["sample_id"], position["prompt_form"], position["seed"])
        mode = normalize_review_mode(position["method"], position.get("review_mode"))
        destination = shared[key] if mode == "shared" else groups[*key, mode]
        if actual or label not in destination:destination[label] = position if actual else None
    for position in evaluation["positions"]:include(position, True)
    # Prepared positions retain missing candidates in the comparison denominator.
    for path in (root / "plans").glob("*.json"):
        for position in load(path)["positions"]:
            include(position, False)
            if position["method"] in TRAJECTORY_METHODS:include({**position,"position":"first"}, False)
    for key in shared:
        if not any(group[:3] == key for group in groups):groups[*key,"shared"] = {}
    for key in sorted({group[:3] for group in groups if group[3] in REVIEW_MODES}):
        cross={}
        for method in ('full','none','pre-experience'):
            label=method+'_final'
            # Reviewer ablation exists only when both modes are actually planned.
            # A planned but unavailable candidate still contributes its missing denominator.
            if not all(label in groups.get((*key,mode),{}) for mode in REVIEW_MODES):continue
            for mode in REVIEW_MODES:cross[label+'@'+mode]=groups.get((*key,mode),{}).get(label)
        if cross:groups[*key,'critic-vs-planner']=cross
    for (sample, form, seed, mode), group in groups.items():
        group.update({label:p for label,p in shared.get((sample,form,seed),{}).items() if label not in group})
        if seed == 42 and any(k in group for k in ("full_final", "none_final", "pre-experience_final", "pe-loop_final", "pe", "planner-once", "direct-best-of-n")):
            group.setdefault("direct", None)
        if "lineage-chain" in group or "lineage-source-restart" in group:
            group.setdefault("lineage-chain", None);group.setdefault("lineage-source-restart", None)
        for method in TRAJECTORY_METHODS:
            if method + "_final" in group:group.setdefault(method + "_first", None)
    from evaluation.statistics import analysis_plan_for
    pairs = evaluation["comparison_pairs"]
    analysis_plan = analysis_plan_for(any(label.startswith("pre-experience_") for pair in pairs for label in pair))
    if evaluation.get('analysis_population'):
        analysis_plan={**analysis_plan,'population':'Full benchmark for main analysis; frozen RSI heldout subset reported separately'}
    contrast_body={"evaluation_sha256":evaluation["sha256"],"pairs":pairs,"analysis_plan":analysis_plan}
    immutable(directory/"contrast-plan-v2.json",{**contrast_body,"sha256":signature(contrast_body)})
    contrasts = contrast_body["pairs"]
    tasks = inventory(repository)
    records = []
    with RunLock(directory / "comparison-owner"):
        for (sample, form, seed, mode), positions in sorted(groups.items()):
            pairs = [(a, b) for a, b in contrasts if a in positions and b in positions]
            if not pairs:
                continue
            topic_id = sample + "__" + form
            present = [p for p in positions.values() if p]
            if present and len({p["source_sha256"] for p in present}) != 1:
                raise ValueError("Pairwise comparison requires the same prepared source time axis")
            task = task_for_entry(tasks[sample, form], present[0], root) if present else tasks[sample, form]
            source = Video(repository / task["source"], directory / "tasks" / topic_id).info
            plan_path = directory / "tasks" / topic_id / "plan.json"
            plan = check_plan(load(plan_path), task["request"], source) if plan_path.exists() else freeze_plan({"track": form}, task["request"], source, plan_path.parent)
            videos = {label: Video(root / p["video"], directory / "tasks" / topic_id).info for label, p in positions.items() if p}
            output = blind_pairs(repository, directory, {"id": topic_id, "request": task["request"]}, videos,
                judges=models, judge_specs=evaluation["judges"], source_plan=(source, plan), pairs=pairs, media_root=root / "media", write_topic_record=False, retain_unknown=True)
            for judge, rows in output.items():
                for left, right in pairs:
                    label = left + "__to__" + right
                    path = None
                    if left in videos and right in videos:
                        identity = {"source": source["sha256"], "left": videos[left]["sha256"], "right": videos[right]["sha256"],
                            "plan": plan["sha256"], "profile": profile()["sha256"], "judge": judge, "seed": 0}
                        from planner_harness.upgrade import cache_directory
                        cached, _ = cache_directory(directory / "blind-judge", identity,
                            ('source','left','right','plan','judge','seed'))
                        path = cached / "result.json"
                    records.append({"sample_id": topic_id + "__" + str(seed) + ("__review-"+mode if mode!="shared" else ""), "source_id": source["sha256"], "review_mode":mode,
                        "length": form, "judge": judge, "comparison": label,"split":task["split"],"source_group":task["source_group"],"seed":seed,
                        "availability":{"left":left in videos,"right":right in videos},
                        "positions":{left:positions[left],right:positions[right]},
                        "runtime":{k:(positions[k] or {}).get("execution",{}) for k in (left,right)},
                        "path": str(path.relative_to(directory)) if path else None, "sha256": sha(path) if path else None, "result": rows[label]})
        body = {"evaluation_sha256": evaluation["sha256"], "records": records}
        save(directory / "comparison-index.json", {**body, "sha256": signature(body)})
    return records


def _read_score(directory, path, evaluation):
    link = load(path)
    result_path = (directory / link["result_path"]).resolve()
    if link["evaluation_sha256"] != evaluation["sha256"] or not result_path.is_relative_to(directory) or sha(result_path) != link["result_sha256"]:
        raise ValueError("Active evaluation score binding changed")
    if link["key"] != _score_key(link["position"], link["judge"]) or path.name != link["key"] + ".json":
        raise ValueError("Active evaluation score key changed")
    result = load(result_path)
    if result["source_sha256"] != link["position"]["source_sha256"] or result["output_sha256"] != link["position"]["video_sha256"]:
        raise ValueError("Active evaluation score/video differs")
    return result


def register_plan(root, batch):
    """Only genuinely prepared method positions become missing rows in the view."""
    body = {"schema": VERSION, "positions": [{"sample_id": t["sample_id"], "prompt_form": t["prompt_form"],
        "method": m, "seed": batch["seed_sequence"]["start"], "review_mode": normalize_review_mode(m,batch.get("review",{}).get("mode") if m in REVIEW_METHODS else None)} for t in batch["topics"] for m in t.get("methods",batch["arms"])]}
    immutable(Path(root) / "plans" / (signature(body) + ".json"), {**body, "sha256": signature(body)})


def evaluation_coverage(directory, evaluation):
    """Expose every metric family and its actual status across unique judgments."""
    from collections import Counter
    from evaluation.final_suite import ratings
    from evaluation.registry import LOW_HIGH_AESTHETICS, LOW_HIGH_RECAST_EXTENT, LOW_HIGH_REPORTED_SPECIALTIES
    from evaluation.validation import DIMENSIONS
    families = {
        'main': tuple(DIMENSIONS),
        'short': LOW_HIGH_REPORTED_SPECIALTIES,
        'long_and_requirements': ('edit_completion', 'binding_accuracy', 'joint_satisfaction',
                                  'required_correspondence', 'unrequested_damage', 'major_damage'),
        'aesthetics': (*LOW_HIGH_AESTHETICS, 'aesthetic_mean'),
        'objective_and_motion': ('clip_f', 'dino_f', 'flow_warp_l1', 'motion_diagonals_per_second',
                                 'low_motion_duration_fraction', 'flow_velocity_error'),
        'recast_extent': LOW_HIGH_RECAST_EXTENT,
    }
    counts = {group: {name: Counter() for name in names} for group, names in families.items()}
    seen, event_reviews = set(), 0
    for position in evaluation['positions']:
        for judge in evaluation['judges']:
            key = _score_key(position, judge['model'])
            if key in seen:
                continue
            seen.add(key)
            link = directory / 'scores' / (key + '.json')
            result = _read_score(directory, link, evaluation) if link.exists() else {}
            metrics = ratings(result)
            absent = 'pending' if not link.exists() else 'missing' if result.get('status') == 'missing' else 'not_measured'
            event_reviews += result.get('event_reviews', 0)
            for group, names in families.items():
                for name in names:
                    counts[group][name][metrics.get(name, {}).get('status', absent)] += 1
    blind = Counter()
    index = directory / 'comparison-index.json'
    if index.exists():
        for record in load(index)['records']:
            for question in ('task_completion', 'production_quality'):
                judgment = (record['result'].get('judgments') or {}).get(question)
                blind[(judgment or {}).get('outcome', 'missing')] += 1
    return {'scope': 'current evaluation collection; duplicate video/task/judge calls counted once',
            'unique_judgments': len(seen), 'metric_families': counts,
            'continuous_event_reviews': event_reviews, 'blind_question_outcomes': dict(blind),
            'blind_comparisons_finished': index.exists()}


def _report_table(title, headers, rows):
    if not rows:
        return ""
    cells = lambda tag, values: "".join(f"<{tag}>{html.escape(str(value))}</{tag}>" for value in values)
    return (f"<h2>{html.escape(title)}</h2><div class='table-scroll'><table><thead><tr>"
            + cells("th", headers) + "</tr></thead><tbody>"
            + "".join("<tr>" + cells("td", row) + "</tr>" for row in rows)
            + "</tbody></table></div>")


def _score_tables(summary):
    from evaluation.registry import LOW_HIGH_AESTHETICS, LOW_HIGH_METRICS, LOW_HIGH_REPORTED_SPECIALTIES
    from evaluation.validation import DIMENSIONS

    labels = dict(zip(DIMENSIONS, ("指令达成", "必要内容保留", "时序一致性", "视觉完整性", "美学协调")))
    labels.update(style_realization="风格实现", scene_specific_design="场景针对性设计",
                  effective_creativity="有效创造性", edit_completion="要求完成", binding_accuracy="对象与属性绑定",
                  joint_satisfaction="联合满足", required_correspondence="必要对应",
                  unrequested_damage="非预期损伤", major_damage="重大损伤",
                  narrative_emotional_fit="叙事与情绪", style_world_consistency="风格与世界一致性",
                  composition_lighting="构图与光影", color_texture="色彩与材质",
                  hierarchy_readability="层次与可读性", aesthetic_mean="美学均值")
    scopes = {"all": "全部", "short": "短任务", "long": "长任务"}
    groups = summary.get("metrics", {}).get("groups", [])
    main = [group for group in groups if "/planner" not in group["variant"]]
    self_review = [group for group in groups if "/planner" in group["variant"]]
    selected = [group for group in main if not group["variant"].endswith(("_first", "_last"))]
    long = ("edit_completion", "binding_accuracy", "joint_satisfaction", "required_correspondence",
            "unrequested_damage", "major_damage")
    auxiliary = tuple(key for key in LOW_HIGH_METRICS if key not in
                      {*DIMENSIONS, *LOW_HIGH_REPORTED_SPECIALTIES, *long, *LOW_HIGH_AESTHETICS, "aesthetic_mean"})

    def cell(metric):
        mean = metric["mean_source_macro"]
        if mean is None:
            states = {"unknown": "未知", "not_assessed": "未评", "not_applicable": "不适用",
                      "missing": "缺失", "not_measured": "未测", "execution_failed": "执行失败"}
            value = "、".join(f"{states.get(state, state)} {count}"
                              for state, count in metric["statuses"].items() if count)
        else:
            value = f"{mean:.3f}"
        return f"{value}（{metric['valid']}/{metric['planned']}）"

    def metrics(title, keys, selection):
        return _report_table(title, ["方法与位置", "判官", "范围", *(labels.get(k, k) for k in keys)],
                             [[variant_label(g["variant"]), g["judge"], scopes[g["length"]],
                               *(cell(g["dimensions"][k]) for k in keys)] for g in selection])

    def variant_label(variant):
        position = "在线选中"
        if variant.endswith("_first"):
            variant, position = variant.removesuffix("_first"), "首轮"
        elif variant.endswith("_last"):
            variant, position = variant.removesuffix("_last"), "末轮"
        method, _, mode = variant.partition("/")
        label = {"pre-experience": "预经验", "full": "全经验", "none": "历史无经验",
                 "direct": "Direct", "pe-loop": "PE Loop"}.get(method, method)
        review = {"critic": "独立 Critic", "planner": "Planner 自评"}.get(mode)
        if method not in TRAJECTORY_METHODS:
            return label
        return " / ".join(part for part in (label, review, position) if part)

    comparisons = []
    for comparison, judges in summary.get("blind_comparisons", {}).items():
        for judge, by_scope in judges.items():
            for scope, questions in by_scope.items():
                for question, counts in questions.items():
                    comparisons.append([comparison, judge, scopes[scope],
                                        {"task_completion": "任务完成", "production_quality": "制作质量"}[question],
                                        counts["left"], counts["tie"], counts["right"],
                                        counts["unknown"], counts["order_unstable"], counts["missing"],
                                        f"{counts['valid']}/{counts['planned']}"])
    return "".join([
        metrics("五维主表（0–4）", DIMENSIONS, main),
        metrics("Planner 自评消融五维（0–4）", DIMENSIONS, self_review),
        metrics("短任务专项（0–4）", LOW_HIGH_REPORTED_SPECIALTIES, [g for g in selected if g["length"] == "short"]),
        metrics("长任务专项（0–1）", long, [g for g in selected if g["length"] == "long"]),
        metrics("美学明细（0–4）", (*LOW_HIGH_AESTHETICS, "aesthetic_mean"), selected),
        metrics("客观指标与运动诊断", auxiliary, selected),
        _report_table("独立盲评", ["对照（左 → 右）", "判官", "范围", "问题", "左胜", "平",
                                    "右胜", "未知", "顺序不稳", "缺失", "有效／计划"], comparisons),
    ])


def report(repository, root, *, methods=None, seeds=None, splits=None, forms=None, review_modes=None, analysis_population=None, output_name="index"):
    root = Path(root).resolve()
    if not SAFE.fullmatch(output_name):raise ValueError('Use a safe report name')
    population_path=root/'analysis-population.json'
    if population_path.exists():
        cohort=load(population_path)
        if cohort['benchmark_sha256']!=sha(Path(repository)/'benchmark_data/benchmark.json'):
            from planner_harness.upgrade import record
            record(root, 'report_inventory', cohort['benchmark_sha256'], sha(Path(repository)/'benchmark_data/benchmark.json'))
    analysis_population=analysis_population or ('main' if population_path.exists() else 'test')
    if analysis_population=='rsi' and splits!=['test']:
        raise ValueError('RSI report must filter heldout tasks')
    tasks = inventory(repository)
    rows, positions = [], set()
    plans = list((root / "plans").glob("*.json"))
    for path in plans:
        plan = load(path)
        if plan.get("sha256") != signature({k: v for k, v in plan.items() if k != "sha256"}):
            raise ValueError("Registered result plan changed")
        positions.update((p["sample_id"], p["prompt_form"], p["method"], p["seed"],normalize_review_mode(p["method"],p.get("review_mode"))) for p in plan["positions"])
    if not plans or any((root / "entries").glob("*/*/direct/seed-42.json")):
        # The current Direct task is already authorized for all current sources.
        positions.update((sample, form, "direct", 42,"shared") for sample, form in tasks)
    positions.update((r["sample_id"], r["prompt_form"], r["method"], r["seed"],normalize_review_mode(r["method"],r.get("review_mode")))
        for r in (verify_entry(root, p) for p in entry_files(root)))
    for sample, form, method, seed, mode in sorted(positions):
        task = tasks.get((sample, form))
        entry = find(root, sample, form, method, seed,mode)
        if entry:task = task_for_entry(task, entry, root)
        if not task:
            raise ValueError("Saved unfinished position needs its original task metadata; no generation was submitted")
        if (splits and task["split"] not in splits) or (forms and form not in forms) or (methods and method not in methods) or (seeds and seed not in seeds) or (review_modes and mode not in {*review_modes,"shared"}):
            continue
        entry = find(root, sample, form, method, seed,mode)
        if entry:
            task = task_for_entry(task, entry, root)
        rows.append({**task, "method": method, "seed": seed, "review_mode":mode,
            "status": "ready" if entry else "missing", "video": entry["video"] if entry else None,
            "video_sha256": entry["video_sha256"] if entry else None, "evaluation_status": "pending",
            "candidates": entry.get("candidates", []) if entry else [],"execution": entry.get("evidence",{}) if entry else {}})
    def selected_comparison(record):
        sample=record['sample_id'].split('__')[0];form=record['length'];task=tasks.get((sample,form),{})
        split=record.get('split',task.get('split'))
        seed=record.get('seed')
        if seed is None:
            try:seed=int(record['sample_id'].rsplit('__',1)[1])
            except (ValueError,IndexError):seed=42
        labels=record['comparison'].split('__to__')
        bases=[label.split('@')[0].removesuffix('_first').removesuffix('_final') for label in labels]
        mode=record.get('review_mode','shared')
        selected_mode=not review_modes or mode in {*review_modes,'shared'} or (mode=='critic-vs-planner' and set(REVIEW_MODES)<=set(review_modes))
        return (not splits or split in splits) and (not forms or form in forms) and (not seeds or seed in seeds) and (not methods or all(m in methods for m in bases)) and selected_mode
    from evaluation.final_suite import ratings
    active = current_evaluation(root)
    metric_rows=[]
    for row in rows:
        row["judges"] = {}
        if active and row["video"]:
            directory, evaluation = active
            for identity in evaluation["judges"]:
                name = identity["model"]
                link = directory / "scores" / (_score_key(row, name) + ".json")
                if link.exists():
                    result = _read_score(directory, link, evaluation)
                    row["judges"][name] = {"status": result.get("status", "scored"), "report": result.get("report"),
                        "metrics": ratings(result),
                        "record": str(link.relative_to(root))}
        if active:
            for identity in active[1]['judges']:
                name=identity['model'];link=active[0]/'scores'/(_score_key(row,name)+'.json') if row['video'] else None
                metric_rows.append({'source_id':row['source_sha256'],'sample_id':row['sample_id']+'__'+row['prompt_form']+'__'+str(row['seed']),
                    'length':row['prompt_form'],'judge':name,'variant':result_variant(row['method'],row['review_mode']),
                    'result':_read_score(active[0],link,active[1]) if link and link.exists() else None})
        if row["judges"]:
            full = len(row["judges"]) == len(active[1]["judges"])
            missing = any(j["report"] is None or j["status"] == "missing" for j in row["judges"].values())
            row["evaluation_status"] = ("complete_with_missing" if missing else "complete") if full else "partial"
        for role in ('first', 'last') if row['method'] in TRAJECTORY_METHODS else ():
            candidate = next((c for c in row['candidates'] if role in c['roles']), None)
            if candidate:
                row[role] = {**candidate, "judges": {}}
            candidate_position = {**row, **candidate} if candidate else None
            if active:
                for identity in active[1]["judges"]:
                    name = identity["model"]
                    link = active[0] / "scores" / (_score_key(candidate_position, name) + ".json") if candidate_position else None
                    result = _read_score(active[0], link, active[1]) if link and link.exists() else None
                    if result:
                        row[role]["judges"][name] = {"metrics": ratings(result), "record": str(link.relative_to(root))}
                    metric_rows.append({"source_id": row["source_sha256"], "sample_id": row["sample_id"] + "__" + row["prompt_form"] + "__" + str(row["seed"]),
                        "length": row["prompt_form"], "judge": name, "variant": result_variant(row["method"],row["review_mode"]) + "_" + role, "result": result})
    summary = {"schema": VERSION, "planned": len(rows), "ready": sum(r["status"] == "ready" for r in rows),
               "evaluation_status": "current_evaluation" if active else "pending_new_evaluation", "analysis_population":analysis_population, "results": rows}
    if active:
        from evaluation.low_high_summary import summarize
        summary['metrics']=summarize(metric_rows)
        summary['evaluation_coverage'] = evaluation_coverage(*active)
        index_path = active[0] / "comparison-index.json"
        if index_path.exists():
            index = load(index_path)
            if index.get("evaluation_sha256") != active[1]["sha256"] or index.get("sha256") != signature({k: v for k, v in index.items() if k != "sha256"}):
                raise ValueError("Current blind comparison index changed")
            records=[r for r in index["records"] if selected_comparison(r)]
            for record in records:
                if record["path"] is None:
                    if record["result"].get("status") != "missing" or record["result"].get("judgments") is not None:
                        raise ValueError("Missing blind comparison must remain explicit")
                    continue
                path = (active[0] / record["path"]).resolve()
                if not path.is_relative_to(active[0]) or sha(path) != record["sha256"] or load(path) != record["result"]:
                    raise ValueError("Current blind comparison result changed")
            from evaluation.pairwise import summary as summarize_blind
            summary["blind_comparisons"] = {label + ("/review-"+mode if mode!="shared" else ""): summarize_blind([{**r, "result": r["result"] if r["result"].get("judgments") else None} for r in records if r["comparison"] == label and r.get("review_mode","shared")==mode])
                for label, mode in sorted({(r["comparison"],r.get("review_mode","shared")) for r in records})}
            from evaluation.low_high_summary import paired
            differences={}
            for record in records:
                label=record['comparison'];mode=record.get('review_mode','shared')
                key=label+('/review-'+mode if mode!='shared' else '')
                sides=[]
                for side in label.split('__to__'):
                    position=record.get('positions',{}).get(side)
                    link=active[0]/'scores'/(_score_key(position,record['judge'])+'.json') if position else None
                    sides.append(_read_score(active[0],link,active[1]) if link and link.exists() else None)
                differences.setdefault(key,[]).append({'sample_id':record['sample_id'],'source_id':record.get('source_group',record['source_id']),
                    'length':record['length'],'judge':record['judge'],'before':sides[0],'after':sides[1]})
            summary['paired_differences']={key:paired(values) for key,values in differences.items()}
    if active and index_path.exists():
        from evaluation.statistics import summarize as formal_summary
        pre_experience = any(label.startswith("pre-experience_") for pair in active[1]["comparison_pairs"] for label in pair)
        modes={r.get('review_mode','shared') for r in records}
        key={'test':'test_analysis','main':'main_analysis','rsi':'rsi_analysis'}[analysis_population]
        summary[key]=formal_summary(records,population=analysis_population,pre_experience=pre_experience) if modes<={'shared','legacy'} else {'by_review_mode':{mode:formal_summary([r for r in records if r.get('review_mode','shared')==mode],population=analysis_population,pre_experience=pre_experience) for mode in sorted(modes)}}
    save(root / ("results.json" if output_name=="index" else output_name+".json"), summary)
    body = ['<!doctype html><meta charset="utf-8"><title>LHA 视频结果</title>',
        '<style>body{font:16px system-ui;max-width:1200px;margin:auto;padding:24px}section{border-top:1px solid #ccc;padding:16px 0}video{max-width:100%;max-height:360px}p{white-space:pre-wrap}.table-scroll{overflow-x:auto}table{border-collapse:collapse;font-size:14px}th,td{border:1px solid #ccc;padding:.45em .65em;text-align:left}th{background:#f3f3f3}</style>',
        '<h1>LHA 视频结果</h1><p>已就绪 ' + str(summary["ready"]) + ' / ' + str(summary["planned"]) + '；按当前评价会话显示评分。</p>']
    body.append('<p>统计范围：'+{'main':'全量主实验','rsi':'RSI 后段测试集','test':'当前筛选范围'}[analysis_population]+'</p>')
    if summary.get("metrics"):
        body.append("<p>各格为按源视频等权的均值（有效条件数／计划条件数）。判官分别报告。</p>")
        body.append(_score_tables(summary))
    if summary.get('evaluation_coverage'):
        body.append('<details><summary>全量评分执行情况</summary><pre>' + html.escape(json.dumps(summary['evaluation_coverage'], ensure_ascii=False, indent=2)) + '</pre></details>')
    if analysis_population=='main' and (root/'rsi.html').exists():body.append('<a href="rsi.html">RSI 测试集对照</a>')
    if summary.get('paired_differences'):
        body.append('<details><summary>当前配对差值</summary><pre>'+html.escape(json.dumps(summary['paired_differences'],ensure_ascii=False,indent=2))+'</pre></details>')
    for row in rows:
        label = {"pre-experience": "预经验", "full": "全经验"}.get(row["method"], row["method"])
        body.append('<section><h2>' + html.escape(f'{row["sample_id"]} / {row["prompt_form"]} / {result_variant(row["method"],row["review_mode"]).replace(row["method"], label, 1)} / seed {row["seed"]}') + '</h2><p>' + html.escape(row["request"]) + '</p>')
        body.append('<video controls preload="none" src="' + quote(row["video"], safe="/.") + '"></video><p>' + ('待新评价' if not row["judges"] else '当前评价：' + html.escape(row["evaluation_status"])) + '</p>' if row["video"] else '<p>视频缺失</p>')
        for name, judgment in row["judges"].items():
            body.append('<h3>' + html.escape(name) + '</h3><pre>' + html.escape(json.dumps(judgment.get("metrics") or {"status":judgment["status"]}, ensure_ascii=False, indent=2)) + '</pre>')
        if row['execution'].get('reviews'):
            body.append('<details><summary>在线复核 '+html.escape(row['review_mode'])+'</summary><pre>'+html.escape(json.dumps(row['execution']['reviews'],ensure_ascii=False,indent=2))+'</pre></details>')
        if row['execution'].get('selection'):
            body.append('<details><summary>候选选择依据</summary><pre>'+html.escape(json.dumps(row['execution']['selection'],ensure_ascii=False,indent=2))+'</pre></details>')
        for role, title in (('first', '首轮'), ('last', '末轮')):
            if row.get(role):
                candidate = row[role]
                body.append('<details><summary>' + title + ' ' + html.escape(candidate["id"]) + ' / seed ' + str(candidate["seed"]) + '</summary>')
                body.append('<video controls preload="none" src="' + quote(candidate["video"], safe="/.") + '"></video>')
                body.append('<pre>' + html.escape(json.dumps(candidate["judges"] or {"status": "待新评价"}, ensure_ascii=False, indent=2)) + '</pre></details>')
        body.append('</section>')
    (root / (output_name+".html")).write_text("\n".join(body), encoding="utf-8")
    return summary


def export_shard(repository,root,run,target):
    """Portable signed entries/media for an explicit nonoverlapping local shard."""
    from .device_scheduler import shard_topics
    from .creative_benchmark import copy_verified
    run,root,target=Path(run),Path(root),Path(target)
    batch=load(run/'batch.json');host=load(run/'host.json')
    topics=shard_topics(batch,host);keys={(t['sample_id'],t['prompt_form']) for t in topics}
    tasks=inventory(repository);rows=[]
    for path in entry_files(root):
        entry=verify_entry(root,path)
        if (entry['sample_id'],entry['prompt_form']) not in keys:continue
        if entry['method'] not in batch['arms'] and not(entry['method']=='direct' and 'direct-best-of-n' in batch['arms']):continue
        if entry['method'] in REVIEW_METHODS and normalize_review_mode(entry['method'],entry.get('review_mode'))!=batch.get('review',{}).get('mode','legacy'):continue
        for candidate in [entry,*entry.get('candidates',[])]:copy_verified(root/candidate['video'],target/candidate['video'],candidate['video_sha256'])
        relative=path.relative_to(root);copy_verified(path,target/relative)
        row={k:entry[k] for k in ('sample_id','prompt_form','method','seed','source_sha256','video','video_sha256','generation')}
        if entry.get('normalization'):
            copy_verified(root / entry['source'], target / entry['source'], entry['source_sha256'])
            row.update({k:entry[k] for k in ('source','original_source_sha256','normalization')})
        row['review_mode']=normalize_review_mode(entry['method'],entry.get('review_mode'))
        row['candidates']=entry.get('candidates',[])
        evidence=copy.deepcopy(entry['evidence'])
        if evidence.get('receipt_sha256'):
            digest=evidence['receipt_sha256'];receipt=Path(evidence['receipt'])
            if not receipt.exists():receipt=root/'receipts'/(digest+'.json')
            portable='receipts/'+digest+'.json';copy_verified(receipt,target/portable,digest)
            evidence['original_receipt']=evidence.get('original_receipt',evidence['receipt']);evidence['receipt']=portable
        row.update(request=tasks[entry['sample_id'],entry['prompt_form']]['request'],evidence={**evidence,'export_batch_sha256':batch['sha256'],'original_entry_sha256':entry['sha256']},
            export_entry=str(relative),export_entry_sha256=entry['sha256'])
        rows.append(row)
    body={'schema':'lha-shard-export-v1','batch_sha256':batch['sha256'],'profile_sha256':batch['profile_sha256'],
        'shard_rank':host.get('shard_rank',0),'shard_count':host.get('shard_count',1),'results':rows,
        'planned_positions':[{'sample_id':t['sample_id'],'prompt_form':t['prompt_form'],'method':m,'seed':batch['seed_sequence']['start'],'review_mode':normalize_review_mode(m,batch.get('review',{}).get('mode') if m in REVIEW_METHODS else None)} for t in topics for m in t.get('methods',batch['arms'])]}
    immutable(target/'manifest.json',{**body,'sha256':signature(body)})
    return target/'manifest.json'
