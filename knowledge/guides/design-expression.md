# From knowledge to a visual proposal

[Knowledge map](../README.md) · [Reading manual](../READING.md) · [Media](media.md) · [Combination](combination.md) · [Bernini experience](../model-experience/bernini-r.md)

Knowledge becomes useful when it helps the model explain what a proposed image will look like and why its elements belong together. Complete cases supply relationships among subject, material, form, light, and time. The model selects and adapts those relationships to the current request, developing its own proposal where the request leaves choices open.

This guide contains two authored walkthroughs using real tasks from the October 29 Bernini probe. The reading paths and new draft prompts below were written during knowledge curation; they are not records of an autonomous Planner run. The actual probe used direct prompts without this knowledge package. Its results provide conditional experience about style expression. Semantic-preservation strategies are deferred in this revision.

## Make a visual direction concrete

A style name locates a field of possibilities. A proposal develops a particular interpretation through visible relationships. Watercolor, for example, can involve transparent color through which pencil remains visible, unpainted paper supplying light, or loose color deliberately displaced from ink. Those choices create different appearances. Reading [053](../entries/opuscar-053.md), [063](../entries/opuscar-063.md), and [024](../entries/opuscar-024.md) makes the differences available for judgment.

Useful specificity explains the result. It can describe how a mark follows a form, how a surface receives light, where a color or texture belongs, or how an effect develops over time. Names, production vocabulary, and numerical settings are worth carrying into a proposal when they clarify that appearance. Source-specific palettes, plot events, timing, and proportions remain choices to interpret in the new task.

The [Bernini record](../model-experience/bernini-r.md) supports trying concrete visual elaboration: the detailed storybook prompt produced a clear illustration where the short label remained largely photographic. The etching label already produced a recognizable medium, while elaboration more closely specified its line work, paper, and sky. Prompt length and information content changed together. The practical direction is to develop useful visual content; a universal word count, sentence order, or named-style formula remains unestablished.

## Benchmark main/041: an open storybook request

The [source clip](../../benchmark_data/main/041/041.mp4) shows a man writing beside a woman in a bright room. His blue striped shirt, her white blouse, and the writing surface offer concrete places to express an illustration treatment. Their social relationship need not be invented to make this visual decision. `main/041` is the benchmark identifier; [OPUSCAR 041](../entries/opuscar-041.md) is an unrelated theater case.

The actual short request was:

> Make it look like a children's storybook.

This leaves the illustration method open. Warm pastel watercolor and soft pencil are the probe author's interpretation of that request. A new Planner can use that interpretation as evidence-bearing inspiration or develop another appropriate one.

### Read to understand a choice

The [media guide](media.md#paper-and-pigment-participate-in-form) introduces differences between transparent washes, opaque color masses, and the relationship between line and color. Follow [053: transparent watercolor](../entries/opuscar-053.md) for paper white, layered glazes, and differentiated wet and dry handling. Follow [063: pencil and watercolor](../entries/opuscar-063.md) for pressure-varied pencil visible through color.

Read their complete original explanations and prompts to see the dependencies. In 053, reserved paper supplies the light and successive smaller glazes develop darker forms. In 063, the underdrawing remains visible because the washes are transparent. This pairing offers a coherent mechanism for drawn contours and gentle color sharing the same image.

Their source contexts also matter. The autumn palette and sadness of 053, and the prairie, journal annotations, magic-hour colors, and opening color-arrival sequence of 063, belong to those complete designs. For this walkthrough, the model borrows the relationship between paper, pencil, and wash, then chooses a bright interior interpretation. [024](../entries/opuscar-024.md) offers a nearby alternative: energetic ink and displaced color. That comparison explains a genuine artistic choice rather than supplying more adjectives for the same prompt.

### Develop the proposal

One possible direction is a bright, intimate illustrated scene: warm, lightly textured paper carries transparent pastel washes; fine pencil lines remain visible through them; the clothing and tabletop share the same medium. Softer shadows support the chosen lightness. The model selects this direction for the current scene and request. The source cases explain how the marks and surfaces can work together, while the warm pastel emphasis is also present in the successful probe condition.

| Design element | Basis | Use in this proposal |
|---|---|---|
| Paper supplies bright areas | OPUSCAR 053 | Let pale paper show through light areas of the illustrated scene |
| Pencil remains visible through color | OPUSCAR 063 | Connect contours and transparent washes across figures and objects |
| Warm pastels and softened shadows | Actual 041 long-prompt condition | Adopt this tested visual direction as one plausible storybook interpretation |
| No journal frame or new drawing-on sequence in this example | Current design choice | Focus this proposal on the appearance of the existing scene |

An illustrative English expression of that proposal is:

```text
Render the man writing beside the woman as a children's storybook illustration. Use transparent warm pastel watercolor washes over fine, pressure-varied pencil lines, with pale textured paper showing through the light areas. Apply the same pencil-and-wash treatment to his blue striped shirt, her white blouse, the notebook, and the tabletop, with gentle color variation and softened shadows.
```

This is a new, untested draft. It adapts knowledge to the probe's successful direction; no additional gain over the actual long prompt has been measured. The actual [041 long input](../../out/prompt_probe/20261029_bernini/041__long/input.json) and [generated result](../../out/prompt_probe/20261029_bernini/041__long/edited.mp4) remain separately accessible.

The relevant content check is whether the proposal conveys a coherent visible treatment and whether its added choices fit the open request. A different storybook interpretation should be considered on its own merits. Watercolor and pastel are not mandatory answers to the short request.

## Benchmark fewshot/004: develop a specified space-station design

The [source clip](../../benchmark_data/fewshot/004/004.mp4) shows two players at a table-tennis table in a sports interior. The detailed probe request already chooses the environment, lighting, clothing direction, Earth view, and blue table edges. Its style-related portion reads:

> Transform the room into a futuristic space-station sports arena with metallic walls, blue-white lighting, and Earth visible through large windows. Dress the players in sleek sci-fi athletic suits and give the table glowing blue edges.

This quotation is the style-related excerpt. The [complete actual input](../../out/prompt_probe/20261029_bernini/fewshot_004__long/input.json) also contains preservation clauses. Those clauses and their outcomes remain in the experiment record; this walkthrough develops the visual design only.

### Read to resolve the remaining design choices

The [subject guide](theme.md#what-the-base-settings-offer) compares technical worlds with different material and social assumptions. [Clean laboratory](../entries/base-clean_lab.md) offers ceramic, matte alloy, glass, panel illumination, and luminous seams. Its source casts people as staff or experiment participants, but the sports request supplies a different purpose for the space. Material and light relationships can inform an arena without taking over the source's roles and plot.

The [science-fiction domain reference](../domain-references/sci_fi_modern.md) supplies ribbed fabric, matte shells, panels, and practical light. In this task, the model can develop those into athletic fabric and restrained technical seams. Implants and communications accessories are further possibilities in the source card, not required consequences of reading it.

For luminous surfaces, [097](../entries/opuscar-097.md) distinguishes a light's physical source from spill, reflected color, and bright cores. Its wet street, signs, snow, and night palette belong to that original proposal. The source-to-surface relationship can help the model describe a local luminous table rim in an otherwise clean sports environment. Whether a small reflected glow would improve the design is an open creative choice.

### Develop the proposal

The requested Earth window anchors the space-station setting. Matte metal wall panels and broad blue-white illumination give the room a common material and light logic. The suits use technical athletic fabric, allowing clothing and arena to belong to the same design. The table's upper playing-surface perimeter is the intended blue-emitting part in this interpretation.

The probe exposes a useful distinction here: both outputs showed substantial blue glow on the lower supports, while the request concerned table edges. A design description should name the intended part when the distinction matters. Whether revised wording actually improves placement remains a generation question.

| Design element | Basis | Use in this proposal |
|---|---|---|
| Space-station arena, Earth windows, blue-white light, sci-fi athletic suits, blue edges | Detailed request | Carry these specified choices into one coherent visual direction |
| Matte metallic panels and organized illumination | Clean-lab material and light relationships | Adapt the materials to the arena's sporting purpose |
| Ribbed technical fabric and restrained seams | Science-fiction domain terminology | Give the requested suits a concrete surface treatment |
| Upper playing-surface perimeter as the emitting part | Interpretation of the request, informed by the observed placement mismatch | Make the local target explicit in the new draft |

An illustrative English expression of the visual portion is:

```text
Turn the room into a futuristic space-station sports arena with matte metallic wall panels, broad blue-white illumination, and Earth visible through large windows. Dress the players in streamlined athletic suits made of ribbed technical fabric with subtle panel seams. Add a thin blue luminous strip along the perimeter of the table's upper playing surface, tracing the tabletop rim.
```

This is a new, untested style-only draft. It is available for subsequent prompt experiments; the specific rim wording has no demonstrated success advantage yet. Compare it with the [actual long result](../../out/prompt_probe/20261029_bernini/fewshot_004__long/edited.mp4) through the [experiment record](../model-experience/bernini-r.md).

## How these paths enter a future Planner

The reading manual supplies guidance; the map, guides, complete entries, and experience record provide material the model can inspect. A task workspace can retain a question such as “which illustration method suits this request?” or “which part is supposed to emit blue light?”, the passages read, and the resulting decision. The model decides which questions are useful and when it has enough information to write a proposal.

A source citation explains why a design choice was considered. The final video prompt can express the resulting appearance in ordinary English without carrying research notes, source IDs, or every fact read. The harness will need to retain the complete proposal and actual submitted text for later inspection. Its implementation remains a subsequent phase; [INTEGRATION](../INTEGRATION.md) records the existing interface direction.

## More complete material to explore

These entries extend the comparisons above. Each provides a complete reading edition, motivated cross-links, and source references.

| Material | Reading orientation |
|---|---|
| [038 \| The Sound of Music: Storybook 3D Alpine Aerial](../entries/opuscar-038.md) | A storybook-like 3D landscape narrows from aerial scale to a spinning figure, with terrain, wind, and movement curves creating flow. |
