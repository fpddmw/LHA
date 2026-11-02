# Shared operating reference

These are common tool semantics for both experience conditions. The runtime supplies a broad phase reminder and whether generation is available. The phase schedule is an engineering convention. It does not predict render duration. Once generation is unavailable, observation, reading and delivery remain available until the deadline. At the deadline the runtime freezes the task. The last intended candidate is retained, or a latest-generated fallback is marked explicitly; a fallback does not claim a pending review completed or a Planner confirmation.

Every successful generation is checked under `review.mode`: `critic` is the default,
while `planner` records the check in the current Planner context. Supply overall
focus, extra questions, event locations or an alternative with `review_focus`.
Both modes use the same overview, native consecutive-frame pages, crops and saved
observations. Describe the useful outcome and consequential findings with concrete
evidence. For short tasks, consider the intended transformation, style/world and
scene-specific coordination. For detailed tasks, check requested objects,
attributes and relations together. The Planner chooses the final candidate using
these checks; delivery starts no additional review.

Bernini accepts concrete English within its encoder capacity. Capacity and input validation happen before dispatch. An invalid unsubmitted request has no generation charge. A dispatched failed attempt is charged once; recovery of the same request is not another attempt. An unknown request keeps its original reservation. Use the action manual for exact arguments and the complete-event guide for frame pagination.

The single-call Planner comparison sees eight source frames and the original request, writes one rendering prompt, and has no knowledge search or generated-output review. Loop-first includes the loop's observations and tool affordances before its first render; these are distinct experimental conditions.
