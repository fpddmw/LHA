# 001 | Wings: Silent-era 3D Dogfight, Tinted Ortho B&W

[Knowledge map](../README.md) · [Reading manual](../READING.md)

Aircraft-mounted viewpoints, orthochromatic grading, and projection wear work together to present a silent-era dogfight.

## Editorial reading and design relationships

The source presents a 3D dogfight through the appearance of a silent-film print. Nose, upper-wing, and over-the-shoulder positions place the camera within the flight. The values assigned to sky, ground, and silhouettes make the airspace readable, while vibration and visible supports establish the viewing position. Amber tint is only one component of this design.

An iris, several hard cuts, and a cloud-white transition organize entry, pursuit, and departure. Selective color on the protagonist, specific frame rates, and handoffs also serve the larger anthology. Their functions can be studied individually; the current design determines which to adopt.

## Further reading

- [Composition, light, and time](../guides/time.md): compare related designs within this topic.
- [Combining styles and methods](../guides/combination.md): compare related designs within this topic.
- [004 | Cimarron: 1889 Sepia Albumen Panorama](../entries/opuscar-004.md): Compare another historical photographic treatment, organized through a print surface and a widening panorama.
- [032 | Ben-Hur: 3D Circus Chariot Race, 65mm Epic](../entries/opuscar-032.md): Compare vehicle-mounted viewpoints, staging, and medium appearance in 3D action.

## Complete source material in English

The following is the preserved English original from OPUSCAR. Clawd, the orange identity color, and handoffs to neighboring films serve its anthology. Colors, actions, timings, and Avoid clauses belong to this case. The original project used code-based drawing and 3D rendering; these records do not establish per-case Bernini results. The complete bilingual record remains available at the source link below.

![Original reference frame for Wings](../../zyx/img/opuscar98/01.jpg)

### Original identifiers and segment position

```json
{
  "no": 1,
  "year": "1927/28",
  "title_en": "Wings",
  "decade": "C1",
  "kind": "3D",
  "tone": "B&W",
  "t0_seconds": 12.917,
  "duration_seconds": 5.0,
  "style_en": "Silent-era 3D Dogfight, Tinted Ortho B&W",
  "frame": "img/opuscar98/01.jpg"
}
```

### Ingredients

- three.js 3D
- Orthochromatic black and white
- Silent-film tinting
- Projector wear and iris

### Original author's design explanation

A three.js dogfight graded like a 1927 orthochromatic print: white skies, deep blacks, an amber tint, gate weave and scratches. Wings is remembered for aerial combat shot from cameras strapped to the planes, so most cameras here ride on the planes.

### Complete original style prompt

Smooth-shaded 3D graded as a silent-era orthochromatic print: high contrast, reds go black. Sky near-white, ground in readable mid-greys, deep blacks (25-35% of frame) only in silhouettes. Tint: blend whites half-way toward amber #FFCC80, so the sky is pale cream-amber, never solid orange; blacks stay black. Only the hero the story centres on keeps colour, whole figure at ~70% saturation (e.g. #D97757); every lamp, fire or other light source stays grey. 24 fps gate weave (±1 px), flicker (±5%), fine grain (±4%), 1-3 thin scratches, sparse dust, rounded corners, vignette; open on a 1 s iris. Signature shot: a camera rigged to something moving with the subject, rig in frame; then chase and POV. Cut every 2-3 s; white out through cloud, smoke or glare. Reference: William Wellman, *Wings* (1927). Avoid: motion blur, colour in the greys.

### All shots in their original order

#### 1. open | 0.9 seconds

Head-on over the cowling: Clawd in a leather cap with goggles pushed up sits between the struts; the iris opens and the camera pushes in slowly.

#### 2. dogfight | 0.6 seconds

Wide aerial: the planes circle among the clouds above patchwork fields and chalk trenches, one Fokker trailing black smoke; a slow push in.

#### 3. cockpit | 0.8 seconds

Cowling camera with engine shake: Clawd looks back at the Fokker on its tail and raises an arm as the twin Vickers flash.

#### 4. enemy | 0.8 seconds

From the Fokker's upper wing, its guns firing, chasing Clawd's SPAD ahead; the camera rides fixed to the enemy plane.

#### 5. dive | 1.1 seconds

Over Clawd's shoulder as the SPAD dives: the upper wing and wires in front, shell craters and zig-zag trenches rushing up.

#### 6. clouds | 0.8 seconds

The SPAD, ghostly in the cloud bank, flies at the camera; the fog thickens until the frame whites out to cream.

### Direction and handoff

Clawd is the American pilot: leather cap, goggles, white scarf, seated in the SPAD. The prologue hands over to the opening frame and the iris opens in the first beat; then five hard cuts, roughly every two beats. Around beat 5 Clawd looks back and the guns fire, and the cloud shot whites out into the cream that opens No. 2.

### References named by the author

William A. Wellman, 1927 · Harry Perry (aerial photography) · Tinted silent-era release prints · RFC aerial photographs of the Somme, 1916–18

The named artists, filmmakers, and works are the original author's reference statements; they were not individually verified through external historical research in this reorganization.

## How the legacy template represents this material

The converter allocated selected sentences to fixed fields by keywords, usually retaining the longest sentence in each field. Camera, editing, timing, and unassigned material went into notes. Read those fragments with the complete design above. Default risk fields such as `identity_risk`, and `common_failure_modes` derived from Avoid clauses, are converter annotations or author advice rather than measured failure records.

<details>
<summary>Complete legacy template data, unchanged</summary>

```json
{
  "strategy_id": "opuscar_01_silent_era_3d_dogfight_tinted_ortho_b_w",
  "style_family": "styles_3d",
  "title": "Silent-era 3D Dogfight, Tinted Ortho B&W",
  "description": "A three.js dogfight graded like a 1927 orthochromatic print: white skies, deep blacks, an amber tint, gate weave and scratches. Wings is remembered for aerial combat shot from cameras strapped to the planes, so most cameras here ride on the planes.",
  "reference_image": "zyx/img/opuscar98/01.jpg",
  "tags": [
    "three.js 3D",
    "Orthochromatic black and white",
    "Silent-film tinting",
    "Projector wear and iris"
  ],
  "intensity": "normal",
  "world_rewrite_cost": "high",
  "identity_risk": "low",
  "common_failure_modes": [
    "motion blur, colour in the greys."
  ],
  "prompt_compilation_notes": [
    "fps gate weave (±1 px), flicker (±5%), fine grain (±4%), 1-3 thin scratches, sparse dust, rounded corners, vignette; open on a 1 s iris.",
    "Signature shot: a camera rigged to something moving with the subject, rig in frame; then chase and POV.",
    "Cut every 2-3 s; white out through cloud, smoke or glare.",
    "Reference: William Wellman, *Wings* (1927)."
  ],
  "pros": [],
  "cons": [],
  "forbidden_mixes": [],
  "anchor_requirements": [],
  "best_for_archetypes": [],
  "high_risk_archetypes": [],
  "recommended_carriers": [],
  "color_grade": "Tint: blend whites half-way toward amber #FFCC80, so the sky is pale cream-amber, never solid orange; blacks stay black.",
  "lighting": "every lamp, fire or other light source stays grey.",
  "material": "",
  "costume": "",
  "headwear": "",
  "jewelry": "",
  "subject_surface": "",
  "environment": "Sky near-white, ground in readable mid-greys, deep blacks (25-35% of frame) only in silhouettes.",
  "props": "",
  "atmosphere": "",
  "subject_integration": ""
}
```

</details>

## Source trail

- [Complete bilingual source collection](../../zyx/styles.json): select `no = 1`.
- [Legacy template](../../src/skills/templates/styles_3d/opuscar_01_silent_era_3d_dogfight_tinted_ortho_b_w.py): `SKILLS[0]`, `opuscar_01_silent_era_3d_dogfight_tinted_ortho_b_w`.
- [Original project description](../../zyx/README.md) · [Saved source page](../../zyx/opuscar98/index.html).
- [Legacy converter](../../scripts/build_opuscar_templates.py) · [Machine-readable provenance](../source-map.json).
