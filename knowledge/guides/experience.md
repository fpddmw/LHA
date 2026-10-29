# The conditions behind generation experience

[Knowledge map](../README.md) · [Video meaning](meaning.md) · [Reading manual](../READING.md) · [Integration design](../INTEGRATION.md)

This guide synthesizes existing repository reviews, experiment descriptions, and source-code comments. The reorganization checked those records and their sources; it did not rerun the historical videos or recompute all metrics. The records explain earlier changes of direction and identify information worth retaining for inspection in the new architecture.

## What kinds of freedom have already been tried?

The [bench_v2 handoff](../../_deprecated/eval/bench_v2/HANDOFF.md) and [three-case prompt review](../../_deprecated/eval/bench_v2/data/walkthrough_notes.json) describe different paths. In v1, the Planner rewrote the expert instruction and replaced it. In v2, the expert's original text was combined with fixed technique and preservation clauses; the default path did not actually use the Planner's proposal. A later planning track combined a one-sentence intent with a model proposal, alongside a `plan_only` composition. These paths differed in available information, the model's task, and the text eventually submitted.

The later [domain cards](../../scripts/eval/bench_v3/skills_v3.py) already proposed giving writers knowledge to understand before writing a short specification. They explored visible-region restrictions, strong replacement through `decisive`, and `execution_only` variants. The new system's contribution must therefore come from richer semantic relationships, more explorable knowledge, and traceable autonomous selection. Renaming templates as knowledge cards would leave the earlier problems unresolved.

## Where did the recorded failures occur?

| Repository observation | Conditions and interpretation | Source |
|---|---|---|
| v1 expanded expert requests, dropping some preservation conditions and adding details | Rewriting a precise proposal introduced semantic drift. The original request, generated proposal, and actual submitted text need distinct records. | [HANDOFF §2.4](../../_deprecated/eval/bench_v2/HANDOFF.md) |
| The 0531 old-video task acquired cabinet replacement and cinematic lighting | An imaging change expanded into content changes. The phrase “silver-haired” also triggered jewelry language, illustrating the difference between contextual understanding and keyword assembly. | [walkthrough: heldout1000_0531](../../_deprecated/eval/bench_v2/data/walkthrough_notes.json) |
| The 0526 historical-costume edit also included preservation of the original clothing outline and coverage | A requested change and a generic preservation clause can work against each other. The record also reports a final prompt of 564 tokens. | [walkthrough: heldout1000_0526](../../_deprecated/eval/bench_v2/data/walkthrough_notes.json) |
| The 0236 case outperformed direct prompting on a comparison but changed the video very little | Source preservation and fulfillment of the requested edit describe different outcomes. Both the content and extent of change matter. | [walkthrough: heldout1000_0236](../../_deprecated/eval/bench_v2/data/walkthrough_notes.json) |
| Domain-card comments report invisible-region detail and vocabulary causing target drift | Terminology can improve specificity while introducing assumptions absent from the user's information. Percentages and scores in those comments remain claims about their historical runs. | [Original skills_v3 comments](../../scripts/eval/bench_v3/skills_v3.py) |

These observations concern both generated content and its surrounding process. A broad request gives a model room to propose a design. If evaluation instead expects exact colors or objects absent from the input, target similarity also measures agreement with an undisclosed answer. The knowledge system should make this information gap understandable and keep user requirements, source-video observations, and model proposals distinguishable.

## Execution and recording can change what happens after text generation

The handoff describes a 512-token text window in the relevant Wan path, where some historical prompt endings were truncated. The order of long prompts, preservation clauses, and model proposals affected what the model received. A later [LESSONS](../../LESSONS.md) entry corrected a record-interpretation error: `compiled_edit_prompt` contained combined text. Treating it as the raw proposal had produced the incorrect claim that “50/50 plans were truncated.” Reading the history requires both the earlier diagnosis and its subsequent correction.

LESSONS also records that some agent arms silently used the source's first frame as a VACE reference while the direct arm did not. Some output differences therefore involved both text and control inputs. A future harness should retain the connections between the request, source observations, knowledge reads, model proposal, submitted text, and actual controls. Experience such as “short sentences work better” also needs the corresponding execution model and experimental conditions. The ongoing instruction experiments will determine applicable expression patterns; this corpus introduces no new universal length or sentence rule.

## What do the evaluation records tell us?

[LESSONS](../../LESSONS.md) records opposing fidelity and quality preferences from two bench_v3 judges on one-sentence intent tasks, with greater agreement on preservation. Target-derived reference images also served as an information-leaking upper bound. The historical [bench_v4 description](../../scripts/bench_v4/README.md) subsequently moved toward deterministic compilation and primary metrics without LLM judges, documenting different changes in target-related metrics, preservation, and aesthetics for the grounded approach.

These records support interpreting request fulfillment, changes to source meaning, image quality, target similarity, and temporal consistency separately, while checking what information each evaluation actually received. They leave the general value of open model-led design unresolved. The immediate contribution to examine is more accurate task understanding, meaningful knowledge comparison, and attributable design decisions. Later Planner and generation tests will measure whether those changes improve video results.

## The October 29 direct Bernini probe

The [Bernini-R experience record](../model-experience/bernini-r.md) adds four source clips and ten direct-prompt conditions, with complete input, output, and review links. Detailed visual descriptions produced a clear pencil-and-watercolor interpretation in 041 where the short storybook request remained largely photographic. The short etching label already worked, while elaboration specified its line work, paper, and sky more closely. Table-tennis outputs achieved much of the space-station setting while putting blue glow mainly on lower supports.

These observations give the knowledge work a concrete focus: help the model develop a style into visible relationships and state relevant locations clearly. Length and information content covaried; the new tabletop-rim wording remains untested. The [application guide](design-expression.md) connects those conditional findings to complete source reading and new authored proposals. Semantic-preservation strategies remain deferred, with the original results available for later work.

## Where different kinds of material remain available

- **The 98 OPUSCAR entries** retain the original author's complete designs, shots, and prompts. Their production context is code and three-dimensional rendering. Specific Avoid lists are author advice; the old converter's `common_failure_modes` field adds no experimental evidence to those lists.
- **The 13 base templates** preserve world proposals and material directions. Many lack shots or supporting experiments. Their complete pages explain these gaps.
- **The 5 domain references** preserve visible-region guidance, terminology, and three card variants. Their editorial readings explain the original cards' assumed editing scope and choices. See the [domain-reference index](../README.md#domain-references).
- **This guide and the source map** explain historical observations and their conditions. [source-map.json](../source-map.json) records hashes for key source files so later changes can be detected.

Future experience becomes useful when it records the task and model conditions, the interpretation or design adopted, what was actually submitted, what happened, and where the evidence is. New proposals can remain in run records. Adding them to persistent knowledge requires the project's authorized review. This provides comparable experience while retaining the conditions of each observation.

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
