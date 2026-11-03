"""Append-only experience contributions and explicit, version-bound curation.

Task contributors add knowledge; only an explicitly invoked curator can revise a
canonical entry. Neither interface edits manuals, Skills or experiment policy.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

from .execution import signature

VERSION = "experience-contributions-v1"
PREFIX = "knowledge/experience/contributions/"
OPS = {"create", "comment", "clarify", "recommend", "propose_revision"}
PLACEMENT_FIELDS = ("layer", "tracks", "families", "stages")


def placement(update, inherited=None):
    """Keep discovery placement with the account; older records default to principles."""
    from .creative_knowledge import layered_fields
    result = {key: copy.deepcopy(update.get(key, (inherited or {}).get(key, "principle" if key == "layer" else [])))
              for key in PLACEMENT_FIELDS}
    layered_fields(result)
    return result


def navigation_documents(catalog):
    """One recommendation source for entry, question-map and renderer routes.

    A v1 catalog keeps the flat map. A v2 catalog groups entries by layer: common
    principles first, then renderer capability, then task conditions by prompt length
    and family. Every line is a catalog summary, so curation updates text and map together.
    """
    def link(row):
        return f"[{row['id']}]({row['path'].removeprefix('knowledge/experience/curated/')})"
    def clean(text):
        return text.replace('|', '\\|').replace('\n', ' ')
    rows = catalog['entries']
    layered = catalog.get('schema') == 'creative-experience-catalog-v2'
    footer = ('\n[Reading guide](../../creative-loop/READING.md) · [Working routes](../../creative-loop/README.md) '
              '· [Renderer entrances](renderers.md)\n')
    if not layered:
        text = ('# Experience for video design and revision\n\n'
                'Choose the condition that matters to the target, then read its explanation and evidence. '
                'This navigation is generated from the frozen entry catalog. Related task contributions '
                'appear beside each entry in browse/read; their source cases and curation decisions remain distinct.\n\n'
                '| Question | Working judgment |\n|---|---|\n')
        for row in rows:
            text += f"| {clean('; '.join(row['questions']))} | {link(row)}: {clean(row['summary'])} |\n"
        text += footer
    else:
        def table(selected):
            body = '| Question | Working judgment |\n|---|---|\n'
            for row in selected:
                body += f"| {clean('; '.join(row['questions']))} | {link(row)}: {clean(row['summary'])} |\n"
            return body
        text = ('# Experience for recasting a video into another world or medium\n\n'
                'Entries are grouped by what they are about. Start with the common principles, then read the '
                'section for the renderer you are using, then the section that matches the prompt length and '
                'the kind of world or medium you were asked for. Each line is the entry\'s own summary; '
                'open the entry for its conditions, exceptions and evidence. Related task contributions appear '
                'beside each entry; their source cases and curation decisions remain distinct.\n\n'
                '## Common principles\n\n' + table([r for r in rows if r.get('layer', 'principle') == 'principle']))
        for renderer in sorted({v for r in rows if r.get('layer') == 'renderer' for v in r['renderers']}):
            text += f'\n## {renderer.title()} capabilities and traps\n\n' + table(
                [r for r in rows if r.get('layer') == 'renderer' and renderer in r['renderers']])
        conditions = [r for r in rows if r.get('layer') == 'condition']
        if conditions:
            text += ('\n## Conditions of the task\n\nPrompt length and the kind of world or medium '
                     'change what a good proposal contains.\n')
            shown = set()
            for label, picked in (
                    ('Short prompts', [r for r in conditions if r.get('tracks') == ['short'] and not r.get('families')]),
                    ('Long prompts', [r for r in conditions if r.get('tracks') == ['long'] and not r.get('families')]),
                    ('By family of world or medium', [r for r in conditions if r.get('families')]),
                    ('Other conditions', [r for r in conditions if not r.get('families') and r.get('tracks') not in (['short'], ['long'])])):
                picked = [r for r in picked if r['id'] not in shown]
                if picked:
                    text += f'\n### {label}\n\n' + table(picked)
                    shown.update(r['id'] for r in picked)
        text += footer
    profiles = ('# Renderer entrances\n\n'
                'Current recommendations below come from the same entry summaries as the question map. '
                'Read the complete account for renderer-specific evidence and counterexamples. '
                '[Historical renderer profiles](evidence/renderer-profile-20261102.md) retain the recorded setups '
                'and earlier interpretations; current entry revisions own current advice.\n')
    for renderer in sorted({v for row in rows for v in row['renderers']}):
        profiles += '\n## ' + renderer.title() + '\n\n'
        for row in rows:
            if renderer in row['renderers']:
                profiles += f"- {link(row)}: {row['summary']}\n"
    return {'knowledge/experience/curated/README.md': text,
            'knowledge/experience/curated/renderers.md': profiles}


def refresh_navigation(snapshot):
    # Historical snapshots remain unchanged until an explicit curation is applied.
    for path, text in navigation_documents(snapshot['curated_catalog']).items():
        snapshot['documents'][path] = {'text': text, 'sha256': digest(text)}
        for row in snapshot['curated_catalog']['resources']:
            if row['path'] == path:
                row.update(sha256=digest(text), version='derived-'+digest(text)[:16],
                           review_reference='Derived from canonical entry metadata')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def layer(snapshot):
    return snapshot.get("experience_contributions", {
        "protocol": VERSION, "items": [], "cases": [], "decisions": []})


def _text(value, name, maximum=40000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} needs nonempty bounded text")
    return value


def _strings(value):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError("Navigation fields must be lists of nonempty strings")
    return value


def validate(snapshot):
    content = layer(snapshot)
    if content.get("protocol") != VERSION:
        raise ValueError("Unknown contribution protocol")
    if any(not isinstance(content.get(k), list) for k in ("items", "cases", "decisions")):
        raise ValueError("Invalid contribution layer")
    if snapshot.get("experience_mode") == "none" and any(content[k] for k in ("items", "cases", "decisions")):
        raise ValueError("No-experience snapshots exclude contributions and cases")
    ids, paths = set(), set()
    for row in content["cases"] + content["items"]:
        identity, path = row["id"], row["path"]
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+", identity) or identity in ids
                or path in paths or path != PREFIX + identity + ".md"):
            raise ValueError("Invalid or duplicate contribution identity")
        ids.add(identity); paths.add(path)
        doc = snapshot.get("documents", {}).get(path)
        if not doc or digest(doc["text"]) != row["sha256"] or doc["sha256"] != row["sha256"]:
            raise ValueError("Contribution body differs from its frozen hash")
        _text(row["title"], "title", 500); _text(row["summary"], "summary", 2000)
    case_ids = {r["id"] for r in content["cases"]}
    entry_ids = {r["id"] for r in snapshot.get("curated_catalog", {}).get("entries", [])}
    contribution_ids = {r["id"] for r in content["items"]}
    for row in content["items"]:
        if row["operation"] not in OPS or row["case_id"] not in case_ids:
            raise ValueError("Contribution lacks a bound source case")
        if row.get("target_id") and row["target_id"] not in entry_ids | contribution_ids:
            raise ValueError("Contribution target is not an entry or another contribution")
        _strings(row.get("questions", [])); _strings(row.get("renderers", []))
        placement(row)
    return content


def append(snapshot, changes, provenance, case=None):
    """Create readable records; canonical text and summaries are unchanged."""
    if snapshot.get("experience_mode") != "full":
        raise ValueError("Contributions require a separate full post-task library")
    if not isinstance(changes, list) or len(changes) > 8:
        raise ValueError("Use at most eight contributions per task")
    result = copy.deepcopy(snapshot)
    content = copy.deepcopy(validate(snapshot))
    result["experience_contributions"] = content
    if not changes:
        return result, []
    if not isinstance(provenance, dict) or not provenance.get("sha256"):
        raise ValueError("Contribution needs source provenance")
    case_body = {"provenance": provenance, **(case or {})}
    case_id = "CASE-" + signature(case_body)[:24]
    if not any(r["id"] == case_id for r in content["cases"]):
        text = "# Source case\n\n" + json.dumps(case_body, ensure_ascii=False, indent=2) + "\n"
        row = {"id": case_id, "path": PREFIX + case_id + ".md", "title": "Source case " + case_id,
               "summary": "Actual task, actions, outcomes and inspected evidence for linked contributions.",
               "sha256": digest(text), "version": "1", "kind": "experience_case"}
        result["documents"][row["path"]] = {"text": text, "sha256": row["sha256"]}
        content["cases"].append(row)
    entries = {r["id"]: r for r in result["curated_catalog"]["entries"]}
    targets = {**entries, **{r["id"]: r for r in content["items"]}}
    occupied = {r["id"] for r in result["curated_catalog"]["entries"] + result["curated_catalog"]["resources"] + content["items"] + content["cases"]}
    changed = []
    for change in changes:
        if not isinstance(change, dict) or change.get("op") not in OPS:
            raise ValueError("Task contributions use create/comment/clarify/recommend/propose_revision; replacement is curator-only")
        if set(change) - {"op", "id", "text", "title", "summary", "questions", "renderers", *PLACEMENT_FIELDS}:
            raise ValueError("Unknown contribution fields")
        op = change["op"]
        text = _text(change.get("text"), "text")
        target_id = None if op == "create" else change.get("id")
        target = targets.get(target_id)
        if op != "create" and target is None:
            raise ValueError("Contribute to an experience entry; manuals and Skills require development authorization")
        identity = change.get("id") if op == "create" else "NOTE-" + signature({"change": change, "case": case_id})[:24]
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", identity):
            raise ValueError("New contributions need a safe ID")
        prior = next((r for r in content["items"] if r["id"] == identity), None)
        operation_hash = signature({"change": change, "case": case_id})
        if prior and prior["operation_sha256"] == operation_hash:
            continue
        if identity in occupied:
            raise ValueError("Contribution ID already exists; add a linked clarification")
        summary = _text(change.get("summary", text.split("\n", 1)[0][:700]), "summary", 2000)
        title = _text(change.get("title", f"{op.replace('_', ' ').title()}: {target_id}"), "title", 500)
        if op == "create":
            _text(change.get("title"), "title", 500)
            _text(change.get("summary"), "summary", 2000)
        row = {"id": identity, "path": PREFIX + identity + ".md", "title": title, "summary": summary,
               "operation": op, "target_id": target_id,
               "target_version": {k: target.get(k) for k in ("version", "sha256")} if target else None,
               "case_id": case_id, "version": "1", "status": "contributed",
               "questions": _strings(change.get("questions", target.get("questions", []) if target else [])),
               "renderers": _strings(change.get("renderers", target.get("renderers", []) if target else [])),
               "operation_sha256": operation_hash, "kind": "experience_contribution"}
        row.update(placement(change, target))
        if row["layer"] == "renderer" and not row["renderers"]:
            raise ValueError("Renderer-layer contributions must name their renderer")
        body = text + f"\n\nSource case: [{case_id}]({case_id}.md)\n"
        row["sha256"] = digest(body)
        result["documents"][row["path"]] = {"text": body, "sha256": row["sha256"]}
        content["items"].append(row); occupied.add(identity); targets[identity] = row; changed.append(identity)
    validate(result)
    return result, changed


def curate(snapshot, decisions, *, authorization):
    """Explicit library-level decisions; no task action or automatic caller."""
    _text(authorization, "curation authorization reference", 4000)
    result = copy.deepcopy(snapshot)
    content = copy.deepcopy(validate(snapshot)); result["experience_contributions"] = content
    entries = {r["id"]: r for r in result["curated_catalog"]["entries"]}
    items = {r["id"]: r for r in content["items"]}
    resolved = {i for d in content["decisions"] for i in d["contribution_ids"]}
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("Curation requires explicit decisions")
    for decision in decisions:
        if set(decision) - {"contribution_ids", "disposition", "reason", "entry", "expected_entry_sha256", "successor_ids"}:
            raise ValueError("Unknown curation fields")
        ids = _strings(decision.get("contribution_ids"))
        if not ids or len(set(ids)) != len(ids) or any(i not in items or i in resolved for i in ids):
            raise ValueError("Choose unresolved contributions from this snapshot")
        disposition = decision.get("disposition")
        if disposition not in {"accept", "merge", "supersede", "decline"}:
            raise ValueError("Choose accept, merge, supersede or decline")
        _text(decision.get("reason"), "curation reason", 4000)
        successors = decision.get("successor_ids", [])
        if disposition == "supersede" and (not successors or any(i not in items or i in ids for i in _strings(successors))):
            raise ValueError("Superseding needs an existing successor contribution")
        update = decision.get("entry")
        if disposition in {"accept", "merge"}:
            required = {"id", "title", "text", "summary", "questions", "renderers"}
            if (not isinstance(update, dict) or not required <= set(update)
                    or set(update) - required - set(PLACEMENT_FIELDS)):
                raise ValueError("Curate complete entry text and discovery metadata together")
            identity = update["id"]
            if not isinstance(identity, str) or not re.fullmatch(r"EX-[A-Za-z0-9_.-]+", identity):
                raise ValueError("Curated entries use EX- IDs; manuals and Skills are outside curation")
            old = entries.get(identity)
            if decision.get("expected_entry_sha256") != (old["sha256"] if old else None):
                raise ValueError("Canonical entry changed since curation was prepared")
            if not old and any(r["id"] == identity for r in result["curated_catalog"]["resources"] + content["items"]):
                raise ValueError("Choose a distinct canonical entry ID")
            inherited = old or {}
            if not old:
                # A new account inherits unambiguous placement from its accepted
                # contributions. Merging conflicting scopes is a curator decision.
                inherited = {}
                for key in PLACEMENT_FIELDS:
                    values = [placement(items[i])[key] for i in ids]
                    if key not in update and any(v != values[0] for v in values[1:]):
                        raise ValueError(f"Merged contributions disagree on {key}; specify the curated placement")
                    inherited[key] = values[0]
            path = old["path"] if old else "knowledge/experience/curated/entries/" + identity + ".md"
            text = _text(update["text"], "entry text")
            row = {**(old or {}), **{k: update[k] for k in ("id", "title", "summary", "questions", "renderers")},
                   "path": path, "sha256": digest(text), "version": "curation-" + signature(decision)[:16],
                   "review_status": "approved", "review_reference": authorization,
                   "evidence_ids": (old or {}).get("evidence_ids", []),
                   "contribution_ids": list(dict.fromkeys([*(old or {}).get("contribution_ids", []), *ids]))}
            row.update(placement(update, inherited))
            if row["layer"] == "renderer" and not row["renderers"]:
                raise ValueError("Renderer-layer entries must name their renderer")
            for key in ("title", "summary"):
                _text(row[key], key, 2000)
            for key in ("questions", "renderers"):
                _strings(row[key])
            # Remove stale derived recommendations rather than carrying the old judgment.
            row["applicability"] = row["summary"]; row["recommendation"] = row["summary"]
            row["aliases"] = [row["title"], *row["questions"]]
            if old:
                result.setdefault("experience_entry_history", []).append({"entry": copy.deepcopy(old), "document": copy.deepcopy(result["documents"][path])})
                old.clear(); old.update(row)
            else:
                result["curated_catalog"]["entries"].append(row); entries[identity] = row
            result["documents"][path] = {"text": text, "sha256": row["sha256"]}
        elif update is not None:
            raise ValueError("Decline/supersede records a decision without changing an entry")
        content["decisions"].append({**copy.deepcopy(decision), "authorization": authorization})
        resolved.update(ids)
    result["curated_catalog"]["revision"] = "curation-" + signature(content["decisions"])[:20]
    if result["curated_catalog"]["schema"] == "creative-experience-catalog-v2":
        order = {"principle": 0, "renderer": 1, "condition": 2}
        result["curated_catalog"]["entries"].sort(key=lambda row: (order[row.get("layer", "principle")], row["id"]))
    refresh_navigation(result)
    validate(result)
    return result
