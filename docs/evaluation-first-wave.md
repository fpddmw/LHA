# 首轮正式评价的执行方式

本轮使用 `lha-evaluation-v1`，评价器为 GPT-6.1-sol / xhigh。运行目录为
`out/evaluation_runs/20261030_first_wave`，初始材料来自不可变交接目录
`out/evaluation_handoff/20261029T163320Z`。

## 范围与比较关系

- 20 条提示词预实验视频、8 条已有 Planner 视频，以及 4 条原片直接交付对照，共 32 条。
- 主要配对为 041 绘本短任务、027 蚀刻短任务、024 故障长任务、fewshot_004 太空乒乓球长任务；每题在 Bernini 和 Ditto 上分别比较直接提示词与 Planner，共 8 对。
- 主表由 `primary_cases.json` 预定的 16 条输出组成：每模型 direct/planner 各 4 题（041/027 短、024/fewshot_004 长），四源等权，形成 8 对。每个方法同时输出四题总体、短 2、长 2 三张表，共 12 个方法×轨道面板。
- 其余 12 条长提示词和保留约束变体作为补充分析，4 条原片对照用于校准，均保留在逐视频页面；它们不扩大主表分母。每源为统计聚类单位，多检查项／多变体不增加独立样本量。
- 短长任务共享指标定义和评分尺度，区别是原始要求、冻结卡和创作自由度。short 不继承未要求的 long 配色／材质细节；Planner 扩写后，原始 track 仍保持 short。
- 这些素材已经用于开发，评价卡在本轮评分前固定，属于回溯性开发评价。四题、单 seed 的结果用于检查具体改善与失败模式。
- 新增知识库消融和 loop 结果由部署会话交付新快照，按各自冻结版本加入后续评价批次。

## 证据与盲评

`prepare_first_wave.py` 固定六张任务卡，校验源视频和输出哈希，读取交接中的根源视频 PTS 映射。
语义与时序评价使用整个任务区间的连续原生帧；不复制末帧补齐。普通题按 5 秒区间取帧，
乒乓球按实际约 4.43 秒区间取帧。允许的风格化变化写在任务卡中。

语义、风格美学、创造性设计分别使用独立模型调用。最终评价只接收原始任务、冻结卡和对应画面，
不接收生成提示词、方法名、知识读取记录、在线 critic 或接受决定。

创造性设计调用使用 12 个概览时间点以及同题的固定匿名候选集合；每个候选取首、中、末三帧。
集合由该初始批次的全部同题生成视频组成，按图像哈希确定顺序，各方法共用同一候选总体。
每次调用按视频 SHA 排除被评视频自身及其完全相同副本，再与其余候选比较；集合保存在 `references_cohort_v2`。
因此相对独创性分数表示该固定候选总体内相对于其他输出的设计差异。后续批次使用版本化集合；跨集合分数需重新统一参照后比较。
初次抽查发现评价器将自身参考的完全匹配计为缺少独创性，故统一启用上述排除规则。
原始调用保留，修正后的创造性调用使用 `creativity_v2.raw.json`，所有条件执行同一规则，语义和美学缓存继续复用。
这一调用的证据范围是外观和设计，细微时序创造性保持未判定。

8 对主要比较另外进行 A/B 顺序互换的匿名偏好评价。配对调用只使用匹配的概览帧，
细微动作保留的判断以连续帧逐项评价为依据。未知与平局分别记录。

当前执行器运行 VLM 指标。CLIP-F、DINO-F 由独立特征程序计算后再接入；运行此批次不代表已经测得这两项。

## 执行与恢复

在具备 PyAV、Pillow 与已登录 Codex 的环境中，从仓库根目录运行：

```powershell
python scripts/eval/prepare_first_wave.py --handoff out/evaluation_handoff/20261029T163320Z --run out/evaluation_runs/20261030_first_wave
python scripts/eval/run_first_wave.py --run out/evaluation_runs/20261030_first_wave --workers 2
```

准备与评价可同时运行，评价器只读取已经完整写出 `evidence.json` 的条目。
`LOW_HIGH_CODEX_BIN` 可指定 Codex 可执行文件；模型与推理强度通过
`LOW_HIGH_AGENT_CODEX_MODEL=gpt-6.1-sol` 和 `LOW_HIGH_AGENT_CODEX_REASONING_EFFORT=xhigh` 固定。
每次调用保留原始响应和签名，复用已完成评分，最多两个独立调用任务并行。
同主机锁避免同一运行目录被重复启动。等待证据的默认检查间隔为 600 秒。

运行过程写出 `worker.json`、`status.json`、`records.json` 和逐条 `judgments/`。
中途报告只覆盖已经评价的条目，待评价条目不计作生成失败。评价异常单独保留，
已确认的交付状态与未知的内容分数分别记录。
全批次结束后输出 `primary_report/`、`primary_differences.json`、
`pairwise_results.json` 与 `completion.json`；异常列表为空才表示全部内容评分成功。

汇报保留语义修改、核心保留、细节保留、风格、美学、创造性设计、时序及未知覆盖率的分项结果，
并提供原视频、生成视频和逐项证据。读知识次数与提示词长度只用于解释过程，不进入视频质量得分。

使用 `python scripts/eval/render_evaluation_review.py --run out/evaluation_runs/20261030_first_wave`
可生成或刷新 `review.html`，同页查看原视频、各条件原生输出、小数分数和逐项证据，并按渲染模型筛选。
该步骤只读取已有材料，不调用模型；页面显示当前评分覆盖数量，未评分项保持待评价。
生成提示词单独折叠展示，用于复盘；它们不进入最终评价模型的上下文。

## 当前统一指标 v3

定义与状态规则见 [统一协议](evaluation-protocol.md)和[自动生成指标表](evaluation-metrics.md)。新 score() 直接输出 0–1 语义分；VLM 原始评分为 1–4、0.1 步长；比例单列 %。unknown、不适用和执行失败在计算及各级统计中保留独立状态。五项美学及跨样本均值标记为计算值，底层精度完整保留。

```bash
python scripts/eval/reexport_first_wave.py --run out/evaluation_runs/20261030_first_wave
```

只读取已保存的 32 条原始 judgment，重新做确定性计分，核对历史标签公式、评分、成功状态和排序；没有模型调用或视频生成。原始 record/judgment 不变。四题主比较输出到 primary_report_v3/，全部条件补充表为 report_v3/，刷新 review.html。

- summary.json/metrics.csv：总体与短长表，有效/适用/预定源数、各状态计数、覆盖率和语义全体界限。
- metadata.json：完整注册表、哈希、逐列计算、尺度及精度。
- records.normalized.json：新计算结构，保留 rating_status/metric_status、原判断签名和版本。
- cohort.json/paired_differences.json：16 条入组及同 seed 配对差值；独立源数为 4。
- validation.json：原始步长、公式、幂等、排序/成功状态及受保护文件 SHA。

041 短任务的装订/独立纸页复核仍 pending，本次保留原判断。

[reports/20261030-evaluation-v2](../reports/20261030-evaluation-v2/README.md) 是此前 32 条结果的 v2 展示快照，继续保留；更早 20261030-sync 是 22/32 阶段快照。当前 canonical score 已在计算入口采用 0–1。需要发布 v3 时，用 --publish 指定新目录，保持历史快照。
