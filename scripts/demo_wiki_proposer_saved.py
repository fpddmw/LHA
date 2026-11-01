"""Inspectable Wiki/proposer walkthrough: real archived evidence, scripted replies."""
import html
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "src"))
from planner_harness.common import load,save,sha
from planner_harness.knowledge import Knowledge
from planner_harness.rsi_data import propose,verify_seal
from planner_harness.rsi_support import experience_digest


class Scripted:
    model="scripted-wiki-interface-demonstration"
    reasoning_effort="none"
    def __init__(self, actions):
        self.actions=iter(actions);self.calls=0
    def predict_text(self,**kwargs):
        self.calls+=1
        return json.dumps(next(self.actions))


def main():
    output=ROOT / "out/wiki_proposer/20261031"
    feedback=verify_seal(load(output / "feedback/bernini_027_after_v1.json"))
    decision=feedback["samples"][0]["decision_id"]
    run,event=decision.split("/")
    model=Scripted([
        {"action":"read_knowledge","arguments":{"id":"wiki-scene-identity"}},
        {"action":"read_knowledge","arguments":{"id":"case-bernini-027-after-v1"}},
        {"action":"view_evidence","arguments":{"id":run,"decision":event,"videos":["source","v1"],"frames_per_video":3}},
        {"action":"read_feedback","arguments":{"index":0}},
        {"summary":"Scripted demonstration ends with no proposed revision.","changes":[],"limitations":["Actions are authored software fixtures; no live model judgment or efficacy measurement."],
         "evidence_requests":["A real model must assess the task-dependent severity disagreement before any live outcome comparison."]}])
    demo=ROOT / "knowledge/staged/wiki-interface-demo-20261031-v2"
    result=propose(ROOT / "out/rsi_review_remediation/20261031/development-final.json",demo,model,root=ROOT,feedback=[feedback])
    knowledge=Knowledge(ROOT)
    rows=[r for r in knowledge.experiences if r.get("kind") in {"concept","experiment_case","knowledge_map"}]
    snapshot={"scope":"Actual tool returns and exact model-facing instructions, with explicitly scripted model replies.",
              "planner_entrances":knowledge.overview(),"experience_digest":experience_digest(knowledge,"bernini"),
              "proposer_initial_call":load(demo / "model-calls/001/single-call.json"),
              "proposer_with_images":load(demo / "model-calls/004/single-call.json"),
              "reading_trace":load(demo / "proposal-reading.json")}
    save(output / "model-visible.json",snapshot)
    sections=[]
    def text_block(text):
        safe=html.escape(text)
        safe=re.sub(r"\[\[([\w.-]+)(?:\|([^\]]+))?\]\]",lambda m:'<a href="#'+m[1]+'">'+(m[2] or m[1])+'</a>' if m[1] in knowledge.items else m[0],safe)
        return '<pre class="prose">'+safe+'</pre>'
    for row in rows:
        sections.append('<section id="'+row['id']+'"><h2>'+html.escape(row['title'])+'</h2>'+text_block(knowledge.document(row)['text']))
        for asset in row.get('assets',[]):
            path=ROOT / asset['path']
            sections.append('<div id="'+asset['id']+'">')
            if path.suffix=='.jpg':
                relative='../../../'+asset['path']
                sections.append('<figure><img src="'+relative+'"><figcaption>'+html.escape(asset.get('title',asset['id']))+'</figcaption></figure>')
            else:
                sections.append('<details><summary>Complete recorded task, prompts and feedback</summary>'+text_block(path.read_text(encoding='utf-8'))+'</details>')
            sections.append('</div>')
        sections.append('</section>')
    # Stable links into the existing library remain inspectable from this local report.
    linked={link['id'] for r in rows for link in knowledge.read(r['id'])['links'] if link['available']}
    included={r['id'] for r in rows}|{a['id'] for r in rows for a in r.get('assets',[])}
    for identity in sorted(linked-included):
        row=knowledge.items[identity]
        sections.append('<section id="'+identity+'"><details><summary>'+html.escape(row['title'])+'</summary>'+text_block(knowledge.document(row)['text'])+'</details></section>')
    nav=' '.join('<a href="#'+r['id']+'">'+html.escape(r['title'])+'</a>' for r in rows)
    header='''<!doctype html><meta charset="utf-8"><title>Wiki and proposer implementation review</title>
<style>body{font:17px/1.65 system-ui;max-width:1080px;margin:35px auto;padding:0 24px;color:#243348;background:#f7f8fa}nav{display:flex;gap:15px;flex-wrap:wrap}section{background:white;padding:24px;margin:24px 0;border:1px solid #d8dfe9;border-radius:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}details pre{font:13px/1.5 monospace}img{width:100%;max-width:800px}a{color:#1556a0}summary{cursor:pointer;font-weight:600}</style>
<h1>Wiki and proposer implementation review</h1><p>2026-10-31. Human-assisted concepts and real archived cases. The interface demonstration uses scripted responses: zero live model calls, zero renderer calls, no automatic knowledge publication.</p>
<p><a href="model-visible.json">Exact model-visible packets</a> · <a href="implementation-receipt.json">Verification receipt</a></p>'''
    call=snapshot['proposer_initial_call']['packet']
    sections.append('<section><h2>Exact proposer instructions</h2>'+text_block(call['system_prompt'])+'<details><summary>Actual scripted tool sequence and returned evidence</summary>'+text_block(json.dumps(snapshot['reading_trace'],indent=2))+'</details></section>')
    report=output / 'review.html';report.write_text(header+'<nav>'+nav+'</nav>'+''.join(sections),encoding='utf-8')
    save(output / 'demo-receipt.json',{'status':result['status'],'scripted_calls_in_artifact':5,'new_scripted_calls':model.calls,
         'paid_model_calls':0,'renderer_calls':0,'publication':'none','model_visible_sha256':sha(output / 'model-visible.json'),
         'attached_frame_count':len(snapshot['proposer_with_images']['packet']['images']),'report_sha256':sha(report)})


if __name__=='__main__':
    main()
