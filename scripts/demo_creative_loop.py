"""Export a software walkthrough using saved media and scripted responses only."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from planner_harness import PlannerHarness
from planner_harness.common import load, save, sha
from critic_harness.adapter import critique
from evaluation.creative import prepare_final_request, ParateraJudge
from test_creative_loop import Scripted, ScriptedCritic, action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="out/creative_loop_refactor/demo")
    parser.add_argument("--candidate", default="out/fewshot_loop/20261031/results/out/fewshot-loop/service/tasks/fewshot_004/run/videos/v1/video.mp4")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if (output / "run/state.json").exists():
        raise SystemExit("Choose a fresh demonstration directory; existing evidence is not overwritten")
    sample = next(s for s in load(ROOT / "benchmark_data/fewshot_index.json") if s["sample_id"] == "fewshot_004")
    source = ROOT / sample["source_video"]
    candidate = (ROOT / args.candidate).resolve()
    if not candidate.is_file():
        raise SystemExit("Supply an existing saved video through --candidate; this demonstration never renders")
    planner = Scripted([
        action("read", targets=[{"id": "manual"}, {"id": "meaning"}]),
        action("search", query="science fiction material blue edge"),
        action("read", targets=[{"id": "design-expression"}, {"id": "domain-sci_fi_modern"}, {"id": "express-edits"}]),
        action("workspace", summary="Scripted demonstration: inspect object/part bindings using the existing materials."),
        action("generate", input_video="source", prompt=sample["prompt_long"]),
    ])
    h = PlannerHarness(output / "run", planner)
    h.start(source, sample["prompt_long"], mode="loop", workflow="creative_loop_v1", execution={"mode": "replay"},
            label="OFFLINE SOFTWARE DEMONSTRATION: scripted choices, existing media, no new generation or quality measurement")
    job = h.state["jobs"][h.state["pending_tool"]]
    save(h.output / "jobs" / job["id"] / "response.json", {
        "request_sha256": job["sha256"], "mode": "replay", "status": "complete",
        "payload": {"video": {"path": str(candidate), "sha256": sha(candidate)},
                    "replay_provenance": "Previously saved fewshot_004 v1, used solely to exercise collection. It was not generated from this scripted prompt.",
                    "execution": {"requested_prompt": job["payload"]["prompt"], "effective_prompt": job["payload"]["prompt"],
                                  "input_sha256": job["payload"]["input"]["sha256"], "backend": "archived_software_fixture"}}})
    h = PlannerHarness(h.output, Scripted([action("critique", video="v1", compare_to="source",
        focus="Inspect visible table structure and effect placement.", extra_checks=["Is blue glow visible on the tabletop outer rim?"])]))
    h.resume()
    review_job = h.state["jobs"][h.state["pending_tool"]]
    review_directory = h.output / "jobs" / review_job["id"]
    feedback = critique(review_job, review_directory, ROOT, model=ScriptedCritic())
    save(review_directory / "response.json", {"request_sha256": review_job["sha256"], "mode": "replay", "status": "complete", "payload": feedback})
    h = PlannerHarness(h.output, Scripted([
        action("observe", video=["source", "v1"], start=1, end=1.5, count=6),
        action("note", text="Software fixture: the Planner can inspect images after review without interrogating the Critic. No genuine judgment is asserted."),
        action("delivery_candidate", video="v1"),
        action("finish", video="v1", message="Scripted selection of archived media; not a real task delivery or quality result.")]))
    h.resume()
    packet, images = prepare_final_request(sample["prompt_long"], h.state["videos"]["source"], h.state["videos"]["v1"], output / "independent-request")
    summary = {"kind": "offline_software_demo", "live_model_calls": 0, "new_generations": 0,
               "independent_scores": 0, "online_scores": "scripted fixture values only",
               "source_sha256": sha(source), "archived_candidate_sha256": sha(candidate),
               "planner_system": str(h.output / "system-prompt.txt"),
               "first_planner_input": str(h.output / "calls/event-0001/input.json"),
               "post_generation_input": str(h.output / "calls/event-0006/input.json"),
               "post_review_input": str(h.output / "calls/event-0007/input.json"),
               "critic_request": str(review_directory / "one-shot-critic/request.json"),
               "critic_report": str(review_directory / "one-shot-critic/feedback.json"),
               "independent_request": str(output / "independent-request/evidence/request.json"),
               "independent_model": "glm5.3flash", "independent_images": len(images),
               "state": str(h.output / "state.json"), "trace": str(h.output / "report.html")}
    save(output / "summary.json", summary)
    links = "\n".join(f"- [{key}]({Path(value).as_posix()})" for key, value in summary.items()
                      if isinstance(value, str) and Path(value).is_file())
    (output / "README.md").write_text(
        "# Creative-loop software walkthrough\n\n"
        "This is an offline software demonstration with scripted model responses and saved fewshot_004 media. "
        "Zero live model calls, new generations or independent scores. All online score values are fixtures. "
        "The scripted prompt is the original long request; the archived video was produced in a different historical run.\n\n"
        "The actual harness reads the retained manuals, semantic guide, design sources and static iteration knowledge; "
        "collects an archived candidate; requests one scripted review; then lets the scripted Planner inspect source and candidate itself and select a result.\n\n"
        + links + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
