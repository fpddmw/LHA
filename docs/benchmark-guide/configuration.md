# 当前开发代码的配置

[仓库首页](../../README.md) · [实验运行安排](../experiment-campaign.md)

本页适用于根目录开发代码。冻结交接 ZIP 使用它自己的配置说明，见 [评分交接](../../handoffs/scoring-20261102/README.md)。

## 配置各管什么

| 文件 | 负责的内容 |
|---|---|
| `configs/creative-loop-v1.json` | New single-task defaults: current workflow, role clients, review mode and fixed generation allowance; historical resumes retain their saved configuration |
| `configs/creative-service.example.json` | 单设备服务、资源槽、渲染资产和角色客户端 |
| `configs/creative-fewshot-host.example.json` | 批次使用的设备、资产和 API 配置 |
| `configs/experiment-campaign.json` | 主实验方法、N、种子、长短条件和任务后维护 |
| `configs/evaluation.json` | 独立判官的结果名称、真实 API 模型、推理配置和输出容量 |
| `configs/chatgpt-subscription-models.json` | Planner／Critic 使用官方 ChatGPT 订阅授权的 Responses 后端 |
| 仓库外 `~/.config/lha/openrouter.env` | 调用密钥、共享 API 地址、可选网络转发 |

在线 review 与独立终评分别配置。修改 `configs/evaluation.json` 会进入正式评分身份；它不会把评分指标发送给在线 Planner／Critic。不要将任务后维护预算混入在线任务期限。

## API 和角色

当前默认统一使用 OpenRouter 的 Chat Completions API。Planner／在线 Critic 默认 `openai/gpt-6.1-sol`、`high`；独立终评为 `z-ai/glm-5.3-flash` 与 `anthropic/claude-sonnet-5.5`，Sonnet 使用 `high`。完整模型配置见上述文件。

本次四视频预览选择 ChatGPT 订阅 Responses 后端，登录与图像探针见 [订阅接入](../chatgpt-subscription.md)。角色工厂为 `vlm.chatgpt_subscription:ChatGPTSubscriptionVisionModel`，使用独立 OAuth 凭证文件；无需 OpenRouter key，也不经过 Codex CLI。

在仓库外的环境文件中填写：

```dotenv
OPENROUTER_API_KEY=YOUR_CALLING_KEY
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-6.1-sol
OPENROUTER_REASONING_EFFORT=high
```

可通过 `LHA_API_ENV_FILE` 指定另一个文件，也可在客户端 `models.<role>.options.credential_file` 指定。已导出的进程环境变量优先于文件；密钥不进入配置快照。管理 key 用于账户管理，推理应使用普通调用 key。

角色模型／推理参数的优先级是：`models.<role>.options` → `planner`／`critic` 角色段 → 顶层参数 → `LHA_API_<ROLE>_MODEL`／`REASONING_EFFORT` → 共享环境 → 默认值。角色为 `planner` 或 `online_critic`；显式 JSON `null` 保留为不设置 reasoning 参数。Single-task and service launches use the same role factory helper. A CLI model or effort override reaches both the actual client and its saved configuration; an explicit factory is never silently replaced by OpenRouter. Single-task launch and resume examples are in [Planner setup](../planner-harness.md#single-task-launch-configuration).

模型配置可以存在而服务尚不可用。当前 GPT／Sonnet 的地区限制和 GLM 合成图实测见 [当前状态](../current-status.md)，不据此自动更换实验模型。

## 生成、时间与维护

Planner uses the complete configured `max_generations` allowance, currently 4, before final selection. PE Loop uses `pe_max_generations`, currently 4. Both knowledge arms share the completion contract and can select an earlier candidate. Task deadlines are the renderer estimate multiplied by N+0.5, currently 5400 seconds for Bernini and 10800 seconds for Ditto. `task_budget` configures that estimate, the token planning basis and headroom. The default token estimate is one million × (N+0.5); actual calls and tokens are metered without the former default turn/call/token ceilings. Planner continues to receive approximate resource hints.

任务后维护使用 `experiment-campaign.json` 中自己的设置；它不追加生成视频。独立终评默认 `max_output_tokens: null`，由供应商处理输出容量；不要求人工填写 GLM／Sonnet 费用额度。显式计算预算只用于相应自动指标账本，不能把旧冻结包的报价模板套成当前在线任务的必填门槛。

## 主机与多卡

主机文件填写实际设备及渲染资产清单。单设备服务串行生成并复用常驻模型；多设备批次由 scheduler 为各设备派发任务，任务内依赖顺序不变。配置两个 GPU 并不意味着同时在一张卡上启动两次 Bernini。

当前双卡主机已配置临时 SSH 出口。远端环境文件可额外包含 `HTTPS_PROXY`、`HTTP_PROXY`、`NO_PROXY`；这些值仅供对应运行进程使用。地址依实际主机设置，不将临时端口作为项目公共默认值。Experiments remain paused during the current integration repair; historical host notes are not a fresh availability check.

## 离线核对

```bash
python scripts/run_experiment_campaign.py plan
python scripts/check_repository.py --suite current
```

资产检查、配置解析、离线测试和真实 API／GPU 可用性分开记录。`run --execute` 才提交真实实验；现有生成视频通过结果入口登记与复用。
