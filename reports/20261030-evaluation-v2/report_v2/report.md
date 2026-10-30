# 视频编辑评价（展示口径 v2）

语义为 0–1 分（分组加权计算分），完整完成比例、成功比例与覆盖率为 %。VLM 原始评分为 1–4、0.1 步长；下表 VLM 列均为计算均值，显示一位小数。美学计算均值先平均五项原始评分。JSON/CSV 保留完整计算精度。

每题先汇总 seed，同源多题先等权合并，再按源宏平均；预定缺项保留分母。短/长沿原始任务卡，Planner 扩写不改变 track。未知保留界限和覆盖率，分项分别解释。

## bernini__baseline_long / development / long

预定 4 题；记录 4/4；原始轨道 {'long': 4}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.6 | [3.4, 3.8] | 4/4 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 色彩与纹理 (color_texture) | rating | 3.6 | [3.2, 3.9] | 4/4 |
| 构图与光影 (composition_lighting) | rating | 3.7 | [3.5, 3.8] | 4/4 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 编辑达成 (edit) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 82.29 | [64.58, 100.00] | 4/4 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 编辑达成下界 (edit_lower) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 编辑达成上界 (edit_upper) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 层次与可读性 (hierarchy_readability) | rating | 3.5 | [3.3, 3.7] | 4/4 |
| 存在重大损伤的比例 (major_damage) | percent | 50.00 | [0.00, 100.00] | 4/4 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.8 | [3.5, 4.0] | 4/4 |
| 核心语义保留 (preserve_core) | score | 0.92 | [0.84, 1.00] | 4/4 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 84.03 | [68.06, 100.00] | 4/4 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.92 | [0.84, 1.00] | 4/4 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.92 | [0.84, 1.00] | 4/4 |
| 细节保留 (preserve_detail) | score | 0.50 | [0.19, 0.75] | 4/4 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 25.00 | [0.00, 50.00] | 4/4 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 细节保留下界 (preserve_detail_lower) | score | 0.50 | [0.19, 0.75] | 4/4 |
| 细节保留上界 (preserve_detail_upper) | score | 0.50 | [0.19, 0.75] | 4/4 |
| 时序语义保留 (preserve_time) | score | 0.85 | [0.71, 1.00] | 4/4 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 70.83 | [41.67, 100.00] | 4/4 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.85 | [0.71, 1.00] | 4/4 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.85 | [0.71, 1.00] | 4/4 |
| 相对独创性 (relative_originality) | rating | 1.9 | [1.4, 2.3] | 4/4 |
| 场景化设计 (scene_specific_design) | rating | 3.1 | [3.0, 3.2] | 4/4 |
| 目标风格 (style) | rating | 3.5 | [3.0, 3.8] | 4/4 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.7 | [3.5, 3.9] | 4/4 |
| 确认成功比例 (success_confirmed) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 成功比例上界 (success_possible) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.8 | [3.7, 4.0] | 4/4 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 4/4 |

## bernini__baseline_long_keep / development / long

预定 4 题；记录 4/4；原始轨道 {'long': 4}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.6 | [3.3, 3.8] | 4/4 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 色彩与纹理 (color_texture) | rating | 3.5 | [3.3, 3.8] | 4/4 |
| 构图与光影 (composition_lighting) | rating | 3.6 | [3.4, 3.9] | 4/4 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 编辑达成 (edit) | score | 0.93 | [0.85, 1.00] | 4/4 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 85.42 | [70.83, 100.00] | 4/4 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 编辑达成下界 (edit_lower) | score | 0.93 | [0.85, 1.00] | 4/4 |
| 编辑达成上界 (edit_upper) | score | 0.93 | [0.85, 1.00] | 4/4 |
| 层次与可读性 (hierarchy_readability) | rating | 3.4 | [3.2, 3.8] | 4/4 |
| 存在重大损伤的比例 (major_damage) | percent | 50.00 | [0.00, 100.00] | 4/4 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.7 | [3.4, 4.0] | 4/4 |
| 核心语义保留 (preserve_core) | score | 0.91 | [0.83, 1.00] | 4/4 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 82.64 | [65.28, 100.00] | 4/4 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.91 | [0.83, 1.00] | 4/4 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.91 | [0.83, 1.00] | 4/4 |
| 细节保留 (preserve_detail) | score | 0.42 | [0.00, 0.75] | 3/4 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 16.67 | [0.00, 50.00] | 3/4 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 87.50 | [62.50, 100.00] | 4/4 |
| 细节保留下界 (preserve_detail_lower) | score | 0.44 | [0.12, 0.69] | 4/4 |
| 细节保留上界 (preserve_detail_upper) | score | 0.56 | [0.12, 0.88] | 4/4 |
| 时序语义保留 (preserve_time) | score | 0.94 | [0.83, 1.00] | 3/4 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 88.89 | [66.67, 100.00] | 3/4 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 87.50 | [62.50, 100.00] | 4/4 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.83 | [0.62, 1.00] | 4/4 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.96 | [0.88, 1.00] | 4/4 |
| 相对独创性 (relative_originality) | rating | 1.8 | [1.2, 2.3] | 4/4 |
| 场景化设计 (scene_specific_design) | rating | 3.0 | [2.8, 3.0] | 4/4 |
| 目标风格 (style) | rating | 3.6 | [3.4, 3.8] | 4/4 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.6 | [3.0, 3.9] | 4/4 |
| 确认成功比例 (success_confirmed) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 成功比例上界 (success_possible) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.7 | [3.2, 4.0] | 4/4 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 75.00 | [25.00, 100.00] | 4/4 |

## bernini__baseline_short / development / short

预定 2 题；记录 2/2；原始轨道 {'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.0 | [2.6, 3.4] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 3.0 | [2.8, 3.3] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.0 | [2.6, 3.4] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 0.50 | [0.00, 1.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 0.50 | [0.00, 1.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 0.50 | [0.00, 1.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.0 | [2.3, 3.8] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 2.8 | [2.6, 3.0] | 2/2 |
| 核心语义保留 (preserve_core) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 0.42 | [0.33, 0.50] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 41.67 | [33.33, 50.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 0.42 | [0.33, 0.50] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 0.42 | [0.33, 0.50] | 2/2 |
| 时序语义保留 (preserve_time) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 相对独创性 (relative_originality) | rating | 1.5 | [1.0, 2.0] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 1.9 | [1.0, 2.8] | 2/2 |
| 目标风格 (style) | rating | 2.1 | [1.0, 3.2] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.1 | [2.2, 4.0] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 4.0 | [4.0, 4.0] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 2/2 |

## bernini__planner_planner / development / long

预定 2 题；记录 2/2；原始轨道 {'long': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.3 | [2.9, 3.6] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 3.4 | [3.0, 3.7] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.2 | [2.9, 3.6] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 0.81 | [0.61, 1.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 77.78 | [55.56, 100.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 0.81 | [0.61, 1.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 0.81 | [0.61, 1.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.1 | [2.8, 3.5] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.5 | [3.3, 3.6] | 2/2 |
| 核心语义保留 (preserve_core) | score | 0.96 | [0.92, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 91.67 | [83.33, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.96 | [0.92, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.96 | [0.92, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 0.75 | [0.50, 1.00] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 0.75 | [0.50, 1.00] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 0.75 | [0.50, 1.00] | 2/2 |
| 时序语义保留 (preserve_time) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 相对独创性 (relative_originality) | rating | 2.2 | [1.8, 2.6] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 2.8 | [2.4, 3.1] | 2/2 |
| 目标风格 (style) | rating | 3.2 | [2.8, 3.7] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.2 | [2.7, 3.8] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.8 | [3.8, 3.8] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 50.00 | [0.00, 100.00] | 2/2 |

## bernini__planner_planner / development / short

预定 2 题；记录 2/2；原始轨道 {'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.8 | [3.6, 3.9] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 3.9 | [3.9, 3.9] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.7 | [3.6, 3.8] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.7 | [3.6, 3.7] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.8 | [3.5, 4.0] | 2/2 |
| 核心语义保留 (preserve_core) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 41.67 | [33.33, 50.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 时序语义保留 (preserve_time) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 相对独创性 (relative_originality) | rating | 2.9 | [2.6, 3.1] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 3.3 | [3.2, 3.4] | 2/2 |
| 目标风格 (style) | rating | 4.0 | [4.0, 4.0] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.8 | [3.5, 4.0] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.9 | [3.8, 4.0] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 2/2 |

## ditto__baseline_long / development / long

预定 4 题；记录 4/4；原始轨道 {'long': 4}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.4 | [3.2, 3.7] | 4/4 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 色彩与纹理 (color_texture) | rating | 3.2 | [2.8, 3.5] | 4/4 |
| 构图与光影 (composition_lighting) | rating | 3.5 | [3.4, 3.7] | 4/4 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 编辑达成 (edit) | score | 0.84 | [0.76, 0.94] | 4/4 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 67.01 | [52.78, 88.89] | 4/4 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 编辑达成下界 (edit_lower) | score | 0.84 | [0.76, 0.94] | 4/4 |
| 编辑达成上界 (edit_upper) | score | 0.84 | [0.76, 0.94] | 4/4 |
| 层次与可读性 (hierarchy_readability) | rating | 3.4 | [3.0, 3.8] | 4/4 |
| 存在重大损伤的比例 (major_damage) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.5 | [3.2, 3.7] | 4/4 |
| 核心语义保留 (preserve_core) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 84.72 | [54.17, 100.00] | 4/4 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 细节保留 (preserve_detail) | score | 0.60 | [0.50, 0.73] | 4/4 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 33.33 | [8.33, 50.00] | 4/4 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 细节保留下界 (preserve_detail_lower) | score | 0.60 | [0.50, 0.73] | 4/4 |
| 细节保留上界 (preserve_detail_upper) | score | 0.60 | [0.50, 0.73] | 4/4 |
| 时序语义保留 (preserve_time) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 79.17 | [58.33, 100.00] | 4/4 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 相对独创性 (relative_originality) | rating | 1.6 | [1.2, 1.9] | 4/4 |
| 场景化设计 (scene_specific_design) | rating | 3.0 | [2.7, 3.2] | 4/4 |
| 目标风格 (style) | rating | 3.2 | [2.8, 3.6] | 4/4 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.5 | [2.9, 4.0] | 4/4 |
| 确认成功比例 (success_confirmed) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 成功比例上界 (success_possible) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.5 | [3.1, 3.9] | 4/4 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 4/4 |

## ditto__baseline_long_keep / development / long

预定 4 题；记录 4/4；原始轨道 {'long': 4}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.5 | [3.1, 3.7] | 4/4 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 色彩与纹理 (color_texture) | rating | 3.2 | [2.3, 3.8] | 4/4 |
| 构图与光影 (composition_lighting) | rating | 3.5 | [3.1, 3.7] | 4/4 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 编辑达成 (edit) | score | 0.86 | [0.77, 0.96] | 4/4 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 72.92 | [54.17, 91.67] | 4/4 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 编辑达成下界 (edit_lower) | score | 0.86 | [0.77, 0.96] | 4/4 |
| 编辑达成上界 (edit_upper) | score | 0.86 | [0.77, 0.96] | 4/4 |
| 层次与可读性 (hierarchy_readability) | rating | 3.5 | [3.1, 3.7] | 4/4 |
| 存在重大损伤的比例 (major_damage) | percent | 50.00 | [0.00, 100.00] | 4/4 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.6 | [3.4, 3.8] | 4/4 |
| 核心语义保留 (preserve_core) | score | 0.91 | [0.83, 1.00] | 4/4 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 86.81 | [73.61, 100.00] | 4/4 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.91 | [0.83, 1.00] | 4/4 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.91 | [0.83, 1.00] | 4/4 |
| 细节保留 (preserve_detail) | score | 0.65 | [0.50, 0.79] | 4/4 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 41.67 | [12.50, 62.50] | 4/4 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 细节保留下界 (preserve_detail_lower) | score | 0.65 | [0.50, 0.79] | 4/4 |
| 细节保留上界 (preserve_detail_upper) | score | 0.65 | [0.50, 0.79] | 4/4 |
| 时序语义保留 (preserve_time) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 79.17 | [58.33, 100.00] | 4/4 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 相对独创性 (relative_originality) | rating | 1.6 | [1.2, 2.0] | 4/4 |
| 场景化设计 (scene_specific_design) | rating | 3.0 | [2.8, 3.3] | 4/4 |
| 目标风格 (style) | rating | 3.4 | [2.8, 3.8] | 4/4 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.8 | [3.6, 3.8] | 4/4 |
| 确认成功比例 (success_confirmed) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 成功比例上界 (success_possible) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.7 | [3.7, 3.8] | 4/4 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 4/4 |

## ditto__baseline_short / development / short

预定 2 题；记录 2/2；原始轨道 {'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.8 | [3.7, 3.8] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 3.8 | [3.7, 3.9] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.7 | [3.7, 3.7] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.6 | [3.5, 3.8] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.8 | [3.7, 3.8] | 2/2 |
| 核心语义保留 (preserve_core) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 0.75 | [0.50, 1.00] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 66.67 | [33.33, 100.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 0.75 | [0.50, 1.00] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 0.75 | [0.50, 1.00] | 2/2 |
| 时序语义保留 (preserve_time) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 相对独创性 (relative_originality) | rating | 2.5 | [2.0, 3.0] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 3.1 | [3.0, 3.2] | 2/2 |
| 目标风格 (style) | rating | 3.9 | [3.7, 4.0] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.9 | [3.8, 4.0] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 4.0 | [3.9, 4.0] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 50.00 | [0.00, 100.00] | 2/2 |

## ditto__planner_planner / development / long

预定 2 题；记录 2/2；原始轨道 {'long': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.7 | [3.7, 3.7] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 3.6 | [3.5, 3.8] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.7 | [3.6, 3.7] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 0.84 | [0.69, 1.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 75.00 | [50.00, 100.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 0.84 | [0.69, 1.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 0.84 | [0.69, 1.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.5 | [3.5, 3.6] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.7 | [3.7, 3.7] | 2/2 |
| 核心语义保留 (preserve_core) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 83.33 | [66.67, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 75.00 | [50.00, 100.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 时序语义保留 (preserve_time) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 75.00 | [50.00, 100.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.88 | [0.75, 1.00] | 2/2 |
| 相对独创性 (relative_originality) | rating | 2.0 | [2.0, 2.0] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 3.0 | [3.0, 3.0] | 2/2 |
| 目标风格 (style) | rating | 3.5 | [3.1, 3.9] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.8 | [3.6, 4.0] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.8 | [3.6, 4.0] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 2/2 |

## ditto__planner_planner / development / short

预定 2 题；记录 2/2；原始轨道 {'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.7 | [3.6, 3.8] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 3.7 | [3.6, 3.8] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.7 | [3.6, 3.7] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.6 | [3.4, 3.9] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.8 | [3.8, 3.9] | 2/2 |
| 核心语义保留 (preserve_core) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留 (preserve_time) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 相对独创性 (relative_originality) | rating | 2.2 | [2.2, 2.2] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 3.1 | [3.0, 3.3] | 2/2 |
| 目标风格 (style) | rating | 3.9 | [3.7, 4.0] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.8 | [3.8, 3.9] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.7 | [3.6, 3.7] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |

## source_control / development / long

预定 2 题；记录 2/2；原始轨道 {'long': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.0 | [2.9, 3.0] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 1.9 | [1.8, 2.0] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 2.8 | [2.8, 2.8] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 0.00 | [0.00, 0.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 0.00 | [0.00, 0.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 0.00 | [0.00, 0.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.8 | [3.6, 4.0] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 2.4 | [2.2, 2.5] | 2/2 |
| 核心语义保留 (preserve_core) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留 (preserve_time) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 相对独创性 (relative_originality) | rating | 1.0 | [1.0, 1.0] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 1.0 | [1.0, 1.0] | 2/2 |
| 目标风格 (style) | rating | 1.0 | [1.0, 1.0] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 4.0 | [4.0, 4.0] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 4.0 | [4.0, 4.0] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |

## source_control / development / short

预定 2 题；记录 2/2；原始轨道 {'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.1 | [2.8, 3.4] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 2.2 | [2.0, 2.5] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.1 | [2.7, 3.5] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 0.00 | [0.00, 0.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 0.00 | [0.00, 0.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 0.00 | [0.00, 0.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.2 | [2.8, 3.7] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 2.9 | [2.5, 3.2] | 2/2 |
| 核心语义保留 (preserve_core) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留 (preserve_time) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 1.00 | [1.00, 1.00] | 2/2 |
| 相对独创性 (relative_originality) | rating | 1.0 | [1.0, 1.0] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 1.0 | [1.0, 1.0] | 2/2 |
| 目标风格 (style) | rating | 1.0 | [1.0, 1.0] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 4.0 | [4.0, 4.0] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 4.0 | [4.0, 4.0] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 0.00 | [0.00, 0.00] | 2/2 |
