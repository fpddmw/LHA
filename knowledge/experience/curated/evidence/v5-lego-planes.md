# Brick-world case (train sample 026): what was converted and what was not

Sources: `v5-train-cases.json` (v5 GLM scores and reasons), the frames of each video sampled at six evenly spaced times, and the exact prompts in the preview records. Bernini, seed 42 to 45, one judge. Frames were opened and compared by the maintainer; they are a sampled view, not a whole-clip review.

**Request (long):** transform the man, truck and surroundings into a brick-built world in the style of The LEGO Movie; the man becomes a workwear minifigure; truck, timber and ground are built from recognizable interlocking pieces; continue unloading long materials with clear brick-hand contact.

| Video | What the frames show | v5 IA | v5 AC |
|---|---|---|---|
| Direct (request text only) | Minifigure and beams converted. Truck, tailgate, hedge, trees, sign, barrier and sky remain photographic; a toy truck appears in the distance. | low | low |
| PE loop, round 1 (291 words, preservation-first) | Minifigure and beam converted. The white truck, tailgate, hedge and sky are photographic. | 2.0 | 2.0 |
| Planner, round 1 (source input) | Same pattern: plastic figure and beam in a photographic yard. | 2.0 | 2.0 |
| Planner, round 2 (continued from round 1; 276 words that name every plane) | The truck side, bed, timber, hedge, trees, barrier and ground are bricks and baseplates. The first moments of the clip still show a smooth white painted panel with the source's shadows. | 2.7 | 2.0 |
| Planner, round 4 (continued from round 2; 313 words; truck recolored red) | Whole scene built. The opening foreground is now red bricks; the final frames show a cluttered wheel and plank corner. | 2.8 | 3.1 |

The judge named the same thing in each low-AC reason: an unrequested mixture of toy-styled subjects and live-action surroundings. The version that listed every plane removed it, and the remaining defect in round 2 was a photographic panel in the first 0.6 s.

**Interpretation corrected against the exact prompts.** The first Planner and PE prompts already specified the truck and environmental construction. The later prompt changed their prominence and construction detail while continuing from an already converted candidate. The subsequent red-truck pass addressed the close opening panel and vehicle/cargo separation. This is useful evidence for revising an explicit but unrealized construction, not a missing-object comparison. Input and seed also changed.

Read the [complete long case](v5-026-long-case.json), [short case](v5-026-short-case.json) and [case-reading index](v5-case-reading.md) for exact prompts, known inputs, full saved reasons and the original comparison sheets.
