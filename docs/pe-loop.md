# PE＋Critic Loop

PE Loop 是固定流程的提示词增强基线：原始任务与源视频概览 → 增强提示词 → 从原视频生成 → Critic 评审 → 修改提示词。当前主实验最多 4 轮，首轮计入 4 次生成；底层 N 仍可配置。增强、定性择优和在线 Critic 均使用 GPT-6.1-sol、high。

## 与 Planner Loop 的区别

PE 每轮获得原始任务、8 帧固定源视频概览、历轮提示词和定性反馈，并复用上一轮 Critic 实际检查的画面。增强模型输出完整英文生成提示词；运行器负责生成、评审和选择。它不检索知识、不自行调用观察工具，每轮生成输入固定为原视频。

Planner 自主安排观察、查阅、提示词与输入候选，决定继续、停止或回选。有知识支持／无知识支持组共用这些操作能力，经验开放范围按各自冻结快照区分。

在线 Critic 使用当前定性诊断协议，可主动检查连续帧；原始要求、short/long 类型与实际生成提示词一并传入。独立终评另行计算五维、长短专项、美学、CLIP/DINO、光流和盲评；终评分数不进入 PE 的下一轮。

### Ditto 的编辑指令适配

现有命令按 `--backend ditto`（或主机配置中的 `renderer.backend`）自动选择 Ditto 模板；双模型一键命令的 Ditto 阶段使用同一分支。模板位于 `src/experiments/pe_loop.py` 的 `DITTO_SYSTEM_PROMPT`，承接已交接 `ditto-grounded-instruction-v2` 的写法：

- 用 Transform、Restyle、Replace 等直接编辑指令起句，并把变化绑定到源视频里的对象和区域。
- 短全局任务展开为 2–4 个协调的材质、形态、服装或场景变化；长任务逐项保全明确要求，局部任务保持对应范围。
- 根据任务目标延续或改编原有活动与道具功能，逐轮把 Critic 的具体发现落实为编辑条款。
- 短全局任务通常写 40–90 个英文词，详细任务按要求展开；词数是写作建议，编码容量由 Ditto tokenizer 检查。

移植沿用当前 Loop 的 8 帧、JSON 输出、历史反馈、原片输入、4 次生成和 2.5 小时上限。Bernini 分支保留原模板。`batch.json` 的 `pe_loop.prompt_sha256` 绑定实际模板，模型调用的 `input.json` 保存实际输入。本次修订前的 Ditto Loop 分支只替换了渲染器名称和编码说明；本次补齐编辑指令写法，后续新批次自动生效。原交接包的三帧单次增强与当前 Loop 各按自身记录解释。

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

### 提示词长度恢复

Bernini 用官方 tokenizer 计算清洗后的提示词和官方前缀，共 512 token；Ditto 计算提示词本身的 512 token。超长请求在 GPU 生成前返回失败，并保存 `prompt-length.json` 中的实际计数。

PE 对明确的生成前长度拒绝最多做两次压缩。压缩模型保留任务的关键变化和视觉关系，按原文长度缩减；每次新提示词再经过实际 tokenizer 检查。正常提示词沿原流程直接生成。压缩调用计入原 PE 账本和截止时间，未派发 GPU 的拒绝不消耗生成次数。

原始增强答卷和 `rounds/NNNN/prompt.json` 保留。压缩调用与输出进入原生成目录的 `prompt-revisions/1`、`2`；新的生成请求分别使用 `N-prompt-1`、`N-prompt-2` 目录。Critic、后续历史和结果记录使用实际渲染的提示词。两次压缩仍超长时，有既有候选的任务按最近一次完成的选择结算，并记录 `prompt_limit_delivery`。

已有旧版本任务可用独立的新代码目录恢复原运行。先检查，再执行同一条命令加 `--execute`：

```bash
python scripts/recover_pe_prompt.py --output /path/original-run \
  --topic SAMPLE__long --device 0 --reason "已核实生成前 tokenizer 超限"
```

`--device` 使用原 worker 的设备编号。执行入口为本次恢复建立独立服务队列，记录当前代码指纹、原失败回执和压缩策略；原代码快照、模型配置、生成参数、视频与调用记录继续保留。已 closed 的调度记录在原期限内重新开放，时钟和已用次数保持原值；期限已到时直接结算已有选择。原失败结算保存在 `settlement-history`，恢复记录位于 `prompt-length-recovery`，结果中保留恢复来源。

如果压缩答卷已保存，但修订渲染在派发前因环境问题失败，可在排除环境问题后指定 `--retry-render 1-prompt-1`（替换成实际失败目录名），再加 `--execute`。入口复用已保存的提示词、种子和生成参数，创建独立的 `1-prompt-1-retry-1` 请求；成功后保存该轮候选，接续原 PE 的评审和后续阶段。原失败回执保持完整。重复执行会复用已保存结果，超过原期限则转入已有候选结算。GPU 独占锁由 resident renderer 持有，外层调度器等待设备可用后启动进程。

### 模型调用中断后的缓存结算

候选和 Critic 评审已完成、选片调用结果未知时，PE 按最近一次已完成的选择结算，登记所有已生成版本，并记录 `selection_unavailable_delivery`。原选片调用继续保留其未知状态和用量记录。

已完成至少一次选择、随后在提示词改写、Critic 评审或选片阶段遇到结果未知的任务，可用以下入口检查；加 `--execute` 后读取保存的阶段结果，按最近一次已完成的选择登记全部视频。模型和 GPU 调用均为零。评审未完成的新视频仍登记为 `last`，已完成评审数单独保留。改写或评审中断的显式结算记录为 `interrupted_delivery`；正常运行的这两个阶段仍可等待原调用结果再恢复。

`--device` 对应原 worker 编号。若原期限已经结束，结算类型为 `deadline_delivery`，原中断阶段、原因和未知调用保存在恢复记录中。

```bash
python scripts/recover_pe_prompt.py --output /path/original-run \
  --topic SAMPLE__long --device 0 --settle-last-choice
```

结果登记三种身份：`first` 首轮、`last` 末轮、`final` 最终选中；`selected` 候选标记对应 final。N=1 时三者可指向同一个视频。内容哈希共用媒体及终评缓存，首轮对照无需再生成。

默认主比较为 PE Loop 最终结果与无知识 Planner Loop 最终结果；有／无知识、首轮／最终及 Direct 参照作为相应增量分析。原有对照仍可显式运行。统计按原始长短任务及来源组汇总。

## 实现入口

- [pe_loop.py](../src/experiments/pe_loop.py)：增强上下文、固定流程及逐阶段恢复。
- [unified_benchmark.py](../src/experiments/unified_benchmark.py)：复用 `Runtime.render/review/choose`、模型工厂与预算账本。
- [results.py](../src/experiments/results.py)：方法切换、视频去重、首轮／末轮／选中登记及评分汇总。
- [test_pe_loop.py](../scripts/test_pe_loop.py)：不调用真实模型或 GPU 的流程与恢复测试。
