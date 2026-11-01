"""Repeat frozen online Critic anchors and compare requirement-level stability."""
from pathlib import Path
from .common import load, sha
from .execution import signature
from .ledger import digest, VALUES
from .lock import RunLock
from .rsi_data import sealed, verify_seal


def run(request, cycle_path, output, *, root, model=None):
    from .rsi_cycle import verify
    from critic_harness.adapter import critique
    cycle, job = verify(cycle_path), load(request)
    if job.get("kind") != "critique" or signature({k:v for k,v in job.items() if k != "sha256"}) != job["sha256"]:
        raise ValueError("Use an existing signed Critic request as the frozen anchor")
    p = job["payload"]
    if p["critic"] != cycle["protocol"]["execution"]["critic"] or not p.get("requirements"):
        raise ValueError("Anchor Critic/requirements differ from the cycle")
    material = p["frozen_critic"]
    for key in ("knowledge", "instructions"):
        if sha(material[key]) != cycle["critic"][key]["sha256"]:
            raise ValueError("Anchor uses different Critic materials")
    output = Path(output).resolve()
    if output == Path(request).resolve().parent:
        raise ValueError("Use a new anchor directory; preserve original review evidence")
    with RunLock(output):
        sealed(output / "binding.json", {"request_sha256": job["sha256"], "cycle_sha256": cycle["sha256"]})
        feedback = critique(job, output, root, model=model)
        path = output / "active-critic/feedback.json"
        body = {"schema":"lha-rsi-critic-anchor-v1", "cycle_sha256":cycle["sha256"], "request_sha256":job["sha256"],
                "feedback":{"path":str(path),"sha256":sha(path)}, "outcome":feedback["outcome"],
                "scope":"Repeated measurement on the identical task, evidence and requirement version; no rendering."}
        return sealed(output / "anchor.json", {**body,"sha256":digest(body)})


def compare(reference, current, output, *, maximum_changed_fraction):
    if type(maximum_changed_fraction) not in {int,float} or not 0 <= maximum_changed_fraction <= 1:
        raise ValueError("Freeze a changed-verdict fraction between zero and one")
    a,b=verify_seal(load(reference)),verify_seal(load(current))
    if any(a[k] != b[k] for k in ("cycle_sha256","request_sha256")):
        raise ValueError("Compare the same frozen Critic anchor")
    for row in (a,b):
        if sha(row["feedback"]["path"]) != row["feedback"]["sha256"]:
            raise ValueError("Anchor feedback changed")
    if a["outcome"]["requirements_sha256"] != b["outcome"]["requirements_sha256"]:
        raise ValueError("Anchor requirement version changed")
    old={r["id"]:r["verdict"] for r in a["outcome"]["requirement_verdicts"]}
    new={r["id"]:r["verdict"] for r in b["outcome"]["requirement_verdicts"]}
    if old.keys() != new.keys():
        raise ValueError("Anchor requirement coverage changed")
    rows=[{"id":k,"reference":old[k],"current":new[k],"changed":old[k]!=new[k],
           "known_pair":old[k] in VALUES and VALUES[old[k]] is not None and new[k] in VALUES and VALUES[new[k]] is not None} for k in old]
    fraction=sum(r["changed"] for r in rows)/len(rows) if rows else None
    body={"schema":"lha-rsi-critic-drift-v1","reference_sha256":a["sha256"],"current_sha256":b["sha256"],"rows":rows,
          "changed_fraction":fraction,"maximum_changed_fraction":maximum_changed_fraction,
          "unknown_pairs":sum(not r["known_pair"] for r in rows),"status":"insufficient_evidence" if not rows else "needs_review" if fraction>maximum_changed_fraction else "within_declared_tolerance",
          "scope":"Stability signal including unknown transitions, not judge correctness. No automatic protocol change."}
    return sealed(output,{**body,"sha256":digest(body)})
