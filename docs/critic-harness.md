# 在线 Critic 与 Planner 自评

当前在线协议为 `lha-qualitative-review-v1`，默认 `review.mode=critic`。它服务于任务内决策；正式评分见 [独立终评](low-high-evaluation-v2.md)。

每次成功生成后，独立 Critic 获得原始任务、提交与实际生效提示词、Planner 的 focus／补充问题、源片、实际输入、候选及参考。Critic 按需调用共享观察器取证，返回 `summary` 和可选 `findings`，给出评价与证据，不输出编辑建议。没有固定分数、正式 task_metrics、评分手册或强制的防御性栏目。

`review.mode=planner` 使用同一观察基础设施，由 Planner 在当前任务上下文中提交自评。两种路径都覆盖每轮生成，包括最后一轮；交付复用已有检查。

## 实现边界

- `critic_harness.qualitative`：检查会话、取证动作、报告与恢复。
- `planner_harness.automatic_review`：生成后排入检查及交回 Planner。
- `planner_harness.video`／`event_observation`：六帧概览、原生连续帧、分页、裁剪和重开。
- [Video review Skill](../.agents/skills/lha-video-review/SKILL.md)：共享检查指南。
- `critic_harness.one_shot`：历史导入兼容；正式数值校验迁至 `evaluation.validation`。

focus 是原样传递的关注重点，`extra_checks` 为补充问题，`events` 可定位时间，`compare_to` 指定比较对象。它们不被替换成正式评分项目，也不要求中性描述通过建议正则。

明确的模型／工具失败返回 Planner；未知外部执行沿原调用恢复。报告解析、证据选择和交付分别处理，避免一份错误报告把整个批次卡住。连续性结论使用实际连续帧证据，概览用于定位。

当前模型和 API 由 [配置说明](benchmark-guide/configuration.md) 管理；本页不把离线脚本报告视为真实模型质量证据。
