from __future__ import annotations

import html
import json
import os
from pathlib import Path

from .common import load


def report(output):
    output = Path(output)
    state = load(output / "state.json")
    continuous = state["config"].get("mode", "plan") == "loop"
    boundary = ("Continuous task: actual tool jobs, imported material and collected outputs are recorded. A selected result is not an independent quality measurement." if continuous else "Planning-only task. No video generation was requested or performed.")
    observations = state["observations"] + state.get("revision_context", {}).get("overviews", [])
    revision_mode = state.get("revision_context", {}).get("mode")
    mode_note = f"Outer-loop mode: {revision_mode}. Replay inputs and scripted responses are not new generation or quality evidence." if revision_mode == "replay" else ""
    lines = ["# Planner run record", "", f"Status: **{state['status']}**", "",
             boundary, "",
             "## Task", "", state["request"]["text"], "",
             f"Source: [{Path(state['request']['source']['path']).name}]({Path(state['request']['source']['path']).as_posix()})", "",
             "Model: `" + state["config"]["model"] + "`, reasoning: `" + state["config"]["reasoning_effort"] + "`.", "",
             "## Observations actually supplied", ""]
    if mode_note:
        lines += [mode_note, ""]
    for observation in observations:
        lines += [f"### {observation['observation_id']} ({observation.get('video_id', 'original')})", "", observation["scope"], ""]
        for frame in observation["frames"]:
            lines += [f"Frame {frame['frame_index']}, {frame['timestamp_seconds']:.3f} s, crop: {frame['crop']}", "",
                      f"![Source observation]({Path(frame['path']).as_posix()})", ""]
    lines += ["## Actual operations and visible decisions", ""]
    html_events = []
    for event in state["events"]:
        request = event.get("request", {})
        lines += [f"### {event['event_id']}: {request.get('action', 'invalid response')}", "", request.get("purpose", ""), ""]
        if request.get("workspace"):
            lines += ["Working-state update:", "", "```json", json.dumps(request["workspace"], ensure_ascii=False, indent=2), "```", ""]
        lines += ["Requested operation:", "", "```json", json.dumps(request.get("arguments", {}), ensure_ascii=False, indent=2), "```", "",
                  f"Result: {event['status']}. [Complete returned result](events/{event['event_id']}.json) · [Exact model input](calls/{event['event_id']}/input.json) · [Exact model response](calls/{event['event_id']}/response.txt)", ""]
        for material in event.get("result", {}).get("materials", []):
            if "read_id" in material:
                lines += [f"- `{material['read_id']}`: `{material['path']}`, lines {material['start_line']}–{material['end_line']}; next line: {material['next_line']}.", ""]
        html_events.append(f"<details><summary>{html.escape(event['event_id'] + ': ' + str(request.get('action')))} — {html.escape(request.get('purpose', ''))}</summary><pre>{html.escape(json.dumps(event, ensure_ascii=False, indent=2))}</pre></details>")
    proposal = state.get("proposal", {})
    prompt_records = [{"job_id": job["id"], "input_video": job["payload"]["input_id"],
                       "prompt": job["payload"]["prompt"]} for job in state.get("jobs", {}).values() if job["kind"] == "generate"]
    if prompt_records:
        if state["config"].get("rsi"):
            for row in prompt_records:
                row["intent"] = state["jobs"][row["job_id"]]["payload"].get("intent")
        lines += ["## Exact generation requests", "", "```json", json.dumps(prompt_records, ensure_ascii=False, indent=2), "```", ""]
    if state["config"].get("rsi"):
        lines += ["## Task learning ledger", "", "```json", json.dumps(state.get("task_memory", {}), ensure_ascii=False, indent=2), "```", ""]
    for field, title in [("understanding", "Final understanding"), ("proposal", "Selected visual proposal"), ("prompt", "Exact English prompt prepared for execution"), ("self_review", "Model's submission review")]:
        lines += ["## " + title, "", proposal.get(field, "No accepted submission yet."), ""]
    lines += ["## Knowledge used in the submitted proposal", "", "```json", json.dumps(proposal.get("sources", []), ensure_ascii=False, indent=2), "```", "",
              "## Unresolved points", "", "```json", json.dumps(proposal.get("unresolved", []), ensure_ascii=False, indent=2), "```", "",
              "## Execution boundary", "", boundary, ""]
    html_videos = []
    lines += ["## Working notes", "", state.get("notes", ""), "", "## Task videos", ""]
    for identity, video in state.get("videos", {}).items():
        relative = Path(os.path.relpath(video["path"], output)).as_posix()
        lines += [f"### {identity}", "", f"[Video]({Path(video['path']).as_posix()})", "", "```json", json.dumps(video, ensure_ascii=False, indent=2), "```", ""]
        html_videos.append(f'<article><h3>{html.escape(identity)}</h3><video controls muted playsinline preload="metadata" style="width:100%;max-width:600px" src="{html.escape(relative, quote=True)}"></video><details><summary>Input, provenance and execution</summary><pre>{html.escape(json.dumps(video,ensure_ascii=False,indent=2))}</pre></details></article>')
    lines += ["## Final selection", "", "```json", json.dumps(state.get("final"), ensure_ascii=False, indent=2), "```", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    def image_tag(frame):
        relative = Path(os.path.relpath(frame["path"], output)).as_posix()
        return f'<figure><img src="{html.escape(relative, quote=True)}"><figcaption>{frame["timestamp_seconds"]:.3f}s · frame {frame["frame_index"]}</figcaption></figure>'
    gallery = "".join("<h3>" + html.escape(o["observation_id"] + " (" + o.get("video_id", "original") + ")") + "</h3><div class=frames>" + "".join(image_tag(f) for f in o["frames"]) + "</div>" for o in observations)
    sections = "".join(f"<h2>{title}</h2><pre>{html.escape(proposal.get(field, 'No accepted submission yet.'))}</pre>" for field, title in [("understanding", "Understanding"), ("proposal", "Visual proposal"), ("prompt", "Exact English prompt"), ("self_review", "Submission review")])
    if continuous and not proposal:
        sections = ""
    sections += "<h2>Exact generation requests</h2><pre>" + html.escape(json.dumps(prompt_records, ensure_ascii=False, indent=2)) + "</pre>" if prompt_records else ""
    if state["config"].get("rsi"):
        sections += "<h2>Task learning ledger</h2><pre>" + html.escape(json.dumps(state.get("task_memory", {}), ensure_ascii=False, indent=2)) + "</pre>"
    body = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Planner run</title>
<style>body{{font:16px system-ui;max-width:1200px;margin:35px auto;padding:0 20px;background:#f6f7f9;color:#172331}}h1,h2{{color:#123b56}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:16px;border-radius:8px}}.frames{{display:flex;flex-wrap:wrap;gap:12px}}figure{{margin:0;max-width:360px}}img{{width:100%;border-radius:6px}}figcaption{{font-size:13px}}details{{background:white;margin:10px 0;padding:14px;border-radius:8px}}summary{{cursor:pointer;font-weight:600}}</style>
<h1>Planner run: {html.escape(output.name)}</h1><p>Status: <b>{html.escape(state['status'])}</b>. {html.escape(boundary)}</p>
<p>{html.escape(mode_note)}</p><h2>Request</h2><pre>{html.escape(state['request']['text'])}</pre><h2>Observed video frames</h2>{gallery}
<h2>Actual operations and returned knowledge</h2>{''.join(html_events)}{sections}
<h2>Working notes</h2><pre>{html.escape(state.get('notes',''))}</pre>
<h2>Task videos</h2>{''.join(html_videos)}<h2>Final selection</h2><pre>{html.escape(json.dumps(state.get('final'),ensure_ascii=False,indent=2))}</pre>
<h2>Sources used</h2><pre>{html.escape(json.dumps(proposal.get('sources',[]),ensure_ascii=False,indent=2))}</pre>
<h2>Unresolved</h2><pre>{html.escape(json.dumps(proposal.get('unresolved',[]),ensure_ascii=False,indent=2))}</pre>
<p>{html.escape(boundary)} <a href="state.json">Full checkpoint</a> · <a href="report.md">Markdown record</a></p></html>'''
    (output / "report.html").write_text(body, encoding="utf-8")
