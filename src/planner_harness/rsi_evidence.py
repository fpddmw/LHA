"""Immutable cases, restricted evidence queries and reviewable skill-maintenance work."""
from __future__ import annotations
import math
import re
from .ledger import digest, english

FILTERS = {"renderer", "route", "failure_type", "criterion", "declared_card", "source_sha256"}
OUTCOMES = {"independent_success", "target_improved", "prediction_hit", "collateral_regression"}


def cases(records):
    rows = []
    for record in records:
        memory = {a["job"]: a for a in (record.get("task_memory") or {}).get("attempts", [])}
        for attempt in record.get("attempts", []):
            m = memory.get(attempt["job"], {})
            body = {"id": record["id"] + "/" + attempt["job"], "source_sha256": record["source_sha256"],
                    "renderer": record.get("renderer"), "request": record["request"],
                    "state_sha256": record["state_sha256"], "action": attempt,
                    "local_signal": {**m, "repair_observations": [r for r in (record.get("task_memory") or {}).get("repair_observations", []) if r["job"] == attempt["job"]]}, "reads": record.get("knowledge_reads", {}),
                    "decision_prefix": next((d for d in record.get("decisions", []) if attempt["job"] == d["id"] + "-generate"), None),
                    "reads_scope": "Retrospective run-wide index; use decision_prefix for what was available before this action",
                    "scope": "Observed state/action/outcome. Untried branches and unmeasured outcomes remain unknown."}
            rows.append({**body, "sha256": digest(body)})
    return rows


def validate_claim(claim):
    for field in ("id", "claim", "mechanism", "comparison", "limitations"):
        if not claim.get(field):
            raise ValueError("Evidence claim needs " + field)
    query = claim.get("query", {})
    if set(query) - {"where", "outcome", "expected"} or any(k not in FILTERS and not re.fullmatch(r"label\.[a-z][a-z0-9_]{0,63}",k) for k in query.get("where", {})):
        raise ValueError("Use the restricted evidence query, not executable code")
    if query.get("outcome") not in OUTCOMES or type(query.get("expected")) is not bool:
        raise ValueError("An evidence query needs an observable outcome and expected boolean")
    if any(not isinstance(v, (str, list)) or isinstance(v, list) and any(not isinstance(x, str) for x in v) for v in query.get("where", {}).values()):
        raise ValueError("Query filters are exact labels or lists of exact labels")
    english(claim)
    return claim


def attributes(case):
    a, m = case["action"], case["local_signal"]
    intent = a.get("intent") or {}
    types = intent.get("failure_types", intent.get("failure_type", {}))
    return {"renderer": case["renderer"], "route": "source" if a["input"] == "source" else "candidate",
            **{"label."+k:v for k,v in case.get("semantic_labels",{}).items()},
            "criterion": intent.get("targets", []), "declared_card": intent.get("cards", []),
            "failure_type": [t for values in types.values() for t in (values if isinstance(values, list) else [values])],
            "source_sha256": case["source_sha256"]}


def observed(case, query):
    a, m = case["action"], case["local_signal"]
    outcome = query["outcome"]
    if outcome == "independent_success":
        from .rsi_statistics import independent
        value = independent(a).get("success")
        return value if type(value) is bool else {"pass": True, "fail": False}.get(value) if isinstance(value, str) else None
    if outcome == "prediction_hit":
        p = m.get("prediction", {})
        if p.get("basis") != "planner_declared":
            return None
        return {"hit": True, "miss": False, "partial": False}.get(p.get("outcome"))
    if outcome == "collateral_regression":
        if m.get("review_status") != "reviewed" or m.get("baseline_status") != "reviewed":
            return None
        return bool(m.get("collateral_regressions"))
    # A matching targeted repair requires before/after judgments, not a confident intent.
    targets = query.get("where", {}).get("criterion", (a.get("intent") or {}).get("targets", []))
    targets = [targets] if isinstance(targets, str) else targets
    if m.get("baseline_status") != "reviewed" or not targets:
        return None
    repairs = {r["requirement"]:r["result"] for r in m.get("repair_observations", [])}
    values = [repairs.get(t) for t in targets]
    return all(v == "improved" for v in values) if values and all(v in {"improved", "unchanged", "regressed"} for v in values) else None


def evaluate(claim, case_rows):
    validate_claim(claim)
    query, eligible = claim["query"], []
    for case in case_rows:
        if case["sha256"] != digest({k:v for k,v in case.items() if k != "sha256"}):
            raise ValueError("Case facts changed")
        attrs = attributes(case)
        def matches(k, wanted):
            actual = attrs.get(k, []) if isinstance(attrs.get(k, []), list) else [attrs[k]]
            return bool(set(actual) & set(wanted if isinstance(wanted, list) else [wanted]))
        if all(matches(k, v) for k,v in query.get("where", {}).items()):
            eligible.append((case, observed(case, query)))
    support = [c["id"] for c,v in eligible if v is not None and v == query["expected"]]
    counter = [c["id"] for c,v in eligible if v is not None and v != query["expected"]]
    unknown = [c["id"] for c,v in eligible if v is None]
    n = len(support) + len(counter)
    # Descriptive attempt interval; repeated attempts are not independent evidence.
    p = len(support)/n if n else None
    z = 1.96
    interval = None
    if n:
        center = (p + z*z/(2*n))/(1+z*z/n)
        margin = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
        interval = [max(0,center-margin), min(1,center+margin)]
    status = "unmeasured" if not n else "mixed" if support and counter else "counterevidence" if counter else "single" if n == 1 else "observed"
    return {"id": claim["id"], "claim_sha256": digest(claim), "status": status,
            "planned": len(eligible), "known": n, "unknown": len(unknown), "support_count": len(support),
            "support": support, "counterexamples": counter, "unresolved": unknown,
            "sources": len({c["source_sha256"] for c,v in eligible if v is not None}),
            "support_rate": p, "descriptive_attempt_interval": interval,
            "scope": "Observed association, not causal or held-out validation. Attempt interval ignores source clustering; not an adoption gate."}


def refresh(records, catalog, *, previous=None, annotations=()):
    rows = cases(records)
    if annotations:
        rows = apply_annotations(rows, annotations)
    claims = [c for topic in catalog for c in topic.get("claims", [])]
    if len({c["id"] for c in claims}) != len(claims):
        raise ValueError("Evidence claim IDs must be unique")
    results = {c["id"]: evaluate(c, rows) for c in claims}
    skills = [c for topic in catalog for c in topic.get("cards", [])]
    todos = []
    for skill in skills:
        refs = skill.get("evidence_claims", [])
        if not set(refs) <= set(results):
            raise ValueError("Skill refers to an unavailable evidence claim")
        bad = [k for k in refs if results[k]["status"] in {"mixed", "counterevidence"}]
        if bad:
            todos.append({"kind": "review_skill", "skill": skill["id"], "claims": bad,
                          "reason": "New or retained counterevidence; propose scope revision, not automatic retirement"})
    linked = {k for s in skills for k in s.get("evidence_claims", [])}
    for key, value in results.items():
        if key not in linked and value["status"] == "observed":
            todos.append({"kind": "consider_skill", "claim": key, "reason": "Observed support without decision guidance; validation still pending"})
        if previous and previous.get("claims", {}).get(key, {}).get("status") != value["status"]:
            todos.append({"kind": "evidence_status_changed", "claim": key, "previous": previous.get("claims", {}).get(key, {}).get("status"), "current": value["status"]})
    body = {"schema": "lha-case-evidence-skill-v1", "cases": rows, "claims": results, "todos": todos,
            "publication": "none; reviewed version changes only"}
    return {**body, "sha256": digest(body)}


def annotate(case, labels, *, reviewed_by, reason, evidence):
    """Versioned semantic interpretation; original case facts remain immutable."""
    from .common import sha
    if case["sha256"] != digest({k:v for k,v in case.items() if k!="sha256"}):
        raise ValueError("Case facts changed")
    if not reviewed_by or not reason or not evidence or not labels:
        raise ValueError("Semantic labels require review, rationale and cited artifacts")
    if any(not re.fullmatch(r"[a-z][a-z0-9_]{0,63}",k) or not isinstance(v,str) or not v.strip() for k,v in labels.items()):
        raise ValueError("Use named semantic labels with explicit string values")
    if any(sha(r["path"]) != r["sha256"] for r in evidence):
        raise ValueError("Annotation evidence changed")
    english([labels,reason])
    body={"schema":"lha-case-annotation-v1","case_id":case["id"],"case_sha256":case["sha256"],
          "labels":labels,"reviewed_by":reviewed_by,"reason":reason,"evidence":evidence,
          "scope":"Reviewed interpretation, not an automatically observed fact or causal attribution"}
    return {**body,"sha256":digest(body)}


def apply_annotations(rows, annotations):
    from .common import sha
    from .rsi_data import verify_seal
    by_id={r["id"]:r for r in rows}
    interpretations={}
    for annotation in annotations:
        a=verify_seal(annotation)
        original=by_id.get(a["case_id"])
        if not original or original["sha256"] != a["case_sha256"]:
            raise ValueError("Annotation belongs to another case revision")
        if any(sha(r["path"]) != r["sha256"] for r in a["evidence"]):
            raise ValueError("Annotation evidence changed")
        bucket=interpretations.setdefault(a["case_id"],{"labels":{},"refs":[]})
        if any(k in bucket["labels"] and bucket["labels"][k]!=v for k,v in a["labels"].items()):
            raise ValueError("Conflicting interpretations need an explicitly selected annotation revision")
        bucket["labels"].update(a["labels"]);bucket["refs"].append(a["sha256"])
    result=[]
    for row in rows:
        bucket=interpretations.get(row["id"])
        if not bucket:
            result.append(row);continue
        body={**{k:v for k,v in row.items() if k!="sha256"},"original_case_sha256":row["sha256"],
              "semantic_labels":bucket["labels"],"annotation_sha256s":bucket["refs"]}
        result.append({**body,"sha256":digest(body)})
    return result


def freeze_partition(decisions, output):
    from .common import sha
    from .rsi_data import sealed
    roles, seen = {}, set()
    for row in decisions:
        if row["id"] in seen or row["role"] not in {"development", "heldout"}:
            raise ValueError("Unique decision IDs and development/heldout roles are required")
        seen.add(row["id"])
        if row.get("exposed") and row["role"] != "development":
            raise ValueError("Feedback-exposed decisions belong to development")
        for key in (row["source_sha256"], row.get("source_group", row["source_sha256"]), row["trajectory"]):
            if key in roles and roles[key] != row["role"]:
                raise ValueError("Source/trajectory leakage across replay roles")
            roles[key] = row["role"]
        if sha(row["input"]) != row["input_sha256"]:
            raise ValueError("Decision prefix changed")
    body = {"schema": "lha-replay-partition-v1", "decisions": decisions,
            "scope": "Frozen before proposal feedback; later exposure requires a new partition"}
    return sealed(output, {**body, "sha256": digest(body)})


def verify_holdout(partition_path, development, inputs):
    from .common import load, sha
    from .rsi_data import verify_seal
    partition = verify_seal(load(partition_path))
    held = {r["id"]:r for r in partition["decisions"] if r["role"] == "heldout"}
    exposed = {r["source_sha256"] for r in development}
    exposed |= {r.get("source_group", r["source_sha256"]) for r in development}
    if not inputs or not set(inputs) <= set(held):
        raise ValueError("Use frozen held-out replay decisions")
    for key, path in inputs.items():
        if held[key]["source_sha256"] in exposed or held[key].get("source_group", held[key]["source_sha256"]) in exposed or sha(path) != held[key]["input_sha256"]:
            raise ValueError("Held-out replay overlaps proposer evidence or changed prefix")
    return partition


def branch_library(records):
    """Observed concrete branches only; no inferred values for untried actions."""
    from .rsi_statistics import independent
    branches = []
    for record in records:
        for attempt in record.get("attempts", []):
            decision = next((d for d in record.get("decisions", []) if attempt["job"] == d["id"] + "-generate"), None)
            action = {k:attempt.get(k) for k in ("input", "input_sha256", "prompt", "renderer_settings", "seed")}
            branches.append({"case": record["id"] + "/" + attempt["job"],
                "prefix_sha256": decision.get("input_sha256") if decision else None,
                "action": action, "action_sha256": digest(action), "output_sha256": attempt.get("output_sha256"),
                "independent": independent(attempt), "online": attempt.get("evaluations", {}),
                "scope": "One observed concrete branch; not the expected value of a route category"})
    body = {"schema": "lha-observed-branches-v1", "branches": branches, "untried_branches": "unknown"}
    return {**body, "sha256": digest(body)}
