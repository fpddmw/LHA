"""One-controller durable orchestration; external adapters own long-running jobs."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil

from planner_harness.common import load, save, sha, stamp
from planner_harness.lock import RunLock
from planner_harness.video import Video


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def immutable(path, value):
    path = Path(path)
    if path.exists():
        if load(path) != value:
            raise ValueError(f"Immutable record differs: {path}")
    else:
        save(path, value)


def require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Provide nonempty {label}")


class AgentLoop:
    def __init__(self, output):
        self.output = Path(output).resolve()
        self.state = None

    def checkpoint(self, event=None):
        if event:
            self.state["events"].append({"at": stamp(), **event})
        self.state["updated_at"] = stamp()
        save(self.output / "state.json", self.state)
        self.report()

    def initialize(self, planner_run, renderer, *, mode="live", max_candidates=3, max_render_jobs=None):
        with RunLock(self.output):
            if (self.output / "state.json").exists():
                raise ValueError("Loop exists; advance the existing run")
            if mode not in {"live", "replay"} or max_candidates < 1:
                raise ValueError("Use live/replay mode and a positive candidate budget")
            max_render_jobs = max_candidates if max_render_jobs is None else max_render_jobs
            if max_render_jobs < 1:
                raise ValueError("Render job budget must be positive")
            require_text(renderer.get("backend"), "renderer backend")
            expected = renderer.get("output", {})
            if not isinstance(expected.get("frames"), int) or expected["frames"] < 1 or not isinstance(expected.get("fps"), (int, float)) or expected["fps"] <= 0:
                raise ValueError("Renderer config needs explicit output.frames and output.fps")
            run = Path(planner_run).resolve()
            prior = load(run / "state.json")
            if prior["status"] != "complete":
                raise ValueError("Initial Planner run must be complete")
            source = prior["request"]["source"]
            if sha(source["path"]) != source["sha256"]:
                raise ValueError("Original video changed")
            self.state = {"schema_version": 1, "created_at": stamp(), "mode": mode,
                          "request": prior["request"], "original": source,
                          "renderer": copy.deepcopy(renderer), "max_candidates": max_candidates,
                          "max_render_jobs": max_render_jobs, "render_jobs": 0,
                          "incumbent": None, "candidates": [], "events": [], "job": None}
            self._adopt(run, "original", "full")
            self.checkpoint({"type": "initialized", "mode": mode})
            return self._advance()

    def _load(self):
        self.state = load(self.output / "state.json")
        if sha(self.state["original"]["path"]) != self.state["original"]["sha256"]:
            raise ValueError("Original video changed")
        for candidate in self.state["candidates"]:
            if sha(candidate["proposal_path"]) != candidate["proposal_sha256"]:
                raise ValueError("Saved proposal changed")
            if candidate.get("video") and sha(candidate["video"]["path"]) != candidate["video"]["sha256"]:
                raise ValueError("Recorded candidate video changed")

    def candidate(self, identity=None):
        if identity is None:
            return self.state["candidates"][-1]
        return next(c for c in self.state["candidates"] if c["id"] == identity)

    def input_video(self, identity):
        return self.state["original"] if identity == "original" else self.candidate(identity)["video"]

    def _adopt(self, run, input_id, instruction_mode):
        prior, proposal, handoff = (load(run / name) for name in ("state.json", "proposal.json", "handoff.json"))
        if prior["status"] != "complete" or prior["request"]["source"]["sha256"] != self.state["original"]["sha256"]:
            raise ValueError("Completed child planning run must refer to the immutable original")
        if prior["request"]["text"] != self.state["request"]["text"]:
            raise ValueError("Planner request changed")
        text = (run / "prompt.txt").read_text(encoding="utf-8")
        if text != proposal["prompt"] or text != handoff["prompt"] or sha(run / "prompt.txt") != handoff["prompt_sha256"]:
            raise ValueError("Planner handoff prompt differs from the accepted proposal")
        identity = f"candidate-{len(self.state['candidates']) + 1:03d}"
        directory = self.output / "candidates" / identity
        immutable(directory / "proposal.json", proposal)
        candidate = {"id": identity, "input_id": input_id, "instruction_mode": instruction_mode,
                     "planner_run": str(run), "planner_state_sha256": sha(run / "state.json"),
                     "proposal_path": str(directory / "proposal.json"), "proposal_sha256": sha(directory / "proposal.json"),
                     "incumbent_at_creation": self.state["incumbent"], "status": "planned", "job_attempt": 1}
        self.state["candidates"].append(candidate)
        self.state.update(status="awaiting_render", job=None)

    def _job_payload(self, kind):
        candidate = self.candidate()
        proposal = load(candidate["proposal_path"])
        common = {"candidate_id": candidate["id"], "request": self.state["request"],
                  "original": self.state["original"], "proposal": proposal,
                  "input_id": candidate["input_id"], "input_video": self.input_video(candidate["input_id"]),
                  "instruction_mode": candidate["instruction_mode"]}
        if kind == "render":
            return {**common, "prompt": proposal["prompt"], "renderer": self.state["renderer"]}
        incumbent = self.candidate(self.state["incumbent"]) if self.state["incumbent"] else None
        common.update(candidate_video=candidate["video"], execution=candidate["execution"],
                      incumbent={"id": incumbent["id"], "video": incumbent["video"],
                                 "proposal": load(incumbent["proposal_path"])} if incumbent else None)
        if kind == "decide":
            common["evaluation"] = candidate["evaluation"]
            common["evaluation_sha256"] = digest(candidate["evaluation"])
            common["remaining_candidates"] = self.state["max_candidates"] - len(self.state["candidates"])
            common["remaining_render_jobs"] = self.state["max_render_jobs"] - self.state["render_jobs"]
        return common

    def _ensure_job(self, kind):
        if self.state["job"] is None:
            if kind == "render" and self.state["render_jobs"] >= self.state["max_render_jobs"]:
                self.state.update(status="stopped", stop_reason="render_job_budget")
                self.checkpoint({"type": "budget_stop"})
                return None
            candidate = self.candidate()
            job_id = f"{candidate['id']}-{kind}-{candidate['job_attempt']:02d}"
            body = {"id": job_id, "kind": kind, "mode": self.state["mode"], "payload": self._job_payload(kind)}
            request = {**body, "sha256": digest(body)}
            self.state["job"] = request
            if kind == "render":
                self.state["render_jobs"] += 1
            # Commit identity before exposing the outbox; restart recreates a missing request.
            self.checkpoint({"type": "job_created", "id": job_id})
        request = self.state["job"]
        immutable(self.output / "jobs" / request["id"] / "request.json", request)
        return request

    def _response(self, request):
        path = self.output / "jobs" / request["id"] / "response.json"
        if not path.exists():
            return None
        response = load(path)
        consumed = path.with_name("consumed.json")
        if consumed.exists() and load(consumed) != response:
            raise ValueError("Previously consumed response changed")
        if response.get("request_sha256") != request["sha256"] or response.get("mode") != self.state["mode"]:
            raise ValueError("Response is stale or has a different live/replay mode")
        if response.get("status") not in {"complete", "failed"}:
            raise ValueError("Publish a response only when complete or failed")
        if response["status"] == "failed":
            require_text(response.get("error"), "adapter error")
            self.state.update(status="failed", failure={"job": request["id"], "error": response["error"]})
            self.checkpoint({"type": "job_failed", "id": request["id"]})
            return None
        if not isinstance(response.get("payload"), dict):
            raise ValueError("Response payload must be an object")
        return response

    def _rendered(self, result):
        candidate = self.candidate()
        execution = result["execution"]
        request = self.state["job"]["payload"]
        if execution.get("requested_prompt") != request["prompt"] or execution.get("input_sha256") != request["input_video"]["sha256"]:
            raise ValueError("Renderer receipt differs from the actual requested prompt/input")
        require_text(execution.get("effective_prompt"), "effective prompt")
        require_text(execution.get("backend"), "execution backend")
        if execution["backend"] != self.state["renderer"]["backend"] or execution.get("settings") != self.state["renderer"].get("settings", {}):
            raise ValueError("Renderer backend/settings differ from the frozen request")
        if not isinstance(execution.get("prompt_transforms"), list):
            raise ValueError("Record prompt_transforms, including an empty list when none apply")
        if execution["effective_prompt"] != execution["requested_prompt"] and not execution["prompt_transforms"]:
            raise ValueError("Effective prompt changed without an explicit transformation receipt")
        if self.state["mode"] == "live":
            if execution.get("preflight") != "passed":
                raise ValueError("Live generation requires successful renderer preflight")
            for field in ("model_revision", "code_revision", "tokenizer_revision"):
                require_text(execution.get(field), field)
            count, limit = execution.get("token_count"), execution.get("token_limit")
            if type(count) is not int or type(limit) is not int or not 0 < count <= limit:
                raise ValueError("Token preflight is missing or exceeds the declared limit")
        else:
            require_text(result.get("replay_provenance"), "replay provenance")
        supplied = result["video"]
        if sha(supplied["path"]) != supplied["sha256"]:
            raise ValueError("Rendered video hash differs")
        directory = self.output / "candidates" / candidate["id"]
        video = Video(supplied["path"], directory)
        expected = self.state["renderer"]["output"]
        if video.info["frames"] != expected["frames"] or abs(video.info["fps"] - expected["fps"]) > .001:
            raise ValueError("Output frame count/FPS differs from the requested contract")
        for dimension in ("width", "height"):
            if dimension in expected and expected[dimension] != video.info[dimension]:
                raise ValueError(f"Output {dimension} differs from the requested contract")
        # Validate before collecting, so invalid media cannot poison an explicit retry.
        video.observe("technical-check", count=2)
        destination = directory / ("video" + Path(supplied["path"]).suffix.lower())
        if destination.exists():
            if sha(destination) != supplied["sha256"]:
                raise ValueError("Previously collected candidate differs")
        else:
            temporary = destination.with_suffix(destination.suffix + ".part")
            shutil.copyfile(supplied["path"], temporary)
            if sha(temporary) != supplied["sha256"]:
                raise ValueError("Video changed during collection")
            os.replace(temporary, destination)
        video.info["path"] = str(destination)
        candidate.update(video=video.info, execution=execution, status="rendered", job_attempt=1,
                         replay_provenance=result.get("replay_provenance"))
        self.state.update(status="awaiting_evaluation", job=None)

    def _evaluated(self, result):
        protocol = result.get("protocol", {})
        require_text(protocol.get("id"), "evaluation protocol ID")
        require_text(protocol.get("version"), "evaluation protocol version")
        if not isinstance(result.get("findings"), list) or not isinstance(result.get("uncertainties"), list):
            raise ValueError("Evaluation must include findings and uncertainties arrays")
        # Preserve metric names, scales, evidence and coverage exactly as the evaluator supplies them.
        self.candidate().update(evaluation=result, status="evaluated", job_attempt=1)
        self.state.update(status="awaiting_decision", job=None)

    def _decided(self, result):
        candidate = self.candidate()
        policy = result.get("policy", {})
        require_text(policy.get("id"), "selection policy ID")
        require_text(policy.get("version"), "selection policy version")
        require_text(result.get("reason"), "decision reason")
        if result.get("evaluation_sha256") != digest(candidate["evaluation"]):
            raise ValueError("Decision must identify the evaluation it used")
        selection, action = result.get("selection"), result.get("next_action")
        if selection not in {"accept", "reject", "undecided"} or action not in {"stop", "revise"}:
            raise ValueError("Choose accept/reject/undecided and stop/revise")
        new_incumbent = candidate["id"] if selection == "accept" else self.state["incumbent"]
        if action == "revise":
            if result.get("input") not in {"original", "incumbent"} or result.get("instruction_mode") not in {"full", "incremental"}:
                raise ValueError("Revision requires an explicit original/incumbent input and full/incremental mode")
            if result["input"] == "incumbent" and new_incumbent is None:
                raise ValueError("No accepted incumbent exists for this revision route")
        candidate.update(decision=result, status=selection)
        self.state.update(incumbent=new_incumbent, job=None)
        if action == "stop":
            self.state.update(status="stopped", stop_reason="decision_policy")
        elif len(self.state["candidates"]) >= self.state["max_candidates"] or self.state["render_jobs"] >= self.state["max_render_jobs"]:
            self.state.update(status="stopped", stop_reason="candidate_or_render_budget")
        else:
            self.state.update(status="awaiting_revision", revision={
                "input_id": "original" if result["input"] == "original" else new_incumbent,
                "instruction_mode": result["instruction_mode"],
                "directory": str(self.output / "planning" / f"revision-{len(self.state['candidates']):03d}"),
            })

    def _advance(self):
        kinds = {"awaiting_render": "render", "awaiting_evaluation": "evaluate", "awaiting_decision": "decide"}
        while self.state["status"] in kinds:
            request = self._ensure_job(kinds[self.state["status"]])
            if request is None:
                break
            try:
                response = self._response(request)
                if response is None:
                    break
                {"render": self._rendered, "evaluate": self._evaluated, "decide": self._decided}[request["kind"]](response["payload"])
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.state.update(status="failed", failure={"job": request["id"], "category": "invalid_response",
                                                           "error": f"{type(exc).__name__}: {exc}"})
                self.checkpoint({"type": "response_rejected", "id": request["id"], "error": str(exc)})
                raise
            # Commit validated evidence before state; a restart can safely reapply it.
            immutable(self.output / "jobs" / request["id"] / "consumed.json", response)
            self.checkpoint({"type": "job_consumed", "id": request["id"], "response_sha256": digest(response)})
        if self.state["status"] == "awaiting_revision":
            self._revision_context()
        self.report()
        return self.state

    def advance(self):
        with RunLock(self.output):
            self._load()
            return self._advance()

    def retry(self, reason):
        require_text(reason, "retry reason")
        with RunLock(self.output):
            self._load()
            if self.state["status"] != "failed":
                raise ValueError("Retry applies only to an explicitly failed adapter job")
            kind = self.state["job"]["kind"]
            self.candidate()["job_attempt"] += 1
            self.state.update(status={"render": "awaiting_render", "evaluate": "awaiting_evaluation", "decide": "awaiting_decision"}[kind], job=None)
            self.checkpoint({"type": "retry_requested", "reason": reason})
            return self._advance()

    def _revision_context(self):
        candidate, revision = self.candidate(), self.state["revision"]
        videos = {"candidate": candidate["video"]}
        if self.state["incumbent"] and self.state["incumbent"] != candidate["id"]:
            videos["incumbent"] = self.candidate(self.state["incumbent"])["video"]
        incumbent = self.candidate(self.state["incumbent"]) if self.state["incumbent"] else None
        payload = {"mode": self.state["mode"], "original_request": self.state["request"],
                   "videos": videos, "previous_proposal": load(candidate["proposal_path"]),
                   "execution": candidate["execution"], "evaluation": candidate["evaluation"],
                   "decision": candidate["decision"], "incumbent_id": self.state["incumbent"],
                   "incumbent": {"id": incumbent["id"], "proposal": load(incumbent["proposal_path"]),
                                 "execution": incumbent["execution"]} if incumbent else None,
                   "next_input": {"id": revision["input_id"], "video": self.input_video(revision["input_id"]),
                                  "instruction_mode": revision["instruction_mode"]},
                   "history": [{"id": c["id"], "input_id": c["input_id"], "status": c["status"],
                                "proposal_path": c["proposal_path"], "decision": c.get("decision")} for c in self.state["candidates"]]}
        path = Path(revision["directory"]) / "revision-context.json"
        immutable(path, payload)
        return path

    def revise(self, model, *, additional_turns=0):
        from .revision import RevisionPlannerHarness
        with RunLock(self.output):
            self._load()
            if self.state["status"] != "awaiting_revision":
                raise ValueError("No revision is pending")
            revision = self.state["revision"]
            context = self._revision_context()
            output = Path(revision["directory"])
            os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(output / "model-usage.jsonl")
            with RunLock(output):
                planner = RevisionPlannerHarness(output, model, context)
                if (output / "state.json").exists():
                    result = planner.resume(additional_turns=additional_turns)
                else:
                    result = planner.start(self.state["original"]["path"], self.state["request"]["text"],
                                           target=self.state["renderer"]["backend"], label="Outer-loop revision")
            if result["status"] == "complete":
                self._adopt(output, revision["input_id"], revision["instruction_mode"])
                self.checkpoint({"type": "revision_completed", "planner_run": str(output)})
                return self._advance()
            self.checkpoint({"type": "revision_incomplete", "planner_status": result["status"]})
            return self.state

    def report(self):
        state = self.state
        lines = ["# Agent loop run", "", f"Mode: **{state['mode']}**. State: **{state['status']}**.", "",
                 f"Incumbent: `{state['incumbent'] or 'none selected'}`.", "",
                 f"Render jobs issued: {state['render_jobs']}/{state['max_render_jobs']}. Candidate budget: {state['max_candidates']}.", "",
                 "A replay run verifies plumbing; its responses do not establish new generation or measured quality.", "",
                 "| Candidate | Generation input | Instruction mode | Selection/status |", "|---|---|---|---|"]
        for c in state["candidates"]:
            lines.append(f"| {c['id']} | {c['input_id']} | {c['instruction_mode']} | {c['status']} |")
        if state.get("job"):
            job = state["job"]
            lines += ["", f"Pending job: [{job['id']}](jobs/{job['id']}/request.json)."]
        if state.get("stop_reason"):
            lines += ["", f"Stop reason: `{state['stop_reason']}`. Stopping does not imply the task passed evaluation."]
        for c in state["candidates"]:
            proposal = load(c["proposal_path"])
            lines += ["", f"## {c['id']}", "", f"Planning record: `{c['planner_run']}`.", "", "### Submitted prompt", "", proposal["prompt"]]
            if c.get("replay_provenance"):
                lines += ["", "Replay provenance: " + c["replay_provenance"]]
            for key in ("execution", "evaluation", "decision"):
                if key in c:
                    lines += ["", f"### {key.title()}", "", "```json", json.dumps(c[key], ensure_ascii=False, indent=2), "```"]
        (self.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def publish_response(output, response):
    """Atomically publish one worker response; do not advance or start any job."""
    output = Path(output).resolve()
    with RunLock(output):
        state = load(output / "state.json")
        job = state.get("job")
        if not job or response.get("request_sha256") != job["sha256"] or response.get("mode") != state["mode"]:
            raise ValueError("Response must match the currently pending job and run mode")
        if response.get("status") not in {"complete", "failed"}:
            raise ValueError("Only complete/failed responses may be published")
        immutable(output / "jobs" / job["id"] / "response.json", response)
