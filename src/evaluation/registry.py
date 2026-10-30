"""Single metric contract shared by validation, scoring, aggregation and presentation."""
from __future__ import annotations
import copy
import hashlib
import json

VERSION = "lha-metrics-v3"
SCORE_VERSION = "lha-score-v3"
REPORT_VERSION = "lha-report-v3"
LABELS = {"pass": 1.0, "partial": .5, "fail": 0.0, "unknown": None}
AESTHETICS = ("narrative_emotional_fit", "style_world_consistency", "composition_lighting", "color_texture", "hierarchy_readability")
RATINGS = ("style", *AESTHETICS, "temporal_coherence", "scene_specific_design", "relative_originality")
SEMANTIC = ("edit", "preserve_core", "preserve_detail", "preserve_time")
RATING_SCALE = (1.0, 4.0)
RATING_STEP = .1
SUCCESS = {"valid_delivery": True, "mandatory_and_core": "all pass", "major_damage": False, "style_threshold": 3.0}
STATES = ("scored", "unknown", "not_applicable", "evaluation_error", "missing_output", "invalid_delivery", "missing_record", "not_measured", "legacy_status_unavailable")
STATE_LABELS = {"scored": "已评分", "unknown": "证据不足", "not_applicable": "不适用", "evaluation_error": "评价执行失败",
                "missing_output": "未交付视频", "invalid_delivery": "交付不合格", "missing_record": "尚无记录",
                "not_measured": "尚未测量", "legacy_status_unavailable": "旧记录未保留状态"}
SOURCE_AGGREGATION = "seed_mean_then_equal_task_mean_within_source_then_equal_source_macro"
MISSING_POLICY = "exclude predeclared not_applicable; retain unknown/errors in eligible denominator; no midpoint imputation"


def definition(label, meaning, unit, scale, decimals, calculation, *, applicability="always", evidence="frozen_card_and_visual_evidence", direction="higher", **extras):
    return dict(label=label, definition=meaning, unit=unit, scale=list(scale), display_decimals=decimals,
                calculation=calculation, aggregation=SOURCE_AGGREGATION, applicability=applicability,
                evidence=evidence, direction=direction, missing_policy=MISSING_POLICY, **extras)


DEFINITIONS = {}
for name, label, meaning in (
    ("edit", "编辑达成", "原始用户要求的修改是否完成"),
    ("preserve_core", "核心语义保留", "未授权改变的关键主体、行为与关系是否保留"),
    ("preserve_detail", "细节语义保留", "冻结卡所列非核心细节是否保留"),
    ("preserve_time", "时序语义保留", "原视频动作、事件顺序与时序关系是否保留")):
    DEFINITIONS[name] = definition(label, meaning, "score", (0, 1), 2, "item_mean_within_group_then_equal_group_mean",
        applicability="selected_card_items", evidence="continuous_sequence" if name == "preserve_time" else "item_required_evidence", kinds=["edit"] if name == "edit" else [name] if name != "preserve_time" else ["preserve_core", "preserve_detail"], temporal_only=name == "preserve_time", raw_labels=LABELS)
    for suffix, text, unit, scale, calc in (
        ("lower", "证据下界", "score", (0, 1), "unknown_labels_at_zero"),
        ("upper", "证据上界", "score", (0, 1), "unknown_labels_at_one"),
        ("coverage", "证据覆盖率", "percent", (0, 100), "group_weighted_known_item_fraction_times_100"),
        ("complete_rate", "完整完成比例", "percent", (0, 100), "group_weighted_pass_fraction_times_100")):
        DEFINITIONS[name + "_" + suffix] = definition(label + "：" + text, meaning + "；" + text, unit, scale, 2, calc, applicability="selected_card_items", evidence="item_required_evidence")
for name, label, meaning in (
    ("style", "目标风格", "输出对用户指定风格的实现程度"),
    ("narrative_emotional_fit", "叙事与情绪契合", "画面设计对场景行为、情绪和要求的支持"),
    ("style_world_consistency", "风格与世界一致性", "人物、物件和环境的设计协调"),
    ("composition_lighting", "构图与光影", "构图、空间、明暗及光源的协调"),
    ("color_texture", "色彩与纹理", "配色、材质与纹理的组织质量"),
    ("hierarchy_readability", "层次与可读性", "主体、物件、动作及焦点是否清晰"),
    ("temporal_coherence", "输出自身时序协调", "输出自身外观、结构、材质和运动的连续性"),
    ("scene_specific_design", "场景化设计", "在允许空间中利用原场景主体、空间、物件和行为进行设计"),
    ("relative_originality", "相对独创性", "相对固定同题匿名参照集合的有效设计差异")):
    applicability = "style_required" if name == "style" else "creativity_enabled" if name in RATINGS[-2:] else "always"
    DEFINITIONS[name] = definition(label, meaning, "rating", RATING_SCALE, 1, "raw_vlm_rating", applicability=applicability,
        evidence="fixed_same_task_reference_set" if name == "relative_originality" else "full_interval_continuous_frames" if name == "temporal_coherence" else "task_visual_evidence",
        raw_step=RATING_STEP, anchors={"1": "明显不足", "2": "部分成立、有明显缺陷", "3": "良好、仅较小缺陷", "4": "充分协调、达到任务优秀水平"})
DEFINITIONS["aesthetic_mean"] = definition("美学计算均值", "五项美学原始评分等权平均", "rating", RATING_SCALE, 1, "equal_component_mean", components=list(AESTHETICS), raw_step=RATING_STEP)
for name, label, meaning in (
    ("success_confirmed", "确认成功比例", "确认通过整题成功条件的预定任务比例（下界）"),
    ("success_possible", "成功比例上界", "已通过及尚可能通过的预定任务比例"),
    ("success_unresolved", "成功待判定比例", "整题成功条件仍待确认的预定任务比例"),
    ("delivery_valid", "有效交付比例", "已确认有效交付的预定任务比例（下界）"),
    ("unrequested_damage", "非预期损伤比例", "存在超出允许修改范围的损伤的视频比例"),
    ("major_damage", "重大损伤比例", "存在关键主体、行为或硬约束重大损伤的视频比例")):
    DEFINITIONS[name] = definition(label, meaning, "percent", (0, 100), 2, "binary_indicator_times_100",
        direction="lower" if name in {"success_unresolved", "unrequested_damage", "major_damage"} else "higher")
for name in ("clip_f", "dino_f"):
    DEFINITIONS[name] = definition(name.upper(), "输出视频自身相邻采样帧特征的平均余弦相似度", "cosine", (-1, 1), 4, "adjacent_normalized_feature_cosine_mean", evidence="fixed_encoder_revision_and_sampling")
METRICS = tuple(DEFINITIONS)


def spec(name, *, aggregate=True):
    row = copy.deepcopy(DEFINITIONS[name])  # Unknown metric names must not silently become percentages.
    row["computed_mean"] = row["unit"] == "rating" and (aggregate or name == "aesthetic_mean")
    if not aggregate:
        row["aggregation"] = row["calculation"]
    return row


def applicable(name, card):
    rule = DEFINITIONS[name]["applicability"]
    if rule == "style_required": return card["style_required"]
    if rule == "creativity_enabled": return card["creativity"] != "none"
    if rule == "selected_card_items":
        base = next(n for n in SEMANTIC if name == n or name.startswith(n + "_"))
        d = DEFINITIONS[base]
        return any(g["kind"] in d["kinds"] and any(not d["temporal_only"] or i["temporal"] for i in g["items"]) for g in card["groups"])
    return True


def snapshot():
    return {"version": VERSION, "scoring_version": SCORE_VERSION, "report_version": REPORT_VERSION,
            "labels": LABELS, "states": STATE_LABELS, "success": SUCCESS, "metrics": copy.deepcopy(DEFINITIONS)}


def fingerprint():
    return hashlib.sha256(json.dumps(snapshot(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def judgment_contract():
    fields = ("definition", "scale", "raw_step", "anchors", "applicability", "evidence")
    return {"fact_labels": list(LABELS), "ratings": {n: {k: DEFINITIONS[n][k] for k in fields} for n in RATINGS}}


def judgment_fingerprint():
    return hashlib.sha256(json.dumps(judgment_contract(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def scoring_fingerprint():
    fields = ("unit", "scale", "calculation", "aggregation", "applicability", "missing_policy")
    value = {"labels": LABELS, "success": SUCCESS, "raw_contract": judgment_fingerprint(),
             "metrics": {n: {k: row[k] for k in fields} | {"components": row.get("components"), "kinds": row.get("kinds"), "temporal_only": row.get("temporal_only")}
                         for n, row in DEFINITIONS.items()}}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def rating_contract(names):
    return "\nRaw metric definitions:\n" + json.dumps({n: judgment_contract()["ratings"][n] for n in names}, ensure_ascii=False, sort_keys=True)


def overview():
    lo, hi = DEFINITIONS["edit"]["scale"]
    return (f"语义为 {lo}–{hi} 分，先组内平均再组间等权，显示 {DEFINITIONS['edit']['display_decimals']} 位小数。"
            f"VLM 原始评分为 {RATING_SCALE[0]:.1f}–{RATING_SCALE[1]:.1f}、{RATING_STEP} 步长，原始分及计算均值显示 {DEFINITIONS['style']['display_decimals']} 位。"
            "完整完成比例、成功比例和覆盖率单列 %。未知、不适用和执行失败分别统计；JSON/CSV 保留完整精度。")


def markdown():
    lines = ["# 统一评价指标定义（自动生成）", "", f"定义版本：`{VERSION}`；计算版本：`{SCORE_VERSION}`。", "",
             "原始判断 → 确定性计算分 → seed/任务/源三级统计。" + overview(), "",
             "unknown 仅表示证据不足；not_applicable 由冻结卡决定并从适用分母排除；执行失败、缺视频、待测和旧状态缺失分别计数。", "",
             "| 指标 ID | 名称与定义 | 尺度／单位 | 小数位 | 计算方式 | 适用性 |", "|---|---|---|---:|---|---|"]
    for name, row in DEFINITIONS.items():
        lines.append(f"| `{name}` | {row['label']}：{row['definition']} | {row['scale']} / {row['unit']} | {row['display_decimals']} | `{row['calculation']}` | `{row['applicability']}` |")
    lines += ["", "统计：同任务 seed 等权；同源原始任务等权；源视频等权。未知或失败 seed 保持该源点估计缺失，适用范围内的源分母保留。报告有效源均值、适用/预定源数、覆盖率及独立状态计数。", "",
              "语义总体上下界沿相同层次汇总每条语义证据上下界；执行缺项使用 [0,1] 的可行范围，分别报告错误计数。这些是证据/缺项界限，源级 bootstrap 置信区间只针对有效源均值。", "",
              f"整题成功：有效交付、mandatory 及核心项全部 pass、无重大非预期损伤；风格任务另需 style ≥ {SUCCESS['style_threshold']:.1f}。成功未知保留上下界，不以视觉均分补偿语义硬失败。", "",
              "本文件由 `python scripts/eval/export_metric_definitions.py` 生成；修改源为 `src/evaluation/registry.py`。", ""]
    return "\n".join(lines)
