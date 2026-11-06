# ChatGPT 订阅接入

LHA 可通过官方 Sign in with ChatGPT 授权后直接调用 Responses API。Planner 和 Critic 使用项目自身的提示词与抽帧结果，客户端不启动 Codex CLI。OpenRouter 后端继续保留；模型工厂选择实际使用的传输。

## 登录与检查

在安装了 `requirements.server-runtime.txt` 的环境执行：

```bash
python scripts/chatgpt_subscription.py login
python scripts/chatgpt_subscription.py status
python scripts/chatgpt_subscription.py models
python scripts/chatgpt_subscription.py probe --output out/chatgpt_subscription_probe
```

`login` 启动本机回调监听并打开官方授权页。使用浏览器登录并授权 LHA 使用 ChatGPT plan。WSL 场景可加 `--no-browser --port 18765`，在 Windows 浏览器打开程序显示的本机地址。授权监听默认等待 30 分钟；这与在线任务的 2.5 小时期限分开。

凭证保存在仓库外 `~/.config/lha/chatgpt-subscription.json`，也可通过 `LHA_CHATGPT_CREDENTIAL_FILE` 或 `--credential-file` 指定。宿主标识保存在同目录 `chatgpt-host.json`。同一凭证的续期通过进程锁串行执行，access/refresh token 一起原子替换。授权记录属于 LHA，不读取 Codex 登录文件。

`models` 查询实际账号可用模型；`probe` 检查 GPT-6.1-sol 并提交一张左红右蓝图片，保存回答、usage 和传输回执。接口可用性以该实测结果为准。探针不替换模型；不会把“已登录”写成“图像调用成功”。

## 实验选择

角色配置文件为 [chatgpt-subscription-models.json](../configs/chatgpt-subscription-models.json)。现有统一入口使用：

```bash
python scripts/run_creative_benchmark.py prepare \
  --output out/subscription-preview \
  --split train test --sample-ids 001 005 026 067 \
  --prompt-form long --method full direct pe-loop \
  --max-generations 4 --no-maintenance \
  --model-config configs/chatgpt-subscription-models.json
```

该示例只准备本次选定的四个视频，保留完整原始 benchmark 清单；`--sample-ids` 在解码和冻结前筛选，输入计划与批次均记录选择。主机的 `models` 应与冻结批次保持一致。准备、离线校验与模型配置解析均不启动 GPU。

底层客户端也可通过 `LOW_HIGH_AGENT_VLM_BACKEND=chatgpt_subscription` 选择，但批次与服务优先使用显式模型工厂。模型逻辑名称保持 `openai/gpt-6.1-sol`，官方线上请求 slug 为 `gpt-6.1-sol`，reasoning 为 `high`。正式 GLM／Sonnet 仍由各自 API 后端提供。

## 运行语义

每次请求发送完整所需上下文；系统提示映射为 `instructions`，截图以原始图像字节发送。使用 `store:false`、`stream:true`，不发送此授权通道不支持的 `max_output_tokens`、temperature、previous_response_id 等字段。项目不额外设置订阅 token 或金额上限；账号自身的服务额度仍由 OpenAI 决定。

订阅客户端通过 `lha.submit_result` 原生 custom tool 提交本步结果，设置 `tool_choice: required` 和 `parallel_tool_calls: false`。工具输入直接承载现有 JSON 动作或所请求的报告，现有 harness 执行一个动作，并在下一请求提供真实结果；不增加模型调用。提交说明完整定义于 `src/vlm/response_contract.py`，实际传输版本记为 `responses-sse-submission-v4`。

客户端按 output/content index 与消息 ID 组装工具输入和文本，`response.completed.output=[]` 或空的 done 快照保留已经收到的内容。只有注册的提交工具输入进入执行层，过程消息不当作动作。兼容历史流时选择最后一条 `phase: final_answer`，无 phase 时使用最后一条未标注消息。真正空答复先尝试从原始流找回正文，仍为空则由原逻辑调用自动重试；每次响应和 usage 保留，已有动作、视频及评价继续复用。格式纠正在原决策步骤内完成。

已有空缓存可从其原始完成流零调用恢复：

```bash
python scripts/recover_subscription_answer.py --run "$RUN" --event event-0010 --stream "$STREAM"
python scripts/recover_subscription_answer.py --run "$RUN" --event event-0010 --stream "$STREAM" --execute
```

入口绑定原 response ID 与 client/relay 流哈希，只为没有执行动作或生成的任务准备恢复。旧空输出、returned 回执、状态和技术结算进入 `response-recoveries/`；原输入、usage、账本、clock、已用次数及其它调用保留。`--execute` 只写回原缓存并重新排入原事件，不调用模型或渲染；监督暂停标记继续保留。没有最终文本的流如实返回 `completed_without_answer`。

升级接续使用独立的新源码目录，与旧冻结源码保持同一目录层级。新目录的 `src/`、`scripts/` 使用修复版；数据、知识、模型及数值后端可链接到原冻结资产，使原 source/input plan 的绝对路径继续有效。使用新目录的 `scripts/run_creative_benchmark.py run --output <原批次> --host-config <原配置> --devices 0 1`，入口 ROOT 和子 worker 导入均指向新源码。原冻结目录保持原样。

维护动作统一为 `{"action":"skill","arguments":{"id":"lha-experience-analysis"}}`，同时兼容历史实际返回的 `{"skill":{"id":"lha-experience-analysis"}}` 和 `{"skill":"lha-experience-analysis"}`。缺少动作的回复在原步骤内纠正；加载成功后，Skill 正文进入下一次输入的 `loaded_skills`。

维护阅读按实际返回页面去重，在当前维护期间保留所有不同页面，并提供 `next_page` 动作继续分页。单页最多 8000 字符；改变更大的请求长度不会产生多个缓存副本。读取已保存的模型输入时，优先展示解析后的 `user_text`，随后展示原系统指令，原文件保持完整。`operation_history` 记录已完成动作；维护自己的 `maintenance_progress` 显示当前步骤，最后一步用于模型提交 `contribute`。这些信息仅用于事后维护，在线 Planner 的模糊预算提示保持原设计。

已经交付、仅维护失败的任务使用 `python scripts/run_creative_benchmark.py recover-maintenance --output <原批次> --topic <原题目ID>`。该入口直接接续指定题目的维护，不经过 GPU 队列；模型沿用批次配置。程序识别旧维护输入中反复出现的 `Choose an available maintenance action` 且 `loaded_skills={}`，在原维护 attempt 下使用 `calls-v2/` 重新开展维护；原 `calls/` 和失败记录保留。有正常进展的旧维护继续使用原调用缓存。已完成的视频、Critic 和选片不重跑，维护成功后重复运行直接复用结果。维护读取任务绑定的经验快照，预经验组与原在线任务读取相同预经验。

在线中断时留下的 `maintenance/training-errors/<题目>.json`、`status: not_eligible` 会在原任务交付后重新检查。原入口及 `recover-maintenance` 先验证交付、候选文件和原题目／源片／请求／profile 绑定，再将旧标记保存至同目录的 `recovery-history/<题目>/` 并接续维护。尚未交付时保留原标记；已完成的维护直接复用。

若旧版本在最后一步仍返回阅读而耗尽维护次数，恢复会从已有回答重建前面的阅读和 Skill 状态，仅在最后一步的 `submission/` 中请求模型提交自己的结论。原最后一步回答保留；步骤上限、token 配置与实际调用账本沿用原值。内容是否形成条目由模型提交的 `changes` 决定，程序不生成“无新增”结论。

完成依据是实际 SSE 帧中的 `response.completed` 和响应对象的 `status: completed`。部分中转会把真实 SSE 标成 `application/json`，客户端保留这个头部差异并按实际流解析；普通 JSON 正文和没有终态的残缺流仍不视为完成。

只有 `response.completed` 且有可用正文才作为返回结果交给 harness。明确失败、截断和空结果保留原因及实际 usage；自动恢复使用同一逻辑调用，每个恢复窗口默认 12 次传输尝试，已保存的完整回答直接收取。恢复扫描跳过历史备份。调用沿用任务配置和原有账本，不重置生成次数。

多卡同机进程共享同一受保护凭证文件，串行续期。跨主机部署时，先指定一个运行宿主为凭证续期负责人；不要复制同一可旋转 refresh token 后让多台主机独立续期。官方支持在本机完成授权后转移到自托管主机，该主机接管后续续期并保留独立宿主标识；使用多个独立运行宿主时应各自完成授权或通过单一凭证负责人转发调用。

本次两台双卡使用单一负责人转发。在持有授权文件的宿主运行：

```bash
python scripts/chatgpt_subscription.py serve --port 18766 \
  --credential-file /root/.config/lha/chatgpt-subscription.json
```

服务只监听 `127.0.0.1`，转发 `/models` 与 `/responses`。第二台宿主通过已有授权的 SSH 通道，把本机 `127.0.0.1:18766` 接到凭证宿主的同一监听端口。两台机器的 Planner／Critic options 均加入 `"relay_url": "http://127.0.0.1:18766"`，模型、reasoning 和业务请求保持一致；Worker 不接触 OAuth token。先运行 `python scripts/chatgpt_subscription.py probe --relay-url http://127.0.0.1:18766 --output <独立探针目录>` 验证各主机路径，再启动任务。卡管理任务持有转发进程和运行回执。

## 接入故障诊断与真实 Planner 检查

每次请求产生一个 `request_id`，客户端与中转层使用同一编号。调用目录的 `attempts/01/client-audit/` 保存原始 `stream.bin`、完成时的 `response.json` 和 `summary.json`；summary 包含 HTTP 状态、Content-Type、事件计数、完成标记、消息 phase、最终选中消息及异常阶段。`unknown.json` 同步引用这些诊断。Authorization 与 OAuth token 不写入日志。

本机转发端口在建立连接时返回 `Connection refused`，表示请求尚未送达转发服务。客户端将它记为 `not_submitted`，该次请求的调用次数、token 和费用占用为零，原始失败回执继续保存。SSH 转发恢复后，直接重跑原 `run` 命令：程序核对旧调用的本机地址、连接阶段、空原始流、请求编号及失败完成回执，将误记为未知的本地拒绝连接修正后，在原 Planner／Critic 调用中继续尝试。公共账本和任务自己的账本均会处理；已生成视频、成功 Critic、原输入、时钟和生成额度保持原值。无需另建任务或使用 `recover_interrupted_model.py`。HTTP 502、连接重置或读取流中断继续保留其实际未知状态。

中转层默认在凭证目录旁的 `subscription-relay-audit/<request_id>/<relay_id>/` 保存上游原始流和诊断，可通过 `serve --audit-dir <目录>` 指定位置。连接上游失败、读取中断、上游正常 EOF、下游写入失败分别记录。上游尚未返回响应便中断时返回明确的 `relay_execution_unknown`；已开始流式响应时发送相应中转错误事件。两者保留原请求的未知状态，均不自动重发 POST。若中转层已收到完整终态但下游断开，可从该请求的 `response.json` 核实原回答。日志落盘失败会保留内存诊断，不使已经完成的回答失败。

红蓝图片探针只验证基本多模态通路。部署接入修复时，还应使用一份此前**已返回调用**的 Planner `transport/input.json` 做独立格式探针：

```bash
python scripts/chatgpt_subscription.py probe-planner \
  --relay-url http://127.0.0.1:18767 \
  --probe-input <已返回调用的transport/input.json> \
  --output <本次独立探针目录>
```

该命令提交一次新的诊断请求，使用已保存的真实提示和原图，校验最终输出能否解析成当前动作结构，并保存 phase、终态和 usage；返回的动作不执行。诊断请求与原实验分别记录。修复版使用独立源码及中转端口验证后，再安排尚未完成的实验。

## 官方依据

- [中间消息与最终回答的 phase](https://developers.openai.com/api/docs/guides/reasoning#phase-parameter)
- [流式响应事件](https://developers.openai.com/api/docs/guides/streaming-responses)
- [注册和登录](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [模型目录与 Responses 调用](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [参数和模态限制](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [自托管服务器](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms)

离线回归：`python scripts/check_repository.py --module test_chatgpt_subscription --module test_api_backend --module test_configuration_boundaries`。
