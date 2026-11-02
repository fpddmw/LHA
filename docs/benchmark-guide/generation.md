# 生成操作说明

[返回仓库首页](../../README.md) · [实验总览](experiment.md)

## 适用范围

以下 PE 命令针对此前交接的 `bernini-tools.zip` 和 `ditto-tools.zip`（Ditto adapted-v2），在各自工具包解压目录执行。工具包与 `benchmark.zip` 需向项目交接人获取；本次 GitHub 评分包不包含它们。Linux / WSL，Python 3.11+，FFmpeg/ffprobe，以及各渲染器依赖和权重需提前安装。

示例路径均需换成使用者机器的真实路径：数据解压到 `/data/lha` 后有 `benchmark_data/benchmark.json`；Bernini 官方代码在 `/opt/Bernini`，Diffusers 权重在 `/models/Bernini-R-1.3B-Diffusers`；Ditto 代码在 `/opt/Ditto`，权重布局按包内 `ditto_models.json` 准备。

## 增强模型配置

两个工具包使用同一组变量。Ditto 沿用 BERNINI_PE 前缀是客户端接口约定：

```bash
export BERNINI_PE_BASE_URL='https://YOUR-PROVIDER/v1'
export BERNINI_PE_MODEL='YOUR-VISION-MODEL-ID'
read -rs -p 'PE API key: ' BERNINI_PE_API_KEY; echo
export BERNINI_PE_API_KEY
```

模型需支持图像输入及该工具包的 `max_completion_tokens` 请求参数。模型名由使用者按实验选定，两组保持一致并记录。示例不替使用者选定模型，不包含我们的服务配置。

## Bernini 官方 PE：150 个位置

在 bernini-tools 解压目录执行：

```bash
bash run_pe.sh /data/lha /opt/Bernini /models/Bernini-R-1.3B-Diffusers /results/bernini-pe-clean --preflight-only
python run_bernini_benchmark.py run --output /results/bernini-pe-clean --bernini-code /opt/Bernini --model-dir /models/Bernini-R-1.3B-Diffusers --only 001__short__pe
bash run_pe.sh /data/lha /opt/Bernini /models/Bernini-R-1.3B-Diffusers /results/bernini-pe-clean
```

依次为环境检查、单条试运行、全量。保留 seed 42、40 steps、v2v_apg、max image size 848 和空负提示词。

## Ditto 适配 PE：150 个位置

在 ditto-tools 解压目录执行：

```bash
bash run_pe.sh /data/lha /opt/Ditto /models /results/ditto-pe-adapted-v2 --preflight-only
python run_ditto_benchmark.py run --output /results/ditto-pe-adapted-v2 --ditto-code /opt/Ditto --model-dir /models --only 001__short__pe
bash run_pe.sh /data/lha /opt/Ditto /models /results/ditto-pe-adapted-v2
```

采用项目专用 `ditto_template.txt`，细节见包内 `TEMPLATE_CHANGES.md`。全局 LoRA，seed 42、50 steps、CFG 5、alpha 1、bf16、tiled、空负提示词。使用新目录，不接续旧增强模板结果。

## 设备、恢复与交回材料

`BENCH_PYTHON` 指定解释器，`BENCH_DEVICE` 指定 GPU。共享 GPU 时所有入口使用相同锁文件，单条命令也应按包内说明传 `--gpu-lock`。先验证环境与首条，再展开；正式生成调用增强 API 并占用 GPU。

保留源帧率与最长 4n+1 帧前缀，记录尾部省略情况。已完成项校验后复用；错误／中断不自动重新提交，按原工具包记录处理。不要删除失败记录以强行续跑。

交回整个 `/results/bernini-pe-clean` 或 `/results/ditto-pe-adapted-v2`，包括 plan.json、runtime.json、cases/、summary.csv、summary.json、index.html。保留原始和增强提示词、模型身份、usage、收据及视频哈希；分享前检查调用记录不含密钥。

## Direct 与 Planner / RSI

Bernini Direct 使用对应原始提示词和对齐生成配置。评分工具包本身不生成 Direct 或 Planner 输出。已有冻结 Direct 运行按其原版本完成，不把新开发脚本替换进正在执行的目录。

完整开发环境的入口为 `scripts/run_creative_benchmark.py`。以下命令只展示当前开发 CLI 的准备、检查、执行顺序，**不适用于仅解压评分 ZIP 的机器**；还需要匹配的 knowledge、host-config、模型及资源配置。完整生成流程存在评分说明列出的两项未通过测试，部署前需核对版本。

```bash
python scripts/run_creative_benchmark.py prepare --output /results/planner-new --split train validation test --prompt-form short long --method planner-once full none --results-root /results/planner-registry
python scripts/run_creative_benchmark.py preflight --output /results/planner-new --host-config /absolute/path/your-host.json
python scripts/run_creative_benchmark.py run --output /results/planner-new --host-config /absolute/path/your-host.json --budget-config /absolute/path/your-generation-budget.json
python scripts/run_creative_benchmark.py status --output /results/planner-new
```

host-config 指定使用者的实际模型服务、设备和资产；生成预算与独立评分预算分别配置。Planner 结果按[评分说明](../../handoffs/scoring-20261102/README.md)的通用清单导入相应渲染器库，full/none 保留 first/selected 候选角色。
