"""Inspect actual cycle artifacts and expose the next authorized transition."""
from pathlib import Path
from .common import load, save, sha
from .ledger import digest
from .rsi_data import verify_seal, sealed


def progress(config, output):
    """No model dispatch or publication. The existing queue/round tools perform work."""
    directory = Path(output)
    sealed(directory / "workflow-config.json", config)
    records, state, next_action = {}, "awaiting_development", "collect"
    sequence = [("development", "propose"), ("proposal", "paired-replay"),
                ("heldout_replay", "prepare-validation"), ("validation", "cycle-monitor"), ("monitoring", "review-adoption"),
                ("adoption", "next-development-batch"), ("next_development", "health-and-canary")]
    for key, action in sequence:
        path = config.get(key)
        if not path or not Path(path).exists():
            break
        value = load(path)
        if key != "adoption":
            verify_seal(value)
        records[key] = {"path": str(Path(path).resolve()), "sha256": sha(path)}
        status = value.get("status")
        if key == "proposal" and status == "no_change":
            state, next_action = "needs_evidence" if value.get("evidence_requests") else "no_change", "review-evidence-request"
            break
        original_replay = verify_seal(load(value["replay_path"])) if key == "heldout_replay" and value.get("schema") == "lha-rsi-replay-review-v1" else value
        if key == "heldout_replay" and (status != "passed" or original_replay.get("replay_role") != "heldout"):
            state, next_action = "replay_needs_review", "review-replay"
            break
        if key == "validation":
            if status != "passed":
                state, next_action = "validation_" + str(status), "review-reject-or-gather-evidence"
                break
            if value.get("proposal_sha256") != load(config["proposal"])["sha256"]:
                raise ValueError("Validation belongs to another proposal")
        if key == "monitoring" and status != "passed":
            state,next_action="monitoring_needs_review","review-monitoring-evidence"
            break
        if key == "adoption":
            if status != "complete" or not value.get("reviewed_by") or value.get("proposal_sha256") != load(config["proposal"])["sha256"]:
                raise ValueError("Use the actual reviewed adoption receipt")
        state, next_action = key + "_recorded", action
    if "next_development" in records:
        import base64, json
        adoption = load(config["adoption"])
        catalog_write = next((w for w in adoption["writes"] if w["path"] == "knowledge/experience/catalog.json"), None)
        if not catalog_write:
            raise ValueError("Adoption lacks its actual published catalog")
        catalog = json.loads(base64.b64decode(catalog_write["after"]))
        expected = {r["id"]:r["sha256"] for r in catalog}
        new_records = load(config["next_development"])["records"]
        if not new_records or any({r["id"]:r["sha256"] for r in run.get("experience_documents", [])} != expected for run in new_records):
            raise ValueError("Next development evidence did not use the adopted experience version")
        state = "next_version_observed; efficacy_requires_paired_outcomes"
    body = {"schema": "lha-rsi-workflow-v1", "status": state, "next_action": next_action,
            "artifacts": records, "config_sha256": digest(config),
            "scope": "Artifact progress only; reviewed adoption and real quality improvement are separate claims"}
    save(directory / "status.json", {**body, "sha256": digest(body)})
    return body


def run(config, output, proposer, planner, *, root):
    """Reuse the round and batch engines, stopping before any experience publication."""
    from types import SimpleNamespace
    from .rsi_cycle import verify
    from .rsi_round import run_round
    from .rsi_validation import prepare, validate
    from .rsi_cli_ops import batch_command
    from .rsi_calibration import verify_calibration
    from .lock import RunLock
    output = Path(output).resolve()
    with RunLock(output):
        sealed(output / "cycle-run-config.json", config)
        cycle = verify(config["cycle"])
        protocol = cycle["protocol"]
        verify_calibration(protocol["judge"])
        if not config["round"].get("heldout_replay"):
            raise ValueError("A real cycle requires a reserved held-out replay configuration")
        round_config = {**config["round"], "cycle": config["cycle"], "splits": cycle["splits"]}
        result = run_round(round_config, output / "round", proposer, planner, root=root)
        if result["status"] != "ready_for_validation":
            return result
        proposal = result["revisions"][-1]["proposal"]
        destination = output / "validation"
        manifest = prepare(cycle["splits"], proposal, destination, protocol, root=root,
                           cycle_path=config["cycle"], replay_gate_path=result["heldout_replay"]["path"])
        batch_dir = output / "batch"
        binding = batch_dir / "batch-binding.json"
        if not binding.exists():
            batch_command(SimpleNamespace(command="batch-init", manifest=str(destination/"manifest.json"),
                          service_config=config["service_config"], directory=str(batch_dir),
                          arms=["base", "candidate"], no_score=False), root)
        status = batch_command(SimpleNamespace(command="batch-run",directory=str(batch_dir),once=config.get("once",False)),root)
        paths = sorted((batch_dir/"receipts").glob("*/*.json"))
        expected = len(manifest["tasks"])*2
        if len(paths) != expected:
            return {"status":"validation_running_or_quarantined", "batch":status,
                    "complete_receipts":len(paths),"expected_receipts":expected}
        result = validate(destination/"manifest.json",paths,output/"validation-result.json")
        monitor_config = repeat_anchors(config,cycle,output,root=root)
        checks = monitor(monitor_config, config["cycle"], output/"validation-result.json",
                         [load(p)["run"] for p in paths], output/"monitoring")
        body = {"status":"awaiting_adoption_review" if result["status"]=="passed" and checks["status"]=="passed" else "awaiting_result_review",
                "proposal":proposal,"validation":str(output/"validation-result.json"),
                "validation_status":result["status"],"monitoring":str(output/"monitoring/result.json"),
                "monitoring_status":checks["status"],
                "publication":"none; explicit reviewed adopt/reject command required"}
        save(output/"cycle-result.json",body)
        return body


def repeat_anchors(config, cycle, output, *, root):
    """Execute only explicitly configured anchor jobs; each has its existing durable recovery."""
    import copy
    monitoring=copy.deepcopy(config.get("monitoring",{}))
    jobs=config.get("anchor_jobs",[])
    if len({j["kind"] for j in jobs}) != len(jobs) or any(j["kind"] not in {"critic_drift","judge_drift"} for j in jobs):
        raise ValueError("Configure at most one frozen anchor set for each judge")
    for job in jobs:
        destination=Path(output)/"anchors"/job["kind"]
        if job["kind"] == "critic_drift":
            from .rsi_anchors import run
            run(job["request"],config["cycle"],destination,root=root)
            current=destination/"anchor.json"
        else:
            from .rsi_calibration import run,profile_key
            from evaluation.backends import OpenAICompatibleJudge
            profile=verify_seal(load(job["manifest"]))["profile"]
            if profile_key(profile) != profile_key(cycle["protocol"]["judge"]):
                raise ValueError("Repeated anchor manifest uses another independent judge")
            client=OpenAICompatibleJudge(model=profile["model"],reasoning_effort=profile.get("reasoning_effort"))
            run(job["manifest"],destination,client,root=root)
            current=destination/"comparison.json"
        monitoring[job["kind"]]={"reference":job["reference"],"current":str(current)}
    return monitoring


def monitor(config, cycle_path, validation_path, runs, output):
    """Join existing health/anchor/canary checks. No model dispatch or publication."""
    from .rsi_cycle import verify
    from .rsi_reporting import health, drift, canary
    from .rsi_anchors import compare
    from .rsi_calibration import profile_key
    cycle = verify(cycle_path)
    result = verify_seal(load(validation_path))
    manifest = verify_seal(load(result["manifest"]))
    if (manifest.get("cycle") or {}).get("sha256") != cycle["sha256"]:
        raise ValueError("Monitoring and validation must belong to the same cycle")
    output = Path(output)
    sealed(output/"config.json", config)
    limits, checks, inputs = cycle["protocol"].get("monitoring", {}), {}, []
    def bind(path):
        inputs.append({"path":str(Path(path).resolve()),"sha256":sha(path)})
        return path
    bind(cycle_path); bind(validation_path)
    for run in runs: bind(Path(run)/"state.json")
    for key in ("health", "critic_drift", "judge_drift", "canary"):
        if key not in limits:
            checks[key] = {"status":"not_configured"}
            continue
        destination = output/(key+".json")
        if key == "health":
            check = health(runs,destination,thresholds=limits[key])
        elif key == "canary" and cycle["protocol"].get("baseline_role") in {"original","human_assisted"}:
            check = {"status":"bootstrap_not_applicable", "reason":"No automatically adopted predecessor; next-version development must supply the previous-version canary."}
        elif key not in config:
            checks[key] = {"status":"awaiting_observation"}
            continue
        elif any(not Path(config[key][k]).exists() for k in (("report",) if key=="canary" else ("reference","current"))):
            checks[key] = {"status":"awaiting_observation"}
            continue
        elif key == "canary":
            report = verify_seal(load(bind(config[key]["report"])))
            if report.get("cycle_sha256") != cycle["sha256"]:
                raise ValueError("Canary report belongs to another cycle")
            check = canary(config[key]["report"],destination,**limits[key])
        else:
            reference, current = (bind(config[key][k]) for k in ("reference","current"))
            old,new = verify_seal(load(reference)),verify_seal(load(current))
            if key == "critic_drift":
                if old["cycle_sha256"] != cycle["sha256"] or new["cycle_sha256"] != cycle["sha256"]:
                    raise ValueError("Critic anchors belong to another cycle")
                for row in (old,new): bind(row["feedback"]["path"])
                check = compare(reference,current,destination,**limits[key])
            else:
                if old["profile_sha256"] != profile_key(cycle["protocol"]["judge"]) or new["profile_sha256"] != old["profile_sha256"]:
                    raise ValueError("Independent anchors use another judge profile")
                for row in [*old["rows"],*new["rows"]]: bind(row["score"]["raw"])
                check = drift(reference,current,destination,**limits[key])
        checks[key] = {"status":check["status"],"result":check}
    good = {"observed","within_declared_tolerance","no_threshold_regression","bootstrap_not_applicable"}
    body={"schema":"lha-rsi-cycle-monitoring-v1","cycle_sha256":cycle["sha256"],
          "validation_sha256":result["sha256"],"status":"passed" if all(c["status"] in good for c in checks.values()) else "needs_review",
          "checks":checks,"inputs":inputs,"publication":"none"}
    result={**body,"sha256":digest(body)}
    sealed(output/"history"/(result["sha256"]+".json"),result)
    save(output/"result.json",result)
    return result


def verify_monitoring(path, validation, cycle):
    if not path:
        raise ValueError("Live adoption requires the completed cycle-monitoring receipt")
    result=verify_seal(load(path))
    if result["status"] != "passed" or result["validation_sha256"] != validation["sha256"] or result["cycle_sha256"] != cycle["sha256"]:
        raise ValueError("Monitoring is incomplete, failed or belongs to another validation")
    if any(sha(r["path"]) != r["sha256"] for r in result["inputs"]):
        raise ValueError("Monitored evidence changed")
    return result
