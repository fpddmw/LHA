"""Review existing 041/table-tennis videos and obtain real Planner continuations without rendering."""
from pathlib import Path
import argparse
import html
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True, help="Prepared specs and imported-video manifests")
    parser.add_argument("--runtime-source", type=Path, help="Frozen src directory for reproducible demonstration imports")
    args = parser.parse_args()
    base = args.directory.resolve()
    if args.runtime_source:
        sys.path.insert(0,str(args.runtime_source.resolve()))
    from critic_harness import CriticHarness
    from critic_harness.adapter import critique
    from planner_harness import PlannerHarness
    from planner_harness.common import load, save, sha
    from planner_harness.lock import RunLock
    from vlm.codex_vlm import CodexVisionModel
    results = []
    with RunLock(base / "demonstration"):
        for name in ("041", "table_tennis"):
            spec = load(base / (name + ".spec.json"))
            output = base / name / "critic"
            os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(output / "usage.jsonl")
            with RunLock(output):
                critic = CriticHarness(output, CodexVisionModel(role="online_critic"), root=ROOT)
                state = critic.resume() if (output / "state.json").exists() else critic.start(spec, max_turns=20)
            if state["status"] != "complete":
                raise RuntimeError(f"{name}: Critic {state['status']}; continue from its saved state")
            planner_output = base / name / "planner"
            os.environ["LOW_HIGH_VLM_AUDIT_LOG"] = str(planner_output / "usage.jsonl")
            with RunLock(planner_output):
                planner = PlannerHarness(planner_output, CodexVisionModel(role="planner"), root=ROOT)
                if (planner_output / "state.json").exists():
                    state = planner.resume()
                else:
                    state = planner.start(spec["videos"]["source"]["path"], spec["request"], target="Bernini",
                        mode="loop", max_turns=16, max_generations=1,
                        execution={"critic":{"max_turns":16,"duration_seconds":spec["duration_seconds"]}},
                        imported=load(base / (name + ".imports.json")), feedback_files=[output / "feedback.json"])
                while state["status"] == "waiting_tool":
                    job = state["jobs"][state["pending_tool"]]
                    if job["kind"] != "critique":
                        # Deliberately no renderer or formal evaluator is dispatched by this demonstration.
                        break
                    directory = planner_output / "jobs" / job["id"]
                    response = {"request_sha256":job["sha256"],"mode":job["mode"],"status":"complete",
                                "payload":critique(job, directory, ROOT)}
                    save(directory / "response.json",response)
                    state = planner.resume()
            pending = state["jobs"].get(state.get("pending_tool"))
            result = {"case":name,"critic_status":"complete","planner_status":state["status"],
                      "next_operation":pending,"final":state.get("final"),"new_video_generations":0,
                      "scope":"Real Critic and Planner calls on historical videos. Pending generation is a proposal only; no renderer was called."}
            save(base / name / "continuation.json",result)
            results.append(result)
            save(base / "results.json",results)
            overview(base,results)
        before = load(base / "protected-before.json")
        changed = [p for p,h in before.items() if sha(ROOT / p) != h]
        save(base / "isolation-check.json", {"protected_file_count":len(before),"changed_files":changed,
             "scope":"Formal evaluation implementation, protocol and frozen cards. No formal output directories were written by this script."})
    print(json.dumps({"completed":len(results),"report":str(base / "report.html"),"new_generations":0}),flush=True)


def overview(base, results):
    from planner_harness.common import load
    esc = html.escape
    parts=['<!doctype html><meta charset="utf-8"><title>Critic and Planner demonstrations</title><style>body{font:16px/1.5 system-ui;max-width:1100px;margin:40px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:18px}a{color:#0563a5}</style><h1>Critic → Planner: existing-video demonstrations</h1><p>Historical source, first edit and second edit. Real model calls; no new video generation. Online findings are separate from formal benchmark scores.</p>']
    for result in results:
        name=result['case']
        feedback=load(base/name/'critic/feedback.json')
        parts += [f'<h2>{esc(name)}</h2><p><a href="{name}/critic/report.html">Original, first edit, second edit and full Critic process</a> · <a href="{name}/planner/report.html">Full Planner continuation</a></p>',
                  '<h3>Original task</h3><p>'+esc(feedback['original_request'])+'</p>',
                  '<h3>Critic outcome</h3><p>'+esc(feedback['outcome']['summary'])+'</p>',
                  '<h3>Feedback supplied to Planner</h3><pre>'+esc(json.dumps(feedback['feedback'],ensure_ascii=False,indent=2))+'</pre>']
        pending=result.get('next_operation')
        if pending and pending['kind']=='generate':
            p=pending['payload']
            parts += ['<h3>Planner chose a next generation proposal</h3><p>Input: <b>'+esc(p['input_id'])+'</b>. This request has not been sent to a renderer.</p>',
                      '<h3>Exact English prompt</h3><pre>'+esc(p['prompt'])+'</pre>']
        elif result.get('final'):
            parts += ['<h3>Planner decision</h3><pre>'+esc(json.dumps(result['final'],ensure_ascii=False,indent=2))+'</pre>']
        parts += ['<details><summary>Complete continuation record</summary><pre>'+esc(json.dumps(result,ensure_ascii=False,indent=2))+'</pre></details>']
    review=base/'review-notes.json'
    if review.exists():
        parts += ['<h2>Review and calibration limits</h2><p>The original model judgments remain intact. These notes identify boundaries for interpretation and further calibration.</p><pre>'+esc(json.dumps(load(review),ensure_ascii=False,indent=2))+'</pre>']
    parts += ['<p><a href="verification.json">Implementation checks</a> · <a href="isolation-check.json">Formal-evaluation isolation check</a> · <a href="revision.json">Visual-memory repair and preserved initial run</a></p>']
    (base/'report.html').write_text('\n'.join(parts),encoding='utf-8')


if __name__ == "__main__": main()
