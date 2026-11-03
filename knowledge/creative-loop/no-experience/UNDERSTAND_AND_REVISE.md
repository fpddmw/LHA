# Interpret results and choose the next action

Compare the generated video with the original request, its actual editing input
and submitted prompt. Assess the requested transformation, recognizable source
moment, temporal behavior and visual quality using the evidence you can observe.
The [review guide](../../../.agents/skills/lha-video-review/SKILL.md) supports both
Critic review and Planner self-review.

Use findings to develop the next design. Decide which observations matter, how to
interpret them and what another attempt should do. You can inspect a video more
closely, read relevant style knowledge, take notes, select an input or generate.
The current intended delivery and the input for another render are separate choices.
All retained candidates remain available for comparison and final selection.

Follow the task's configured generation and delivery policy. Each submitted prompt
addresses the input selected for that attempt. Review the new result in its actual
context; another candidate can still be the better delivery.

In Critic mode, the reviewer returns descriptive evidence for the original task,
actual prompt, focus, source, input and candidate. In Planner mode, perform the
check in your task context. Evaluate those observations and their coverage yourself.
Use [complete-event observation](../OBSERVE_EVENTS.md) when the question needs
continuous evidence. Keep useful interpretation in notes/workspace. Delivery uses
the recorded per-generation checks and starts no additional review.
