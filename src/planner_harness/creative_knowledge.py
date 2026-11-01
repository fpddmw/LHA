"""Read-only creative-loop corpus; no live experience catalog or publication hooks."""
from __future__ import annotations

import copy
import posixpath
import re
from pathlib import Path

from .common import load, save, sha
from .knowledge import Knowledge


class CreativeKnowledge(Knowledge):
    NAV_ALIASES = {"knowledge/README.md": "map", "knowledge/READING.md": "manual",
                   "knowledge/experience/README.md": "experience-map"}
    def __init__(self, root, snapshot=None):
        root = Path(root).resolve()
        saved = copy.deepcopy(snapshot) if isinstance(snapshot, dict) else load(snapshot) if snapshot else None
        if saved:
            if saved.get("profile") != "creative_loop_v1":
                raise ValueError("Creative loop requires its own knowledge snapshot")
            allow = saved["allowlist"]
            super().__init__(root, saved)
            curated = saved.get("curated_catalog", {"schema": "creative-experience-catalog-v1", "revision": "legacy-none", "entries": [], "resources": []})
        else:
            allow = load(root / "knowledge/creative-loop/manifest.json")
            source = load(root / allow["source_manifest"])
            manifest = {key: copy.deepcopy(source.get(key, [])) for key in allow["source_groups"]}
            manifest["totals"] = copy.deepcopy(source["totals"])
            topics = [{"id": identity, "path": path, "title": identity.replace("-", " ")}
                      for identity, path in allow["static_topics"].items()]
            # A constructed snapshot avoids reading the mutable experience catalog.
            super().__init__(root, {"manifest": manifest, "experiences": topics,
                                   "entrances": {}, "documents": {}, "asset_hashes": {}})
            catalog_path = allow.get("curated_catalog")
            if catalog_path and catalog_path != "knowledge/experience/curated/catalog.json":
                raise ValueError("Creative experience uses the dedicated curated catalog")
            curated = load(root / catalog_path) if catalog_path else {
                "schema": "creative-experience-catalog-v1", "revision": "none", "entries": [], "resources": []}
        for identity in ("map", "manual", "integration"):
            row = self.items.pop(identity, None)
            if row:
                self.paths.pop(row["path"], None)
        for identity, path in allow["navigation"].items():
            self.add(identity, path, identity, "operational_guidance")
        self.curated_catalog = copy.deepcopy(curated)
        self._add_curated(saved is not None)
        for path in self.paths:
            parts = Path(path).parts
            if "wiki" in parts or "staged" in parts or any(p.startswith("rsi_") for p in parts):
                raise ValueError("Excluded material in creative knowledge manifest")
        self.allowlist = allow
        if saved is None:
            self.snapshot = None

    def _add_curated(self, frozen):
        catalog = self.curated_catalog
        if (catalog.get("schema") != "creative-experience-catalog-v1"
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
            if row.get("review_status") != "approved":
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
            if frozen:
                recorded = (self.snapshot or {}).get("documents", {}).get(row["path"], {}).get("sha256")
                recorded = recorded or (self.snapshot or {}).get("asset_hashes", {}).get(row["path"])
                if recorded != row["sha256"]:
                    raise ValueError("Curated snapshot is missing its bound text or asset")
            else:
                file = (self.root / relative).resolve()
                if not file.is_relative_to(self.root / "knowledge/experience/curated") or not file.is_file() or sha(file) != row["sha256"]:
                    raise ValueError("Curated content missing or changed since review")
            self.add(row["id"], row["path"], row["title"], "experience" if entry else "experience_evidence")
            self.items[row["id"]].update(copy.deepcopy(row))
            self.items[row["id"]]["kind"] = "experience" if entry else "experience_evidence"

    def usage_index(self):
        """Factual source identities; not an injected list of card instructions."""
        records = {}
        for identity, row in self.items.items():
            if row["kind"] not in {"experience", "experience_evidence", "model_experience"} and identity != "experience":
                continue
            text_hash = row.get("sha256")
            if not text_hash and Path(row["path"]).suffix in {".md", ".json", ".txt"}:
                text_hash = self.document(row)["sha256"]
            records[identity] = {k: row[k] for k in ("id", "path", "title", "kind")}
            records[identity].update(sha256=text_hash, version=row.get("version", "static-source"))
        return {"catalog_revision": self.curated_catalog["revision"], "items": records}

    def freeze(self, path):
        # No publication lock/journal: this profile has no learning/publication path.
        self._freeze(path)
        self.snapshot.update(profile="creative_loop_v1", allowlist=copy.deepcopy(self.allowlist),
                             curated_catalog=copy.deepcopy(self.curated_catalog))
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
        return result

    def browse(self, target="map"):
        if not self.enabled:
            return {"entrances": [], "guidance": "Knowledge access disabled in this arm."}
        curated_ids = {r["id"] for r in self.curated_catalog["entries"] + self.curated_catalog["resources"]}
        if target == "experience-map":
            return {"material": self.items[target], "entries": [self.items[r["id"]] for r in self.curated_catalog["entries"]],
                    "static_resources": [r for r in self.items.values() if r["kind"] in {"experience", "model_experience"} and r["id"] not in curated_ids],
                    "catalog_revision": self.curated_catalog["revision"],
                    "instruction": "Choose a relevant question or renderer; read depth is optional."}
        if target in curated_ids:
            return {"material": self.items[target], "instruction": "Read the explanation and its scoped evidence when relevant."}
        if target in self.allowlist["navigation"] and target != "map":
            return {"material": self.items[target], "instruction": "Read this operating page when useful."}
        return super().browse(target)

    def overview(self):
        ids = ("manual", "understand-and-design", "understand-and-revise", "meaning", "design-expression", "experience-map")
        return {"classes": self.allowlist["classes"],
                "guidance": "Read a known ID, browse comparative guides, or search a question. Reading is optional and model-led.",
                "entrances": [self.items[i] for i in ids if i in self.items], "totals": self.manifest["totals"]}
