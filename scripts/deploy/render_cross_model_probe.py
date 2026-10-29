"""Render source, Bernini and Ditto clips with matched-protocol item judgments."""
import argparse
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
LABELS = {"short": "短提示词", "long": "详细提示词", "long_keep": "详细提示词＋保留要求",
          "clear": "清楚", "partial": "部分", "absent": "未出现", "unjudgeable": "无法判断",
          "done": "完成", "not_done": "未完成", "kept": "保留", "changed": "改变",
          "high": "高", "medium": "中", "low": "低"}
TITLES = {"027": "城市 → 蚀刻画", "041": "人物书写 → 儿童绘本",
          "fewshot_004": "乒乓球 → 太空场景", "024": "车内通话 → 故障艺术"}


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ditto", type=Path, required=True)
    p.add_argument("--bernini", type=Path, required=True)
    args = p.parse_args()
    manifests = {"Bernini": args.bernini.resolve(), "Ditto": args.ditto.resolve()}
    specs = {k: read(v) for k, v in manifests.items()}
    dest = args.ditto.resolve().parent
    notes = read(dest / "cross-model-review.json", {})

    def link(path):
        return quote(os.path.relpath(path, dest).replace(os.sep, "/"))

    def player(path):
        return f'<video controls muted playsinline preload="metadata" src="{link(path)}"></video>'

    def text(value):
        return escape(str(value))

    def card(model, case):
        folder = manifests[model].parent / case["case_id"]
        result = read(folder / "result.json", {})
        body = '<h4>' + model + '</h4>'
        if result.get("status") == "complete" and (folder / "edited.mp4").exists():
            d = result["delivery"]
            body += player(folder / "edited.mp4")
            body += f'<p>{d["seconds"]:.3f} 秒 · {d["fps"]:g} fps · {d["frames"]} 帧 · {d["width"]}×{d["height"]}</p>'
            body += f'<p><a href="{link(folder / "edited.mp4")}">打开视频</a> · <a href="{link(folder / "result.json")}">运行记录</a> · <a href="{link(folder / "input.json")}">实际模型输入</a></p>'
        else:
            body += '<p class="pending">生成待完成</p>'
        judged = read(folder / "judgment_v3.json")
        if judged:
            assert judged["output_sha256"] == result["output_sha256"]
            j = judged["judgment"]
            body += '<p><b>整体风格：' + LABELS[j["style_match"]["label"]] + '</b>。' + text(j["style_match"]["evidence"]) + '</p>'
            body += '<p>' + text(j["summary"]) + '</p>'
            for heading, key in (("修改要求逐项评价", "edits"), ("语义保留逐项评价", "preservation")):
                body += '<details open><summary>' + heading + '</summary><table><thead><tr><th>观察项</th><th>判断与证据</th></tr></thead><tbody>'
                for row in j[key]:
                    required = '（风格观察线索）' if key == "edits" and not row.get("explicitly_required", True) else ''
                    times = '、'.join(f'{t:g}' for t in row.get("times_seconds", []))
                    body += '<tr><td>' + text(row["item"]) + required + '</td><td><b>' + LABELS[row["label"]] + '</b> · ' + text(row["evidence"])
                    body += '<small>输出时间：' + text(times or '未定位') + ' 秒；置信度：' + LABELS.get(row.get("confidence", ""), "未提供") + '</small></td></tr>'
                body += '</tbody></table></details>'
            body += '<p class="muted">时序证据范围：' + text('；'.join(j["temporal_limitations"])) + '</p>'
            body += f'<a href="{link(folder / "judgment_v3.json")}">完整评价 JSON</a> · <a href="{link(folder / "judge_provenance_v3.json")}">评价输入与帧对应</a>'
        else:
            body += '<p class="pending">统一口径逐项评价待完成</p>'
        return '<article>' + body + '</article>'

    sections = []
    for sample in dict.fromkeys(c["sample_id"] for c in specs["Ditto"]["cases"]):
        cases = [c for c in specs["Ditto"]["cases"] if c["sample_id"] == sample]
        body = '<section><h2>' + text(TITLES[sample]) + ' · ' + sample + '</h2>'
        body += '<div class="source"><h3>原视频</h3>' + player(ROOT / cases[0]["source_video"]) + '</div>'
        note = notes.get("samples", {}).get(sample)
        if note:
            body += '<div class="finding"><b>跨模型发现</b><p>' + text(note.get("finding", "")) + '</p>'
            for item in note.get("comparisons", []):
                body += '<p>' + text(item) + '</p>'
            body += '</div>'
        else:
            body += '<p class="pending">跨模型结论待完成生成、评价与配对复核后填写。</p>'
        body += '<button onclick="playGroup(this)">本题全部视频从头播放</button><button onclick="pauseGroup(this)">暂停本题</button>'
        for case in cases:
            counterpart = next(c for c in specs["Bernini"]["cases"] if c["case_id"] == case["case_id"])
            assert case["prompt"] == counterpart["prompt"] and case["source_video_sha256"] == counterpart["source_video_sha256"]
            body += '<h3>' + LABELS[case["condition"]] + '</h3><details><summary>完整提示词（两个模型使用同一用户文本）</summary><pre>' + text(case["prompt"]) + '</pre></details>'
            body += '<div class="pair">' + card("Bernini", counterpart) + card("Ditto", case) + '</div>'
        sections.append(body + '</section>')
    metadata = []
    for model, spec in specs.items():
        completed = sum(read(manifests[model].parent / c["case_id"] / "result.json", {}).get("status") == "complete"
                        and (manifests[model].parent / c["case_id"] / "edited.mp4").exists() for c in spec["cases"])
        judged = sum((manifests[model].parent / c["case_id"] / "judgment_v3.json").exists() for c in spec["cases"])
        metadata.append(f'<p><b>{model}</b>：本地视频 {completed}/10，统一评价 {judged}/10。模型：{text(spec["model"])}。</p><details><summary>{model} 生成配置</summary><pre>' + text(json.dumps(spec["generation"], ensure_ascii=False, indent=2)) + '</pre></details>')
    html = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ditto 与 Bernini 提示词对照</title>
<style>body{font:16px/1.65 system-ui,sans-serif;background:#f5f7fa;color:#182332;margin:0;padding:28px}main{max-width:1500px;margin:auto}section{margin:38px 0;padding-top:16px;border-top:2px solid #cbd5e1}h1,h2,h3,h4{line-height:1.4}.source{max-width:700px;margin:16px 0}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}article{background:white;padding:18px;border:1px solid #dbe3ec;border-radius:10px;min-width:0}video{width:100%;aspect-ratio:16/9;background:#111}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 system-ui}button{padding:9px 14px;margin:8px 8px 8px 0;border:1px solid #9baabd;border-radius:6px;cursor:pointer}a{color:#155fa0}.muted,small{color:#64748b}.pending{color:#986612}.finding{padding:16px;background:#e9f1fb;border-radius:8px}details{margin:12px 0}summary{cursor:pointer;font-weight:600}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #dbe3ec;padding:8px}th:first-child,td:first-child{width:28%}small{display:block;font-size:12px}@media(max-width:800px){.pair{grid-template-columns:1fr}body{padding:14px}}</style><main>
<h1>Ditto × Bernini：提示词与语义保留对照</h1>
<p>4 个源视频、每模型 10 个条件、每条件 seed 42。正式题目 5 秒；乒乓球沿用原片约 4.43 秒。每个题目提供原片、两个模型的视频、完整提示词和逐项评价。</p>
<p>短→详细比较描述具体化的作用；详细→详细＋保留要求比较追加约束的作用。两模型使用各自固定生成配置，比较这些具体条件中的效果方向。</p>
<p>统一评价采用 GPT-6.1-sol / xhigh，各视频独立上下文，使用实际条件帧映射对齐的 12 对采样帧。动作、物体形态和空间关系分项记录。无法从采样帧判定的运动细节单列。四个题目、单 seed 提供探索性案例证据。</p>'''
    html += ''.join(metadata) + ''.join(sections)
    html += '''</main><script>function playGroup(b){b.closest('section').querySelectorAll('video').forEach(v=>{v.currentTime=0;v.play().catch(()=>{})})}function pauseGroup(b){b.closest('section').querySelectorAll('video').forEach(v=>v.pause())}</script></html>'''
    target = dest / "comparison.html"
    target.write_text(html, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
