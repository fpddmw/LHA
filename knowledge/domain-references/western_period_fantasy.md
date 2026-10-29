# Western period and fantasy settings: specific materials and open world assumptions

[Knowledge map](../README.md) · [Reading manual](../READING.md)

Wool, linen, brocade, timber, stone, and practical lights provide one setting direction within a broad range of historical and fantasy possibilities.

## Editorial reading and design relationships

The card groups garment materials, architectural parts, and visible light sources. A wool coat, linen shirt, brocade vest, stone hearth, beams, arched window, and sconces can jointly create an interior experience. Their relationships supply more information than a fantasy label.

The entrance includes period drama, fantasy, and magical realism without developing their eras, social relationships, or magical systems. Replacing a prop with a same-position period or fantasy counterpart is one historical experimental strategy. Adoption, retention, or a change of function depends on the current design. Holbein-like portraiture and Elizabethan miniatures offer distinct expressions without requiring new magical objects.

## Further reading

- [Subject matter and visual language](../guides/theme.md): compare related designs within this topic.
- [Combining styles and methods](../guides/combination.md): compare related designs within this topic.
- [The conditions behind generation experience](../guides/experience.md): compare related designs within this topic.
- [039 | A Man for All Seasons: Holbein Tudor Portrait in Oils](../entries/opuscar-039.md): Study how fabric, posture, and portrait viewing establish identity.
- [071 | Shakespeare in Love: Hilliard Elizabethan Miniature](../entries/opuscar-071.md): Compare a private pendant and public theater using a related painting language.
- [Medieval fantasy: material, heraldry, and an inhabited world](../entries/base-medieval_fantasy.md): Read another proposal centered on broader world reconstruction and compare its scope.

## Original experimental context

This card comes from the bench_v3 edit-specification writing experiments. Its source comments identify invented detail on invisible carriers, under-editing with long prompts, and target drift caused by added vocabulary. The 90-English-word advice, one-change clauses, preservation lists, and replacement directions belong to that context. The comments report 36% unknowable detail, change values of 0.21 to 0.17 to 0.12, and a 0.06 GT decline for a vocabulary variant. These remain attributed historical statements, not newly recomputed results. See the [experience synthesis](../guides/experience.md).

## Complete original structured card

```json
{
  "key": "western_period_fantasy",
  "title": "Western period, fantasy or magical realism",
  "carriers": [
    [
      "headwear / hair",
      "cap, scarf, bare head",
      "period hat, styled hair with metal or leather ornament"
    ],
    [
      "upper garment",
      "t-shirt, jacket, hoodie",
      "period garment: wool coat, linen shirt, brocade vest, leather straps"
    ],
    [
      "background set",
      "park, plain wall, office, modern interior",
      "period room or fantasy interior: stone hearth, wooden beams, arched window, candle sconces"
    ],
    [
      "light sources",
      "overcast daylight, office lighting",
      "motivated practical light: firelight, candle, window shaft, enchanted glow"
    ],
    [
      "props at hand",
      "cup, book, screen, phone",
      "period or fantasy counterpart of the same prop in the same place"
    ]
  ],
  "vocabulary": [
    "wool coat",
    "linen shirt",
    "brocade vest",
    "leather bracer",
    "stone hearth",
    "wooden beam",
    "arched window",
    "candle sconce",
    "enchanted ember",
    "aged parchment",
    "carved oak",
    "iron chandelier"
  ],
  "off_carrier_policy": "leave it alone and shift the grade instead: warmer highlights, deeper shadows",
  "model_priors": [
    "This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words.",
    "One change per clause, verb first; put the most important change first.",
    "Do not write preservation boilerplate; the model already receives a preserve list."
  ],
  "failure_modes": [
    "Do not invent props or rooms that are not visible.",
    "Do not swap a person's face or change how many people there are.",
    "Do not describe camera moves; the source motion is reused.",
    "Do not add creatures or effects the request did not ask for."
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
CATEGORY: Western period, fantasy or magical realism
CARRIERS (only edit the ones you can see):
- headwear / hair | looks like: cap, scarf, bare head | do: period hat, styled hair with metal or leather ornament
- upper garment | looks like: t-shirt, jacket, hoodie | do: period garment: wool coat, linen shirt, brocade vest, leather straps
- background set | looks like: park, plain wall, office, modern interior | do: period room or fantasy interior: stone hearth, wooden beams, arched window, candle sconces
- light sources | looks like: overcast daylight, office lighting | do: motivated practical light: firelight, candle, window shaft, enchanted glow
- props at hand | looks like: cup, book, screen, phone | do: period or fantasy counterpart of the same prop in the same place
VOCABULARY (use these nouns only for visible carriers): wool coat, linen shirt, brocade vest, leather bracer, stone hearth, wooden beam, arched window, candle sconce, enchanted ember, aged parchment, carved oak, iron chandelier
IF A CARRIER IS NOT VISIBLE: leave it alone and shift the grade instead: warmer highlights, deeper shadows
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not add creatures or effects the request did not ask for.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

<details>
<summary>Decisive: stronger replacement on relevant visible carriers, original wording</summary>

```text
CATEGORY: Western period, fantasy or magical realism
CARRIERS (only edit the ones you can see):
- headwear / hair | looks like: cap, scarf, bare head | do: period hat, styled hair with metal or leather ornament
- upper garment | looks like: t-shirt, jacket, hoodie | do: period garment: wool coat, linen shirt, brocade vest, leather straps
- background set | looks like: park, plain wall, office, modern interior | do: period room or fantasy interior: stone hearth, wooden beams, arched window, candle sconces
- light sources | looks like: overcast daylight, office lighting | do: motivated practical light: firelight, candle, window shaft, enchanted glow
- props at hand | looks like: cup, book, screen, phone | do: period or fantasy counterpart of the same prop in the same place
VOCABULARY (use these nouns only for visible carriers): wool coat, linen shirt, brocade vest, leather bracer, stone hearth, wooden beam, arched window, candle sconce, enchanted ember, aged parchment, carved oak, iron chandelier
IF A CARRIER IS NOT VISIBLE: leave it alone and shift the grade instead: warmer highlights, deeper shadows
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not add creatures or effects the request did not ask for.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
INTENSITY: Make every requested replacement unmistakable: the new element must be clearly present in the first frame and stay for the whole clip, not a tint or a blend. Replace, do not overlay: the old garment/background/ornament must be gone, not visible underneath. If a carrier is visible and the user's request touches it, change it fully; do not hedge.
```

</details>

<details>
<summary>Execution only: elaborate only requested content, original wording</summary>

```text
CATEGORY: Western period, fantasy or magical realism
CARRIERS VISIBLE OR NOT: you may only change what the user asked for. Do not introduce an element, garment, ornament or set piece the request does not mention.
IF THE USER'S REQUEST NAMES A THING, name its execution with these words: wool coat, linen shirt, brocade vest, leather bracer, stone hearth, wooden beam, arched window, candle sconce, enchanted ember, aged parchment, carved oak, iron chandelier
IF THE USER'S REQUEST ONLY NAMES A MOOD OR LOOK, express it through grade, light and texture only: leave it alone and shift the grade instead: warmer highlights, deeper shadows
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not add creatures or effects the request did not ask for.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

## Source trail

- [Original cards, shared guidance, and routing](../../scripts/eval/bench_v3/skills_v3.py): `CARDS["western_period_fantasy"]`, `_COMMON_PRIORS`, `DECISIVE_PRIORS`, and `card_block`.
- [Experiment configuration](../../scripts/eval/bench_v3/README.md) · [Provenance](../source-map.json).

The legacy router uses the first keyword match. These domain entrances support reading and comparison across domains. Future access is described in [INTEGRATION](../INTEGRATION.md).
