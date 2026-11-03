# LHA：多模态视频编辑 Agent Loop

LHA 研究 Planner 如何结合视频观察、生成反馈和编辑经验完成 Low→High 视频编辑。当前开发主线统一使用 API：默认每次生成后由独立 Critic 做定性检查，也可配置 Planner 自评；正式评分在任务结束后独立执行。

## 开发与运行入口

| 要做什么 | 入口 |
|---|---|
| Reproduce the experiments from a fresh checkout; run a CPU-only smoke test | [Public experiment guide](docs/public-experiment-guide.md) |
| 理解完整 loop、模块职责和设计边界 | [Loop 设计与实现](docs/creative-loop-implementation.md) |
| 配置模型、凭据、资源和评审方式 | [配置说明](docs/benchmark-guide/configuration.md) |
| 准备并运行主实验、经验训练及消融 | [实验运行安排](docs/experiment-campaign.md) |
| 部署服务、并发调度、停止与恢复 | [服务运行说明](docs/server-runtime.md) |
| 阅读评分标准、自动指标及盲评 | [独立终评](docs/low-high-evaluation-v2.md) |
| 对已有视频一键完成全量评分 | [评分命令与指标范围](docs/experiment-campaign.md#一键全量评分) |
| 查看当前验证结果与真实服务限制 | [当前状态](docs/current-status.md) |
| 查找全部文档及历史方案 | [文档索引](docs/README.md) |

先在 Python 3.11+ 环境安装控制器依赖；GPU 渲染继续使用已经配好的 Bernini 环境：

```bash
python -m pip install -r requirements.server-runtime.txt
python scripts/run_experiment_campaign.py plan
python scripts/smoke_experiment_campaign.py --output out/public-smoke
python scripts/check_repository.py --suite current
```

`plan` 依据当前数据清单计算任务数，不提交生成或模型请求。检查脚本运行离线测试。Live execution requires the explicit experiment launch command. This integration repair starts no experiment; deployment and provider availability require a separate live preflight when experiments are resumed.

## 当前数据和实验

唯一当前清单是 [benchmark_data/benchmark.json](benchmark_data/benchmark.json)：67 条源视频，训练 40、测试 27，不设验证集；保留原编号和 short/long 两种独立任务条件，共 134 个条件。数据视频与模型权重需另行准备；任务定义、分布和示例见 [数据说明](benchmark_data/README.md)，清单读取见 [代码](scripts/inspect_benchmark.py)。

The main experiment runs Direct, PE Loop, no-experience Planner and full-experience Planner over the full population. The no-experience arm maintains its private library after training tasks, then runs the held-out tasks without maintenance. The full arm reads the resulting frozen library. Held-out experience analysis reuses the same videos and independent scores. Planner loops use the complete configured generation allowance (default N=4), then select any candidate, including an earlier one. PE also uses N=4. Task deadlines are the renderer estimate multiplied by N+0.5: currently 90 minutes for Bernini and 180 minutes for Ditto. Planner receives approximate resource hints. Self-review is a separate ablation with its own privately accumulated library.

## 代码边界

- `src/planner_harness/`：任务状态、Planner 动作、工作记忆、交付、资源计量和恢复；`compat/` 保存旧流程实现。
- `src/critic_harness/`：在线定性评审及共享视频证据能力。
- `src/vlm/`：角色配置和模型 API 传输。
- `src/server_runtime/`：持久任务队列、资源调度和渲染器。
- `src/experiments/`：实验编排、方法执行、经验版本、结果注册及多设备调度。
- `src/evaluation/`：独立评分、证据校验、自动指标、盲评和统计；历史服务适配集中在 `legacy_providers.py`。
- `configs/`：在线任务、主机、实验批次及独立判官配置；`knowledge/` 和 `.agents/skills/`：运行中可读取的材料。
- `scripts/`：命令入口和离线测试；当前运行说明见上表，历史脚本仅用于对应旧协议。

## 固定版本交接

[评分交接包](handoffs/scoring-20261102/README.md)、Bernini／Ditto 生成工具包及历史结果继续保留。冻结 ZIP 使用包内代码和说明；根目录是持续迭代的开发实现。数据版本以 reviewed67 清单为准，已有视频按实际生成条件复用。

本仓库的离线测试验证工程行为。模型效果、真实 API 可用性和双卡长时运行分别记录，不以软件测试替代实验结果。
