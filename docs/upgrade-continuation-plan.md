# Continue existing work across software upgrades

Authorized 2026-11-05. Status: implemented and verified locally; published with the accompanying code commit. Local changes and offline
tests only; do not connect to, deploy to, restart or change running experiments.

## Contract

The original command and output directory identify an existing experiment. Load
its task list and saved state before considering current defaults. Completed steps
remain complete. Partial Planner tasks retain their context, candidates, reviews,
knowledge, pending operations and consumed generation allowance. An upgrade never
creates another allowance or silently converts old work into missing work.

Code, configuration, knowledge and media versions are provenance. Differences from
current defaults are recorded, not prerequisites for continuation. Retain actual
historical inputs and outputs. Check missing/corrupt artifacts and live ownership
where they affect execution; never respond by automatically regenerating them.

## Implementation scope

1. Campaign and lower-level preparation: reopen saved manifests/configuration,
   retain their tasks, sources, groups and budgets; record current-default changes.
   Existing result reuse covers all methods. A compatibility/import problem must
   not fall through into generation. Preserve existing explicit reuse sources.
2. Runtime and Planner: accept saved execution/knowledge/manual records with new
   implementation code. Replay pending calls with their exact original inputs.
   Use compatibility defaults for absent fields, without creating a new run.
   Completed jobs are reused before version checks or model construction.
3. Direct, PE, PE Loop and Planner variants: restore original phase receipts and
   candidates; preserve both Critic and self-review paths. The original four-render
   allowance remains cumulative. New rendering can prepare a 117-frame CPU input
   copy when required, while keeping historical candidates and ancestry intact.
4. Online reviews, maintenance and independent scoring: reuse original requests,
   outcomes, contributions and activations. Resume missing work using saved
   instructions/configuration where available. Software changes alone never start
   a new evaluation or maintenance task. Missing original material is a reported
   recovery issue, not permission for a replacement call.
5. Recovery preview: report observed saved work and unresolved steps; remove fixed
   zero claims that were not derived from actual records. Documentation consistently
   explains upgrade continuation rather than recommending a new output directory.
6. Upgrade tests: use saved real-run records plus offline scripted models/renderers
   to exercise old manifests, different code/defaults, original commands/directories,
   completed/partial phases, Planner memory and four-render accounting. Assert exact
   external-call counts, including zero repeat calls for completed work. No live API
   calls or GPU execution. Commit and push after verification.

## Boundaries

Distinct experiment arms remain distinct tasks. There is no global filename-based
deduplication, new scheduler, automatic RSI, score rewriting or historical video
replacement. Historical results retain their actual frame counts and scoring
conditions. A new experiment or deliberate repeat requires an explicit new-work
request, not a side effect of updating software.

## Progress

- Plan saved before implementation.
- Saved campaign, batch, task, deployment, knowledge, model-call and phase records
  now take precedence over changed defaults. Upgrade differences are written under
  `upgrade-history/`; original signed inputs/results are retained.
- Original campaign and lower-level commands reuse their output directories. The
  standalone Planner command also detects an existing state without `--resume`.
  Existing stage aliases and physical GPU reassignment retain original task IDs.
  A later campaign stage inherits the original population IDs; newly added benchmark
  rows are not silently admitted into the saved campaign.
- Direct, PE, PE Loop, best-of-N, single-pass Planner, both Loop review families,
  training maintenance and independent scoring reuse their completed phases.
  Result reuse no longer filters historical videos by the new 117-frame recipe.
- Planner recovery restores pending decisions, candidate ancestry, notes, reviews,
  knowledge and original cumulative generation occupancy. Technical settlements
  can reopen once original operations are reconciled. A completed delivery is
  retained; selecting an early candidate remains supported.
- Old wall deadlines are lifted for unfinished work, while original count budgets,
  submitted-operation ownership, charge records and model-call receipts remain.
  A changed launch default does not refill the original four-render allowance.
- Maintenance retains its original materials/contribution/activation. Independent
  evaluation retains its model identities, requests, accepted projections, metric
  components and blind caches. Lost evaluation pointers recover an existing
  evaluation directory rather than creating a replacement scoring run.
- Old video axes remain recorded as observed. Only a future request that explicitly
  needs fixed117 receives a CPU conditioning copy; historical videos stay intact.

## Verification evidence

The portable fixture `scripts/fixtures/upgrade-records-20261104.json` contains
metadata projections from 71 locally saved Direct records and one interrupted
three-of-four Planner state. Original runtime files were read only. Its historical
hashes/axes are provenance, not synthetic performance measurements.

`test_upgrade_continuation` checks those records against newer defaults and uses
scripted execution to interrupt the fourth generation, change implementation and
launch defaults, resume the original saved answer, retain the original four-render
allowance and select v1. Additional cases cover uncertain-call protection, cached
answers, original judge construction and an interrupted scoring pipeline whose
accepted main judgment survives a validator update.

Cross-entry tests cover duplicate process starts, physical GPU reassignment,
missing tool responses with durable render receipts, Direct/PE phase reuse,
Critic/self-review, private knowledge families and scoring-only continuation.
The public smoke blocks external network/model imports and hides CUDA. Local
scripted tests verify orchestration and evidence recovery; they do not establish
GPU compatibility, real-provider availability or quality improvements.

Verification completed on 2026-11-05:

- 516 distinct tests across 46 modules have passing latest results. The broad
  current-suite run exercised 503 tests and caught one accepted-projection receipt
  validation failure. That failure was repaired; the 46-test targeted rerun passed.
  The 96-test affected-entry rerun and final 19-test campaign/public-entry rerun
  also passed without source changes during their checks. These are combined
  module results, rather than a claim of one clean 516-test invocation.
- The guarded public CPU smoke passed 129 tests. Later CLI/scoring changes were
  covered by the targeted runs above. No live models or GPU generation were used.
- Historical fixture checks cover all 71 retained Direct records and the partial
  Planner state; original output records were not edited.
- Local evidence: `out/upgrade-continuation/verified-summary.json`,
  `acceptance/smoke.json`, `final-current/`, `final-affected/`, `final-verify/`,
  and `final-campaign/`. Generated test logs remain outside the source commit.
- Whitespace validation and parsing of every changed Python module passed.

## Operator behavior

Repeat the original command against the original output directory. There is no
upgrade flag, reset, new directory or new generation allowance to select. Changed
software/defaults are recorded while existing work is reused. New physical devices
can be supplied with the existing device options.

A genuinely missing/corrupt original artifact or unresolved submitted operation
remains a recovery issue. Its result is never silently replaced by another paid
call or render. Restore or reconcile the original evidence to continue. Historical
protocol differences remain visible in reports; reuse does not relabel old output
as generated under the newer recipe.

No active experiment was connected to, deployed to, restarted or modified in this
change. Publishing this code does not itself upgrade a running remote process.
