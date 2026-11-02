# LHA：经验引导的视频编辑实验

LHA 研究 Planner 如何结合视频观察、生成反馈和编辑经验，完成从源视频到目标风格或场景的编辑。本仓库比较原始提示词直出（Direct）、提示词增强（PE）、一次规划（Planner-once）以及有／无经验的迭代编辑。

## 从这里开始

| 你要做什么 | 阅读入口 |
|---|---|
| 了解数据、实验分工和完整顺序 | [实验总览](docs/benchmark-guide/experiment.md) |
| 用 Bernini / Ditto 生成 PE，准备 Direct / Planner 对照 | [生成操作说明](docs/benchmark-guide/generation.md) |
| 导入生成视频、评分、补交 Planner、查看结果 | [评分操作说明](handoffs/scoring-20261102/README.md) |
| 填写自己的 API 和预算配置 | [配置说明](docs/benchmark-guide/configuration.md) |
| 查看此前的架构、知识及历史介绍 | [此前 README 原文](docs/benchmark-guide/previous-readme.md)（保留历史状态，不作为当前启动说明） |

## 数据与实验条件

唯一当前 benchmark 为 75 个源视频，编号连续，不区分 fewshot 类别。每个样本包含 `video.mp4`、`prompt_short.txt`、`prompt_long.txt`，总清单为 `benchmark_data/benchmark.json`。

| 划分 | 编号 | 源视频数 | 每个方法的长短条件数 |
|---|---|---:|---:|
| train | 001–040 | 40 | 80 |
| validation | 041–050 | 10 | 20 |
| test | 051–075 | 25 | 50 |
| 合计 | 001–075 | 75 | 150 |

出现在 evidence card 中的相关条目按已确定规则归入训练集。训练用于经验开发，验证用于流程和设置校准，测试结果单独报告。短、长提示词是两种独立任务条件；各方法在同一条件下从同一条原始提示词出发。

## 推荐运行顺序

1. 获取配套 `benchmark.zip`，核对 75 条统一编号数据。
2. 使用已交接的 `bernini-tools.zip` / `ditto-tools.zip`，先环境检查，再单条试运行，最后完成各 150 个 PE 输出。Bernini 保留官方增强模板；Ditto 使用项目适配模板。
3. 收集 Bernini Direct，以及需要比较的 Planner / RSI 实际生成视频。保留生成收据、提示词与运行信息。
4. 下载 [评分工具包](handoffs/scoring-20261102/scoring-tools.zip) 与 [校验文件](handoffs/scoring-20261102/scoring-tools.zip.sha256)，按[评分说明](handoffs/scoring-20261102/README.md)独立解压运行。Bernini、Ditto 分库存储。
5. 使用自己的模型服务和预算配置执行评分，查看 `index.html` 与 `results.json`。迟到结果可追加后续跑。

## 版本与交付边界

本分支是 **2026-11-02 实验交接入口**。评分命令针对 `handoffs/scoring-20261102/scoring-tools.zip` 内的冻结代码；根目录开发代码与冻结包可能不同，不能混用。数据包、PE 生成工具包、模型权重均单独交接，不包含在评分 ZIP 中。只克隆仓库尚不具备全部数据和模型。

配置由使用者提供；仓库不包含我们的密钥、服务配置或实际预算。离线准备与导入无需付费评分调用；PE 正式生成涉及增强 API 与 GPU，正式评分涉及双裁判 API 和自动指标计算。

评分复用 `lha-low-high-final-v3`：五维 0–4 分、长短专项、自动指标和双向盲评。依据始终是原始提示词与可见视频；缺失不算零分，不新增加权总分。详细评分标准位于评分 ZIP 的 `docs/low-high-evaluation-v2.md`。

交接已完成 3 项导入、8 项结果登记、11 项评分专项离线测试；更广生成流程另有 2 项测试未通过，详见评分说明。未执行真实在线终评。本说明不代表完整 GPU / API 环境已部署或正式实验已完成。

## 开发目录导航

- `src/planner_harness/`：Planner 执行、观察、资源计量与恢复。
- `src/critic_harness/`：视频评审及评分锚点。
- `src/evaluation/`：独立终评、自动指标、盲评和汇总。
- `src/experiments/`、`scripts/`：批次生成、结果登记和命令入口。
- `knowledge/`：Planner 可用知识及编辑经验。
- `benchmark_data/`：当前数据清单与样本（视频需要单独数据包）。
- `handoffs/`：固定版本交接材料；`docs/`：实现与操作说明。

开发路径以对应版本代码和文档为准。历史计划、运行记录和此前 README 用于溯源，不作为新实验的默认启动命令。
