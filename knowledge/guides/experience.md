# What earlier generation experiments teach the current design

[Knowledge map](../README.md) · [Video meaning](meaning.md) · [Current reading manual](../creative-loop/READING.md) · [Experience entrance](../experience/curated/README.md)

Earlier runs expose three recurring design problems: expanding the user's request while rewriting it, combining instructions that pull in opposite directions, and interpreting outcomes without checking the actual renderer input. This guide derives practical reading and design judgments from those records. The historical observations retain their original protocols; this synthesis adds no new generation or scoring results.

## What kinds of freedom have already been tried?

The [bench_v2 handoff](../../_deprecated/eval/bench_v2/HANDOFF.md) and [three-case prompt review](../../_deprecated/eval/bench_v2/data/walkthrough_notes.json) describe different paths. In v1, the Planner rewrote the expert instruction and replaced it. In v2, the expert's original text was combined with fixed technique and preservation clauses; the default path did not actually use the Planner's proposal. A later planning track combined a one-sentence intent with a model proposal, alongside a `plan_only` composition. These paths differed in available information, the model's task, and the text eventually submitted.

The later [domain cards](../../scripts/eval/bench_v3/skills_v3.py) already proposed giving writers knowledge to understand before writing a short specification. They explored visible-region restrictions, strong replacement through `decisive`, and `execution_only` variants. Give source knowledge a concrete job in the proposal: clarify the event, distinguish alternative visual constructions or resolve a material relationship. The benefit to test is whether those choices improve the actual output. Access to more terminology alone leaves the earlier scope and composition problems intact.

## Where did the recorded failures occur?

| Repository observation | Conditions and interpretation | Source |
|---|---|---|
| v1 expanded expert requests, dropping some preservation conditions and adding details | Rewriting a precise proposal introduced semantic drift. The original request, generated proposal, and actual submitted text need distinct records. | [HANDOFF §2.4](../../_deprecated/eval/bench_v2/HANDOFF.md) |
| The 0531 old-video task acquired cabinet replacement and cinematic lighting | An imaging change expanded into content changes. The phrase “silver-haired” also triggered jewelry language, illustrating the difference between contextual understanding and keyword assembly. | [walkthrough: heldout1000_0531](../../_deprecated/eval/bench_v2/data/walkthrough_notes.json) |
| The 0526 historical-costume edit also included preservation of the original clothing outline and coverage | A requested change and a generic preservation clause can work against each other. The record also reports a final prompt of 564 tokens. | [walkthrough: heldout1000_0526](../../_deprecated/eval/bench_v2/data/walkthrough_notes.json) |
| The 0236 case outperformed direct prompting on a comparison but changed the video very little | Source preservation and fulfillment of the requested edit describe different outcomes. Both the content and extent of change matter. | [walkthrough: heldout1000_0236](../../_deprecated/eval/bench_v2/data/walkthrough_notes.json) |
| Domain-card comments report invisible-region detail and vocabulary causing target drift | Terminology can improve specificity while introducing assumptions absent from the user's information. Percentages and scores in those comments remain claims about their historical runs. | [Original skills_v3 comments](../../scripts/eval/bench_v3/skills_v3.py) |

## Apply the historical distinctions to a new proposal

A precise user design deserves faithful interpretation before enrichment. For an imaging request such as aged home video, prioritize grain, tonal response, exposure and viewing character; introduce new furniture only when the task calls for a changed setting. For historical clothing, interpret preservation around the person's role, action and requested identity, allowing the silhouette to change as the new garment requires. Generic preservation wording can otherwise oppose the edit itself.

When an added source detail changes the task's scope, decide whether that change helps the user's goal. A familiar keyword is insufficient: the historical silver-haired/jewelry mismatch illustrates how a surface association can displace the intended person description. Read the complete case or the actual scene to resolve that association.

An open request leaves legitimate design alternatives. Compare results against what the request specified and what the visible scene needs to remain intelligible. Exact colors or objects found only in a hidden target describe agreement with that target, a different question from whether the user's requested transformation succeeded.

## Execution and recording can change what happens after text generation

The handoff describes a 512-token text window in the relevant Wan path, where some historical prompt endings were truncated. The order of long prompts, preservation clauses, and model proposals affected what the model received. A later [LESSONS](../../LESSONS.md) entry corrected a record-interpretation error: `compiled_edit_prompt` contained combined text. Treating it as the raw proposal had produced the incorrect claim that “50/50 plans were truncated.” Reading the history requires both the earlier diagnosis and its subsequent correction.

LESSONS also records that some agent arms silently used the source's first frame as a VACE reference while the direct arm did not. Some output differences therefore involved both text and control inputs. In the current loop, use the saved prompt and render receipt to establish what was actually submitted, and the read trace to establish what knowledge was encountered. When comparing expression strategies, identify the renderer, supplied controls and changed prompt content. Those details determine whether a recommendation about length or phrasing transfers to the next task.

## What do the evaluation records tell us?

[LESSONS](../../LESSONS.md) records opposing fidelity and quality preferences from two bench_v3 judges on one-sentence intent tasks, with greater agreement on preservation. Target-derived reference images also served as an information-leaking upper bound. The historical [bench_v4 description](../../scripts/bench_v4/README.md) subsequently moved toward deterministic compilation and primary metrics without LLM judges, documenting different changes in target-related metrics, preservation, and aesthetics for the grounded approach.

These records support interpreting request fulfillment, changes to source meaning, image quality, target similarity, and temporal consistency separately, while checking what information each evaluation actually received. Read the fixed score dimensions separately when they imply different trade-offs. Strong preservation can accompany an unrealized edit, and a strong visual treatment can obscure an action. The Planner must weigh those findings against the request when selecting a result. Historical scores describe their own runs; new loop comparisons establish the effect of the current design.

## The October 29 direct Bernini probe

The [Bernini-R experience record](../model-experience/bernini-r.md) adds four source clips and ten direct-prompt conditions, with complete input, output, and review links. Detailed visual descriptions produced a clear pencil-and-watercolor interpretation in 041 where the short storybook request remained largely photographic. The short etching label already worked, while elaboration specified its line work, paper, and sky more closely. Table-tennis outputs achieved much of the space-station setting while putting blue glow mainly on lower supports.

These observations give the knowledge work a concrete focus: help the model develop a style into visible relationships and state relevant locations clearly. Length and information content covaried; the new tabletop-rim wording remains untested. The [application guide](design-expression.md) connects those conditional findings to complete source reading and new authored proposals. The preservation clauses in the probe had mixed outcomes. Check the visible object and action relationships directly when they affect the next decision; the presence of a clause is evidence of the instruction, not of the resulting preservation.

## Where different kinds of material remain available

- **The 98 OPUSCAR entries** retain the original author's complete designs, shots, and prompts. Their production context is code and three-dimensional rendering. Specific Avoid lists are author advice; the old converter's `common_failure_modes` field adds no experimental evidence to those lists.
- **The 13 base templates** preserve world proposals and material directions. Many lack shots or supporting experiments. Their complete pages explain these gaps.
- **The 5 domain references** preserve visible-region guidance, terminology, and three card variants. Their editorial readings explain the original cards' assumed editing scope and choices. See the [domain-reference index](../README.md#domain-references).
- **This guide and the source map** explain historical observations and their conditions. [source-map.json](../source-map.json) records hashes for key source files so later changes can be detected.

For current use, follow the [experience entrance](../experience/curated/README.md). New entries should explain a recognizable condition, why it changes the decision, the preferred response and the cases that constrain it. This historical guide supplies background; the maintained entries own specific renderer and revision recommendations. Batch maintenance follows the separate authoring and review Skills, with publication controlled by explicit approval.

## More complete material to explore

These entries extend the comparisons above. Each provides a complete reading edition, motivated cross-links, and source references.

| Material | Reading orientation |
|---|---|
| [087 \| Birdman: 3D Backstage Long Take](../entries/opuscar-087.md) | Backstage lights, doorways, and camera motion turn space into performance; the source retains both a long-take intention and a particular shot arrangement. |
| [Alien biomechanics: a shared logic for organic and artificial structures](../entries/base-alien_biomech.md) | Living walls, membranes, pulsing light, and biomechanical metal form a whole-world proposal with extensive strategy annotations. |
| [Wormhole portal: science fiction organized around a spatial event](../entries/base-wormhole_portal.md) | A ring device, event-driven light, and participants organize a proposed portal-opening scene. |
| [Chinese period settings: vocabulary, visible evidence, and historical card scope](../domain-references/chinese_period.md) | The original card supplies terms for headwear, clothing, sets, and light sources, while recording visible-region restrictions and their trade-offs. |
| [Western period and fantasy settings: specific materials and open world assumptions](../domain-references/western_period_fantasy.md) | Wool, linen, brocade, timber, stone, and practical lights provide one setting direction within a broad range of historical and fantasy possibilities. |
| [Science fiction and modern styling: technical vocabulary and world assumptions](../domain-references/sci_fi_modern.md) | Technical garments, panels, cables, and accessories offer local vocabulary; cyberpunk, clean laboratories, and biomechanical worlds have different organizing ideas. |
| [Whole-image appearance: the historical filter card and complete medium design](../domain-references/style_filter.md) | The original card describes style transfer through grading and texture; complete cases develop image construction, viewing apparatus, and motion. |
| [Nature and landscape: space, light, and human experience](../domain-references/nature_landscape.md) | The original card organizes sky, vegetation, distance, and aerial perspective; other cases add different times and viewing relationships. |
