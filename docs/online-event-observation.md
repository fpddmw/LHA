# Planner 与 Critic 共用的视频观察

当前两种 review 模式共用 `planner_harness.event_observation.observe_videos`。独立 Critic 通过自己的 observe/review 循环调用它；Planner 自评使用原任务中的 observe。视频由 PyAV 按原生 PTS 顺序解码，连续窗口保留解码序号与时间戳。

## 观察一个事件

```json
{
  "action": "observe",
  "arguments": {
    "video": "v1",
    "mode": "continuous",
    "start": 1.2,
    "end": 3.8,
    "count": 16,
    "page": 1
  }
}
```

`count` 是每页的原生帧数（2–16）。相邻页重叠一帧，`next_arguments` 给出下一页参数；页面附有实际图像。`video` 可传入多个视频 ID，一次最多供给 32 帧。`crop` 使用规范化坐标。已有 `observation` ID 可重开，采样观察通过 `mode: sampled` 使用同一入口。

连续页保留 `page_coverage` 和相同视频、窗口、裁剪的累计 `coverage`。`complete` 表示请求窗口的帧覆盖；时间、帧索引和图像保存在原观察记录。不同视频按自己的 PTS 解码，同一秒数不自动执行动作对齐。

## 每次生成后的检查

每次成功生成都触发配置的 review，包括最后一次。Planner 可在 `generate.review_focus` 提供 `focus`、`extra_checks`、`compare_to`、`events`；这些检查重点与原始任务、提交／生效提示词一起提供给 reviewer。

Critic 先收到原片、实际输入、候选及指定对比视频的六帧概览，再自主选择窗口、分页、裁剪或重看。最终返回 `summary` 和可选 `findings`，描述结果与依据，不包含正式数值评分或修改建议。观察与 review 按原调用记录恢复，已完成的调用不因恢复再次提交。

Planner 自评保持同样的观察工具和操作指南，在检查结果中返回 `review`，随后继续规划或交付。Planner 的完整任务上下文和 Critic 的独立上下文仍有差别，实验结果按 review mode 分组。

在线协议为 `lha-qualitative-review-v1`。旧固定“选事件→12段→五维评分→长短专项”属于历史 `event_review` 路径，当前在线运行不再调用。正式终评独立选择证据并评分，见 [评价说明](low-high-evaluation-v2.md)。

操作见 [观察指南](../knowledge/creative-loop/OBSERVE_EVENTS.md)，实现见 [共享观察器](../src/planner_harness/event_observation.py)、[原生解码](../src/planner_harness/video.py)、[Critic 循环](../src/critic_harness/qualitative.py)。当前回归为 `test_review_modes`、`test_loop_engineering`；旧 `test_online_event_selection` 保留历史选片协议断言。
