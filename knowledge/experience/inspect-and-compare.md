# Inspect and compare results

[Experience map](README.md) · [Meaning](../guides/meaning.md) · [Generation history](../guides/experience.md)

Version 1. The inspection recommendations are common-sense starting guidance. Historical review disagreements and sampling limits have linked evidence. These pages do not define a replacement evaluation metric or a compulsory review phase.

## Look where an uncertainty can change the next action

When a potentially important defect is unclear, inspect the relevant region or time interval before spending another generation on it. Use the original to understand the user's source, and generated candidates to understand their current states. A crop can clarify object structure; observations across time can clarify progression. Neither a single still nor sparse samples establish an exact fast trajectory.

Video identity and timing matter. Different frame rates, cropping or resampling can make equally numbered frames depict different moments. Use recorded mappings when available. If alignment or motion evidence is insufficient, retain uncertainty rather than inventing a precise difference.

## Compare alternatives around the same question

When two candidates trade advantages, compare them against the original request using consistent observations. The user's requirements, the Planner's optional additions and the evaluator's observations are different kinds of information. Failure to realize an optional design flourish may justify dropping it; a missed user requirement deserves a different response.

Keep useful alternatives available. Stronger style may conceal changes that remain difficult to inspect. A plausible explanation of a defect is a hypothesis until the available evidence distinguishes it from alternatives. Seeing a failure does not by itself locate its cause in wording, sampling or model capability.

## Use external evaluation with its evidence scope

An evaluator can supply observations and measurements the Planner should consider. Preserve its identity, protocol and uncertainty. A score summarizes its particular questions and evidence; the next action can require looking at the underlying finding. The separately maintained evaluation implementation determines its metrics. The Planner need not fill an evaluation card or decide a universal score threshold before acting.

The [041 paired review](../../out/prompt_probe/20261029_bernini/041-paired-review.json) did not confirm an earlier apparent preservation improvement. Both illustrated versions weakened the implement/notebook construction. The [Bernini record](../model-experience/bernini-r.md) also explains why sampled frames did not establish precise motion. These observations motivate comparison with consistent evidence and explicit unknowns; they do not prove that every generated result needs an identical evaluation sequence.

## Decide whether another observation is worth it

Inspect more when a plausible answer would change the plan, input or final selection. Finish an observation when it has answered that question sufficiently for the task. A simple local edit may need little investigation. A consequential ambiguity may justify a closer look or external evaluation. There is no fixed frame or reading quota in this advice.
