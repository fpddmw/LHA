"""Verify an actual Planner run's recorded inputs, reads, citations and handoff."""
import argparse
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# This verifier requires no model calls or video-generation dependencies.
import hashlib


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify(output):
    output = Path(output).resolve()
    state = read(output / "state.json")
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    check(state["status"] == "complete", "Run is not complete")
    check(not state.get("pending_event"), "Pending model call remains")
    check(digest(state["request"]["source"]["path"]) == state["request"]["source"]["sha256"], "Source video hash changed")
    check(digest(output / "system-prompt.txt") == state["system_prompt_sha256"], "Operating instructions changed")
    reads, attachments = {}, set()
    for event in state["events"]:
        identity = event["event_id"]
        call = read(output / "calls" / identity / "input.json")
        payload = json.loads(call["user_text"])
        check(payload["task"] == state["request"], f"Task changed in {identity}")
        check(call["system_prompt"] == (output / "system-prompt.txt").read_text(encoding="utf-8"), f"Instructions differ in {identity}")
        response = (output / "calls" / identity / "response.txt").read_text(encoding="utf-8")
        if event.get("request"):
            check(json.loads(response) == event["request"], f"Response differs from executed action: {identity}")
        check(read(output / "events" / f"{identity}.json") == event, f"Checkpoint/event mismatch: {identity}")
        check(set(payload["read_receipts"]) == set(reads), f"Missing or invented read receipts in model input: {identity}")
        for image in call["images"]:
            check(digest(image["path"]) == image["sha256"], f"Observation image changed: {identity}")
            attachments.add(image["path"])
        for material in event.get("result", {}).get("materials", []):
            if "read_id" not in material:
                continue
            path = ROOT / material["path"]
            check(digest(path) == material["sha256"], f"Read source changed: {material['path']}")
            lines = path.read_text(encoding="utf-8").splitlines()
            start, end = material["start_line"], material["end_line"]
            expected = "\n".join(f"{i+1}: {lines[i]}" for i in range(start-1, end))
            check(material["text"] == expected, f"Returned source passage differs: {material['read_id']}")
            reads[material["read_id"]] = material
    proposal = state.get("proposal", {})
    check(read(output / "proposal.json") == proposal, "Saved proposal differs from checkpoint")
    handoff = read(output / "handoff.json")
    check((output / "prompt.txt").read_text(encoding="utf-8") == proposal.get("prompt") == handoff["prompt"], "Prompt was altered between proposal and handoff")
    check(digest(output / "prompt.txt") == handoff["prompt_sha256"], "Prompt hash mismatch")
    for citation in proposal.get("sources", []):
        check(citation["read_id"] in reads, "Final citation has no returned source")
    for observation in state["observations"]:
        for frame in observation["frames"]:
            check(frame["path"] in attachments, f"Prepared observation never supplied: {observation['observation_id']}")
    check(html.escape(proposal.get("prompt", "")) in (output / "report.html").read_text(encoding="utf-8"), "Report does not contain exact prompt")
    usage_path = output / "model-usage.jsonl"
    usage = [json.loads(line) for line in usage_path.read_text(encoding="utf-8").splitlines() if line] if usage_path.exists() else []
    for record in usage:
        check(record["model"] == state["config"]["model"], "Transport model differs from run configuration")
        check(record["reasoning_effort"] == state["config"]["reasoning_effort"], "Transport reasoning effort differs")
    check(state["renderer_submission"]["status"] == "not_requested", "Unexpected renderer submission")
    result = {"status": "passed" if not errors else "failed", "errors": errors,
              "run": output.name, "model": state["config"]["model"], "model_calls": state["attempts"],
              "successful_transport_records": len(usage), "read_passages": len(reads),
              "unique_attached_images": len(attachments), "observation_operations": len(state["observations"]),
              "cited_passages": len(proposal.get("sources", [])), "prompt_characters": len(proposal.get("prompt", "")),
              "prompt_words": len(proposal.get("prompt", "").split()),
              "model_call_seconds": round(sum(record.get("elapsed_seconds", 0) for record in usage), 2),
              "scope": "Record integrity and traceability; no independent aesthetic or generated-video quality assessment"}
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    args = parser.parse_args()
    result = verify(args.output)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)
