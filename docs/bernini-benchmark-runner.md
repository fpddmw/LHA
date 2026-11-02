# Bernini-R 官方增强工具包

> 阶段记录：本文保留当时的设计、数据版本或执行状态。当前开发版以 [文档入口](README.md)、[当前状态](current-status.md) 和 [实验运行安排](experiment-campaign.md) 为准。

只使用配套 benchmark.zip。解压到 /data/lha 后，应存在 /data/lha/benchmark_data/benchmark.json。
75 条普通样本，统一编号 001–075；训练 001–040，验证 041–050，测试 051–075。没有额外样本子集。
任务为每条的短、长提示词分别增强后生成，共 150 个视频（训练 80 / 验证 20 / 测试 50）。Direct 与评分不在本包任务中。

## 使用

Linux、Python 3.11+、FFmpeg/ffprobe，以及对应模型的完整运行依赖。模型权重与凭证不随包分发。
Bernini 使用官方代码及本地 Bernini-R-1.3B Diffusers 权重；不使用完整 latent planner 模型。
两个渲染器配置同一个支持图像输入及 max_completion_tokens 的增强模型服务。

```bash
export BERNINI_PE_BASE_URL="https://YOUR-PROVIDER/v1"
export BERNINI_PE_MODEL="gpt-5.4-2026-03-05"
read -rs -p "PE API key: " BERNINI_PE_API_KEY
export BERNINI_PE_API_KEY
bash run_pe.sh /data/lha /opt/Bernini /models/Bernini-R-1.3B-Diffusers /results/bernini-pe-clean --preflight-only
# 环境检查后先单条试运行：
python run_bernini_benchmark.py run --output /results/bernini-pe-clean --bernini-code /opt/Bernini --model-dir /models/Bernini-R-1.3B-Diffusers --only 001__short__pe
# 确认首条后，运行其余位置并复用已完成项：
bash run_pe.sh /data/lha /opt/Bernini /models/Bernini-R-1.3B-Diffusers /results/bernini-pe-clean
```

使用新结果目录；旧编号结果不能直接接续。BENCH_PYTHON 指定 Python，BENCH_DEVICE 指定 GPU。共享 GPU 时，所有入口（包括单条试运行的 --gpu-lock）必须使用相同锁文件。

## 实验记录

vendor/ 内为固定提交版本、未经改写的 Bernini 官方增强器及许可证。Ditto 使用迁移版本，不宣称是 Ditto 官方方法。两包各自调用增强模型，因此改写文本可能不同；当前比较的是整套流程。固定增强文本的跨渲染器比较需另行复用同一份保存文本。

Bernini：seed 42，40 steps，v2v_apg，max image size 848，空负提示词。
保留源帧率和最长 4n+1 前缀，省略末尾 0–3 帧并记录。增强失败不回退成成功结果；超出 512 token 停止，不截断。错误与中断不会自动重新提交；已完成项复用前校验哈希。

完整返回输出目录：plan.json、runtime.json、cases/、summary.csv、summary.json、index.html。保留原始提示词、实际增强文本、API 请求与返回、模型/代码身份、视频及哈希、耗时和 usage。价格未知时不编造费用。

打包只完成离线检查，未调用 API 或 GPU；目标机器需通过 preflight 并核对首条。测试输出不用于修改本版经验；评价以每组原始短或长提示词为准。
