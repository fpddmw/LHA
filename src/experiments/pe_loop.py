"""Fixed prompt-refinement loop over the shared renderer, Critic and selector.

The enhancer has no tool or knowledge access. Each round renders from the source.
Durable phase receipts allow recovery without repeating completed external work.
"""
from pathlib import Path
import copy
import json

from planner_harness import accounting
from planner_harness.common import load, save, sha
from planner_harness.execution import immutable, signature
from planner_harness.integrity import IntegrityError
from planner_harness.lock import RunLock
from planner_harness.resources import ResourceExhausted
from .bernini_pe import system_prompt as bernini_system_prompt

PROTOCOL = "lha-pe-critic-loop-v1"
MAX_PROMPT_REVISIONS = 2
COMPACT_PROMPT = """Shorten a video rendering prompt to fit the renderer's text encoder.
Keep the original task's defining visual changes, subjects, relations and actions.
Combine repeated descriptions and express the complete scene in compact English.
Use the supplied target word count as an editing guide, prioritizing the requested
changes and distinctive details. The renderer checks the actual encoder tokens.
Return exactly JSON {"prompt": "..."}.
"""


class PromptLengthRefused(RuntimeError):
    """A recorded tokenizer refusal before any GPU generation was submitted."""

    def __init__(self, details):
        self.details = details
        super().__init__("Rendering prompt exceeds the text encoder capacity")


class RecordedInterruption(RuntimeError):
    """Explicit cached settlement of an already recorded interrupted phase."""


def compact_prompt(topic, prompt, details, directory, model, scope, *, backend="bernini"):
    from planner_harness.model_call import call_text
    from planner_harness.json_output import decode_object
    from planner_harness.ledger import english
    from .render_profiles import prompt_guidance

    directory = Path(directory)
    count, limit = details.get("token_count"), details.get("token_limit", 512)
    ratio = min(.85, max(.1, (limit - 32) / count)) if count else .8
    packet = {"original_request": topic["request"], "prompt": prompt,
              "target_words": max(1, int(len(prompt.split()) * ratio)),
              "renderer": prompt_guidance(backend), "refusal": details}
    immutable(directory / "revision-input.json", packet)

    def produce():
        accounting.check_task(scope)
        raw = call_text(directory / "call", model, COMPACT_PROMPT,
                        json.dumps(packet, ensure_ascii=False), [], attempts=1)
        answer = decode_object(raw)
        if set(answer) != {"prompt"} or not isinstance(answer["prompt"], str) or not answer["prompt"].strip():
            raise ValueError("Prompt compaction requires one nonempty English prompt")
        english(answer["prompt"])
        return answer["prompt"]

    return _completed(directory / "prompt.json", produce)


SYSTEM_PROMPT = bernini_system_prompt()


# Port the grounded-instruction writing from the Ditto adapted-v2 handoff to
# the shared loop's eight-frame evidence, JSON response and Critic history.
DITTO_SYSTEM_PROMPT = """You rewrite editing instructions for Ditto V2V.
Use the user's original request, chronological source frames and any recorded
Critic feedback to write one complete English editing paragraph.

Begin with the requested transformation in a direct imperative: Transform,
Render, Restyle, Change, Replace, Add or Remove as appropriate. Follow with
concrete editing clauses grounded in visible subjects, surfaces, garments,
objects and spatial relationships. Describe how to edit this source video.

For a short global style or scene request, resolve its visual realization with
two to four salient, coordinated changes on visible elements. Specify materials,
surface treatments, characteristic shapes, palette, clothing or architectural
decoration that express the requested style. Bind each detail to an object or
region. For clay, textile, paper, ceramic or painting, explain how subjects and
environment take that medium throughout the clip. For a target setting or design
period, coordinate architecture, furniture, clothing and activity as appropriate
to the request. Lighting supports these concrete material and scene changes.

For a detailed request, retain every requested object, attribute, addition,
removal, quantity, relation and explicit preservation requirement. Organize these
requirements clearly and add realization details that support them. For a local
edit, name the visible target and its new state precisely, use observable location
when useful, and keep the surrounding scene consistent. Match the requested scope;
addition, removal and replacement each describe a different operation.

Carry forward recognizable subjects, movement, interactions and camera behavior
that serve the target. When the requested world or activity changes, adapt the
roles, prop functions and actions to make that target coherent. A material restyle
can change surfaces and contours. Use one compact, task-specific preservation
clause for the source relationships that matter. Choose visible, relevant details
from this source and this request.

On later rounds, turn the previous prompts, descriptive Critic findings and
supplied visual evidence into concrete changes to the editing instruction.
Retain effective choices and revise the objects, attributes or relations behind
the reported problem. Each render starts from the original video; write the full
editing instruction for that source, including the desired changes already found.

Use a compact, actionable paragraph, typically 40-90 English words for a short
global request. A simple local edit can be shorter; a detailed request can be
longer to retain all its requirements. These are writing guides. Ditto accepts
512 text-encoder tokens and encodes the editing instruction directly.
Return exactly JSON {"prompt": "..."}. The paragraph contains the editing
instruction itself. You have no tools or knowledge library. Use the original
request for this task and the supplied online evidence, with qualitative findings
guiding revisions.
"""


def system_prompt(backend="bernini"):
    from .render_profiles import backend as resolve_backend
    name = resolve_backend({"backend": backend})
    return SYSTEM_PROMPT if name == "bernini" else DITTO_SYSTEM_PROMPT


def configuration(backend="bernini"):
    return {"protocol": PROTOCOL, "prompt_sha256": signature({"text": system_prompt(backend)}),
            "source_frames": 8, "input_policy": "original_source_every_round",
            "review_mode": "critic", "model_role": "planner", "knowledge_access": False}


def diagnostics(feedback):
    report = feedback.get("report", {})
    return {k: report[k] for k in ("summary", "findings", "limitations") if k in report}


def rewrite(topic, directory, model, history, *, backend="bernini"):
    """One durable enhancement call, using only recorded online evidence."""
    from planner_harness.video import Video
    from planner_harness.model_call import call_text
    from planner_harness.json_output import decode_object
    from planner_harness.ledger import english
    directory = Path(directory)
    source = Video(topic["source_info"]["path"], directory / "source")
    observation = source.observe("pe-source", count=configuration(backend)["source_frames"])
    images, evidence = [], []
    for frame in observation["frames"]:
        images.append(frame["path"])
        evidence.append({"id": "source:" + str(frame["frame_index"]), "video_id": "source",
                         "timestamp_seconds": frame["timestamp_seconds"], "attachment": len(images)})
    # Reuse the latest Critic's actual evidence; historical rounds keep their text.
    for frame in history[-1]["feedback"].get("evidence", []) if history else []:
        path = frame.get("path")
        if not path:
            continue
        if not frame.get("sha256") or sha(path) != frame["sha256"]:
            raise IntegrityError("PE feedback image changed")
        if path in images:
            continue
        images.append(path)
        evidence.append({"id": frame["id"], "video_id": frame["video_id"],
                         "timestamp_seconds": frame.get("timestamp_seconds"), "attachment": len(images)})
    packet = {"original_request": topic["request"], "track": topic["prompt_form"],
              "source": {k: topic["source_info"].get(k) for k in ("sha256", "frames", "fps", "duration_seconds")},
              "round": len(history) + 1, "evidence": evidence,
              "latest_feedback_candidate_id": history[-1]['candidate']['id'] if history else None,
              "history": [{"candidate_id": row["candidate"]["id"], "prompt": row["prompt"],
                           "feedback": diagnostics(row["feedback"])} for row in history]}
    raw = call_text(directory / "call", model, system_prompt(backend),
                    json.dumps(packet, ensure_ascii=False), images, attempts=1)
    answer = decode_object(raw)
    if set(answer) != {"prompt"} or not isinstance(answer["prompt"], str) or not answer["prompt"].strip():
        raise ValueError("PE enhancement requires one nonempty prompt")
    english(answer["prompt"])
    return answer["prompt"]


def _completed(path, produce):
    """Commit one phase; lower-level adapters own provider/GPU recovery."""
    if path.exists():
        record = load(path)
        if signature(record["value"]) != record["sha256"]:
            raise IntegrityError("PE phase receipt changed")
        return record["value"]
    value = produce()
    immutable(path, {"value": value, "sha256": signature(value)})
    return value


def execute(topic, batch, runtime, directory, scope):
    """Return selected + all candidates; unfinished feedback remains recoverable."""
    directory = Path(directory)
    from .render_profiles import backend
    binding = {"configuration": configuration(backend(batch)), "source_sha256": topic["source_sha256"],
               "request": topic["request"], "track": topic["prompt_form"],
               "models": batch.get("models"), "planner": batch["planner"],
               "critic": batch.get("critic"), "profile_sha256": batch["profile_sha256"],
               "generation": batch["generation"], "native_output": topic["native_output"],
               "renderer": batch.get("renderer_identity"), "seed_sequence": batch["seed_sequence"],
               "max_generations": batch["max_generations"], "resource_policy": batch.get("resource_policy"),
               "selection": batch["selection"]}
    with RunLock(directory / "loop-owner"):
        immutable(directory / "loop.json", binding)
        if (directory / "complete.json").exists():
            return _completed(directory / "complete.json", lambda: None)
        history, candidates, reviews = [], [], []
        selected, decision, stop = 0, None, None
        stop_kind = "deadline_delivery"
        phase, number = "enhance", 0
        try:
            for number in range(batch["max_generations"]):
                folder = directory / "rounds" / f"{number + 1:04d}"
                phase = "enhance"
                def enhance():
                    accounting.check_task(scope)
                    return runtime.refine(topic, folder / "enhance", scope, history)
                prompt = _completed(folder / "prompt.json", enhance)
                phase = "render"
                def render():
                    accounting.check_task(scope)
                    seed = batch["seed_sequence"]["start"] + number * batch["seed_sequence"]["step"]
                    value = runtime.render(topic, "pe-loop", prompt, seed, number, scope)
                    return {**value, "id": "v" + str(number + 1), "prompt": value.get("prompt", prompt)}
                candidate = _completed(folder / "candidate.json", render)
                if sha(candidate["video"]["path"]) != candidate["video"]["sha256"]:
                    raise IntegrityError("PE candidate video changed")
                candidates.append(candidate)
                phase = "review"
                def review():
                    accounting.check_task(scope)
                    feedback = runtime.review(topic, candidate, folder / "review", scope)
                    summary = feedback.get("report", {}).get("summary")
                    if not isinstance(summary, str) or not summary.strip():
                        raise ValueError("PE round needs a completed descriptive Critic report")
                    return feedback
                feedback = _completed(folder / "feedback.json", review)
                reviews.append(feedback)
                phase = "select"
                def choose():
                    if len(candidates) == 1:
                        return [0, {"policy": batch["selector"], "selected_index": 0,
                                    "reason": "Only one completed candidate is available", "model_called": False}]
                    accounting.check_task(scope)
                    return runtime.choose(topic, candidates, reviews, folder / "selection", scope)
                selected, decision = _completed(folder / "choice.json", choose)
                if type(selected) is not int or not 0 <= selected < len(candidates):
                    raise IntegrityError("PE selector returned an unknown candidate")
                history.append({"prompt": candidate["prompt"], "candidate": candidate, "feedback": feedback})
                save(directory / "progress.json", {"round": number + 1, "phase": "reviewed",
                                                     "selected": candidates[selected]["id"]})
        except ResourceExhausted as exc:
            stop = str(exc)
            if not candidates:
                raise
        except PromptLengthRefused as exc:
            if not candidates:
                raise
            stop = "Prompt length remains over capacity after bounded revisions"
            stop_kind = "prompt_limit_delivery"
            save(directory / "prompt-limit-stop.json", exc.details)
        except accounting.ExternalExecutionUnknown as exc:
            if phase != "select" or decision is None:
                save(directory / "progress.json", {"round": number + 1, "phase": phase,
                     "status": "awaiting_recovery", "error_type": type(exc).__name__, "reason": str(exc)})
                raise
            stop = str(exc)
            stop_kind = "selection_unavailable_delivery"
            save(directory / "selection-stop.json", {"round": number + 1,
                 "reason": stop, "retained_candidate": candidates[selected]["id"],
                 "call": str(folder / "selection/call")})
        except RecordedInterruption as exc:
            if decision is None:
                raise
            stop = str(exc)
            stop_kind = "interrupted_delivery"
        except Exception as exc:
            save(directory / "progress.json", {"round": number + 1, "phase": phase,
                 "status": "awaiting_recovery", "error_type": type(exc).__name__, "reason": str(exc)})
            raise
        # Budget settlement never calls a model or turns an unreviewed candidate
        # into a claimed quality improvement. Keep the last committed choice.
        decision = decision or {"policy": batch["selector"], "selected_index": 0,
                                "reason": "No selection completed; retain the first completed candidate", "model_called": False}
        for i, candidate in enumerate(candidates):
            candidate["roles"] = (["first"] if i == 0 else []) + (["last"] if i == len(candidates) - 1 else []) + (["selected"] if i == selected else [])
        selection = {**decision, "requested_n": batch["max_generations"], "completed": len(candidates),
                     "reviewed": len(reviews), "effective_generation_count": len(candidates),
                     "stop": stop, "candidate_ids": [c["id"] for c in candidates],
                     "review_sha256": [signature(r) for r in reviews]}
        operations = accounting.load_ledger(scope['root'])['operations'].values()
        selection['actual_submitted'] = sum(r['topic'] == scope['topic'] and r['lane'] == scope['lane']
            and r['kind'] == 'render' and r['status'] != 'not_submitted' for r in operations)
        immutable(directory / "selection.json", selection)
        chosen = copy.deepcopy(candidates[selected])
        chosen.update(actual_generations=len(candidates), delivery_kind=stop_kind if stop else "selected",
                      planner_confirmed=False, reviews=selection["review_sha256"])
        result = {"candidate": chosen, "candidates": candidates, "partial": bool(stop)}
        return _completed(directory / "complete.json", lambda: result)
