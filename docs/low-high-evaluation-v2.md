# Low→High 评分与默认评测（当前 v3）

2026-11-02 本地实现。入口为 [run_low_high_eval.py](../scripts/run_low_high_eval.py) 和当前统一实验调度；本轮没有提交真实模型、渲染或编码器任务。

## 任务依据

终评依据原始提示词、源视频和生成视频，使用统一评分手册。逐题冻结意图、核心转换补充、人工审批状态及相关等待已移除。长短任务共用五维锚点，各自按实际输入的提示词评价；短任务不承担只在长提示词中出现的细节要求。

原提示词按原文标点分成固定片段，保存文字及字符位置。片段只用于核对原文，模型不扩写任务。一个片段包含多个要求时，全部满足才记 pass。`track=short/long` 表示提示词类型，与视频时长无关；统一入口从 `prompt_form` 传入，单项入口用 `plan --track short|long`。

```json
{"track":"long"}
```

`plan.json` 只记录原文片段、任务类型、固定证据区间和条件动作比较配置，并绑定源视频、原文和协议版本。创建过程无需模型或人工意图审批。代码见 [task_spec.py](../src/evaluation/task_spec.py)、[low_high.py](../src/evaluation/low_high.py)。当前协议为 `lha-low-high-final-v3`、任务计划为 `lha-low-high-task-plan-v3`；历史计划和评分保留原版，新评价使用新目录，不修改已有生成视频。

## 评分组成

| 层次 | 指标 | 尺度与判断 |
|---|---|---|
| 共同五维 | IA 指令达成、CP 必要源内容对应、TC 时序一致性、VI 视觉完整性、AC 美学协调 | 每次判断为整数 0–4；各分值的具体锚点见[统一评分定义](../src/critic_harness/SCORE_DEFINITIONS.md) |
| 逐项语义 | edit_completion、required_correspondence | pass=1、partial=0.5、fail=0；unknown 未知；真正不适用另列。动作重构允许替换原行为逻辑，不以逐帧原样保持为目标 |
| 长任务专项 | binding_accuracy、joint_satisfaction | 对象—属性／关系绑定正确度 0–1；全要求联合满足为 0/1，检查原文全部片段、必要对应和非授权损坏 |
| 短任务专项 | style_realization、scene_specific_design、effective_creativity、relative_originality | 风格实现、场景适配、有效创造性、相对原创性，各整数 0–4。无相应设计自由度可不适用；相对原创性缺固定匿名参照集时记 unknown |
| 美学诊断 | narrative_emotional_fit、style_world_consistency、composition_lighting、color_texture、hierarchy_readability | 叙事情绪适配、风格世界一致、构图光照、色彩材质、视觉层次，各整数 0–4；五项齐全才计算 aesthetic_mean |
| 非授权损坏 | unrequested_damage、major_damage | 每题 0/1；轻微或严重损坏均计前者，严重损坏单列后者；总体以有效题的比例呈现 |
| 特征连续性 | CLIP-F、DINO-F | 输出视频 4 fps 相邻抽样帧的特征余弦均值，原始范围 −1 至 1 |
| 全帧时序 | flow_warp_l1、motion_diagonals_per_second、low_motion_duration_fraction | 光流补偿像素误差、每秒归一化运动量、低运动时长占比；保留原始单位 |
| 条件动作保留 | flow_velocity_error；可选轨迹误差 | 仅在任务要求保留运动、指定对应区域且几何配准明确时比较源与输出；未满足条件则不出数 |
| 两两盲评 | task_completion、production_quality | A 胜／B 胜／持平／证据不足；随机初始顺序后交换再评，两次分歧记 order_unstable |

五维评价整体表现，逐项语义解释哪些原文要求完成，长短专项解释任务类型差异，美学与自动指标补充诊断。各项分别呈现，不加权拼成一个总分。短任务同样计算明确要求的完成度；长任务同样计算美学五项和全部输出时序诊断。

长任务联合满足：全部适用要求 pass 且未发现非授权损坏，记 1；明确 partial/fail 或存在非授权损坏，记 0；其余证据不足记 unknown。它是严格的联合条件统计，不是视频交付资格，也不替代连续分数。

逐项语义有未知时保留 `valid/applicable`、下界和上界，不把未知补成中间分或用已知项均值冒充整题完成度。证据不足记 unknown；不存在等待逐题意图确认的评分项。数据结构、短任务五档锚点与计算见 [task_metrics.py](../src/evaluation/task_metrics.py)、[registry.py](../src/evaluation/registry.py)。旧评价卡的逐项核对方法沿用；旧 1–4／0.1 步长的历史记录保留原协议，不转换成新版 0–4。

## 证据、自动指标与盲评

终评概览固定沿源时间轴均匀取帧，5–6 秒通常 20 帧；输出缺失位置按缺项记录。当前默认把完整源时间轴按原生 PTS 分段，逐段查看连续帧，再给主分及专项诊断。每段边界由源视频决定，所有方法共用；如操作方预先固定特定事件区间，也保存其版本。每次调用的实际范围、缺失和失败单独记录。终评不读取在线选帧、关注意见和分数。

在线检查使用 `lha-qualitative-review-v1`，每次成功生成后运行。默认由独立 Critic 根据原始任务、提交／实际提示词、Planner 关注重点、源片、实际输入和候选给出定性评价与证据；可配置为 Planner 自评。两种模式共用概览、原生连续帧、分页、裁剪和补看。在线检查不暴露本页的五维锚点、`task_metrics` 或正式评分手册；长短提示词按实际原任务理解。参见 [Video review Skill](../.agents/skills/lha-video-review/SKILL.md)。

[final_suite.py](../src/evaluation/final_suite.py) 默认调度 CLIP、DINO 和光流，并按视频与配置缓存，跨判官与重复候选复用。CLIP-L/14 和 DINOv2-large 的精确版本已固定，采样为 4 fps。光流采用 Farneback、最长边 512，对全部原生相邻帧计算前后向一致性掩膜后的 warp L1，按有效时长平均，并记录有效帧对及像素覆盖。静止片段也可能有低误差、高特征相似度，因此同时展示运动量和低运动占比。它们不单独判断语义或动作完成。

源—输出光流一致性是条件项；世界重构不默认要求复制源动作。专项 `temporal --geometry-aligned` 入口用于已经核实对应范围与几何的情况。可选轨迹误差只接收已有注册轨迹，本轮没有增加姿态检测器。

原三组调度默认在五个报告位置形成六组既定对照，双方可用时调用[两次交换顺序的盲评](../src/evaluation/pairwise.py)。判官只见匿名 A/B、原任务和终评证据。缺失交付的配对保留 planned 分母。两位判官分别汇总。

## 运行与结果

先本地生成原任务与证据配置文件，不调用模型：

```bash
python scripts/run_low_high_eval.py plan --source /path/source.mp4 \
  --request-file /path/request.txt --track long --output /path/new-plan
```

准备好环境并获得本次运行授权后，单项默认评测：

```bash
python scripts/run_low_high_eval.py score --source /path/source.mp4 \
  --candidate /path/output.mp4 --request-file /path/request.txt \
  --plan /path/new-plan/plan.json --judge glm5.3flash \
  --output /path/new-score --budget-config /path/compute-budget.json --execute
```

省略 `--execute` 只导出终评概览请求。GLM/Sonnet独立终评不要求人为token、调用或费用额度，使用真实live_meter_only记录usage；仅保留请求超时和有限故障恢复。两位判官与 Planner、Critic 共用 OpenRouter Chat Completions API 和外置 `OPENROUTER_API_KEY`。GLM 使用 `z-ai/glm-5.3-flash`，Sonnet 使用 `anthropic/claude-sonnet-5.5`、`reasoning.effort=high`；两者均省略人为输出 token 上限。双卡服务器从 `/root/.config/lha/openrouter.env` 读取临时 SSH 转发设置，流量经用户本机出网。若提供预算文件，仅供`compute:features`、`compute:temporal`的计算账本；默认编码器使用CPU。缺依赖或预算配置时记录 `not_measured`；执行失败保留失败状态及原因，分数为 null。修复环境后的补跑使用新的评测目录，不覆盖旧失败记录。此次离线验证不下载编码器权重、不产生正式实验分数。

每题保存 `judgment.json`（五维＋专项原始评分）、`suite.json`（附自动指标）、`task-metrics/`（原始输入、回答及计算）、自动指标的明细帧对及共享缓存。批次归档补齐同样结果与盲评；`summary.json` 含全部指标的配对差值和有效题数。汇总器 [low_high_summary.py](../src/evaluation/low_high_summary.py) 分长／短／全部及判官、方法输出，先在源视频内求均值，再等权平均源视频；均值可有小数，单次等级分仍为整数。未知、不适用、未测和失败各列计数。

统一视频结果目录使用 `benchmark_results.py prepare-evaluation` 和 `score-evaluation`，评分默认包含全部共同／专项与自动指标；生成与评测分开启动。具体命令见[执行入口](creative-benchmark-execution.md)。

独立主分按维度、专项按字段执行确定性证据校验：合法字段保留原判断，缺失/非法引用字段标unknown，原字段及错误保存在投影回执，verify_answer核验原回答与真正selected-answer绑定。结构不可解析仍作有限恢复，重试输入包含前次输入/回答hash和中性的结构错误反馈。HTTP诊断保留status及脱敏code/message；单请求400/413不自动封禁整个服务，状态码本身也不证明重试安全。

## 配置与实现边界

独立判官配置为 [evaluation.json](../configs/evaluation.json)，由 `evaluation.providers` 创建；API 客户端共享 `vlm.settings` 和 `vlm.openrouter`。正式校验位于 `evaluation.validation`，在线定性评审无需加载它。终评 profile 绑定判官配置与相关实现，更改判官会生成不同评价身份。历史直连接口保留在 `evaluation.legacy_providers`，当前默认入口不使用它。

## 原文位置与视频时间

2026-11-03 输入投影修复：冻结计划中的 requirements.start/end 保留原始请求的字符偏移，用于定位原文；模型可见的 requirement 只包含 id 与原文 text。真实视频事件使用 start_seconds／end_seconds、requested_interval_seconds 和 interval_seconds，帧证据仍使用 frame_index 与 timestamp_seconds。事件观察、终评、成对比较及分项评分共用这一投影。修改会产生新的 final profile 哈希；旧报告与原始输入保留，新评分使用新 profile 的缓存目录。
