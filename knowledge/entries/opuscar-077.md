# 077 | Million Dollar Baby: 16-bit Arcade Fighting Game

[Knowledge map](../README.md) · [Reading manual](../READING.md)

Boxing is adapted into a fighting game: pixels, rounds, hit stops, and victory conditions form one proposal.

## Editorial reading and design relationships

Regular pixels, limited colors, a side-view arena, and a custom interface are only part of the design. Round starts, health bars, combos, hit stops, and an ending state reorganize events through the chosen form.

This is a specific adaptation; treating obstacles as opponents is also the author's creative proposal. A Planner may study that transformation or borrow only pixel rendering. The current task determines the scope of adoption.

## Further reading

- [Video meaning and design possibilities](../guides/meaning.md): compare related designs within this topic.
- [Combining styles and methods](../guides/combination.md): compare related designs within this topic.
- [007 | It Happened One Night: 1930s B&W Rubber-hose Cartoon](../entries/opuscar-007.md): Compare how cartoon movement grammar and game rules affect performance.
- [073 | Gladiator: Roman Floor Mosaic](../entries/opuscar-073.md): Compare pixels and mosaics in their grids, forms, and materials.

## Complete source material in English

The following is the preserved English original from OPUSCAR. Clawd, the orange identity color, and handoffs to neighboring films serve its anthology. Colors, actions, timings, and Avoid clauses belong to this case. The original project used code-based drawing and 3D rendering; these records do not establish per-case Bernini results. The complete bilingual record remains available at the source link below.

![Original reference frame for Million Dollar Baby](../../zyx/img/opuscar98/77.jpg)

### Original identifiers and segment position

```json
{
  "no": 77,
  "year": "2004",
  "title_en": "Million Dollar Baby",
  "decade": "C8",
  "kind": "2D",
  "tone": "",
  "t0_seconds": 232.917,
  "duration_seconds": 2.5,
  "style_en": "16-bit Arcade Fighting Game",
  "frame": "img/opuscar98/77.jpg"
}
```

### Ingredients

- 16-bit pixel art
- Arcade fighting-game HUD
- CRT scanlines

### Original author's design explanation

An original 16-bit arcade fighting-game screen: health bars, a round timer, ROUND 1 / FIGHT!, a combo counter, hit-stop and a big K.O. A boxing film about a shot at the title becomes one round told in arcade grammar.

### Complete original style prompt

An original 16-bit arcade fighting game. Draw at 320×180 and nearest-neighbour upscale by a whole number (×6 for 1080p); CRT scanlines (alternate lines ~15% darker). A side-on arena from the subject's world, flattened into stage and backdrop (e.g. a ring with a dark purple crowd band #1D1435). UI in a self-drawn 5×7 pixel font: two health bars (yellow #F5C53A, red damage trail), timer, banner, ROUND 1 / FIGHT!, combo counter. Chunky sprites about 50 px tall, 1-px highlights, dark outlines, ~32 colours per frame. The story becomes a contest between the hero and a rival (if none exists, personify an obstacle: a storm, a deadline). Hits spark, freeze 3–4 frames and flash white; the loser is knocked back, then K.O. and WINNER. Fixed side-on camera, no cuts. Reference: early-1990s arcade fighters. Avoid: real games' characters or logos; anti-aliased pixels.

### All shots in their original order

#### 1. game | 2.5 seconds

One locked side-on game screen: ROUND 1, FIGHT!, the shadow boxer swings a hook and Clawd ducks under it, dashes in for jab, jab and an uppercut with hit-stop and a white flash; the rival flies back, K.O., and Clawd raises its glove as the winner.

### Direction and handoff

Clawd wears a green satin robe with white trim and red gloves; the rival is a faceless navy boxer called SHADOW. The fight is choreographed to the clock: the uppercut lands at 1.46 s with a hit-stop, K.O. at 1.6 s, victory at 1.95 s. One shot, no cuts, the game's own camera.

### References named by the author

Clint Eastwood, 2004 · Early-1990s arcade fighting games (genre grammar) · Million Dollar Baby: Maggie's green robe

The named artists, filmmakers, and works are the original author's reference statements; they were not individually verified through external historical research in this reorganization.

## How the legacy template represents this material

The converter allocated selected sentences to fixed fields by keywords, usually retaining the longest sentence in each field. Camera, editing, timing, and unassigned material went into notes. Read those fragments with the complete design above. Default risk fields such as `identity_risk`, and `common_failure_modes` derived from Avoid clauses, are converter annotations or author advice rather than measured failure records.

<details>
<summary>Complete legacy template data, unchanged</summary>

```json
{
  "strategy_id": "opuscar_77_16_bit_arcade_fighting_game",
  "style_family": "styles_2d",
  "title": "16-bit Arcade Fighting Game",
  "description": "An original 16-bit arcade fighting-game screen: health bars, a round timer, ROUND 1 / FIGHT!, a combo counter, hit-stop and a big K.O. A boxing film about a shot at the title becomes one round told in arcade grammar.",
  "reference_image": "zyx/img/opuscar98/77.jpg",
  "tags": [
    "16-bit pixel art",
    "Arcade fighting-game HUD",
    "CRT scanlines"
  ],
  "intensity": "normal",
  "world_rewrite_cost": "medium",
  "identity_risk": "low",
  "common_failure_modes": [
    "real games' characters or logos; anti-aliased pixels."
  ],
  "prompt_compilation_notes": [
    "An original 16-bit arcade fighting game.",
    "Draw at 320×180 and nearest-neighbour upscale by a whole number (×6 for 1080p); CRT scanlines (alternate lines ~15% darker).",
    "a ring with a dark purple crowd band #1D1435).",
    "UI in a self-drawn 5×7 pixel font: two health bars (yellow #F5C53A, red damage trail), timer, banner, ROUND 1 / FIGHT!, combo counter.",
    "The story becomes a contest between the hero and a rival (if none exists, personify an obstacle: a storm, a deadline).",
    "Hits spark, freeze 3–4 frames and flash white; the loser is knocked back, then K.O."
  ],
  "pros": [],
  "cons": [],
  "forbidden_mixes": [],
  "anchor_requirements": [],
  "best_for_archetypes": [],
  "high_risk_archetypes": [],
  "recommended_carriers": [],
  "color_grade": "Chunky sprites about 50 px tall, 1-px highlights, dark outlines, ~32 colours per frame.",
  "lighting": "",
  "material": "",
  "costume": "",
  "headwear": "",
  "jewelry": "",
  "subject_surface": "",
  "environment": "A side-on arena from the subject's world, flattened into stage and backdrop (e.g.",
  "props": "",
  "atmosphere": "",
  "subject_integration": ""
}
```

</details>

## Source trail

- [Complete bilingual source collection](../../zyx/styles.json): select `no = 77`.
- [Legacy template](../../src/skills/templates/styles_2d/opuscar_77_16_bit_arcade_fighting_game.py): `SKILLS[0]`, `opuscar_77_16_bit_arcade_fighting_game`.
- [Original project description](../../zyx/README.md) · [Saved source page](../../zyx/opuscar98/index.html).
- [Legacy converter](../../scripts/build_opuscar_templates.py) · [Machine-readable provenance](../source-map.json).
