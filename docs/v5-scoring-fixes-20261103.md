# V5 evaluation repair and re-evaluation preparation

Authorized scope: repair status normalization, record CLIP text truncation and actual
coverage, and prepare a fresh v5 re-evaluation entry. No live scoring is authorized
in this work. Scoring definitions, experience, Planner and generation stay unchanged.

1. Limit numeric status repair to the explicit `observed` alias. Preserve invalid
   original fields and their errors; retain track-specific applicability handling.
2. Save exact CLIP input IDs and masks, the decoded text actually encoded, original
   and retained token counts, truncation side and token coverage. Keep the current
   feature calculation; surface partial-text scope alongside its diagnostic score.
3. Bind the existing video cohort to a fresh v5 profile and output directory.
   Provide offline preparation/verification and a separately explicit execution
   command. Reuse the existing judge, evidence and cache implementations.
4. Verify invalid-status handling, short/long text coverage, diagnostic propagation,
   immutable preparation and execution guards with offline tests. Record actual
   scope and hashes; do not run the re-evaluation.

Implementation complete. Fifty-six offline tests passed, including full field
projection of ambiguous status words, valid observed aliases, masked/padded CLIP
inputs, prefix/suffix truncation, exact encoder input recording and propagation,
frozen preparation, execution refusal without --execute, and CLI handoff.
Encoder pipeline checks used explicit stub models on a synthetic video; no real
CLIP/DINO values or judge scores were computed.

All 82 protected scoring-standard and experience files retained their hashes.
The scoring rubric and v5 metric definitions are unchanged. Field projection is
now v3; feature provenance is v3. Their implementation hashes produce a new v5
profile: `7f0d19f741aef98800010a2ef192104c31129c943856a1a16b7a9c7c359a1dd1`.
Original failed/normalized fields remain in receipts. Only observed with a valid
numeric score and sufficient evidence can become scored. Unknown/missing/other
status words receive the existing unknown-field projection.

CLIP records original and actual input IDs, attention mask, original and retained
token counts, truncation side, model/tokenizer limits, a content-token span and
decoded text. Decoded text is tokenizer-normalized, not a source character slice.
The target-text-gain diagnostic includes its full/prefix/suffix coverage alongside
the score. The embedding, truncation policy and score formula remain unchanged.

## Prepared cohort and commands

Fresh output: `out/four_video_preview_20261102/glm-v5-repaired-20261103`.
The manifest binds 8 original short/long task conditions and 58 completed unique
task/video pairs, including retained candidates. Shared first/final media use one
job per original task. All media hashes were checked. Only GLM is selected; no new
blind comparisons, generation, or Planner feedback are scheduled by this entry.
Old scoring scripts, results, profiles and cache namespaces are preserved.

Offline verification (safe now):

```sh
python scripts/preview_reevaluation.py verify \
  --output out/four_video_preview_20261102/glm-v5-repaired-20261103
```

After separate user authorization, in an environment with the declared encoder
dependencies and credentials, the prepared entry can call the existing scoring CLI:

```sh
python scripts/preview_reevaluation.py run \
  --output out/four_video_preview_20261102/glm-v5-repaired-20261103 \
  --budget-config /path/to/existing-compute-budget.json \
  --credentials /path/to/private/openrouter.env --execute
```

This command has NOT been run. Missing --execute, dependencies or compute config
stops before judging. The profile, judge, request plans and media must match the
prepared manifest; implementation changes require a fresh preparation. Existing
scoring code owns recovery and cached calls. The local verification environment
still lacks torch/transformers; real encoder execution remains untested here.

Evidence: `out/v5_scoring_fixes_20261103` (test log, protected-file hashes,
scoped implementation patch and verification receipt).
