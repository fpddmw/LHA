# 视频编辑评价（展示口径 v2）

语义为 0–1 分（分组加权计算分），完整完成比例、成功比例与覆盖率为 %。VLM 原始评分为 1–4、0.1 步长；下表 VLM 列均为计算均值，显示一位小数。美学计算均值先平均五项原始评分。JSON/CSV 保留完整计算精度。

每题先汇总 seed，同源多题先等权合并，再按源宏平均；预定缺项保留分母。短/长沿原始任务卡，Planner 扩写不改变 track。未知保留界限和覆盖率，分项分别解释。

## bernini_direct / development / all

预定 4 题；记录 4/4；原始轨道 {'long': 2, 'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.2 | [2.8, 3.5] | 4/4 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 色彩与纹理 (color_texture) | rating | 3.2 | [2.9, 3.5] | 4/4 |
| 构图与光影 (composition_lighting) | rating | 3.3 | [2.8, 3.5] | 4/4 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 编辑达成 (edit) | score | 0.65 | [0.21, 0.96] | 4/4 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 57.29 | [16.67, 91.67] | 4/4 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 编辑达成下界 (edit_lower) | score | 0.65 | [0.21, 0.96] | 4/4 |
| 编辑达成上界 (edit_upper) | score | 0.65 | [0.21, 0.96] | 4/4 |
| 层次与可读性 (hierarchy_readability) | rating | 3.2 | [2.5, 3.7] | 4/4 |
| 存在重大损伤的比例 (major_damage) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.2 | [2.8, 3.5] | 4/4 |
| 核心语义保留 (preserve_core) | score | 0.95 | [0.85, 1.00] | 4/4 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 90.28 | [70.83, 100.00] | 4/4 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.95 | [0.85, 1.00] | 4/4 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.95 | [0.85, 1.00] | 4/4 |
| 细节保留 (preserve_detail) | score | 0.52 | [0.37, 0.69] | 4/4 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 33.33 | [12.50, 50.00] | 4/4 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 细节保留下界 (preserve_detail_lower) | score | 0.52 | [0.37, 0.69] | 4/4 |
| 细节保留上界 (preserve_detail_upper) | score | 0.52 | [0.37, 0.69] | 4/4 |
| 时序语义保留 (preserve_time) | score | 0.85 | [0.71, 1.00] | 4/4 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 70.83 | [41.67, 100.00] | 4/4 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.85 | [0.71, 1.00] | 4/4 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.85 | [0.71, 1.00] | 4/4 |
| 相对独创性 (relative_originality) | rating | 1.9 | [1.2, 2.5] | 4/4 |
| 场景化设计 (scene_specific_design) | rating | 2.5 | [1.5, 3.1] | 4/4 |
| 目标风格 (style) | rating | 2.6 | [1.6, 3.3] | 4/4 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.3 | [2.5, 3.9] | 4/4 |
| 确认成功比例 (success_confirmed) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 成功比例上界 (success_possible) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.8 | [3.7, 4.0] | 4/4 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 4/4 |

## bernini_direct / development / long

预定 2 题；记录 2/2；原始轨道 {'long': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.4 | [3.3, 3.5] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 3.3 | [3.0, 3.6] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.5 | [3.5, 3.6] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 0.79 | [0.75, 0.83] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 64.58 | [62.50, 66.67] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 0.79 | [0.75, 0.83] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 0.79 | [0.75, 0.83] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.3 | [3.3, 3.4] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.5 | [3.4, 3.7] | 2/2 |
| 核心语义保留 (preserve_core) | score | 0.90 | [0.81, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 80.56 | [61.11, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.90 | [0.81, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.90 | [0.81, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 25.00 | [0.00, 50.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 时序语义保留 (preserve_time) | score | 0.71 | [0.67, 0.75] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 41.67 | [33.33, 50.00] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.71 | [0.67, 0.75] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.71 | [0.67, 0.75] | 2/2 |
| 相对独创性 (relative_originality) | rating | 2.3 | [2.0, 2.6] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 3.1 | [3.0, 3.2] | 2/2 |
| 目标风格 (style) | rating | 3.1 | [2.8, 3.4] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.5 | [3.4, 3.5] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.7 | [3.6, 3.7] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 2/2 |

## bernini_direct / development / short

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

## bernini_planner / development / all

预定 4 题；记录 4/4；原始轨道 {'long': 2, 'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.5 | [3.1, 3.8] | 4/4 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 色彩与纹理 (color_texture) | rating | 3.6 | [3.2, 3.9] | 4/4 |
| 构图与光影 (composition_lighting) | rating | 3.5 | [3.1, 3.8] | 4/4 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 编辑达成 (edit) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 88.89 | [66.67, 100.00] | 4/4 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 编辑达成下界 (edit_lower) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 编辑达成上界 (edit_upper) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 层次与可读性 (hierarchy_readability) | rating | 3.4 | [3.0, 3.7] | 4/4 |
| 存在重大损伤的比例 (major_damage) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.6 | [3.4, 3.9] | 4/4 |
| 核心语义保留 (preserve_core) | score | 0.98 | [0.94, 1.00] | 4/4 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 95.83 | [87.50, 100.00] | 4/4 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.98 | [0.94, 1.00] | 4/4 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.98 | [0.94, 1.00] | 4/4 |
| 细节保留 (preserve_detail) | score | 0.69 | [0.50, 0.88] | 4/4 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 45.83 | [12.50, 83.33] | 4/4 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 细节保留下界 (preserve_detail_lower) | score | 0.69 | [0.50, 0.88] | 4/4 |
| 细节保留上界 (preserve_detail_upper) | score | 0.69 | [0.50, 0.88] | 4/4 |
| 时序语义保留 (preserve_time) | score | 1.00 | [1.00, 1.00] | 4/4 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 时序语义保留下界 (preserve_time_lower) | score | 1.00 | [1.00, 1.00] | 4/4 |
| 时序语义保留上界 (preserve_time_upper) | score | 1.00 | [1.00, 1.00] | 4/4 |
| 相对独创性 (relative_originality) | rating | 2.5 | [2.0, 3.0] | 4/4 |
| 场景化设计 (scene_specific_design) | rating | 3.0 | [2.6, 3.3] | 4/4 |
| 目标风格 (style) | rating | 3.6 | [3.1, 4.0] | 4/4 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.5 | [3.0, 3.9] | 4/4 |
| 确认成功比例 (success_confirmed) | percent | 75.00 | [25.00, 100.00] | 4/4 |
| 成功比例上界 (success_possible) | percent | 75.00 | [25.00, 100.00] | 4/4 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.8 | [3.8, 4.0] | 4/4 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 75.00 | [25.00, 100.00] | 4/4 |

## bernini_planner / development / long

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

## bernini_planner / development / short

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

## ditto_direct / development / all

预定 4 题；记录 4/4；原始轨道 {'long': 2, 'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.6 | [3.3, 3.8] | 4/4 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 色彩与纹理 (color_texture) | rating | 3.7 | [3.5, 3.8] | 4/4 |
| 构图与光影 (composition_lighting) | rating | 3.6 | [3.5, 3.7] | 4/4 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 编辑达成 (edit) | score | 0.95 | [0.86, 1.00] | 4/4 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 90.62 | [71.88, 100.00] | 4/4 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 编辑达成下界 (edit_lower) | score | 0.95 | [0.86, 1.00] | 4/4 |
| 编辑达成上界 (edit_upper) | score | 0.95 | [0.86, 1.00] | 4/4 |
| 层次与可读性 (hierarchy_readability) | rating | 3.5 | [3.0, 3.8] | 4/4 |
| 存在重大损伤的比例 (major_damage) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.5 | [3.2, 3.8] | 4/4 |
| 核心语义保留 (preserve_core) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 84.72 | [54.17, 100.00] | 4/4 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.90 | [0.71, 1.00] | 4/4 |
| 细节保留 (preserve_detail) | score | 0.69 | [0.50, 0.94] | 4/4 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 45.83 | [12.50, 87.50] | 4/4 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 细节保留下界 (preserve_detail_lower) | score | 0.69 | [0.50, 0.94] | 4/4 |
| 细节保留上界 (preserve_detail_upper) | score | 0.69 | [0.50, 0.94] | 4/4 |
| 时序语义保留 (preserve_time) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 79.17 | [58.33, 100.00] | 4/4 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.90 | [0.79, 1.00] | 4/4 |
| 相对独创性 (relative_originality) | rating | 2.2 | [1.9, 2.8] | 4/4 |
| 场景化设计 (scene_specific_design) | rating | 3.0 | [2.8, 3.2] | 4/4 |
| 目标风格 (style) | rating | 3.6 | [3.1, 4.0] | 4/4 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.6 | [3.0, 4.0] | 4/4 |
| 确认成功比例 (success_confirmed) | percent | 50.00 | [0.00, 100.00] | 4/4 |
| 成功比例上界 (success_possible) | percent | 50.00 | [0.00, 100.00] | 4/4 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.7 | [3.1, 4.0] | 4/4 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 75.00 | [25.00, 100.00] | 4/4 |

## ditto_direct / development / long

预定 2 题；记录 2/2；原始轨道 {'long': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.4 | [3.1, 3.7] | 2/2 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 色彩与纹理 (color_texture) | rating | 3.5 | [3.5, 3.6] | 2/2 |
| 构图与光影 (composition_lighting) | rating | 3.5 | [3.5, 3.6] | 2/2 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/2 |
| 编辑达成 (edit) | score | 0.91 | [0.81, 1.00] | 2/2 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 81.25 | [62.50, 100.00] | 2/2 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 编辑达成下界 (edit_lower) | score | 0.91 | [0.81, 1.00] | 2/2 |
| 编辑达成上界 (edit_upper) | score | 0.91 | [0.81, 1.00] | 2/2 |
| 层次与可读性 (hierarchy_readability) | rating | 3.3 | [2.9, 3.8] | 2/2 |
| 存在重大损伤的比例 (major_damage) | percent | 50.00 | [0.00, 100.00] | 2/2 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.3 | [3.1, 3.5] | 2/2 |
| 核心语义保留 (preserve_core) | score | 0.81 | [0.61, 1.00] | 2/2 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 69.44 | [38.89, 100.00] | 2/2 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.81 | [0.61, 1.00] | 2/2 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.81 | [0.61, 1.00] | 2/2 |
| 细节保留 (preserve_detail) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 25.00 | [0.00, 50.00] | 2/2 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 细节保留下界 (preserve_detail_lower) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 细节保留上界 (preserve_detail_upper) | score | 0.62 | [0.50, 0.75] | 2/2 |
| 时序语义保留 (preserve_time) | score | 0.79 | [0.75, 0.83] | 2/2 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 58.33 | [50.00, 66.67] | 2/2 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 2/2 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.79 | [0.75, 0.83] | 2/2 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.79 | [0.75, 0.83] | 2/2 |
| 相对独创性 (relative_originality) | rating | 1.9 | [1.9, 2.0] | 2/2 |
| 场景化设计 (scene_specific_design) | rating | 3.0 | [2.7, 3.3] | 2/2 |
| 目标风格 (style) | rating | 3.3 | [2.8, 3.9] | 2/2 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.3 | [2.6, 4.0] | 2/2 |
| 确认成功比例 (success_confirmed) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 成功比例上界 (success_possible) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 2/2 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.5 | [2.9, 4.0] | 2/2 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 100.00 | [100.00, 100.00] | 2/2 |

## ditto_direct / development / short

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

## ditto_planner / development / all

预定 4 题；记录 4/4；原始轨道 {'long': 2, 'short': 2}。

| 指标 | 单位 | 分数或计算均值 | 95% CI | 有效/预定源数 |
|---|---|---:|---|---:|
| 美学计算均值 (aesthetic_mean) | rating | 3.7 | [3.7, 3.8] | 4/4 |
| clip_f (clip_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 色彩与纹理 (color_texture) | rating | 3.7 | [3.5, 3.8] | 4/4 |
| 构图与光影 (composition_lighting) | rating | 3.7 | [3.6, 3.7] | 4/4 |
| 有效交付比例 (delivery_valid) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| dino_f (dino_f) | cosine | 未知 / 未测 | N/A | 0/4 |
| 编辑达成 (edit) | score | 0.92 | [0.77, 1.00] | 4/4 |
| 编辑达成：完整完成比例 (edit_complete_rate) | percent | 87.50 | [62.50, 100.00] | 4/4 |
| 编辑达成：证据覆盖率 (edit_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 编辑达成下界 (edit_lower) | score | 0.92 | [0.77, 1.00] | 4/4 |
| 编辑达成上界 (edit_upper) | score | 0.92 | [0.77, 1.00] | 4/4 |
| 层次与可读性 (hierarchy_readability) | rating | 3.6 | [3.5, 3.8] | 4/4 |
| 存在重大损伤的比例 (major_damage) | percent | 25.00 | [0.00, 75.00] | 4/4 |
| 叙事与情绪 (narrative_emotional_fit) | rating | 3.8 | [3.7, 3.9] | 4/4 |
| 核心语义保留 (preserve_core) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 核心语义保留：完整完成比例 (preserve_core_complete_rate) | percent | 91.67 | [75.00, 100.00] | 4/4 |
| 核心语义保留：证据覆盖率 (preserve_core_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 核心语义保留下界 (preserve_core_lower) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 核心语义保留上界 (preserve_core_upper) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 细节保留 (preserve_detail) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 细节保留：完整完成比例 (preserve_detail_complete_rate) | percent | 87.50 | [62.50, 100.00] | 4/4 |
| 细节保留：证据覆盖率 (preserve_detail_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 细节保留下界 (preserve_detail_lower) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 细节保留上界 (preserve_detail_upper) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 时序语义保留 (preserve_time) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 时序语义保留：完整完成比例 (preserve_time_complete_rate) | percent | 87.50 | [62.50, 100.00] | 4/4 |
| 时序语义保留：证据覆盖率 (preserve_time_coverage) | percent | 100.00 | [100.00, 100.00] | 4/4 |
| 时序语义保留下界 (preserve_time_lower) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 时序语义保留上界 (preserve_time_upper) | score | 0.94 | [0.81, 1.00] | 4/4 |
| 相对独创性 (relative_originality) | rating | 2.1 | [2.0, 2.2] | 4/4 |
| 场景化设计 (scene_specific_design) | rating | 3.1 | [3.0, 3.2] | 4/4 |
| 目标风格 (style) | rating | 3.7 | [3.3, 4.0] | 4/4 |
| 风格与世界一致性 (style_world_consistency) | rating | 3.8 | [3.6, 4.0] | 4/4 |
| 确认成功比例 (success_confirmed) | percent | 50.00 | [0.00, 100.00] | 4/4 |
| 成功比例上界 (success_possible) | percent | 50.00 | [0.00, 100.00] | 4/4 |
| 待判定比例 (success_unresolved) | percent | 0.00 | [0.00, 0.00] | 4/4 |
| 视频自身时序协调 (temporal_coherence) | rating | 3.7 | [3.6, 3.9] | 4/4 |
| 存在非预期损伤的比例 (unrequested_damage) | percent | 50.00 | [0.00, 100.00] | 4/4 |

## ditto_planner / development / long

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

## ditto_planner / development / short

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
