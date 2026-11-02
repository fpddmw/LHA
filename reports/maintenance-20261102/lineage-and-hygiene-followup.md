# Lineage and repository hygiene follow-up — 2026-11-02

The original issues 12 and 16 now have additional implementation and verified historical evidence. Real matched-control results and media-rights conclusions remain distinct open requirements.

## Lineage measurements

`analyze_lineage_cohort.py` reads saved live-mode runs, verifies signed generation receipts and local media hashes, and writes per-run lineage records. It supports old qualitative Critic outcomes without converting their verdicts into current numeric scores. Paired numeric changes require one assessment per candidate with the same recorded scoring profile. Requirement transitions retain their original contract, evidence scope and coverage. Cumulative rendering time follows each candidate's ancestry and preserves unknown costs.

The selected historical cohort contains 12 runs, 36 generated candidates and 14 chain edges. All 36 outputs and all 12 source references have now been verified locally. Depth 1 contains 22 candidates and depth 2 contains 14; there are no deeper trajectories in this cohort. Saved generation wall times total 27,370.79 seconds (about 7.60 hours), incurred historically, with zero new rendering or scoring in this analysis. None of the original-source candidates matches a chained candidate's complete prompt and seeded renderer configuration, so the observed trajectories have no matched restart control.

Three historical RSI edges expose 27 same-contract requirement transitions: 9 pass→pass, 10 unknown→unknown, 4 partial→partial, and one each partial→fail, fail→pass, fail→partial and partial→pass. These summarize the original online findings and their different evidence scopes; they are descriptive observations. Current-rubric degradation effects still need the prepared matched comparison.

Fourteen control plans have verified local inputs. `historical-lineage/proposed-control.json` selects fewshot_006 for two new renders with the same prompt, seed 44 and renderer settings, using historical v2 versus the original source. Both inputs decode with native PTS; the frozen output configuration records the common output length. The previous single render took about 456 seconds; twice that time is only a scheduling reference. The user authorized coordination with the Bernini execution thread, which owns the three GPUs and existing task schedule. Independent final judging remains paused pending the execution owner's current authorization. Current coordination belongs under `out/lineage_control/20261102/coordination.json`.

## Hygiene and recovery

Eight root scratch files totaling 96,482 bytes, together with the empty deprecated directory, moved into `out/maintenance-recovery/20261102-root-hygiene`. The manifest records exact hashes and restoration paths. Root ignore patterns prevent accidentally tracking these scratch names again. No benchmark or experience content was changed by this work.

Git maintenance retained every one of 5,128 objects, every ref and HEAD, with reflog expiry and pruning disabled. `git fsck --full --no-dangling` passed. Object storage decreased from about 727.60 MiB to 720.85 MiB; most of its size is historical media. The largest object is the 88,696,195-byte `zyx/films/opuscar98.mp4`. Removing such historic bytes would change repository history and was not performed.

The refreshed audit checked the current 75-source benchmark and all prompt hashes, and found all 1,175 removed media entries recoverable from indexed Git blobs. One source shared by two historical runs was restored from Git into the isolated recovery directory, with exact SHA-256 verification; it was not reintroduced into the active dataset. The audit now includes exact references in nonignored untracked text as well as tracked text. Dynamically assembled or remote references remain outside that exact-text scope.

Current provenance records source metadata and keeps redistribution/permission unknown. This work supplies concrete recovery and rights-status evidence; it does not assign an unsupported license or publish media.

## Evidence

- `lineage-validation.log`: eight focused offline tests passed.
- `historical-lineage/summary.json`: cohort counts and per-run verified reports.
- `historical-lineage/descriptive-measurements.json`: original-scale transitions.
- `historical-source-recovery.json`: successful exact source restoration.
- `root-hygiene-recovery.json`: reversible scratch cleanup.
- `git-storage-maintenance.json` and `git-object-integrity.json`: preserved objects/refs and integrity check.
- `current-hygiene/media-inventory.json`: current media, references and recovery inventory.

## Current entry checks after data maintenance

The local preflight now validates actual reviewed catalog membership instead of requiring exactly fourteen entries. The verified current catalog contains 15 entries and 56 resources; the none arm exposes none of the curated entries. Two source links in the no-experience design manual were matched by their original Git media SHA-256 to train/020 and train/037 and updated. The actual local preflight passed without a model or GPU call. Curated content and review hashes were unchanged.

Two historical example evaluation cards remain invalid after the separately authorized dataset path migration: both changed only source_video while retaining the previous frozen card signature. Their files remain unchanged by this repair, and the exact comparison is saved in example-card-integrity.json. Contract unit tests use explicitly synthetic frozen cards so this separate data integrity finding is neither silently re-signed nor mistaken for a worker implementation failure.
