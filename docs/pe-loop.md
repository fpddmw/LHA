# PE＋Critic Loop

PE Loop 是固定流程的提示词增强基线：原始任务与源视频概览 → 增强提示词 → 从原视频生成 → Critic 评审 → 修改提示词。当前主实验最多 4 轮，首轮计入 4 次生成；底层 N 仍可配置。增强、定性择优和在线 Critic 均使用 GPT-6.1-sol、high。

## 与 Planner Loop 的区别

PE 每轮获得原始任务、8 帧固定源视频概览、历轮提示词和定性反馈，并复用上一轮 Critic 实际检查的画面。增强模型输出完整英文生成提示词；运行器负责生成、评审和选择。它不检索知识、不自行调用观察工具，每轮生成输入固定为原视频。

Planner 自主安排观察、查阅、提示词与输入候选，决定继续、停止或回选。有知识支持／无知识支持组共用这些操作能力，经验开放范围按各自冻结快照区分。

在线 Critic 使用当前定性诊断协议，可主动检查连续帧；原始要求、short/long 类型与实际生成提示词一并传入。独立终评另行计算五维、长短专项、美学、CLIP/DINO、光流和盲评；终评分数不进入 PE 的下一轮。

## 模式与复用

| 选择 | 行为 |
|---|---|
| 当前全量主实验 | `direct pe-loop none full`，PE=4、Planner=4，每个条件最多 `1 + 4 + 4 + 4` 个视频 |
| `--method pe-loop` | 仅执行新的 PE＋Critic 循环 |
| `--method pe` | 保留旧版官方单次增强适配器与原始运行身份 |
| `--method planner-once` / `direct-best-of-n` | 显式运行补充对照 |
| `--review-mode critic` / `planner` | 切换完整 Planner Loop 的独立 Critic／Planner 自评；PE Loop 始终使用独立 Critic，作为共享基线 |

`pe-loop` 与旧 `pe` 使用不同结果键；其首轮是本协议下的单次增强结果。旧 PE 视频保留原模型、模板与配置，不自动登记为新 PE Loop 首轮。切换生成预算、模型、模板、评审或选择协议时准备新批次，使用独立结果目录避免同键覆盖。

```bash
# 仅冻结计划，不启动 API 或 GPU
python scripts/run_creative_benchmark.py prepare \
  --output /path/pe-loop-test --results-root /path/pe-loop-results \
  --split train test --method pe-loop --no-maintenance --prompt-form short long --max-generations 4

# 专门准备 PE Loop
python scripts/run_creative_benchmark.py prepare \
  --output /path/pe-only --results-root /path/pe-only-results \
  --split train test --method pe-loop --no-maintenance --max-generations 4
```

实际运行沿[统一实验入口](creative-benchmark-execution.md)提供主机与预算配置。预算分配需要包含 `pe-loop`，生成额度支持 N；若使用模型调用数硬上限，至少容纳 N 次增强、N 次评审和 N−1 次选择，Critic 补看还会增加调用。训练与维护费用单独计算。当前经验维护嵌在全量无经验 Planner 的前 40 条中；PE 全程只读，详见 [全量实验安排](experiment-campaign.md)。

## 保存、恢复与评分

每轮保存增强调用、提示词、生成回执、Critic 完整反馈和选择结果。反馈或选择失败时保留待恢复阶段，恢复复用已经完成的调用与视频。达到时间预算后交付最近一次完成的选择；若尚无选择，则保留第一条完成视频，并明确记录评审覆盖与预算停止原因。

原批次已记录失败时，先核实外部请求已经结束，并按已有模型调用恢复工具处理原调用，再执行：

```bash
python scripts/run_creative_benchmark.py recover-pe-loop \
  --output /path/pe-loop-test --topic SAMPLE__short --reason "原请求已核实，接续保存阶段"
```

该命令只重新开放原任务的结算和队列位置，保存恢复原因；它不调用模型、不重置预算或删除阶段记录。之后用原 `run` 命令接续。仍在执行或结果未知的外部请求会阻止恢复，历史失败结算单独存档。

结果登记三种身份：`first` 首轮、`last` 末轮、`final` 最终选中；`selected` 候选标记对应 final。N=1 时三者可指向同一个视频。内容哈希共用媒体及终评缓存，首轮对照无需再生成。

默认主比较为 PE Loop 最终结果与无知识 Planner Loop 最终结果；有／无知识、首轮／最终及 Direct 参照作为相应增量分析。原有对照仍可显式运行。统计按原始长短任务及来源组汇总。

## 实现入口

- [pe_loop.py](../src/experiments/pe_loop.py)：增强上下文、固定流程及逐阶段恢复。
- [unified_benchmark.py](../src/experiments/unified_benchmark.py)：复用 `Runtime.render/review/choose`、模型工厂与预算账本。
- [results.py](../src/experiments/results.py)：方法切换、视频去重、首轮／末轮／选中登记及评分汇总。
- [test_pe_loop.py](../scripts/test_pe_loop.py)：不调用真实模型或 GPU 的流程与恢复测试。
