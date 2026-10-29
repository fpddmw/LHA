# Whole-image appearance: the historical filter card and complete medium design

[Knowledge map](../README.md) · [Reading manual](../READING.md)

The original card describes style transfer through grading and texture; complete cases develop image construction, viewing apparatus, and motion.

## Editorial reading and design relationships

The card provides terms such as halation, grain, gate weave, sepia, engraving, ink line, and wash. Its task was whole-image appearance editing with content retained, so highlights, shadows, and texture dominate. This context explains the recommendation to state grading before texture.

The model can deepen a requested medium by explaining how it forms the image: which lines carry contours, how marks build shadow, where paper remains visible, or which layer carries recording artifacts. The comparative media guide and complete cases supply those relationships. The Bernini probe adds conditional evidence for concrete expression without turning any single technique into a fixed prompt formula.

Complete cases show woodcut formed through black-and-white shapes and cuts, watercolor through reserved paper and transparent layers, and television through screen boundaries and entry into program space. Medium knowledge can help a model reconsider form and time. Filmic toe and preserved shadow detail are not shared goals of every aged image, silhouette, or high-contrast design.

## Further reading

- [How different media form an image](../guides/media.md): compare related designs within this topic.
- [Combining styles and methods](../guides/combination.md): compare related designs within this topic.
- [The conditions behind generation experience](../guides/experience.md): compare related designs within this topic.
- [003 | All Quiet on the Western Front: Kollwitz Anti-war Woodcut](../entries/opuscar-003.md): Compare woodcut form with a simple texture addition.
- [028 | Marty: 1955 Kinescope on a Living-Room TV](../entries/opuscar-028.md): Compare viewing spaces inside and outside a screen.
- [084 | The Artist: Polished Silent-Film Black & White](../entries/opuscar-084.md): Compare a modern silent-film tribute with a heavily aged silent-print appearance.

## Original experimental context

This card comes from the bench_v3 edit-specification writing experiments. Its source comments identify invented detail on invisible carriers, under-editing with long prompts, and target drift caused by added vocabulary. The 90-English-word advice, one-change clauses, preservation lists, and replacement directions belong to that context. The comments report 36% unknowable detail, change values of 0.21 to 0.17 to 0.12, and a 0.06 GT decline for a vocabulary variant. These remain attributed historical statements, not newly recomputed results. See the [experience synthesis](../guides/experience.md).

## Complete original structured card

```json
{
  "key": "style_filter",
  "title": "Whole-frame style transfer (film stock, monochrome, illustration, retro video)",
  "carriers": [
    [
      "the whole frame",
      "any content",
      "grade and texture the entire image; do not restyle individual objects"
    ],
    [
      "highlight response",
      "flat digital highlights",
      "halation, gentle rolloff, film-like shoulder"
    ],
    [
      "shadow response",
      "crushed or lifted blacks",
      "filmic toe: deep but detailed shadows"
    ],
    [
      "texture layer",
      "clean digital surface",
      "grain, vignette, gate weave or paper/ink texture as the reference implies"
    ]
  ],
  "vocabulary": [
    "high-contrast monochrome",
    "selective colour retention",
    "halation",
    "film grain",
    "gate weave",
    "sepia wash",
    "crosshatch etching",
    "ink line",
    "pastel wash",
    "soft bloom",
    "vignette"
  ],
  "off_carrier_policy": "this category edits the whole frame; keep objects, faces and motion intact",
  "model_priors": [
    "This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words.",
    "One change per clause, verb first; put the most important change first.",
    "Do not write preservation boilerplate; the model already receives a preserve list.",
    "For this category the change is global, so state the grade first and the texture second."
  ],
  "failure_modes": [
    "Do not change what objects are in frame.",
    "Do not flatten faces into illustration unless the request says so."
  ],
  "must_preserve": [
    "each person's facial identity",
    "facial expressions",
    "body pose and action",
    "composition and camera framing"
  ]
}
```

## Three complete versions supplied to the writer

<details>
<summary>Base card, original wording</summary>

```text
CATEGORY: Whole-frame style transfer (film stock, monochrome, illustration, retro video)
CARRIERS (only edit the ones you can see):
- the whole frame | looks like: any content | do: grade and texture the entire image; do not restyle individual objects
- highlight response | looks like: flat digital highlights | do: halation, gentle rolloff, film-like shoulder
- shadow response | looks like: crushed or lifted blacks | do: filmic toe: deep but detailed shadows
- texture layer | looks like: clean digital surface | do: grain, vignette, gate weave or paper/ink texture as the reference implies
VOCABULARY (use these nouns only for visible carriers): high-contrast monochrome, selective colour retention, halation, film grain, gate weave, sepia wash, crosshatch etching, ink line, pastel wash, soft bloom, vignette
IF A CARRIER IS NOT VISIBLE: this category edits the whole frame; keep objects, faces and motion intact
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list. For this category the change is global, so state the grade first and the texture second.
KNOWN FAILURES TO AVOID: Do not change what objects are in frame. Do not flatten faces into illustration unless the request says so.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

<details>
<summary>Decisive: stronger replacement on relevant visible carriers, original wording</summary>

```text
CATEGORY: Whole-frame style transfer (film stock, monochrome, illustration, retro video)
CARRIERS (only edit the ones you can see):
- the whole frame | looks like: any content | do: grade and texture the entire image; do not restyle individual objects
- highlight response | looks like: flat digital highlights | do: halation, gentle rolloff, film-like shoulder
- shadow response | looks like: crushed or lifted blacks | do: filmic toe: deep but detailed shadows
- texture layer | looks like: clean digital surface | do: grain, vignette, gate weave or paper/ink texture as the reference implies
VOCABULARY (use these nouns only for visible carriers): high-contrast monochrome, selective colour retention, halation, film grain, gate weave, sepia wash, crosshatch etching, ink line, pastel wash, soft bloom, vignette
IF A CARRIER IS NOT VISIBLE: this category edits the whole frame; keep objects, faces and motion intact
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list. For this category the change is global, so state the grade first and the texture second.
KNOWN FAILURES TO AVOID: Do not change what objects are in frame. Do not flatten faces into illustration unless the request says so.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
INTENSITY: Make every requested replacement unmistakable: the new element must be clearly present in the first frame and stay for the whole clip, not a tint or a blend. Replace, do not overlay: the old garment/background/ornament must be gone, not visible underneath. If a carrier is visible and the user's request touches it, change it fully; do not hedge.
```

</details>

<details>
<summary>Execution only: elaborate only requested content, original wording</summary>

```text
CATEGORY: Whole-frame style transfer (film stock, monochrome, illustration, retro video)
CARRIERS VISIBLE OR NOT: you may only change what the user asked for. Do not introduce an element, garment, ornament or set piece the request does not mention.
IF THE USER'S REQUEST NAMES A THING, name its execution with these words: high-contrast monochrome, selective colour retention, halation, film grain, gate weave, sepia wash, crosshatch etching, ink line, pastel wash, soft bloom, vignette
IF THE USER'S REQUEST ONLY NAMES A MOOD OR LOOK, express it through grade, light and texture only: this category edits the whole frame; keep objects, faces and motion intact
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list. For this category the change is global, so state the grade first and the texture second.
KNOWN FAILURES TO AVOID: Do not change what objects are in frame. Do not flatten faces into illustration unless the request says so.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

## Source trail

- [Original cards, shared guidance, and routing](../../scripts/eval/bench_v3/skills_v3.py): `CARDS["style_filter"]`, `_COMMON_PRIORS`, `DECISIVE_PRIORS`, and `card_block`.
- [Experiment configuration](../../scripts/eval/bench_v3/README.md) · [Provenance](../source-map.json).

The legacy router uses the first keyword match. These domain entrances support reading and comparison across domains. Future access is described in [INTEGRATION](../INTEGRATION.md).
