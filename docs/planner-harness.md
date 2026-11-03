# Planner Harness

当前主线为 `creative_loop_v1`，完整状态流见 [Loop 设计](creative-loop-implementation.md)。模型由 API 客户端提供，运行目录保存实际输入、响应、动作、视频和恢复信息。

## 当前动作

Planner 可 `read`／`search` 知识、`observe` 视频、维护 `note`／`workspace`、`generate` 新视频、指定 `delivery_candidate`，并通过 `finish` 交付或合法停止。Planner 自评模式另接收 `review`；它可以与下一动作同次提交。精确动作格式由运行时 [操作手册](../src/planner_harness/CREATIVE_LOOP.md) 提供。

`generate` 明确输入视频和提示词，可提供 `review_focus`。所有成功生成都进入配置的检查路径。选择交付候选不会偷偷改变下一次生成输入；最终交付不额外发起评审。

## 生成提示词的视觉化改写

每次 Planner 调用都包含共享的 [提示词编写指引](../knowledge/creative-loop/PROMPT_WRITING.md)，与操作手册、当前知识条件的阅读指南和 review 指南一起进入系统提示。指引沿用 PE 的视觉化改写方式：结合原始任务和已观察画面，把风格与效果落实到主体、承载表面、位置、材质、光照和动作关系，再形成完整的英文生成提示词。

full 的阅读指南进一步引导 Planner 把适用经验落实到输入选择、视觉构造和具体措辞；full／none 共享视觉化编写方式，各自使用已有资料权限。生成后，Planner 将 Critic 发现或自己的评审与原任务、实际输入、已提交提示词对照，把选定的修订整合进下一份完整提示词。输入仍可选择原片或已有候选。

改写在原有 Planner 调用中完成，使用现有 `generate.prompt`，调用次数和交付条件沿用当前流程。新准备的实验将这份指引与知识一起冻结；使用已有快照的任务沿用其中的指引，恢复中的任务继续使用已保存的系统提示。部署新实验时核对 `system-prompt.txt` 已包含视觉化改写指引。

## 上下文与检索

`context.py` 组织原始任务、候选、工作记录、读取材料及最近结果；`working_memory.py` 管理笔记与文本预算；`creative_knowledge.py` 按 full／none 权限提供入口、搜索和分页。观察支持原生 PTS 连续帧、概览、裁剪、翻页和重开记录。图片传输使用 API 客户端实际记录的附件。

无经验组在 RSI 训练部分的任务后维护累计私有经验，在线始终使用 none；后段只运行不维护。full 在全量任务上读取训练结束的固定快照，none 不读取经验。review 操作指南在两种知识条件下都可见，经验内容不因检查方式泄露给 none。

## 运行和恢复

- Single-task entry: `scripts/run_planner_harness.py`; new tasks default to `creative_loop_v1` and loop mode. `run_agent_loop.py` delegates to the same entry. Historical proposal-only execution requires `--workflow legacy`; resumes use the saved workflow.
- 生成工具 worker：`scripts/run_planner_worker.py`。
- 实验入口：`scripts/run_experiment_campaign.py`。
- 多任务服务：[server-runtime.md](server-runtime.md)。

The current experiment profile requires using all N generation attempts before final selection, with default N=4. Both knowledge arms can select an earlier candidate at the end. The task deadline is the renderer estimate multiplied by N+0.5: 90 minutes for Bernini and 180 minutes for Ditto at this N. Tokens are estimated and metered rather than capped by a default token limit. Resume retains the original counts and deadline and collects saved answers or receipts under their original call/job. Known failure and uncertain external execution retain their respective recovery paths. Configuration changes use a new run directory.

Planner 调用明确失败时，结果登记沿用运行中已保存的候选选择，保留所有生成版本。原状态及 arm 回执保持 `execution_failed`；展示结果记录 `interrupted_delivery`、`partial=true`、`planner_confirmed=false`，同时保存原失败状态与选择依据。旧运行可用 `python scripts/settle_planner_failure.py --output 原run --topic SAMPLE__long --device 原worker编号` 检查，加 `--execute` 后登记。该入口只读取缓存，新增模型和 GPU 调用均为零，原 native 状态、调用回执和时钟保持原样。

旧 proposal-only／RSI 实现在 `planner_harness.compat`，用于历史运行解析和对应兼容测试，不定义当前主实验协议。

## Single-task launch configuration

The single-task CLI and server runtime use `vlm.settings.create_client` to instantiate the configured role factory and options. New tasks use `configs/creative-loop-v1.json` unless `--profile` supplies another creative profile. An execution file can provide renderer settings and role clients, including the subscription factory. CLI model/effort overrides apply to the actual client and its recorded configuration. `--backend` must agree with an explicitly configured factory.

```bash
python scripts/run_planner_harness.py --source /path/source.mp4 \
  --request-file /path/request.txt --execution-config /path/execution.json \
  --output out/single-task
python scripts/run_planner_harness.py --output out/single-task --resume
```

These are execution commands: starting a task calls its configured model. A render worker or service is still required to execute a returned `waiting_tool` job. For a complete experiment use the campaign entry instead of manually duplicating its workers.

For a new task, `--max-generations N` updates both the resource limit and continuation guard. A profile's explicit wall-time limit remains explicit; otherwise time is derived from the effective N and renderer. Creative tasks have no `--max-turns` control. Resume constructs the saved client, preserves an explicit null reasoning effort, and retains the original generation limit, review mode and execution configuration. It never substitutes today's default profile for a historical run.

## 检索和工作记忆

`search {query, scope?: "style"|"experience"|"all"}` 在已冻结且获准的资料中检索。排名结合词频、稀有词、标题／摘要和连续短语；全部候选先参与排名，再截取结果。返回正文摘录与可打开条目。查询中的作品名不存在时，明确返回该事实，并按视觉特征寻找相关参考，避免把共享标题词当成同一作品。可继续读正文、看参考图或换视觉关系搜索，不强制阅读次数。

`creative-memory-v2` 保留任务内所有已读页面；相同页面重读只更新记录，目录和重复元数据留在原始 read 事件。最近一次读取与工作记忆只展示一份正文。总文本／图像容量确实不足时，各来源保留可见摘录和重开入口，原始页面保持完整；新的较小上下文恢复完整页面展示。full／none 使用同一记忆机制和各自资料权限。

资源提示沿用模糊阶段。`generate.justification` 可选，用于记录尝试目的；继续生成无需回答阶段问题。`finish` 使用已有检查直接交付，不增加评分或说明准入。
