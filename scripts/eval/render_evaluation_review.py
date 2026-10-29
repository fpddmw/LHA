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


LABELS = {
    "edit": "编辑达成", "preserve_core": "核心语义保留", "preserve_detail": "细节保留",
    "preserve_time": "时序语义保留", "style": "目标风格", "aesthetic_mean": "美学均值",
    "narrative_emotional_fit": "叙事与情绪", "style_world_consistency": "风格与世界一致性",
    "composition_lighting": "构图与光影", "color_texture": "色彩与纹理",
    "hierarchy_readability": "层次与可读性", "temporal_coherence": "视频自身时序协调",
    "scene_specific_design": "场景化设计", "relative_originality": "相对独创性",
}
VERDICTS = {"pass": "达成", "partial": "部分达成", "fail": "未达成", "unknown": "未知", "unresolved": "待判定"}


def rel(path, page):
    return quote(Path(os.path.relpath(Path(path).resolve(), page.parent.resolve())).as_posix(), safe="/")


def num(value):
    return "未知 / 未测" if value is None else f"{value:.2f}"


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
                result = row["result"]
                require(result["card_sha256"] == card["card_sha256"], "Report/card mismatch")
                body += f'<p>任务达成判定：<b>{VERDICTS.get(result["success"], escape(result["success"]))}</b></p>'
                body += '<table><tr><th>语义指标（%）</th><th>分数</th><th>证据覆盖</th></tr>'
                for name, value in result["semantic"].items():
                    bound = "" if value["score"] is not None else f' [{num(value["lower"])}–{num(value["upper"])}]'
                    body += f'<tr><td>{LABELS.get(name, escape(name))}</td><td>{num(value["score"])}{bound}</td><td>{num(value["coverage"])}%</td></tr>'
                body += '</table><table><tr><th>视觉指标（1–4）</th><th>分数</th></tr>'
                for name in ("style", "aesthetic_mean", "scene_specific_design", "relative_originality", "temporal_coherence"):
                    body += f'<tr><td>{LABELS[name]}</td><td>{num(result["ratings"].get(name))}</td></tr>'
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
                    ratings = ''.join(f'<li><b>{LABELS.get(k, escape(k))}</b>：{num(v["score"]) if v["status"] == "scored" else escape(v["status"])}<p>{escape(v["evidence"])}</p></li>' for k, v in judgment["ratings"].items())
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
            cards.append(f'<article data-renderer="{renderer}" data-primary="{str(cid in primary).lower()}">{body}</article>')
        source_html = f'<video controls preload="metadata" src="{rel(source, page)}"></video>'
        sections.append(f'<section id="{escape(task)}"><h2>{escape(task)}</h2><p class="requirement">{escape(card["requirement"])}</p><details><summary>原视频与允许修改范围</summary>{source_html}<p>{escape(card.get("scene_summary", ""))}</p><ul>' + ''.join(f'<li>{escape(x)}</li>' for x in card["allowed_changes"]) + '</ul></details><div class="grid">' + ''.join(cards) + '</div></section>')
    css = """body{font:16px/1.55 system-ui,sans-serif;background:#f2f5f8;color:#172536;margin:0}main{max-width:1600px;margin:auto;padding:28px}nav{display:flex;gap:18px;flex-wrap:wrap}a{color:#155b9d}section{margin-top:36px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px}article{background:white;border:1px solid #dce3ea;border-radius:10px;padding:18px;min-width:0}video{display:block;width:100%;max-width:960px;background:#111}table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px}th,td{text-align:left;padding:5px;border-bottom:1px solid #e4e9ee}details{margin:12px 0}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 ui-monospace,monospace}.small{font-size:12px;color:#596b7b;overflow-wrap:anywhere}.requirement{background:#e2edf6;padding:12px}.error{color:#a32222}.toolbar{padding:15px 0}h3{margin:0}li p{margin:4px 0 12px}[hidden]{display:none!important}select{font:inherit;padding:4px}"""
    script = """const filter=document.querySelector('#renderer');filter.onchange=()=>{for(const c of document.querySelectorAll('article'))c.hidden=filter.value!=='all'&&c.dataset.renderer!==filter.value&&c.dataset.renderer!=='source';};"""
    html = f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>视频编辑正式评价复盘</title><style>{css}</style><main><h1>视频编辑正式评价复盘</h1><p>完整评分 {complete}/{len(manifest)} · 评价异常 {failed} · 更新 UTC {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}</p><p>按原始用户要求评价。语义为百分制，视觉维度为 1.0–4.0；未知保留范围与覆盖率。美学分与语义分分别解释。原片直接交付用于校准，预期没有完成要求的风格修改。</p><p class="small">开发集四题、单 seed；创造性采用固定同题候选总体并排除自身副本。CLIP-F / DINO-F 尚未测得。页面仅展示保存结果，待评价项不计为生成失败。细微动作依据连续帧评分，概览 A/B 偏好另行报告。</p><nav>' + ''.join(nav) + '</nav><div class="toolbar"><label>显示模型 <select id="renderer"><option value="all">全部</option><option value="bernini">Bernini</option><option value="ditto">Ditto</option></select></label></div>' + ''.join(sections) + f'</main><script>{script}</script></html>'
    page.write_text(html, encoding="utf-8")
    print(f"Rendered {page}: {complete}/{len(manifest)} complete, {failed} evaluation errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    render(parser.parse_args().run)
