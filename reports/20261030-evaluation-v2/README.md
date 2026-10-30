# 首批完整评价：展示 v2

32 条完整记录；16 条预定主比较；8 个模型×任务配对、4 个独立源。

- [视频、四题总体、短长分轨及逐项证据](review.html)
- [主报告](primary_report_v2/report.md) · [完整精度 CSV](primary_report_v2/metrics.csv) · [量尺与计算元数据](primary_report_v2/metadata.json)
- [入组清单](primary_report_v2/cohort.json) · [配对差值](primary_report_v2/paired_differences.json) · [验证记录](primary_report_v2/validation.json)
- [全部条件补充表](report_v2/report.md) · [原始记录](records.json) · [冻结任务卡](cards)

语义为 0–1 分、两位小数；VLM 原始评分 1–4、0.1 步长，原始分及计算均值默认显示一位。比例单列 %。原始判断、未知、损伤和成功状态保留。041 短任务的装订/独立纸页复核仍 pending。

HTML 复用 ../20261030-sync/media 中已发布视频，原片位于 ../../benchmark_data；克隆完整仓库后可离线浏览。JSON 中保留运行时原始路径供追溯，不将其重写为新的实验输入。更早的 22/32 阶段快照保留在 20261030-sync。本次只重新导出，没有模型调用或视频生成。
