# Benchmark 统一实验入口

主实验按 [全量四组＋统一终评](experiment-campaign.md) 的一键入口执行；独立 Critic 为主实验，自评为追加消融。底层使用 scripts/run_creative_benchmark.py，按当前统一清单选择 split、short/long 和 method。prepare 冻结所选任务与条件，保留原始提示词。使用新的输出目录；历史批次保留原记录而不自动接续。

```bash
python scripts/run_creative_benchmark.py prepare --output /path/new-batch \
  --split train --prompt-form short long
```

这里只准备任务，不调用模型。真实执行仍沿既有实验授权与环境要求。同一 prompt-form 下各方法共用原指令。统一结果目录按样本、长短任务、方法和种子记录视频。生成入口不自动启动独立终评。

## 在线取证与独立终评

有／无知识 Planner Loop 共用 [连续事件操作指南](../knowledge/creative-loop/OBSERVE_EVENTS.md)，经验访问范围由冻结 manifest 区分。当前在线协议为 `lha-qualitative-review-v1`：根据实际画面、任务与关注问题取证，返回定性诊断。每次成功生成后自动进入配置的评审流程；`--review-mode critic/planner` 切换独立 Critic 或 Planner 自评。重点意见在 generate.review_focus 提供，交付确认复用报告。[PE Loop](pe-loop.md) 固定使用独立 Critic，并复用其反馈和取证结果改写下一轮提示词。

独立终评使用 [Low→High 协议](low-high-evaluation-v2.md)的原始提示词、源视频和生成视频，以及独立固定的连续片段与概览，各方法共用，在线关注区间不传入终评。新手册、知识快照或协议使用新的输出目录；历史批次保留原运行版本。模型调用和 GPU 执行仍依当前授权状态开展。具体启动与恢复状态见 [current-status.md](current-status.md)。

真实模型/渲染使用统一预算账本。服务的 `budget` 需要明确 live 模式与独立方法范围；默认使用 `count_limits_only` 保留未知金额，显式金额保护需提供费用报价。在线任务按独立 N 次生成与最多 2.5 小时执行，调用和 token 仅计量；维护与独立终评分别配置账本，见 [accounting.py](../src/planner_harness/accounting.py)；示例配置中的模型名与资源数量本身不构成费用授权。

独立终评按 track／prompt_form 分流长短专项，同时计算五维、逐项语义、美学、CLIP/DINO 与全帧光流；编码器精确版本已固定，重复候选复用计算。当前四组默认实验追加交换顺序的匿名盲评，汇总长／短／全部的逐指标均值、配对统计和有效题数。PE Loop 保存首轮、末轮和选中结果；单轮对照直接使用首轮。benchmark 与已有视频保持原样，逐题意图审批已退出评价流程。运行前提供 compute:features 与 compute:temporal 的预算配置和依赖；缺项明确记录 null 与原因。

## 统一结果目录的独立评分

```bash
python scripts/benchmark_results.py prepare-evaluation --root /path/results --evaluation-id eval-v2
python scripts/benchmark_results.py score-evaluation --root /path/results \
  --execute --budget-config /path/live-budget.json
```

第一步只冻结新的评价身份，不调用模型；第二步在授权运行时计算五维、专项、美学、特征和光流，并更新统一页面。同视频同任务跨方法复用评分，两位判官分别保留。旧分数不导入新会话，缺项列状态与有效数。单独的盲评命令、原三组的首轮／最终对照及通用长短分组汇总见 [当前指标手册](low-high-evaluation-v2.md)。

## 当前默认矩阵与资源

当前主实验四组 `direct pe-loop none full` 均覆盖全量 67 条：PE 最多 4 次，Planner 最多 4 次。40／27 仅作为 RSI 角色；无经验组先执行前 40 条并维护，再继续后 27 条只读执行，随后全量有经验组读取固定累计经验。累计维护已包含在无经验主实验中。campaign 显式冻结 `training_maintenance`，只有 zero 开启；底层全量只读批次使用 `--no-maintenance`。细分批次及次数见 [全量运行安排](experiment-campaign.md)。

运行设备写在 host 配置的 `devices`（物理编号/UUID列表或 `auto`），也可传 `--devices auto`。宿主 CUDA_VISIBLE_DEVICES 的空值和 -1 会拒绝派发。每卡一个常驻 renderer，不凭猜测超配显存；GPU型号、设备和并发仅记运行元数据。单机动态队列须放本地磁盘。跨机复用同一冻结 plan，以不重叠 `--shard-rank/--shard-count` 分片和各自主机本地队列运行只读任务；`local_results_root` 可指定本地注册目录。训练任务后维护的顺序流保持在同一主机。使用 `benchmark_results.py export-shard --root <local-results> --run <batch> --output <portable>`，再用现有 `import --manifest <portable>/manifest.json` 合并到统一结果入口，保留缺失的 planned 位置。无需新的网络调度服务。

达到生成数上限后仍可读取、观察和交付。PE Loop 与 Best-of-N 复用定性候选选择接口，比较可见画面与诊断并记录理由；时间耗尽时保留最近完成的选择，尚无选择则保留首个完成候选并标明原因。PE 每轮保存增强、生成、评审与选择阶段，失败恢复复用已完成阶段。selection 记录 N、完成与评审覆盖；实际请求及费用见预算账本。历史 Direct 保留原计时和硬件信息，缺失保持未知。

完整单题训练 smoke 沿 prepare_creative_smoke → run_server_pipeline init/submit/run --once → close_creative_smoke。最后的 close 会实际运行独立训练维护；只有维护状态 activated/no_increment 才通过，失败不改变在线结果。三卡独立 smoke 是三个私有训练流，不声称彼此按序学习。

独立 GLM/Sonnet 终评使用 live_meter_only，不要求调用、token或费用额度。GLM不传 max_tokens；Sonnet Native Messages 的必填容量使用官方模型最大128000，保持 adaptive/high。实际 usage、超时未知、原回答和有限故障恢复都留回执。若评分CLI提供 --budget-config，该配置只给 features/temporal 的 compute 调用，模型调用不受其额度准入。终评与在线 N/2.5 小时保持独立。
