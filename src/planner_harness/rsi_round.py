"""Resumable development proposal and decision-replay round; no automatic publication."""
from pathlib import Path
from .common import load, save, sha
from .ledger import digest
from .lock import RunLock
from .rsi_data import collect, propose, sealed, verify_seal
from .rsi_paired_replay import probe
from .rsi_wiki import replay_feedback


def reviewed_result(original, path):
    if not path or not Path(path).exists():
        return original
    from .rsi_paired_replay import summarize
    review=verify_seal(load(path))
    if review.get("replay_sha256") != original["sha256"]:
        raise ValueError("Replay review belongs to another decision sample")
    check=summarize(original["samples"],[c["target"] for c in original["comparisons"]],labels=review["labels"])
    if check["status"] != review["status"]:
        raise ValueError("Replay review status differs from its bound labels")
    return {**original,**check,"review_path":str(path),"review_sha256":review["sha256"]}


def run_round(config, output, proposer, planner, *, root):
    """An operator freezes the development subset and replay decision IDs once."""
    output = Path(output).resolve()
    with RunLock(output):
        sealed(output / "round-config.json", config)
        status = {"schema": "lha-rsi-round-v1", "config_sha256": digest(config), "status": "collecting"}
        save(output / "status.json", status)
        development = collect(config["runs"], config["splits"], output / "development.json", root=root,
                              independent_records=config.get("independent_records", []),annotations=config.get("annotations", []))
        status.update(status="proposing", development_sha256=development["sha256"])
        save(output / "status.json", status)
        limit = 3
        if config.get("cycle"):
            from .rsi_cycle import verify
            cycle = verify(config["cycle"])
            if cycle["split_sha256"] != verify_seal(load(config["splits"]))["sha256"]:
                raise ValueError("Round sources differ from the frozen cycle")
            limit = cycle["protocol"]["max_changed_cards"]
        available = {r["id"] + "/" + d["id"]: d for r in development["records"] for d in r["decisions"]}
        selected = config["replay_decisions"]
        if not selected or len(set(selected)) != len(selected) or any(k not in available for k in selected):
            raise ValueError("Choose unique decision prefixes from this development collection")
        for identity in selected:
            decision = available[identity]
            if sha(decision["input"]) != decision["input_sha256"]:
                raise ValueError("Collected decision input changed")
        base = Path(root) / "knowledge/experience/catalog.json"
        frozen_base = output / "base-catalog.json"
        sealed(frozen_base, load(base))
        revisions = config.get("max_revisions", 2)
        if type(revisions) is not int or not 1 <= revisions <= 3:
            raise ValueError("Use one to three bounded proposal revisions")
        feedback = [verify_seal(load(p)) for p in config.get("feedback_packets", [])]
        allowed_decisions = set(available)
        if any(s["decision_id"] not in allowed_decisions for f in feedback for s in f.get("samples", [])):
            raise ValueError("Feedback must concern the collected development decisions")
        status["revisions"] = []
        for index in range(revisions):
            directory = Path(config["candidate_directory"])
            if index:
                directory = directory.with_name(directory.name + f"-revision-{index+1}")
            proposal = propose(output / "development.json", directory, proposer, root=root,
                               max_changed_cards=limit, feedback=feedback)
            if sha(base) != proposal["base_catalog_sha256"] or load(base) != load(frozen_base):
                raise ValueError("Experience base changed during the revision series")
            status.update(proposal_sha256=proposal["sha256"], candidate_catalog=proposal["candidate_catalog"])
            if proposal["status"] == "no_change":
                status.update(status="needs_evidence" if proposal.get("evidence_requests") else "no_change",
                              evidence_requests=proposal.get("evidence_requests", []))
                status["revisions"].append({"index": index+1, "proposal": str(directory / "proposal.json"), "status": status["status"]})
                break
            targets = [{"decision_id": key, "metric": change["metric"], "direction": change["direction"],
                        **{k: change[k] for k in ("minimum_delta", "tolerance") if k in change},
                        **({"video": change["expected_video"]} if change.get("expected_video") else {})}
                       for change in proposal["changes"] for key in change["replay_decisions"]]
            if not {t["decision_id"] for t in targets} <= set(selected):
                raise ValueError("Replay all decision points targeted by the proposal")
            replay_dir = output / ("paired-replay" if index == 0 else f"paired-replay-revision-{index+1}")
            status.update(status="replaying", revision=index+1)
            save(output / "status.json", status)
            result = probe({k: available[k]["input"] for k in selected}, frozen_base, proposal["candidate_catalog"],
                           replay_dir, planner, root=root, repetitions=config.get("replay_repetitions", 3),
                           max_turns=config.get("replay_max_turns", 12), targets=targets, cycle_path=config.get("cycle"))
            result=reviewed_result(result,config.get("reviewed_replays",{}).get(str(index+1)))
            status["paired_replay"] = {"path": str(replay_dir / "result.json"), "sha256": result["sha256"], "status": result["status"]}
            status["revisions"].append({"index": index+1, "proposal": str(directory / "proposal.json"), "status": result["status"]})
            if result["status"] == "passed":
                heldout = config.get("heldout_replay")
                if heldout:
                    from .rsi_evidence import verify_holdout
                    verify_holdout(heldout["partition"], development["records"], heldout["inputs"])
                    heldout_dir = output / "heldout-replay"
                    check = probe(heldout["inputs"], frozen_base, proposal["candidate_catalog"], heldout_dir,
                                  planner, root=root, repetitions=heldout["repetitions"], targets=heldout["targets"],
                                  cycle_path=config.get("cycle"), partition=heldout["partition"])
                    check=reviewed_result(check,heldout.get("review"))
                    status["heldout_replay"] = {"path": check.get("review_path",str(heldout_dir / "result.json")), "sha256": check.get("review_sha256",check["sha256"]), "status": check["status"]}
                    status["status"] = "ready_for_validation" if check["status"] == "passed" else "heldout_needs_review"
                else:
                    status["status"] = "development_diagnostic_passed; heldout_replay_required"
                break
            if result["status"] != "no_predicted_shift":
                status["status"] = "needs_replay_review"
                break
            item = replay_feedback(replay_dir / "result.json", proposal, root=root)
            item = {**item, "sha256": digest(item)}
            sealed(output / f"feedback-{index+1}.json", item)
            feedback.append(item)
            status["status"] = "revision_budget_exhausted"
        status["scope"] = "Behavior differences only; predicted behavior requires interpretation and video quality awaits held-out validation."
        save(output / "status.json", status)
        return status
