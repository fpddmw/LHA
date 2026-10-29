"""Build a local, self-contained index of source clips, outputs and exact prompts."""
import argparse
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    notes_path = manifest.parent / "review_notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else {}
    labels = {"short": "短提示词", "long": "长提示词", "long_keep": "长提示词 + 具体保留约束"}
    def link(path):
        return quote(os.path.relpath(path, manifest.parent).replace(os.sep, "/"))
    def player(path):
        return f'<video controls muted playsinline preload="metadata" src="{link(path)}"></video>'
    sections = []
    for sample_id in dict.fromkeys(c["sample_id"] for c in spec["cases"]):
        cases = [c for c in spec["cases"] if c["sample_id"] == sample_id]
        cards = [f'<article><h3>原视频</h3>{player(ROOT/cases[0]["source_video"])}</article>']
        for case in cases:
            directory = manifest.parent / case["case_id"]
            result_path = directory / "result.json"
            result = json.loads(result_path.read_text()) if result_path.exists() else {}
            content = '<p>尚未生成</p>'
            if result.get("status") == "complete" and (directory/"edited.mp4").exists():
                d = result["delivery"]
                content = player(directory/"edited.mp4")
                content += f'<p>{d["seconds"]:.3f} s · {d["frames"]} 帧 · {d["fps"]:g} fps · {d["width"]}×{d["height"]}</p>'
                content += f'<a href="{link(directory/"edited.mp4")}">视频</a> · <a href="{link(result_path)}">运行记录</a>'
            content += '<details><summary>完整输入提示词</summary><pre>' + escape(case["prompt"]) + '</pre></details>'
            input_path = directory / "input.json"
            if input_path.exists():
                actual = json.loads(input_path.read_text(encoding="utf-8"))
                content += f'<p>含模型前缀共 {actual["token_count"]} tokens · <a href="{link(input_path)}">模型实际输入</a></p>'
            judge_path = directory / "judgment.json"
            if judge_path.exists():
                judged = json.loads(judge_path.read_text(encoding="utf-8"))["judgment"]
                content += '<div class="judgment"><p>风格：' + escape(judged["style_match"]["label"]) + '</p>'
                content += '<p>' + escape(str(judged["summary"])) + '</p>'
                content += '<details><summary>逐项风格与保留评价（原始单条评价）</summary>'
                for heading, key in [("要求的修改", "edits"), ("保留语义", "preservation")]:
                    content += '<h4>' + heading + '</h4><ul>'
                    for item in judged[key]:
                        content += '<li><b>' + escape(item["item"]) + ' — ' + escape(item["label"]) + '</b><br>' + escape(item["evidence"]) + '</li>'
                    content += '</ul>'
                content += '<p>' + escape('；'.join(judged["temporal_limitations"])) + '</p></details>'
                content += f'<a href="{link(judge_path)}">逐项反馈与证据</a></div>'
            else:
                content += '<p class="muted">逐项评价待完成</p>'
            cards.append('<article><h3>' + labels[case["condition"]] + '</h3>' + content + '</article>')
        note = notes.get("samples", {}).get(sample_id, {})
        review = '<p>' + escape(note.get("finding", "")) + '</p>' if note else ''
        if sample_id == "041" and (manifest.parent/"041-paired-review.json").exists():
            review += '<p><a href="041-paired-review.json">统一口径的配对复核</a> · <a href="041-writing-detail.jpg">书写工具与纸本细节对照</a></p>'
        sections.append(f'<section><h2>题目 {sample_id}</h2>' + review + '<button onclick="playGroup(this)">从头同步播放本组</button><button onclick="pauseGroup(this)">暂停本组</button><div class="grid">' + ''.join(cards) + '</div></section>')
    html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bernini 提示词探索</title>
<style>body{font:16px/1.6 system-ui,sans-serif;background:#f6f7f8;color:#182332;margin:0;padding:32px}main{max-width:1700px;margin:auto}h1{margin:0}h2{margin-top:40px}h3{font-size:16px}article{background:white;padding:16px;border:1px solid #dde2e8;border-radius:10px;min-width:0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:16px}video{width:100%;aspect-ratio:16/9;background:#111}pre{white-space:pre-wrap;font:14px/1.6 system-ui}button{padding:8px 12px;margin-right:8px;border:1px solid #adb8c6;border-radius:6px;cursor:pointer}a{color:#125f9c}.muted{color:#657183}.judgment{border-top:1px solid #dde2e8;margin-top:14px;font-size:14px}details{margin-top:12px}</style><main>
<h1>Bernini 直接提示词探索</h1><p>新版 benchmark · 4 个源视频 · 10 个提示词条件 · 每条固定 seed 42。正式题目交付前 5 秒；乒乓球题按模型要求从原 134 帧均匀取 133 帧，保持 30 fps，时长从 4.47 秒变为 4.43 秒。</p>
<p>40 步，v2v_apg，负提示词为空，关闭提示词增强。短、长提示词来自新版包；保留约束依据原视频补充。每条评价使用原片与结果各 12 张采样帧，快速运动及帧间稳定性需要结合完整视频复核。</p>
<p class="muted">单次生成用于发现问题与检查评价方式；下面是逐题反馈，尚不构成统计显著性或跨模型结论。保留观察项包含复合条件和重叠信息，其标签数量仅用于查看本题反馈；后续统计以源视频与提示词条件为单位，并单独记录无法判断的运动细节。</p>'''
    html += ''.join(sections)
    html += '''</main><script>function playGroup(b){b.closest('section').querySelectorAll('video').forEach(v=>{v.currentTime=0;v.play().catch(()=>{})})}function pauseGroup(b){b.closest('section').querySelectorAll('video').forEach(v=>v.pause())}</script></html>'''
    output = manifest.parent / "comparison.html"
    output.write_text(html, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
