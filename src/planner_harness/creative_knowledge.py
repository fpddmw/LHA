"""Read-only creative-loop corpus; no live experience catalog or publication hooks."""
from __future__ import annotations

import copy
import posixpath
import re
from pathlib import Path

from .common import load, save, sha
from .knowledge import Knowledge


CATALOG_SCHEMAS = ("creative-experience-catalog-v1", "creative-experience-catalog-v2")
LAYERS = ("principle", "renderer", "condition")
TRACKS = ("short", "long")
STAGES = ("design", "inspect", "revise", "deliver")


def layered_fields(row):
    """Validate the optional v2 placement fields; v1 entries default to common principles."""
    layer = row.get("layer", "principle")
    if layer not in LAYERS:
        raise ValueError("Experience layer must be principle, renderer or condition")
    for key, allowed in (("tracks", TRACKS), ("stages", STAGES)):
        values = row.get(key, [])
        if not isinstance(values, list) or any(v not in allowed for v in values):
            raise ValueError(f"Experience {key} use only {', '.join(allowed)}")
    families = row.get("families", [])
    if not isinstance(families, list) or any(not isinstance(v, str) or not v.strip() for v in families):
        raise ValueError("Experience families are lists of nonempty labels")
    return layer


class CreativeKnowledge(Knowledge):
    NAV_ALIASES = {"knowledge/README.md": "map", "knowledge/READING.md": "manual",
                   "knowledge/experience/README.md": "experience-map"}
    def __init__(self, root, snapshot=None, *, experience_mode=None):
        root = Path(root).resolve()
        saved = copy.deepcopy(snapshot) if isinstance(snapshot, dict) else load(snapshot) if snapshot else None
        recorded_mode = saved.get("experience_mode", "full") if saved else None
        if experience_mode is not None and recorded_mode and experience_mode != recorded_mode:
            raise ValueError("Resume must retain the frozen experience mode")
        self.experience_mode = recorded_mode or experience_mode or "full"
        if self.experience_mode not in {"full", "none"}:
            raise ValueError("Experience mode must be full or none")
        if saved:
            if saved.get("profile") != "creative_loop_v1":
                raise ValueError("Creative loop requires its own knowledge snapshot")
            allow = saved["allowlist"]
            super().__init__(root, saved)
            curated = saved.get("curated_catalog", {"schema": "creative-experience-catalog-v1", "revision": "legacy-none", "entries": [], "resources": []})
        else:
            allow = load(root / "knowledge/creative-loop/manifest.json")
            mode = allow.get("experience_modes", {}).get(self.experience_mode, {})
            if self.experience_mode == "none" and not mode:
                raise ValueError("No-experience scope is not configured")
            allow = copy.deepcopy(allow)
            allow["source_groups"] = [g for g in allow["source_groups"] if g not in mode.get("exclude_source_groups", [])]
            for key in ("static_topics", "navigation", "operations_manual"):
                if key in mode:
                    allow[key] = copy.deepcopy(mode[key])
            source = load(root / allow["source_manifest"])
            manifest = {key: copy.deepcopy(source.get(key, [])) for key in allow["source_groups"]}
            manifest["totals"] = copy.deepcopy(source["totals"])
            for group in allow["source_groups"]:
                manifest[group] = [r for r in manifest[group] if r.get("id") not in mode.get("exclude_ids", [])]
            for row in manifest.get("guides", []):
                if row["id"] in mode.get("guide_overrides", {}):
                    row["path"] = mode["guide_overrides"][row["id"]]
            if self.experience_mode == "none":
                manifest["totals"].update(guides=len(manifest.get("guides", [])), model_experience=0)

            topics = [{"id": identity, "path": path, "title": identity.replace("-", " ")}
                      for identity, path in allow["static_topics"].items()]
            # A constructed snapshot avoids reading the mutable experience catalog.
            super().__init__(root, {"manifest": manifest, "experiences": topics,
                                   "entrances": {}, "documents": {}, "asset_hashes": {}})
            catalog_path = allow.get("curated_catalog")
            if catalog_path and catalog_path != "knowledge/experience/curated/catalog.json":
                raise ValueError("Creative experience uses the dedicated curated catalog")
            curated = load(root / catalog_path) if catalog_path and self.experience_mode == "full" else {
                "schema": "creative-experience-catalog-v1", "revision": "none", "entries": [], "resources": []}
        for identity in ("map", "manual", "integration"):
            row = self.items.pop(identity, None)
            if row:
                self.paths.pop(row["path"], None)
        for identity,path in allow['navigation'].items():
            if identity=='score-definitions':continue
            self.add(identity,path,identity,'operational_guidance')
        if self.experience_mode == "none":
            prefixes = allow.get("experience_modes", {}).get("none", {}).get("exclude_path_prefixes", [])
            for identity, row in list(self.items.items()):
                if any(row["path"].startswith(prefix) for prefix in prefixes):
                    self.items.pop(identity)
                    self.paths.pop(row["path"], None)
            if curated["entries"] or curated["resources"]:
                raise ValueError("No-experience snapshot contains curated content")
        self.curated_catalog = copy.deepcopy(curated)
        self._add_curated(saved is not None)
        from .experience_contributions import validate
        self.contributions = copy.deepcopy(validate(saved or {"experience_mode": self.experience_mode}))
        decisions = {identity: decision for decision in self.contributions["decisions"]
                     for identity in decision["contribution_ids"]}
        for row in self.contributions["cases"] + self.contributions["items"]:
            if row["id"] in self.items or row["path"] in self.paths:
                raise ValueError("Contribution identity collides with existing knowledge")
            self.add(row["id"], row["path"], row["title"], row["kind"])
            self.items[row["id"]].update(copy.deepcopy(row))
            if row["id"] in decisions:
                decision = decisions[row["id"]]
                self.items[row["id"]]["curation"] = {k: copy.deepcopy(decision[k])
                    for k in ("disposition", "reason", "authorization", "successor_ids") if k in decision}
                self.items[row["id"]]["curation"]["entry_id"] = decision.get("entry", {}).get("id")
        for path in self.paths:
            parts = Path(path).parts
            if "wiki" in parts or "staged" in parts or any(p.startswith("rsi_") for p in parts):
                raise ValueError("Excluded material in creative knowledge manifest")
        if 'review' not in self.items:
            self.add('review','.agents/skills/lha-video-review/SKILL.md','Video review','operational_guidance')
        self.add("operating-actions",allow.get("operations_manual","src/planner_harness/CREATIVE_LOOP.md"),"Operating actions","operational_guidance")
        self.allowlist = allow
        if saved is None:
            self.snapshot = None

    def _add_curated(self, frozen):
        catalog = self.curated_catalog
        if (catalog.get("schema") not in CATALOG_SCHEMAS
                or not isinstance(catalog.get("revision"), str)
                or not isinstance(catalog.get("entries"), list)
                or not isinstance(catalog.get("resources"), list)):
            raise ValueError("Invalid curated experience catalog")
        rows = catalog["entries"] + catalog["resources"]
        resource_ids = {r.get("id") for r in catalog["resources"]}
        for row in rows:
            required = ("id", "path", "title", "sha256", "version", "review_reference")
            if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
                raise ValueError("Curated items require identity, revision, content hash and content-review reference")
            private_training = frozen and (self.snapshot or {}).get("training_revision",{}).get("protocol") == "lha-private-training-experience-v1"
            if row.get("review_status") != "approved" and not (private_training and row.get("review_status")=="training_validated"):
                raise ValueError("Only content explicitly marked approved can enter the curated runtime catalog")
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", row["id"]) or not re.fullmatch(r"[a-f0-9]{64}", row["sha256"]):
                raise ValueError("Invalid curated identity or hash")
            relative = Path(row["path"])
            if (relative.is_absolute() or ".." in relative.parts or "\\" in row["path"]
                    or not row["path"].startswith("knowledge/experience/curated/")
                    or relative.suffix.lower() not in {".md", ".json", ".txt", ".png", ".jpg", ".jpeg", ".webp"}):
                raise ValueError("Curated items must be explicit text/image files in the curated directory")
            if row["id"] in self.items or row["path"] in self.paths:
                raise ValueError("Duplicate curated identity or path")
            entry = row in catalog["entries"]
            if entry:
                if relative.suffix != ".md" or not isinstance(row.get("summary"), str) or not row["summary"].strip():
                    raise ValueError("Experience entries need Markdown and a substantive summary")
                for key in ("questions", "renderers", "evidence_ids"):
                    if not isinstance(row.get(key), list) or any(not isinstance(v, str) for v in row[key]):
                        raise ValueError("Entry navigation fields must be lists of strings")
                if any(i not in resource_ids for i in row["evidence_ids"]):
                    raise ValueError("Experience evidence must be explicitly cataloged")
                row_layer = layered_fields(row)
                if catalog["schema"] == "creative-experience-catalog-v2" and row_layer == "renderer" and not row["renderers"]:
                    raise ValueError("Renderer-layer experience must name its renderer")
            if frozen:
                recorded = (self.snapshot or {}).get("documents", {}).get(row["path"], {}).get("sha256")
                recorded = recorded or (self.snapshot or {}).get("asset_hashes", {}).get(row["path"])
                if recorded != row["sha256"]:
                    raise ValueError("Curated snapshot is missing its bound text or asset")
            else:
                file = (self.root / relative).resolve()
                if not file.is_relative_to(self.root / "knowledge/experience/curated") or not file.is_file() or sha(file) != row["sha256"]:
                    raise ValueError(f"Curated content missing or changed since review: {file}")
            self.add(row["id"], row["path"], row["title"], "experience" if entry else "experience_evidence")
            self.items[row["id"]].update(copy.deepcopy(row))
            self.items[row["id"]]["kind"] = "experience" if entry else "experience_evidence"

    def usage_index(self):
        """Factual source identities; not an injected list of card instructions."""
        records = {}
        for identity, row in self.items.items():
            if row["kind"] not in {"experience", "experience_evidence", "model_experience", "experience_contribution", "experience_case"} and identity != "experience":
                continue
            text_hash = row.get("sha256")
            if not text_hash and Path(row["path"]).suffix in {".md", ".json", ".txt"}:
                text_hash = self.document(row)["sha256"]
            records[identity] = {k: row[k] for k in ("id", "path", "title", "kind")}
            records[identity].update(sha256=text_hash, version=row.get("version", "static-source"))
            records[identity].update({k: copy.deepcopy(row[k]) for k in ("layer", "tracks", "families", "stages", "renderers") if k in row})
        return {"catalog_revision": self.curated_catalog["revision"], "items": records}

    def freeze(self, path):
        # Freeze the exact private contribution layer alongside canonical material.
        revision=(self.snapshot or {}).get("training_revision")
        history=copy.deepcopy((self.snapshot or {}).get("experience_entry_history", []))
        self._freeze(path)
        if revision:self.snapshot["training_revision"]=copy.deepcopy(revision)
        self.snapshot["experience_contributions"] = copy.deepcopy(self.contributions)
        if history:self.snapshot["experience_entry_history"] = history
        self.snapshot.update(profile="creative_loop_v1", allowlist=copy.deepcopy(self.allowlist),
                             curated_catalog=copy.deepcopy(self.curated_catalog), experience_mode=self.experience_mode)
        save(path, self.snapshot)

    def links(self, text, source_path=None):
        links = []
        for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0]
            relative = posixpath.normpath(posixpath.join(posixpath.dirname(source_path or ""), target))
            row = self.paths.get(relative) or self.items.get(self.NAV_ALIASES.get(relative))
            if row:
                links.append({"id": row["id"], "label": label, "path": row["path"], "available": True})
        return links

    def read(self, target, start_line=1, section=None, *, max_chars=6000, start_char=0):
        target = self.NAV_ALIASES.get(target, target)
        if type(max_chars) is not int or not 256 <= max_chars <= 8000:
            raise ValueError("Choose a page size between 256 and 8000 characters")
        result = super().read(target, start_line, section, max_chars=max_chars,
                              start_char=start_char, split_long_lines=True)
        row = self.items.get(target) or self.paths[target]
        links = self.links(result["text"], row["path"])
        result["links"] = links[:12]
        result["link_count_on_page"] = len(links)
        result["link_scope"] = "Up to twelve resolved navigation links; exact source-page text remains intact."
        result["profile"] = "creative_loop_v1"
        result.update(self.related(row["id"]))
        if row.get("case_id"):
            result["source_case"] = self.items[row["case_id"]]
        if row["id"] in {"experience-map", "EX-renderer-profiles"}:
            result["current_entries"] = self.entry_index()
        return result

    def related(self, identity):
        adopted = self.items.get(identity, {}).get("contribution_ids", [])
        rows = [self.items[r["id"]] for r in self.contributions["items"]
                if r.get("target_id") == identity or r["id"] in adopted]
        rows.sort(key=lambda r: bool(r.get("curation")))
        return {"related_contributions": rows[:6], "related_contribution_count": len(rows),
                "contribution_scope": "Linked contributions retain their author and case; curation records show adoption. Browse contributions or search for more."} if rows else {}

    def entry_index(self):
        keys = ("id", "title", "summary", "questions", "renderers")
        return [{**{k: self.items[r["id"]][k] for k in keys},
                 **{k: r[k] for k in ("layer", "tracks", "families", "stages") if k in r}}
                for r in self.curated_catalog["entries"]]

    def browse(self, target="map"):
        if not self.enabled:
            return {"entrances": [], "guidance": "Knowledge access disabled in this arm."}
        curated_ids = {r["id"] for r in self.curated_catalog["entries"] + self.curated_catalog["resources"]}
        if target == "contributions" or re.fullmatch(r"contributions:[0-9]+", target):
            if self.experience_mode != "full":
                raise ValueError("Contributions are outside the no-experience scope")
            start = int(target.split(':')[1]) if ':' in target else 0
            rows = self.contributions["items"]
            return {"contributions": [self.items[r["id"]] for r in rows[start:start+20]],
                    "total": len(rows), "next": f"contributions:{start+20}" if start+20 < len(rows) else None,
                    "instruction": "Read a contribution and its source case. Adopted, superseded and declined records retain their curation decision."}
        if target in {r["id"] for r in self.contributions["items"] + self.contributions["cases"]}:
            return {"material": self.items[target], **self.related(target)}
        if target == "experience-map" and target in self.items:
            return {"material": self.items[target], "entries": [{**self.items[r["id"]], **self.related(r["id"])} for r in self.curated_catalog["entries"]],
                    "contributions": {"count": len(self.contributions["items"]), "browse": "contributions"},
                    "static_resources": [r for r in self.items.values() if r["kind"] in {"experience", "model_experience"} and r["id"] not in curated_ids],
                    "catalog_revision": self.curated_catalog["revision"],
                    "work_entrances":[self.items[i] for i in ("understand-and-design","planning-resources","observation-diagnosis","generation-input","understand-and-revise","manual") if i in self.items],
                    "model_entrances":[r for r in self.curated_catalog["resources"] if "renderer" in r["id"].lower() or "renderer" in r["path"].lower()],
                    "instruction": "Choose a working question or model; inspect conditions, the full explanation and consequential counterevidence."}
        if target in curated_ids:
            return {"material": self.items[target], **self.related(target), "instruction": "Read the explanation and its scoped evidence when relevant."}
        if target in self.allowlist["navigation"] and target != "map":
            return {"material": self.items[target], "instruction": "Read this operating page when useful."}
        return super().browse(target)

    def search(self, query, limit=8, scope="all"):
        from .knowledge_search import search

        result = search(self, query, limit, scope)
        for row in result['matches']:
            if row.get('kind')=='experience':
                row['applicability'] = row.get('applicability',row.get('summary'))
                row['recommendation'] = row.get('recommendation',row.get('summary'))
            row['open'] = {'action':'read','arguments':{'targets':[{'id':row['id']}]}}
            row.update(self.related(row['id']))
        return result

    def overview(self):
        if not self.enabled:return {"entrances":[],"guidance":"This method had no knowledge access."}
        ids = ("manual", "understand-and-design", "understand-and-revise", "planning-resources", "observation-diagnosis", "generation-input", "meaning", "design-expression", "experience-map")
        return {"classes": self.allowlist["classes"],
                "guidance": "Read a known ID, browse comparative guides, or search a question. Reading is optional and model-led.",
                "entrances": [self.items[i] for i in ids if i in self.items], "totals": self.manifest["totals"]}
