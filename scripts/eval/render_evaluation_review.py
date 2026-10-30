"""Render local videos, frozen requirements and saved evaluations without model calls."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from html import escape
import os
from pathlib import Path
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from evaluation.protocol import read, require
from evaluation.reporting import display, metric_spec, scale_label


from evaluation.registry import DEFINITIONS, STATE_LABELS, overview
from evaluation.reporting import PRIMARY_DIRECTORY as PRIMARY, REPORT_DIRECTORY as SUPPLEMENTARY
from evaluation.compat import canonical_record
LABELS = {n: d["label"] for n, d in DEFINITIONS.items()}
VERDICTS = {"pass": "达成", "partial": "部分达成", "fail": "未达成", "unknown": "未知", "unresolved": "待判定"}


def rel(path, page):
    return quote(Path(os.path.relpath(Path(path).resolve(), page.parent.resolve())).as_posix(), safe="/")


def summary_html(run):
    path = run / PRIMARY / "summary.json"
    if not path.exists():
        return '<p>四题总体/短长汇总尚未导出，可运行 reexport_first_wave.py。</p>'
    panels = read(path)
    chunks = ['<section id="primary-summary"><h2>预定主要对照：四题宏平均及短／长分轨</h2><p>direct＝原始 benchmark 提示词直送；planner＝本批已保存的单轮规划提示词输出。每个方法四个独立源视频（短 2、长 2），单 seed；每题等权。共 16 条主比较输出、8 个模型×任务配对，独立源数仍为 4。其余 12 条提示词变体及 4 条原片对照另列。表中分别给出有效／适用／预定源数及未知、不适用、执行失败计数。</p>']
    for track, title in (("all", "四题总体（短 2＋长 2）"), ("short", "短任务（原始约束，2 题）"), ("long", "长任务（原始约束，2 题）")):
        chunks.append(f'<h3>{title}</h3>')
        for names, heading in [(("edit", "preserve_core", "preserve_detail", "preserve_time", "style", "aesthetic_mean", "scene_specific_design", "relative_originality"), f"分项分数：语义 {scale_label('edit')}，视觉计算均值 {scale_label('style')}"),
                               (("success_confirmed", "success_unresolved", "edit_complete_rate", "preserve_core_complete_rate", "edit_coverage", "preserve_core_coverage", "unrequested_damage", "major_damage"), "比例（%），与语义分数分列")]:
            chunks.append(f'<p>{heading}</p><div class="scroll"><table><tr><th>模型／方法</th><th>实际／预定输出</th>' + ''.join(f'<th>{escape(metric_spec(n)["label"])}<br>{"分" if metric_spec(n)["unit"] == "score" else "计算均值" if metric_spec(n)["unit"] == "rating" else "%"}</th>' for n in names) + '</tr>')
            for row in panels:
                if row["track"] != track:
                    continue
                chunks.append(f'<tr data-renderer="{escape(row.get("model") or "unknown")}"><td>{escape(row["method"])}</td><td>{row["n_records"]}/{row["expected_records"]}</td>')
                for n in names:
                    value = row["metrics"][n]
                    chunks.append(f'<td>{display(value["mean"], n)}<br><span class="small">有效/适用/预定={value["n_sources"]}/{value.get("applicable_sources", value["total_sources"])}/{value["total_sources"]}<br>{escape(str({STATE_LABELS.get(s,s):n for s,n in value.get("observation_counts",{}).items() if n and s != "scored"}))}</span></td>')
                chunks.append('</tr>')
            chunks.append('</table></div>')
    chunks.append(f'<p class="small">{escape(overview())} 短任务不继承未要求的长任务细节，Planner 扩写不改变原始 track。区间及逐项数据见 JSON。</p><p><a href="{PRIMARY}/report.md">完整主报告</a> · <a href="{PRIMARY}/metrics.csv">完整精度 CSV</a> · <a href="{PRIMARY}/metadata.json">指标定义与元数据</a> · <a href="{PRIMARY}/paired_differences.json">配对差值</a> · <a href="{SUPPLEMENTARY}/report.md">补充报告</a></p></section>')
    return ''.join(chunks)



def details(title, body):
    return f"<details><summary>{escape(title)}</summary>{body}</details>"


def render(run):
    page = run / "review.html"
    manifest = read(run / "manifest.json")["cases"]
    records = {r["case_id"]: r for r in read(run / "records.json")} if (run / "records.json").exists() else {}
    primary = set(read(run / "primary_cases.json")) if (run / "primary_cases.json").exists() else set()
    groups = defaultdict(list)
    for case in manifest:
        card = read(ROOT / case["card"])
        groups[card["task_id"]].append((case, card))
    complete = sum(r["status"] == "complete" for r in records.values())
    failed = sum(r["status"] != "complete" for r in records.values())
    nav, sections = [], []
    for task, cases in sorted(groups.items()):
        card = cases[0][1]
        nav.append(f'<a href="#{escape(task)}">{escape(task)}</a>')
        source = ROOT / card["source_video"]
        cards = []
        for case, _ in sorted(cases, key=lambda c: (c[0]["case_id"] not in primary, c[0]["case_id"])):
            cid = case["case_id"]
            row = records.get(cid)
            renderer = "source" if case["method"] == "source_control" else cid.split("__")[0]
            label = case["method"].replace("__", " · ")
            status = "待评价" if row is None else "完整评分" if row["status"] == "complete" else "评价异常"
            video = ROOT / case["output_video"]
            body = f'<h3>{escape(label)}</h3><p class="small">{escape(cid)} · {status}'
            body += " · 主要配对" if cid in primary else ""
            body += f'</p><video controls preload="metadata" src="{rel(video, page)}"></video>' if video.exists() else '</p><p>视频尚未交付</p>'
            if row:
                jp = run / "judgments" / cid / "judgment.json"
                if jp.exists() and row["status"] == "complete":
                    from evaluation.scoring import score
                    result = score(card, read(jp), role="final")
                else:
                    result = canonical_record(row)["result"]
                require(result["card_sha256"] == card["card_sha256"], "Report/card mismatch")
                body += f'<p>任务达成判定：<b>{VERDICTS.get(result["success"], escape(result["success"]))}</b></p>'
                body += f'<table><tr><th>语义指标</th><th>分组加权得分（{scale_label("edit")} 分）</th><th>完整完成比例（%）</th><th>证据覆盖率（%）</th></tr>'
                for name, value in result["semantic"].items():
                    bound = "" if value["score"] is not None or value["lower"] is None else f' [{display(value["lower"], name+"_lower")}–{display(value["upper"], name+"_upper")}]'
                    body += f'<tr><td>{LABELS.get(name, escape(name))}</td><td>{display(value["score"], name, status=value["status"])}{bound}</td><td>{display(value["complete_rate"], name+"_complete_rate", status=result["metric_status"][name+"_complete_rate"])}</td><td>{display(value["coverage"], name+"_coverage", status=result["metric_status"][name+"_coverage"])}</td></tr>'
                body += f'</table><table><tr><th>视觉指标（{scale_label("style")}）</th><th>分数</th></tr>'
                for name in ("style", "aesthetic_mean", "scene_specific_design", "relative_originality", "temporal_coherence"):
                    label = "美学计算均值（五项）" if name == "aesthetic_mean" else LABELS[name] + "（VLM 原始评分）"
                    body += f'<tr><td>{label}</td><td>{display(result["ratings"].get(name), name, aggregate=False, status=result["rating_status"].get(name))}</td></tr>'
                body += '</table>'
                if row.get("evaluation_error"):
                    body += f'<p class="error">{escape(row["evaluation_error"])}</p>'
                jp = run / "judgments" / cid / "judgment.json"
                if jp.exists() and row["status"] == "complete":
                    judgment = read(jp)
                    labels = {i["id"]: i["text"] for g in card["groups"] for i in g["items"]}
                    facts = []
                    for item in judgment["items"]:
                        times = ", ".join(f"{t:.2f}" for t in item.get("times_seconds", []))
                        facts.append(f'<li><b>{escape(labels[item["id"]])}</b>：{VERDICTS[item["label"]]}<p>{escape(item["evidence"])}<br><span class="small">输出时刻：{times or "未提供"} 秒</span></p></li>')
                    body += details("逐项语义依据", '<ul>' + ''.join(facts) + '</ul>')
                    ratings = ''.join(f'<li><b>{LABELS.get(k, escape(k))}</b>：{display(v["score"], k, aggregate=False) if v["status"] == "scored" else escape(v["status"])}<p>{escape(v["evidence"])}</p></li>' for k, v in judgment["ratings"].items())
                    body += details("视觉评分依据", '<ul>' + ratings + '</ul>')
                    damage = ''.join(f'<li>{escape(d["severity"])}：{escape(d["evidence"])}</li>' for d in judgment.get("damages", []))
                    body += details("语义损伤记录", '<ul>' + damage + '</ul>' if damage else '<p>本次评价未记录损伤；详见各项证据覆盖。</p>')
                    body += f'<p class="small"><a href="{rel(jp, page)}">完整评分 JSON</a></p>'
            else:
                body += '<p>正在排队评价；当前没有成绩。</p>'
            input_path = video.parent / "input.json"
            if case["method"] != "source_control" and input_path.exists():
                input_record = read(input_path)
                prompt = input_record.get("prompt")
                if prompt:
                    body += details("生成提示词（仅供过程复盘，未送最终评价器）", f'<pre>{escape(prompt)}</pre>')
            cards.append(f'<article data-renderer="{renderer}" data-track="{escape(card["track"])}" data-primary="{str(cid in primary).lower()}"><p class="small">原始任务：{escape(card["track"])} · {"主比较" if cid in primary else "原片对照" if renderer == "source" else "补充提示词条件"}</p>{body}</article>')
        source_html = f'<video controls preload="metadata" src="{rel(source, page)}"></video>'
        sections.append(f'<section id="{escape(task)}"><h2>{escape(task)}</h2><p class="requirement">{escape(card["requirement"])}</p><details><summary>原视频与允许修改范围</summary>{source_html}<p>{escape(card.get("scene_summary", ""))}</p><ul>' + ''.join(f'<li>{escape(x)}</li>' for x in card["allowed_changes"]) + '</ul></details><div class="grid">' + ''.join(cards) + '</div></section>')
    css = """body{font:16px/1.55 system-ui,sans-serif;background:#f2f5f8;color:#172536;margin:0}main{max-width:1600px;margin:auto;padding:28px}nav{display:flex;gap:18px;flex-wrap:wrap}a{color:#155b9d}section{margin-top:36px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px}article{background:white;border:1px solid #dce3ea;border-radius:10px;padding:18px;min-width:0}video{display:block;width:100%;max-width:960px;background:#111}table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px}th,td{text-align:left;padding:5px;border-bottom:1px solid #e4e9ee}details{margin:12px 0}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 ui-monospace,monospace}.small{font-size:12px;color:#596b7b;overflow-wrap:anywhere}.requirement{background:#e2edf6;padding:12px}.error{color:#a32222}.toolbar{padding:15px 0}h3{margin:0}li p{margin:4px 0 12px}[hidden]{display:none!important}select{font:inherit;padding:4px}"""
    css += ".scroll{overflow-x:auto}.scroll th,.scroll td{min-width:85px}"
    script = """const filter=document.querySelector('#renderer');filter.onchange=()=>{for(const c of document.querySelectorAll('[data-renderer]'))c.hidden=filter.value!=='all'&&c.dataset.renderer!==filter.value&&c.dataset.renderer!=='source';};"""
    reviews = read(run / "review_queue.json").get("reviews", []) if (run / "review_queue.json").exists() else []
    pending = '<p class="error">041 短任务的装订／独立纸页复核仍 pending：当前页面保留原判分，<a href="review_queue.json">复核队列</a>可追溯。</p>' if any(r["id"] == "041_short_object_boundaries" and r["status"].startswith("pending") for r in reviews) else ''
    html = f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>视频编辑正式评价复盘</title><style>{css}</style><main><h1>视频编辑正式评价复盘</h1><p>完整评分 {complete}/{len(manifest)} · 评价异常 {failed} · 更新 UTC {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}</p><p>{escape(overview())}</p><p class="small">原始短/长要求使用同一指标尺度；short 不继承未要求的 long 细节。开发集四题、单 seed；创造性使用固定同题候选总体并排除自身副本。CLIP-F / DINO-F 尚未测得。概览 A/B 偏好保持独立于连续帧细微动作评价。</p>' + pending + '<nav>' + ''.join(nav) + '</nav><div class="toolbar"><label>显示模型 <select id="renderer"><option value="all">全部</option><option value="bernini">Bernini</option><option value="ditto">Ditto</option></select></label></div>' + summary_html(run) + ''.join(sections) + f'</main><script>{script}</script></html>'
    page.write_text(html, encoding="utf-8")
    print(f"Rendered {page}: {complete}/{len(manifest)} complete, {failed} evaluation errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    render(parser.parse_args().run)
