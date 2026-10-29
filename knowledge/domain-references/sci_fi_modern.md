# Science fiction and modern styling: technical vocabulary and world assumptions

[Knowledge map](../README.md) · [Reading manual](../READING.md)

Technical garments, panels, cables, and accessories offer local vocabulary; cyberpunk, clean laboratories, and biomechanical worlds have different organizing ideas.

## Editorial reading and design relationships

The card associates carbon-fiber implants, titanium communications accessories, ribbed fabric, matte shells, cables, and panel glow with heads, upper garments, and backgrounds. These terms can clarify where a particular technical appearance comes from and how material and assembly enter the image.

When developing a proposal, connect a chosen material to its intended object and visible part: ribbing can describe athletic fabric, matte panels can describe walls, and a luminous strip can trace a tabletop rim. These are possible applications of the vocabulary. The model selects them from the request and scene, and later generation determines how well each placement is realized.

Cool key light, rim separation, and technical dressing within the same space are one treatment. Clean laboratory, industrial wasteland, and alien-biomechanical entries provide different world structures. Neon can also be understood as light propagating through wet ground and snow. The card retains its original local-editing scope so readers can distinguish it from open world design.

## Further reading

- [Subject matter and visual language](../guides/theme.md): compare related designs within this topic.
- [How different media form an image](../guides/media.md): compare related designs within this topic.
- [The conditions behind generation experience](../guides/experience.md): compare related designs within this topic.
- [From knowledge to a visual proposal](../guides/design-expression.md): See technical vocabulary selected for athletic clothing, walls, and a specific light-emitting table part.
- [Clean laboratory: a controlled technological setting](../entries/base-clean_lab.md): Compare order and material as sources of technical character in a clean laboratory.
- [Alien biomechanics: a shared logic for organic and artificial structures](../entries/base-alien_biomech.md): Compare organic biomechanical structures with assembled technical vocabulary.
- [097 | Anora: Snowy Neon Night](../entries/opuscar-097.md): Study the relationships among neon, snow, ground, and light.

## Original experimental context

This card comes from the bench_v3 edit-specification writing experiments. Its source comments identify invented detail on invisible carriers, under-editing with long prompts, and target drift caused by added vocabulary. The 90-English-word advice, one-change clauses, preservation lists, and replacement directions belong to that context. The comments report 36% unknowable detail, change values of 0.21 to 0.17 to 0.12, and a 0.06 GT decline for a vocabulary variant. These remain attributed historical statements, not newly recomputed results. See the [experience synthesis](../guides/experience.md).

## Complete original structured card

```json
{
  "key": "sci_fi_modern",
  "title": "Sci-fi, futuristic or modern character styling",
  "carriers": [
    [
      "headwear / eyewear",
      "bare head, glasses, earbud",
      "technical accessory: micro-comm nodule, visor, eye patch with strap, matte ear stud"
    ],
    [
      "upper garment",
      "sweater, jacket, t-shirt",
      "technical garment: tactical tunic, seam-lined shell, ribbed knit, matte leather"
    ],
    [
      "background set",
      "office, street, interior",
      "same space with technical dressing: panels, cable runs, cool practicals"
    ],
    [
      "light sources",
      "office light, daylight",
      "cool key with rim separation; practical panel glow"
    ],
    [
      "small props",
      "laptop, cup, phone",
      "technical counterpart in the same position"
    ]
  ],
  "vocabulary": [
    "tactical tunic",
    "carbon-fibre implant",
    "titanium micro-comm",
    "ribbed knit",
    "matte shell",
    "halo rim light",
    "panel glow",
    "cable run",
    "holo interface"
  ],
  "off_carrier_policy": "keep the region as-is; add the look through contrast and cool grade",
  "model_priors": [
    "This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words.",
    "One change per clause, verb first; put the most important change first.",
    "Do not write preservation boilerplate; the model already receives a preserve list."
  ],
  "failure_modes": [
    "Do not invent props or rooms that are not visible.",
    "Do not swap a person's face or change how many people there are.",
    "Do not describe camera moves; the source motion is reused.",
    "Do not turn the scene into a spaceship or add crowds."
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
CATEGORY: Sci-fi, futuristic or modern character styling
CARRIERS (only edit the ones you can see):
- headwear / eyewear | looks like: bare head, glasses, earbud | do: technical accessory: micro-comm nodule, visor, eye patch with strap, matte ear stud
- upper garment | looks like: sweater, jacket, t-shirt | do: technical garment: tactical tunic, seam-lined shell, ribbed knit, matte leather
- background set | looks like: office, street, interior | do: same space with technical dressing: panels, cable runs, cool practicals
- light sources | looks like: office light, daylight | do: cool key with rim separation; practical panel glow
- small props | looks like: laptop, cup, phone | do: technical counterpart in the same position
VOCABULARY (use these nouns only for visible carriers): tactical tunic, carbon-fibre implant, titanium micro-comm, ribbed knit, matte shell, halo rim light, panel glow, cable run, holo interface
IF A CARRIER IS NOT VISIBLE: keep the region as-is; add the look through contrast and cool grade
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not turn the scene into a spaceship or add crowds.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

<details>
<summary>Decisive: stronger replacement on relevant visible carriers, original wording</summary>

```text
CATEGORY: Sci-fi, futuristic or modern character styling
CARRIERS (only edit the ones you can see):
- headwear / eyewear | looks like: bare head, glasses, earbud | do: technical accessory: micro-comm nodule, visor, eye patch with strap, matte ear stud
- upper garment | looks like: sweater, jacket, t-shirt | do: technical garment: tactical tunic, seam-lined shell, ribbed knit, matte leather
- background set | looks like: office, street, interior | do: same space with technical dressing: panels, cable runs, cool practicals
- light sources | looks like: office light, daylight | do: cool key with rim separation; practical panel glow
- small props | looks like: laptop, cup, phone | do: technical counterpart in the same position
VOCABULARY (use these nouns only for visible carriers): tactical tunic, carbon-fibre implant, titanium micro-comm, ribbed knit, matte shell, halo rim light, panel glow, cable run, holo interface
IF A CARRIER IS NOT VISIBLE: keep the region as-is; add the look through contrast and cool grade
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not turn the scene into a spaceship or add crowds.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
INTENSITY: Make every requested replacement unmistakable: the new element must be clearly present in the first frame and stay for the whole clip, not a tint or a blend. Replace, do not overlay: the old garment/background/ornament must be gone, not visible underneath. If a carrier is visible and the user's request touches it, change it fully; do not hedge.
```

</details>

<details>
<summary>Execution only: elaborate only requested content, original wording</summary>

```text
CATEGORY: Sci-fi, futuristic or modern character styling
CARRIERS VISIBLE OR NOT: you may only change what the user asked for. Do not introduce an element, garment, ornament or set piece the request does not mention.
IF THE USER'S REQUEST NAMES A THING, name its execution with these words: tactical tunic, carbon-fibre implant, titanium micro-comm, ribbed knit, matte shell, halo rim light, panel glow, cable run, holo interface
IF THE USER'S REQUEST ONLY NAMES A MOOD OR LOOK, express it through grade, light and texture only: keep the region as-is; add the look through contrast and cool grade
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not turn the scene into a spaceship or add crowds.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

## Source trail

- [Original cards, shared guidance, and routing](../../scripts/eval/bench_v3/skills_v3.py): `CARDS["sci_fi_modern"]`, `_COMMON_PRIORS`, `DECISIVE_PRIORS`, and `card_block`.
- [Experiment configuration](../../scripts/eval/bench_v3/README.md) · [Provenance](../source-map.json).

The legacy router uses the first keyword match. These domain entrances support reading and comparison across domains. Future access is described in [INTEGRATION](../INTEGRATION.md).
