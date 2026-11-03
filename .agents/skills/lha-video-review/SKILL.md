---
name: lha-video-review
description: Inspect a newly generated LHA video against the user task, actual prompt and relevant source, input and references; provide a qualitative review or Planner self-review.
---

Check what the generated video actually achieves for the original task. The task
recasts the source moment into the requested world or medium: the moment should stay
recognizable while the visible scene is rebuilt, and the sequence should be stable and
clean. Report which regions or intervals remain source-like, and inspect focal faces,
hands, held props, contacts and the final second closely. Read the
actual generation prompt as process context; it does not replace the user's goal.
For short requests, consider the intended transformation, style/world and concrete
coordination of the scene. For detailed requests, check requested objects,
attributes, relations and whether they hold together.

Start from the supplied overview. Use the shared `observe` tool when motion,
a small feature, an input/output contrast or a reference needs a closer look.
`mode: continuous` reads native consecutive frames; follow `next_arguments` for
another page, use `crop` for a region, or reopen an observation by its ID. Choose
what helps the judgment; there is no required frame or page count.

Lead with the useful outcome, then consequential strengths, defects and evidence.
Describe concrete observations and evidence; inspect the relevant interval when
needed. Attribute an earlier reviewer's observations when you use them.
Use concise professional prose.

As Critic, return evaluation and evidence, with no prompt rewrite or next-action
advice. You can request `observe`, retain a brief `note`, or return
`review` with a nonempty `summary` and optional `findings` (ordinary text or
objects with evidence references). As Planner, include the current candidate's
`review: {video_id, summary, findings?}` beside your next action, or use a separate
`review` action. Keep your task context and choose the next input, prompt or final
candidate yourself. Every successful generation is checked, including the last.
