"""Show source-matched baseline and model-led Planner outputs without provisional scores."""
from html import escape as h
import json
import os
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'out/planner_probe/20261029'


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def link(p):
    return quote(os.path.relpath(p,DEST).replace('\\','/'))


def player(p):
    return f'<video controls muted playsinline preload="metadata" src="{link(p)}"></video>'


def result_card(directory,label):
    target=directory/'result.json'
    result=read(target) if target.exists() else {}
    body=f'<article><h4>{h(label)}</h4>'
    if result.get('status')=='complete' and (directory/'edited.mp4').exists():
        body+=player(directory/'edited.mp4')
        d=result['delivery']
        body+=f'<p>{d["seconds"]:.3f}s · {d["frames"]} frames · {d["width"]}×{d["height"]}</p>'
        body+=f'<a href="{link(directory/"native.mp4")}">Native video</a> · <a href="{link(directory/"input.json")}">Exact input</a> · <a href="{link(target)}">Run record</a>'
    else:body+='<p class="pending">Generation or verified local transfer pending.</p>'
    return body+'</article>'


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    plans=read(DEST/'matched-plans.json')['matched']
    observations_path=DEST/'visual-observations.json'
    observations=read(observations_path) if observations_path.exists() else None
    baselines={m:read(ROOT/f'out/prompt_probe/20261029_{m}/cases.json') for m in ['bernini','ditto']}
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Planner prompt comparison</title>
<style>body{font:16px/1.6 system-ui;background:#f6f7fb;color:#172536;margin:0;padding:24px}main{max-width:1400px;margin:auto}section{margin:32px 0;border-top:2px solid #ccd4df;padding-top:18px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}article{padding:16px;background:white;border:1px solid #d4dce6;border-radius:10px}video{width:100%;background:#111;aspect-ratio:16/9}.source{max-width:650px}pre{white-space:pre-wrap;font:14px/1.6 system-ui}a{color:#175b9b}.pending{color:#966414}button{padding:8px;margin-right:8px}summary{cursor:pointer;font-weight:600}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><main>
<h1>Model-led Planner × Bernini / Ditto</h1><p>The Planner prompt is passed unchanged to both renderers. Within each renderer, source video, conditioning frames, seed 42, resolution, steps and other generation settings match the existing baseline. Bernini uses 40 steps; Ditto uses 50.</p>
<p>Evaluation metrics are being developed. No overall scores or winner claims are assigned here. The Planner's own review establishes an inspectable proposal, not generated-video quality. The 041 and 004 tasks are known integration examples; 004's knowledge reads include the previously observed tabletop-lighting issue.</p>'''
    for task in plans:
        sid=task['sample_id'];base=[c for c in baselines['bernini']['cases'] if c['sample_id']==sid]
        plan=ROOT/task['planner_run'];prompt=(plan/'prompt.txt').read_text(encoding='utf-8')
        page+=f'<section><h2>{h(sid)}</h2><p><b>User request:</b> {h(task["user_requirement"])}</p><div class="source"><h3>Original</h3>{player(ROOT/base[0]["source_video"])}</div>'
        page+='<button onclick="playAll(this)">Play this task from start</button><button onclick="pauseAll(this)">Pause</button>'
        page+=f'<h3>Model-led Planner</h3><p><a href="{link(plan/"report.html")}">Observations, knowledge reads and proposal</a> · <a href="{link(plan/"handoff.json")}">Unchanged handoff</a></p><details open><summary>Exact prompt</summary><pre>{h(prompt)}</pre></details>'
        page+='<div class="pair">'+''.join(result_card(ROOT/f'out/planner_probe/20261029_{m}'/(sid+'__planner'),m.title()) for m in ['bernini','ditto'])+'</div>'
        if observations and sid in observations['cases']:
            observation=observations['cases'][sid]
            page+=f'<details><summary>画面抽查记录（未评分）</summary><p>{h(observations["scope"])}</p><ul>'
            page+=''.join(f'<li>{h(note)}</li>' for note in observation['notes'])+'</ul>'
            page+=f'<a href="{link(DEST/observation["contact_sheet"])}">查看原片、直接提示词与 Planner 的抽帧对照</a></details>'
        for case in base:
            page+=f'<h3>Existing baseline: {h(case["condition"])}</h3><details><summary>Exact baseline prompt</summary><pre>{h(case["prompt"])}</pre></details>'
            page+='<div class="pair">'+''.join(result_card(ROOT/f'out/prompt_probe/20261029_{m}'/case['case_id'],m.title()) for m in ['bernini','ditto'])+'</div>'
        page+='</section>'
    page+='''</main><script>function playAll(b){b.closest('section').querySelectorAll('video').forEach(v=>{v.currentTime=0;v.play().catch(()=>{})})}function pauseAll(b){b.closest('section').querySelectorAll('video').forEach(v=>v.pause())}</script></html>'''
    (DEST/'comparison.html').write_text(page,encoding='utf-8')
    print(DEST/'comparison.html')


if __name__=='__main__':main()
