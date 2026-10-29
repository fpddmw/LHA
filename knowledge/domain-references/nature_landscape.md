# Nature and landscape: space, light, and human experience

[Knowledge map](../README.md) · [Reading manual](../READING.md)

The original card organizes sky, vegetation, distance, and aerial perspective; other cases add different times and viewing relationships.

## Editorial reading and design relationships

The card connects distant haze, plant surfaces, low-angle light, and receding structures. It supplies vocabulary for depth, aerial perspective, dew, and long shadows. Its task was improving the production appearance of an existing landscape, with roads, buildings, and landmarks retained.

Golden hour and a warm-cool split are one direction. A pastel horizon can darken while a person walks, sits, and looks. Fixed desert views can make headlights, a coin, and distant change threatening. An aerial journey can narrow to a handshake. Meaning in nature scenes also depends on experience, information timing, and duration.

## Further reading

- [Video meaning and design possibilities](../guides/meaning.md): compare related designs within this topic.
- [Composition, light, and time](../guides/time.md): compare related designs within this topic.
- [The conditions behind generation experience](../guides/experience.md): compare related designs within this topic.
- [093 | Nomadland: Magic-Hour Soft Pastel](../entries/opuscar-093.md): Read a case where changing daylight and sustained action form an experience.
- [080 | No Country for Old Men: 3D West Texas Dusk, Deakins Light](../entries/opuscar-080.md): Compare the narrative role of small changes within fixed views.
- [058 | Out of Africa: 3D Biplane over the Rift Valley](../entries/opuscar-058.md): Compare landscape scale and a human relationship connected within one sequence.

## Original experimental context

This card comes from the bench_v3 edit-specification writing experiments. Its source comments identify invented detail on invisible carriers, under-editing with long prompts, and target drift caused by added vocabulary. The 90-English-word advice, one-change clauses, preservation lists, and replacement directions belong to that context. The comments report 36% unknowable detail, change values of 0.21 to 0.17 to 0.12, and a 0.06 GT decline for a vocabulary variant. These remain attributed historical statements, not newly recomputed results. See the [experience synthesis](../guides/experience.md).

## Complete original structured card

```json
{
  "key": "nature_landscape",
  "title": "Nature, landscape and documentary scenery",
  "carriers": [
    [
      "sky and atmosphere",
      "flat sky, haze, clouds",
      "aerial perspective: layered haze, god rays, colour-graded sky"
    ],
    [
      "ground and vegetation",
      "field, road, trees",
      "richer material response: dew, warm rim on foliage, defined texture"
    ],
    [
      "light sources",
      "overcast or flat light",
      "golden-hour key with long shadows and warm-cool split"
    ],
    [
      "distant structure",
      "houses, poles, roads",
      "keep them; let haze set them back in depth"
    ]
  ],
  "vocabulary": [
    "aerial perspective",
    "golden-hour key",
    "warm-cool split",
    "long shadows",
    "layered haze",
    "dew sheen",
    "volumetric light",
    "deep focus"
  ],
  "off_carrier_policy": "grade globally; do not invent landmarks",
  "model_priors": [
    "This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words.",
    "One change per clause, verb first; put the most important change first.",
    "Do not write preservation boilerplate; the model already receives a preserve list."
  ],
  "failure_modes": [
    "Do not add animals, people or buildings that are not there."
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
CATEGORY: Nature, landscape and documentary scenery
CARRIERS (only edit the ones you can see):
- sky and atmosphere | looks like: flat sky, haze, clouds | do: aerial perspective: layered haze, god rays, colour-graded sky
- ground and vegetation | looks like: field, road, trees | do: richer material response: dew, warm rim on foliage, defined texture
- light sources | looks like: overcast or flat light | do: golden-hour key with long shadows and warm-cool split
- distant structure | looks like: houses, poles, roads | do: keep them; let haze set them back in depth
VOCABULARY (use these nouns only for visible carriers): aerial perspective, golden-hour key, warm-cool split, long shadows, layered haze, dew sheen, volumetric light, deep focus
IF A CARRIER IS NOT VISIBLE: grade globally; do not invent landmarks
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not add animals, people or buildings that are not there.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

<details>
<summary>Decisive: stronger replacement on relevant visible carriers, original wording</summary>

```text
CATEGORY: Nature, landscape and documentary scenery
CARRIERS (only edit the ones you can see):
- sky and atmosphere | looks like: flat sky, haze, clouds | do: aerial perspective: layered haze, god rays, colour-graded sky
- ground and vegetation | looks like: field, road, trees | do: richer material response: dew, warm rim on foliage, defined texture
- light sources | looks like: overcast or flat light | do: golden-hour key with long shadows and warm-cool split
- distant structure | looks like: houses, poles, roads | do: keep them; let haze set them back in depth
VOCABULARY (use these nouns only for visible carriers): aerial perspective, golden-hour key, warm-cool split, long shadows, layered haze, dew sheen, volumetric light, deep focus
IF A CARRIER IS NOT VISIBLE: grade globally; do not invent landmarks
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not add animals, people or buildings that are not there.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
INTENSITY: Make every requested replacement unmistakable: the new element must be clearly present in the first frame and stay for the whole clip, not a tint or a blend. Replace, do not overlay: the old garment/background/ornament must be gone, not visible underneath. If a carrier is visible and the user's request touches it, change it fully; do not hedge.
```

</details>

<details>
<summary>Execution only: elaborate only requested content, original wording</summary>

```text
CATEGORY: Nature, landscape and documentary scenery
CARRIERS VISIBLE OR NOT: you may only change what the user asked for. Do not introduce an element, garment, ornament or set piece the request does not mention.
IF THE USER'S REQUEST NAMES A THING, name its execution with these words: aerial perspective, golden-hour key, warm-cool split, long shadows, layered haze, dew sheen, volumetric light, deep focus
IF THE USER'S REQUEST ONLY NAMES A MOOD OR LOOK, express it through grade, light and texture only: grade globally; do not invent landmarks
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not add animals, people or buildings that are not there.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

## Source trail

- [Original cards, shared guidance, and routing](../../scripts/eval/bench_v3/skills_v3.py): `CARDS["nature_landscape"]`, `_COMMON_PRIORS`, `DECISIVE_PRIORS`, and `card_block`.
- [Experiment configuration](../../scripts/eval/bench_v3/README.md) · [Provenance](../source-map.json).

The legacy router uses the first keyword match. These domain entrances support reading and comparison across domains. Future access is described in [INTEGRATION](../INTEGRATION.md).
