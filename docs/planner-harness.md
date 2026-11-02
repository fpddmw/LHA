# Planner Harness

当前主线为 `creative_loop_v1`，完整状态流见 [Loop 设计](creative-loop-implementation.md)。模型由 API 客户端提供，运行目录保存实际输入、响应、动作、视频和恢复信息。

## 当前动作

Planner 可 `read`／`search` 知识、`observe` 视频、维护 `note`／`workspace`、`generate` 新视频、指定 `delivery_candidate`，并通过 `finish` 交付或合法停止。Planner 自评模式另接收 `review`；它可以与下一动作同次提交。精确动作格式由运行时 [操作手册](../src/planner_harness/CREATIVE_LOOP.md) 提供。

`generate` 明确输入视频和提示词，可提供 `review_focus`。所有成功生成都进入配置的检查路径。选择交付候选不会偷偷改变下一次生成输入；最终交付不额外发起评审。

## 上下文与检索

`context.py` 组织原始任务、候选、工作记录、读取材料及最近结果；`working_memory.py` 管理笔记与文本预算；`creative_knowledge.py` 按 full／none 权限提供入口、搜索和分页。观察支持原生 PTS 连续帧、概览、裁剪、翻页和重开记录。图片传输使用 API 客户端实际记录的附件。

无经验组在 RSI 训练部分的任务后维护累计私有经验，在线始终使用 none；后段只运行不维护。full 在全量任务上读取训练结束的固定快照，none 不读取经验。review 操作指南在两种知识条件下都可见，经验内容不因检查方式泄露给 none。

## 运行和恢复

- 单任务入口：`scripts/run_planner_harness.py`。
- 生成工具 worker：`scripts/run_planner_worker.py`。
- 实验入口：`scripts/run_experiment_campaign.py`。
- 多任务服务：[server-runtime.md](server-runtime.md)。

默认生成上限 5 次、在线期限一小时；恢复使用原有计数和截止时间。已保存回答或工具回执应沿原调用恢复；明确失败返回可处理的结果，未知外部执行按原任务核实。运行中的配置变更使用新目录，不修改已有回执。

旧 proposal-only／RSI 实现在 `planner_harness.compat`，用于历史运行解析和对应兼容测试，不定义当前主实验协议。
