# Pre-experience isolation and multi-GPU campaign finalization

Status: implementation and offline validation complete. No live model, evaluation or GPU jobs were started.

## Agreed behavior

- The public main campaign contains pre-experience, full-experience, Direct and PE Loop. Pre-experience uses the nonempty initial library from its first planning call; it is not a no-knowledge arm.
- Every pre-experience task and its maintenance session read the same frozen initial library. Each settled task can contribute new accounts, comments, clarifications and revision proposals. Other pre-experience tasks never read those increments.
- Training contributions accumulate in the batch's private library. Test contributions are archived for a later batch and do not enter this campaign's full-experience input. The canonical repository library stays unchanged.
- Starting full-experience in the same campaign output automatically freezes and selects the completed training library. Critic-review, self-review, Bernini and Ditto maintain their own ownership; no global library switch is needed.
- A host with N selected GPUs can run N independent task workers. Each task retains the existing generation budget and sequential candidate decisions. Full-experience starts after its pre-experience stage has settled; GPU count does not change the experiment groups, seeds, budgets or scoring protocol.

## Inspection findings

The v5 campaign already binds the first stage and post-task maintenance to the initial library and automatically selects the accumulated library for full-experience. The remaining scheduler still links all pre-experience tasks into the historical accumulating no-knowledge chain. That dependency is unnecessary now that online and maintenance reads are fixed. Shared contribution activation and result registration also use immediate-fail locks, which need bounded waiting for independent GPU workers.

The lower-level public preparation command also retained a legacy no-knowledge default. It now selects pre-experience explicitly. Historical Python fixtures and explicit legacy method selections remain supported for existing records.

The full smoke also found that the v5 status command hid historical `zero` folders.
Current stages now retain their new names, while historical stages appear only
when their actual batch exists. Old no-knowledge output is never relabeled as
pre-experience.

## Implementation

1. Preserve the v5 exposure and split rules. Make pre-experience work units independent while retaining the legacy adaptive chain for historical no-knowledge runs.
2. Serialize only short shared-library/result commits, with bounded lock waiting and durable receipts. Preserve immutable task inputs and handle interrupted activation before subsequent commits.
3. Expose a consistent device override on the public campaign entry, accept explicit devices or `auto`, and document one coordinator with N workers. Check device declarations offline; resolve physical availability only at real launch.
4. Verify fixed initial exposure, training-only accumulation, deferred test contributions, automatic full-experience selection, ownership isolation, parallel claims, concurrent commits, and resume safety with saved/synthetic inputs and scripted models.
5. Update public instructions, run the CPU-only smoke suite, commit and synchronize the scoped changes to GitHub. Keep experiment execution paused.

## Completion record

Completed on 2026-11-04:

- Independent pre-experience claims across N devices; legacy adaptive queues retain their historical dependencies.
- Bounded waiting for private appends and video registration, interrupted-append recovery, and consistent linking when separate tasks propose the same new entry ID.
- Device list/auto overrides on both public runners, matching offline declaration checks, and a pre-experience default on the lower-level CLI.
- Automatic same-campaign full-experience binding and split/family isolation verified. The seed currently contains 21 curated entries. No canonical experience content or scoring standard changed.
- Final CPU-only public smoke: **107 tests passed** across 10 modules. Additional result/dispatch/legacy compatibility checks: **61 tests passed** across 4 modules. The initial smoke's historical-status regression was fixed and the complete smoke rerun successfully.
- Evidence: `out/pre-experience-multigpu-20261104/smoke-final/smoke.json`, `smoke-final/tests/summary.json`, `compatibility/summary.json`, and `configuration-audit.json`. The parallel tests use three real OS processes for claims and scripted maintenance responses for concurrent commits. Real model quality, provider access and GPU deployment remain untested in this task.

Public commands and continuation instructions are in [the experiment guide](public-experiment-guide.md#n-gpus-on-one-host). The implementation and this completion record are committed together. Experiment execution remains paused.
