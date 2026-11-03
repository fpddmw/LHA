---
name: lha-video-review
description: Inspect a newly generated LHA video against the user task, actual prompt and relevant source, input and references; provide a qualitative review or Planner self-review.
---

Check what the generated video actually achieves for the original task. The task
recasts the source moment into the requested world or medium: the moment should stay
recognizable while the visible scene is rebuilt, and the sequence should be stable and
clean. Read the actual generation prompt as process context; it does not replace the
user's goal.

Look in this order, and report each as description:
1. Regions or intervals that remain source-like (background, ground, sky, props, the
   first and last second).
2. Focal faces, hands, held props and contacts: who they are, whether each source
   person is still one person, and what is happening at each contact.
3. Medium switches: places where the look changes between photographic and the target
   medium, or where the light or style flips across a cut, a camera move or an occlusion.
4. Each item the request names (for a detailed request) or the intended transformation
   and its scene-level coordination (for a short request).

A strong overview or opening can hide a failure in any of these. Describe what is seen;
leave scoring and rewrites to the caller.

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
