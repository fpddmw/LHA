# Same-command experiment recovery

Status: implemented and offline validated on 2026-11-05. Experiments remain paused.
No live model request, GPU allocation, video generation or scoring was performed.

## Contract

Repeating the original experiment command against its original output directory
continues the original tasks. Completed work is reused after integrity checks.
Planner context, candidates, pending actions, knowledge bindings, seeds and the
four-submission generation allowance survive interruption. Direct retains its
one-submission allowance. Recovery never grants additional generation slots.

The experiment identity freezes requests, input transformation (117 frames at
24 fps), model and review settings, knowledge and generation policy. Deployment
placement (host, GPU and locks) is separate. Existing absolute artifact paths are
preserved when mounting storage on a replacement node. Concurrent starts cannot
claim the same work. Ambiguous external execution stays blocked until its owned
receipt or definite termination can be established; process death alone does
not authorize repeating a render or a possibly completed model call.

## Implementation

1. Correct original/normalized source verification and null-deadline recovery.
2. Add receipt reconciliation to the existing campaign/batch startup, covering
   Direct, PE phases, Planner and self-review, maintenance, scoring and archive.
   Retain original task identities and recoverable technical interruptions.
3. Separate task storage from current GPU placement. Reuse legacy task locations
   through a durable index. Verify old ownership before changing placement.
   Keep one host-local queue and one renderer per GPU; do not add a scheduler.
4. Replay saved model responses and completed tool results before making new
   calls. Rebuild missing settlement records from original evidence. Preserve
   pending/unknown operations and finite transport retry accounting.
5. Recover maintenance journals exactly once and retain family/seed isolation.
   Continue the same independent evaluation; historical policy (superseded by
   upgrade-continuation-plan.md): changed evaluation protocols required
   an explicit new evaluation, never an automatic full rescore on restart.
6. Extend existing check/status/run interfaces with a recovery preview and clear
   blocked reasons. Preserve ordinary commands. New topics or extra generation
   allowance require a separate explicit change; restart admits neither.
7. Add offline interruption, concurrent-start and GPU-reassignment smoke tests
   through real entry points, with fake external calls/renderers only.
8. Update public commands/documentation, record validation, commit and push.

## Validation

Exercise interruption after video/response persistence, before task settlement,
during PE review/selection, after fourth generation before delivery, after
experience activation, and between independent judges. Reissue the original
command and compare actual external-call counts, video hashes, task identities,
seed sequence and generation accounting. Exercise duplicate starts and changed
GPU assignments. Validate no implicit migration of historical protocols.

## Progress

- Plan saved before code edits.
- Initial inspection found reusable durable queues, response caches, activation
  journals and per-phase PE receipts. The missing recovery integration and device
  independence are now implemented. Original/normalized source checks and the
  null-deadline recovery command are corrected.
- Recovery integration implemented across campaign, device dispatch, runtime,
  Planner, PE phases, maintenance and independent scoring. New task locations are
  independent of GPU assignments; historical locations have a durable index.
- Atomic state/model-answer writes now flush before replacement. Original model
  completions and render receipts repair missing local responses without new calls.
- Public command defaults are unchanged. Check/status expose recovery scope;
  this historical test did not cover code upgrades. Upgrade coverage is recorded in
  upgrade-continuation-plan.md. No live work was launched.
- Queue initialization now validates the complete original task list before any
  insertion. A rejected additional task leaves the queue unchanged.
- Public commands and per-method recovery behavior are documented in
  `docs/public-experiment-guide.md` and linked from runtime/configuration guides.
- Acceptance: 122 public smoke tests and 95 runtime regression tests passed
  (217 total). The 11 dedicated recovery tests cover the original CLI, fourth-render
  delivery continuation, missing tool responses, unknown calls, duplicate process
  starts, GPU reassignment, frozen source verification, scoring resumption and task
  admission. Existing maintenance tests also verify activation recovery exactly once.

## Verification evidence

- `out/same-command-recovery/acceptance/smoke.json`: passed; network blocked,
  GPUs hidden, model/GPU library imports blocked, zero live external calls.
- `out/same-command-recovery/acceptance/tests/summary.json`: 122 passed.
- `out/same-command-recovery/runtime-acceptance/summary.json`: 95 passed.
- Earlier failed probes remain in adjacent directories. They exposed the queue
  admission gap and obsolete expectations for automatic rescoring and a numeric
  task deadline; the final tests cover the corrected behavior.

Reproduce the public smoke without API credentials or GPU access:

```bash
python scripts/smoke_experiment_campaign.py --output out/recovery-smoke-review
```

Use a fresh smoke output directory to preserve previous verification evidence.
These tests exercise real orchestration with scripted model/render/encoder outputs.
They do not establish remote provider availability, CUDA compatibility or performance.
Superseded limitation: that implementation covered same-version restarts only.
The upgrade-continuation plan now supports updated code in the original directory,
retaining saved inputs, results and allowances. Ambiguous external submissions
still require their original receipt or explicit evidence-bound reconciliation.
