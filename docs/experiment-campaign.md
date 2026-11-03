# 全量主实验与 RSI 运行安排

主实验四组均覆盖当前 **67 条任务**，每条保留 short、long 两版，共 **134 个条件**。40／27 是 RSI 的经验积累与测试划分，四组主实验都跑全量。独立 Critic 为主实验评审方式，Planner 自评切换作为追加消融。

## 先跑什么、跑多少次

| 顺序／入口 | 覆盖范围与行为 | 每个条件最多生成 | 完整任务轨迹数 | 视频生成上限 |
|---|---|---:|---:|---:|
| 1 `zero` | 无经验 Planner 跑完 67 条；先跑前 40 条并逐题维护经验，再跑后 27 条，后段关闭维护 | 4 | 134 | 536＝320＋216 |
| 2 `knowledge` | 用刚积累的固定经验，跑全量 67 条有经验 Planner | 4 | 134 | 536 |
| 3 `direct` | 全量 Direct；兼容的历史结果直接复用 | 1 | 134 | 134 |
| 4 `pe-loop` | 全量 PE＋Critic Loop，含首轮共最多 4 次 | 4 | 134 | 536 |
| 5 `score` | 同批视频统一终评，输出全量主表与 RSI 子集表 | 0 | 复用视频 | 0 |
| 追加 `self-review` | 全量有／无经验 Planner 切为 Planner 自评；独立积累并冻结自身经验 | 每组 4 | 268 | ＋1072 |

**主实验最多 1742 次视频生成、536 条完整任务轨迹。** 每个提示词条件对应 `1＋4＋4＋4＝13` 次生成。无经验前 40 条的 320 次已经包含其中，经验维护追加的是模型调用，不追加视频。只跑一种提示词时，上述主实验是 871 次；配置默认长短两版均跑。

一键顺序是 `zero → knowledge → direct → pe-loop → score`。Direct 和 PE 是独立基线，也能单独启动；有经验组依赖无经验全量流程结束后的经验快照。Planner loops use the complete configured generation allowance before final selection, including when an early candidate is adequate. The Planner chooses every prompt and input and may finally select an earlier candidate. Actual submissions include failed render attempts; deadline, execution-unknown and interrupted outcomes remain separately reported. Historical Direct reuse reduces new submissions. First-round comparisons reuse each loop's first saved video.

## 40／27 怎样用于 RSI

当前清单保留原编号：前 40 条为 001–040 中仍保留的 35 条，加 041–045；后 27 条为 046–075 中仍保留的条目。具体 ID 在命令 `plan` 输出及冻结的 `plan.json` 中；同一 source_group 和同一源视频哈希不会跨 RSI 两侧。原始视频、提示词与文件路径保持原样，`split` 标签表示 RSI 角色，不限制主实验覆盖。

`zero` 的前 40 条在线不读经验，但从预置知识库开始维护。任务结算后，恢复该题 Planner 的实际工作记录，开放三个维护 Skill、预置条目和累计私有经验，允许新建经验、追加评论和提出修订建议；正式整理另行决定采纳与改写。下一题在线继续无经验；只在任务后的维护中读取累计经验。后 27 条继续运行同一个无经验方法，关闭维护，也不读取积累的经验。

这一批 67 条全部结算后，把前 40 条累积的经验固定为 `trained-experience.json`。`knowledge` 用这份经验跑完整 67 条，整个过程只读。经验更新留在本次运行的私有快照，仓库共享知识库保持原样；维护失败或无增量保留此前版本，未确认的外部执行按原请求恢复。

**主表汇总 67 条四组结果；RSI 对照直接取后 27 条的无经验／有经验结果。** 前者衡量整个流程，后者衡量经验向未参与维护任务的迁移。两张表共用视频、独立评分和缓存；没有额外的训练批次或 RSI 测试重跑，也不设验证集。本次有经验组包含现有基础经验和前 40 条的维护增量。所有批次开跑前固定非空的 `initial-experience.json`；`none` 只控制在线经验可见范围，不表示库为空。基础设计知识仍可用，Direct／PE 不使用 Planner 经验工具；后 27 题与固定经验组按实验配置只读。

## Planner self-review: independent accumulation and frozen use

P1 uses the same complete Planner to review its result within the task context.
For each renderer, both review families start from the same nonempty seed, then
maintain separate private libraries. Online `none` disables experience access
while editing; it retains the full seeded corpus for post-task maintenance.

| Stage | Online experience | Post-task maintenance | Maximum renders |
|---|---|---|---:|
| `self-review-zero` | None during editing | First 40 training tasks only, both prompt forms | 536 |
| `self-review-knowledge` | Its own frozen self-review library | Disabled for all 67 tasks | 536 |

`--stage self-review` runs these two stages in order. It does not depend on or
import the Critic family's `zero`/`knowledge` run. Its immutable result is
`self-review-trained-experience.json` with a receipt recording the source family,
renderer, seed, training coverage and revision. The existing `trained-experience.json`
continues to belong to the Critic family. Direct/PE results remain reusable;
PE keeps its independent Critic. Both renderers together add at most 2,144 renders.

Private libraries carry an immutable owner identity. Enqueue, maintenance read,
contribution ingestion, recovery and family freeze verify this identity. A frozen
read-only copy must match an actual revision of that owner. Empty full libraries
are rejected at batch preparation and maintenance entry points. Existing unbound
legacy runs remain historical records; use a new output directory for this policy.

Maintenance appends new entries, comments, clarifications and revision proposals
with their source cases. An explicit curator can revise canonical guidance. Online
`none` tasks never receive the library or post-task contributions in their editing
context. Full tasks read the frozen map, entries, contributions and linked cases.

```bash
python scripts/run_experiment_campaign.py run --backend bernini --stage self-review \
  --host-config configs/bernini-campaign-host.local.json --output out/main-all67-n4/bernini --execute
```

This command is documented for later authorized execution; the family repair was
validated offline and did not launch it.

## 双模型一键命令与配置

在自己的 LHA 仓库根目录执行。通用实验参数见 [experiment-campaign.json](../configs/experiment-campaign.json)：Planner／PE 含首轮最多 4 次，seed42 起步，每条在线任务的时间与 token 预估按下述公式计算；Planner 与 Critic 使用 6.1-sol high。模型资产、设备和凭据放在各自主机配置里。

时间上限 = `单次生成秒数 ×（本阶段生成次数上限＋0.5）`；token 预估 = `每次 token 基数 ×（本阶段生成次数上限＋0.5）`。配置集中在 `task_budget`，Planner 与 PE 的次数可分别设置。当前 token 基数为 100 万，沿此前 4 次／400 万配置折算，用于规划；没有 token 硬上限。它包含在线 Planner／PE、Critic 和选片的输入与输出用量；维护和独立终评分开记录。Planner 继续获得模糊资源提醒。

| 阶段 | 次数上限 | Bernini（20 分钟/次） | Ditto（40 分钟/次） | token 预估 |
|---|---:|---:|---:|---:|
| Planner／PE Loop | 4 | 90 分钟 | 180 分钟 | 450 万 |
| Direct | 1 | 30 分钟 | 60 分钟 | 无在线模型调用；通用公式预留 150 万 |

`plan` 展示各阶段、各渲染器的计算值，批次记录 `budget_estimate`。实际时间从设备和服务就绪、任务开始执行时计算；恢复沿用原截止时间。

首次复制三个示例，然后填写两份主机配置的实际设备、已验证资产清单及哈希。`*.local.json` 已加入 Git 排除。两模型若部署在同一主机，可直接使用 `both`；分处两台主机时，各自在本机用对应单模型命令。

```bash
cp -n configs/bernini-campaign-host.example.json configs/bernini-campaign-host.local.json
cp -n configs/ditto-campaign-host.example.json configs/ditto-campaign-host.local.json
cp -n configs/experiment-hosts.example.json configs/experiment-hosts.local.json
python scripts/run_experiment_campaign.py plan --backend both
```

完整双模型主实验：

```bash
python scripts/run_experiment_campaign.py run --backend both --stage main \
  --host-config configs/experiment-hosts.local.json --output out/main-all67-n4 --execute
```

入口顺序执行 Bernini、Ditto，各自完成 `zero → knowledge → direct → pe-loop → score`。运行开始固定同一份预置知识；两模型的维护增量、视频与评分缓存分别进入 `out/main-all67-n4/bernini` 和 `out/main-all67-n4/ditto`。每模型主实验上限 1742 个视频，双模型上限 3484；已完成结果和同视频评分继续复用。

PE 随渲染器自动适配：Ditto 使用[专用编辑指令模板](pe-loop.md#ditto-的编辑指令适配)，将短风格要求具体展开、保全长任务条款，并吸收逐轮 Critic 反馈；Bernini 使用自己的模板。沿用本页命令即可，单独执行 Ditto PE 时使用 `--backend ditto --stage pe-loop` 和 Ditto 主机配置。`pe-loop` 的渲染设置中 `prompt_enhancer=false` 表示渲染器直接接收已增强的文本，增强由 Loop 负责。

分批运行时，保留同一输出目录，把 `--stage main` 换成下表的阶段：

| 批次 | 阶段参数 | 前置条件／产出 |
|---|---|---|
| 无知识支持 Planner＋维护 | `zero` | 从预置库开始；前 40 题交付后维护，后 27 题关闭维护；产出本模型固定经验 |
| 有知识支持 Planner | `knowledge` | 依赖本模型 zero 结算；读取本模型固定经验 |
| Direct | `direct` | 独立基线；复用条件一致的历史视频 |
| PE Loop | `pe-loop` | 原视频逐轮生成，独立 Critic 反馈，在线选片 |
| 终评／汇总 | `score` | 复用已有视频与有效评分，输出主表和 RSI 子集 |

单模型运行示例（另一模型将 `bernini` 换成 `ditto`）：

```bash
python scripts/run_experiment_campaign.py run --backend bernini --stage main \
  --host-config configs/bernini-campaign-host.local.json --output out/main-all67-n4/bernini --execute
python scripts/run_experiment_campaign.py status --backend both --output out/main-all67-n4
```

Each model writes `results/index.html` and `results/results.json`, with `results/rsi.html` and `results/rsi.json` for the held-out experience analysis. Campaign execution requires `run --execute`; `plan` and `status` submit no work.

`status` reads existing dispatch records, worker checkpoints and durable method settlements while a batch is running, then the final checkpoint. It reports planned/recorded/ready counts, outcome and claim counts, and unresolved outcomes. `running` means the latest recorded dispatch state, not a fresh process-liveness check. With a combined output directory, model subdirectories are detected automatically; explicit `--backend both` also works. The lower-level `run_creative_benchmark.py status --output <batch>` uses the same projection. These commands do not resume or repair jobs.

## 复用与实现

[一键入口](../scripts/run_experiment_campaign.py)通过 [campaign.py](../src/experiments/campaign.py)复用原 [统一运行器](../src/experiments/unified_benchmark.py)、设备队列、生成回执和结果注册。各批冻结自己的生成次数与 `training_maintenance`：主实验中只有 `zero` 为 true，其他主实验批次为 false。底层手动运行全量有经验组时，使用 `--split train test --method full --no-maintenance`；PE 单独使用 `--max-generations 4 --no-maintenance`。

`zero` 的设备队列将前 40 条的长短条件组成顺序维护链，最后一个维护任务结算后才放行后 27 条。全量有经验组中的前 40 条保持只读，不会因原有 `train` 标签重新维护。具体维护由 [training_experience.py](../src/planner_harness/training_experience.py)与 [maintenance.py](../src/planner_harness/maintenance.py)处理。

独立评分复用 [results.py](../src/experiments/results.py) 中的五维、长短专项、CLIP/DINO、光流和匿名交换顺序盲评；原始提示词与源视频是共同评价依据。主实验统计覆盖全部源组，RSI 单独覆盖后段源组。Direct 从 `reuse_direct_results` 指定的历史注册目录核验后导入，旧分数不导入；同一视频的首轮／末轮／选中角色共用新评分。真实调用数、维护费用和 GPU 请求单独记录。

相同目录接续会复用已完成阶段。切换这版 67 条全流程、生成次数或协议时使用新的输出目录；原实验结果继续保留。没有 `--execute` 不启动实际调用。

## 一键全量评分

已有视频注册到结果目录后，直接执行：

```bash
python scripts/benchmark_results.py score-evaluation \
  --root out/main-all67-n4/bernini/results --execute
```

Ditto 将路径中的 `bernini` 换为 `ditto`。命令自动创建当前协议评价会话、追加新视频、评分、盲评和汇总；再次执行复用已完成调用。协议改变时自动使用新评分目录，旧原始评分保留。想主动另起同协议评价，仍可使用 `prepare-evaluation --evaluation-id ...`。

已启动过的双模型 campaign 也可一次评分两个结果目录：

```bash
python scripts/run_experiment_campaign.py run --backend both --stage score \
  --output out/main-all67-n4 --execute
```

单模型使用相应 `--backend` 和它的输出目录。评分阶段直接读取已有视频，即使知识组尚未生成也可开始。

| 默认执行部分 | 内容 |
|---|---|
| 独立五维 | 指令遵循、内容保留、时序一致性、视觉完整性、美学协调；0–4 分、0.1 步长 |
| 短任务专项 | 风格实现、场景针对性设计、有效创造性、相对原创性 |
| 长任务与要求核对 | 逐条完成、对象／属性绑定、联合满足、必要对应、非预期及重大损伤 |
| 美学 | 五项美学诊断及计算均值 |
| 客观指标 | CLIP-F、DINO-F、光流补偿误差 |
| 连续性与运动 | 全原生连续帧分段观察、运动强度、低运动时长比例、条件性源运动对应 |
| 独立盲评 | 两位判官分别评任务完成与制作质量；匿名 A/B 随机顺序后交换再评 |
| 汇总 | 当前结果页、长短条件及判官分组、首轮／末轮／选中结果、配对差值与既定统计；campaign 另出 RSI 子集 |

执行当前注册指标的全部管线；相对原创性需要对应参考条件，精确源运动保留需要适用任务、区域和配准条件，缺少时记录相应状态。可选人工轨迹误差需要另行提供注册轨迹。结果页的“全量评分执行情况”和 `results.json` 的 `evaluation_coverage` 按指标列出已评分、未知、不适用、未测及失败，显示连续片段评审数和盲评结果。

环境安装 `requirements.evaluation.txt`，准备 `configs/evaluation.json` 指定判官的凭据；CLIP/DINO 首次运行需要相应权重。默认无需费用或 token 额度配置。`--budget-config` 若显式提供，仅用于客观指标计算任务。此命令会调用独立判官并计算指标。
