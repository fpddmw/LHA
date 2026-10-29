"""A local review page with actual footage, observations and model exchanges."""
import html
import json
from pathlib import Path

from planner_harness.common import load


def report(directory):
    directory = Path(directory)
    state = load(directory / "state.json")
    def esc(value):
        return html.escape(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))
    def url(path):
        import os
        return html.escape(os.path.relpath(path, directory).replace("\\", "/"), quote=True)
    parts = ['<!doctype html><meta charset="utf-8"><title>Online Critic review</title><style>body{font:16px/1.5 system-ui;max-width:1250px;margin:30px auto;padding:0 20px;background:#f6f7fa;color:#18232c}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:16px;border:1px solid #ddd}video{width:48%;max-height:380px;background:#111}img{width:220px}details{margin:12px 0}h2{margin-top:35px}.frames{display:flex;flex-wrap:wrap;gap:8px}figure{margin:4px}figcaption{font-size:12px}</style>', '<h1>Online Critic review</h1>',
             '<p>Historical videos; this review generates no new footage. Online feedback is separate from formal evaluation.</p>',
             '<pre>' + esc({"status":state["status"],"request":state["spec"]["request"],"question":state["spec"].get("question"),"candidate":state["spec"]["candidate"]}) + '</pre>']
    for identity, video in state["spec"]["videos"].items():
        parts += [f'<h2>{esc(identity)}</h2><p>Actual parent: {esc(video.get("parent", "unknown / original"))}</p>', f'<video controls preload="metadata" src="{url(video["path"])}"></video>']
    if state["assessment"]:
        assessment = state["assessment"]
        parts += ['<h2>Outcome assessment before execution-context access</h2><p>' + esc(assessment["summary"]) + '</p>',
                  '<table style="border-collapse:collapse;width:100%"><tr><th>Area / verdict</th><th>Finding and scope</th><th>Evidence</th></tr>']
        for finding in assessment["findings"]:
            refs = ' · '.join(f'<a href="#{esc(r["observation_id"])}">{esc(r["video"])} / {esc(r["observation_id"])}</a>' for r in finding.get("evidence",[]))
            boundary = '<p>Partial boundary: '+esc(finding['partial_boundary'])+'</p>' if finding.get('partial_boundary') else ''
            parts += [f'<tr><td style="padding:12px;border:1px solid #ddd">{esc(finding["dimension"])}<br><b>{esc(finding["verdict"])}</b><br>{esc(finding["importance"])}</td><td style="padding:12px;border:1px solid #ddd">{esc(finding["claim"])}{boundary}</td><td style="padding:12px;border:1px solid #ddd">{refs}</td></tr>']
        parts += ['</table>']
        for key in ('strengths','unresolved','comparisons','ratings'):
            if assessment.get(key):
                parts += [f'<h3>{esc(key.replace("_"," ").title())}</h3><pre>{esc(assessment[key])}</pre>']
        parts += ['<details><summary>Full outcome record</summary><pre>'+esc(assessment)+'</pre></details>']
    feedback = directory / "feedback.json"
    if feedback.exists():
        parts += ['<h2>Feedback for Planner</h2>']
        for key,value in load(feedback)["feedback"].items():
            parts += [f'<h3>{esc(key.replace("_"," ").title())}</h3><pre>{esc(value)}</pre>']
    parts += ['<h2>Evidence and observations</h2>']
    for identity, observation in state["observations"].items():
        parts += [f'<details id="{esc(identity)}"><summary>{esc(identity)}: {esc(observation["scope"])}</summary><pre>{esc({k:v for k,v in observation.items() if k != "frames"})}</pre><div class="frames">']
        for f in observation["frames"]:
            parts += [f'<figure><a href="{url(f["path"])}"><img loading="lazy" src="{url(f["path"])}"></a><figcaption>{esc(f["video"])} · {f["time_seconds"]:.3f}s</figcaption></figure>']
        parts += ['</div></details>']
    parts += ['<h2>Actual operations and model calls</h2>']
    for event in state["events"]:
        identity = event["event_id"]
        parts += [f'<details><summary>{esc(identity)} · {esc(event.get("request", {}).get("action", event["status"]))}</summary><pre>{esc(event)}</pre>',
                  f'<a href="calls/{identity}/input.json">Exact model input and image hashes</a> · <a href="calls/{identity}/response.txt">Raw response</a></details>']
    parts += ['<p><a href="state.json">Complete state</a> · <a href="feedback.json">Feedback JSON</a> · <a href="instructions.json">Frozen operating manual and guides</a></p>']
    (directory / "report.html").write_text('\n'.join(parts), encoding="utf-8")
