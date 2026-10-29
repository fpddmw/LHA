# Chinese period settings: vocabulary, visible evidence, and historical card scope

[Knowledge map](../README.md) · [Reading manual](../READING.md)

The original card supplies terms for headwear, clothing, sets, and light sources, while recording visible-region restrictions and their trade-offs.

## Editorial reading and design relationships

The card connects liangbatou, diancui, jade pins, chenyi and changyi robes, standing collars, embroidery, wooden latticework, and court lanterns to visible heads, upper garments, backgrounds, and light sources. It shows how particular period proposals can become precise and how the original card connected terms to visible form.

The entrance groups Qing court drama, hanfu, and wuxia, but its main examples come from Qing dress and palace interiors. Historical applicability needs to be checked against the chosen setting. Chinese-period expression can also involve gongbi ceremony, ink space, or martial action. Warm lanterns, amber shadows, and reduced green saturation are choices in one experimental proposal.

The base card restricted specificity by visible carrier. The decisive variant encouraged full replacement on visible carriers; execution_only further limited additions to requested content. These changes record attempts to balance invented detail and under-editing. A new Planner can study the trade-offs and judge the task's design scope. Fixed replacements and preservation clauses remain historical source wording.

## Further reading

- [Video meaning and design possibilities](../guides/meaning.md): compare related designs within this topic.
- [Subject matter and visual language](../guides/theme.md): compare related designs within this topic.
- [The conditions behind generation experience](../guides/experience.md): compare related designs within this topic.
- [060 | The Last Emperor: Gongbi Court Painting on Silk](../entries/opuscar-060.md): Gongbi court painting connects ceremony, composition, and medium, adding design reasons beyond a vocabulary card.
- [Wuxia: action, historical materials, and poetic space](../entries/base-wuxia.md): Compare martial action with palace furnishing as different world assumptions.
- [Xianxia: the original card's spiritual and ceremonial direction](../entries/base-xianxia.md): Distinguish historical terminology from mythic world construction instead of treating them as one clothing system.

## Original experimental context

This card comes from the bench_v3 edit-specification writing experiments. Its source comments identify invented detail on invisible carriers, under-editing with long prompts, and target drift caused by added vocabulary. The 90-English-word advice, one-change clauses, preservation lists, and replacement directions belong to that context. The comments report 36% unknowable detail, change values of 0.21 to 0.17 to 0.12, and a 0.06 GT decline for a vocabulary variant. These remain attributed historical statements, not newly recomputed results. See the [experience synthesis](../guides/experience.md).

## Complete original structured card

```json
{
  "key": "chinese_period",
  "title": "Chinese historical / period drama (Qing, Han, wuxia, palace)",
  "carriers": [
    [
      "headwear on each visible head",
      "bun, hairpins, floral ornament, bare hair",
      "upgrade to period headdress: liangbatou / diancui filigree / jade pins / tassels, sized to the head"
    ],
    [
      "upper garment of each visible person",
      "t-shirt, sweater, blouse, modern collar",
      "replace with period robe: chenyi / changyi / qipao, standing collar, gold-thread embroidery"
    ],
    [
      "background wall or set behind the people",
      "plain wall, mural, window, foliage, LED panel",
      "replace with palace interior: carved rosewood lattice, silk partition, bronze lanterns, palace wall"
    ],
    [
      "light sources in frame",
      "flat daylight, ceiling lights, glowing orbs",
      "relight as warm directional lantern light with soft falloff; remove modern glowing fixtures"
    ],
    [
      "makeup and skin",
      "modern natural makeup",
      "refine to period makeup: defined liner, red lip, even complexion"
    ]
  ],
  "vocabulary": [
    "liangbatou headdress",
    "diancui kingfisher-feather filigree",
    "nephrite hairpin",
    "silk tassel",
    "chenyi robe",
    "changyi robe",
    "standing collar",
    "gold-thread embroidery",
    "embroidered rank badge",
    "carved rosewood lattice",
    "painted silk partition",
    "bronze court lantern",
    "palace wall",
    "warm candlelight"
  ],
  "off_carrier_policy": "leave that region untouched; carry the period look through grade and light only (warm amber shadows, lower saturation in the greens)",
  "model_priors": [
    "This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words.",
    "One change per clause, verb first; put the most important change first.",
    "Do not write preservation boilerplate; the model already receives a preserve list."
  ],
  "failure_modes": [
    "Do not invent props or rooms that are not visible.",
    "Do not swap a person's face or change how many people there are.",
    "Do not describe camera moves; the source motion is reused.",
    "Do not name a dynasty or rank the frame does not support.",
    "Do not turn one headdress into a crown, or one robe into armour."
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
CATEGORY: Chinese historical / period drama (Qing, Han, wuxia, palace)
CARRIERS (only edit the ones you can see):
- headwear on each visible head | looks like: bun, hairpins, floral ornament, bare hair | do: upgrade to period headdress: liangbatou / diancui filigree / jade pins / tassels, sized to the head
- upper garment of each visible person | looks like: t-shirt, sweater, blouse, modern collar | do: replace with period robe: chenyi / changyi / qipao, standing collar, gold-thread embroidery
- background wall or set behind the people | looks like: plain wall, mural, window, foliage, LED panel | do: replace with palace interior: carved rosewood lattice, silk partition, bronze lanterns, palace wall
- light sources in frame | looks like: flat daylight, ceiling lights, glowing orbs | do: relight as warm directional lantern light with soft falloff; remove modern glowing fixtures
- makeup and skin | looks like: modern natural makeup | do: refine to period makeup: defined liner, red lip, even complexion
VOCABULARY (use these nouns only for visible carriers): liangbatou headdress, diancui kingfisher-feather filigree, nephrite hairpin, silk tassel, chenyi robe, changyi robe, standing collar, gold-thread embroidery, embroidered rank badge, carved rosewood lattice, painted silk partition, bronze court lantern, palace wall, warm candlelight
IF A CARRIER IS NOT VISIBLE: leave that region untouched; carry the period look through grade and light only (warm amber shadows, lower saturation in the greens)
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not name a dynasty or rank the frame does not support. Do not turn one headdress into a crown, or one robe into armour.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

<details>
<summary>Decisive: stronger replacement on relevant visible carriers, original wording</summary>

```text
CATEGORY: Chinese historical / period drama (Qing, Han, wuxia, palace)
CARRIERS (only edit the ones you can see):
- headwear on each visible head | looks like: bun, hairpins, floral ornament, bare hair | do: upgrade to period headdress: liangbatou / diancui filigree / jade pins / tassels, sized to the head
- upper garment of each visible person | looks like: t-shirt, sweater, blouse, modern collar | do: replace with period robe: chenyi / changyi / qipao, standing collar, gold-thread embroidery
- background wall or set behind the people | looks like: plain wall, mural, window, foliage, LED panel | do: replace with palace interior: carved rosewood lattice, silk partition, bronze lanterns, palace wall
- light sources in frame | looks like: flat daylight, ceiling lights, glowing orbs | do: relight as warm directional lantern light with soft falloff; remove modern glowing fixtures
- makeup and skin | looks like: modern natural makeup | do: refine to period makeup: defined liner, red lip, even complexion
VOCABULARY (use these nouns only for visible carriers): liangbatou headdress, diancui kingfisher-feather filigree, nephrite hairpin, silk tassel, chenyi robe, changyi robe, standing collar, gold-thread embroidery, embroidered rank badge, carved rosewood lattice, painted silk partition, bronze court lantern, palace wall, warm candlelight
IF A CARRIER IS NOT VISIBLE: leave that region untouched; carry the period look through grade and light only (warm amber shadows, lower saturation in the greens)
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not name a dynasty or rank the frame does not support. Do not turn one headdress into a crown, or one robe into armour.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
INTENSITY: Make every requested replacement unmistakable: the new element must be clearly present in the first frame and stay for the whole clip, not a tint or a blend. Replace, do not overlay: the old garment/background/ornament must be gone, not visible underneath. If a carrier is visible and the user's request touches it, change it fully; do not hedge.
```

</details>

<details>
<summary>Execution only: elaborate only requested content, original wording</summary>

```text
CATEGORY: Chinese historical / period drama (Qing, Han, wuxia, palace)
CARRIERS VISIBLE OR NOT: you may only change what the user asked for. Do not introduce an element, garment, ornament or set piece the request does not mention.
IF THE USER'S REQUEST NAMES A THING, name its execution with these words: liangbatou headdress, diancui kingfisher-feather filigree, nephrite hairpin, silk tassel, chenyi robe, changyi robe, standing collar, gold-thread embroidery, embroidered rank badge, carved rosewood lattice, painted silk partition, bronze court lantern, palace wall, warm candlelight
IF THE USER'S REQUEST ONLY NAMES A MOOD OR LOOK, express it through grade, light and texture only: leave that region untouched; carry the period look through grade and light only (warm amber shadows, lower saturation in the greens)
MODEL BEHAVIOUR: This edit model under-edits when the prompt is long: keep the whole prompt under 90 English words. One change per clause, verb first; put the most important change first. Do not write preservation boilerplate; the model already receives a preserve list.
KNOWN FAILURES TO AVOID: Do not invent props or rooms that are not visible. Do not swap a person's face or change how many people there are. Do not describe camera moves; the source motion is reused. Do not name a dynasty or rank the frame does not support. Do not turn one headdress into a crown, or one robe into armour.
ALWAYS KEEP: each person's facial identity; facial expressions; body pose and action; composition and camera framing
```

</details>

## Source trail

- [Original cards, shared guidance, and routing](../../scripts/eval/bench_v3/skills_v3.py): `CARDS["chinese_period"]`, `_COMMON_PRIORS`, `DECISIVE_PRIORS`, and `card_block`.
- [Experiment configuration](../../scripts/eval/bench_v3/README.md) · [Provenance](../source-map.json).

The legacy router uses the first keyword match. These domain entrances support reading and comparison across domains. Future access is described in [INTEGRATION](../INTEGRATION.md).
