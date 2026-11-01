"""Frozen paired validation, evidence receipts and reviewed library transactions."""
from __future__ import annotations

import base64
import copy
import json
import math
from pathlib import Path

from .common import ROOT, load, save, sha, stamp
from .ledger import digest
from .lock import RunLock
from .rsi_data import sealed, verify_seal
from .rsi_support import candidate_knowledge


def runtime_hashes():
    source = Path(__file__).parents[1]
    result = {p.relative_to(source).as_posix(): sha(p) for package in ("planner_harness", "critic_harness", "evaluation", "server_runtime", "vlm")
            for p in (source / package).rglob("*") if p.suffix in {".py", ".md"}}
    for name in ("run_planner_worker.py", "run_rsi.py"):
        path = source.parent / "scripts" / name
        result["scripts/" + name] = sha(path)
    return result


def prepare(splits_path, proposal_path, output, protocol, *, root=ROOT, cycle_path=None, split="V", replay_gate_path=None, adoption_path=None):
    """Freeze a runnable paired specification, without starting a model or renderer."""
    root, output = Path(root).resolve(), Path(output).resolve()
    splits, proposal = verify_seal(load(splits_path)), verify_seal(load(proposal_path))
    protocol = copy.deepcopy(protocol)
    if proposal["status"] != "proposed":
        raise ValueError("There is no proposed experience change to validate")
    if sha(proposal["candidate_catalog"]) != proposal["candidate_catalog_sha256"]:
        raise ValueError("Proposed catalog changed")
    for field in ("execution", "planner", "judge", "selector", "seed_schedule", "generation_budget", "primary_metric"):
        if field not in protocol:
            raise ValueError("Freeze validation field: " + field)
    if protocol["primary_metric"] not in {"non_improving_generations", "selection_regret", "success_at_budget", "selected_utility", "delivered_success"}:
        raise ValueError("Choose one primary decision metric before validation")
    live = protocol["execution"].get("mode", "live") == "live"
    if live:
        validate_quality_protocol(protocol)
    budget, seeds = protocol["generation_budget"], protocol["seed_schedule"]
    if type(budget) is not int or budget < 1 or len(seeds) < budget or any(type(s) is not int for s in seeds):
        raise ValueError("Fixed seed schedule must cover the generation budget")
    if not protocol["execution"].get("critic") or not protocol["judge"].get("model") or not protocol["judge"].get("protocol_sha256"):
        raise ValueError("Freeze online Critic and an independently configured final judge")
    critic = protocol["execution"]["critic"]
    critic.setdefault("model", "gpt-6.1-sol")
    critic.setdefault("reasoning_effort", "xhigh")
    critic.setdefault("max_turns", 12)
    supported = {"kind": "online_ledger_lexicographic", "order": ["preserve_core", "edit", "preserve_detail"], "unknown": "lower_bound", "ties": "earliest"}
    if protocol["selector"].get("unknown") == "ineligible" and protocol["execution"].get("mode") == "replay":
        protocol["selector"] = supported  # Compatibility for explicitly synthetic fixtures.
    if protocol["selector"] != supported:
        raise ValueError("Use the frozen lower-bound selector for controls; loop gates measure Planner selection")
    if split not in {"D", "V", "T"}:
        raise ValueError("Select D, V or T explicitly")
    tasks = [t for t in splits["tasks"] if t["split"] == split]
    if not tasks:
        raise ValueError("No tasks exist in the selected split")
    cycle = None
    if cycle_path:
        from .rsi_cycle import verify
        cycle = verify(cycle_path)
        if "task_card_hashes" in cycle["protocol"]:
            protocol["task_card_hashes"] = cycle["protocol"]["task_card_hashes"]
        if cycle["split_sha256"] != splits["sha256"] or any(protocol.get(k) != v for k, v in cycle["protocol"].items() if k != "max_changed_cards"):
            raise ValueError("Task protocol differs from its experiment cycle")
    elif protocol["execution"].get("mode", "live") == "live":
        raise ValueError("Live runs require one frozen experiment cycle shared across rounds")
    if protocol["execution"].get("mode", "live") == "live":
        if split == "T":
            if not adoption_path:
                raise ValueError("Freeze the reviewed E_final adoption before test-set execution")
            adoption = load(adoption_path)
            if adoption.get("status") != "complete" or not adoption.get("reviewed_by") or adoption.get("proposal_sha256") != proposal["sha256"]:
                raise ValueError("Test candidate does not match a completed reviewed adoption")
        if split == "V":
            if not replay_gate_path:
                raise ValueError("Live candidate validation requires a passed paired behavioral replay")
            gate = verify_seal(load(replay_gate_path))
            original = verify_seal(load(gate["replay_path"])) if gate.get("schema") == "lha-rsi-replay-review-v1" else gate
            if gate.get("schema") == "lha-rsi-replay-review-v1" and original["sha256"] != gate["replay_sha256"]:
                raise ValueError("Reviewed replay evidence changed")
            if original.get("runtime") != runtime_hashes():
                raise ValueError("Replay used different code from this validation cycle")
            if original.get("cycle_sha256") != cycle["sha256"]:
                raise ValueError("Formal replay and validation must use the same frozen cycle")
            if gate["status"] != "passed" or original.get("candidate_catalog_sha256") != proposal["candidate_catalog_sha256"]:
                raise ValueError("Replay did not support this experience candidate")
            if original.get("replay_role") != "heldout" or not original.get("partition"):
                raise ValueError("Development replay is diagnostic; live V requires held-out replay")
            from .rsi_evidence import verify_holdout
            packet = load(Path(proposal_path).parent / "proposal-input.json")
            partition_ref = original["partition"]
            if sha(partition_ref["path"]) != partition_ref["sha256"]:
                raise ValueError("Held-out partition changed")
            partition_rows = verify_seal(load(partition_ref["path"]))["decisions"]
            used = {s["decision_id"] for s in original["samples"]}
            verify_holdout(partition_ref["path"], packet["development"]["records"],
                           {r["id"]:r["input"] for r in partition_rows if r["id"] in used})
            if original.get("base_catalog_semantic_sha256") != digest(load(root / "knowledge/experience/catalog.json")):
                raise ValueError("Replay used a different experience base")
        from .task_criteria import validate as validate_card
        for task in tasks:
            card = validate_card(load(task["card"]))
            if card["source_sha256"] != task["source_sha256"] or card["requirement"] != task["request"]:
                raise ValueError("Freeze source-only independent cards matching validation tasks")
            task["card_file_sha256"] = sha(task["card"])
            if task.get("references"):
                task["references_sha256"] = sha(task["references"])
    base_catalog = root / "knowledge/experience/catalog.json"
    if split == "V" and (sha(base_catalog) != proposal["base_catalog_sha256"] or any(sha(root / p) != h for p, h in proposal["base_files"].items())):
        raise ValueError("Experience base changed before validation preparation")
    from .knowledge import Knowledge
    if not (output / "base-knowledge.json").exists():
        if cycle:
            from .rsi_cycle import planner_snapshot
            packet_path = Path(proposal_path).parent / "proposal-input.json"
            if sha(packet_path) != proposal.get("proposal_input_sha256"):
                raise ValueError("Frozen proposal base material changed")
            packet = load(packet_path)
            if split == "T":
                save(output / "base-knowledge.json", load(cycle["initial_planner_knowledge"]["path"]))
            else:
                planner_snapshot(cycle, packet["base_catalog"], packet["base_documents"], output / "base-knowledge.json", root=root)
            candidate = candidate_knowledge(root, proposal["candidate_catalog"])
            planner_snapshot(cycle, candidate.experiences, {r["id"]: (root / r["path"]).read_text(encoding="utf-8") for r in candidate.experiences},
                             output / "candidate-knowledge.json", root=root)
        else:
            Knowledge(root).freeze(output / "base-knowledge.json")
            candidate_knowledge(root, proposal["candidate_catalog"]).freeze(output / "candidate-knowledge.json")
    # Capture a common Critic snapshot before either Planner library is installed.
    if not (output / "critic-knowledge.json").exists():
        if cycle:
            save(output / "critic-knowledge.json", load(cycle["critic"]["knowledge"]["path"]))
        else:
            Knowledge(root).freeze(output / "critic-knowledge.json")
        package = Path(__file__).parents[1] / "critic_harness"
        save(output / "critic-instructions.json", load(cycle["critic"]["instructions"]["path"]) if cycle else {p.relative_to(package).as_posix(): p.read_text(encoding="utf-8") for p in package.rglob("*.md")})
    frozen = {name: {"path": str(output / name), "sha256": sha(output / name)} for name in
              ("base-knowledge.json", "candidate-knowledge.json", "critic-knowledge.json", "critic-instructions.json")}
    body = {"schema": "lha-rsi-validation-v1", "split_sha256": splits["sha256"], "proposal": str(Path(proposal_path).resolve()),
            "proposal_sha256": proposal["sha256"], "candidate_catalog_sha256": proposal["candidate_catalog_sha256"],
            "base_catalog_sha256": proposal["base_catalog_sha256"], "tasks": tasks, "protocol": protocol, "runtime": runtime_hashes(),
            "protocol_sha256": digest(protocol), "frozen": frozen, "split": split,
            "cycle": {"path": str(Path(cycle_path).resolve()), "sha256": cycle["sha256"]} if cycle else None,
            "replay_gate": {"path": str(Path(replay_gate_path).resolve()), "sha256": sha(replay_gate_path)} if replay_gate_path else None,
            "adoption": {"path": str(Path(adoption_path).resolve()), "sha256": sha(adoption_path)} if adoption_path else None,
            "base_role": "cycle_E0" if split == "T" else "proposal_base",
            "gate": protocol.get("quality_gate", {"success_count_delta_min": -1, "core_mean_delta_min": 0, "primary_improvement": "strict", "unknowns": "incomplete"}),
            "scope": "Exploratory predeclared selection gate; not a statistical non-inferiority claim."}
    return sealed(output / "manifest.json", {**body, "sha256": digest(body)})


def validate_quality_protocol(protocol):
    if protocol["primary_metric"] not in {"selected_utility", "delivered_success"}:
        raise ValueError("Live adoption must measure actual delivered quality, not fewer attempts or candidate-set success")
    gate = protocol.get("quality_gate", {})
    fields = {"minimum_sources", "minimum_primary_gain", "max_core_drop", "max_success_drop", "max_major_damage_increase"}
    if set(gate) != fields or type(gate["minimum_sources"]) is not int or gate["minimum_sources"] < 2:
        raise ValueError("Predeclare source count and all quality protections before validation")
    if any(type(gate[k]) not in {int, float} or not math.isfinite(gate[k]) or gate[k] < 0 for k in fields - {"minimum_sources"}) or gate["minimum_primary_gain"] <= 0:
        raise ValueError("Predeclare a positive meaningful gain and nonnegative regression tolerances")
    if not protocol.get("analysis_plan") or protocol.get("baseline_role") not in {"original", "human_assisted", "previous_auto_version"}:
        raise ValueError("Freeze the analysis plan and honest experience baseline identity")
    replay = protocol.get("replay_gate", {})
    if (type(replay.get("minimum_repetitions")) is not int or not 2 <= replay["minimum_repetitions"] <= 10
            or type(replay.get("minimum_decision_points")) is not int or replay["minimum_decision_points"] < 1
            or type(replay.get("minimum_delta")) not in {int,float} or not math.isfinite(replay["minimum_delta"]) or not 0 < replay["minimum_delta"] <= 1):
        raise ValueError("Freeze repeated-sample, decision-coverage and positive-effect replay thresholds")
    weights = protocol["judge"].get("utility_weights", {})
    from evaluation.registry import SEMANTIC,RATINGS
    allowed=set(SEMANTIC)|{"rating:"+k for k in (*RATINGS,"aesthetic_mean")}
    if not weights or not set(weights)<=allowed or any(type(w) not in {int,float} or not math.isfinite(w) or w<=0 for w in weights.values()) or abs(sum(weights.values())-1)>1e-8:
        raise ValueError("Freeze known, positive, finite utility components summing to one")
    if protocol["primary_metric"] == "selected_utility" and not any(k.startswith("rating:") for k in weights):
        raise ValueError("Delivery utility must include reviewed visual-quality components")


def verify_manifest(path):
    manifest = verify_seal(load(path))
    if manifest.get("cycle"):
        from .rsi_cycle import verify
        if verify(manifest["cycle"]["path"])["sha256"] != manifest["cycle"]["sha256"]:
            raise ValueError("Experiment cycle changed")
    if manifest.get("replay_gate") and sha(manifest["replay_gate"]["path"]) != manifest["replay_gate"]["sha256"]:
        raise ValueError("Behavioral replay gate changed")
    if manifest.get("adoption") and sha(manifest["adoption"]["path"]) != manifest["adoption"]["sha256"]:
        raise ValueError("Test-set adoption binding changed")
    for item in manifest["frozen"].values():
        if sha(item["path"]) != item["sha256"]:
            raise ValueError("Frozen validation material changed")
    if digest(manifest["protocol"]) != manifest["protocol_sha256"]:
        raise ValueError("Validation protocol changed")
    return manifest


def common_selection(state, selector):
    """A benchmark selector, never a controller of Planner's next action."""
    from .ledger import build
    candidates = build(state).get("candidates", {})
    eligible = []
    for identity, record in candidates.items():
        if identity == "source":
            continue
        metrics = [record["scores"][name] for name in selector["order"]]
        values = (int(record["major_damage"] is False),) + tuple(m["lower"] if m["items"] else 1.0 for m in metrics)
        eligible.append((identity, values))
    return max(eligible, key=lambda item: item[1])[0] if eligible else None


def require_resolved_tool(run, protocol):
    """A transport/render failure cannot consume the next paired sample in live arms."""
    path = Path(run) / "state.json"
    if protocol["execution"].get("mode", "live") != "live" or not path.exists():
        return
    state = load(path)
    identity = state.get("pending_tool")
    response = Path(run) / "jobs" / str(identity) / "response.json"
    if identity and response.exists() and load(response).get("status") == "failed":
        raise RuntimeError("Reconcile the failed tool in place before resuming this paired arm; preserve its logical seed")


def run_task(manifest_path, task_id, arm, output, model, *, worker=None, root=ROOT):
    """Run/resume one frozen validation task; worker is the existing signed-job worker."""
    from .runner import PlannerHarness
    manifest = verify_manifest(manifest_path)
    if manifest["runtime"] != runtime_hashes():
        raise ValueError("Runtime changed after validation was frozen; prepare a new manifest")
    if arm not in {"base", "candidate", "singlepass"}:
        raise ValueError("Use base/candidate loops or the singlepass control")
    task = next(t for t in manifest["tasks"] if t["id"] == task_id)
    protocol = manifest["protocol"]
    if getattr(model, "model", None) != protocol["planner"]["model"] or getattr(model, "reasoning_effort", None) != protocol["planner"]["reasoning_effort"]:
        raise ValueError("Planner differs from the frozen validation profile")
    output = Path(output).resolve()
    binding = {"manifest_sha256": manifest["sha256"], "task": task_id, "arm": arm}
    with RunLock(output):
        sealed(output / "validation-binding.json", binding)
        harness = PlannerHarness(output, model, root=root)
        if (output / "state.json").exists():
            require_resolved_tool(output, protocol)
            state = harness.resume()
        else:
            frozen = manifest["frozen"]
            state = harness.start(task["source"], task["request"], mode="loop", target=task["renderer"],
                execution=protocol["execution"], max_generations=1 if arm == "singlepass" else protocol["generation_budget"],
                max_turns=protocol["planner"].get("max_turns", 32),
                rsi={"task_card": task.get("card"), "seed_schedule": protocol["seed_schedule"], "knowledge_snapshot": frozen[("base" if arm in {"base", "singlepass"} else "candidate") + "-knowledge.json"],
                     "frozen_critic": {"knowledge": frozen["critic-knowledge.json"], "instructions": frozen["critic-instructions.json"]}})
        while state["status"] == "waiting_tool" and worker:
            directory = output / "jobs" / state["pending_tool"]
            worker(directory / "request.json", directory / "response.json")
            if not (directory / "response.json").exists():
                break
            require_resolved_tool(output, protocol)
            state = harness.resume()
        if state["status"] == "complete":
            save(output / "common-selection.json", {"video": common_selection(state, protocol["selector"]),
                "planner_selected": state["final"].get("video"), "selector": protocol["selector"], "binding": binding})
    return state


def decision_metrics(candidates, selected):
    """Keep identifiable metrics even when another candidate is incompletely observed."""
    if not candidates or selected not in {r["id"] for r in candidates}:
        raise ValueError("A completed arm needs scored candidates and a selected candidate")
    for row in candidates:
        if row.get("success") is not None and type(row["success"]) is not bool:
            raise ValueError("Invalid independent success judgment")
        for k in ("core", "utility"):
            if row.get(k) is not None and (type(row[k]) not in {int, float} or not math.isfinite(row[k]) or not 0 <= row[k] <= 1):
                raise ValueError("Invalid independent score")
    interval = lambda row, key: [float(row[key]), float(row[key])] if row.get(key) is not None else [0.0, 1.0]
    point = lambda b: b[0] if abs(b[0]-b[1]) < 1e-12 else None
    best, ineffective, curve, curve_bounds = [-1.0, -1.0], [0, 0], [], []
    for i, row in enumerate(candidates):
        lo, hi = interval(row, "utility")
        if i:
            ineffective[0] += int(hi <= best[0])
            ineffective[1] += int(lo <= best[1])
        best = [max(best[0], lo), max(best[1], hi)]
        curve_bounds.append(best[:])
        curve.append(point(best))
    chosen = next(r for r in candidates if r["id"] == selected)
    chosen_utility = interval(chosen, "utility")
    others = [interval(r, "utility") for r in candidates if r["id"] != selected]
    regret = [max(0.0, max((r[0] for r in others), default=0)-chosen_utility[1]),
              max(0.0, max((r[1] for r in others), default=0)-chosen_utility[0])]
    success_any = [int(any(r.get("success") is True for r in candidates)), int(any(r.get("success") is not False for r in candidates))]
    bounds = {"success": interval(chosen, "success"), "core": interval(chosen, "core"), "utility": chosen_utility,
              "selection_regret": regret, "non_improving_generations": ineffective, "success_at_budget": success_any}
    bounds.update(delivered_success=bounds["success"], selected_utility=chosen_utility,
                  candidate_set_success=success_any, major_damage=interval(chosen, "major_damage"))
    return {**{k: point(b) for k, b in bounds.items()}, "bounds": bounds, "best_so_far": curve,
            "best_so_far_bounds": curve_bounds, "generations": len(candidates),
            "scope": "success_at_budget is a legacy alias of candidate_set_success, not delivery. Unknowns yield logical bounds. Non-improvement is retrospective, not causal avoidability."}


def record_arm(manifest_path, run, scored_candidates, output):
    """Join independent scores to actual output hashes and retain all generation costs."""
    manifest = verify_manifest(manifest_path)
    run = Path(run).resolve()
    binding, state = load(run / "validation-binding.json"), load(run / "state.json")
    if binding["manifest_sha256"] != manifest["sha256"] or state["status"] != "complete":
        raise ValueError("Run is incomplete or belongs to another validation")
    task = next(t for t in manifest["tasks"] if t["id"] == binding["task"])
    protocol = manifest["protocol"]
    if state["request"]["source"]["sha256"] != task["source_sha256"] or state["request"]["text"] != task["request"]:
        raise ValueError("Source/request differs from validation")
    if state["generation_requests"] > protocol["generation_budget"]:
        raise ValueError("Generation budget exceeded")
    if state["config"]["execution"].get("mode", "live") != protocol["execution"].get("mode", "live"):
        raise ValueError("Execution mode differs from validation")
    generated = [v for k, v in state["jobs"].items() if v["kind"] == "generate"]
    expected = load(manifest["frozen"][("candidate" if binding["arm"] == "candidate" else "base") + "-knowledge.json"]["path"])
    if load(run / "knowledge-snapshot.json") != expected:
        raise ValueError("Run used a different experience or source library")
    for filename in ("critic-knowledge", "critic-instructions"):
        if load(run / (filename + ("-snapshot.json" if filename == "critic-knowledge" else ".json"))) != load(manifest["frozen"][filename + ".json"]["path"]):
            raise ValueError("Run used a different frozen Critic")
    for i, job in enumerate(generated):
        if job["payload"]["renderer"].get("seed") != protocol["seed_schedule"][i]:
            raise ValueError("Paired attempt seed differs")
        expected_renderer = {**protocol["execution"].get("renderer", {}), "seed": protocol["seed_schedule"][i]}
        if job["payload"]["renderer"] != expected_renderer:
            raise ValueError("Renderer settings differ from validation")
    if state["config"]["execution"].get("critic") != protocol["execution"]["critic"]:
        raise ValueError("Online Critic model/profile changed")
    actual = {k: v for k, v in state["videos"].items() if v.get("job_id")}
    if len(scored_candidates) != len(actual) or {s["id"] for s in scored_candidates} != set(actual):
        raise ValueError("Score every actual candidate once")
    score_rows = []
    for row in scored_candidates:
        video = actual[row["id"]]
        if sha(video["path"]) != video["sha256"] or row["output_sha256"] != video["sha256"]:
            raise ValueError("Independent score/video hash mismatch")
        if row["judge"] != protocol["judge"]:
            raise ValueError("Independent judge profile differs")
        raw = Path(row["raw"])
        if sha(raw) != row["raw_sha256"]:
            raise ValueError("Raw independent judgment changed")
        # Normalized fields are embedded in the raw artifact; no untraced manual overwrite.
        raw_value = load(raw)
        if raw_value.get("output_sha256") != video["sha256"] or raw_value.get("source_sha256") != task["source_sha256"] or raw_value.get("judge") != protocol["judge"]:
            raise ValueError("Raw judgment provenance differs from this candidate/task/judge")
        normalized = raw_value.get("rsi_metrics")
        if normalized != {k: row[k] for k in ("success", "core", "utility", "major_damage") if k in row}:
            raise ValueError("Normalized metrics must be present in the preserved judgment artifact")
        score_rows.append(row)
    # Preserve chronological generation order independently of score-file order.
    order = {k: i for i, k in enumerate(actual)}
    score_rows.sort(key=lambda row: order[row["id"]])
    common = common_selection(state, protocol["selector"])
    selected = common if binding["arm"] in {"direct", "best-of-3"} else state["final"].get("video")
    metrics = decision_metrics(score_rows, selected) if selected else None
    critic_counts = []
    for identity, job in state["jobs"].items():
        if job["kind"] == "critique":
            path = run / "jobs" / identity / "active-critic/state.json"
            critic_counts.append(load(path)["attempts"] if path.exists() else None)
    generation_seconds = [v.get("execution", {}).get("generation_seconds", v.get("execution", {}).get("elapsed_seconds")) for v in actual.values()]
    fresh_seconds = [v.get("execution", {}).get("generation_seconds", v.get("execution", {}).get("elapsed_seconds")) for v in actual.values() if not v.get("reuse_provenance")]
    body = {"schema": "lha-rsi-arm-v1", **binding, "source_sha256": task["source_sha256"], "track": task.get("track", "unspecified"),
            "protocol_sha256": manifest["protocol_sha256"], "run": str(run), "state_sha256": sha(run / "state.json"),
            "candidates": score_rows, "selected": selected, "planner_selected": state["final"].get("video"), "metrics": metrics,
            "planner_selection_metrics": decision_metrics(score_rows, state["final"]["video"]) if state["final"].get("video") in actual else None,
            "common_selected": common, "common_selection_metrics": decision_metrics(score_rows, common) if common else None,
            "first_candidate_metrics": decision_metrics(score_rows[:1], score_rows[0]["id"]) if score_rows else None,
            "cost": {"generation_requests": state["generation_requests"], "successful_outputs": len(actual),
                     "reused_outputs": sum(bool(v.get("reuse_provenance")) for v in actual.values()),
                     "new_generation_requests": state["generation_requests"] - sum(bool(v.get("reuse_provenance")) for v in actual.values()),
                     "controller_steps": state["attempts"], "planner_calls": 0 if binding["arm"] in {"direct", "best-of-3"} else state["attempts"],
                     "critic_jobs": len(critic_counts), "critic_model_calls": sum(critic_counts) if None not in critic_counts else None,
                     "generation_seconds": sum(generation_seconds) if generation_seconds and None not in generation_seconds else None,
                     "new_generation_seconds": sum(fresh_seconds) if None not in fresh_seconds else None,
                     "failed_generation_requests": len(generated) - len(actual),
                     "attempt_seeds": [{"job": j["id"], "logical_attempt": j["payload"].get("logical_attempt", i+1),
                                        "seed": j["payload"]["renderer"].get("seed")} for i, j in enumerate(generated)],
                     "planner_response_attempts": len(list((run / "calls").glob("*/attempts/*/submitted.json"))),
                     "critic_response_attempts": len(list((run / "jobs").glob("*/active-critic/calls/*/attempts/*/submitted.json"))),
                     "unknown_costs": ["Missing wall times/token receipts remain unknown; generation failures are charged as requests."]}}
    return sealed(output, {**body, "sha256": digest(body)})


def validate(manifest_path, receipts, output):
    manifest = verify_manifest(manifest_path)
    if manifest.get("split", "V") != "V":
        raise ValueError("Experience adoption uses validation sources only; use report for development/test arms")
    rows = [verify_seal(load(p)) for p in receipts]
    expected = {(t["id"], arm) for t in manifest["tasks"] for arm in ("base", "candidate")}
    found = [(r["task"], r["arm"]) for r in rows]
    if len(set(found)) != len(found) or any(pair not in expected for pair in found):
        raise ValueError("Duplicate or foreign validation receipt")
    for row in rows:
        if row["manifest_sha256"] != manifest["sha256"] or row["protocol_sha256"] != manifest["protocol_sha256"]:
            raise ValueError("Receipt protocol differs from frozen validation")
        if sha(Path(row["run"]) / "state.json") != row["state_sha256"]:
            raise ValueError("Validation run changed after receipt")
        for score in row["candidates"]:
            if sha(score["raw"]) != score["raw_sha256"]:
                raise ValueError("Validation judgment changed after receipt")
    missing = sorted(expected - set(found))
    unknown = [(r["task"], r["arm"]) for r in rows if r["metrics"] is None]
    paired = []
    index = {(r["task"], r["arm"]): r for r in rows}
    for task in manifest["tasks"]:
        a, b = (index.get((task["id"], arm), {}).get("metrics") for arm in ("base", "candidate"))
        if a is not None and b is not None:
            keys = ("success", "core", "selection_regret", "non_improving_generations", "success_at_budget", "selected_utility", "delivered_success", "major_damage")
            bound = lambda m, k: m.get("bounds", {}).get(k, [m[k], m[k]])
            paired.append({"task": task["id"], "source": task.get("source_group", task["source_sha256"]), "track": task.get("track", "unspecified"),
                           "deltas": {k: b[k] - a[k] if b[k] is not None and a[k] is not None else None for k in keys},
                           "delta_bounds": {k: [bound(b,k)[0]-bound(a,k)[1], bound(b,k)[1]-bound(a,k)[0]] for k in keys}})
    mean = lambda key: sum(r["deltas"][key] for r in paired) / len(paired) if paired and all(r["deltas"][key] is not None for r in paired) else None
    total_bounds = lambda key: [sum(r["delta_bounds"][key][i] for r in paired) for i in (0, 1)]
    primary = manifest["protocol"]["primary_metric"]
    success_b, core_b, primary_b = (total_bounds(k) for k in ("success", "core", primary))
    passed = bool(paired) and success_b[0] >= -1 and core_b[0] >= 0 and (primary_b[0] > 0 if primary == "success_at_budget" else primary_b[1] < 0)
    rejected = bool(paired) and (success_b[1] < -1 or core_b[1] < 0 or (primary_b[1] <= 0 if primary == "success_at_budget" else primary_b[0] >= 0))
    if "quality_gate" in manifest["protocol"]:
        limits = manifest["protocol"]["quality_gate"]
        source_rows = {}
        for pair in paired:
            source_rows.setdefault(pair["source"], []).append(pair)
        def macro_bounds(key):
            return [sum(sum(p["delta_bounds"][key][i] for p in group)/len(group) for group in source_rows.values())/len(source_rows)
                    if source_rows else None for i in (0,1)]
        success_b, core_b, primary_b, damage_b = (macro_bounds(k) for k in ("success", "core", primary, "major_damage"))
        enough = len(source_rows) >= limits["minimum_sources"]
        passed = enough and success_b[0] >= -limits["max_success_drop"] and core_b[0] >= -limits["max_core_drop"] and damage_b[1] <= limits["max_major_damage_increase"] and primary_b[0] >= limits["minimum_primary_gain"]
        rejected = enough and (success_b[1] < -limits["max_success_drop"] or core_b[1] < -limits["max_core_drop"] or damage_b[0] > limits["max_major_damage_increase"] or primary_b[1] < limits["minimum_primary_gain"])
    from evaluation.aggregate import estimate
    panels = []
    for track in sorted({"all"} | {t.get("track", "unspecified") for t in manifest["tasks"]}):
        planned = [t for t in manifest["tasks"] if track == "all" or t.get("track", "unspecified") == track]
        chosen = [p for p in paired if track == "all" or p["track"] == track]
        source_values = {}
        for row in chosen:
            if row["deltas"][primary] is not None:
                source_values.setdefault(row["source"], []).append(row["deltas"][primary])
        panels.append({"track": track, "planned_tasks": len(planned), "complete_pairs": len(chosen),
                       "primary_source_macro": estimate([sum(v)/len(v) for v in source_values.values()]),
                       "aggregation": "equal tasks within source, equal sources; source bootstrap"})
    body = {"schema": "lha-rsi-validation-result-v1", "manifest": str(Path(manifest_path).resolve()), "manifest_sha256": manifest["sha256"],
            "proposal_sha256": manifest["proposal_sha256"], "receipt_paths": [str(Path(p).resolve()) for p in receipts],
            "receipt_hashes": [sha(p) for p in receipts], "status": "incomplete" if missing or unknown else "passed" if passed else "rejected" if rejected else "incomplete",
            "missing": missing, "unknown": unknown, "pairs": paired, "primary_metric": primary, "primary_mean_delta": mean(primary),
            "gate": manifest["gate"], "gate_total_delta_bounds": {"success": success_b, "core": core_b, primary: primary_b},
            "panels": panels, "scope": manifest["scope"]}
    return sealed(output, {**body, "sha256": digest(body)})


def _write_transaction(journal, path, root):
    for write in journal["writes"]:
        target = root / write["path"]
        if not target.resolve().is_relative_to(root / "knowledge/experience"):
            raise ValueError("Publication target escapes experience")
        before = base64.b64decode(write["before"]) if write["before"] is not None else None
        after = base64.b64decode(write["after"]) if write["after"] is not None else None
        current = target.read_bytes() if target.exists() else None
        if current not in (before, after):
            raise ValueError("Publication conflicts with another writer")
        if current != after:
            if after is None:
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(target.suffix + ".rsi-tmp")
                temporary.write_bytes(after)
                temporary.replace(target)
    journal["status"] = "complete"
    save(path, journal)
    return journal


def adopt(proposal_path, validation_path, reviewed_by, *, root=ROOT, monitoring_path=None):
    """Call only after user authorization of this concrete, validated publication."""
    if not reviewed_by.strip():
        raise ValueError("Reviewed publication needs a named reviewer")
    root = Path(root).resolve()
    proposal, result = verify_seal(load(proposal_path)), verify_seal(load(validation_path))
    if result["status"] != "passed" or result["proposal_sha256"] != proposal["sha256"]:
        raise ValueError("Adoption needs a passed validation of this exact proposal")
    manifest = verify_manifest(result["manifest"])
    if manifest["protocol"]["execution"].get("mode", "live") != "live":
        raise ValueError("Replay fixtures cannot authorize experience adoption")
    if manifest["sha256"] != result["manifest_sha256"] or any(sha(p) != h for p, h in zip(result["receipt_paths"], result["receipt_hashes"])):
        raise ValueError("Validation evidence changed")
    # Re-evaluate raw provenance and the frozen gate before publication.
    temporary_check = Path(validation_path).with_name("adoption-recheck.json")
    checked = validate(result["manifest"], result["receipt_paths"], temporary_check)
    if checked["status"] != "passed":
        raise ValueError("Validation no longer passes")
    if "quality_gate" in manifest["protocol"]:
        from .rsi_workflow import verify_monitoring
        verify_monitoring(monitoring_path,result,load(manifest["cycle"]["path"]))
    identity = proposal["sha256"][:20]
    journal_path = root / "knowledge/experience/versions" / (identity + ".json")
    with RunLock(root / "knowledge/experience"):
        marker = root / "knowledge/experience/.rsi-publication.json"
        if marker.exists():
            other = Path(load(marker)["journal"])
            if other != journal_path and load(other)["status"] == "pending":
                raise ValueError("Finish the existing interrupted library transaction first")
        if journal_path.exists():
            journal = load(journal_path)
            if journal["reviewed_by"] != reviewed_by or journal["validation_sha256"] != result["sha256"]:
                raise ValueError("Publication retry must retain the recorded approval")
            return _write_transaction(journal, journal_path, root)
        catalog_path = root / "knowledge/experience/catalog.json"
        if sha(catalog_path) != proposal["base_catalog_sha256"] or any(sha(root / p) != h for p, h in proposal["base_files"].items()):
            raise ValueError("Active experience changed after proposal")
        if sha(proposal["candidate_catalog"]) != proposal["candidate_catalog_sha256"]:
            raise ValueError("Candidate changed")
        raw = load(proposal["candidate_catalog"])
        catalog = copy.deepcopy(raw["entries"])
        writes = []
        for row in catalog:
            source = root / row["path"]
            if sha(source) != row["sha256"]:
                raise ValueError("Candidate text changed")
            target = root / "knowledge/experience" / (row["id"] + ".md")
            writes.append((target, source.read_bytes()))
            row.update(path=target.relative_to(root).as_posix(), validation_sha256=result["sha256"],
                       validation_scope="Experience-version validation; not per-claim causal validation")
            if row["id"] in {c["id"] for c in proposal["changes"]}:
                row["origin"] = "validated_model_revision"
        # Unindexed old documents remain archived evidence, inaccessible through the new catalog.
        writes.append((catalog_path, (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode()))
        encode = lambda b: base64.b64encode(b).decode() if b is not None else None
        journal = {"status": "pending", "proposal_sha256": proposal["sha256"], "validation_sha256": result["sha256"],
                   "monitoring": {"path":str(Path(monitoring_path).resolve()),"sha256":sha(monitoring_path)} if monitoring_path else None,
                   "reviewed_by": reviewed_by, "at": stamp(), "writes": [{"path": p.relative_to(root).as_posix(),
                       "before": encode(p.read_bytes() if p.exists() else None), "after": encode(data)} for p, data in writes]}
        save(journal_path, journal)
        save(root / "knowledge/experience/.rsi-publication.json", {"journal": str(journal_path)})
        return _write_transaction(journal, journal_path, root)


def reject(proposal_path, reason, reviewed_by, *, root=ROOT):
    proposal = verify_seal(load(proposal_path))
    if not reason.strip() or not reviewed_by.strip():
        raise ValueError("Record why the proposal was rejected and by whom")
    body = {"proposal_sha256": proposal["sha256"], "reason": reason, "reviewed_by": reviewed_by, "status": "rejected"}
    return sealed(Path(root) / "knowledge/experience/decisions" / (proposal["sha256"][:20] + "-rejected.json"), body)


def rollback(journal_path, reviewed_by, *, root=ROOT):
    root, journal_path = Path(root).resolve(), Path(journal_path).resolve()
    if not journal_path.is_relative_to(root / "knowledge/experience/versions") or not reviewed_by.strip():
        raise ValueError("Use a recorded publication journal and named reviewer")
    with RunLock(root / "knowledge/experience"):
        original = load(journal_path)
        if original["status"] != "complete":
            raise ValueError("Finish the interrupted publication before rollback")
        path = journal_path.with_name(journal_path.stem + "-rollback.json")
        if path.exists():
            reverse = load(path)
            if reverse["reviewed_by"] != reviewed_by:
                raise ValueError("Rollback retry must retain its reviewer")
        else:
            reverse = {"status": "pending", "rollback_of": str(journal_path), "reviewed_by": reviewed_by,
                       "writes": [{"path": w["path"], "before": w["after"], "after": w["before"]} for w in reversed(original["writes"])]}
            save(path, reverse)
            save(root / "knowledge/experience/.rsi-publication.json", {"journal": str(path)})
        return _write_transaction(reverse, path, root)
