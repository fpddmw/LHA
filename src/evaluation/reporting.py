"""Versioned display scales. Original judgments and legacy scoring stay intact."""
from __future__ import annotations

import copy
from .protocol import AESTHETICS, RATINGS, require

VERSION = "lha-report-v2"
SEMANTIC = ("edit", "preserve_core", "preserve_detail", "preserve_time")
NAMES = {"edit": "编辑达成", "preserve_core": "核心语义保留", "preserve_detail": "细节保留",
         "preserve_time": "时序语义保留", "style": "目标风格", "aesthetic_mean": "美学计算均值",
         "narrative_emotional_fit": "叙事与情绪", "style_world_consistency": "风格与世界一致性",
         "composition_lighting": "构图与光影", "color_texture": "色彩与纹理", "hierarchy_readability": "层次与可读性",
         "temporal_coherence": "视频自身时序协调", "scene_specific_design": "场景化设计", "relative_originality": "相对独创性",
         "success_confirmed": "确认成功比例", "success_possible": "成功比例上界", "success_unresolved": "待判定比例",
         "delivery_valid": "有效交付比例", "unrequested_damage": "存在非预期损伤的比例", "major_damage": "存在重大损伤的比例"}
METRICS = (*RATINGS, "aesthetic_mean", "clip_f", "dino_f",
           *(b + suffix for b in SEMANTIC for suffix in ("", "_lower", "_upper", "_coverage", "_complete_rate")),
           "success_confirmed", "success_possible", "success_unresolved", "delivery_valid", "unrequested_damage", "major_damage")


def normalized_result(result):
    """Convert only score/bounds, once. Completion/coverage remain genuine percentages."""
    out = copy.deepcopy(result)
    scale = out.get("reporting", {}).get("semantic_score_scale", "legacy_0_100")
    require(scale in {"legacy_0_100", "unit_interval"}, "Unknown semantic score scale")
    factor = 100 if scale == "legacy_0_100" else 1
    for part in out["semantic"].values():
        for key in ("score", "lower", "upper"):
            if part[key] is not None:
                require(0 <= part[key] <= factor, "Semantic score outside declared scale")
                part[key] /= factor
    out["reporting"] = {"version": VERSION, "semantic_score_scale": "unit_interval",
        "semantic_aggregation": "pass=1, partial=0.5, fail=0; item mean within group, equal group mean; unknown retains bounds",
        "rate_scale": "percent", "vlm_raw_scale": [1, 4], "vlm_raw_step": 0.1,
        "aesthetic_mean_components": list(AESTHETICS), "rounding": "display only; full computation precision retained"}
    return out


def normalized_records(records):
    return [{**copy.deepcopy(row), "result": normalized_result(row["result"])} for row in records]


def metric_spec(name, *, aggregate=True):
    for base in SEMANTIC:
        if name in {base, base + "_lower", base + "_upper"}:
            suffix = {base: "", base + "_lower": "下界", base + "_upper": "上界"}[name]
            return {"label": NAMES[base] + suffix, "unit": "score", "scale": [0, 1], "display_decimals": 2,
                    "aggregation": "source_macro_of_group_weighted_label_score" if aggregate else "group_weighted_label_score"}
        for suffix, label in (("coverage", "证据覆盖率"), ("complete_rate", "完整完成比例")):
            if name == base + "_" + suffix:
                return {"label": NAMES[base] + "：" + label, "unit": "percent", "scale": [0, 100],
                        "display_decimals": 2, "aggregation": "group_weighted_rate_then_source_macro"}
    if name in {*RATINGS, "aesthetic_mean"}:
        return {"label": NAMES.get(name, name), "unit": "rating", "scale": [1, 4], "raw_step": 0.1,
                "display_decimals": 1, "computed_mean": aggregate or name == "aesthetic_mean",
                "aggregation": ("five_aesthetic_items_then_source_macro" if aggregate else "five_aesthetic_items") if name == "aesthetic_mean"
                               else "source_macro_of_raw_vlm_ratings" if aggregate else "raw_vlm_rating"}
    if name in {"clip_f", "dino_f"}:
        return {"label": name, "unit": "cosine", "scale": [-1, 1], "display_decimals": 4, "aggregation": "source_macro"}
    return {"label": NAMES.get(name, name), "unit": "percent", "scale": [0, 100], "display_decimals": 2, "aggregation": "source_macro_of_rates"}


def display(value, name, *, aggregate=True):
    spec = metric_spec(name, aggregate=aggregate)
    return "未知 / 未测" if value is None else f"{value:.{spec['display_decimals']}f}"


def difference_spec(name):
    spec = metric_spec(name)
    span = spec["scale"][1] - spec["scale"][0]
    return {**spec, "label": "差值：" + spec["label"], "source_scale": spec["scale"], "scale": [-span, span],
            "aggregation": "paired_same_task_seed_then_task_source_macro"}
