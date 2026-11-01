"""Independent final scoring bridge; no Planner trace or online review is exposed."""
from __future__ import annotations
import json
from pathlib import Path

from .common import load, save, sha
from .ledger import digest
from .rsi_calls import call_once
from .rsi_validation import verify_manifest, runtime_hashes


def protocol_hash():
    from evaluation import judges, registry
    return digest({"prompts": {k: getattr(judges, k).replace("in Chinese", "in English") for k in ("SEMANTIC", "DESIGN", "CREATIVITY")},
                   "judgment": registry.judgment_fingerprint(), "scoring": registry.scoring_fingerprint(),
                   "language": "English", "bridge": "lha-rsi-independent-v1"})


class DurableJudge:
    def __init__(self, client, directory):
        self.client, self.directory = client, Path(directory)
        self.model = client.model
        self.reasoning_effort = getattr(client, "reasoning_effort", None)

    def predict_json(self, *, system_prompt, user_text, image_paths):
        system = system_prompt.replace("in Chinese", "in English")
        directory = self.directory / digest({"system": system, "user": user_text, "images": [sha(p) for p in image_paths]})
        outer = self
        class TextAdapter:
            model = outer.model
            reasoning_effort = outer.reasoning_effort
            def predict_text(self, **kwargs):
                return json.dumps(outer.client.predict_json(system_prompt=kwargs["system_prompt"], user_text=kwargs["user_text"], image_paths=kwargs["image_paths"]), ensure_ascii=False)
        return json.loads(call_once(directory, TextAdapter(), system, user_text, image_paths, 16000))


def judge_run(manifest_path, run, output, client, *, root):
    from evaluation.media import prepare
    from evaluation.judges import judge
    from evaluation.protocol import validate_card
    from evaluation.scoring import score
    manifest = verify_manifest(manifest_path)
    if manifest["runtime"] != runtime_hashes():
        raise ValueError("Independent scoring runtime changed after validation was frozen")
    profile = manifest["protocol"]["judge"]
    if client.model != profile["model"] or getattr(client, "reasoning_effort", None) != profile.get("reasoning_effort") or profile["protocol_sha256"] != protocol_hash():
        raise ValueError("Final judge differs from the frozen independent protocol")
    from .rsi_calibration import verify_calibration
    verify_calibration(profile)
    weights = profile.get("utility_weights")
    if not isinstance(weights, dict) or not weights or any(type(w) not in {int, float} or w <= 0 for w in weights.values()) or abs(sum(weights.values()) - 1) > 1e-8:
        raise ValueError("Freeze positive semantic utility weights summing to one")
    run, output = Path(run), Path(output)
    state, binding = load(run / "state.json"), load(run / "validation-binding.json")
    if binding["manifest_sha256"] != manifest["sha256"] or state["status"] != "complete":
        raise ValueError("Score a complete bound run")
    task = next(t for t in manifest["tasks"] if t["id"] == binding["task"])
    card = validate_card(load(task["card"]))
    if sha(task["card"]) != task["card_file_sha256"] or card["source_sha256"] != task["source_sha256"] or card["requirement"] != task["request"]:
        raise ValueError("Independent task card changed")
    rows = []
    for identity, video in state["videos"].items():
        if not video.get("job_id"):
            continue
        if sha(video["path"]) != video["sha256"]:
            raise ValueError("Generated video changed")
        rows.append(score_case(task, video, profile, client, output / identity, root=root, identity=identity))
    save(output / "scores.json", rows)
    return rows


def score_case(task, video, profile, client, directory, *, root, identity):
    """Shared blind scoring for calibration and frozen experiment arms."""
    from evaluation.media import prepare
    from evaluation.judges import judge
    from evaluation.protocol import validate_card
    from evaluation.scoring import score
    directory = Path(directory)
    card = validate_card(load(task["card"]))
    weights = profile["utility_weights"]
    if not weights or any(type(w) not in {int, float} or w <= 0 for w in weights.values()) or abs(sum(weights.values())-1) > 1e-8:
        raise ValueError("Freeze positive utility weights summing to one")
    if sha(task["card"]) != task["card_file_sha256"] or card["source_sha256"] != task["source_sha256"] or card["requirement"] != task["request"]:
        raise ValueError("Scoring card changed")
    if sha(video["path"]) != video["sha256"]:
        raise ValueError("Scoring video changed")
    evidence_path = directory / "evidence.json"
    if evidence_path.exists():
        evidence = load(evidence_path)
        if evidence["output_sha256"] != video["sha256"]:
            raise ValueError("Independent evidence changed")
    else:
        evidence = prepare(card, Path(video["path"]), directory / "frames", root=Path(root),
                           frame_count=profile.get("frame_count", 12), dense_ranges=profile.get("dense_ranges", []), mapping=video.get("time_mapping"))
        save(evidence_path, evidence)
    references = load(task["references"]) if task.get("references") else None
    if references and sha(task["references"]) != task["references_sha256"]:
        raise ValueError("Frozen reference cohort changed")
    result = judge(card, evidence, DurableJudge(client, directory / "calls"), directory / "raw", references=references)
    scored = score(card, result, role="final_rsi_independent")
    semantic = scored["semantic"]
    values = utility_components(scored, weights)
    metrics = {"success": True if scored["success"] == "pass" else False if scored["success"] == "fail" else None,
               "major_damage": scored.get("major_damage"),
               "core": semantic["preserve_core"]["score"],
               "utility": sum(weights[k] * v for k, v in values.items()) if all(v is not None for v in values.values()) else None}
    artifact = {"judge": profile, "output_sha256": video["sha256"], "source_sha256": task["source_sha256"], "judgment": result, "score": scored,
                "rsi_metrics": metrics, "evidence_sha256": evidence["evidence_sha256"]}
    save(directory / "judgment.json", artifact)
    return {"id": identity, "output_sha256": video["sha256"], "judge": profile,
            "raw": str((directory / "judgment.json").resolve()), "raw_sha256": sha(directory / "judgment.json"), **metrics}


def utility_components(scored, weights):
    """Explicit semantic [0,1] and anchored visual [1,4] components; missing stays missing."""
    result = {}
    for key in weights:
        if key in scored["semantic"]:
            result[key] = scored["semantic"][key]["score"]
        elif key.startswith("rating:"):
            name = key.split(":", 1)[1]
            if name not in scored["ratings"]:
                raise ValueError("Unknown utility visual component: " + name)
            value = scored["ratings"][name]
            result[key] = (value - 1) / 3 if value is not None and scored["rating_status"].get(name) == "scored" else None
        else:
            raise ValueError("Utility must name a semantic metric or explicit rating:name")
    return result
