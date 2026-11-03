# Experience library rebuild, 2026-11-03

## Why

The task is to recast a video into another world or medium. The older library was organized around preservation and editing (instance identity, connected scope, input conditioning, and so on), was written before the v5 scoring, and partitioned guidance by renderer and task in a way that hid shared lessons. This rebuild reorganizes it around the recast task, adds train-split evidence scored under `lha-low-high-final-v5`, and makes the partition soft.

## What changed

- **Catalog v2** (`creative-experience-catalog-v2`): entries carry `layer` (principle, renderer, condition) and optional `tracks`, `families`, `stages`. v1 snapshots load unchanged. The navigation (`README.md`, `renderers.md`) is generated from this metadata and orders entries principle, then renderer, then condition.
- **21 entries**: 8 principles (`P-*`), 6 Bernini and 2 Ditto renderer entries (`B-*`, `D-*`), and 5 condition entries (`C-short`, `C-long`, `C-craft`, `C-film-world`, `C-hand-drawn`). The fifteen older entries are archived in `knowledge/experience/curated/evidence/superseded-entries-20261103/`.
- **Evidence**: `v5-train-cases.json`, `v5-lego-planes.md`, `pe-token-limit.md`, all restricted to train samples.
- **Builder**: `scripts/build_experience_catalog.py` (with `--check`) validates metadata, evidence ids and hashes and rejects evidence citing a held-out source video.
- **Manuals**: `UNDERSTAND_AND_DESIGN`, `UNDERSTAND_AND_REVISE`, `PROMPT_WRITING`, `GENERATION_INPUT`, `OBSERVATION_DIAGNOSIS`, `PLANNING_RESOURCES`, the READING and README entrances, and the `no-experience` copies are rewritten to the recast workflow (moment, planes, counterparts, medium logic, worst second, compare retained). The no-experience copies carry the same method without empirical conclusions.
- **Retired**: the four legacy static topics (`choose-editing-input`, `express-edits`, `inspect-and-compare`, `use-design-knowledge`) are no longer exposed in `creative_loop_v1`; their files remain for old snapshots.
- **Harness**: `task_track` is exposed in the execution profile; `knowledge_search` aliases point to the new vocabulary.
- **Skills**: `lha-video-review` gets a check order; the three experience skills gain layer placement, evidence status and held-out rules.

## Hygiene and limits

- Held-out sample 067 and every other test-split video are excluded from the library and from the entries' evidence.
- The evidence is one judge, one seed per condition, a handful of train tasks (001, 005, 026 preview; 002, 011 steady-train; plus older fewshot runs). Entries state their status. Family entries for anime, painting and comic have no scored runs and are marked as hypotheses.
- No claim in this library has been tested by a new generation run. The effect of the library on the final score is to be measured by the full vs none comparison.
- The repaired evaluation profile (`7f0d19f7…`) has not been used to re-score the evidence.
