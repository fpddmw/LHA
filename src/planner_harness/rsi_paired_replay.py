"""Repeated paired decision probes; experience is the only between-arm intervention."""
from pathlib import Path
import math
from .common import load, save, sha
from .ledger import digest
from .rsi_data import sealed, verify_seal
from .rsi_replay import replay, prefix


def probe(inputs, base_catalog, candidate_catalog, output, model, *, root, repetitions=3, max_turns=12, targets=(), labels=(), cycle_path=None, partition=None):
    if type(repetitions) is not int or not 1 <= repetitions <= 10 or not inputs or not targets:
        raise ValueError("Paired replay needs decision inputs, 1-10 repeated samples and declared behavior targets")
    output = Path(output).resolve()
    from .rsi_validation import runtime_hashes
    from .rsi_cycle import verify
    cycle = verify(cycle_path) if cycle_path else None
    partition_value = None
    if partition:
        partition_value = verify_seal(load(partition))
        allowed = {r["id"]: r for r in partition_value["decisions"] if r["role"] == "heldout"}
        if not set(inputs) <= set(allowed) or any(sha(p) != allowed[k]["input_sha256"] for k,p in inputs.items()):
            raise ValueError("Replay inputs differ from the frozen held-out partition")
        if cycle:
            gate = cycle["protocol"]["replay_gate"]
            if repetitions < gate["minimum_repetitions"] or len(inputs) < gate["minimum_decision_points"]:
                raise ValueError("Held-out replay is below the frozen replication/coverage budget")
            targets = [{**t, **({"minimum_delta": t.get("minimum_delta",gate["minimum_delta"])} if t["direction"] != "maintain" else {})} for t in targets]
            if any(t["direction"] != "maintain" and t["minimum_delta"] < gate["minimum_delta"] for t in targets):
                raise ValueError("Held-out target weakens the frozen minimum effect")
            split = verify_seal(load(cycle["splits"]))
            development_sources = {t["source_sha256"] for t in split["tasks"] if t["split"] == "D"}
            if any(allowed[k]["source_sha256"] not in development_sources for k in inputs):
                raise ValueError("Held-out replay uses a reserved D subset; V/T are not replay material")
    if cycle and any(getattr(model, key, None) != cycle["protocol"]["planner"][key] for key in ("model", "reasoning_effort")):
        raise ValueError("Replay Planner differs from the frozen cycle")
    contract = {"inputs": {k: {"path": str(Path(p).resolve()), "sha256": sha(p)} for k, p in inputs.items()},
                "base": {"path": str(base_catalog), "sha256": sha(base_catalog)},
                "candidate": {"path": str(candidate_catalog), "sha256": sha(candidate_catalog)},
                "repetitions": repetitions, "max_turns": max_turns, "targets": list(targets), "runtime": runtime_hashes(), "cycle_sha256": cycle["sha256"] if cycle else None,
                "partition": {"path": str(partition), "sha256": sha(partition)} if partition else None}
    sealed(output / "contract.json", contract)
    rows = []
    for key, path in inputs.items():
        _, _, state, _ = prefix(path, root)
        if partition_value and state["request"]["source"]["sha256"] != allowed[key]["source_sha256"]:
            raise ValueError("Held-out source identity disagrees with the actual prefix")
        if cycle and state.get("criteria_authority") != "independent_frozen":
            raise ValueError("Formal replay requires native independently frozen task criteria; legacy prefixes are diagnostic only")
        ordered = [k for k in state["videos"] if k != "source"]
        for sample in range(repetitions):
            for arm in (["base", "candidate"] if sample % 2 == 0 else ["candidate", "base"]):
                destination = output / digest(key)[:16] / str(sample) / arm
                result = replay(path, base_catalog if arm == "base" else candidate_catalog, destination, model,
                                root=root, max_turns=max_turns, paired=True, environment_snapshot=cycle["initial_planner_knowledge"]["path"] if cycle else None)
                rows.append({"id": key + "/" + str(sample) + "/" + arm, "decision_id": key, "sample": sample,
                             "arm": arm, "decision": result.get("decision"), "status": result["status"],
                             "decision_sha256": digest(result.get("decision")), "earlier_candidates": ordered[:-1],
                             "prefix_sha256": load(destination / "replay-contract.json")["neutral_prefix_sha256"]})
    for key in inputs:
        if len({r["prefix_sha256"] for r in rows if r["decision_id"] == key}) != 1:
            raise ValueError("Paired arms did not receive the same neutral prefix")
    body = summarize(rows, targets, labels=labels)
    body.update(schema="lha-rsi-paired-replay-v1", contract_sha256=digest(contract), samples=rows,
                candidate_catalog_sha256=sha(candidate_catalog), base_catalog_semantic_sha256=digest(load(base_catalog)), runtime=contract["runtime"], cycle_sha256=contract["cycle_sha256"],
                replay_role="heldout" if partition else "development_diagnostic", partition=contract["partition"],
                scope="Conditional behavior probe, not video quality or a statistical efficacy claim. Provider sampling is repeated; no unsupported provider seed control is claimed.")
    return sealed(output / "result.json", {**body, "sha256": digest(body)})


def summarize(rows, targets, *, labels=()):
    lookup = {r["id"]: r for r in rows}
    judged = {}
    for label in labels:
        if label.get("sample_id") not in lookup or not label.get("reviewed_by") or not label.get("reason"):
            raise ValueError("Mechanism labels require sample ID, boolean, reason and reviewer")
        row = lookup[label["sample_id"]]
        if label.get("decision_sha256") != row["decision_sha256"]:
            raise ValueError("Mechanism label refers to a different decision")
        if "new_realization" in label and type(label["new_realization"]) is not bool:
            raise ValueError("Realization labels must be boolean")
        if "decision_value" in label:
            value = label["decision_value"]
            if type(value) not in {int, float} or not 0 <= value <= 1 or not label.get("outcome_evidence"):
                raise ValueError("Decision value needs reviewed outcome evidence and a unit-interval value")
            for ref in label["outcome_evidence"]:
                if sha(ref["path"]) != ref["sha256"]:
                    raise ValueError("Decision-value outcome evidence changed")
        judged[row["id"]] = label
    comparisons = []
    for target in targets:
        minimum = target.get("minimum_delta", 0)
        if target.get("direction") not in {"increase", "decrease", "maintain"} or type(minimum) not in {int, float} or not math.isfinite(minimum) or minimum < 0:
            raise ValueError("Predeclare increase/decrease and a nonnegative minimum delta")
        metric = target["metric"]
        def value(row):
            action = row.get("decision")
            if not action or row["status"] != "decision_recorded":
                return None
            kind, args = action["action"], action.get("arguments", {})
            if metric == "stop_rate":
                return kind == "finish"
            if metric == "source_rate":
                return args.get("input_video") == "source" if kind == "generate" else None
            if metric == "earlier_input_rate":
                return args.get("input_video") in row["earlier_candidates"] if kind == "generate" else None
            if metric == "selected_video_rate":
                if not target.get("video"):
                    raise ValueError("A selection target needs the expected video")
                return args.get("video") == target["video"] if kind == "finish" else None
            if metric == "new_realization_rate":
                return judged.get(row["id"], {}).get("new_realization") if kind == "generate" else None
            if metric == "reviewed_decision_value":
                return judged.get(row["id"], {}).get("decision_value")
            raise ValueError("Unknown replay behavior metric")
        arms = {}
        for arm in ("base", "candidate"):
            values = [value(r) for r in rows if r["decision_id"] == target["decision_id"] and r["arm"] == arm]
            valid = [v for v in values if v is not None]
            selected_rows = [r for r in rows if r["decision_id"] == target["decision_id"] and r["arm"] == arm]
            expected_action = "finish" if metric == "selected_video_rate" else "generate"
            not_applicable = sum(bool(r.get("decision")) and r["decision"]["action"] != expected_action for r in selected_rows) if metric not in {"stop_rate", "reviewed_decision_value"} else 0
            arms[arm] = {"planned": len(values), "valid": len(valid), "not_applicable": not_applicable,
                         "rate": sum(valid)/len(valid) if valid else None}
        delta = arms["candidate"]["rate"] - arms["base"]["rate"] if all(a["rate"] is not None for a in arms.values()) else None
        directional = delta if target["direction"] == "increase" else -delta if delta is not None else None
        complete = all(a["planned"] == a["valid"] + a["not_applicable"] and a["valid"] > 0 for a in arms.values())
        if target["direction"] == "maintain":
            tolerance = target.get("tolerance", 0)
            if type(tolerance) not in {int, float} or not math.isfinite(tolerance) or tolerance < 0:
                raise ValueError("Maintain targets need a nonnegative tolerance")
            passed = delta is not None and abs(delta) <= tolerance
        else:
            passed = directional is not None and directional > minimum
        comparisons.append({"target": target, "arms": arms, "delta": delta,
                            "status": "incomplete" if not complete else "passed" if passed else "no_predicted_shift"})
    status = "passed" if comparisons and all(c["status"] == "passed" for c in comparisons) else "incomplete" if not comparisons or any(c["status"] == "incomplete" for c in comparisons) else "no_predicted_shift"
    return {"status": status, "comparisons": comparisons}


def review(path, labels, output):
    original = verify_seal(load(path))
    targets = [c["target"] for c in original["comparisons"]]
    body = {"schema": "lha-rsi-replay-review-v1", "replay_path": str(Path(path).resolve()), "replay_sha256": original["sha256"], "labels": labels,
            **summarize(original["samples"], targets, labels=labels)}
    return sealed(output, {**body, "sha256": digest(body)})
