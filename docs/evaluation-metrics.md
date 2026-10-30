# 统一评价指标定义（自动生成）

定义版本：`lha-metrics-v3`；计算版本：`lha-score-v3`。

原始判断 → 确定性计算分 → seed/任务/源三级统计。语义为 0–1 分，先组内平均再组间等权，显示 2 位小数。VLM 原始评分为 1.0–4.0、0.1 步长，原始分及计算均值显示 1 位。完整完成比例、成功比例和覆盖率单列 %。未知、不适用和执行失败分别统计；JSON/CSV 保留完整精度。

unknown 仅表示证据不足；not_applicable 由冻结卡决定并从适用分母排除；执行失败、缺视频、待测和旧状态缺失分别计数。

| 指标 ID | 名称与定义 | 尺度／单位 | 小数位 | 计算方式 | 适用性 |
|---|---|---|---:|---|---|
| `edit` | 编辑达成：原始用户要求的修改是否完成 | [0, 1] / score | 2 | `item_mean_within_group_then_equal_group_mean` | `selected_card_items` |
| `edit_lower` | 编辑达成：证据下界：原始用户要求的修改是否完成；证据下界 | [0, 1] / score | 2 | `unknown_labels_at_zero` | `selected_card_items` |
| `edit_upper` | 编辑达成：证据上界：原始用户要求的修改是否完成；证据上界 | [0, 1] / score | 2 | `unknown_labels_at_one` | `selected_card_items` |
| `edit_coverage` | 编辑达成：证据覆盖率：原始用户要求的修改是否完成；证据覆盖率 | [0, 100] / percent | 2 | `group_weighted_known_item_fraction_times_100` | `selected_card_items` |
| `edit_complete_rate` | 编辑达成：完整完成比例：原始用户要求的修改是否完成；完整完成比例 | [0, 100] / percent | 2 | `group_weighted_pass_fraction_times_100` | `selected_card_items` |
| `preserve_core` | 核心语义保留：未授权改变的关键主体、行为与关系是否保留 | [0, 1] / score | 2 | `item_mean_within_group_then_equal_group_mean` | `selected_card_items` |
| `preserve_core_lower` | 核心语义保留：证据下界：未授权改变的关键主体、行为与关系是否保留；证据下界 | [0, 1] / score | 2 | `unknown_labels_at_zero` | `selected_card_items` |
| `preserve_core_upper` | 核心语义保留：证据上界：未授权改变的关键主体、行为与关系是否保留；证据上界 | [0, 1] / score | 2 | `unknown_labels_at_one` | `selected_card_items` |
| `preserve_core_coverage` | 核心语义保留：证据覆盖率：未授权改变的关键主体、行为与关系是否保留；证据覆盖率 | [0, 100] / percent | 2 | `group_weighted_known_item_fraction_times_100` | `selected_card_items` |
| `preserve_core_complete_rate` | 核心语义保留：完整完成比例：未授权改变的关键主体、行为与关系是否保留；完整完成比例 | [0, 100] / percent | 2 | `group_weighted_pass_fraction_times_100` | `selected_card_items` |
| `preserve_detail` | 细节语义保留：冻结卡所列非核心细节是否保留 | [0, 1] / score | 2 | `item_mean_within_group_then_equal_group_mean` | `selected_card_items` |
| `preserve_detail_lower` | 细节语义保留：证据下界：冻结卡所列非核心细节是否保留；证据下界 | [0, 1] / score | 2 | `unknown_labels_at_zero` | `selected_card_items` |
| `preserve_detail_upper` | 细节语义保留：证据上界：冻结卡所列非核心细节是否保留；证据上界 | [0, 1] / score | 2 | `unknown_labels_at_one` | `selected_card_items` |
| `preserve_detail_coverage` | 细节语义保留：证据覆盖率：冻结卡所列非核心细节是否保留；证据覆盖率 | [0, 100] / percent | 2 | `group_weighted_known_item_fraction_times_100` | `selected_card_items` |
| `preserve_detail_complete_rate` | 细节语义保留：完整完成比例：冻结卡所列非核心细节是否保留；完整完成比例 | [0, 100] / percent | 2 | `group_weighted_pass_fraction_times_100` | `selected_card_items` |
| `preserve_time` | 时序语义保留：原视频动作、事件顺序与时序关系是否保留 | [0, 1] / score | 2 | `item_mean_within_group_then_equal_group_mean` | `selected_card_items` |
| `preserve_time_lower` | 时序语义保留：证据下界：原视频动作、事件顺序与时序关系是否保留；证据下界 | [0, 1] / score | 2 | `unknown_labels_at_zero` | `selected_card_items` |
| `preserve_time_upper` | 时序语义保留：证据上界：原视频动作、事件顺序与时序关系是否保留；证据上界 | [0, 1] / score | 2 | `unknown_labels_at_one` | `selected_card_items` |
| `preserve_time_coverage` | 时序语义保留：证据覆盖率：原视频动作、事件顺序与时序关系是否保留；证据覆盖率 | [0, 100] / percent | 2 | `group_weighted_known_item_fraction_times_100` | `selected_card_items` |
| `preserve_time_complete_rate` | 时序语义保留：完整完成比例：原视频动作、事件顺序与时序关系是否保留；完整完成比例 | [0, 100] / percent | 2 | `group_weighted_pass_fraction_times_100` | `selected_card_items` |
| `style` | 目标风格：输出对用户指定风格的实现程度 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `style_required` |
| `narrative_emotional_fit` | 叙事与情绪契合：画面设计对场景行为、情绪和要求的支持 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `always` |
| `style_world_consistency` | 风格与世界一致性：人物、物件和环境的设计协调 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `always` |
| `composition_lighting` | 构图与光影：构图、空间、明暗及光源的协调 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `always` |
| `color_texture` | 色彩与纹理：配色、材质与纹理的组织质量 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `always` |
| `hierarchy_readability` | 层次与可读性：主体、物件、动作及焦点是否清晰 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `always` |
| `temporal_coherence` | 输出自身时序协调：输出自身外观、结构、材质和运动的连续性 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `always` |
| `scene_specific_design` | 场景化设计：在允许空间中利用原场景主体、空间、物件和行为进行设计 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `creativity_enabled` |
| `relative_originality` | 相对独创性：相对固定同题匿名参照集合的有效设计差异 | [1.0, 4.0] / rating | 1 | `raw_vlm_rating` | `creativity_enabled` |
| `aesthetic_mean` | 美学计算均值：五项美学原始评分等权平均 | [1.0, 4.0] / rating | 1 | `equal_component_mean` | `always` |
| `success_confirmed` | 确认成功比例：确认通过整题成功条件的预定任务比例（下界） | [0, 100] / percent | 2 | `binary_indicator_times_100` | `always` |
| `success_possible` | 成功比例上界：已通过及尚可能通过的预定任务比例 | [0, 100] / percent | 2 | `binary_indicator_times_100` | `always` |
| `success_unresolved` | 成功待判定比例：整题成功条件仍待确认的预定任务比例 | [0, 100] / percent | 2 | `binary_indicator_times_100` | `always` |
| `delivery_valid` | 有效交付比例：已确认有效交付的预定任务比例（下界） | [0, 100] / percent | 2 | `binary_indicator_times_100` | `always` |
| `unrequested_damage` | 非预期损伤比例：存在超出允许修改范围的损伤的视频比例 | [0, 100] / percent | 2 | `binary_indicator_times_100` | `always` |
| `major_damage` | 重大损伤比例：存在关键主体、行为或硬约束重大损伤的视频比例 | [0, 100] / percent | 2 | `binary_indicator_times_100` | `always` |
| `clip_f` | CLIP_F：输出视频自身相邻采样帧特征的平均余弦相似度 | [-1, 1] / cosine | 4 | `adjacent_normalized_feature_cosine_mean` | `always` |
| `dino_f` | DINO_F：输出视频自身相邻采样帧特征的平均余弦相似度 | [-1, 1] / cosine | 4 | `adjacent_normalized_feature_cosine_mean` | `always` |

统计：同任务 seed 等权；同源原始任务等权；源视频等权。未知或失败 seed 保持该源点估计缺失，适用范围内的源分母保留。报告有效源均值、适用/预定源数、覆盖率及独立状态计数。

语义总体上下界沿相同层次汇总每条语义证据上下界；执行缺项使用 [0,1] 的可行范围，分别报告错误计数。这些是证据/缺项界限，源级 bootstrap 置信区间只针对有效源均值。

整题成功：有效交付、mandatory 及核心项全部 pass、无重大非预期损伤；风格任务另需 style ≥ 3.0。成功未知保留上下界，不以视觉均分补偿语义硬失败。

本文件由 `python scripts/eval/export_metric_definitions.py` 生成；修改源为 `src/evaluation/registry.py`。
