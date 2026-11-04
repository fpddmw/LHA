# Uniform 117-frame experiment inputs and count-only task budgets

Approved change, 2026-11-04. Experiments remain paused.

All new experiment arms use the same deterministic source preparation: sample
117 frames uniformly across the entire original clip, including both endpoints,
and encode at 24 fps. Short sources repeat nearest frames; long sources subsample.
The original files remain unchanged. Record original hash, frame count, FPS,
sample indices, normalized hash and policy identity. Planner, renderer and final
evaluation use the normalized source. Every generated candidate must also contain
117 frames at 24 fps. Existing native-length results are historical, not reusable
under this contract. Both renderers use identical source timing.

Remove elapsed-time admission and stopping limits from new campaign tasks,
post-task maintenance and independent evaluation. Retain elapsed-time accounting,
the four submitted-generation budget, model-led input/prompt/selection decisions,
and existing non-time controls. Transport/connection timeouts and process-failure
detection remain technical recovery mechanisms. Explicit finite policies on
historical runs retain their original meaning; never rewrite frozen receipts.

Implementation checklist:

- [x] Shared source normalization and frame provenance; renderer/output checks.
- [x] Nullable time budgets across resource accounting, workers and maintenance.
- [x] Campaign/configuration/commands and current documentation updated.
- [x] CPU-only regression checks, including the fifth-render refusal, slow-call
      completion, source endpoints and incompatible historical result reuse.
- [x] Commit and synchronize the authorized changes; no model or GPU calls.

Use a new output directory when starting this protocol. Runtime plan/profile hashes
must prevent resuming an incompatible old input plan as a uniform-frame batch.

## Implementation and validation

- `experiments.video_contract` normalizes inputs once per source hash and saves
  exact full-span indices. Unified and standalone CLI preparation use this path.
  Bernini consumes the prepared time axis directly; Ditto receives explicit indices.
- Registration, scoring and shard export carry the prepared source and its original
  identity. Candidate decoding rejects the wrong frame count or FPS. Reuse checks
  actual media, not only a declared output profile.
- Resources, accounting, resident supervisors, retry/recovery and candidate selection
  accept a null deadline. Maintenance and independent evaluation use the same
  no-deadline setting. New default reminders depend only on generation count.
- Campaign configuration v6, public launch/configuration docs, the current operation
  reference, local full configuration package and Feishu command page are synchronized.
  Approved experience prose and scoring definitions were unchanged.

CPU verification: 244 distinct tests across 21 modules passed, using the public
smoke suite and additional renderer/accounting/recovery tests. Initial failures
were assertions pinning the previous frame/time defaults; those modules passed
with the new expected contract. Original failure logs remain available.
`out/fixed117-checks/verified-summary.json` identifies each final module result.
The local command guide also passed 7 JSON-block checks, 19 shell syntax checks,
actual configuration parsers and its hash-filling helper on disposable fixtures.

New focused coverage includes deterministic output across separate preparations,
short/long-source endpoints, original-file preservation, wrong-length rejection,
normalized-source scoring and shard roundtrip, arbitrarily elapsed task time,
and refusal of a fifth render while model-side finishing remains available.
The public smoke command includes these checks. No real API, model, GPU or quality
evaluation was run. Use the public guide's smoke command to reproduce verification.
