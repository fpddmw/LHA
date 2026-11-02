# 文档入口

当前开发版从下表进入。运行数量读取 `benchmark_data/benchmark.json` 和 campaign plan；运行状态集中在 `current-status.md`。历史文档中的“已启动／暂停／待执行”只描述当时的任务。

| 内容 | 当前说明 | 对应实现 |
|---|---|---|
| 完整 Loop 与模块边界 | [实现说明](creative-loop-implementation.md) | `planner_harness`、`critic_harness` |
| Planner 动作、上下文、恢复 | [Planner](planner-harness.md) | `runner`、`creative_actions`、`context` |
| 每次生成后的定性检查 | [Critic](critic-harness.md) | `qualitative`、`automatic_review` |
| 连续帧、分页、裁剪、重看 | [观察能力](online-event-observation.md) | `video`、`event_observation` |
| 模型、任务与主机配置 | [配置说明](benchmark-guide/configuration.md) | `vlm.settings`、`configs/` |
| ChatGPT 订阅授权与图像调用 | [订阅接入](chatgpt-subscription.md) | `vlm.chatgpt_auth`、`vlm.chatgpt_subscription` |
| GPU 服务、失败与恢复 | [运行服务](server-runtime.md) | `server_runtime`、`device_scheduler` |
| 全量主实验与 RSI 子集 | [实验运行安排](experiment-campaign.md) | `experiments.campaign` |
| PE 固定流程基线 | [PE Loop](pe-loop.md) | `experiments.pe_loop` |
| 终评与分析 | [评价协议](low-high-evaluation-v2.md)、[统计约定](benchmark-analysis-plan.md) | `evaluation` |
| 经验内容与使用 | [使用接口](experience-usage-interface.md)、[写作标准](experience-authoring-standard.md)、[维护实现](experience-curation-implementation.md) | `creative_knowledge`、`training_experience` |
| 已验证状态与剩余问题 | [当前状态](current-status.md)、[问题及修复记录](code-review-remediation-checklist-20261102.md) | 离线报告与运行回执 |

## 开发检查

在已安装 `requirements.server-runtime.txt` 的 Python 环境运行：

```bash
python scripts/check_repository.py --suite current
python scripts/check_repository.py --module test_api_backend --module test_review_modes
```

检查默认离线，使用合成视频和脚本化模型；本地 HTTP fixture 可用，外部连接会被测试入口拦截。每个模块独立进程，只收集本模块定义的测试，避免导入测试类重复计数。默认每个测试模块最多运行 180 秒，可用 `--timeout` 调整；这是测试工具的超时，与实验 2.5 小时期限分开。`--jobs` 控制测试并发。

日志和汇总默认写入 `out/repository-check/`。当前模块清单在 [检查入口](../scripts/check_repository.py) 的 `CURRENT`。`--suite historical` 保留先前协议的测试入口；其中旧 RSI、旧数值在线评审和旧 Planner 生命周期的部分断言已经失效，修改对应兼容代码时按模块核对。`--suite all` 用于调查全部历史兼容情况，不作为当前协议通过声明。

格式工具见 `requirements.dev.txt` 和 `pyproject.toml`。修改运行行为时同步当前说明和相关回归；实验、模型或结果身份改变时更新相应配置。一般文档编辑不引起在线协议迁移。

## 冻结交接与阶段记录

[生成工具包说明](benchmark-guide/generation.md) 和 [评分交接包](../handoffs/scoring-20261102/README.md) 对应冻结的外部工具，使用包内入口时依包内说明。根目录是持续迭代的开发实现。

旧 `agent-loop*`、`rsi-*`、`two-level-rsi-*`、`*-plan.md` 和七题运行／交接记录保留在原位置，解释历史决定及结果。其旧 CLI、评分和调度要求不定义当前运行方式。原始问题清单保留阶段证据，当前结论以顶部和 `current-status.md` 为准。数据与经验专项审阅记录继续由对应维护任务管理。
