# Seeded experience and self-review family repair

Status: implemented and verified offline. No model calls, GPU work or experiment launch.

## Agreed behavior

Every batch starts from a nonempty reviewed experience corpus. Online `none`
restricts experience exposure during editing; post-task maintenance still reads
the full seeded library. The knowledge map and entry structure are shared, while
each renderer and review family owns its own accumulated library.

For each renderer, Critic review and Planner self-review start from the same seed:

1. Run all 67 tasks in short and long forms with online experience disabled.
   Only the first 40 training tasks may contribute after task settlement. The
   remaining 27 tasks cannot maintain the library.
2. Freeze that family's accumulated library after the run and maintenance settle.
3. Run all 67 tasks in both forms with this frozen library available online and
   all maintenance disabled.

Each self-review arm retains its existing maximum of 536 renders (67 x 2 x 4).
This repair does not change generation, review, model or resource policies.
Post-task contributions remain append-only. Canonical entry/manual curation
remains a separate explicit operation; there is no automatic RSI adoption.

## Implementation

- [x] Split the self-review campaign into ordered accumulation and frozen-use
  stages; keep `self-review` as a convenience command for both.
- [x] Bind each private library to its owning batch, review mode, renderer and
  seed. Verify ownership at initialization/resume, maintenance read, contribution
  ingestion and family freeze. Identical initial content is not shared ownership.
- [x] Require full, nonempty maintenance snapshots at all entry points. Remove
  the fallback to an online `none` snapshot. Keep online exposure independently
  frozen and exclude maintenance traces from the online task.
- [x] Enforce the seed invariant in batch preparation, including read-only arms;
  retain immutable snapshots and explicit errors for incompatible old runs.
- [x] Update CLI, campaign documentation and meaningful offline tests covering
  positive behavior, cross-family rejection, resume and 40/27 maintenance scope.

## Verification and delivery

Use real repository knowledge and temporary test runs with simulated responses.
Confirm equal initial content, independent updates, self-review-only frozen use,
and no changes to online `none` exposure. Report actual tests and remaining
limitations. Preserve concurrent working-tree edits; retain a scoped pre-change
backup and patch under `out/experience_family_fix/20261103`.

## Progress

- Baseline captured before edits. The existing top-level campaign seed guard is
  retained. The missing protections are in lower-level batch/maintenance paths
  and the self-review campaign dependency.

## Implemented result

- `self-review` now executes `self-review-zero` followed by
  `self-review-knowledge`. Each covers 134 conditions and at most 536 renders.
  Only the 80 training conditions in the first stage enable maintenance.
- Critic and self-review libraries start with the same fifteen reviewed entries.
  Renderer and review-family libraries have separate owners, histories and frozen
  receipts. New contributions retain their family through exported snapshots.
- Lower-level initialization and read-only batch preparation reject empty full
  libraries. Missing maintenance bindings no longer fall back to online exposure;
  eligible standalone maintenance initializes a full owned seed. Read-only batches
  cannot enqueue maintenance, even for a row labelled training.
- Owner checks cover original job admission, maintenance reading, cached recovery,
  ingestion, frozen-copy preparation and batch verification. A copied owner label
  does not authorize a foreign revision. Existing unbound legacy runs are retained
  as historical records; prepare a new output directory for this protocol.
- Knowledge content and Skill authority remain unchanged. Maintenance uses the
  existing map and append-only contributions; canonical curation remains explicit.

The broad offline regression run passed 134 tests. It covered campaign routing,
renderer separation, contribution/case discovery, explicit curation, actual
simulated Planner continuation, final review, resource accounting and the unified
result runner. A final focused family suite passed all 13 tests, including the last read-only
admission change. Exact logs and the scoped source patch are in
`out/experience_family_fix/20261103`. These are software tests, not evidence of
model quality or learned experience effectiveness.
