# Benchmark 整理记录 — 2026-11-02

> 阶段记录：本文保留当时的设计、数据版本或执行状态。当前开发版以 [文档入口](README.md)、[当前状态](current-status.md) 和 [实验运行安排](experiment-campaign.md) 为准。

当前版本 lha-benchmark-20261102-clean：75 条统一样本，训练 001–040、验证 041–050、测试 051–075。所有源视频和长短提示词字节未变，原分组归属未变。

benchmark_data 顶层只有 benchmark.json、README.md、review.html 及三个划分目录。每条目录只有 video.mp4、prompt_short.txt、prompt_long.txt。全部运行入口共用唯一清单，默认开发限制为训练集。

旧编号映射和原证据扫描记录保存在 reports/benchmark-release-20261102，仅用于追溯。历史结果/证据中的原始标识不重写；当前数据不保留特殊子集、分类标记或重复索引。执行 python scripts/validate_benchmark.py 检查完整性和证据隔离。
