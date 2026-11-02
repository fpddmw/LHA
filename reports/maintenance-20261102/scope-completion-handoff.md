# 原始范围 004 / 013 实施交接 — 2026-11-02

执行进程：GPT-6.1-sol / xhigh，直接实施与自查，未派生 agent。父会话负责 LHA-012/016、主清单与独立验收。本文件与 `scope-code-inventory.json` 记录本次贡献，不能把整个共享工作树 diff 归于本进程。未提交/推送、未部署、未恢复实验、未调用真实 API/GPU、未停止真实进程、未删媒体、未改经验/审核 catalog。

当前 active Critic 为 `lha-creative-review-v4-events`；当前 benchmark 的 001–075、train40、重命名后的 benchmark 入口与数据整理属于另一项已授权工作。历史 v2/v3、67题与旧 fewshot 名称不代表当前运行身份。

## 逐项状态

| 原项 | 实际交付 | 当前验证与边界 |
|---|---|---|
| LHA-004 | `lha-unified-budget-v1`：统一 batch/topic/lane 账本，模型/渲染/计算预留、提交、用量结算、未知费用、越额与恢复证据；当前真实入口要求用户提供 live 政策/报价。原每臂轮次、96模型调用/8生成的本地保护继续存在。 | 软件实现与离线自查已完成；父会话独立验收进行中。它按显式报价提供提交前额度保护和有界监督隔离。供应商实际扣费硬上限、真实超时和成本表现尚待获授权环境验证。没有实际用户额度或真实报价。 |
| LHA-013 | 22 个 RSI 实现进入 `planner_harness.compat.rsi`；experience/ledger/task_criteria 与历史 runner 动作、上下文/配置/调用钩子进入 `compat.legacy`。根旧模块为同模块对象的薄 alias；共享上下文留在 context，当前 creative 动作保持独立。 | 旧 Planner/continuous/RSI 和真实旧 import/monkeypatch 路径离线回归通过。历史目录与文档资产保留；代码变化后的历史 live 状态仍需冻结旧 checkout 或显式迁移，不能直接混用新协议。 |

## 预算范围与身份

实际接线入口如下：

- `model_call.call_text` 覆盖当前 Planner、在线 Critic 的事件选择/观察/最终报告、交付审查、source-only 解释计划、独立 final/event/pairwise；每个实际 transport/report attempt 独立入账，成功重放读取原回执，不重复扣计。模型 clone 每次请求先清空旧 usage/provider metadata。
- Service 的 Direct/full/none 渲染经同一 `invoke`，请求签名包含 accounting scope。PersistentRenderer 构造与调用在预留后的执行线程中进行。
- temporal/feature compute 包装接入账本；feature 的真实预训练推理要求 live budget，离线 temporal 可以未定价。
- `run_creative_benchmark` / schedule / `run_creative_judge` / `run_low_high_eval` 的真实操作要求预算并走监督子进程；prepare、请求导出、软件 fixture 不需要真实报价。
- 本地 `run_bernini_benchmark.py` 升为 v4，覆盖独立 75-source runner 的 render 与官方 PE SDK create。隐藏 SDK retry 关闭；读取 max_completion_tokens / max_output_tokens / max_tokens 的明确输出上限。旧服务器上已复制的冻结脚本未修改、未同步、未部署；旧运行不据此追认统一保护。

真实调用发生前政策必须明确：version、live mode、币种、batch/topic 的 model_calls/render_requests/compute_requests/tokens/wall_seconds/amount、每次调用期限，以及 direct/full/none/independent 各 lane 同名资源分配。金额为十进制字符串。每个实际目标报价包含同币种、request 单位、max_amount、source、quoted_at；可附输入/输出每百万 token 价、每秒价或明确固定收费。程序不推断价格、汇率、额度、报价真实性或账单取消结果。用户需按其实际合同/环境填写；本轮没有生成一份可误用的真实消费配置。

full 与 none 分配相等，且分别容纳原 96/8 额度。topic 聚合至少覆盖所有 lane；当前 cohort 还验证五位置、两 judge、source plan 与合法事件分段的最大报告阶段调用容量。按预留报价检验声明 lane 资金是否支持其调用/渲染/计算数量。输入 token/图像 token 是估计，实际 usage 与实际越额另记。共享资金保护不等同于两组共享同一份96/8额度。

cohort 采用持久的串行 topic admission：开始首臂前必须还有整题容量；上一题未归档关闭时拒绝另一题并发入场。题内 lane 独立计数/资金/时间，后运行 none 不会消耗 full 的额度。归档后释放未用 admission 容量；实际未知操作继续保留自己的预留。不同题/入口若要并行使用同一 ledger，须另行设计明确的 admission 合同，当前不支持偷偷并发放行。

账本 `policy.json` 不可变，scope 绑定政策 SHA；ledger 记录 hash-chain reserve/start/timeout/settle/admit/close 转换并核对投影余额、时钟和 breach。completion 另有原字节哈希。账本摘要将未定价或未结费用保留为 unknown；quoted reservation 不记成供应商已扣款。实际超出 quote 最大边界或已声明资金/token 额度留下 breach，保留超出实耗，不截断，再次提交被拒绝。`invoice_ceiling_verified` 始终为 false。

## 超时、隔离与恢复

统一期限在真正提交前再次核对 batch/topic/lane 余量，已过期零调用。预提交异常留下 definitely_not_submitted 分类并释放 execution lease；同 key 双线程争用在 lease 后重新读取 ledger，最多发出一次原请求。scope marker 采用专属锁，避免同目录 fixed temp 文件竞争。

原执行使用保留所有权的线程。到期时调用方返回 `execution_unknown`，原线程、execution lease、金额预留与 renderer/GPU 锁继续保留；不发 kill，不声称设备已释放。晚到原结果写 completion 并结算；重放不再调用。未知原结果保持原任务不可自动重提，known budget refusal 与未知结果分开记录。`reopen_call` 不接受对未知原调用的盲目新提交。

ResidentWorker 与 CLI supervisor 使用独立进程保存原执行；close 只发合作 drain 与有界等待，超时写 retained/resource_released=false，不调用 Pool.join 或终止进程。在途 GPU worker 隔离后不接新命令。`accounting_worker` 的 started 标记与 commands 分目录，真实空闲轮询测试确认不消费自身标记。

Scoring/Engine 的业务回调在预算期限后结束；其 executor shutdown 不再无限等待同一个原生外部调用。Service.close 遇 owned call 写 resources-retained，不清理仍占用的 renderer。Codex 在统一 scope 下由外层监督期限管理，关闭 subprocess.run 自带的 kill-on-timeout；连接中断保留未知结果，避免重提未知请求。直接使用未绑定的历史兼容 API 保留其旧语义，不能据此宣称所有历史脚本已升级。

`accounting.reconcile` 绑定原操作、理由与证据文件哈希，可读取原 durable completion 或记录明确的未提交证据；不自动调用外部服务。原账本/attempt/unknown 审计材料保留。未知 provider 账单或未结束 GPU 的释放仍需对应真实回执；手工移走标记不构成恢复依据。

## 包边界与兼容

`legacy-move-map.json` 保存25份移动前 SHA 与实际实现目的地；根 shim 不复制实现，并维持旧模块对象身份，旧 import 与 monkeypatch 落到同一处。`HARNESS_ROOT` 把 OPERATIONS.md/RSI.md 和 critic 资源路径保持在原位置。runner 新增明确 dispatch 边界，旧操作/提交、旧 RSI 上下文与 hook 已提取，事件 observe 的并发 v4 工作保留。

广义 runtime/audit inventory 递归包括 compat；当前 creative 的显式 protocol inventory 加入 accounting/supervisor/worker/standalone 依赖，排除不可达 compat 实现与旧 RSI 手册。测试确认预算实现变化改变当前身份，旧兼容文档变化只改变 audit。66份显式登记文件均存在。旧 run 的冻结源码哈希会变化；旧运行材料不重写，运行迁移仍需独立处理。

## 自查记录

全部命令使用 `out/creative_loop_refactor/venv/bin/python -B`，纯 fixture，无真实 API/GPU。`scripts/validate_resource_legacy.py` 按真实文件/类/方法去重并保存起止源码、手册与测试 SHA。

| 记录 | 结果 | 对应范围 |
|---|---|---|
| resource-legacy-first-validation.log | 最初154（含重复导入）中152过/2错 | 两个旧 PE mock 没有新显式 offline 标记；失败原始证据保留。 |
| resource-legacy-validation.json/.log | 143个唯一测试全过，23.78秒，起止稳定 | 新预算/边界、standalone Bernini、旧 Planner/continuous、四组 RSI。 |
| resource-active-validation.json/.log | 89个唯一测试86过/3错，106.48秒，起止稳定 | current creative/delivery/batch/low-high/worker。两错为新增 scope marker 并发写，已加锁；一错为真实历史041卡 frozen hash，与预算无关。 |
| resource-final-targeted.json/.log | 39个唯一测试全过，44.36秒，起止稳定 | scope并发、Codex scoped timeout mock、预算/边界、batch与schedule。 |
| resource-last-incremental.json/.log | 33个唯一测试全过，5.73秒，起止稳定 | 真实 Service/Queue/Engine native阻塞保留锁、新预算/边界、临时 synthetic冻结卡 worker契约。 |

上述测试有重叠，不能将数量相加当作唯一覆盖率；前轮269/旧56项也不代表本轮最终基线。最终去重的统一快照由父会话审阅记录承接。

真实041_short/041_long两份示例冻结卡的路径迁移与旧hash矛盾，由父会话另存 `example-card-integrity.json` 并纳入 LHA-016；本进程未更新真实卡、未放宽验证。测试只使用临时 synthetic card/media。父会话还完成动态 catalog preflight 与两个旧媒体链接迁移，真实本地 preflight 已通过；该并发贡献与本进程的 synthetic provider preflight 修正分开记录。

## 最后合流与独立验收

父会话在本进程上一稳定点独立完成 `final-stable-validation.json/.log`：390个唯一测试全过、0失败/错误/跳过，180.70秒，源码/测试/模型可见文件起止一致，experiment profile 均为 `8fe9f49b48a384b16aee324e26822cf34a11ddb7fe7c68a9e75d10584dbdeae2`。本进程在该整轮期间没有改源码。父会话另有2组预算独立探针，见其维护的 `root-budget-probes.json`；此处只是引用父会话报告，不宣称本进程重新运行。

整轮结束后按父会话授权，只补两处生产改动：source-plan missing 汇总沿用 plan.reason，保留 execution_unknown/budget_exhausted 区分；compat RSI replay 的 harness SHA 递归绑定实际 compat 实现。新增对应两项测试，`scope-final-incremental.json/.log` 50个唯一测试全部通过、0跳过，6.81秒，起止稳定。最后增量的身份以本交接随附代码清单/父会话复核为准；390项基线的 profile 保留其原始版本，不能偷换成补丁后的全量回归结果。

随后父会话明确追加一处最小分类修正，已完成：`SubmissionRefused` 继承原 `ResourceExhausted`，明确 `outcome_unknown=False`、`retryable=False`。invoke 锁前/锁后识别原 `not_submitted` 记录，保持原账本零调用/零扣计；Service 检查 render-started 的本地意图与原账本，不把已知未提交转成未知渲染。模型路径直接传播该已知拒绝，不进入传输重试或 report recovery。

`scope-refusal-incremental.json/.log`：27项预算测试全过，0错误/失败/跳过，5.86秒，源码/测试起止稳定；新增3项分别覆盖相同key三次重放、真实call_text三次重放、真实Service三次重放，外部模型/渲染调用均0，扣计token/金额均0；另覆盖锁后旧record路径。没有新增恢复政策或自动重提交。

最终 experiment profile 为 `52732a6aa7c574b90422eebfe04d11a49ee4c0bb53e0160c57d029a86630db4a`；66文件 protocol inventory SHA 为 `af6818f23866a62e268bc1696bda6dcce6c73b2dda59fa053228cfa61fb1d3e5`。精确最终文件 SHA 见 scope-code-inventory.json。390项整轮与后续50/27项增量各自保留实际基线，不把前轮全绿改写为补丁后重跑全量。实现与自查至此交回父会话独立审阅。

主清单与 independent-review.json 由父会话维护。请父会话独立检查本次 diff、live gate、争用/过期/timeout所有权和lane公平性。真实供应商报价/额度仍由用户配置，真实在途调用/冻结服务器不热迁移。未开展真实画质/成本结论测量。
