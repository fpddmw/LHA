"""Private training contributions with provenance-bound, idempotent ingestion.

Ingestion appends searchable contributions. Canonical guidance is unchanged;
explicit curation is a separate operation. Campaign code controls online exposure.
"""

import hashlib
from pathlib import Path
from .common import load, save, sha
from .execution import immutable, signature
from .lock import RunLock

VERSION = "lha-private-training-experience-v1"


def validate_snapshot(root, snapshot):
    from .creative_knowledge import CreativeKnowledge

    if snapshot.get("experience_mode") != "full":
        raise ValueError("Training revisions need a full knowledge snapshot")
    for path, row in snapshot.get("documents", {}).items():
        if hashlib.sha256(row["text"].encode()).hexdigest() != row["sha256"]:
            raise ValueError("Snapshot text hash differs")
    knowledge = CreativeKnowledge(root, snapshot, experience_mode="full")
    if not knowledge.curated_catalog.get("entries"):
        raise ValueError("Experience maintenance requires a nonempty pre-existing library")
    return knowledge


def family(state):
    execution = state.get("config", {}).get("execution", {})
    return {
        "review_mode": execution.get("review", {}).get("mode", "critic"),
        "renderer_backend": execution.get("renderer", {}).get("backend", "bernini"),
    }


def validate_owner(owner, *, output=None, review_mode=None, renderer_backend=None):
    if not isinstance(owner, dict) or set(owner) != {
        "id", "batch_root", "review_mode", "renderer_backend", "seed_sha256"
    } or owner["id"] != signature({k: v for k, v in owner.items() if k != "id"}):
        raise ValueError("Experience library has no valid owner; retain legacy runs separately")
    if owner["review_mode"] not in {"critic", "planner"} or owner["renderer_backend"] not in {"bernini", "ditto"}:
        raise ValueError("Unknown experience library family")
    if output is not None and owner["batch_root"] != str(Path(output).resolve()):
        raise ValueError("Experience library belongs to another batch")
    if review_mode is not None and owner["review_mode"] != review_mode:
        raise ValueError("Experience library belongs to another review family")
    if renderer_backend is not None and owner["renderer_backend"] != renderer_backend:
        raise ValueError("Experience library belongs to another renderer")
    return owner


def bound_snapshot(root, library, *, output=None, review_mode=None, renderer_backend=None):
    """Check a retained private revision, including historical maintenance reads."""
    if not library:
        raise ValueError("Post-task maintenance requires a bound full library")
    owner = validate_owner(library.get("owner"), output=output,
                           review_mode=review_mode, renderer_backend=renderer_backend)
    directory = Path(owner["batch_root"]) / "training-experience"
    if load(directory / "library.json") != owner:
        raise ValueError("Experience library owner changed")
    path = Path(library["snapshot"]).resolve()
    if not path.is_relative_to(directory.resolve() / "versions") or sha(path) != library["snapshot_sha256"]:
        raise ValueError("Private experience revision changed or belongs elsewhere")
    return validate_snapshot(root, load(path))


def owned_copy(root, path, owner):
    """A frozen read-only copy must match a real revision of its stated owner."""
    validate_owner(owner)
    value = load(path)
    revision = "base" if sha(path) == owner["seed_sha256"] else signature(value)
    original = Path(owner["batch_root"]) / "training-experience/versions" / revision / "snapshot.json"
    return bound_snapshot(root, {"owner": owner, "snapshot": str(original), "snapshot_sha256": sha(path)})


def initialize(root, output, initial=None, *, review_mode="critic", renderer_backend="bernini"):
    from .creative_knowledge import CreativeKnowledge

    output = Path(output)
    directory = output / "training-experience"
    with RunLock(directory / "owner"):
        marker = directory / "current.json"
        if marker.exists():
            pointer = current(root, output)
            validate_owner(pointer["owner"], output=output, review_mode=review_mode,
                           renderer_backend=renderer_backend)
            if initial and load(initial) != load(directory / "versions/base/snapshot.json"):
                raise ValueError("Private library initial seed differs")
            return pointer
        snapshot = load(initial) if initial else None
        target = directory / "versions/base/snapshot.json"
        if snapshot is None:
            CreativeKnowledge(root, experience_mode="full").freeze(target)
            snapshot = load(target)
        else:
            validate_snapshot(root, snapshot)
            immutable(target, snapshot)
        validate_snapshot(root, snapshot)
        identity = {"batch_root": str(output.resolve()), "review_mode": review_mode,
                    "renderer_backend": renderer_backend, "seed_sha256": sha(target)}
        owner = {**identity, "id": signature(identity)}
        validate_owner(owner)
        immutable(directory / "library.json", owner)
        body = {
            "protocol": VERSION,
            "owner": owner,
            "version": 0,
            "snapshot": str(target.resolve()),
            "snapshot_sha256": sha(target),
            "source": "initial reviewed corpus",
            "training_sources": [],
        }
        save(marker, body)
        return body


def current(root, output):
    pointer = load(Path(output) / "training-experience/current.json")
    path = Path(pointer["snapshot"])
    if pointer.get("protocol") != VERSION or sha(path) != pointer["snapshot_sha256"]:
        raise ValueError("Private training pointer changed")
    bound_snapshot(root, pointer, output=output)
    return pointer


def base_snapshot(root, output):
    directory = Path(output).resolve() / "training-experience"
    owner = load(directory / "library.json")
    revision = {"owner": owner, "version": 0,
                "snapshot": str(directory / "versions/base/snapshot.json"),
                "snapshot_sha256": owner["seed_sha256"]}
    bound_snapshot(root, revision, output=output)
    return revision


def verify_pre_experience(run, library):
    run = Path(run)
    execution = load(run / "state.json")["config"]["execution"]
    digest = (library or {}).get("snapshot_sha256")
    if (execution.get("experience_condition") != "pre-experience"
            or not digest or digest != library["owner"]["seed_sha256"]
            or execution.get("experience_snapshot_sha256") != digest
            or load(run / "knowledge-snapshot.json") != load(library["snapshot"])):
        raise ValueError("Pre-experience maintenance and online reads must share the original seed")


def changeset(root, snapshot, changes, provenance, case=None):
    """Append a contribution layer; existing entries and manuals stay fixed."""
    from .experience_contributions import append
    validate_snapshot(root, snapshot)
    result, changed = append(snapshot, changes, provenance, case)
    if changed:
        result["training_revision"] = {
            "protocol": VERSION, "parent_snapshot_sha256": signature(snapshot),
            "source": provenance, "changed_ids": changed,
            "change_scope": "append_only_contributions",
        }
        validate_snapshot(root, result)
    return result, changed


def activate(root, output, contribution):
    from .maintenance import provenance
    from .json_output import decode_object

    contribution = Path(contribution)
    value = load(contribution)
    job_path = Path(value["job_path"])
    if sha(job_path) != value["job_sha256"]:
        raise ValueError("Training contribution job changed")
    job = load(job_path)
    pre_experience = job["method"] == "pre-experience"
    if (
        job["method"] not in {"none", "full", "pre-experience"}
        or provenance(root, job["run"], job["split"], deferred=pre_experience) != value["provenance"]
        or job["provenance"] != value["provenance"]
    ):
        raise ValueError(
            "Only original training Planner trajectories may activate a private revision"
        )
    call = value["contribution_call"]
    folder = Path(call["path"])
    for key, name in [
        ("input_sha256", "input.json"),
        ("response_sha256", "response.txt"),
        ("returned_sha256", "returned.json"),
    ]:
        if sha(folder / name) != call[key]:
            raise ValueError("Original training contribution call changed")
    if load(folder / "returned.json")["sha256"] != call["response_sha256"]:
        raise ValueError("Training contribution has no original returned answer")
    action = decode_object((folder / "response.txt").read_text())
    if (
        action.get("action") != "contribute"
        or action["arguments"].get("text") != value["text"]
        or action["arguments"].get("changes", []) != value["changes"]
    ):
        raise ValueError("Training revision differs from original Planner contribution")
    directory = Path(output) / "training-experience"
    with RunLock(directory / "owner"):
        before = current(root, output)
        library = job.get("maintenance_snapshot")
        bound_snapshot(root, library, output=output, **family(load(Path(job["run"]) / "state.json")))
        if library["owner"] != before["owner"]:
            raise ValueError("Maintenance contribution belongs to another experience library")
        if pre_experience:
            verify_pre_experience(job["run"], library)
            if job["split"] == "test":
                record = {
                    "status": "deferred" if value["changes"] else "no_increment",
                    "provenance": value["provenance"],
                    "contribution": {"path": str(contribution.resolve()), "sha256": sha(contribution)},
                    "seed_sha256": library["snapshot_sha256"],
                }
                immutable(directory / "deferred" / (job["id"] + ".json"), record)
                return record
        receipt = directory / "activations" / (job["id"] + ".json")
        journal = directory / "journals" / (job["id"] + ".json")
        if receipt.exists():
            return load(receipt)
        if journal.exists():
            record = load(journal)
            after = record["after"]
            if sha(after["snapshot"]) != after["snapshot_sha256"]:
                raise ValueError("Training activation journal snapshot changed")
            if before == record["before"]:
                save(directory / "current.json", after)
            elif before != after:
                raise ValueError("Training activation journal conflicts with current revision")
            immutable(receipt, record)
            return record
        # Legacy maintenance reads the current revision. Pre-experience
        # maintenance reads the seed while activation appends to the revision.
        if not pre_experience and library["snapshot_sha256"] != before["snapshot_sha256"]:
            raise ValueError("Maintenance library is no longer the current training revision")
        observed = load(before["snapshot"])
        online = load(Path(job["run"]) / "knowledge-snapshot.json")
        if job["method"] == "none" and online.get("experience_mode") != "none":
            raise ValueError("No-knowledge training task saw full experience online")
        case = {
            "request": load(Path(job["run"]) / "state.json")["request"],
            "settlement": job["settlement"], "run": job["run"],
            "run_state_sha256": job["run_state_sha256"],
            "online_knowledge_sha256": job["knowledge_snapshot_sha256"],
            "online_experience_mode": job["experience_mode"],
            "experience_owner": before["owner"],
            "contribution": {"path": str(contribution), "sha256": sha(contribution)},
            "contributor_account": value["text"],
            "source_index": value.get("source_index", {}),
            "event_refs": value.get("event_refs", []),
            "videos": load(Path(job["run"]) / "state.json").get("videos", {}),
            "events": load(Path(job["run"]) / "state.json").get("events", []),
            "maintenance_observations": value.get("observations", []),
        }
        changes = value["changes"]
        if pre_experience:
            from .experience_contributions import append
            append(load(library["snapshot"]), changes, value["provenance"])
            occupied = {row["id"] for row in observed.get("experience_contributions", {}).get("items", [])}
            # Independent tasks can propose the same new ID without seeing one another.
            changes = [
                {**change, "id": change["id"] + "-" + job["id"][:16]}
                if change["op"] == "create" and change["id"] in occupied else change
                for change in changes
            ]
        snapshot, changed = changeset(root, observed, changes, value["provenance"], case)
        after = before
        if changed:
            snapshot["training_revision"]["owner"] = before["owner"]
            identity = signature(snapshot)
            target = directory / "versions" / identity / "snapshot.json"
            immutable(target, snapshot)
            after = {
                "protocol": VERSION,
                "owner": before["owner"],
                "version": before["version"] + 1,
                "snapshot": str(target.resolve()),
                "snapshot_sha256": sha(target),
                "source": "task contributions; canonical entries unchanged",
                "training_sources": [*before["training_sources"], value["provenance"]],
                "contribution": {"path": str(contribution), "sha256": sha(contribution)},
            }
        record = {
            "status": "activated" if changed else "no_increment",
            "before": before,
            "after": after,
            "changed_ids": changed,
            "shared_corpus_changed": False,
            "canonical_entries_changed": False,
            "contribution_layer_changed": bool(changed),
            "change_scope": "append_only_contributions",
        }
        immutable(journal, record)
        if changed:
            save(directory / "current.json", after)
        immutable(receipt, record)
        return record


def maintain(root, output, run, job_id, config=None, *, model_factory=None):
    from .maintenance import configuration, _execute

    cfg = configuration(
        {**(config or {}), "enabled": True, "automatic_phase": "after_each_training_task"}
    )
    output = Path(output)
    folder = output / "maintenance/jobs" / job_id
    job = load(folder / "job.json")
    if Path(job["run"]).resolve() != Path(run).resolve():
        raise ValueError("Maintenance job belongs to another task")
    bound_snapshot(root,job.get("maintenance_snapshot"),output=output,**family(load(Path(run)/"state.json")))
    result_path = folder / "training-maintenance.json"
    if result_path.exists():
        return load(result_path)
    job["original_job_path"] = str(folder / "job.json")
    job["original_job_sha256"] = sha(folder / "job.json")
    if model_factory is None:
        from vlm.openrouter import OpenRouterVisionModel
        from vlm.settings import role_settings

        settings = role_settings({}, "post_task_planner")
        model_factory = lambda: OpenRouterVisionModel(role="post_task_planner", **settings)
    before = current(root, output)
    result = None
    for number in range(1, cfg["attempts"] + 1):
        attempt = folder / ("training-attempt-" + str(number))
        try:
            contribution = _execute(root, attempt, job, cfg, model_factory())
            result = activate(root, output, attempt / "contribution.json")
            break
        except Exception as exc:
            result = {
                "status": "execution_unknown"
                if getattr(exc, "outcome_unknown", False)
                else "failed",
                "error_type": type(exc).__name__,
                "reason": str(exc),
                "retained_version": before,
                "shared_corpus_changed": False,
            }
            save(attempt / "failure.json", result)
            if getattr(exc, "outcome_unknown", False):
                break
    save(result_path, result)
    save(
        folder / "status.json",
        {
            "status": "complete"
            if result["status"] in {"activated", "no_increment", "deferred"}
            else result["status"],
            "attempts": number,
        },
    )
    return result


def curate_library(root, output, decisions, *, authorization, expected_snapshot_sha256):
    """Explicit operator/curator entry point; never exposed to a task model."""
    from .experience_contributions import curate
    directory = Path(output) / 'training-experience'
    with RunLock(directory / 'owner'):
        before = current(root, output)
        key = signature({'parent': expected_snapshot_sha256, 'decisions': decisions,
                         'authorization': authorization})
        receipt = directory / 'curations' / (key + '.json')
        if receipt.exists():
            record = load(receipt)
            if sha(record['after']['snapshot']) != record['after']['snapshot_sha256']:
                raise ValueError('Curation recovery snapshot changed')
            if before == record['before']:
                save(directory / 'current.json', record['after'])
            # Later versions legitimately retain this earlier curation receipt.
            elif before != record['after'] and before['version'] <= record['after']['version']:
                raise ValueError('Curation recovery conflicts with the private pointer')
            return record
        if before['snapshot_sha256'] != expected_snapshot_sha256:
            raise ValueError('Private library advanced; review against its current snapshot')
        revised = curate(load(before['snapshot']), decisions, authorization=authorization)
        revised['training_revision'] = {**revised.get('training_revision', {}),
            'protocol':VERSION,'owner':before['owner'],'change_scope':'explicit_curation',
            'parent_snapshot_sha256':before['snapshot_sha256']}
        validate_snapshot(root, revised)
        target = directory / 'versions' / signature(revised) / 'snapshot.json'
        immutable(target, revised)
        after = {**before, 'version': before['version'] + 1,
                 'snapshot': str(target.resolve()), 'snapshot_sha256': sha(target),
                 'source': 'explicit library curation', 'curation_authorization': authorization}
        record = {'status': 'curated', 'before': before, 'after': after,
                  'decisions': decisions, 'authorization': authorization,
                  'shared_corpus_changed': False}
        # The receipt is also the recovery journal for the atomic pointer update.
        immutable(receipt, record)
        save(directory / 'current.json', after)
        return record
