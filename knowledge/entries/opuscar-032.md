# 032 | Ben-Hur: 3D Circus Chariot Race, 65mm Epic

[Knowledge map](../README.md) · [Reading manual](../READING.md)

Multiple viewpoints within continuous 3D chariot racing connect spectacle at scale with local collisions.

## Editorial reading and design relationships

Monumental architecture, repeated stands, material detail, dust, and widescreen grading establish the race's scale. Wheels, reins, and whipping gestures depend on coordinated motion, linking small actions to the overall scene.

Start, bend, parallel tracking, hub collision, character close-up, and final wide composition provide spatial, danger, and character information in sequence. The case supports study of multi-shot action design. Its original 3D implementation and a video editor's available controls have separate evidential status.

## Further reading

- [Composition, light, and time](../guides/time.md): compare related designs within this topic.
- [Video meaning and design possibilities](../guides/meaning.md): compare related designs within this topic.
- [001 | Wings: Silent-era 3D Dogfight, Tinted Ortho B&W](../entries/opuscar-001.md): Compare viewpoint and motion information from cameras attached to vehicles.
- [098 | One Battle After Another: 3D Dip-Road Chase, Long Lens](../entries/opuscar-098.md): Compare speed conveyed through arena coverage and telephoto road pursuit.

## Complete source material in English

The following is the preserved English original from OPUSCAR. Clawd, the orange identity color, and handoffs to neighboring films serve its anthology. Colors, actions, timings, and Avoid clauses belong to this case. The original project used code-based drawing and 3D rendering; these records do not establish per-case Bernini results. The complete bilingual record remains available at the source link below.

![Original reference frame for Ben-Hur](../../zyx/img/opuscar98/32.jpg)

### Original identifiers and segment position

```json
{
  "no": 32,
  "year": "1959",
  "title_en": "Ben-Hur",
  "decade": "C3",
  "kind": "3D",
  "tone": "",
  "t0_seconds": 101.25,
  "duration_seconds": 5.0,
  "style_en": "3D Circus Chariot Race, 65mm Epic",
  "frame": "img/opuscar98/32.jpg"
}
```

### Ingredients

- Procedural 3D (three.js)
- MGM Camera 65 widescreen
- Technicolor print grade
- Second-unit action staging

### Original author's design explanation

A fully procedural 3D Circus in widescreen-epic light: hard desert sun, dust, marble and gold, a Technicolor grade and 65mm grain. The chariot race is the film's most famous sequence, so the scene is the race, under the poster's golden colossus.

### Complete original style prompt

1959 65mm widescreen epic built in 3D. Default: hard high sun (about 50°), short crisp shadows, cobalt sky fading to sandy white; under a low sun shadows stay hard but long, the sky turns amber. Marble, gilt, red granite and sandstone, with mouldings and fluted columns, never bare boxes. Warm sunlit haze mixes about 20% into mid-distance colours. Technicolor-print grade: warm, saturated, slightly contrasty, no clipping or bloom; fine grain (±3%), slight gate weave. Scale is the point: monumental architecture, statues and repeated elements fill the background, never empty. The one hero subject (e.g. orange #D97757) is the most saturated thing in frame; any repeated motion (stride, wheel, oar) keeps time with speed. Signature shot: low tracking beside the moving hero, 35–50 mm full-frame; then wide, top-down, close-up, low angle. Avoid: clean CG light, empty or primitive sets, overexposure.

### All shots in their original order

#### 1. start | 0.9 seconds

Wide on the white start line: nine four-horse chariots side by side, Clawd's white team among them, the packed stands behind; the teams launch as the lens slowly tightens.

#### 2. turn | 0.8 seconds

High overhead on the east turn: the chariots sling round the gilded turning posts, dust arcing behind them.

#### 3. track | 1.1 seconds

Low tracking shot alongside Clawd's chariot: white horses at full gallop, spinning spokes, dust; the camera moves forward with it.

#### 4. wheel | 0.6 seconds

Low between the two chariots: Messala's bladed hub bites into Clawd's wheel and throws sparks; the camera rides with the chariots.

#### 5. close | 0.8 seconds

Close on Clawd cracking the whip from its chariot, Messala's black team alongside; slow push in.

#### 6. still | 0.8 seconds

The poster shot: low side angle as Clawd's white team draws level under a golden seated colossus on the spina, stands and governor's box behind; the lens slowly widens.

### Direction and handoff

Clawd plays Judah Ben-Hur: a linen headband, reins in one hand and a whip in the other, behind four white horses. Six shots in five seconds cover the race the way the 1959 second unit did: start, turn, tracking, wheels, close, poster. Every set-up moves with the chariots, so the pace never drops.

### References named by the author

William Wyler, 1959 · Yakima Canutt & Andrew Marton (chariot race) · Robert Surtees (cinematography) · 1959 MGM poster

The named artists, filmmakers, and works are the original author's reference statements; they were not individually verified through external historical research in this reorganization.

## How the legacy template represents this material

The converter allocated selected sentences to fixed fields by keywords, usually retaining the longest sentence in each field. Camera, editing, timing, and unassigned material went into notes. Read those fragments with the complete design above. Default risk fields such as `identity_risk`, and `common_failure_modes` derived from Avoid clauses, are converter annotations or author advice rather than measured failure records.

<details>
<summary>Complete legacy template data, unchanged</summary>

```json
{
  "strategy_id": "opuscar_32_3d_circus_chariot_race_65mm_epic",
  "style_family": "styles_3d",
  "title": "3D Circus Chariot Race, 65mm Epic",
  "description": "A fully procedural 3D Circus in widescreen-epic light: hard desert sun, dust, marble and gold, a Technicolor grade and 65mm grain. The chariot race is the film's most famous sequence, so the scene is the race, under the poster's golden colossus.",
  "reference_image": "zyx/img/opuscar98/32.jpg",
  "tags": [
    "Procedural 3D (three.js)",
    "MGM Camera 65 widescreen",
    "Technicolor print grade",
    "Second-unit action staging"
  ],
  "intensity": "normal",
  "world_rewrite_cost": "high",
  "identity_risk": "low",
  "common_failure_modes": [
    "clean CG light, empty or primitive sets, overexposure."
  ],
  "prompt_compilation_notes": [
    "mm widescreen epic built in 3D.",
    "Marble, gilt, red granite and sandstone, with mouldings and fluted columns, never bare boxes.",
    "The one hero subject (e.g.",
    "Signature shot: low tracking beside the moving hero, 35–50 mm full-frame; then wide, top-down, close-up, low angle."
  ],
  "pros": [],
  "cons": [],
  "forbidden_mixes": [],
  "anchor_requirements": [],
  "best_for_archetypes": [],
  "high_risk_archetypes": [],
  "recommended_carriers": [],
  "color_grade": "Default: hard high sun (about 50°), short crisp shadows, cobalt sky fading to sandy white; under a low sun shadows stay hard but long, the sky turns amber.",
  "lighting": "",
  "material": "",
  "costume": "",
  "headwear": "",
  "jewelry": "",
  "subject_surface": "",
  "environment": "Scale is the point: monumental architecture, statues and repeated elements fill the background, never empty.",
  "props": "",
  "atmosphere": "",
  "subject_integration": ""
}
```

</details>

## Source trail

- [Complete bilingual source collection](../../zyx/styles.json): select `no = 32`.
- [Legacy template](../../src/skills/templates/styles_3d/opuscar_32_3d_circus_chariot_race_65mm_epic.py): `SKILLS[0]`, `opuscar_32_3d_circus_chariot_race_65mm_epic`.
- [Original project description](../../zyx/README.md) · [Saved source page](../../zyx/opuscar98/index.html).
- [Legacy converter](../../scripts/build_opuscar_templates.py) · [Machine-readable provenance](../source-map.json).
