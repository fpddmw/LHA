# LHA 工程问题与阶段修复记录 — 2026-11-02

## 当前工程整理

当前入口统一见 [实现说明](creative-loop-implementation.md)、[配置说明](benchmark-guide/configuration.md)、[当前状态](current-status.md) 和 [文档索引](README.md)。本轮覆盖 API 配置封装、在线／正式评价边界、异步失败恢复、任务隔离、实验结算与文档一致性；验证结果集中在当前状态和离线报告。 最终 29 模块 325 项独立离线测试全部通过，源码／配置起止一致，见 [本轮验证](../reports/maintenance-20261102/engineering-cleanup-validation.json)。

默认路径已是 API-only、每次生成后定性 Critic／可选 Planner 自评，finish 复用已有检查。Codex CLI 控制、在线数值评分和二次交付确认属于下文历史阶段。主实验与 RSI 的最新范围见 [运行安排](experiment-campaign.md)。

原始 16 项和历次证据保留在下方。其勾选、运行数量、训练 full、预算和部署状态只代表所在阶段，不累加为本轮通过数量。链式画质结论、历史媒体许可和真实模型效果与当前代码行为分开报告。本轮仅做代码和离线验证，真实实验等待用户通知。

## 历史阶段：API-only 与定性 review 改造之前的执行待办

本节是当前工作的唯一待办入口；下文原 16 项和历史测试用于查询依据。用户最新“去做吧”已授权本轮代码、配置、经验检索及三个 Skill 的实施。此前批注“修了”表示要求修复，不表示已验收。

**本轮采用的约定**

- 每个样本 × 长短任务 × 方法 × seed 独立限额：默认最多 5 次生成，可配置 N；从在线任务获得资源并开始时计时，最多 1 小时。恢复沿用原截止时间。旧默认 64 轮、96 调用、400 万累计 token 不再提前结束任务，保留消耗记录；金额上限是可选能力。
- 用户最新明确取消 GLM/Sonnet 独立终评的人为 token、调用次数和金额额度；只记真实消耗，保留请求超时和有限故障恢复。服务必填的输出容量字段按服务能力配置，不再从低额度反复试探。此更改不影响在线任务 N 次生成／一小时硬限。
- Planner 保留模糊预算提示。内部以生成比例和时间比例的较大值映射既有阶段；不新增精确余额、调用／token 面板或预估耗时门禁。达到 N 后仍可在时限内观察、评审和交付；到时冻结结果并处置本任务持有的执行。
- 继续采用可审计的 Codex 后端，控制客户端基础指令、附加配置、工具及实际图像输入。在线 Critic 保持固定共同评分，补短／长任务诊断和自定义问题逐项响应。
- 用户随后在三卡会话明确确认：train 跑 Planner full，每道任务结束后维护经验并供下一题使用；validation/test 只读经验，经验 full/none 对照放在 test，长短条件均保留。train 维护在运行私有经验版本内核验后原子激活，预算/账本独立；验证和测试固定读取版本。此前“仅测试集维护”及“train 整批后才维护/默认关闭”均由此替换；训练集不默认铺六方法或跑 none。
- 复用现有知识检索能力建立经验地图、手册、模型入口和证据链接；三个经验 Skill 改为面向任务后的 Planner 贡献及批次整理。有效建议、失败与例外均可沉淀，无新认识时允许不提交。
- 保留现有 75 条数据、长短提示、划分、视频和已授权并行维护；源片标准、任务定义校准、新测试划分及论文主张暂缓。旧评分退出当前有效结果，视频集中在同一入口，匹配视频不重生成。统计方案已在代码固定为 seed42 的 test 源视频聚类／配对分析；多生成 seed 的正式实验尚未执行。

| 顺序 | 工作 | 当前状态与完成依据 |
|---|---|---|
| 1 | [ ] N 次生成／一小时的生命周期、模糊提示与取消恢复 | 原轮次／取消恢复修复已通过新增独立复核；D02/D05 到时候选保留及按资源隔离已落地，正在联合验证新调度与最新训练接线 |
| 2 | [x] 在线 Critic 长短诊断与自定义问题闭环 | 已实现同一份主报告中的共同评分、长短诊断及按 ID 绑定的原始问题；自动评审、报告分页确认、终评隔离已覆盖离线检查 |
| 3 | [x] Codex 客户端输入控制与真实请求审计 | 固定实际 CLI 0.165.0 及二进制哈希；本地 mock 捕获真实请求，无暴露工具，图像哈希匹配；注入工具调用被拒且未执行。服务端追加输入仍属未知，未开展付费推理 |
| 4 | [x] 经验检索组织与三个 Skill 的协作方式 | 地图、问题／手册／模型入口、保留阅读和三个 Skill 已接入；full／none 隔离与 Skill 格式已检查，真实使用效果待后续实验 |
| 5 | [ ] 终态后的独立经验维护 | train full逐题维护及私有版本激活已实现，真实Harness→贡献→下一Harness读到新版本的离线测试通过；val/test只读。三卡完整流程实测包已交付启动，未发布共享经验库 |
| 6 | [ ] 主会话独立审阅与必要运行检查 | 独立 90 回合／87 页报告完整交付探针通过；源码在探针期间一致，提前确认被拒且终态恢复不改结果。新D01–D15与真实运行仍在收尾；用户最新明确三卡并行跑三个完整 Planner full harness 验收，包括任务后训练经验维护；裸Best-of-5已停，旧full/none及Direct计划不恢复 |
| 持续 | [x] 统一视频与六方法入口；[ ] Direct 收集和真实对照 | 上轮真实 75 源／150 任务／6 方法离线准备通过，0 次模型或 GPU 调用。三卡会话最近确认 119/150 Direct 已收集校验；统一页面自动更新，另保留 2 个链式控制 |
| 后续 | [ ] 统一新评价与链式分析（LHA-012） | 12 条现有视频的 CPU 特征／光流已实跑完成；双判官四份首轮报告暴露截断／单字段引用问题，正在修正后跑完当前真实评分。现有未评分准备随最终协议刷新；不沿用旧分，不重跑同一视频 |
| 保留 | [ ] 仓库卫生边界（LHA-016） | 历史卡签名与源码导出已修；共享 Git 历史约 721 MiB 及历史媒体许可未知仍保留，本轮不重写历史、删除媒体或发布 |

**供独立审阅者使用。** 审阅当前工作区及未提交改动，不能只审 HEAD。覆盖上列最新用户约定及下列原 16 项；重点检查到时结算与 GPU 所有权、Critic 到 Planner 的问题／证据／确认链、受控 Codex 的实际输入，以及维护失败与实验结果的隔离。原第 1 项取消未确认边界已经补验，当前还有下方新增 D01–D15 的实施与真实测试；不要将上一阶段快照视为本轮最终冻结版。

最新D01–D15受影响联合回归17个文件全过，280项报告测试含导入重复，143.598秒、源码起止一致，见 `out/loop_protocol_upgrade_20261102/final-integrated/verification.json`。此后HTTP安全诊断/服务余额暂停属最后窄补，单独验证与最终包随后列入；这不代表真实GPU/终评已全部验收。

本轮 13 组回归在上一阶段全部通过；日志累计 212 次测试运行含重复导入，不作为 212 个独立测试报告。证据：`out/loop_protocol_upgrade_20261102/verification.json`；真实 CLI 正常／注入请求证据：该目录下 `codex-wire-0.165.0/verification.json` 与 `codex-wire-0.165.0-rejected/verification.json`；主会话独立跨路径证据：`reports/maintenance-20261102/root-paged-delivery-probe.json`。上述验证未调用付费模型或真实 GPU。最终补丁的源码指纹及受影响回归完成后更新本节，不另设平行待办。

## 新增末轮审阅修复 — 2026-11-02

用户在最后一处预算修复验证期间补充 Devin 末轮审阅，明确要求全部修复并支持多卡服务器。以下为当前新增工作范围。保持默认 N=5 可配、最长一小时、Planner 模糊提示；此前暂缓的源片替换、A/B/C 三档重做、i2i/rv2v 新方法和论文主张不混入本轮工程修复。

| 编号 | 当前待办 | 验证与交付要求 |
|---|---|---|
| D01 | [ ] 经验改进的划分与逐题学习 | train full 有序逐题维护，运行私有经验版本核验后供下一题使用；val/test 只读，test 对照固定版本；预算/账本独立，禁止从val/test正式学习或伪造Direct反思 |
| D02 | [ ] 到时保留可用候选与实际预算 | 已评候选可形成明确的 deadline 交付，不伪造 Planner satisfied 确认；best-of-N 保留已完成子集，报告请求 N/实际提交/完成与用时，小时上限不变 |
| D03 | [ ] 核心盲评配对与默认方法 | full/none final 对 direct-best-of-N、none-first 对 planner-once 等；按划分定义默认矩阵（train full学习、validation明确校准、test正式对比），保留长短条件；不再全split默认六方法 |
| D04 | [ ] unknown 评分的候选选择 | 已评维度均值与覆盖数量、确定性 tie/all-unknown 规则，逐候选记录，合法 unknown 不使整列失败 |
| D05 | [ ] 任务与设备分别隔离 | 模型未知隔离该任务/调用，确认空闲 GPU 可继续；GPU 未释放仅隔离该设备，其他 worker 继续；恢复不重复提交 |
| D06 | [ ] 新终评真实验收 | 12视频CPU特征/光流完成；32组双判官评分及盲序比较已实际启动，GLM继续。Sonnet账户明确返回余额不足（剩余$0.287094、请求预扣$0.333828），已暂停该服务并请用户补余额；已完成评分保留。代码人为额度已取消。out/final_evaluation_smoke_20261102/current-report.json承接真实覆盖率、原答、字段投影、消耗与缓存情况；不把外部余额阻碍写成评分失败或工程已全部验收 |
| D07 | [x] 冻结统计方案 | evaluation/statistics.py固定test主终点none-final对direct-best-of-N、全部planned分母、输出缺失赋值与判官未知界限、源视频聚类/配对检验、Holm次要比较和seed42范围；主会话已核对实现，离线回归通过。正式实验数据待运行 |
| D08 | [ ] 最新回归与可部署冻结版本 | 确认审阅者三项失败；源码、测试和运行快照身份一致。共享未提交的数据整理不被打包提交；先以精确源码快照验证部署 |
| D09 | [ ] 多 GPU／多服务器吞吐 | 显式设备或自动发现、每卡常驻 worker、任务原子认领与恢复、统一 profile、共用结果入口；默认每卡一生成，多并发需已测显存依据；运行元数据记录硬件 |
| D10 | [x] Direct 与 ProcessRenderer 路径等价性 | train 001 short / seed42 / 同一4090D实跑与官方Direct文件字节完全一致；101帧PTS/RGB全同，参数、编码提示与资产核对通过；主会话复核28份证据哈希及视频字节。见 out/bernini_direct_final/20261102/parity-closeout/report.txt；适用此精确案例 |
| D11 | [ ] 自动评价与人工评价边界 | 提供可执行的少量人工盲评抽样/表单与导入，正式结论保留需真人评价；AI 不代填人工结果 |
| D12 | [ ] full/none 共用操作说明 | 公共规划、观察与输入操作规则移入共享手册；full 增量仅为经验发现与经验内容 |
| D13 | [ ] 划分分布与迁移解释 | 实际 source_group/来源分布自动汇总，明确 train→test 来源差异；不改变已授权数据划分 |
| D14 | [ ] planner-once 的真实含义 | 说明其视频证据、无检索及一次规划边界，分别展示 PE / planner-once / none-first / full-first / final，避免名称造成等价误读 |
| D15 | [ ] 卫生和当前文档 | 删除已确认空杂文件（有锁持有者时保留运行锁）；修真实历史路径引用，在线 Critic v6 与入口/预算/维护口径一致 |

已完成的新证据：上一处“在线到时且无法确认取消”的修复由主会话独立重跑 3 项，6.243 秒全过且源码前后一致，见 `reports/maintenance-20261102/root-final-boundary-validation.json`。121 个现有视频位置（119 Direct + 2 链式）的新评分准备已刷新且未调用模型；153 个 benchmark 文本文件聚合哈希与本轮执行前一致。新增 D01–D15 仍需按上表验证，不沿用旧测试为其背书。

## 范围与当前状态

- 用户先要求保存清单，随后明确授权 GPT-6.1-sol/xhigh 执行进程逐项全量修复并自查，交回主会话独立审阅。
- 核对基线：本地分支 codex/experience-curation-v1，HEAD c431ce67827aad1f355ed10eec7f1b8f31f56c53。本文行号对应此基线。
- 原始 16 项跟踪：**13 项已完成工程验收，LHA-004 / LHA-012 / LHA-016 仍保留上表所列限制与待完成工作。** 下文 390 项整组和 71 项增量属于此前稳定源码的验证，不能视为本轮所有新变更的覆盖；当前接线与准备状态以本文顶部为准，历史记录保留作为问题和修复依据。
- 初次实施阶段使用合成媒体、脚本回答和离线 HTTP mock；后续主会话增加真实历史记录重分析，并经用户授权协调两次独立真实渲染。各阶段证据与当前结果见文末。
- 保持用户的 P0 / P1 / P2 和原编号。P0 已确认影响主要是实验阻塞与有效评测缺失，相关原始回答通常仍被保存。
- 本文记录问题和修复建议，不替代既有实验版本。涉及行为、评分、证据或预算的变更，实施时记录新版本及旧运行适用边界。
- 勾选只表示所述工程关闭条件与验证范围已达到；真实效果、授权外工作及审阅限制随条目保留。本进程没有删除媒体、重写历史或提交/推送。另一项已授权数据整理变更了媒体与划分，不能归为本进程的修复。

## 跟踪总表

| 状态 | 编号 | 优先级 | 问题 | 基线核对结论（修复见文末） |
|---|---|---|---|---|
| [x] | LHA-001 | P0 | 无效 Critic 报告造成恢复死路 | 确认，现行协议和常规恢复入口下无有效出口 |
| [x] | LHA-002 | P0 | 禁止建议正则误拒、漏检，且污染独立终评 | 探针复现，首批四份终评中一次误拒有记录 |
| [x] | LHA-003 | P0 | validate_focus 误拒中性问题 | 探针复现 |
| [ ] | LHA-004 | P0 | 默认预算无上限，非交付终态阻塞 batch | 确认，已有可选轮次/生成上限，当前实验未启用 |
| [x] | LHA-005 | P0 | 判官截断缺少可恢复处理路径 | 确认，约一万 reasoning tokens 是单次预检证据 |
| [x] | LHA-006 | P1 | 笔记无界增长，多模态上下文预算不完整 | 确认，非 JSON 自动记笔记有前缀和语言例外 |
| [x] | LHA-007 | P1 | Planner / Critic / 判官 JSON 解析不一致 | 确认 |
| [x] | LHA-008 | P1 | 知识只保留最新读取结果，引入记忆策略混杂 | 机制确认，实际影响幅度待测量 |
| [x] | LHA-009 | P1 | 证据帧连续性缺少解码层保证 | 确认保证不足，尚未证明当前样本实际抽错帧 |
| [x] | LHA-010 | P1 | 候选级评审缓存静默忽略新问题 | 离线复现 |
| [x] | LHA-011 | P1 | 动作失败留下部分状态修改 | 两种路径均离线复现 |
| [ ] | LHA-012 | P1 | 链式 v2v 缺少累积退化的专门分析 | 确认设计缺口，链式输入可选，已有一般保真评分 |
| [x] | LHA-013 | P2 | 历史实现耦合，核心模块风格密集 | 确认，同包有 22 个 rsi_*.py |
| [x] | LHA-014 | P2 | profile 将过宽源码/文档集合绑定为协议身份 | 确认，并非所有 docs 文档都被哈希 |
| [x] | LHA-015 | P2 | 调度迁移依赖进程启发式和强制信号 | 确认风险，现有多重检查仍须如实保留 |
| [ ] | LHA-016 | P2 | 媒体、残留与文档状态卫生 | 确认，当前媒体计数校正，版权状态待核实 |

## P0：实验阻塞与有效评测缺失

### LHA-001 — 无效 Critic 报告使任务进入无出口状态

**证据。** src/planner_harness/delivery_review.py:71–83 在候选已有评审请求、却没有有效报告时写入 needs_reconciliation；src/planner_harness/recovery.py:26–29 拒绝替换已 collected 的结果；src/planner_harness/model_call.py:21–30 拒绝重开已有原始回答的调用。scripts/test_creative_delivery_review.py:129–170 明确覆盖并维持该行为。

**机制与范围。** 普通 Critic 无效回答可以先被作为失败收集，之后交付要求有效报告，又禁止替换同候选评审。专门交付评审失败则在 execution.py:226–234 直接暂停；该分支不一定已有 collected 标记，但重放同一无效原始回答仍不能产生有效报告。串行 topic gate 把局部失败扩大为整批阻塞。“永久”指当前协议和正常恢复入口没有出口，不能靠再次 resume 自愈。

**拟修方向。** 区分传输中断、输出截断、结构无效、证据校验失败和确有失败结论；保留原始请求、回答及失败记录，增加有界恢复或明确失败结算路径。新的评审尝试使用独立身份、关联原尝试并计费，不覆盖旧答案，也不反复评分直到满意。与 LHA-004 / 005 一起打通 batch 对失败的处理。

**关闭条件。** 注入无效普通评审和无效交付评审，两者均可按策略恢复或正式结算失败；正常恢复不重复生成视频；旧回答保持不变；后续 topic 能继续；旧测试改为验证新出口。

### LHA-002 — 禁止建议正则误拒描述、漏检建议，并影响独立终评

**证据。** src/critic_harness/one_shot.py:183–195；独立终评在 src/evaluation/creative.py:150–165 复用同一校验器。本轮以真实有效报告为基底，仅替换 reason，得到：

| 输入句子 | 当前结果 | 问题 |
|---|---|---|
| The request says the tabletop rim should glow. | 拒绝 | 描述用户要求 |
| The player appears to try to block the shot. | 拒绝 | 描述画面动作 |
| Players select the ball. | 拒绝 | 描述动作 |
| Using v1 as the base would likely preserve the faces better. | 接受 | 提议输入选择 |
| Rendering once more from the original clip is likely to fix the geometry. | 接受 | 提议再次生成 |

**运行证据。** 本地 out/creative_benchmark_live/20261101/first-pass/final-judge 中保存四份终评，其中 2c958b7b75461881254aafb0ae49c0253393908a8d5ea94c1fcc8ac090c8a09c 有 invalid-report.json，错误为禁止建议。实际触发句为 “The request does not state whether the basketball hoop should be removed, so its retention is treated as an ambiguity rather than a clear violation.” 该份后来经过专项独立复核，已有补充验证的 judgment.json，保留原拒绝记录且未增加模型调用。因此一次误拒已证实，但该份目前已有补回结果；专项例外未修正通用规则。

**拟修方向。** 拆分结构/证据有效性与在线反馈行为边界。独立终评不向 Planner 回流，移除无必要的在线建议门控；在线 Critic 对真实动作建议单独处理，避免把常见词命中等同于整份评分无效。确定性校验承担可可靠判断的约束，剩余语义风险明确记录。

**关闭条件。** 上述正常描述和历史误拒报告通过应有的结构/证据校验；明确动作建议按在线策略处理；终评正常描述不造成缺失；数值越界、无效证据等真正错误仍被拒绝。通用修复不依赖逐句白名单。

### LHA-003 — validate_focus 误拒中性问题

**证据。** src/critic_harness/one_shot.py:87–98 将 set 与其后 55 字符内的数字 0–4 连在一起判断为评分操纵。探针 “Does the set dressing in the first 2 seconds match the source?” 被拒；把 set dressing 换成 decor 即通过。

**拟修方向。** 将评分操纵规则限定到明确评分对象、赋分语义与指令结构，保留时间、数量、场景陈设等正常表达。与 LHA-002 共用正反例，但保持 focus 与 report 的不同用途。

**关闭条件。** 中性时间/空间问题通过，要求给特定分数或改写评分准则的请求仍被拦截；加入 set、rate、mark 等多义词的最小回归样例。

### LHA-004 — 默认缺少资源上限，batch 只接受成功交付

**证据。** src/planner_harness/runner.py:26,533 支持 max_turns，默认 None；src/planner_harness/continuation.py:23–43 支持 hard_generation_limit，默认 None。src/experiments/creative_benchmark.py:52,71–84 当前 batch 明确使用无轮次/生成上限的 delivery 配置。继续生成的说明要求不构成硬资源限制。未见覆盖 Planner、Critic、生成和终评的统一成本上限。

**终止语义。** src/planner_harness/delivery.py:25–36 已有 budget_exhausted、execution_failed、delivery_blocked 等状态；但 verify_delivery():85–95 只接受 complete + satisfied，creative_benchmark.py:171,206 和 topic gate 依赖该验证。因此问题是实验结算只接受成功交付，而非底层完全没有其它状态。一直 read/observe 的模型同样缺少当前默认的轮次和费用保护。

**拟修方向。** 将“任务已结算”与“成功交付”分开，允许合理停止、预算耗尽和明确失败进入 batch 结果及统计分母。提供可配置的轮次、生成请求数、token/费用及运行时间保护；未知计费保留未知。具体默认数值在实施时依据预检和实验用途确定，安全上限不冒充任务成功条件。

**关闭条件。** 无限 read/observe、连续生成、no_promising_attempt、工具失败、预算耗尽分别有有界且可审计的结果；失败样本保留在 planned/missing/failed 统计中；后续 topic 可继续；成功交付仍要求真实交付证据。

### LHA-005 — 判官截断被固化为不可恢复失败

**证据。** src/evaluation/creative.py:59–82,112–128 返回文本，未在判决路径显式分类 provider 的 finish/stop reason；judge_candidate():157–165 解析失败后记录 semantic_retry: false。model_call.py:29–30 阻止已有回答的重开，恢复调用还会重用已保存文本。creative_benchmark.py:415–418 和 scripts/creative_benchmark_schedule.py:253–268 将终评异常传播为 topic/batch 阻塞。

**容量证据。** 已保存 GLM 预检 out/creative_benchmark_preparation/20261101/provider-capability/contract/call/attempts/07/result.json 记录 completion_tokens=12011，其中 reasoning_tokens=10708。当前适配器已将 GLM max_tokens 提到至少 16384。约一万推理 token 是这次调用的观测，不能推成每次固定消耗或足以保证后续不截断。

**拟修方向。** 持久化并使用结束原因、输出预算与 usage，区分容量截断和完整无效回答。为容量/格式失败制定预先固定、有次数和总费用上限的恢复策略；每次新尝试留痕，最终无法评分时记为明确缺失并允许批次推进。避免依据评分高低选择是否重试。

**关闭条件。** 用 length/max_tokens 结束、半截 JSON、完整但结构无效、正常完整输出四类响应验证分类；重试次数与费用受限；历史尝试可追溯；超限后保留缺失原因并结算 topic。

## P1：实验正确性与解释边界

### LHA-006 — 无界笔记与不完整的多模态预算

**证据。** runner.py:445–448 对 notes 追加或替换，但无长度上限；runner.py:586–591 将非 JSON 普通文本转换为 note。精确边界：以左花括号、左方括号或代码围栏开头的非法输出会进入 response_error；笔记仍受英文校验，并非任何非 JSON 字节都能追加。context.py 保留核心 notes，runner.py:544–547 最终触发 context_limit；该检查只数 system 和 user_text 字符，不计算图像占用。

**拟修方向。** 给工作笔记分配预算并保留完整归档；明确自然语言输出究竟是合法 note 协议还是解析错误，避免异常输出无条件污染工作记忆。按文本与图像共同估算上下文占用，为模型限制留余量，记录实际 usage 校准估算。

**关闭条件。** 连续长文本、长 note 和高图像数量输入能够有界处理；关键任务事实和原始记录可恢复；达到限制后有明确动作/终态，而非仅要求不断增大字符阈值。

### LHA-007 — JSON 代码围栏处理不一致

**证据。** Planner 直接 json.loads(raw)，将围栏前缀解析失败记为 response_error（runner.py:586–600）。Critic（one_shot.py:212–216）与独立终评（evaluation/creative.py:158–162）接受精确的 json 围栏。

**拟修方向。** 共用明确且小范围的输出规范化/JSON 解码入口，统一纯 JSON、围栏和空白的处理，保留原始文本。不要通过猜测或拼接任意散文来改变动作语义。

**关闭条件。** 三类调用对同一合法 envelope 的接受结果一致；空白、CRLF、合法围栏有明确规则；缺失字段、多对象和真正截断的 JSON 仍作为错误处理。

### LHA-008 — 知识效果依赖未显式控制的记笔记与重读策略

**证据。** src/planner_harness/context.py:108–120 把最近操作中除最后一次外的完整结果替换为 event_id/action/history 入口，read_receipts 只保存元数据。原文没有从磁盘丢失，可以经 history 重读，但跨轮次直接可见性迅速消失。

**实验含义。** 已有读取和 exposure 记录；目前缺少对“知识内容保留多久、模型是否摘记、是否反复重读”作为记忆条件的明确控制和分析。知识/经验效果可能同时反映内容质量与模型自身记忆管理，影响幅度仍需实验确认。

**拟修方向。** 在统一预算下保留可追溯的近期知识片段或模型显式固定的关键证据，定义淘汰与重开规则。对 full/none 使用相同记忆机制，记录读取、可见、摘记、重读及后续操作的关系，再用小规模对照评估保留策略的影响。

**关闭条件。** 多次 read 之后关键知识不会无声明地只剩指针；可见内容可从调用输入重建；各组记忆条件可比；报告能区分内容暴露、保留和使用。

### LHA-009 — “连续帧”证据缺少原生解码身份保证

**证据。** src/planner_harness/video.py:14–26,43–49 从 OpenCV 读取元数据并使用 CAP_PROP_POS_FRAMES 定位，按索引/fps 标注时间。当前 src/critic_harness/one_shot.py 使用该 Video 路径。已有 src/critic_harness/evidence.py:14–32 基于 PyAV 顺序解码、验证递增 PTS；其 Evidence 实现未接入当前 one-shot 协议。

**范围。** 这是证据保证不足，尤其涉及变帧率、长 GOP、元数据失真或 seek 偏差；本轮没有证实当前所有样本实际抽帧错误。

**拟修方向。** 复用已有 PTS 解码能力，适配当前抽样数量、窗口和协议身份；以实际解码帧序列和原始 PTS 绑定 evidence。整体观测与局部连续帧的覆盖范围分别记录。

**关闭条件。** 在恒定帧率、变帧率、非零起始 PTS 和长 GOP 样例上，引用帧与实际解码帧一致；dense window 中相邻证据确为相邻解码帧；缓存和版本变更可追溯。

### LHA-010 — 评审缓存忽略新 compare_to / focus / extra_checks

**证据。** src/planner_harness/creative.py:117–145 虽先校验新参数，但在 131–137 行仅按候选 video_id 匹配历史评审。离线探针在已有报告后提交新的 compare_to=source 和新 focus，得到 payload=None、cached=True 及旧 feedback_id。

**拟修方向。** 以完整请求身份决定是否复用。相同请求安全命中；不同问题明确创建受预算约束的补充评审，或清楚返回当前协议不支持。主评分复用与补充比较/检查的边界单独定义，避免通过反复提问挑选满意分数。

**关闭条件。** 相同请求不重复调用；不同 focus、比较目标、补充问题不会被静默标为已完成；返回结果与请求绑定一致；调用和评分来源可追溯。

### LHA-011 — 无效动作可先修改业务状态

**证据。** runner.py:314–317 在具体动作参数校验前写 note/workspace；runner.py:394–419 在验证 stop_reason 前作废交付提案。本轮用离线临时 fixture 复现：
1. 空 targets 的非法 read 报错，但 notes 和 workspace 已改变。
2. ready 交付提案遇到非法 stop_reason，动作报错，但 active_delivery_proposal 已变为 None，提案状态变为 superseded。

**拟修方向。** 先验证完整操作，再提交相关状态变更，明确失败审计与业务状态的边界。涉及外部工具的动作，在发出不可逆请求前完成可预检的校验，保持请求身份与恢复幂等。

**关闭条件。** 两个复现路径报错后业务状态保持一致，仅增加明确失败事件；有效操作正确写入 note/workspace；工具请求不会因回滚/恢复而重复提交。

### LHA-012 — 链式 v2v 的累积变化缺少专门测量

**证据与校准。** src/server_runtime/renderers.py:73,88–104 使用 payload 指定的输入，92–93 行检查迭代输入时间轴。Planner 可选 source 或已生成候选，并非强制每轮输入紧邻上一轮。已有 content_preservation、temporal_consistency 等评分及候选/输入记录，因此“完全没有保真测量”过强。缺少的是以生成谱系深度、父候选和原片为基准的累积退化分析及对照。

**拟修方向。** 从已有输入关系重建 candidate lineage，记录 chain depth、重启原片和分支。分别评估目标编辑完成、原片需保留内容、父候选到子候选的变化；在相同成本和可比设置下比较链式迭代与原片重启。指标需匹配编辑目标，避免把所有变化都当退化。

**关闭条件。** 报告能按谱系深度和输入策略展示保真/时序变化与成本；包含至少一组原片重启对照；区分意图内变化与累积损伤，保留定性证据和测量限制。

## P2：可维护性、运维与仓库卫生

### LHA-013 — 历史路径耦合与高密度代码增加维护负担

**证据。** src/planner_harness 当前有 44 个直接 Python 模块，其中 22 个为 rsi_*.py；runner.py 同时包含 legacy、RSI 和 creative 分支。delivery_review.py、continuation.py 多处用分号串接多个状态变更，降低状态机审阅可读性。当前 creative 路径排除了部分旧机制，但代码和冻结范围仍有耦合。

**拟修方向。** 优先拆分动作验证、状态变更和持久化边界；将历史工作流置于清晰兼容边界，保留历史运行的读取/复现入口。先做不改变实验语义的小步整理，避免与 P0 修复混成大规模重写。

**关闭条件。** 当前入口和依赖路径清晰；核心 creative 状态转换可独立阅读和验证；历史路径有明确归属；必要回归证明行为未被结构或格式调整意外改变。

### LHA-014 — 冻结 profile 对无关变更过于敏感

**证据。** src/planner_harness/creative.py:63–94 哈希六个 src 包下全部 .py/.md，还纳入知识集合及若干脚本/配置。历史 RSI、未使用实现和包内说明文档的变动可能改变 cohort identity。普通 docs 下任意文件并不必然进入哈希集合。

**拟修方向。** 区分用于审计的源码/环境清单与定义可比性的协议身份；协议身份显式覆盖实际执行依赖、提示、评分、证据采样、模型配置及可见知识内容。被模型实际读取的操作手册仍是实质输入，不能一概排除 Markdown。

**关闭条件。** 纯说明性文档或不可达历史代码变更不会触发不必要的协议迁移；实际影响输出/评分的变更必然改变对应身份；旧运行的来源指纹和回放依据保留。

### LHA-015 — 调度迁移通过进程启发式及强制信号回收

**证据。** scripts/creative_benchmark_schedule.py:162–219 检查父进程命令行中的硬编码 /creative-20261101/run_batch.py、停止状态、worker wchan，发送 SIGSTOP，再检查队列与任务/交付记录，最终 SIGKILL。确实存在多重保护，不能描述为“只看 wchan 就杀进程”。

**风险。** 硬编码部署身份和 workers/0 队列路径、未充分绑定 worker 进程身份/创建时间，以及检查与发信号之间的竞态，使其依赖特定部署和人工历史状态。wchan 反映内核等待位置，缺乏应用自身的完整空闲/排空确认。

**拟修方向。** 使用显式 worker 生命周期、停止接单和排空确认；绑定进程身份及启动标识，配置化路径。把历史迁移脚本与正常调度生命周期隔离；退出与恢复都留有可验证回执。

**关闭条件。** 用模拟进程/队列测试覆盖活跃模型或渲染调用、PID 变化、排空失败、已完成任务和重复退出；不误伤进程、不遗失任务；验证本身不向真实实验进程发信号。

### LHA-016 — 媒体、临时残留与当前状态文档需要清理

**数量核对（保存本文之前）。**

| 项目 | 实际观测 |
|---|---|
| .git 磁盘占用 | du -sh 为 730M |
| Git 跟踪媒体路径 | 1393：1248 个 .mp4、132 个 .jpg、13 个 .png，均存在 |
| 媒体范围说明 | 其中 885 个在归档_extract/，其余 508 个；用户提出的 509 与当前全仓口径不同 |
| zyx/films/opuscar98.mp4 | 88,696,195 字节，约 88.7 MB |
| docs Markdown 数量 | 工作树 49 份，Git 跟踪 48 份 |
| 临时/归档残留 | _wtest、_wtest2、_wtest3 存在但未跟踪；_trash/ 跟踪 5 条路径；归档_extract/ 跟踪 887 条路径 |
| 空日志 | 已跟踪 2026-10-26_09-31-33_ivebench.log，0 字节 |

**文档证据。** README.md:20 仍写等待开机；docs/creative-benchmark-three-arm-plan.md:68 保留 batch 已启动与 heartbeat active 的历史描述，其第 7 行已注明暂停并说明下文是历史合同；docs/creative-benchmark-execution.md:3 明确暂停。时间先后部分已有交代，但 README 当前入口仍过时，读者需要跨文档重建状态。“49 份状态互相矛盾”应理解为文档集合中存在状态不一致，不能推成每一份都错。

**来源边界。** 大媒体的来源、许可及再分发用途需要核查；仅凭文件名、体积和 Git 跟踪状态不能确定版权违规。本轮未取得足以作该判断的授权材料。

**拟修方向。** 建立轻量媒体清单，区分实验输入、引用展示、历史产物和可再生输出，核实来源和允许用途；选择适合的外置存储或 Git LFS 策略。清理残留前核对引用和用途，更新当前状态入口并明确历史文档时间。删除媒体、迁移历史和重写 Git 历史分别列出具体方案再执行。

**关闭条件。** 媒体数量与来源台账一致；当前文档直接给出暂停/部署/代码版本的真实状态；必要历史记录仍可定位；清理不破坏实验引用或运行复现。版权/再分发结论只按具体证据填写。

## 关联待修项：前轮审阅中不与上述 16 项重复的发现

以下独立条目保留前轮在同一代码基线下取得的证据，不替代用户编号。实施时纳入对应修复，不扩展为立即重做数据或清理历史。

- [x] **A-01 — 活跃 benchmark 数量与文档不一致。** 活跃 sample_index 为 24 个主样本，all_samples 为 31（24+7），短/长请求各 24，当前 scaffold 为 55 个任务；主素材及原导入来源记录仍为 50+7。明确 active subset 版本、筛选依据和入口文档，保留原导入 provenance，与 LHA-016 一并核对并单独验证实验分母。
- [x] **A-02 — 终评缓存未对齐原始模型回答。** src/experiments/creative_benchmark.py:250–259 检查身份、schema 和证据文件，却未比对 report 与持久化 raw response。前轮离线探针仅把缓存 score 从 3 改为 4，缓存仍接受。参照交付评审已有原文绑定方式，验证合法 schema 的篡改也被检出；补充复核走有出处的独立记录。
- [x] **A-03 — 默认启动入口与新调度实现分离。** scripts/run_creative_benchmark.py:43–46 仍调用旧 experiments.creative_benchmark.run，旧路径在各 arm 完成后评所有候选；新脚本实现五个位置及更早启动终评。明确正式入口、报告位置与时序契约，避免文档采用新流程、默认命令执行旧流程。
- [x] **A-04 — 已有回答恢复未补回 returned 回执。** src/planner_harness/model_call.py:69–86,111–114 中回答已持久化但 returned.json 尚未写入时中断，恢复会返回答案而不重建回执，交付确认依赖该回执。前轮离线注入已复现，额外 Planner 调用可以继续，不属于永久死锁。修复后同一已完成调用可补齐可验证回执，无重复推理。
- [x] **A-05 — 历史导出使用不可移植路径。** scripts/eval/reexport_first_wave.py:32 直接使用旧 manifest 内 Windows 反斜杠路径，在 Linux 下失败。前轮离线测试 183 项中 182 通过，唯一错误为该路径问题。修复路径解析和可移植性并保留历史来源，无需因此重跑真实模型。

## 修复承接

1. 先处理 P0 的失败生命周期与批次结算：LHA-001 / 004 / 005；LHA-002 / 003 是已知触发源，需要同时消除。实现可分小提交，验收覆盖跨模块恢复和继续推进。
2. 再处理状态正确性与评审身份：LHA-011 / 007 / 010，以及 A-02 / A-04。
3. 处理上下文、证据和实验测量：LHA-006 / 008 / 009 / 012，以及 A-01。
4. 主链稳定后推进模块边界、profile、运维和卫生：LHA-013–016，以及 A-03 / A-05；若某项阻碍前述修复，只先解决必要部分。
5. 每项关闭记录包含实际变化、验证结果、协议/历史运行影响和剩余限制。测试通过只证明覆盖场景，不代替真实实验有效性；清单保存完成不表示实现已经修复。


## 历史执行记录（2026-11-02 早期阶段；当前状态以文末为准）

基线仍为 `c431ce6` 的未提交工作树。工程恢复/结算在 creative cohort v2 上实施；另一个已授权工作随后把在线 rubric 更新为 `lha-creative-review-v3-low-high`，独立终评更新为 `lha-low-high-final-v1`，并增加 source-only 解释和事件评审。本进程使用导入的当前协议路由，保留他方方法与数据整理；不把旧 v2 自查当作新方法的真实评分验证。

验证记录入口：`reports/maintenance-20261102/offline-validation-intermediate.{json,log}` 是最终收尾与新协议之前的 21 模块、254 个去重测试，中间只剩同一旧断言的两个 subtest（hard cap 从 null 变为 8），断言已更新。`targeted-validation.{json,log}` 记录后续局部测试及新增 source-plan 交叉失败；该失败已促成下述有出处缺失结算。`ir06-ir07-validation.log` 的 3 项真实 Service/Queue/Engine 与预算/协议回归通过；`shared-plan-failure-validation.log` 的 4 项失败双 topic 与历史描述验证通过。最终统一结果由 `offline-validation.{json,log}` 单独记录，含运行前后源码和测试哈希。

父会话的独立检查由其维护 `reports/maintenance-20261102/independent-review.json`，执行交接时尚在进行；现已完成本轮独立检查，最终状态及范围见该记录。父会话已明确报告：永久授权失败三次重放只产生一次 provider fixture 调用；3/1 轮冲突在零调用时拒绝；当前 creative 协议正确路由、旧 v1/v2 拒绝；未知渲染跨实际 Service/Engine 隔离并允许后任务结算、重放不重渲染；实际 Paratera 适配器在离线 HTTP mock 下识别 reasoning-only length 截断并保留 usage 后选择第二次完整回答。其他源码审阅项不写成父会话已全部独立测试。

| 条目 | 实际变化与自查证据 | 协议/历史影响及剩余限制 |
|---|---|---|
| LHA-001 | `report_call` 按预定策略有界恢复，永久失败保存 terminal；普通评审失败在交付时正式 execution_failed，专门交付评审失败收集后结算。原始调用/回答不覆盖。delivery tests 与失败双 topic 测试覆盖出口。 | 不按评分重试；同候选保持一个主评审请求。既有签名/哈希异常保持 IntegrityError，旧运行需原快照/另行迁移。 |
| LHA-002 | `validate_report` 专管结构/证据；在线 `online_projection` 按字段遮蔽显式动作建议，记录 projection_fields，原文仅在 audit call。终评接受中性描述。覆盖清单五句及历史 should 误拒；缓存与交付比较投影后的原始回答。 | 正则是窄语法反馈政策，语义含混仍依赖提示约束；没有声称完备识别建议。当前新 rubric 保留他方版本。 |
| LHA-003 | focus 的评分操纵匹配增加明确评分对象与赋分语义；set dressing/时间/rate/mark 多义词正例及特定赋分负例通过。 | 中性问句不再因数字/多义词误拒；语义边界仍以描述性提问协议为准。 |
| LHA-004 | 新任务默认 64 轮、8 渲染请求、96 模型提交、400 万 token、6 小时提交保护；可配置保守模型 token 单价与 allowance，未知用量保留估计/未知费用。顶层/资源策略冲突拒绝，显式续期同步记录。`verify_settlement` 保留成功、失败、预算、context 与 execution_unknown，planned 分母涵盖所有 topic。 | 保护在提交边界检查；在途调用可超估计。价格 allowance 覆盖已声明的模型 token 价格，未报价 GPU/其他收费保持未知，不宣称统一精确货币封顶。IR-07 用实际服务/队列/引擎补齐未知渲染隔离，后 topic 可继续。 |
| LHA-005 | 每个报告最多两次、每次 16384 输出 token 预留，记录 finish_reason/usage；length、半 JSON、完整结构错误、完整有效、永久传输失败均有测试。source-only plan 耗尽也生成 hash-bound missing marker，使相应终评全记缺失并归档全部 plan 尝试。 | 选择第一份完整合法回答，失败重放不增调用；身份/哈希错误及合法解释中的实质歧义保持阻断。新分段终评的每个计划/事件/评分分别受同一报告策略约束，实际总体费用需按 usage 汇总。 |
| LHA-006 | notes 限 12000 字符、超限要求替换压缩；普通散文为 response_error，原始回答和成功 note 事件可恢复。Planner 输入保存文字+图像+余量估计；报告另保存多模态提交预算。连续散文/observe、长 note 和高图像数测试覆盖。 | 模型实际 token 量在 transport result 记录；估计不是供应商精确 tokenizer。达到限制明确结算，不靠无止境增大阈值。 |
| LHA-007 | Planner/Critic/judge 共用 `json_output.decode_object`，接受纯对象、空白/CRLF、精确 json/无语言围栏，拒绝散文、多对象、数组和截断。交付确认也用同入口核对真实原文。 | 原始字节保留，既有历史输出不被改写。 |
| LHA-008 | `creative-memory-v1` 为 full/none 共用 18000 字符片段预算、FIFO 淘汰、精确片段重读刷新及淘汰记录；`memory-analysis.json` 从实际保存输入重建可见片段/notes/后续动作。双组机制一致性测试已实现。 | 机制、可见性与测量能力已实现。内容质量、保留策略对实际编辑效果的影响待受控实验，时间相邻只作描述。 |
| LHA-009 | `Video` 复用已有 PyAV metadata 顺序解码并验证 PTS/time_base/ordinal，dense 显式相邻索引；证据绑定原生时间和哈希；conditioning ancestry 同用实际 source.times。CFR/VFR/非零 PTS/长 GOP 合成样例核对时间与像素。 | 新证据身份与旧 OpenCV 采样不混用；局部连续窗口不推成整片连续验证。 |
| LHA-010 | 完整 compare_to/focus/extra_checks 相同才复用并校验原始缓存；不同请求明确返回 unsupported_supplemental_request，表示没有回答。 | 沿用单候选主评分，避免通过追加问题挑分；补充请求未来若开放须另行版本化。 |
| LHA-011 | `operate` 在独立状态副本执行，完整成功才提交；当前 creative 动作独立模块先校验 stop_reason。非法 read 附带 note/workspace、非法 finish 不修改原业务状态。外部 dispatch 在成功事件 checkpoint 之后。 | 失败只留明确事件；本地 durable intent 不等于外部执行，恢复仍以原签名 job 幂等。 |
| LHA-012 | `lineage.analyze` 重建深度、分支、原片重启、源/父相关评审、已知/未知成本；`control_plan` 给出同 prompt/seed/renderer 的 source/parent 双输入签名 job，标 not_submitted。合成谱系含匹配原片重启对照，CLI 和报告已接入。 | **真实对照与累积损伤结果仍待实验，保留未关闭。** 当前交付可执行的测量/对照意图与离线验证，不以 fixture 替代真实画质结论。 |
| LHA-013 | 当前 creative 动作进入 `creative_actions`；runner 留明确 legacy/RSI 兼容边界。delivery/continuation 拆开密集状态语句，报告/资源/JSON/记忆各有小模块。 | 历史模块未大规模删除或重写；旧流回归与当前测试共同验证结构边界。 |
| LHA-014 | 显式 `protocol_sources` 列当前执行依赖，完整 audit inventory 单独保存；可见知识、手册、评分定义、证据策略、模型配置仍进身份。说明 README/不可达 RSI 不触发迁移的测试已实现。 | 他方 low/high 新依赖也已登记，曾有登记先于文件的短暂并发阶段；最终 60 文件基线须随统一回归核对。新增实际执行依赖需更新登记。 |
| LHA-015 | 复用 Engine drain/stop 和 queue.dispatch，新增 owner/PID/start ticks/boot ID 绑定的 lifecycle 请求及回执；禁用旧 SIGSTOP/SIGKILL 自动迁移。测试覆盖活跃任务排空、错误身份、重复请求/核验与已完成任务。 | 退出回执证明 Engine 循环结束和 handler close 返回，不推断 OS 进程退出；旧 worker 缺合作回执时需另行人工迁移。本轮没有给真实进程发信号。 |
| LHA-016 | 本进程交付只读媒体/来源/精确引用清单、状态入口和清理边界；保留 before-concurrent-cleanup 快照。另一项已获用户授权的整理实施 67 项新数据和历史清理，当前 audit 分开列 Git 跟踪1393、现存285（含新36）与移出1144。 | 当前输入/提示哈希及 split 一致性已只读核对；移出媒体的完整恢复/引用验证由该整理及父会话承接。本进程未删除/移动媒体；许可/再分发保持未核实，不作新的版权结论。 |
| A-01 | 初始24+7及55-task分母保留为时间快照。当前已确认另一项用户授权整理替换为67（31 train/6 validation/30 test），fewshot7属train；audit 核对索引/67组哈希。 | 不恢复移出旧项、不把旧数量当当前事实。新 split 与当前代码入口兼容性另做 prepare/verify_batch smoke。 |
| A-02 | 终评缓存回查所选 attempt 原始回答、returned hash、输入/模型/证据 packet；合法 schema 下改分也拒绝。新解释/事件记录的绑定由当前 low/high 路径承接。 | 历史专项描述复核保持原出处；新协议用新身份，不靠旧逐句例外。 |
| A-03 | CLI 和 `experiments.creative_benchmark.run` 都委派当前五位置 early schedule。未知/失败位置保留显式缺失，中间候选不追加独立评分。 | 旧 run/旧全候选评分保持历史源码快照，不以当前入口偷换历史合同。 |
| A-04 | 已保存 response 的两条恢复路径从原 attempt 补齐 returned 回执；无匹配 attempt/回执哈希时为 IntegrityError。 | 不新增推理，legacy usage 缺失保留未知。 |
| A-05 | 历史 card 路径用 PureWindowsPath 解析仓库相对片段并验证不越界；两处读取均修复。 | 原 manifest 字节不改、跨平台导出不调用真实模型；历史所需文件若由另项整理移出，使用其恢复依据。 |

### 交付与剩余边界

- 本进程修改的是实现/配置/必要测试与本清单、当前工程说明；没有提交/推送，没有改全局偏好或 Skill，没有恢复实验。
- 当前 active benchmark/split、已授权清理、low/high rubric 与新增评估模块属于并发工作。README、媒体状态页、audit 与部分测试收到其兼容更新，按最终文件保留；相同文件中的修复贡献与方法贡献不能互相冒领。
- LHA-008/012 的真实科学效果、真实模型容量/费用与运行时表现仍待单独授权的实验；本轮只给工程能力、可追溯记录、合成离线控制和必要自查。
- 主会话已完成本轮独立审阅；部署/旧运行迁移尚未执行，新协议不直接恢复旧 batch。


### 执行进程交接时的验证与历史阻碍（后续复核见末尾）

- `offline-validation.json`：22 模块、269 个唯一测试全部通过，143.63 秒；期间 3 个实现文件和 `test_low_high.py` 有并发变化，记录完整，不能作为同一冻结基线全部通过。
- `post-concurrency-validation.json`：只复测受影响的 4 模块，56 个测试全部通过，71.94 秒；源码与测试起止哈希均一致。未重复无关旧流测试。
- 最后补丁将 Paratera/Sonnet 实际返回模型身份不一致保留为硬 `IntegrityError`；其原始失败与重放不会降格成报告缺失。`provider-identity-validation.log` 覆盖两适配器离线 HTTP mock 与三次重放，1 项通过。
- `final-incremental-validation.json` 的 7 项最终增量复测中，6 项通过；IR-07 在启动 Planner 前被并发经验完整性校验拦截。`ir07-final-validation.log` 明确失败为 `Curated content missing or changed since review`，没有开始生成或隔离路径。IR-07 本身此前的本地与父会话真实 Service/Queue/Engine 回归已经通过。
- `current-integrity-status.json` 保存 14 份 curated entry 与 catalog 声明 SHA 不一致的只读证据。父会话进一步核对为实质语义修订（例如 Revision 4→5），明确要求保留现场，**本进程没有更新审核哈希或采纳这些新内容**。交接时的工作树入口检查尚未通过；对应经验维护随后完成同步，主会话入口复核结果见末尾。
- 当前新数据 `prepare + verify_batch` smoke（7 条 training fewshot、14 份 arm spec、64/8 保护）通过；记录版本为 `lha-benchmark-20261102-v5`，对应核查时间见 JSON。它发生在上述经验完整性阻碍出现之前；同步后的入口验证另见 post-curation-entry-validation.json。
- 原始 CRLF 实现文件保持原格式；对本次范围运行 `git -c core.whitespace=trailing-space,space-before-tab,cr-at-eol diff --check` 通过。没有提交/推送、真实推理/GPU、线上恢复或真实进程信号。

执行实现与自查在此阶段交回主会话。随后主会话完成独立审阅，外部经验维护完成审核同步，入口复核通过；详见末尾补记。真实实验与剩余开放项仍未完成。

用户确认：14 份经验属于另一项已授权维护，由对方完成审核同步。同步后的入口复测已由主会话完成，执行进程与主会话均未改写经验正文或审核 catalog。

## 早期独立检查补记 — 2026-11-02（历史）

主会话审阅实际调用链，并另行完成六组离线探针，覆盖永久失败重放、预算冲突、当前/旧协议路由、GLM reasoning-only 截断、未知渲染的真实 Service/Queue/Engine 隔离，以及在线建议的 context/history/state 可见性。审阅推动的 IR-01–09 与各自证据见 reports/maintenance-20261102/independent-review.json；其中明确区分源码核对、执行进程测试与主会话独立探针。

用户确认的经验维护随后完成审核同步。主会话验证 full/none 知识入口可加载，并重跑最后七项入口/增量检查：7/7 通过，无跳过，源码与实验 profile 起止一致（2fea33c1ee46a170b7fe444b402bbf930e9e6aea350e8feb84ca997dba3a4a86）。结果见 reports/maintenance-20261102/post-curation-entry-validation.{json,log}。此前 6/7 和知识完整性拒绝记录保留为历史过程，不再代表当前启动状态。本会话未改写经验正文或审核 catalog。

上一轮按较窄工程条件记为 19 项关闭。下方按原始问题范围复核后，LHA-004 与 LHA-013 也重新打开；上述 19 项数字保留为历史判断，不再代表当前完成度。记忆机制、累计退化和最终画质的科学效果待真实实验。未提交、部署或恢复线上实验。


## 原始 16 项最终范围复核 — 2026-11-02

本轮对照完整审阅意见后，按原始要求收紧为 **13 项工程关闭、3 项部分完成**。第 4 项此前按“提交保护与超时隔离”关闭；实际单次输出与费用硬上限尚未建立，现重新保留为部分完成。工程关闭表示实现、关键失败路径和已覆盖离线行为通过审阅；条件与真实实验边界随条目保留。附录 5 项不计入原始 16 项的完成数；这些工程数量不代表第 4 节科研问题已经解决。

| 原编号 | 当前判定 | 已确认的实际结果与适用条件 |
|---|---|---|
| 1 | 已修复 | 无效报告按固定次数恢复，耗尽后明确失败结算；原回答保留，后续 topic 可继续。身份或证据被改动仍须核对。 |
| 2 | 已修复 | 终评移除在线建议词门控；在线显式建议按字段投影，评分与审计原文保留。指定误拒/漏检样例覆盖，语义启发式边界明确。 |
| 3 | 已修复 | 中性 set dressing/时间/rate/mark 问句通过，明确赋分指令仍拦截。 |
| 4 | **部分完成（提交保护与超时隔离已修复）** | Planner、Critic、终评/解释、渲染、计算及未来 standalone 入口接入统一账本；full/none 独立等额分配，整题先验证容量。轮次、生成次数和新请求准入有界；合理无交付停止可结算。token/金额按预留额度准入，真实超支如实记录并阻止后续提交。CodexVLM.predict_text 的 max_new_tokens 仍未传入执行命令；单次输出硬上限与实际供应商账单硬上限尚未验证。超时有界返回且原执行保持归属、不重提，并不代表外部计费立即停止。新 live 仍需真实预算与报价。 |
| 5 | 已修复 | 每个报告阶段有界恢复，截断/格式/永久失败分别记录，耗尽为明确缺失；解释计划失败原因保留到汇总。总调用受第 4 项账本约束。 |
| 6 | 已修复 | 普通非 JSON 输出不自动写笔记；笔记有限额，输入预算包含图像估计，实际 usage 单独留存。 |
| 7 | 已修复 | Planner/Critic/终评共享 JSON envelope 解码，合法围栏可用，截断或多对象拒绝。 |
| 8 | 已修复（机制） | full/none 共用知识片段预算、淘汰/重读策略与实际输入可见性记录；记忆策略对真实任务质量的影响仍需实验。 |
| 9 | 已修复 | PyAV 顺序解码，帧以 ordinal/PTS/time_base/哈希绑定；连续证据来自相邻解码帧，范围明确。 |
| 10 | 已修复（显式拒绝方案） | 同一完整请求才复用；不同 focus/compare_to/checks/events 明确返回不支持补充请求，用户问题不会被静默忽略。 |
| 11 | 已修复 | 业务状态在副本上操作，动作通过后才提交；非法动作/finish 不提前改笔记、工作区或交付提案。 |
| 12 | **部分完成** | 测量与 cohort CLI 已实现；12 次历史运行的 36 个候选、14 条链式边及所有源/输出已验证。历史原片重启匹配对照为 0。fewshot_006（现 train/039）两次全新同提示、seed 44、同参数渲染已经完成；主会话复算两份本地视频 SHA-256，与回执一致。当前新增 1 对链式/原片重启控制，独立质量评测仍暂停，尚无新成对质量结论。历史定性变化不当作因果退化结论。 |
| 13 | 已修复 | 22 个 RSI 实现迁入 compat/rsi；历史动作、运行钩子与旧账本等进入 compat/legacy。旧导入路径是同模块对象的薄兼容入口，当前 creative 明确分派；实际迁移实现进入历史审计哈希。 |
| 14 | 已修复 | 当前 66 份实际协议依赖显式登记；可见手册/知识继续绑定，普通说明和不可达历史代码留在独立审计清单。 |
| 15 | 已修复 | wchan 启发式与 SIGSTOP/SIGKILL 自动迁移禁用，改为身份绑定的合作排空/回执；未知执行保留原进程所有权。未用本轮修复控制真实运行进程。 |
| 16 | **部分完成** | 8 个根目录残留文件已可逆归档；全部 1175 项移出媒体可由 Git 对象恢复，5128 个对象/所有 refs/HEAD 保留，fsck 通过。当前状态文档已区分正在运行的冻结 Direct、暂停的判官和未部署的新实现；启动检查及两个失效媒体链接已修复。仍有两份历史示例卡路径迁移后签名不一致、历史媒体约 720.85 MiB 及来源许可未知项。未改历史卡、重写 Git 或作无依据的许可判断。 |

### 最终验证与真实执行边界

- 主会话 `final-stable-validation.json/.log`：390 个唯一测试全过，0 失败/错误/跳过，源码/测试/可见材料起止一致，profile 为 `8fe9f49b48a384b16aee324e26822cf34a11ddb7fe7c68a9e75d10584dbdeae2`。
- 最后仅修正解释计划缺失原因、RSI replay 实际源码哈希及已知未提交分类。主会话 `root-final-incremental.json/.log`：71 项受影响测试全过，起止稳定；精确六份实现/测试变化已记录，最终 profile 为 `52732a6aa7c574b90422eebfe04d11a49ee4c0bb53e0160c57d029a86630db4a`。两轮有重叠，不相加当作唯一测试数。
- `root-budget-probes.json`：主会话独立验证超时原执行只运行一次、锁/未知费用保留、晚到结果可复用，以及 full 用尽配额后 none 仍可执行。
- `final-local-preflight/local-preflight.json`：当前 15 份经验、56 项资源完整性与 full/none 隔离检查通过，none curated entries 为 0。没有修改 curated 正文或审核 catalog。
- `historical-lineage/summary.json`、`lineage-followup-validation.json`、`git-object-integrity.json` 与 `current-hygiene/media-inventory.json` 分别记录历史实证重分析、8 项谱系软件验证、Git 完整性和媒体恢复证据。
- `example-card-integrity.json`：041_short/041_long 仅 source_video 被另一数据维护迁移而保留旧 card_sha256；当前 validate_card 失败。保留真实卡原样，单元契约测试明确使用 synthetic 冻结卡；未把测试通过当成真实示例卡已修复。
- 已与 Bernini 执行拥有者协调完成两次新谱系对照，随后恢复该卡的 Direct 分片；没有新租/延租、重发未知请求或启动判官。`out/lineage_control/20261102/coordination.json` 与 `local-verification.json` 已记录两次成功、seed 44、各 113 帧 720×400/30fps，合计渲染调用约 1898.82 秒。主会话复算本地两视频哈希，与回执一致；实际金额未知，独立质量评价仍暂停，第 12 项继续开放。
- 本地修复未提交、推送或部署。现有 75 题长/短 Direct 使用独立冻结运行版本，不能追认已经采用新统一预算。实际费用未知时如实保留，实际画质和记忆策略结论仍按其证据范围报告。
