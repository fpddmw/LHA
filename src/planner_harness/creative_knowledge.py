"""Read-only creative-loop corpus; no live experience catalog or publication hooks."""
from __future__ import annotations

import copy
import posixpath
import re
from pathlib import Path

from .common import load, save
from .knowledge import Knowledge


class CreativeKnowledge(Knowledge):
    NAV_ALIASES = {"knowledge/README.md": "map", "knowledge/READING.md": "manual"}
    def __init__(self, root, snapshot=None):
        root = Path(root).resolve()
        saved = copy.deepcopy(snapshot) if isinstance(snapshot, dict) else load(snapshot) if snapshot else None
        if saved:
            if saved.get("profile") != "creative_loop_v1":
                raise ValueError("Creative loop requires its own knowledge snapshot")
            allow = saved["allowlist"]
            super().__init__(root, saved)
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
        for identity in ("map", "manual", "integration"):
            row = self.items.pop(identity, None)
            if row:
                self.paths.pop(row["path"], None)
        for identity, path in allow["navigation"].items():
            self.add(identity, path, identity, "operational_guidance")
        for path in self.paths:
            parts = Path(path).parts
            if "wiki" in parts or "staged" in parts or any(p.startswith("rsi_") for p in parts):
                raise ValueError("Excluded material in creative knowledge manifest")
        self.allowlist = allow
        if saved is None:
            self.snapshot = None

    def freeze(self, path):
        # No publication lock/journal: this profile has no learning/publication path.
        self._freeze(path)
        self.snapshot.update(profile="creative_loop_v1", allowlist=copy.deepcopy(self.allowlist))
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
        if target in self.allowlist["navigation"] and target != "map":
            return {"material": self.items[target], "instruction": "Read this operating page when useful."}
        return super().browse(target)

    def overview(self):
        ids = ("manual", "meaning", "design-expression", "experience-map")
        return {"classes": self.allowlist["classes"],
                "guidance": "Read a known ID, browse comparative guides, or search a question. Reading is optional and model-led.",
                "entrances": [self.items[i] for i in ids], "totals": self.manifest["totals"]}
