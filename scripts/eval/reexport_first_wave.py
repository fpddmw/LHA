"""Re-export saved first-wave evaluations; no model, video generation or rescoring calls."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import os
import re
import shutil
import sys
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from evaluation.aggregate import export_report, paired_difference, summarize
from evaluation.protocol import file_hash, read, require, validate_judgment, write
from evaluation.reporting import SEMANTIC, VERSION, difference_spec, metric_spec, normalized_records
from evaluation.scoring import score


def primary_cohort(run, records, *, root=ROOT):
    manifest = {c["case_id"]: c for c in read(run / "manifest.json")["cases"]}
    identities = read(run / "primary_cases.json")
    require(len(set(identities)) == len(identities), "Duplicate predeclared primary case")
    lookup = {r["case_id"]: r for r in records}
    require(len(lookup) == len(records), "Duplicate saved record")
    selected, cohort = [], []
    for cid in identities:
        case = manifest[cid]
        card = read(root / case["card"])
        renderer = cid.split("__")[0]
        role = "planner" if "__planner__" in cid else "direct"
        require(renderer in {"bernini", "ditto"} and case["method"] != "source_control", "Invalid primary method")
        if role == "direct":
            require(cid == f"{renderer}__baseline__{card['source_id']}__{card['track']}", "Supplementary variants cannot enter the main cohort")
        method = renderer + "_" + role
        cohort.append({"case_id": cid, "method": method, "renderer": renderer, "seed": case["seed"],
                       **{k: card[k] for k in ("task_id", "source_id", "track", "split")}})
        if cid in lookup:
            row = lookup[cid]
            require(row["result"]["card_sha256"] == card["card_sha256"] and row["seed"] == case["seed"], "Saved record/card mismatch")
            require(row["result"]["track"] == card["track"], "Planner expansion must retain original track")
            selected.append({**row, "method": method, "original_method": row["method"], "renderer": renderer})
    return selected, cohort


def source_hashes(run):
    paths = [run / n for n in ("records.json", "primary_records.json", "primary_cases.json", "primary_differences.json",
             "manifest.json", "completion.json", "pairwise_results.json", "review_queue.json") if (run / n).exists()]
    paths += list((run / "judgments").rglob("*.json")) + list((run / "pairwise").rglob("*.json")) + list((run / "cards").glob("*.json"))
    return {str(p.relative_to(run)).replace("\\", "/"): file_hash(p) for p in paths}


def reexport(run, *, repeats=2000):
    before = source_hashes(run)
    records = read(run / "records.json")
    selected, cohort = primary_cohort(run, records)
    require(len(records) == 32 and len(selected) == len(cohort) == 16, "This export requires the completed 32/16 first wave")
    require(all(r["status"] == "complete" for r in records), "Keep evaluation errors visible; first wave is not complete")
    require(Counter((r["method"], r["track"]) for r in cohort) == Counter({(m, t): 2 for m in ("bernini_direct", "bernini_planner", "ditto_direct", "ditto_planner") for t in ("short", "long")}), "Expected two short and two long tasks per method")
    normalized = normalized_records(selected)
    raw_ratings = 0
    for row in records:
        case = next(c for c in read(run / "manifest.json")["cases"] if c["case_id"] == row["case_id"])
        card = read(ROOT / case["card"])
        j = validate_judgment(card, read(run / "judgments" / row["case_id"] / "judgment.json"))
        require(score(card, j) == row["result"], "Saved score disagrees with original labels/formula")
        for item in j["ratings"].values():
            if item["score"] is not None:
                require(abs(item["score"] * 10 - round(item["score"] * 10)) < 1e-8, "Raw VLM rating off 0.1 grid")
                raw_ratings += 1
    for old, new in zip(selected, normalized):
        require(old["result"]["success"] == new["result"]["success"], "Success status changed")
        require(old["result"]["ratings"] == new["result"]["ratings"], "Raw or computed rating changed")
        for part in SEMANTIC:
            for field in ("score", "lower", "upper"):
                a, b = old["result"]["semantic"][part][field], new["result"]["semantic"][part][field]
                require((a is None and b is None) or abs(a / 100 - b) < 1e-12, "Semantic scale mismatch")
        require(new == normalized_records([new])[0], "Normalization applied twice")
    old_summary = summarize(selected, repeats=0, include_overall=True, cohort=cohort)
    main = export_report(selected, run / "primary_report_v2", repeats=repeats, cohort=cohort)
    for old, new in zip(old_summary, main):
        for key, stats in old["metrics"].items():
            factor = 100 if metric_spec(key)["unit"] == "score" else 1
            a, b = stats["mean"], new["metrics"][key]["mean"]
            require((a is None and b is None) or abs(a / factor - b) < 1e-10, "Macro formula changed")
    # Full precision ordering, including ties, is preserved by the positive scale conversion.
    metrics = sorted(main[0]["metrics"])
    for track in ("all", "short", "long"):
        for metric in metrics:
            def ranks(rows):
                return sorted((r["metrics"][metric]["mean"], r["method"]) for r in rows if r["track"] == track and r["metrics"][metric]["mean"] is not None)
            require([m for _, m in ranks(old_summary)] == [m for _, m in ranks(main)], "Method ordering changed")
    export_report([{**r, "renderer": "source" if r["method"] == "source_control" else r["case_id"].split("__")[0]} for r in records],
                  run / "report_v2", repeats=repeats, include_overall=False)
    diffs = []
    for renderer in ("bernini", "ditto"):
        for metric in ("edit", "preserve_core", "preserve_detail", "preserve_time", "style", "aesthetic_mean", "scene_specific_design", "relative_originality"):
            values = paired_difference(normalized, renderer + "_planner", renderer + "_direct", metric,
                                       repeats=repeats, include_overall=True, cohort=cohort)
            diffs.extend({**r, "model": renderer, "metadata": difference_spec(metric)} for r in values)
    write(run / "primary_report_v2/paired_differences.json", {"version": VERSION, "direction": "planner - direct", "panels": diffs})
    pairs = read(run / "pairwise_results.json")
    require(len(pairs) == 8, "Expected eight saved A/B pairs")
    write(run / "primary_report_v2/cohort.json", {"version": VERSION, "planned_cases": cohort,
        "main_outputs": 16, "tasks_per_method": 4, "model_task_pairs": 8, "independent_sources": 4, "seed": 42,
        "supplementary_outputs": 12, "source_controls": 4, "pairwise_results": "../pairwise_results.json",
        "design": "Retrospective development set; two short/two long, each renderer separately, fixed original task/card; variants and controls outside primary cohort"})
    from render_evaluation_review import render
    render(run)
    after = source_hashes(run)
    require(before == after, "Historical records/judgments/pairwise/review queue changed")
    audit = {"version": VERSION, "records": 32, "primary_records": 16, "paired_comparisons": 8,
        "summary_panels": len(main), "raw_vlm_ratings_verified": raw_ratings, "raw_vlm_rating_scale": [1, 4], "raw_vlm_rating_step": 0.1,
        "success_states_unchanged": True, "full_precision_rankings_unchanged": True,
        "aggregate_formula_verified": True, "normalization_idempotent": True,
        "source_files_unchanged": before, "pending_review": read(run / "review_queue.json") if (run / "review_queue.json").exists() else [],
        "model_calls": 0, "generation_calls": 0}
    write(run / "primary_report_v2/validation.json", audit)
    return {k: v for k, v in audit.items() if k not in {"source_files_unchanged", "pending_review"}}


def publish(run, destination):
    """Small tracked export; reuse the already published, hash-verified video bundle."""
    destination.mkdir(parents=True, exist_ok=True)
    bundle = ROOT / "reports/20261030-sync"
    media = {str((ROOT / row["original_path"]).resolve()): row for row in read(bundle / "videos.json")}
    for name in ("primary_report_v2", "report_v2", "cards"):
        shutil.copytree(run / name, destination / name, dirs_exist_ok=True)
    for name in ("records.json", "manifest.json", "primary_cases.json", "pairwise_results.json", "review_queue.json", "completion.json"):
        shutil.copyfile(run / name, destination / name)
    for path in (run / "judgments").glob("*/judgment.json"):
        target = destination / path.relative_to(run)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    seen = set()
    def replace(match):
        attribute, url = match.groups()
        if url.startswith("#") or "://" in url:
            return match.group(0)
        origin = (run / unquote(url)).resolve()
        if origin.is_relative_to(run.resolve()):
            target = destination / origin.relative_to(run.resolve())
        elif str(origin) in media:
            entry = media[str(origin)]
            target = bundle / entry["video"]
            if target not in seen:
                require(file_hash(target) == entry["sha256"], "Published video hash mismatch")
                seen.add(target)
        else:
            target = origin  # Original source videos already tracked in benchmark_data.
        require(target.exists(), f"Missing published report link: {target}")
        relative = quote(Path(os.path.relpath(target.resolve(), destination.resolve())).as_posix(), safe="/")
        return f'{attribute}="{relative}"'
    html = re.sub(r'(src|href)="([^"]+)"', replace, (run / "review.html").read_text(encoding="utf-8"))
    (destination / "review.html").write_text(html, encoding="utf-8")
    (destination / "README.md").write_text(
        "# 首批完整评价：展示 v2\n\n"
        "32 条完整记录；16 条预定主比较；8 个模型×任务配对、4 个独立源。\n\n"
        "- [视频、四题总体、短长分轨及逐项证据](review.html)\n"
        "- [主报告](primary_report_v2/report.md) · [完整精度 CSV](primary_report_v2/metrics.csv) · [量尺与计算元数据](primary_report_v2/metadata.json)\n"
        "- [入组清单](primary_report_v2/cohort.json) · [配对差值](primary_report_v2/paired_differences.json) · [验证记录](primary_report_v2/validation.json)\n"
        "- [全部条件补充表](report_v2/report.md) · [原始记录](records.json) · [冻结任务卡](cards)\n\n"
        "语义为 0–1 分、两位小数；VLM 原始评分 1–4、0.1 步长，原始分及计算均值默认显示一位。"
        "比例单列 %。原始判断、未知、损伤和成功状态保留。041 短任务的装订/独立纸页复核仍 pending。\n\n"
        "HTML 复用 ../20261030-sync/media 中已发布视频，原片位于 ../../benchmark_data；克隆完整仓库后可离线浏览。"
        "JSON 中保留运行时原始路径供追溯，不将其重写为新的实验输入。更早的 22/32 阶段快照保留在 20261030-sync。"
        "本次只重新导出，没有模型调用或视频生成。\n", encoding="utf-8")
    write(destination / "publication.json", {"version": VERSION, "records": 32, "primary": 16, "pairs": 8,
          "reused_video_files_hash_verified": len(seen), "links_verified": True,
          "source_run": str(run).replace("\\", "/"), "source_records_sha256": file_hash(run / "records.json")})


if __name__ == "__main__":
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--bootstrap", type=int, default=2000)
    p.add_argument("--publish", type=Path, help="Optional tracked report folder; reuse the existing published media")
    args = p.parse_args()
    print(json.dumps(reexport(args.run, repeats=args.bootstrap), ensure_ascii=False))
    if args.publish:
        publish(args.run, args.publish)
