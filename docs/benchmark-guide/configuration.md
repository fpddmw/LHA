# 使用者自己的运行配置

[返回仓库首页](../../README.md)

## API 配置是什么

API 配置提供模型服务地址、模型标识与密钥。PE 增强、Planner 和独立评分属于不同调用角色，不自动共用凭据。仓库不提供我们的配置。

- PE：`BERNINI_PE_BASE_URL`、`BERNINI_PE_MODEL`、`BERNINI_PE_API_KEY`，见[生成说明](generation.md)。
- 独立评分：`LHA_PARATERA_BASE_URL`、`LHA_PARATERA_API_KEY`、`LHA_SONNET_BASE_URL`、`LHA_SONNET_API_KEY`。
- 当前评分适配器使用 glm5.3flash 与 sonnet-5.5high，分别校验 `llmapi.paratera.com` 与 `api.tu-zi.com`。这些是代码的适配范围，不是附送账号；替换提供方需要适配代码和新的评分版本。

环境变量示例：

```bash
export LHA_PARATERA_BASE_URL='https://llmapi.paratera.com/REPLACE_WITH_VERIFIED_BASE_PATH'
read -rs -p 'GLM API key: ' LHA_PARATERA_API_KEY; echo
export LHA_PARATERA_API_KEY
export LHA_SONNET_BASE_URL='https://api.tu-zi.com/REPLACE_WITH_VERIFIED_BASE_PATH'
read -rs -p 'Sonnet API key: ' LHA_SONNET_API_KEY; echo
export LHA_SONNET_API_KEY
```

示例路径必须替换为提供方已确认的 base URL。不要把密钥粘贴进 README、预算文件或提交记录。设置好环境变量不代表已验证在线连通性。

## 预算配置是什么

预算文件用于控制批次、单任务和 independent 评分通道的调用次数、token、计算次数、时间与费用预留。重启继续使用同一账本，不重新获得一份额度。它不是模型价格表的自动查询功能，也不是提供方账单的绝对硬上限。

当前代码支持两种明确选择：

| cost_control | 需要填写 | 保护范围 |
|---|---|---|
| quoted_allowance | 币种、用户接受的金额上限、真实报价来源和日期、各请求最大费用，以及资源限额 | 根据报价进行本地预留与结算 |
| count_limits_only | 明确资源限额；金额保持 null | 次数、token、时间等；不提供货币金额上限 |

正式运行要求 `mode: live`。使用者自行选择模式及限额；本交接不预设哪一种已获同意。

[预算填写模板](budget.template.json)给出 quoted_allowance 的完整字段结构，所有 `FILL_...` 必须替换。它故意不能直接通过验证，不包含真实价格或默认开销授权。batch 为整个评分会话，topic 为单源视频的某个长短条件，allocations.independent 为该任务内独立评分通道。topic 限额应能容纳该通道，batch 至少能容纳一个 topic；多方法和交换顺序盲评也消耗评分额度。

资源限额填写非负整数，wall_seconds 和 max_call_seconds 为正数；金额使用十进制字符串。quoted_allowance 的四个报价项覆盖两位裁判、features 和 temporal；max_amount 是每次请求的最大费用边界，需要按实际计价方式核实，不是每百万 token 单价。

填好后，在评分 ZIP 解压目录离线验证，不调用模型：

```bash
PYTHONPATH=src python -c 'import json,sys; from planner_harness.accounting import validate_policy; p=json.load(open(sys.argv[1])); validate_policy(p,require_live=True,required_quotes=("model:glm5.3flash/none","model:sonnet-5.5high/high","compute:features","compute:temporal")); print("Budget schema OK; no API calls")' /absolute/path/your-budget.json
```

通过仅表示结构与约束通过；报价真实性、可用额度和服务连通性由使用者核实。之后按[评分说明](../../handoffs/scoring-20261102/README.md)将此路径传给 `--budget-config`。

## 费用与操作阶段

环境检查、任务准备、结果导入和普通 report 命令不调用付费评分模型。PE 正式运行调用增强模型并渲染；Planner 正式运行调用规划／在线评审并渲染；score-evaluation 调用独立裁判并计算视频指标。自动特征首次使用可能下载固定版本权重。不同工具包版本的预算入口不同，遵循其对应说明，不把评分预算参数随意套到冻结 PE 工具包。
