# 当前 Benchmark：50 条正式题目 + 7 条示例

当前版本为 `2026-10-29-dest`，来自用户指定的 `dest.zip`。所有 57 段视频和
57 份 `prompt.txt` 均按原始字节导入。正式 50 条的详细提示词与包内
`rewrite_results.jsonl` 逐条一致。50 段正式视频通过 SHA-256 与仓库旧源视频
逐条对应，映射保存在 `legacy_sample_id`，不依赖目录顺序猜测。

## 当前数据入口

| 文件 | 内容 |
| --- | --- |
| `sample_index.json` | 正式 50 条；ID 为 `001`–`050` |
| `fewshot_index.json` | 包内 `ok/` 的 7 条示例；ID 为 `fewshot_001`–`fewshot_007` |
| `all_samples.json` | 完整 57 条，含明确的 `split` |
| `instructions_short.jsonl` | 正式 50 条短提示词，原样取自 `style_intent` |
| `instructions_long.jsonl` | 正式 50 条详细提示词，原样取自 `rewritten_prompt` / `prompt.txt` |
| `main/<ID>/` | 正式题目的视频和原始 `prompt.txt` |
| `fewshot/<ID>/` | 7 条示例的视频和原始 `prompt.txt` |
| `rewrite_results.jsonl` | ZIP 内的完整重写溯源记录，含历史原文 |
| `provenance.json` | ZIP 哈希、文件哈希、数量和来源说明 |

索引内的 `source_video`、`prompt_file` 均相对于仓库根目录。`instruction` 默认等于
`prompt_long`；短提示词在 `prompt_short` 中。两份 `instructions_*.jsonl` 同时提供
`instruction` 和兼容既有读取器的 `intent` 字段，字段值均为该文件对应的提示词。
7 条示例在原包中没有独立的短提示词，`prompt_short` 保留为 `null`。

包内 `.frames/target/` 是重写对象视频的抽帧目录；经视频哈希匹配，正式视频均是
旧仓库的 source_low。这次导入没有把这些帧命名解释成目标视频或标准答案。
当前包没有提供新版生成结果、目标视频、评分量表或指标结果。

## 与历史实验的关系

当前题目与提示词以本目录为准。`reports/top50_video_bundle_20260725_nodup/`、
`归档_extract/` 以及 `scripts/eval/bench_v3/`、`scripts/bench_v4/`、
`scripts/bench_v5/` 中的旧提示词、派生 checklist、分数和生成记录保留为历史材料，
它们对应此前运行的输入，不是本版的结果或评分目标。

`scripts/bench_skill/run_bench.py` 的默认 `--sample-index` 已指向本版正式 50 条。
旧版本专用启动脚本仍用于历史复现；读取当前数据时使用本目录索引及其源视频路径。
本次只更新数据与读取默认值，没有执行旧 loop，也没有改造 planner、critic 或 skill。
