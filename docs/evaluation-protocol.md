# 视频编辑与 agent loop 统一评价协议

冻结卡/原始 judgment 协议仍为 `lha-evaluation-v1`；新计算结果为 `lha-score-v3`，统计/展示为 `lha-report-v3`，唯一指标定义为 `lha-metrics-v3`。

可执行定义位于 `src/evaluation/registry.py`，名称、含义、尺度、精度、适用性、证据和计算方式见 [自动生成指标表](evaluation-metrics.md)。校验、计分、judge 评分定义、报告和文档共用注册表。三层依次为原始判断、确定性计算、源级统计。
PickScore 不属于本版。代码入口为 `scripts/eval/evaluate_benchmark.py`，核心实现位于 `src/evaluation/`。

## 1. 评价对象与资产边界

- 正式依据为原视频、用户原始指令和生成前固定的评价卡。planner 扩写提示词只进入过程诊断。
- 当前 `benchmark_data/all_samples.json` 有 50 条正式视频与 7 条示例。正式视频有短、长两个任务；示例只有长任务，共 107 个任务入口。
- 新数据包没有配套标准生成视频。包中的 source 抽帧、旧 target、旧 rubric 和旧评分不作为本版目标答案。
- `main`、`fewshot`、`development` 分开统计；已经参与提示词／planner 调试的题目应标记开发暴露。
- 一个源视频是统计聚类单位。多 seed、短长指令、帧和检查项都不是独立的视频样本。
- `examples/evaluation/041_*.card.json` 是基于已看片的开发示例，包含真正的原始需求与源文件哈希；不附带虚构评分。041 已用于开发，不代表未接触的测试题。

## 2. 评价卡

每张卡含 `task_id/source_id/split/track`、原始 `requirement`、源视频路径和 SHA-256、评价时间范围、允许设计范围、风格与创造力适用性，以及分组检查项。

| 字段 | 约定 |
| --- | --- |
| `groups[].kind` | `edit`、`preserve_core`、`preserve_detail` |
| `groups[].items[].id` | 全卡唯一、稳定；judge 原样返回 |
| `text` | 对象—属性—位置—时间的可观察命题 |
| `mandatory` | 生成前确定的硬要求；核心保留项始终为硬约束 |
| `partial_rule` | 明确部分达成边界；不允许部分时填 `not allowed` |
| `temporal` | 是否属于动作／事件／时序语义 |
| `evidence` | `frames` 或 `sequence`，细微动作与事件需连续证据 |
| `interval_seconds` | 可选的局部证据时间范围；缺省表示整个任务区间 |
| `allowed_changes` | 用户授权的修改及设计自由，保留语义所允许的绘制变化 |
| `creativity` | `open`、`bounded`、`none` |
| `duration_seconds` | 实际约定的完整片段长度，5 秒任务填 5.0 |
| `source_start_seconds` | 原片片段起点，默认 0 |

原始要求是一级组，组内再拆观察点。把一个要求拆得更细不会增加该要求的总权重。
短任务不继承长任务的额外配色／材质要求；保留项按语义制定，允许风格化改变像素和表面绘制。
没有固定检查项数量配额。

`scaffold` 只创建任务入口，**不生成已经审定的语义标签**。`annotate` 只看源视频与原始指令，生成草稿。
审阅者核对原片、要求、保留边界、部分分标准及时间要求后运行 `freeze`。审阅者可以是独立核对源证据的执行者，人工终评另行记录。
冻结后记录 `reviewed_by` 与内容签名；任何内容改变都会使既有 judgment 失效。修改卡应建立新版本和新运行目录。

## 3. 语义指标

事实标签：`pass=1.0`、`partial=0.5`、`fail=0.0`、`unknown=null`。保留项的 pass 表示保留成立。
每项须有证据和输出时间点；已判断的 sequence 项须有连续证据。

对同一种类的 K 个要求组，0–1 归一化语义得分为：

```
S = 1 / K * sum(mean(该组检查项分值))
```

这是标签的分组加权计算分，显示两位小数；不采用 VLM 连续 0.1 打分。完整完成比例使用同样分组权重，只将 pass 计为 1，乘 100 后以 % 单列。证据覆盖率、成功比例、损伤比例同样明确标为 %。

新 score() 直接产生 0–1 的 score/lower/upper，记录 scoring_version、semantic_scale、metric_registry_version/sha256。历史 v1 record 的语义 0–100 编码只由 compat.py 转换；历史 v2 unit_interval 标记直接复用。版本不明确且不属于已知旧协议的数据被拒绝，不按数值大小猜尺度。旧原始文件保留，重导出使用新版本目录。重复适配保持幂等，coverage/complete_rate 仍为 %。旧 68.75 对应新 0.6875 分，默认显示 0.69。

四项语义为 edit、preserve_core、preserve_detail、preserve_time，定义由注册表生成。非预期/重大损伤是独立的视频比例。时序语义保留关注原行为与事件；输出自身时序协调关注输出连续性。

某类语义指标包含 unknown 时，该指标 score=null，同时给出 lower/upper/coverage。
lower 将未确认项按 0、upper 按 1 计算，表示**证据上下界**，不等于统计置信区间。
coverage 采用相同的组等权规则，items/unknown 另外提供原始检查项数量，因此 coverage 不一定等于简单的已知项数／总项数。
unknown 不删除、不填 0.5；没有适用项目与证据不足分别记录。
damage_review 未完成时，无已确认损伤不能自动解释为零损伤。
每条 damage 通过 related_item_ids 关联既有检查项；仅涉及 optional detail 的变化只能记 minor，包括这些细节对象的数量与结构。空关联表示未列出的新问题，major 仍须涉及关键主体、行为或硬约束。judge 不能通过另写一条严重损伤，把预先确定的细节要求升级成硬门槛。

整题成功条件由注册表 SUCCESS 固定：有效交付、mandatory 及核心项全部 pass、无重大非预期损伤，以及适用时达到风格门槛；当前门槛见自动生成指标表。
任何已知硬失败产生 fail；没有硬失败但关键证据不足产生 unresolved；其余为 pass。
报告同时给出 `success_confirmed`、`success_possible` 和 `success_unresolved`。
风格、美学与创造力分数不补偿语义硬失败。

## 4. 风格、美学与创造力

单次评分范围与步长读取注册表，当前为 1.0–4.0、0.1；拒绝 NaN、越界或超出步长的原始评分。
1：明显不足；2：部分成立且有清楚缺陷；3：良好，只有较小问题；4：充分协调、达到该任务优秀水平。
小数按可观察的程度插值，必须提供理由。小数显示不意味着 0.1 的差异必然可靠。

风格、五项美学、输出自身时序协调及两项创造性的原始定义、锚点、证据和适用范围均在注册表维护，judge 提示词直接引用。详见自动生成指标表。

五项美学等权平均为 `aesthetic_mean`。这是本版明确计算的平均值，和历史 holistic overall score 含义不同。
单个 VLM 原始评分及其均值默认显示一位小数。`3.64` 可以是五项原始评分的算术均值，也可以是跨样本的计算均值；报告显式标为计算均值，默认显示 `3.6`，JSON 和 CSV 的 mean 保留完整精度，并另存 display_mean。显示舍入不改变排序计算、成功状态或原始评分精度。
情绪依据原场景及用户要求；颗粒、轮廓简化、设计性闪烁按风格条件评判，不默认追求写实、昂贵感或高饱和。

开放短任务完整评价创造性设计；详细长任务评价剩余自由；严格局部修改设 creativity=none，两项 N/A。
用户指定了水彩，完成水彩本身计入编辑／风格；创造力评价其在场景中的具体组织。
未经要求的新主体和错误替换按语义损伤记录，不靠增加元素获取创造力分。
没有固定对照集时，relative_originality=unknown。对照集必须属于同题，提供匿名帧、文件哈希和集合签名。

## 5. 视频证据和自动指标

`prepare` 使用 PyAV 解码真实 PTS，对齐 source/output，保存索引、时间、JPEG 哈希和整包签名。
默认 12 对概览帧；不会复制最后一帧补足短视频。
交付时长容差固定为 0.08 秒，当前允许 101/20=5.05 秒的完整 native 视频作为 5 秒任务。
源片不足约定片段、错误映射、哈希不匹配会明确报错。时长有效不代表动作有效，异常冻结仍由动作和时序项目判断。

默认映射为同时间秒；模型重采样或裁剪时，传入实际逐输出帧对应表：

```json
{"source_sha256":"...","output_sha256":"...","source_times_seconds":[0.0,0.05,0.1]}
```

数组长度必须等于实际解码输出帧数。不要把经过 stream-copy 的 edited.mp4 直接假定为 native 前 N 帧；此前产物出现过尾部 B 帧丢弃。
映射采用原片起始 PTS 归零后的时间。任务片段起点另由 source_start_seconds 给出。

`--dense START END` 追加该区间所有输出帧及对应源帧，可重复传入。
无 dense 时，代码拒绝 judge 声称拥有连续证据，temporal_coherence 必须 unknown。
有 dense 也检查证据范围：只有覆盖检查项 interval_seconds（缺省为全片）才允许确定性 sequence 判断；全片 temporal_coherence 需要全片 dense 覆盖。局部片段不能证明全片细微动作保留。必要时整段提供或人工看片。
`pairwise` 使用统一概览采样协议，允许原生帧率导致的至多 0.1 秒取帧差异；每个候选都带自己的真实对应源帧与时间表，避免把不同帧率强行视为逐像素同步。超过容差会报错，不进行尾帧填补。

CLIP-F/DINO-F 使用输出本身，在固定 4 fps 采样后，对相邻帧特征归一化并取余弦均值；不输入原视频。
默认 CLIP ViT-L/14 和 DINOv2-large 的 CLS 特征。编码器可配置，记录模型、revision、实际解析 revision、预处理、采样索引和时间戳。
正式运行固定权重 revision；不同编码器／采样配置拒绝汇总到同一报告。
尺度为原始余弦，显示四位小数，允许数学上的负值；不沿用旧脚本乘 100 的尺度。
高内部一致性可由静止画面获得，动作保持由语义时序项和连续证据另行验证。

## 6. 独立 judge、盲评与可靠性

语义、设计、创造力各一次独立请求。请求仅包含原始需求、允许范围、评价卡和视觉证据，不含方法名、生成提示词、在线 critic 或既往分数。
raw 响应、system/user 请求、模型配置与图像哈希分别保存。相同签名复用；输入或 judge 配置变化拒绝静默复用。
每张图发送前后涉及的缩放由 backend 决定；正式运行固定 backend。内置兼容 API 后端固定最长边 1024、JPEG 95。
本地 Codex 后端采用其自身的固定预处理并记录 client 类型；不同后端不能默认为同一种评价器。

`pairwise` 将 A/B 交换再评一次：方向冲突记 tie 并记录 order_disagreement；证据不足仍记 unknown。
`preferences` 汇总 A 胜、B 胜、平局、未知、N/A，并按 `(A胜 + 0.5*平局)/可判断数` 计算偏好率。
输入的各条配对必须始终保持同一方法为外部 A、同一方法为外部 B。

人工主对比建议两名独立评分者；分歧复核。`agreement` 对同一指标的一组唯一 case_id 计算平均绝对差、A-B 偏差与相差不超过 0.5 的比例，保留缺失数量。
它用于 1–4 小数评分的校准；二元事实和偏好的一致性另看原始标签／配对结果，不能把 0.5 容差率跨尺度比较。
同一个模型隔离上下文提供流程独立性；模型偏好仍需要人工或第二评价模型检查。

## 7. 状态、统计与输出

每个结果保留 metric_status/rating_status；原始标签、证据和时间点在 judgment 中。unknown 是证据不足；not_applicable 由冻结卡决定并排除适用分母。evaluation_error、missing_output、invalid_delivery、missing_record、not_measured 分别表示评价失败、缺视频、交付不合格、尚无记录、尚未测量；legacy_status_unavailable 表示旧空值没有可恢复状态。有原判断时重新做确定性计算即可恢复状态，无需调用 VLM。

汇总逐列给出 observation_counts、source_counts、n_sources、applicable_sources、total_sources、coverage_percent。无适用源时 coverage=null、missing_sources=0；未知及失败保留在适用分母。mean/ci95 针对完整适用源。语义 population_lower/upper 对全体适用源按同样权重汇总；执行缺项使用 [0,1] 可行范围并另列错误计数。十个等权任务中八个为 0.9、两个未知时，已知均值 0.9，全体区间 [0.72,0.92]；这与 bootstrap 置信区间分别解释。

`report` 按 method/split/track 分组，并支持 `track=all` 的同一预定任务集合总体表。先在每个任务内平均 seed，同源多任务再等权合并，最后对源宏平均；源级 bootstrap 2000 次，固定 seed=20261029，给出 95% 百分位区间。四题主比较一源一题，因此总体等于四题等权平均；短 2、长 2 分轨采用同一指标、量尺和算法，区别在原始要求、冻结卡与创作自由度。Planner 扩写不改变原始 track。
单个源视频不给统计区间。某源的某项存在缺失 seed 时，该源点估计留空，但语义上下界仍纳入报告；每个指标显示 n_sources/total_sources。
`compare` 先匹配 task/source/seed，再计算 A-B，以源为单位 bootstrap；不匹配和缺失明确保留。
CLI 和 Python 汇总/配对入口统一读取兼容适配后的 0–1 语义分。差值尺度从原指标范围推导，当前语义差值 [-1,1]，VLM 差值 [-3,3]。不保留第二套百分制语义计算路径。
所有方法必须共享同一 frozen card。完整评测必须提供完整的预定 manifest，不能仅提交成功生成的条目。
缺少 output 计 missing_output，内容未评价且整题交付失败；不合格时长等计 invalid_delivery。judge／环境／证据准备失败计 evaluation_error，整题为 unresolved 或已知交付失败。执行错误单独记录，不构造假的 unknown judgment。CLI 评价执行失败退出码为 1，记录留在预定分母。

原始输出包括 `records.json`、逐视频 `judgment.json`；新计算/统计输出 `records.normalized.json`、`metadata.json`、`summary.json`、`metrics.csv`、`report.md`。metadata 逐列给出 scale、unit、aggregation、display_decimals、computed_mean 等信息。
0–1 语义计算分和比例显示两位小数，VLM 原始评分及其计算均值显示一位，特征余弦四位；JSON/CSV mean 保留完整计算精度。主表严格使用预定的主要对照清单，补充提示词 long/long_keep 变体和原片对照另列；源级有效样本量不会随检查项、seed 或同源变体增加。预定缺失输出、指标未知和证据覆盖分别可见。
总体报告始终显示覆盖率；创造力合格子集的分析必须同时附全体结果及子集比例，不单独展示筛选后的高分。
正式论文用语义表、设计与质量表、loop 表，避免把它们加权成一个可互相抵消的总分。

## 8. Loop

每个候选保留实际 input_version、prompt、previous_accepted、accepted、decision_reason、generation_seconds 和独立终评 judgment。
首轮 accepted=true，作为共享 incumbent；后续的 previous_accepted 必须对应真实上一接受版本，拒绝候选不成为比较基准。
每份 judgment 都使用原始 source 的同一评价卡，不能将上一生成视频当成保留语义的最终真值。

- 修复率：上一接受版本未完成的编辑项，本轮转为 pass 的比例。
- 新损伤率：上一接受版本 pass 的保留项，本轮转为 partial/fail 的比例。
- 回退率：上一接受版本 pass 的编辑项，本轮转为 partial/fail 的比例。
- unknown 不当作修复或损伤结论；给出可确认上下界，分母为零时 N/A。
- 终评错误接受使用显式 v1 标准：无事实分下降、无新增严重损伤、交付有效，且至少一项事实或设计分有可观察提升。
- 该标准比整题成功更关注迭代的增量；尚未整题成功的候选仍可在确有改善时接受。
- 同时输出首轮／最终各项差值、每次机会后的已接受版本曲线、所有候选总次数与耗时、错误接受率及其未知上界。

该接受标准需与在线 critic 的实验协议一致。若未来使用其他接受策略，应明确新增协议，而不能把 v1 的错误接受率直接贴到另一策略上。
成本包含被拒绝的生成。首轮共享时保留实际成本，跨路线成本比较注明共享分摊。固定生成预算的重复采样基线需要相同独立终评。
回退通过选择保存的历史视频实现。本模块离线分析，不修改在线 loop 的决定或长期 skill。

## 9. Planner 诊断

`plan` 接收结构化可观察 proposals，独立检查 edit 要求覆盖／冲突和每个设计的可见落地情况。
输出明确标记 diagnostic_only；它不改变正式用户目标或主评分。
不按提示词长度、知识条目数或自我解释奖励 planner。

## 10. 安装与运行

Python >=3.10。评分、验证、统计、loop 和单元测试核心仅用标准库；真实视频和编码器需要：

```bash
python -m pip install -r requirements.evaluation.txt
python scripts/test_evaluation.py -v
python scripts/eval/evaluate_benchmark.py --help
```

大模型权重仅在显式运行 features 时按指定编码器加载；安装依赖和执行统计不会自动运行生成模型。
不覆盖现有 GPU 的 PyTorch 环境；按该机器 CUDA 版本安装兼容 torch，或在独立评测环境安装。

建立 107 个任务入口：

```bash
python scripts/eval/evaluate_benchmark.py scaffold \
  --index benchmark_data/all_samples.json --out out/evaluation/task_index.json
```

生成一张 source-only 草稿并审阅冻结：

```bash
python scripts/eval/evaluate_benchmark.py annotate \
  --index out/evaluation/task_index.json --task 041__long \
  --factory evaluation.backends:OpenAICompatibleJudge --out out/evaluation/annotation/041_long
python scripts/eval/evaluate_benchmark.py freeze \
  --card out/evaluation/annotation/041_long/card.draft.json \
  --reviewer YOUR_REVIEWER_ID --out out/evaluation/cards/041_long.json
```

内置 API 后端读取 `LHA_EVAL_BASE_URL`（包含 /v1 的兼容根地址）、`LHA_EVAL_API_KEY`、`LHA_EVAL_MODEL`；默认模型 gpt-6.1-sol，reasoning_effort=xhigh。
需要网关支持 chat/completions 的图像输入与 JSON 输出；接口不兼容会明确报错，不伪造评分。
已有本地订阅后端可传 `--factory vlm.codex_vlm:CodexVisionModel`，使用该项目部署后的 Codex CLI 登录和环境。其实现由现有部署代码提供，不在本模块重复复制。
所有后端也可用 `--factory your_module:YourClass --client-options '{"role":"benchmark_final"}'` 接入；构造后需有 `predict_json(system_prompt=, user_text=, image_paths=)`。
凭证放环境变量，不放 client-options、manifest 或 Git。

使用本版 041 开发示例跑单视频：

```bash
python scripts/eval/evaluate_benchmark.py prepare \
  --card examples/evaluation/041_long.card.json \
  --video out/prompt_probe/20261029_bernini/041__long_keep/native.mp4 \
  --out out/evaluation/041/evidence
python scripts/eval/evaluate_benchmark.py judge \
  --card examples/evaluation/041_long.card.json --evidence out/evaluation/041/evidence/evidence.json \
  --factory evaluation.backends:OpenAICompatibleJudge --out out/evaluation/041/judge
python scripts/eval/evaluate_benchmark.py score \
  --card examples/evaluation/041_long.card.json --judgment out/evaluation/041/judge/judgment.json \
  --out out/evaluation/041/score.json
```

补连续证据时在新的目录运行 prepare，并增加 `--dense 0 5`；局部片段可用 `--dense 1.2 1.8`。全片帧数可能较多，按 judge 的图像容量选择片段或人工复核。

批量 manifest（路径相对 `--root`，默认工作目录）：

```json
{"cases":[{"case_id":"bernini_041_long_seed42","method":"bernini_baseline","seed":42,
"card":"examples/evaluation/041_long.card.json",
"output_video":"out/prompt_probe/20261029_bernini/041__long_keep/native.mp4"}]}
```

可选 `mapping`、`references`、`features` 为对应 JSON 文件路径。预先固定同题 reference set 格式：

```json
{"task_id":"041__long","candidates":[{"images":["/absolute/anonymous_frame.jpg"],"image_sha256":["..."]}]}
```

```bash
python scripts/eval/evaluate_benchmark.py evaluate --manifest manifest.json \
  --factory evaluation.backends:OpenAICompatibleJudge --out out/evaluation/run01
python scripts/eval/evaluate_benchmark.py report --records out/evaluation/run01/records.json \
  --out out/evaluation/run01/report
python scripts/eval/evaluate_benchmark.py compare --records out/evaluation/run01/records.json \
  --a planner --b baseline --metric edit --out out/evaluation/run01/edit_difference.json
python scripts/eval/evaluate_benchmark.py features --video output.mp4 --device cuda \
  --clip-revision YOUR_COMMIT --dino-revision YOUR_COMMIT --out features.json
```

配对用 `pairwise --card CARD --a EVIDENCE_A --b EVIDENCE_B --factory FACTORY --out DIR`，再把各配对 JSON 组成数组交给 `preferences --pairs FILE --out FILE`。
人工校准输入为 `[{"case_id":"...","a":3.4,"b":3.7}]`，用 `agreement --pairs FILE --out FILE`。
Planner 输入为 `{"proposals":[{"id":"design_1","text":"可观察的设计"}]}`，用 `plan --card CARD --plan PLAN --evidence EVIDENCE --factory FACTORY --out DIR`。

Loop 输入是数组，每项结构如下；judgment 为完整新协议对象，不是文件名：

```json
{"id":"r2","input_version":"r1","previous_accepted":"r1","accepted":true,
"prompt":"实际发送提示词","decision_reason":"在线决定理由","generation_seconds":640.2,
"final_judge_independent":true,"judgment":{"protocol":"lha-evaluation-v1","...":"完整对象"}}
```

运行 `loop --card CARD --rounds ROUNDS_JSON --out RESULT_JSON`。首轮 input_version=source，无 previous_accepted。
`final_judge_independent` 是运行记录的声明，执行者须确实使用独立终评上下文；布尔标记本身不证明独立性。

旧 `judgment.json`、`judgment_v2.json`、`judgment_v3.json` 保留原状。旧结果缺失本版量表和部分证据，不能直接改标签当作新协议完整结果。

## 11. 方法来源与适用边界

- CoVEBench 的分项指令、保真和整体组合要求评价：[官方实现](https://github.com/NJU-LINK/CoVEBench)。
- VBench 的视频内部一致性、运动和闪烁等多维分解：[官方项目](https://vchitect.github.io/VBench-project/)。
- 本文的分组权重、1–4 小数评分、成功门槛、创造力和 loop 定义是本项目 v1 协议，不宣称与上述论文的指标数值可直接互换。

评测代码和可执行入口不等于已经完成全量标注或全量打分。正式运行前仍需完成全部任务的源视频评价卡审阅、固定参考集与独立人工校准；不得把 draft 或测试 fixture 作为正式成绩。

## 12. 定义维护与版本边界

```bash
python scripts/eval/export_metric_definitions.py
python scripts/eval/export_metric_definitions.py --check
python scripts/test_metric_registry.py
```

新增或更改指标只修改 registry.py，并更新版本与生成文档。结果绑定注册表、冻结卡、原 judgment 签名及可用的证据/参照/evaluator 版本。新 judgment 绑定原始判断契约，计算结果绑定计算契约，完整注册表哈希用于追溯。原始定义/量尺/锚点/证据改变时拒绝复用旧判断；计分/权重/成功规则改变时需重新做确定性计分。仅改名称或显示精度时，两份契约哈希不变，可直接复用原判断和计算分。展示脚本不另建名称、尺度或精度表。

在线结果标记 online_feedback/online_critic，正式汇总拒绝这些诊断记录；历史角色不明的记录保留来源供审计。Loop 先记录最终选择，再执行终评。此次重构不启动 loop、不改变候选选择。
