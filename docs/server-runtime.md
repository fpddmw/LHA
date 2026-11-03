# 服务、并发与恢复

服务在 Planner Harness 外调度持久任务，不重写 Planner 的决策循环。当前使用 API-only 模型调用；实际 API 可用性和双卡测试状态见 [当前状态](current-status.md)。

## 调度结构

每个任务顺序经历 Planner → 生成 → Critic／自评 → Planner。不同任务可以交错：一个任务等待 Critic 时，GPU 可处理另一任务。每张 GPU 的服务串行渲染、复用常驻 Bernini；批次多卡分派由 `experiments.device_scheduler` 负责。

`queue.py` 保存任务及依赖，`engine.py` 管资源槽和派发，`service.py` 将任务接入原 Harness，`renderers.py` 管渲染调用与资产，`media_cache.py` 复用解码。SQLite 数据库与运行目录应放在执行主机本地磁盘。

服务资源槽描述并发能力，不是每条任务的新预算。单任务默认 N=4，期限为单次生成耗时 ×（N＋0.5）：Bernini 90 分钟、Ditto 180 分钟，保持真实计量和模糊提示。未提供预算文件的 API 服务也使用在线计量，不落回旧的 offline／调用次数额度。

## 失败与恢复

| 情况 | 处理 |
|---|---|
| 完整模型响应已保存、状态尚未提交 | 读取原响应继续，不重新调用 |
| 完整工具回执已保存 | 沿原 job 收集，不重新生成 |
| Critic 明确失败 | 形成工具失败结果，Planner 继续决定 |
| 某任务模型执行未知 | 保留并隔离该任务，其他独立任务仍可派发 |
| GPU 执行未知 | 保留该设备占用，先核实原执行 |
| 达到任务期限 | 冻结候选和实际执行状态，不给恢复任务重新计时 |
| 正常交付或合法无交付停止 | 结算任务及依赖，批次继续 |

运行目录由所有者锁保护。`drain` 停止派发并等待当前调用结束；`resume` 恢复派发许可，再执行 `run`。未知外部请求的恢复核实与普通已知失败重试区分，避免重复消耗。

## 命令入口

使用 [服务模板](../configs/creative-service.example.json) 填好实际资产和 API 角色配置。已有 Bernini 环境安装 `requirements.server-runtime.txt` 即可补充控制器／证据依赖，不重新安装 torch/CUDA。

```bash
python scripts/run_server_pipeline.py --service /persistent/lha-service init --config /path/service.json
python scripts/run_server_pipeline.py --service /persistent/lha-service submit --manifest /path/task.json
python scripts/run_server_pipeline.py --service /persistent/lha-service run --once
python scripts/run_server_pipeline.py --service /persistent/lha-service status
python scripts/run_server_pipeline.py --service /persistent/lha-service drain
```

常驻服务使用 `run`，单次排空依赖链使用 `run --once`。既有任务继续使用冻结配置与收据；代码升级在新服务目录验证。正式 Low→High 终评从独立结果入口运行，creative 服务不混入旧 task-card 评价队列。

多卡主实验优先使用 [实验运行安排](experiment-campaign.md) 中的 campaign 入口；不要手动重复启动同一张卡的生成 worker。用户目前要求等待通知才启动双卡 loop。

## Relay 502 后续接原文本调用

`scripts/recover_interrupted_model.py` 处理已经返回本地失败回执的 Planner／Critic 文本调用。先停止原 worker，再用原 `client-audit/summary.json` 的 SHA256 检查恢复范围：

```bash
python scripts/recover_interrupted_model.py --run /path/batch/workers/0/tasks/TASK/run \
  --audit-sha256 ORIGINAL_SUMMARY_SHA256 --reason "Resume interrupted relay text request"
```

加 `--execute --abandon-response` 准备原状态与队列的续接，随后由原调度命令运行。准备步骤不调用模型或 GPU；保留原时限、候选、生成回执和原账本费用，为同一文本请求开放一次新的 transport attempt。旧异常、队列结果及外层中断汇总保存在该 run 的 `model-recoveries/` 中。已过期任务保持原结果。

`upstream_connect` 覆盖发送请求及等候响应；`RemoteDisconnected` 或 `SSL EOF` 本身均不证明未提交。此入口将两者记为 `possibly_submitted`，原未知费用继续保留。`--abandon-response` 表示放弃该次中断文本并另取一次回答，不声称原请求未执行。已保存回答走原结果收集路径。

冻结运行只需复制这一个脚本到原 checkout 的 `scripts/`；无需更新运行库、提示词或 profile。兼容测试覆盖冻结 `4db2bba` 的 Planner 同事件续接和 Critic 第四次检查续接。
