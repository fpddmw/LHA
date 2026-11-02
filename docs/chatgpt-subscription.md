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

客户端从 `response.completed.output` 中选择最后一条 `phase: final_answer` 助手消息；同一次响应中的 `commentary` 不进入 Planner 动作解析。未提供 phase 的兼容响应使用最后一条未标注消息；只有 commentary 时返回空文本，走已有输出校验。原始输出项与所有中间消息完整保存在调用证据中。

完成依据是实际 SSE 帧中的 `response.completed` 和响应对象的 `status: completed`。部分中转会把真实 SSE 标成 `application/json`，客户端保留这个头部差异并按实际流解析；普通 JSON 正文和没有终态的残缺流仍不视为完成。

只有 `response.completed` 才保存为成功回答。明确失败和截断保留原因及实际 usage；连接中断保留未确认状态，由原运行的恢复入口处理。原请求已经保存完整回答时直接收取，不重复提交。模型调用沿用在线任务的 2.5 小时期限以及原有账本。

多卡同机进程共享同一受保护凭证文件，串行续期。跨主机部署时，先指定一个运行宿主为凭证续期负责人；不要复制同一可旋转 refresh token 后让多台主机独立续期。官方支持在本机完成授权后转移到自托管主机，该主机接管后续续期并保留独立宿主标识；使用多个独立运行宿主时应各自完成授权或通过单一凭证负责人转发调用。

本次两台双卡使用单一负责人转发。在持有授权文件的宿主运行：

```bash
python scripts/chatgpt_subscription.py serve --port 18766 \
  --credential-file /root/.config/lha/chatgpt-subscription.json
```

服务只监听 `127.0.0.1`，转发 `/models` 与 `/responses`。第二台宿主通过已有授权的 SSH 通道，把本机 `127.0.0.1:18766` 接到凭证宿主的同一监听端口。两台机器的 Planner／Critic options 均加入 `"relay_url": "http://127.0.0.1:18766"`，模型、reasoning 和业务请求保持一致；Worker 不接触 OAuth token。先运行 `python scripts/chatgpt_subscription.py probe --relay-url http://127.0.0.1:18766 --output <独立探针目录>` 验证各主机路径，再启动任务。卡管理任务持有转发进程和运行回执。

## 接入故障诊断与真实 Planner 检查

每次请求产生一个 `request_id`，客户端与中转层使用同一编号。调用目录的 `attempts/01/client-audit/` 保存原始 `stream.bin`、完成时的 `response.json` 和 `summary.json`；summary 包含 HTTP 状态、Content-Type、事件计数、完成标记、消息 phase、最终选中消息及异常阶段。`unknown.json` 同步引用这些诊断。Authorization 与 OAuth token 不写入日志。

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
