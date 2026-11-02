# 当前状态 — 2026-11-03

当前开发版入口为 [README](../README.md)、[Loop 实现](creative-loop-implementation.md)、[配置](benchmark-guide/configuration.md) 和 [实验运行安排](experiment-campaign.md)。用户已授权四视频长任务效果预览，卡管理会话负责设备和部署。订阅接入已实际运行，当前正在修复真实任务暴露的多消息拼接与断流诊断问题。

## 2026-11-03 四视频预览接入

- 官方 ChatGPT 订阅 Responses 后端已实现，见 [登录、配置与运行说明](chatgpt-subscription.md)。保留现有 Planner／Critic 提示词、原图传输与使用量记录，独立于 Codex CLI。
- 订阅与 Loop 相关 91 项离线测试通过；明确样本选择与结果管理另 34 项通过。用户已在 Edge 完成 LHA 授权，真实 `gpt-6.1-sol/high` Responses 调用正确识别左红右蓝图像，完整结束并返回 79 个 token 的 usage。回执位于 `out/chatgpt_subscription_probe/live/`。
- `--sample-ids` 已实际准备 001、005、026、067 的 long 任务：full、direct、pe-loop 三组，共 12 条轨迹；Loop 含首轮最多 4 次、每任务一小时，关闭本次共享经验维护和终评。
- 四张卡已开始实际运行。2026-11-03 01:42（UTC+8）快照：4 个 Direct 已完成，005 Full 已交付；001 Full 继续生成，005／026／067 PE 在生成。026／067 原 Full 在首次视频生成前因第 6 次 Planner 调用缺少流终态停止。
- 调查确认另一个独立缺陷：客户端曾拼接多个助手消息，6 次已返回调用因此形成说明加重复 JSON。现已改为按 phase 提取最终消息，保留原始输出；客户端和中转层新增同请求编号的原始流、异常阶段与完整响应记录。此前两次断流缺少原始事件，具体断点仍未知。修复版 7 个相关模块、105 项离线测试全部通过。两台真实 Planner 格式调用已返回完整 SSE 和 final_answer；中转将类型标成 application/json，曾触发新增头部检查误拒。现改为按实际 SSE 帧与完成状态判定，两份真实响应零新调用重放均通过，补充 34 项回归通过。原运行记录保留。
- 同步清单、离线检查和授权状态分别保存在 `out/four_video_preview_20261102/backend-readiness.json`、`out/chatgpt_subscription_probe/`；卡管理部署及运行动态状态在 `out/four_video_preview_20261102/dispatch-status.json`。

## 代码与 Loop

- **API-only。** Planner／Critic 默认 `openai/gpt-6.1-sol`、high；共享模型、环境和角色参数解析集中到 `vlm.settings`。旧本地模型与 LiteLLM 按需导入，当前路径不启动 Codex CLI。
- **每次生成后检查。** 默认独立定性 Critic，可切 Planner 自评；两者共用原生 PTS 连续帧、分页、裁剪、重看。正式终评校验移至 `evaluation.validation`，独立判官工厂读取 `configs/evaluation.json`；历史直连接口独立存放。
- **交付与恢复。** `finish` 复用已有检查；明确的 Critic 失败返回 Planner。服务恢复已经保存的模型回答，避免重复请求。有效自评可以保留，随后无效动作单独返回错误。
- **任务与资源隔离。** 默认服务使用每任务 N／一小时策略；不再隐式套用旧 96 调用／400 万 token／900 秒限制。未知模型调用隔离相应任务；未知 GPU 执行保留该设备占用，其他设备继续工作。
- **经验与结果。** 已知训练／维护失败保留覆盖和此前经验版本；未知执行仍沿原请求恢复。Direct 完成回执可恢复收取，媒体同文件系统可硬链接复用。经验阅读导出包含定性 summary／findings 和实际单次交付记录。

调用、token、usage 和已知费用继续记录；在线任务的主限制为生成次数与期限。Planner 保留模糊资源提醒。任务后维护单独计量，GLM／Sonnet 正式终评没有人为调用、token 或金额额度。

## 当前验证

统一离线入口为 `python scripts/check_repository.py --suite current`。每模块独立进程，只运行本模块定义的测试，防止导入 fixture 重复计数。最终整合检查 **29 个模块、325 个独立测试全部通过**，测试期间源码与配置无变化。471 个 Python 文件通过语法检查，全部 `src/`／`scripts/` 通过未定义名称及关键语法静态检查；10 个配置可解析，六个主要命令入口可加载，11 份当前文档的本地链接有效。详见 [验证记录](../reports/maintenance-20261102/engineering-cleanup-validation.json)，逐模块日志与源码指纹位于 `out/engineering_cleanup_20261102/final/`。

当前与历史协议的测试已区分。旧数值在线评分、二次交付确认及旧 RSI 的部分断言不再适用，保留给相应兼容路径使用；本轮不以这些旧用例宣称当前协议覆盖。先前 133、390 等测试数量是各自阶段记录，不累加为本轮结果。

## 实验配置与数据

唯一清单为 `benchmark_data/benchmark.json`。当前 67 条、short／long 共 134 个条件；RSI 划分 40／27，主实验四组都覆盖全量。先跑无经验组，前段逐题维护、后段只运行；冻结经验后 full 跑全量。Planner 最多 4 次，PE 最多 4 次，每任务一小时。主实验与 RSI 子集共享视频及评分，具体计划通过 campaign 的 `plan` 命令计算。

数据、提示词与经验内容仍由各自已授权维护任务管理。本轮保留视频、冻结交接包与 Git 历史，调整当前代码、配置和操作文档。

## 真实接入的已知状态

先前 SSH 转发检查中，OpenRouter 鉴权返回 200，GLM 正确识别一张红／蓝合成图；GPT 与 Sonnet 返回地区不可用 403。路由诊断停在 `Gate Endpoints with Geo Restrictions`，尚未选中模型提供商。记录在 `out/api_route_20261102/`；本轮未重新测试该外部状态，也未更换实验模型。

现代 Direct 恢复当前支持收取原完成回执；确认未执行后创建全新替代 attempt 尚未实现。

四视频真实运行已产生 Direct 和部分 Loop 视频，动态状态见上述执行记录。正式评价与链式 v2v 画质结论仍待对应评价完成。
