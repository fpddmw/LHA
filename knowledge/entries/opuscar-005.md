# 005 | Grand Hotel: MGM Silver B&W 3D Lobby

[Knowledge map](../README.md) · [Reading manual](../READING.md)

A 3D lobby is built around a concentric overhead composition, then experienced differently through a figure-height tracking shot.

## Editorial reading and design relationships

Circular galleries, a checkerboard floor, reflective surfaces, and silvery monochrome form a navigable space. From above, people become small points within its order; from the side, revolving doors, walking, and passing scenery restore human scale. Camera position shapes how the set must be built and understood.

The direction notes include a revision to step frequency and actual displacement. This is an implementation record from the original project, useful for understanding coordination between walking and photography. It does not establish equivalent control in a video-editing model; design intent and execution conditions remain distinct.

## Further reading

- [Composition, light, and time](../guides/time.md): compare related designs within this topic.
- [Video meaning and design possibilities](../guides/meaning.md): compare related designs within this topic.
- [009 | The Great Ziegfeld: Silver B&W 3D Wedding-cake Stage](../entries/opuscar-009.md): Compare another layered 3D structure whose space supports the display of a performance.
- [087 | Birdman: 3D Backstage Long Take](../entries/opuscar-087.md): Compare spatial understanding through cuts with continuous corridor tracking.

## Complete source material in English

The following is the preserved English original from OPUSCAR. Clawd, the orange identity color, and handoffs to neighboring films serve its anthology. Colors, actions, timings, and Avoid clauses belong to this case. The original project used code-based drawing and 3D rendering; these records do not establish per-case Bernini results. The complete bilingual record remains available at the source link below.

![Original reference frame for Grand Hotel](../../zyx/img/opuscar98/05.jpg)

### Original identifiers and segment position

```json
{
  "no": 5,
  "year": "1931/32",
  "title_en": "Grand Hotel",
  "decade": "C1",
  "kind": "3D",
  "tone": "B&W",
  "t0_seconds": 27.083,
  "duration_seconds": 2.5,
  "style_en": "MGM Silver B&W 3D Lobby",
  "frame": "img/opuscar98/05.jpg"
}
```

### Ingredients

- three.js 3D
- MGM silver-screen black and white
- Art Deco interiors
- Overhead symmetry

### Original author's design explanation

A three.js model of the circular lobby, graded in MGM's silver black and white with Clawd's orange as the only colour. The film's best-known image is the shot straight down the well, galleries closing in rings, so the set is built around it.

### Complete original style prompt

A real 3D set, by default an Art Deco interior (marble, chrome, chandelier, glossy checkerboard floor); outdoors keep the real setting with glossy surfaces (wet pavement, still water) and symmetrical framing. Ambient occlusion, soft bloom; 1930s studio silver: about 40% deep black, glossy whites near 90%, no washed-out greys. Light falls in shafts from one high source. All neutral grey except the hero the story centres on (e.g. #D97757), at least 1/6 of frame height; warm lamps render white, bloom only around them. Grain (±3%), halation. Signature shot: eye-height wide into a deep symmetrical set, floor and ceiling in frame, floor reflections; then 4-6 s tracks; one overhead on rings, figures as chess pieces. Period figures (heads, hats, limbs) walk routes. References: art director Cedric Gibbons, cinematographer William Daniels. Avoid: walking in place, frame-filling abstract patterns, colour casts.

### All shots in their original order

#### 1. overhead | 1.1 seconds

Straight down the six-gallery light well, the rings closing toward the key tower; the orange bellboy is a single dot crossing the checkerboard marble; a slow push in as the lens narrows.

#### 2. follow | 1.4 seconds

Side tracking shot at Clawd's height: it walks with its suitcase, the lobby sliding past, the revolving door turning ahead; the camera eases forward and in.

### Direction and handoff

Clawd is the bellboy in a pillbox cap, carrying a suitcase covered in hotel labels. In v6 it really walks, 1.4 m/s at 2.4 strides a second, matched to the distance it covers. The film plays 1:1 with one hard cut at 1.08 s, from the overhead to the tracking shot.

### References named by the author

Edmund Goulding, 1932 · Cedric Gibbons (art direction) · William Daniels (cinematography)

The named artists, filmmakers, and works are the original author's reference statements; they were not individually verified through external historical research in this reorganization.

## How the legacy template represents this material

The converter allocated selected sentences to fixed fields by keywords, usually retaining the longest sentence in each field. Camera, editing, timing, and unassigned material went into notes. Read those fragments with the complete design above. Default risk fields such as `identity_risk`, and `common_failure_modes` derived from Avoid clauses, are converter annotations or author advice rather than measured failure records.

<details>
<summary>Complete legacy template data, unchanged</summary>

```json
{
  "strategy_id": "opuscar_05_mgm_silver_b_w_3d_lobby",
  "style_family": "styles_3d",
  "title": "MGM Silver B&W 3D Lobby",
  "description": "A three.js model of the circular lobby, graded in MGM's silver black and white with Clawd's orange as the only colour. The film's best-known image is the shot straight down the well, galleries closing in rings, so the set is built around it.",
  "reference_image": "zyx/img/opuscar98/05.jpg",
  "tags": [
    "three.js 3D",
    "MGM silver-screen black and white",
    "Art Deco interiors",
    "Overhead symmetry"
  ],
  "intensity": "normal",
  "world_rewrite_cost": "high",
  "identity_risk": "low",
  "common_failure_modes": [
    "walking in place, frame-filling abstract patterns, colour casts."
  ],
  "prompt_compilation_notes": [
    "All neutral grey except the hero the story centres on (e.g.",
    "Signature shot: eye-height wide into a deep symmetrical set, floor and ceiling in frame, floor reflections; then 4-6 s tracks; one overhead on rings, figures as chess pieces.",
    "References: art director Cedric Gibbons, cinematographer William Daniels."
  ],
  "pros": [],
  "cons": [],
  "forbidden_mixes": [],
  "anchor_requirements": [],
  "best_for_archetypes": [],
  "high_risk_archetypes": [],
  "recommended_carriers": [],
  "color_grade": "Ambient occlusion, soft bloom; 1930s studio silver: about 40% deep black, glossy whites near 90%, no washed-out greys.",
  "lighting": "Light falls in shafts from one high source.",
  "material": "A real 3D set, by default an Art Deco interior (marble, chrome, chandelier, glossy checkerboard floor); outdoors keep the real setting with glossy surfaces (wet pavement, still water) and symmetrical framing.",
  "costume": "",
  "headwear": "Period figures (heads, hats, limbs) walk routes.",
  "jewelry": "",
  "subject_surface": "",
  "environment": "",
  "props": "",
  "atmosphere": "",
  "subject_integration": ""
}
```

</details>

## Source trail

- [Complete bilingual source collection](../../zyx/styles.json): select `no = 5`.
- [Legacy template](../../src/skills/templates/styles_3d/opuscar_05_mgm_silver_b_w_3d_lobby.py): `SKILLS[0]`, `opuscar_05_mgm_silver_b_w_3d_lobby`.
- [Original project description](../../zyx/README.md) · [Saved source page](../../zyx/opuscar98/index.html).
- [Legacy converter](../../scripts/build_opuscar_templates.py) · [Machine-readable provenance](../source-map.json).
