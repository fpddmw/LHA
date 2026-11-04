# 全量主实验与 RSI 运行安排

For a fresh checkout, deployment interfaces, complete launch commands and the
CPU-only smoke test, start with the [public experiment guide](public-experiment-guide.md).

主实验四组均覆盖当前 **67 条任务**，每条保留 short、long 两版，共 **134 个条件**。40／27 是 RSI 的经验积累与测试划分，四组主实验都跑全量。独立 Critic 为主实验评审方式，Planner 自评切换作为追加消融。

## 先跑什么、跑多少次

| 顺序／入口 | 覆盖范围与行为 | 每个条件最多生成 | 完整任务轨迹数 | 视频生成上限 |
|---|---|---:|---:|---:|
| 1 `pre-experience` | 预经验 Planner 跑完 67 条，每题结算后维护；前 40 条的贡献用于本轮，后 27 条留到下一批 | 4 | 134 | 536＝320＋216 |
| 2 `full-experience` | 用刚积累的固定经验，跑全量 67 条全经验 Planner | 4 | 134 | 536 |
| 3 `direct` | 全量 Direct；兼容的历史结果直接复用 | 1 | 134 | 134 |
| 4 `pe-loop` | 全量 PE＋Critic Loop，含首轮共最多 4 次 | 4 | 134 | 536 |
| 5 `score` | 同批视频统一终评，输出全量主表与 RSI 子集表 | 0 | 复用视频 | 0 |
| 追加 `self-review` | 全量预经验／全经验 Planner 切为 Planner 自评；独立积累并冻结自身经验 | 每组 4 | 268 | ＋1072 |

**主实验最多 1742 次视频生成、536 条完整任务轨迹。** 每个提示词条件对应 `1＋4＋4＋4＝13` 次生成。预经验组每题结算后维护，维护只增加模型调用。只跑一种提示词时，上述主实验是 871 次；配置默认长短两版均跑。

一键顺序是 `pre-experience → full-experience → direct → pe-loop → score`。Direct 和 PE 是独立基线，也能单独启动；全经验组依赖预经验全量流程结束后的经验快照。Planner loops use the complete configured generation allowance before final selection, including when an early candidate is adequate. The Planner chooses every prompt and input and may finally select an earlier candidate. Actual submissions include failed render attempts; execution-unknown and interrupted outcomes remain separately reported. Historical Direct reuse reduces new submissions. First-round comparisons reuse each loop's first saved video.

## 40／27 怎样用于 RSI

当前清单保留原编号：前 40 条为 001–040 中仍保留的 35 条，加 041–045；后 27 条为 046–075 中仍保留的条目。具体 ID 在命令 `plan` 输出及冻结的 `plan.json` 中；同一 source_group 和同一源视频哈希不会跨 RSI 两侧。原始视频、提示词与文件路径保持原样，`split` 标签表示 RSI 角色，不限制主实验覆盖。

所有任务开跑前冻结 `initial-experience.json`。`pre-experience` 阶段运行预经验组。每题在线 Planner 和任务后的维护模型均绑定同一份预经验，维护模型另外读取本题的工作记录和维护指南，可写评论、提修订或提交新条目。

前 40 条的贡献按来源登记到私有经验版本。评论和修订建议与原条目关联，新条目作为贡献层进入检索。后 27 条的贡献及来源记录保存在该阶段的 `training-experience/deferred/` 与维护任务目录，供下一批整理。它们不会进入本轮的全经验快照。

预经验阶段结算后，`trained-experience.json` 固定预经验与前 40 条的贡献。`full-experience` 阶段用这份快照跑完整 67 条，整组只读。主表汇总全量四组结果，RSI 表取后 27 条的预经验／全经验结果。历史 `none` 结果保留原实验身份。切换到这版 campaign 时使用新的实验目录。

## Planner self-review: independent accumulation and frozen use

P1 uses the same complete Planner to review its result within the task context.
For each renderer, both review families start from the same nonempty seed, then
maintain separate private libraries. The pre-experience stage reads the frozen seed during editing and maintenance.

| Stage | Online experience | Post-task maintenance | Maximum renders |
|---|---|---|---:|
| `self-review-pre-experience` | Frozen pre-experience seed | All 67 tasks, both forms. The first 40 contribute to this campaign | 536 |
| `self-review-full-experience` | Its own frozen self-review library | Disabled for all 67 tasks | 536 |

`--stage self-review` runs these two stages in order. It does not depend on or
import the Critic family's `pre-experience`/`full-experience` run. Its immutable result is
`self-review-trained-experience.json` with a receipt recording the source family,
renderer, seed, training coverage and revision. The existing `trained-experience.json`
continues to belong to the Critic family. Direct/PE results remain reusable;
PE keeps its independent Critic. Both renderers together add at most 2,144 renders.

Private libraries carry an immutable owner identity. Enqueue, maintenance read,
contribution ingestion, recovery and family freeze verify this identity. A frozen
read-only copy must match an actual revision of that owner. Empty full libraries
are rejected at batch preparation and maintenance entry points. Existing unbound
legacy runs retain their original group and saved tasks when resumed. Do not relabel
an actual no-experience result as pre-experience.

Maintenance appends new entries, comments, clarifications and revision proposals
with their source cases. An explicit curator can revise canonical guidance. Full tasks read the frozen map, entries, contributions and linked cases.

```bash
python scripts/run_experiment_campaign.py run --backend bernini --stage self-review \
  --host-config configs/bernini-campaign-host.local.json --output out/main-all67-n4/bernini --execute
```

This command is documented for later authorized execution; the family repair was
validated offline and did not launch it.

## 双模型一键命令与配置

在自己的 LHA 仓库根目录执行。通用实验参数见 [experiment-campaign.json](../configs/experiment-campaign.json)：Planner／PE 含首轮最多 4 次，seed42 起步，每条在线任务的时间与 token 预估按下述公式计算；Planner 与 Critic 使用 6.1-sol high。模型资产、设备和凭据放在各自主机配置里。

All new arms use 117 frames at 24 fps, sampled uniformly across each complete
source including both endpoints. Source hashes and selected indices are recorded.
The same prepared source is supplied to the Planner, renderer and final judges.
Original videos remain unchanged. Existing output directories resume their saved
manifests. Completed results remain usable with their actual frame counts and
preparation policy; the uniform117 default applies to new tasks.

There are no elapsed-time task, maintenance or evaluation limits. Planner and PE
use four submitted render attempts; Direct uses one. The `task_budget` time/token
values are estimates only. Generation-count phases supply qualitative reminders;
wall time cannot freeze a new task. Connection timeouts remain technical recovery
controls. The default disables historical Direct reuse.

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

入口顺序执行 Bernini、Ditto，各自完成 `pre-experience → full-experience → direct → pe-loop → score`。运行开始固定同一份预置知识；两模型的维护增量、视频与评分缓存分别进入 `out/main-all67-n4/bernini` 和 `out/main-all67-n4/ditto`。每模型主实验上限 1742 个视频，双模型上限 3484；已完成结果和同视频评分继续复用。

PE 随渲染器自动适配：Ditto 使用[专用编辑指令模板](pe-loop.md#ditto-的编辑指令适配)，将短风格要求具体展开、保全长任务条款，并吸收逐轮 Critic 反馈；Bernini 使用自己的模板。沿用本页命令即可，单独执行 Ditto PE 时使用 `--backend ditto --stage pe-loop` 和 Ditto 主机配置。`pe-loop` 的渲染设置中 `prompt_enhancer=false` 表示渲染器直接接收已增强的文本，增强由 Loop 负责。

分批运行时，保留同一输出目录，把 `--stage main` 换成下表的阶段：

| 批次 | 阶段参数 | 前置条件／产出 |
|---|---|---|
| 预经验 Planner＋维护 | `pre-experience` | 每题读固定预经验并维护。前 40 题贡献进入全经验，后 27 题延后 |
| 全经验 Planner | `full-experience` | 依赖本模型预经验组结算；读取本模型固定经验 |
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

[一键入口](../scripts/run_experiment_campaign.py)通过 [campaign.py](../src/experiments/campaign.py)复用原 [统一运行器](../src/experiments/unified_benchmark.py)、设备队列、生成回执和结果注册。各批冻结自己的生成次数与 `training_maintenance`：主实验中只有 `pre-experience` 为 true，其他主实验批次为 false。底层手动运行全量有经验组时，使用 `--split train test --method full --no-maintenance`；PE 单独使用 `--max-generations 4 --no-maintenance`。

`pre-experience` tasks run independently on N selected GPUs. Each task reads the same seed online and during maintenance; shared contribution commits serialize briefly. Full-experience waits for the stage's settlements and automatically reads its frozen training contributions. Test contributions remain deferred. Both public runners accept `--devices 0 1 ...` or `--devices auto`; see [multi-GPU execution and continuation](public-experiment-guide.md#n-gpus-on-one-host). The existing [training experience](../src/planner_harness/training_experience.py) and [maintenance](../src/planner_harness/maintenance.py) modules implement the handoff.

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


使用 `--stage all` 可一次运行四组主实验、两组 Planner 自评消融和独立终评。默认 `main` 运行四组主实验和终评。旧版飞书命令里的 `zero`、`knowledge` 仍可作为入口别名，新实验目录使用 `pre-experience`、`full-experience`。

评分后的 `results/index.html` 展开五维主表、长短专项、美学、客观指标与运动诊断、两两盲评。每位判官和长短条件分别报告，均值附有效数和计划数。主表含首轮、末轮和在线选中结果。RSI 子集使用同一套分数生成 `rsi.html`。
