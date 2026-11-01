# Renderer entrances

Draft navigation for the reviewed collection. Profiles point to explanations rather than repeat instructions. Exact per-output settings are in source extracts. These are development observations under historical versions.

## Bernini

The historical and new runs use Bernini-R 1.3B, 40-step `v2v_apg`, maximum image size 848, no prompt enhancer and an empty negative prompt. The new seven-task run preserves native time axes; older benchmark runs use their own recorded frame/fps setup. Seed, encoded text and model/code revisions remain in each receipt. Differences in tasks and reasoning effort also limit batch-to-batch comparisons.

- **Style labels and visible construction:** [style realization](entries/style-realization.md). Concrete relationships can determine an interpretation; a short etching label also worked.
- **Faces, roles and interactions:** [instance identity](entries/instance-identity.md), [activity relations](entries/activity-relations.md), [object continuity](entries/object-continuity.md). New people scenes broaden the old identity evidence; F006 and F004 supply counterexamples to blanket failure.
- **Environment and illumination:** [environment replacement](entries/environment-replacement.md), [lighting integration](entries/lighting-integration.md). Theme accents can succeed while the location stays ordinary. F001/F004 v1 show strong replacement is possible.
- **Local appearance and structure:** [part binding](entries/part-binding.md), [design conflict](entries/design-conflict.md). Emission on supports and occlusion by authored garments are different failures.
- **Revisions:** [input conditioning](entries/input-conditioning.md), [connected scope](entries/connected-scope.md), [realization change](entries/realization-change.md), [continuation value](entries/continuation-value.md). Stable continuation, actual gain and final choice remain separate.
- **Time:** [time binding](entries/time-binding.md). Costume persistence, expression timing and exact motion are not interchangeable evidence.

## Ditto

Historical setup: Wan2.1-VACE-14B with Ditto LoRA, 50 steps, CFG 5, LoRA alpha 1, tiled bf16, empty negative prompt, no enhancer. There is no new Ditto experiment in this pass. Independent scores referenced here are historical; most Ditto claims are online-review observations.

- On the shared table-tennis source, strong early environment change coexisted with face and eyewear changes: [environment replacement](entries/environment-replacement.md), [instance identity](entries/instance-identity.md).
- Costume ornament could succeed while collars/headwear structure failed; glitch-colored blocks could appear without confirmed displacement of scene content: [style realization](entries/style-realization.md), [realization change](entries/realization-change.md).
- A specified dome repair added another dome: [part binding](entries/part-binding.md). The same record does not justify a blanket candidate-editing prohibition.
- Warm palace skin and attempted color correction: [wanted state](entries/wanted-state.md), [lighting integration](entries/lighting-integration.md). Positive and negative wording were mixed with input and sampling changes.
- Source orientation and stylized architecture: [realization change](entries/realization-change.md), [continuation value](entries/continuation-value.md). Omission repair and task-relative significance require different judgments.

Transfer from one renderer, task or interface to another remains an explicit hypothesis. A profile supplies relevant evidence to inspect, not a capability whitelist or a fixed action policy.
