"""Operator recovery primitives, independent of any learning workflow."""
from pathlib import Path

from .common import load, save, sha, stamp
from .lock import RunLock


class UncertainRender(RuntimeError):
    outcome_unknown = True


def recover_tool(run, job_id, action, reason, *, response=None, extra_attempts=1):
    """Reconcile the same signed job without executing a renderer or model."""
    if not reason.strip():
        raise ValueError("Record the operator's recovery reason")
    run = Path(run).resolve()
    with RunLock(run):
        state = load(run / "state.json")
        if state["config"].get("workflow") != "creative_loop_v1":
            raise ValueError("Use the historical recovery procedure for legacy runs")
        clock=state.get('online_clock',{})
        import time
        frozen=bool(clock and (clock.get('frozen_unix') or (clock.get('deadline_unix') is not None and time.time()>=clock['deadline_unix']) or state.get('final')))
        job = state["jobs"][job_id]
        if frozen:
            if action=='retry-review':raise ValueError('The task is settled; no new review submission is allowed')
            if action not in {'receipt','not-executed'}:raise ValueError('Choose original receipt or not-executed evidence')
            evidence=load(response) if action=='receipt' else None
            if evidence is not None:
                if evidence.get('request_sha256')!=job['sha256'] or evidence.get('mode')!=job['mode']:
                    raise ValueError('Late evidence must match the original signed job')
                if evidence.get('status')=='complete' and job['kind']=='generate':
                    media=evidence['payload']['video']
                    if sha(media['path'])!=media['sha256']:raise ValueError('Late media changed')
            record={'action':action,'reason':reason,'job_id':job_id,'request_sha256':job['sha256'],
                    'evidence':evidence,'task_state_sha256':sha(run/'state.json'),'task_result_changed':False}
            from .execution import immutable,signature
            immutable(run/'late-evidence'/(signature(record)+'.json'),record)
            return record
        folder = (run / "jobs" / job_id).resolve()
        if not folder.is_relative_to(run / "jobs") or state.get("pending_tool") not in {None, job_id}:
            raise ValueError("Recover the outstanding job in this run")
        with RunLock(folder / "worker"):
            if (folder / "collected.json").exists():
                raise ValueError("A finalized result cannot be replaced through recovery")
            if (folder / "response.json").exists() and load(folder / "response.json").get("status") == "complete":
                raise ValueError("A completed tool receipt exists; collect it instead of changing it")
            if action == "receipt":
                receipt = load(response)
                if receipt.get("request_sha256") != job["sha256"] or receipt.get("mode") != job["mode"]:
                    raise ValueError("Recovery receipt must match the immutable signed job")
                if receipt.get("status") not in {"complete", "failed"} or receipt.get("outcome_unknown") or receipt.get("failure_kind") == "model_transport":
                    raise ValueError("Supply a definite outcome receipt")
                if receipt["status"] == "complete" and job["kind"] == "generate":
                    media = receipt["payload"]["video"]
                    if sha(media["path"]) != media["sha256"]:
                        raise ValueError("Recovered render artifact hash mismatch")
            elif action == "not-executed":
                if job["kind"] != "generate":
                    raise ValueError("Not-executed confirmation applies to a render job")
                # The explicit command is an operator confirmation, not an inference
                # from a missing output file. The reason and old markers are retained.
            elif action == "retry-review":
                if job["kind"] != "critique":
                    raise ValueError("Choose a Critic transport job")
                from .model_call import reopen_call
                review=folder/'one-shot-critic'
                current=load(review/'state.json') if (review/'state.json').exists() else None
                call=review/'calls'/('review-'+str(current['attempts']+1).zfill(4))/'call' if current is not None else review/'call'
                reopen_call(call,reason,extra_attempts)
            else:
                raise ValueError("Choose receipt, not-executed or retry-review")
            history = folder / "recoveries"
            archive = history / f"{len(list(history.glob('*'))) + 1:04d}"
            archive.mkdir(parents=True)
            files = ["response.json"] + (["render-started.json"] if action == "not-executed" else [])
            retained = {}
            for name in files:
                path = folder / name
                if path.exists():
                    retained[name] = sha(path)
                    path.replace(archive / name)
            record = {"at": stamp(), "action": action, "reason": reason, "job_id": job_id,
                      "request_sha256": job["sha256"], "archived": retained,
                      "confirmation": "Operator verified dispatch did not execute" if action == "not-executed" else None}
            save(archive / "record.json", record)
            if action == "receipt":
                save(folder / "response.json", receipt)
            state.setdefault("unresolved_jobs", {}).pop(job_id, None)
            state.setdefault("recoveries", []).append(record)
            state.update(pending_tool=job_id, status="waiting_tool", updated_at=stamp())
            save(run / "state.json", state)
            return record
