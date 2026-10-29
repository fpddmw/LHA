# LHA full skill reorganization plan

Approval date: 2026-10-29.

User authorization, translated from Chinese: “Proceed with the full scope according to this plan, and save the plan first. When it is finished, show me how the knowledge map, comparative guides, and complete material connect.”

This phase delivers a knowledge package independent of the old Planner: complete material, comparative guides, reading entrances, source relationships, and integration guidance for a future Planner and harness. The [current design direction](skill-reorganization-discussion.md) provides its basis. Work proceeds across the full scope, followed by review of the complete result.

## Complete input scope

| Input | Treatment |
|---|---|
| 98 OPUSCAR records in `zyx/styles.json` and their 98 derived templates | Compare each pair and create 98 complete entries, preserving full prompts, 302 shots, direction notes, references, and links to 98 images; retain bilingual originals at their sources |
| 13 base templates | Create 13 reference entries, retaining specific design proposals and explaining available knowledge and gaps |
| 5 cards in `scripts/eval/bench_v3/skills_v3.py` | Create 5 domain references, distinguishing specialist content, original advice, and model experience; retain complete cards and the context of their variants |
| Dimension descriptions such as `src/skills/dimensions.py` | Retain terminology and historical rule provenance; explain the old purpose while allowing a new knowledge structure independent of those fields and routes |
| `LESSONS.md`, historical handoffs, relevant case reviews, and experiment descriptions | Supply conditional experience, cases, and sources for guides and entries, with evidence limits stated |

Historical synthesis uses existing repository records. Rerunning every historical video is outside this phase. Existing source templates, Planner runtime code, and another conversation's experiment files remain unchanged.

## Continuous work steps

### 1. Map all sources

Align original records, template IDs, images, and historical material in `source-map.json`. Every input has an explicit destination or supporting use. Each OPUSCAR original and its derived template belong to the same source chain.

### 2. Read and organize every entry

Read complete records and compare legacy templates, restoring content that was truncated, fragmented, or placed in a different context. Every entry contains an informative introduction, coherent design interpretation, complete source material, and onward links. Subject, medium, design, and shot relationships remain connected. The material determines the prose structure.

Curatorial synthesis, original author statements, and experimental observations are identified separately. Thin sources retain their knowledge gaps. Methods and validation claims require supporting material.

### 3. Complete six comparative guides

| Guide | Content |
|---|---|
| Video meaning and design possibilities | How object roles, events, relationships, time, and shots form meaning; design questions opened by different requests |
| Subject matter and visual language | Why cases use particular expressions, and how these serve subject, mood, and world assumptions |
| How different media form an image | Mechanisms and differences in painting, printing, photography, animation, and three-dimensional material |
| Composition, light, and time | Relationships among spatial arrangement, lighting, shots, editing, and rhythm |
| Combining styles and methods | Existing mixed designs, their relationships, differences, and tradeoffs |
| The conditions behind generation experience | Task, model, execution conditions, evidence status, and subsequent corrections |

Each guide supplies substantive explanations, comparisons, concrete cases, and further reading. The model can move across these topics in an order suited to its task.

### 4. Build the map and reading guidance

```text
knowledge/
  README.md
  entries/
  domain-references/
  guides/
  READING.md
  INTEGRATION.md
  source-map.json
```

`README.md` provides the map and complete catalog. Links explain what further reading contributes or compares. `READING.md` explains content status, reading depth, provenance, and knowledge use. `INTEGRATION.md` defines the browsing, search, complete reading, and citation capabilities needed by the new Planner, plus the boundary between task workspace and long-term knowledge. Runtime interfaces are subsequent work.

### 5. Check and deliver the complete package

Integrity checks cover all templates, records, cards, shots, original text, and links. Content review covers design context, judgments and evidence, generalization from cases, and substantive comparisons.

Programs support extraction, mapping, and integrity checks. Semantic prose is authored through reading and synthesis. Delivery demonstrates working paths from map to guide to complete entry and original source.

## Completion boundary

Deliver 111 complete entries, 5 domain references, 6 guides, the map, reading manual, integration design, source map, and a brief validation account. Readability, completeness, and provenance are checked in this phase. Actual Planner use and video improvements require later runtime evaluation.

## English working edition

On 2026-10-29, the user accepted the current form and authorized systematic conversion to English. The subsequent clarification keeps user-facing conversation in Chinese and repository working content in English.

This pass covers the entire accepted knowledge package and its current planning documents: navigation, editorial readings, comparison reasons, guides, the reading manual, integration design, manifests, and validation. Stable IDs and relationships retain their meaning. Existing English source text is reproduced exactly; Chinese-only template values receive explicitly identified English reading editions. Original-language source files remain intact for provenance and historical reproducibility.

English is the working language for the planned Planner's operational guidance, tool-facing material, visible task notes, design proposals, and prompt drafts. Original user input retains its provenance. The next discussion will address the broader harness, reflection and evaluation, and the agent loop.

## Execution status

The approved plan was saved first, followed by the full knowledge reorganization. The initial [knowledge map](../knowledge/README.md) connected all 111 complete entries, 5 domain references, and 6 guides with reading, integration, and source documentation. The approved application revision below adds a seventh guide and one model-experience record.

The English working edition covers the same full package. Its [validation account](../knowledge/VALIDATION.md) records language, completeness, source preservation, and navigation checks. Runtime integration, prompt-expression experiments, and the generation feedback loop remain subsequent work. Completion of the content and checks does not imply that the user has reviewed every curatorial judgment.


## Approved style-application revision

The user subsequently deferred semantic-preservation prompting because the Bernini experiment did not establish a reliable wording strategy, then authorized correction of the skill and knowledge system. This is a content revision of the accepted architecture.

The authorized work is to review all 111 entry editorials and 5 domain references, deepen useful explanations of visual mechanisms and their applicability, improve the reading manual, add an application guide using benchmark main/041 and fewshot/004, and connect the existing Bernini probe as conditional model experience. Existing source material and complete cases remain attributed and intact. English continues as the repository working language.

The revision retains model-led interpretation and creative selection. Knowledge supports relationships and alternatives; original example aesthetics remain particular choices. The application guide distinguishes authored walkthroughs and untested new wording from the actual experiment inputs and outputs.

The implementation enriches 35 of the 111 entry editorials and 2 of the 5 domain editorials after reviewing the full set; the remaining editorials retain their existing explanations. Four existing guide bodies gain application or experience connections. The new guide, manual, map, and source map provide paths from a task question to complete material and experiment evidence. The integrity checks cover the original package as well as the ten probe inputs, source/output media hashes, and new navigation.

Runtime Planner and harness implementation, semantic-preservation strategies, new evaluation calibration, generation experiments, and the agent loop remain subsequent work. Current content revision and source checks do not establish improved video performance.
