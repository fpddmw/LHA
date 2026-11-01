"""One immutable measurement environment across all experience versions in a cycle."""
from pathlib import Path
import copy

from .common import load, sha
from .ledger import digest
from .rsi_data import sealed, verify_seal


def freeze(splits_path, protocol, output, *, root):
    from .knowledge import Knowledge
    from .rsi_validation import runtime_hashes
    root, output = Path(root).resolve(), Path(output).resolve()
    splits = verify_seal(load(splits_path))
    for name in ("execution", "planner", "judge", "seed_schedule", "generation_budget"):
        if name not in protocol:
            raise ValueError("Cycle is missing frozen field: " + name)
    protocol = copy.deepcopy(protocol)
    if protocol["execution"].get("mode", "live") == "live":
        from .rsi_validation import validate_quality_protocol
        from .task_criteria import validate
        validate_quality_protocol(protocol)
        for task in splits["tasks"]:
            card = validate(load(task["card"]))
            if card["source_sha256"] != task["source_sha256"] or card["requirement"] != task["request"]:
                raise ValueError("Freeze matching independent task criteria for all cycle tasks")
        protocol["task_card_hashes"] = {t["id"]: sha(t["card"]) for t in splits["tasks"]}
    critic = protocol["execution"].get("critic")
    if not critic:
        raise ValueError("A cycle requires a frozen online Critic")
    critic.setdefault("model", "gpt-6.1-sol")
    critic.setdefault("reasoning_effort", "xhigh")
    critic.setdefault("max_turns", 12)
    protocol.setdefault("max_changed_cards", 3)
    if type(protocol["max_changed_cards"]) is not int or not 1 <= protocol["max_changed_cards"] <= 3:
        raise ValueError("The initial cycle supports at most three changed cards per proposal")
    if (output / "cycle.json").exists():
        current = verify(output / "cycle.json")
        if current["protocol"] != protocol or current["split_sha256"] != splits["sha256"]:
            raise ValueError("Cycle changed; create a new cycle directory")
        return current
    k = Knowledge(root)
    if protocol.get("baseline_role") == "original" and any(
            str(r.get("origin", "")).startswith(("human_assisted", "model_proposed", "validated_model"))
            for r in k.experiences):
        raise ValueError("The active library includes assisted or learned material; label it honestly or use the preserved original snapshot in an isolated experiment")
    k.freeze(output / "initial-planner-knowledge.json")
    # Outcome judgment has no reason to consume evolving action-selection experience.
    k.freeze(output / "critic-knowledge.json")
    snapshot = load(output / "critic-knowledge.json")
    experience_paths = {r["path"] for r in snapshot.get("experiences", [])}
    experience_ids = {r["id"] for r in snapshot.get("experiences", [])}
    snapshot["experiences"] = []
    snapshot["entrances"] = {k: v for k, v in snapshot.get("entrances", {}).items() if k not in experience_ids}
    snapshot["documents"] = {p: d for p, d in snapshot.get("documents", {}).items() if p not in experience_paths}
    snapshot["asset_hashes"] = {p: h for p, h in snapshot.get("asset_hashes", {}).items() if p not in experience_paths}
    from .common import save
    save(output / "critic-knowledge.json", snapshot)
    package = Path(__file__).parents[1] / "critic_harness"
    sealed(output / "critic-instructions.json", {p.relative_to(package).as_posix(): p.read_text(encoding="utf-8") for p in package.rglob("*.md")})
    frozen = {key: {"path": str(output / filename), "sha256": sha(output / filename)}
              for key, filename in (("knowledge", "critic-knowledge.json"), ("instructions", "critic-instructions.json"))}
    body = {"schema": "lha-rsi-cycle-v1", "split_sha256": splits["sha256"], "splits": str(Path(splits_path).resolve()),
            "protocol": protocol, "runtime": runtime_hashes(), "critic": frozen,
            "initial_planner_knowledge": {"path": str(output / "initial-planner-knowledge.json"), "sha256": sha(output / "initial-planner-knowledge.json")},
            "scope": "Only Planner experience changes within this cycle. Knowledge excludes decision experience. Code/config changes start a new cycle."}
    return sealed(output / "cycle.json", {**body, "sha256": digest(body)})


def verify(path, *, check_runtime=True):
    from .rsi_validation import runtime_hashes
    value = verify_seal(load(path))
    if value.get("schema") != "lha-rsi-cycle-v1":
        raise ValueError("Expected a frozen experiment cycle")
    if verify_seal(load(value["splits"]))["sha256"] != value["split_sha256"]:
        raise ValueError("Cycle source split changed")
    for task in load(value["splits"])["tasks"]:
        expected = value["protocol"].get("task_card_hashes", {}).get(task["id"])
        if expected and sha(task["card"]) != expected:
            raise ValueError("Cycle task criteria changed")
    for item in [*value["critic"].values(), value["initial_planner_knowledge"]]:
        if sha(item["path"]) != item["sha256"]:
            raise ValueError("Cycle Critic material changed")
    if check_runtime and value["runtime"] != runtime_hashes():
        raise ValueError("Cycle code changed; start a new cycle")
    return value


def planner_snapshot(cycle, catalog, documents, output, *, root):
    """Pin all non-experience material to cycle E0; replace only experience text/metadata."""
    import hashlib
    from .knowledge import Knowledge
    initial = load(cycle["initial_planner_knowledge"]["path"])
    old_paths = {r["path"] for r in initial["experiences"]}
    old_ids = {r["id"] for r in initial["experiences"]}
    initial["documents"] = {p: d for p, d in initial["documents"].items() if p not in old_paths}
    initial["entrances"] = {k:v for k,v in initial.get("entrances", {}).items() if k not in old_ids or k in {r["id"] for r in catalog}}
    initial["experiences"] = catalog
    for row in catalog:
        text = documents[row["id"]]
        initial["documents"][row["path"]] = {"text": text, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    Knowledge(root, initial).freeze(output)
