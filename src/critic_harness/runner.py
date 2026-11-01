"""Durable model-led critique, isolated from formal benchmark evaluation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from planner_harness.common import ROOT, load, page, save, sha, stamp
from planner_harness.execution import signature
from planner_harness.knowledge import Knowledge
from .evidence import Evidence, metadata, validate_assessment


class CriticHarness:
    def __init__(self, output, model, *, root=ROOT):
        self.output, self.model, self.root = Path(output).resolve(), model, Path(root).resolve()
        self.state = None

    def checkpoint(self):
        self.state["updated_at"] = stamp()
        save(self.output / "state.json", self.state)

    def start(self, spec, *, max_turns=18):
        if (self.output / "state.json").exists():
            raise ValueError("Existing review; use resume")
        spec = copy.deepcopy(spec)
        if not spec.get("request") or "source" not in spec["videos"] or spec["candidate"] not in spec["videos"]:
            raise ValueError("Need original request, source and candidate")
        for identity, info in spec["videos"].items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", identity):
                raise ValueError("Unsafe video ID")
            path = (self.root / info["path"]).resolve()
            digest = sha(path)
            if info.get("sha256", digest) != digest:
                raise ValueError("Video hash mismatch")
            info.update(path=str(path), sha256=digest, **metadata(path))
            if info.get("parent") and info["parent"] not in spec["videos"]:
                raise ValueError("Actual parent must be available; omit unknown ancestry")
        for identity in spec["videos"]:
            seen, current = set(), identity
            while current:
                if current in seen:
                    raise ValueError("Video ancestry cycle")
                seen.add(current)
                current = spec["videos"][current].get("parent")
        duration = float(spec.get("duration_seconds", spec["videos"]["source"]["duration_seconds"]))
        if duration <= 0 or duration > spec["videos"]["source"]["duration_seconds"] + 1e-6:
            raise ValueError("Invalid original task duration")
        spec["duration_seconds"] = duration
        self.output.mkdir(parents=True, exist_ok=True)
        package = Path(__file__).parent
        materials = {p.relative_to(package).as_posix(): p.read_text(encoding="utf-8") for p in package.rglob("*.md")}
        frozen = spec.get("frozen_critic")
        if frozen:
            if sha(frozen["instructions"]) != frozen["instructions_sha256"] or sha(frozen["knowledge"]) != frozen["knowledge_sha256"]:
                raise ValueError("Frozen task Critic material changed")
            materials = load(frozen["instructions"])
        save(self.output / "instructions.json", materials)
        self.system = materials["OPERATIONS.md"]
        if spec.get("requirements"):
            self.system += "\n\n" + materials["RSI.md"]
        self.knowledge = Knowledge(self.root, frozen["knowledge"] if frozen else None)
        self.knowledge.freeze(self.output / "knowledge-snapshot.json")
        self.knowledge = Knowledge(self.root, self.output / "knowledge-snapshot.json")
        self.state = {"protocol": "lha-online-critic-rsi-v1" if spec.get("requirements") else "lha-online-critic-v1", "status": "running", "created_at": stamp(), "spec": spec,
                      "spec_sha256": signature(spec), "instructions_sha256": sha(self.output / "instructions.json"),
                      "knowledge_sha256": sha(self.output / "knowledge-snapshot.json"),
                      "runtime": {p.name: sha(p) for p in package.glob("*.py")},
                      "model": getattr(self.model, "model", type(self.model).__name__),
                      "reasoning_effort": getattr(self.model, "reasoning_effort", "unknown"),
                      "backend": type(self.model).__name__, "max_turns": max_turns, "attempts": 0,
                      "observations": {}, "events": [], "notes": [], "process_opened": False,
                      "assessment": None, "pending": None}
        self.evidence = Evidence(spec["videos"], self.output, cache=frozen.get("evidence_cache") if frozen else None)
        overview = self.evidence.observe("overview", list(spec["videos"]), count=5,
                                         end=min(duration, *(v["duration_seconds"] for v in spec["videos"].values())))
        self.state["observations"]["overview"] = overview
        self.checkpoint()
        return self.run()

    def resume(self, additional_turns=0):
        self.state = load(self.output / "state.json")
        if signature(self.state["spec"]) != self.state["spec_sha256"]:
            raise ValueError("Review spec changed")
        for name, key in (("instructions.json", "instructions_sha256"), ("knowledge-snapshot.json", "knowledge_sha256")):
            if sha(self.output / name) != self.state[key]:
                raise ValueError("Frozen review material changed")
        if self.state["backend"] != type(self.model).__name__ or self.state["model"] != getattr(self.model, "model", type(self.model).__name__) or self.state["reasoning_effort"] != getattr(self.model, "reasoning_effort", "unknown"):
            raise ValueError("Resume requires the same model configuration")
        for v in self.state["spec"]["videos"].values():
            if sha(v["path"]) != v["sha256"]:
                raise ValueError("Review video changed")
        self.system = load(self.output / "instructions.json")["OPERATIONS.md"]
        if self.state["spec"].get("requirements"):
            self.system += "\n\n" + load(self.output / "instructions.json")["RSI.md"]
        self.knowledge = Knowledge(self.root, self.output / "knowledge-snapshot.json")
        self.evidence = Evidence(self.state["spec"]["videos"], self.output, cache=self.state["spec"].get("frozen_critic", {}).get("evidence_cache"))
        if self.state["status"] != "complete":
            self.state["max_turns"] += additional_turns
            self.state["status"] = "running"
            return self.run()
        return self.state

    def context(self):
        spec = self.state["spec"]
        # Outcome context deliberately excludes execution prompts, paths, method names and prior scores.
        task = {k: spec[k] for k in ("request", "candidate", "duration_seconds")}
        task["question"] = spec.get("question", "")
        task["compare_to"] = spec.get("compare_to")
        if spec.get("requirements"):
            task["requirements"] = spec["requirements"]
        actual_duration = spec["videos"][spec["candidate"]]["duration_seconds"]
        task["delivery"] = {"actual_seconds": actual_duration, "expected_seconds": spec["duration_seconds"],
                            "tolerance_seconds": 0.08, "duration_valid": abs(actual_duration - spec["duration_seconds"]) <= .08,
                            "scope": "Decoded duration check; motion and content quality require visual evidence."}
        task["videos"] = {k: {field: v.get(field) for field in ("parent", "duration_seconds", "frames", "width", "height", "timing_basis")}
                          for k, v in spec["videos"].items()}
        observations = list(self.state["observations"].values())
        latest = observations[-1]
        # Calls are independent model contexts. Keep the original overview visible,
        # and carry brief attributed visual notes across changes of observation.
        selected = [observations[0]] if latest is observations[0] else [observations[0], latest]
        mapping = []
        for observation in selected:
            for frame in observation["frames"]:
                mapping.append({"attachment": len(mapping)+1, "observation_id": observation["observation_id"], **frame})
        summaries = [{k: v for k, v in o.items() if k != "frames"} for o in observations]
        payload = {"task": task, "observations": summaries, "attached_images": mapping,
                   "events": self.state["events"], "notes": self.state["notes"],
                   "knowledge_entrances": self.knowledge.browse(), "guides": ["judgment", "evidence"],
                   "assessment": self.state["assessment"], "process_opened": self.state["process_opened"],
                   "visual_memory": "Original overviews and latest observation images are attached. Earlier visual findings survive through your attributed observation notes; reopen any evidence you need to check. Coverage metadata is not itself a visual finding.",
                   "turns_remaining": self.state["max_turns"] - self.state["attempts"]}
        return json.dumps(payload, ensure_ascii=False, indent=2), mapping

    def operate(self, call, identity):
        action, args = call["action"], dict(call.get("arguments", {}))
        observation_note = call.get("observation_note") or args.pop("observation_note", None)
        if observation_note:
            if not isinstance(observation_note, str):
                raise ValueError("observation_note is brief English text about the attached evidence")
            self.state["notes"].append({"observation_id": list(self.state["observations"])[-1],
                                       "model_call": identity, "text": observation_note})
        if action == "observe":
            observation_args = dict(args)
            purpose = observation_args.pop("purpose", call.get("purpose"))
            result = self.evidence.observe(identity, **observation_args)
            if purpose:
                result["purpose"] = purpose
            self.state["observations"][identity] = result
            return {k: v for k, v in result.items() if k != "frames"}
        if action == "guide":
            if args["id"] not in {"judgment", "evidence"}:
                raise ValueError("Unknown guide")
            text = load(self.output / "instructions.json")["guides/" + args["id"] + ".md"]
            return {"id": args["id"], "origin": "versioned initial evaluation guidance", **page(text, args.get("start_line", 1))}
        if action == "browse":
            return self.knowledge.browse(args.get("id", "map"))
        if action == "search":
            return self.knowledge.search(**args)
        if action == "read":
            if not 1 <= len(args["targets"]) <= 4:
                raise ValueError("Read 1-4 targets")
            return {"materials": [self.knowledge.read(t["id"], start_line=t.get("start_line", 1), section=t.get("section")) for t in args["targets"]]}
        if action == "note":
            self.state["notes"].append({"observation_id": list(self.state["observations"])[-1],
                                       "model_call": identity, "text": args["text"]})
            return {"saved": True}
        if action == "assess":
            if self.state["assessment"] is not None:
                raise ValueError("Outcome assessment is already recorded; explain later diagnostic qualifications in finish")
            report = copy.deepcopy(args)
            if self.state["spec"].get("requirements"):
                from planner_harness.ledger import validate_review, project_findings
                report = validate_review(report, self.state["spec"]["requirements"], self.state["spec"]["candidate"], self.state["spec"]["videos"], self.state["observations"])
                report = project_findings(report, self.state["spec"]["requirements"], self.state["spec"]["candidate"], self.state["observations"], self.state["spec"]["duration_seconds"])
            report = validate_assessment(report, self.state["observations"], self.state["spec"]["videos"], self.state["spec"]["candidate"], self.state["spec"]["duration_seconds"])
            self.state["assessment"] = report
            save(self.output / "outcome.json", report)
            return {"saved": True, "scope": "Outcome assessment recorded before execution-prompt access"}
        if action == "process_context":
            if self.state["assessment"] is None:
                raise ValueError("Record an outcome assessment before reading execution prompts")
            self.state["process_opened"] = True
            return {"videos": {k: {field: v.get(field) for field in ("parent", "prompt", "provenance", "time_mapping")}
                               for k, v in self.state["spec"]["videos"].items()},
                    "scope": "Process diagnostics only. Optional Planner choices do not change user requirements."}
        if action == "finish":
            if self.state["assessment"] is None or not args.get("summary"):
                raise ValueError("Finish needs a recorded assessment and an English summary")
            if args.get("process_diagnostics") and not self.state["process_opened"]:
                raise ValueError("Read actual process context before diagnosing prompt coverage")
            if args.get("failure_types") and not self.state["process_opened"]:
                raise ValueError("Read process context before assigning failure hypotheses")
            if args.get("failure_types") and self.state["spec"].get("requirements"):
                from planner_harness.ledger import TYPES
                ids = {r["id"] for r in self.state["spec"]["requirements"]["items"]}
                if not isinstance(args["failure_types"], dict):
                    raise ValueError("Failure hypotheses map requirement IDs to tags")
                for k, values in args["failure_types"].items():
                    values = values if isinstance(values, list) else [values]
                    if k not in ids or any(v not in TYPES for v in values):
                        raise ValueError("Unknown failure hypothesis or requirement ID")
            spec = self.state["spec"]
            result = {"protocol": self.state["protocol"], "usage": "online_feedback; not independent formal benchmark scoring",
                      "original_request": spec["request"], "source_sha256": spec["videos"]["source"]["sha256"],
                      "candidate": spec["candidate"], "videos": spec["videos"], "question": spec.get("question", ""),
                      "outcome": self.state["assessment"], "feedback": args,
                      "observations": self.state["observations"], "model": self.state["model"],
                      "reasoning_effort": self.state["reasoning_effort"], "run_directory": str(self.output),
                      "instructions_sha256": self.state["instructions_sha256"], "knowledge_sha256": self.state["knowledge_sha256"]}
            result["sha256"] = signature(result)
            save(self.output / "feedback.json", result)
            self.state["status"] = "complete"
            return {"saved": True, "feedback": str(self.output / "feedback.json")}
        raise ValueError("Unknown Critic operation")

    def run(self):
        from .report import report
        try:
            while self.state["status"] == "running" and (self.state["pending"] or self.state["attempts"] < self.state["max_turns"]):
                if self.state["pending"]:
                    identity = self.state["pending"]
                    saved = load(self.output / "calls" / identity / "input.json")
                else:
                    text, images = self.context()
                    if len(text) + len(self.system) > 220000:
                        self.state["status"] = "context_limit"
                        break
                    self.state["attempts"] += 1
                    identity = f"event-{self.state['attempts']:04d}"
                    saved = {"system_prompt": self.system, "user_text": text, "images": images}
                    save(self.output / "calls" / identity / "input.json", saved)
                    self.state["pending"] = identity
                    self.checkpoint()
                if saved["system_prompt"] != self.system or any(sha(f["path"]) != f["sha256"] for f in saved["images"]):
                    raise ValueError("Model call inputs changed")
                directory = self.output / "calls" / identity
                raw_path = directory / "response.txt"
                print(f"[{self.output.name}] {identity}: Critic call, {len(saved['images'])} images", flush=True)
                if raw_path.exists():
                    raw = raw_path.read_text(encoding="utf-8")
                else:
                    if self.state["spec"].get("requirements"):
                        from planner_harness.rsi_calls import call_once
                        raw = call_once(directory, self.model, self.system, saved["user_text"], [f["path"] for f in saved["images"]], 8000)
                    else:
                        raw = self.model.predict_text(system_prompt=self.system, user_text=saved["user_text"], image_paths=[f["path"] for f in saved["images"]], max_new_tokens=8000)
                    raw_path.write_text(raw, encoding="utf-8")
                event = {"event_id": identity, "at": stamp()}
                try:
                    call = json.loads(raw)
                    event["request"] = call
                    if re.search(r"[\u3400-\u9fff]", json.dumps(call, ensure_ascii=False)):
                        raise ValueError("Use English for all Critic working text")
                    event.update(request=call, status="ok", result=self.operate(call, identity))
                except (ValueError, KeyError, TypeError, OSError) as exc:
                    event.update(status="operation_error", result={"error": str(exc)})
                self.state["events"].append(event)
                save(self.output / "events" / (identity + ".json"), event)
                self.state["pending"] = None
                self.checkpoint()
                print(f"[{self.output.name}] {identity}: {event.get('request', {}).get('action')} / {event['status']}", flush=True)
            if self.state["status"] == "running":
                self.state["status"] = "budget_exhausted"
        except Exception as exc:
            self.state["status"] = "runtime_error"
            self.state["last_error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self.checkpoint()
            report(self.output)
        return self.state


def load_feedback(path, request, videos):
    """Verify a review before exposing it to a Planner; no prior score injection."""
    data = load(path)
    if data.get("protocol") not in {"lha-online-critic-v1", "lha-online-critic-rsi-v1"} or signature({k: v for k, v in data.items() if k != "sha256"}) != data.get("sha256"):
        raise ValueError("Critic feedback signature mismatch")
    if data["original_request"] != request or data["source_sha256"] != videos["source"]["sha256"]:
        raise ValueError("Critic feedback does not match original task")
    identity_map = {}
    for identity, info in data["videos"].items():
        if identity in videos and videos[identity]["sha256"] == info["sha256"]:
            identity_map[identity] = identity
            continue
        matches = [k for k, v in videos.items() if v["sha256"] == info["sha256"] and k != "source"]
        if not matches:
            raise ValueError("Critic feedback references a video absent from the Planner task")
        if len(matches) != 1:
            raise ValueError("Identical candidate files have ambiguous task identities; keep review and task IDs consistent")
        identity_map[identity] = matches[0]
    for observation in data["observations"].values():
        for frame in observation["frames"]:
            if sha(frame["path"]) != frame["sha256"]:
                raise ValueError("Critic evidence changed")
    return {"protocol": data["protocol"], "usage": data["usage"], "identity_map": identity_map,
            "candidate": identity_map[data["candidate"]], "question": data["question"],
            "outcome": data["outcome"], "feedback": data["feedback"],
            "report_path": str(Path(path).resolve()), "sha256": data["sha256"],
            "note": "Finding references use review IDs; identity_map resolves them to current task videos."}
