# Bernini-R: concrete style expression in the October 29 probe

[Knowledge map](../README.md) · [Experience synthesis](../guides/experience.md) · [From knowledge to a proposal](../guides/design-expression.md) · [Reading manual](../READING.md)

Evidence status: synthesis of an existing exploratory run and its recorded reviews. This page adds no new generation or model evaluation. Its current operational use concerns style expression; semantic-preservation strategies are deferred.

## Run conditions

The probe used the official Bernini renderer with direct prompts and no legacy Planner. There were four source clips and ten conditions, one independent generation per condition with seed 42. The model was `ByteDance/Bernini-R-1.3B-Diffusers`, revision `ff4c5d4d2d31365c2ffeb30e9753065ee18f58ce`: 40 inference steps, `v2v_apg`, maximum image size 848, empty negative prompt, and prompt enhancer disabled.

Eight main-set deliveries are five seconds, 100 frames at 20 fps. The two table-tennis deliveries are approximately 4.43 seconds, 133 frames at 30 fps. Native versus delivered frame counts and source-frame mapping are documented in the result records and [frame-mapping audit](../../out/prompt_probe/20261029_bernini/frame-mapping-audit.json). Per-condition `input.json` retains the prompt, system prefix, effective text, and token count. These records distinguish authored text from the actual text prepared for the model.

The primary reviews used GPT-6.1-sol with xhigh reasoning on 12 sampled frames per clip. The 041 paired review used six sampled frames per clip. [Evaluation provenance](../../out/prompt_probe/20261029_bernini/evaluation-provenance.json) records the execution hosts and review scope. Sampling supports appearance judgments and broad comparisons; exact continuous motion requires different evidence.

## What the existing results contribute

| Task and conditions | Recorded appearance | Implication for knowledge use |
|---|---|---|
| main/027: short, long, long_keep | The short etching label produced a recognizable etched image and added celestial/cloud forms. Detailed descriptions more closely specified black contours, hatching, ivory paper, and an open sky. | A label can activate a medium. Knowledge can refine its visible character and distribution across the image. |
| main/041: short, long, long_keep | The short storybook request remained largely photographic. Both detailed versions produced clear watercolor-and-pencil illustration. | Developing one interpretation into visible marks, colors, shadow treatment, and support texture is a useful direction for this model and task. |
| fewshot/004: long, long_keep | Both versions produced a space-station environment, Earth view, and technical clothing. Blue glow appeared mainly on the lower table supports. | Overall setting and clothing can work while a local effect lands on a different part. Name the intended part clearly when developing the proposal; a wording fix remains untested. |
| main/024: long, long_keep | Both versions produced substantial glitch treatment. The additional-clause version was judged to have more complete RGB separation. | The prompt's described effects provide an inspectable visual direction. This comparison offers no isolated test of effect vocabulary or clause order. |

The synthesis draws on the individual judgments, the existing [comparison page](../../out/prompt_probe/20261029_bernini/comparison.html), and [review notes](../../out/prompt_probe/20261029_bernini/review_notes.json). The latter two are original historical artifacts in their original language; this English working record supplies navigation and a scoped interpretation.

The useful finding is that concrete visual elaboration helped express the chosen styles in these runs. Longer prompts also contained more information, so the experiment leaves their separate contributions unresolved. Storybook watercolor is one interpretation of a broad label; the short request did not itself demand its pastel palette. The 027 result shows that short labels can also work.

## Guidance available to a Planner

Use medium and design knowledge to develop a coherent visible interpretation. Describe relevant relationships: pencil visible through a transparent wash, hatching building darker foliage, light emitted by a particular surface, or RGB separation affecting a specified image region. Select details because they contribute to the current design. The [application guide](../guides/design-expression.md) demonstrates this with complete-source reading paths.

The experiment motivates explicit object, part, and region wording as a clarity measure. Its table-tennis results also show why a well-specified intention and an achieved placement need separate records. The new tabletop-rim sentence in the application guide is a candidate for later testing, with its untested status kept alongside it.

Prompt order, optimum length, compulsory opening scene descriptions, fixed word counts, and a universal style vocabulary were not isolated in this probe. This record provides conditional guidance that a later expression interface can consult; it supplies no mandatory prompt template. Source materials and user requests continue to determine the design content.

## Boundaries of this evidence

The ten conditions were independent single outputs, with no repeated seeds or multi-round refinement. The results concern this Bernini model revision and setup. The separate Ditto smoke test provides no corresponding style-quality conclusion.

The `long_keep` inputs and their reviews remain available below for accurate provenance. The table-tennis `long` input already contains preservation wording. Their comparison is therefore an addition of further clauses. Semantic outcomes remain in the original records; this revision does not derive a preservation recipe from them. The [041 paired review](../../out/prompt_probe/20261029_bernini/041-paired-review.json) supersedes the earlier apparent object-preservation advantage: both illustrated variants simplified the implement and weakened the notebook's construction.

## Evidence chain and complete inputs

[Case definitions and settings](../../out/prompt_probe/20261029_bernini/cases.json) · [Preflight](../../out/prompt_probe/20261029_bernini/preflight.json) · [Run summary](../../out/prompt_probe/20261029_bernini/run-summary.json) · [Local output verification](../../out/prompt_probe/20261029_bernini/local-output-verification.json) · [Renderer script](../../scripts/deploy/run_prompt_probe.py) · [Review script](../../scripts/deploy/judge_prompt_probe.py)

The following condition index and verbatim prompts are assembled from `cases.json`. Each input record provides the effective text; each result record provides delivered duration and output hash; each judgment supplies the recorded interpretation. Prompts are historical experimental inputs, including any imperative clauses they contain.

| Condition | Source | Actual input | Output and metadata | Recorded review |
|---|---|---|---|---|
| `027__short` | [Source](../../benchmark_data/main/027/027.mp4) | [Input](../../out/prompt_probe/20261029_bernini/027__short/input.json) | [Video](../../out/prompt_probe/20261029_bernini/027__short/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/027__short/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/027__short/judgment.json) |
| `027__long` | [Source](../../benchmark_data/main/027/027.mp4) | [Input](../../out/prompt_probe/20261029_bernini/027__long/input.json) | [Video](../../out/prompt_probe/20261029_bernini/027__long/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/027__long/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/027__long/judgment.json) |
| `027__long_keep` | [Source](../../benchmark_data/main/027/027.mp4) | [Input](../../out/prompt_probe/20261029_bernini/027__long_keep/input.json) | [Video](../../out/prompt_probe/20261029_bernini/027__long_keep/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/027__long_keep/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/027__long_keep/judgment.json) |
| `041__short` | [Source](../../benchmark_data/main/041/041.mp4) | [Input](../../out/prompt_probe/20261029_bernini/041__short/input.json) | [Video](../../out/prompt_probe/20261029_bernini/041__short/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/041__short/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/041__short/judgment.json) |
| `041__long` | [Source](../../benchmark_data/main/041/041.mp4) | [Input](../../out/prompt_probe/20261029_bernini/041__long/input.json) | [Video](../../out/prompt_probe/20261029_bernini/041__long/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/041__long/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/041__long/judgment.json) |
| `041__long_keep` | [Source](../../benchmark_data/main/041/041.mp4) | [Input](../../out/prompt_probe/20261029_bernini/041__long_keep/input.json) | [Video](../../out/prompt_probe/20261029_bernini/041__long_keep/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/041__long_keep/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/041__long_keep/judgment.json) |
| `fewshot_004__long` | [Source](../../benchmark_data/fewshot/004/004.mp4) | [Input](../../out/prompt_probe/20261029_bernini/fewshot_004__long/input.json) | [Video](../../out/prompt_probe/20261029_bernini/fewshot_004__long/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/fewshot_004__long/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/fewshot_004__long/judgment.json) |
| `fewshot_004__long_keep` | [Source](../../benchmark_data/fewshot/004/004.mp4) | [Input](../../out/prompt_probe/20261029_bernini/fewshot_004__long_keep/input.json) | [Video](../../out/prompt_probe/20261029_bernini/fewshot_004__long_keep/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/fewshot_004__long_keep/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/fewshot_004__long_keep/judgment.json) |
| `024__long` | [Source](../../benchmark_data/main/024/024.mp4) | [Input](../../out/prompt_probe/20261029_bernini/024__long/input.json) | [Video](../../out/prompt_probe/20261029_bernini/024__long/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/024__long/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/024__long/judgment.json) |
| `024__long_keep` | [Source](../../benchmark_data/main/024/024.mp4) | [Input](../../out/prompt_probe/20261029_bernini/024__long_keep/input.json) | [Video](../../out/prompt_probe/20261029_bernini/024__long_keep/edited.mp4), [result](../../out/prompt_probe/20261029_bernini/024__long_keep/result.json) | [Judgment](../../out/prompt_probe/20261029_bernini/024__long_keep/judgment.json) |

### Verbatim experiment prompts

<details>
<summary>027__short: original prompt</summary>

```text
Make it look like a 19th-century etching.
```

</details>

<details>
<summary>027__long: original prompt</summary>

```text
Render the tree-lined town skyline as a 19th-century etching, with crisp black ink on lightly aged ivory paper. Define rooftops, domes, and towers with fine contour lines, and build the shaded foliage with dense crosshatching. Replace all color with monochrome tones, leaving the bright sky mostly unmarked for contrast.
```

</details>

<details>
<summary>027__long_keep: original prompt</summary>

```text
Render the tree-lined town skyline as a 19th-century etching, with crisp black ink on lightly aged ivory paper. Define rooftops, domes, and towers with fine contour lines, and build the shaded foliage with dense crosshatching. Replace all color with monochrome tones, leaving the bright sky mostly unmarked for contrast. Preserve the skyline layout, the shapes and relative positions of the rooftops, domes, towers, and tree masses. Preserve the original camera movement. Change their rendering into ink and paper without adding, removing, or relocating buildings.
```

</details>

<details>
<summary>041__short: original prompt</summary>

```text
Make it look like a children's storybook.
```

</details>

<details>
<summary>041__long: original prompt</summary>

```text
Transform the bright scene of a man writing beside a woman into a children’s storybook illustration, using warm pastel colors and soft pencil outlines. Render his blue striped shirt, her white blouse, the notebook, and the tabletop with gentle watercolor washes, softened shadows, and subtle paper texture.
```

</details>

<details>
<summary>041__long_keep: original prompt</summary>

```text
Transform the bright scene of a man writing beside a woman into a children’s storybook illustration, using warm pastel colors and soft pencil outlines. Render his blue striped shirt, her white blouse, the notebook, and the tabletop with gentle watercolor washes, softened shadows, and subtle paper texture. Keep the same two people in their original positions. Preserve the man writing in the notebook and the woman standing beside him with her original hand contact on his shoulder. Keep the pen, notebook, and tabletop in their original spatial relationships. Preserve their movements and the camera motion while rendering the scene as an illustration.
```

</details>

<details>
<summary>fewshot_004__long: original prompt</summary>

```text
Transform the room into a futuristic space-station sports arena with metallic walls, blue-white lighting, and Earth visible through large windows. Dress the players in sleek sci-fi athletic suits and give the table glowing blue edges. Preserve faces, playing motions, ball trajectory, table geometry, and camera movement.
```

</details>

<details>
<summary>fewshot_004__long_keep: original prompt</summary>

```text
Transform the room into a futuristic space-station sports arena with metallic walls, blue-white lighting, and Earth visible through large windows. Dress the players in sleek sci-fi athletic suits and give the table glowing blue edges. Preserve faces, playing motions, ball trajectory, table geometry, and camera movement. Keep the same two players on their original sides of the table. Preserve the sequence of their paddle swings, the visible ball motion, and the shape and placement of the table and net throughout the rally. Change the setting and clothing while retaining the original player interactions and camera movement.
```

</details>

<details>
<summary>024__long: original prompt</summary>

```text
Transform the man’s phone call in the beige leather car interior into digital glitch art, with high-contrast shadows and RGB color separation across his navy suit, seats, and window reflections. Apply horizontal pixel shifts, fragmented blocks, and flickering scan-line textures across the entire frame, with distorted color highlights.
```

</details>

<details>
<summary>024__long_keep: original prompt</summary>

```text
Transform the man’s phone call in the beige leather car interior into digital glitch art, with high-contrast shadows and RGB color separation across his navy suit, seats, and window reflections. Apply horizontal pixel shifts, fragmented blocks, and flickering scan-line textures across the entire frame, with distorted color highlights. Keep the same man holding the phone to his ear inside the car. Preserve his original head, mouth, and hand movements and their order. Preserve the arrangement of the man, phone, seats, and windows. Apply the requested glitch distortions while keeping these scene elements and the phone-call action recognizable.
```

</details>

