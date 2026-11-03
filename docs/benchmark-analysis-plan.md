# 全量主实验与 RSI 统计范围

主实验覆盖当前 67 条任务的长短两版，共 134 个条件，包含 Direct、PE Loop、无经验 Planner Loop、有经验 Planner Loop。RSI 的 40／27 划分用于规定经验积累来源与迁移评价子集；四组主实验均跑全量。

先跑无经验全量流程，前 40 条逐题维护，后 27 条关闭维护；再以固定累计经验跑全量有经验组。两者使用同一结果注册目录，前段结果直接进入主表，后段结果直接构成 RSI 对照。经验积累不额外生成一批训练视频。

主实验预设主比较为无经验 Planner 最终对 PE 最终的 task_completion 盲偏好；RSI 子集的主比较为后 27 条无经验对有经验最终结果。Direct 对各首轮、各自首轮对最终、有／无经验全量对照作为相应增量分析。Planner self-review is an additional ablation. Critic and self-review families start from the same canonical seed, accumulate separate private contributions, and freeze their own libraries for their corresponding full arm. Their results and experience ownership are reported separately.

每个源组先聚合 short/long 条件，统计单位为 source_group。采用源组聚类 bootstrap 和配对源组符号置换检验；每位判官分别报告，对次要比较及终点做 Holm 校正。当前 seed42 的结论覆盖这一生成种子。程序的 `main_analysis` 使用全量；`rsi_analysis` 仅使用 RSI 测试侧，并明确各自分母和主比较。

输出缺失时保留 planned 分母：单侧缺失按行政 ITT 效用记负、双侧缺失各记一半，并标明这类赋值的性质。两个视频存在但判官未知、传输失败或交换顺序不稳定时，保留全分母上下界；有效子集偏好作为辅助结果。逐项指标保留有效样本数。

PE 含首轮最多 4 次，Planner 含首轮最多 4 次。主实验每个条件最多 `1＋4＋4＋4＝13` 次，全量最多 1742 次；追加两个 Planner 自评组最多再加 1072 次。按请求预算、有效生成、实际提交、历史复用、维护开销和硬件分别报告。运行命令见 [全量实验安排](experiment-campaign.md)，评分协议保持现行五维、长短专项与客观指标。
