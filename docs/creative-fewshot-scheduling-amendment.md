# Five-position early judging deployment

Date: 2026-11-01. Authorization: the explicit execution handoff in
[creative-fewshot-sol-handoff.md](creative-fewshot-sol-handoff.md).

The execution owner deployed `scripts/creative_fewshot_schedule.py` as an outer
scheduling adapter. The frozen renderer, Planner, optional Critic, knowledge,
judge adapters, evidence construction and rubric remain byte-for-byte unchanged.
The original runtime is commit `42e18b363ca43986440af07ae1018e4f81550956`; its
profile remains `e0f7709309e41556dd02b951e6e0c890597dc6ad3fc653f2374c70485618dc72`.
The adapter is outside the frozen profile's source/entry-point set. It verifies
the original profile rather than replacing it. Adapter snapshots, deployment
hashes and operator actions are retained under the result directory's
`scheduling/` tree.

## Migration and ownership

The old parent coordinator was waiting for its generation pool. The execution
owner stopped that parent alone, leaving the existing GPU worker and its active
render/model calls intact. This prevents the old in-memory all-candidate final
scoring stage from racing the approved owner.

The adapter waits for a completed arm receipt and an idle worker IPC boundary.
It stops that worker momentarily, checks that every existing Loop task is
complete and no queue job is running, verifies the completed full-arm receipt,
and records the evidence before retiring the old processes. An unsafe boundary
continues the original worker. The new generation pool starts only after the
old owner is retired and the original batch lock is acquired. Receipt reuse
preserves completed arms; no uncertain render is resubmitted.

`ownership-migration.json`, `legacy-retirement-authorized.json` and
`legacy-retired.json` distinguish the initial parent stop from the later verified
idle-boundary retirement. Never resume the old parent into all-candidate judging.
The same authorized single device is used, with no instance shutdown action.

## Eligible scoring and reuse

Direct and each Loop's first candidate become eligible after their completed
receipt, request binding and media hashes pass validation. A delivered Loop adds
its selected final candidate, including an earlier candidate if selected. There
are exactly five reporting positions: Direct, full-first, full-final,
none-first and none-final. The existing cache binds the exact original request,
source, candidate, protocol, judge identity and judge-adapter hash. Identical
first/final positions reuse that cache entry.

Each provider has one executor and a durable provider lock; each candidate also
retains the existing cache/call locks. A separate scoring-owner lock permits the
initial early-scoring process to finish before the adopting scheduler takes
over. Successful calls and bounded failed attempts remain in their original
cache directories. Invalid reports receive no semantic retry. Both judges keep
their frozen independent inputs and never feed back to generation.

The scheduler checks current-topic receipt availability while generation is
running. This is the early-scoring dispatch loop, separate from the existing
15-minute human-facing heartbeat. It creates no additional automation. A judge
failure permits current-topic generation to finish and blocks archive/next-topic
admission. Loop delivery remains uncapped.

## Archive behavior and verification

The adapter reuses the frozen summary and archive implementation. It supplies
only eligible judgments and an explicit HTML display record for other retained
trajectory candidates: `not independently scored`. These records contain no
numeric scores and create no final-judge cache entries. The archive additionally
contains `scoring-scope.json` with selected/first identities, unscored
intermediates and the adapter hash. Every original video and complete trace is
still copied and hash verified. Five-position comparisons and judge disagreement
remain separate per judge.

Thirteen focused offline checks passed: eight existing coordinator/recovery checks
and five adapter checks covering early receipt/hash rejection, five-position
deduplication, unscored intermediate archival and restart reuse, provider
serialization, and a judge failure blocking the next topic while current-topic
generation finishes, and confirmed-stop/active-job safety at the legacy migration
boundary. These are software fixtures, not benchmark results. A waiting adapter
was replaced before it owned any generation to add that confirmed-stop check;
both adapter revisions and the replacement record are retained.

The original execution owner remains responsible for retrieving and verifying
each completed topic archive locally, the complete seven-topic comparison and
the final readable overview. Runtime PIDs, current progress and private paths
belong in the ignored live checkpoint, not credentials or public documentation.

## Supplemental validation disposition

The main chat independently reviewed one descriptive-word false positive after
early GLM judging. The outer cache adapter now recognizes its exact hash-bound
supplemental review while preserving the frozen validator, original answer,
original rejection and all scores. Native and supplemental validation statuses
remain distinct in position summaries and archive scope records. See
[the complete case and bounded checks](creative-fewshot-supplemental-validation.md).
Three additional validation checks passed alongside the thirteen checks above.
