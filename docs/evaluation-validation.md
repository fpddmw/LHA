# 当前统一指标实现

当前代码采用 lha-metrics-v3 / lha-score-v3 / lha-report-v3，定义见 [生成指标表](evaluation-metrics.md)，方法见 [统一协议](evaluation-protocol.md)。新计分直接为 0–1，状态在全链路保留；当前检查包括：32 项评价行为、11 项汇总/兼容、15 项注册表/状态/分母、6 项 worker 合同及 2 项服务评价桥接，共 66 项通过。原始/计算契约还验证了纯显示修改可复用判断与分数。

32 条保存 judgment 已离线生成 primary_report_v3/report_v3，原始 288 个 VLM 评分、16 条主比较的分值、排序与成功状态不变；原始文件受 SHA 核对保护。没有新增模型调用或视频生成。

以下 v1 样例与检查记录作为历史验证，不代表当前计算入口。

# Evaluation v1 实施与验证记录

日期：2026-10-29。范围：独立评价模块、CLI、规范和开发示例；原 planner、在线 loop、历史 judge 与实验资产保持各自版本。

## 已实际完成

- 纯 Python 的卡验证、分组计分、未知上下界、成功判定、源级统计、配对差值和 loop 分析。
- 独立语义／设计／创造力 judge 请求、缓存签名、A/B 反转盲评、人工评分一致性汇总、planner 诊断接口。
- 原生视频解码、PTS 对齐、完整时长检查、显式逐帧映射、概览／连续区间证据及哈希校验。
- CLIP-F 与 DINO-F 的编码器执行入口、原始余弦计算与配置记录。
- 当前 benchmark 入口核对：50 条短任务、57 条长任务，共 107；正式 100、示例 7。
- 041 短／长两张源视频评价卡，明确标记 development。

## 自动测试

命令：`python scripts/test_evaluation.py -v`。

Windows bundled Python、PyAV 19.0.2 与 Pillow 环境：31 项通过，包括真实生成测试视频后的编码、解码和证据校验。
WSL Python 3.12 可运行标准库测试；没有 av/Pillow 时视频测试明确 skip。
测试用假模型、合成评分和合成视频均标为 fixture，不进入真实 benchmark 成绩。

重点行为：

- 3.7 小数评分保留，未知不填中间分，核心失败不被美学抵消。
- 同一个原始要求拆成更多检查点不会提高权重。
- 稀疏证据无法产生确定的 sequence 结论，局部 dense 无法覆盖全片命题。
- 细节损伤不会被 judge 重新命名后升级为核心失败。
- 生成失败保留在批量分母中；缺少 seed 的点估计不通过删缺失值抬高。
- A/B 顺序偏好、unknown 和真正平局分别记录。
- loop 比较上一接受版本；拒绝版本不成为下一轮默认参照。
- 输入／卡／图像变化使旧缓存失效。

## 一次真实视频与订阅 judge 集成

输入：已有 Bernini `041__long_keep/native.mp4`，101 帧、20 fps、5.05 秒。
原片：benchmark 041；任务：原始长指令。没有重新生成视频。
评价器：本地订阅 GPT-6.1-sol / xhigh，三个独立无工具上下文，12 对概览帧。

首次集成发现并修复两项问题：创造力独立请求缺少完整返回 schema；可选细节被 judge 升级为严重损伤。
原始失败响应保留在运行目录，修复后在新目录重新调用，未直接修改模型返回分数。

修复后实际链路完成：prepare → 三次 judge → schema/evidence 校验 → score → JSON/CSV/Markdown 报告。

历史 v1 样例存储：风格 3.9，五项美学计算均值 3.80；编辑得分编码 100.00、细节得分编码 16.67。
展示 v2 对应为风格 3.9、美学计算均值 3.8、编辑 1.00 分、细节 0.17 分。书写过程未获得连续证据，核心保留的证据区间显示为 [0.50,1.00] 分，整题状态仍为 unresolved。这里只转换显示单位与精度，历史判断及存储保持原状。
时序连贯性留空；没有固定参考集，相对独特性留空。
这些数值只验证新协议能保留风格达成、细节损伤和未知时序之间的差异，是一个已开发样本的一次 judge 输出，不能作为全量模型比较或人工确认结论。

本地运行资产（out 不提交 Git）：

- `out/evaluation_v1_validation/task_index.json`
- `out/evaluation_v1_validation/041_long/evidence/evidence.json`
- `out/evaluation_v1_validation/041_long/judge_verified/judgment.json`
- `out/evaluation_v1_validation/041_long/score.json`
- `out/evaluation_v1_validation/report/report.md`

## 尚未执行的工作

- 其余任务的完整评价卡标注与审阅、全量视频重新打分、人工校准与新 planner 的正式比较。
- GPU 编码器的真实 CLIP/DINO 权重运行。当前执行环境未安装 torch/transformers，也没有这些权重；已测试余弦与汇总逻辑，未为此次代码交付另行下载大权重。
- 内置兼容 API 后端的真实远程服务验证。本次真实模型链路使用已有 Codex 订阅后端。
- 新评价协议对全部历史 loop 的终评；旧 v3 结果保持原样，不补造缺失的风格／美学／创造力分。

以上是运行边界，不代表协议缺失的成绩已经完成。后续按正式 manifest、审定卡、独立终评和同预算对照推进。
