# Two-level RSI implementation

2026-10-31 Wiki/proposer extension: see [the approved upgrade and implementation](wiki-proposer-upgrade-plan.md). The authorized human-assisted starting library now links three contextual concepts and four archived cases. The proposer can inspect linked references and recorded development frame comparisons, revise concepts as well as experience, and consume actual failed-replay feedback in a bounded revision series. The exact model-facing interface is demonstrated locally with scripted replies. Real model-led knowledge improvement and the seven Bernini delivery loops await the user's review; no live experiment or automatic adoption occurred in this extension.

This implements the calibrated architecture in `two-level-rsi-design.md`. It is an opt-in runtime and a set of executable experience-revision tools. New video quality, automatic experience gains, and cross-renderer transfer have not been established by this implementation.

## What a Planner sees

The original request, source overview and latest candidate/observations remain central. Context version 3 adds a compact requirement ledger, attempt history, target prediction checks, collateral regressions and complete concise experience navigation. Existing reading, observation, notes, dynamic workspace and candidate tools remain available. There is no prescribed sequence of reasoning or route approval form.

The new model-facing instructions are the complete `src/planner_harness/RSI.md`. The additions to the existing interfaces are:

```json
{"action":"requirements","arguments":{"items":[
  {"id":"E1","text":"Apply an illustrated storybook treatment.","kind":"edit","priority":"core"},
  {"id":"P1","text":"Retain the writing action and the relation between hand, pen and notebook.","kind":"preserve","priority":"core","origin":"source_relation","temporal":true}
]}}
```

```json
{"action":"generate","arguments":{
  "input_video":"v1",
  "prompt":"The complete English instruction for this input goes here.",
  "intent":{"targets":["E1"],"change":"Express pigment and paper as a connected surface treatment.","expect":"The illustration medium becomes clear without replacing the writing scene.","baseline":"v2","checks":{"E1":"improve","P1":"same_or_better"}},
  "contenders":["v2"]
}}
```

These are interface examples, not observed model decisions or recommended prompts for every task. `checks`, failure hypotheses, contenders and working notes are optional. A generation's three compact intent fields are required in RSI mode. The harness records unresolved requirements at finish, so the model does not retype the ledger. Requirements can be corrected with a reason; earlier evaluations retain their original version.

The model chooses whether to continue an input, return to an earlier candidate, restart from the original, or stop. The ledger does not route, stop or rank the model's task. A target prediction hit and an unrelated regression appear separately. Missing evidence yields unknown bounds, not a midpoint or a fabricated success.

## Inner RSI execution

1. A normal Planner generation tool call creates a signed job containing the real input, exact prompt, requirement version and intent. Only the renderer's actual inputs are sent to the renderer.
2. Collection verifies provenance and video output, then schedules one automatic Critic job. The comparison baseline defaults to the latest reviewed candidate under the current requirements, even when generating from source. Source, output, actual parent, baseline and optional contenders must fit four unique videos. The runtime does not discard contenders to fit the limit.
3. The Critic uses instructions, knowledge and model settings frozen independently of the Planner experience version. It assesses the original task before opening generation prompts; it does not see the Planner prediction during outcome assessment.
4. The Critic writes one grounded verdict list. The runtime derives compatibility findings instead of requiring duplicate authoring. It can flag missing requirements and important damage. After opening process context it can attach overlapping failure hypotheses. It leaves the next route to the Planner.
5. `ledger.py` joins verdicts to the actual attempt, checks narrow predictions when evidence supports them, retains unknowns and collateral losses, and presents the result to the same Planner conversation. Notes remain optional.

The online ledger uses equal weights within the declared edit/preserve and core/detail item sets. These are task-local feedback measures. The independent benchmark retains its separately frozen source-card groups and scoring protocol. Changing the Planner checklist cannot change the final benchmark card.

Response-only model calls have a default three-attempt budget with backoff, per-attempt request/outcome records, and one accepted response. Internal retries are disabled only on a copied client, leaving shared clients unchanged. Exhausted calls and ambiguous legacy submissions have explicit reconciliation commands. Rendering has a separate started marker and no automatic uncertain rerun. Live experiment arms quarantine failed tools before Planner can consume another paired seed; same-job recovery retains the logical attempt and seed. Legacy runs retain their old context/tool contract.

When explicit prediction checks are absent, the ledger checks target attainment relative to the baseline. It labels these derived checks and leaves the free-text mechanism prediction unscored. Unrelated attempts do not reset a target's known nonachievement count; unknown targets have a separate count. Temporal observations include interval coverage. A supported local counterexample can establish failure; sampled success remains a sampled observation with whole-interval status unknown until covered.

## Experience and knowledge

The seven staged E1 topics retain 45 rule cards. The calibration distinguishes observations, mechanism hypotheses and budget recommendations, and corrects exaggerated certainty and mismatched conditions. Explanations now address property-to-part binding, conditioning information, identity reconstruction, and connected visual fields. The connected-field strategy remains unvalidated; a request for a small repair is not a spatial edit mask.

An experience catalog stores each card's condition/action summary, evidence status, renderer scope and full-text read target. All 45 assisted summaries are visible, labeled applicable, renderer unknown or other-renderer only. The renderer comes from execution.renderer.backend. Disabling knowledge removes summaries/read access from Planner and leaves Critic unchanged.

The assisted E1 is explicitly selected through `experience_catalog`. It is still staged, human assisted and unvalidated. It has not replaced the active shared library. Immutable run snapshots retain the exact card text and metadata used by that run.

## Outer RSI execution

`scripts/run_rsi.py` provides these operations:

| Operation | Executed behavior |
|---|---|
| `splits` | Freeze operator-supplied metadata assignments; reject source/hash/group overlap and exposed sources outside D. |
| `collect` | Read D runs and independent scores joined by output hash. Produce deterministic first-attempt, route, target repair, prediction and major-damage agreement statistics with missing denominators. Optional reviewed criterion alignment enables itemwise agreement. Historical intents remain missing. |
| `propose` | Present compact aggregates/case summaries and paged full evidence. Stage at most three actual card changes, with evidence, counterexamples, target decision points and predicted behavior. A semantic body diff counts even when its metadata is unchanged. |
| `replay` | Restore only a saved pre-decision context and eligible historical artifacts. Let Planner read, observe and work until generate/finish, then intercept the decision before any renderer or evaluator dispatch. |
| `paired-replay`, `review-replay` | Repeat base/candidate decisions on identical neutral prefixes and current instructions; gate on declared behavioral shifts. Reviewed labels handle changes of visual realization. |
| `round` | Resume collect → bounded proposal → paired replay; readiness requires the predicted shift. Starts no validation render or publication. |
| `freeze-cycle` | Freeze code, initial Planner library, Critic instructions/non-experience knowledge, model profiles, splits, seed sequence and budget for the whole experiment cycle. |
| `prepare-validation` | Pin D/V/T execution to its cycle. Live V requires a passed paired replay; T requires reviewed E_final adoption and retains cycle E0 as base. Starts no jobs. |
| `run-validation` | Run/resume one base/candidate arm, or the single-pass control, through the existing signed-job worker interface. |
| `run-control` | Run direct input or three fixed-prompt samples, reusing the single-pass prompt, its actual first sample, and the paired seed schedule. These deterministic controls are labeled separately from adaptive Planner behavior. |
| `judge-protocol`, `judge-run` | Expose the new English independent protocol fingerprint; score completed candidates through a separately configured compatible model endpoint, with blind inputs and durable calls. |
| `record-arm`, `validate` | Verify every output/score join, retain costs and unknowns, then evaluate the predeclared paired gate. |
| `batch-init/run/status/retry` | Use the existing durable GPU/LLM/CPU queue for all task/arm dependencies, bounded slots, restart recovery and isolated failures. |
| `reconcile-call`, `recover-tool`, `remote-fetch` | Resolve response-only retries or recovered signed outputs without silently creating new render samples. |
| `calibration-prepare/run/review` | Freeze saved cases, score with the proposed independent profile, compare actual judgments and record explicit review. A status string alone cannot authorize scoring. |
| `report`, `health`, `drift`, `canary` | Report all five arms/tracks, selected versus first, costs/unknowns, health measures, fixed-video judge drift and reviewed rollback suggestions. |
| `critic-anchor`, `critic-drift` | Repeat an existing signed Critic request in a separate directory under the same cycle; compare requirement verdicts and unknown transitions on identical evidence. No rendering. |
| `adopt`, `reject`, `rollback` | Publish a specifically reviewed validated library, record rejection for future proposals, or restore the previous complete library through a recoverable transaction. Replay fixtures cannot authorize publication. |

The proposer can return no change. It chooses which full cases to read; a proposal is not a fixed form for how it reasons. The revision envelope exists so software can apply and audit the resulting library change.

Paired replay removes prior knowledge-read text, notes and derived workspace text from both arms; it retains actual earlier prompts, observations and results. Both arms use the same current manuals. Repeated samples alternate arm order and have durable call records. Behavior is conditional on the saved prefix; a new library cannot undo how that history was produced. The one-sided replay command remains a diagnostic. Video-quality claims require held-out rendering and independent evaluation.

## Validation and selection

Validation uses one predeclared primary decision measure: non-improving generations, selection regret, or success within budget. The exploratory acceptance gate also requires core preservation not to decrease and success count not to drop by more than one task. It is a development selection rule, not a statistical non-inferiority result.

The main loop metrics and adoption gate use Planner's actual selection. The frozen common selector ranks lower bounds (core preservation, edit, detail preservation), prefers confirmed absence of major damage, and breaks ties by earlier generation. Unknown candidates remain eligible with their uncertainty intact. This selector supplies direct/best-of-three choices and a separate loop diagnostic. Partial independent evidence preserves identifiable selected metrics and gives regret/improvement bounds. A gate passes or rejects only when the available bounds settle its conditions; overlap remains incomplete.

An independent utility must be frozen explicitly for selection-regret and non-improving-attempt metrics. Raw semantic components and all unknowns remain available; utility is not the task's universal definition of quality. Attempts that did not improve it are retrospective outcomes, not necessarily avoidable mistakes.

The final judge adapter reuses frozen task cards, timestamp-aligned evidence, applicability rules and the existing semantic/design/creativity scoring machinery. It uses an English prompt fingerprint and an independent model profile, suitable for the intended Claude endpoint. The concrete Claude model, credentials and reviewed calibration are still required before real scoring. This implementation does not silently use GPT final scores as new Claude measurements.

## Running it

Use the project's installed Python environment and existing worker command. `--rsi` or `--rsi-config` enables the new inner runtime in `scripts/run_planner_harness.py`. A candidate catalog can be selected with:

```json
{"experience_catalog":"knowledge/staged/e1-20261030/catalog.json","seed_schedule":[42,43,44]}
```

Examples of local preparation:

```text
python scripts/run_rsi.py collect --runs <saved-run> ... --splits <splits.json> --output <development.json>
python scripts/run_rsi.py propose --development <development.json> --output knowledge/staged/<candidate> --execute
python scripts/run_rsi.py replay --input <run>/calls/<event>/input.json --catalog knowledge/staged/<candidate>/catalog.json --output <replay-dir> --execute
python scripts/run_rsi.py freeze-cycle --splits <splits.json> --protocol <protocol.json> --output <cycle-dir>
python scripts/run_rsi.py paired-replay --config <paired-replay.json> --output <replay-dir> --execute
python scripts/run_rsi.py prepare-validation --splits <splits.json> --proposal <proposal.json> --protocol <protocol.json> --cycle <cycle-dir>/cycle.json --replay-gate <replay-dir>/result.json --split V --output <validation-dir>
python scripts/run_rsi.py batch-init --manifest <validation-dir>/manifest.json --service-config <service.json> --directory <local-batch-dir> --arms base candidate
python scripts/run_rsi.py batch-run --directory <local-batch-dir> --execute --once
```

Model/renderer operations have explicit `--execute` flags. Publication requires concrete user review and a reviewer name; an implementation authorization does not publish a candidate automatically. Do not run two operating systems as concurrent owners of the same run: existing Windows and Linux lock domains remain distinct.

Keep the queue's SQLite database on the owner's local disk, not a Windows UNC share. Batch slots use the existing queue limits (`gpu`, `llm`, `cpu`); use one GPU slot per renderer allocation. `--once` drains currently runnable/dependent work and exits. Failed tasks remain isolated; repair or reconcile their exact job, then explicitly retry that queue job. Health reports are immutable revisions with a latest pointer. Live worker/config/code changes start a new cycle.

For paired replay configuration, provide inputs keyed by collected decision ID, base_catalog, candidate_catalog, cycle, repetitions and targets. Formal replay and validation must use the same cycle; the non-experience library, reading manual and Planner model are pinned to it. A probe without a cycle remains a software/development diagnostic and cannot open live V validation.

Freeze a small anchor set and its review cadence before a live batch. `critic-anchor` reuses the signed request's source/candidate and requirement version, but uses a new output directory for a new measurement. It verifies the cycle Critic profile and material hashes. `critic-drift` reports changed verdicts including known/unknown transitions; independent `calibration-run` plus `drift` measures the final judge on the same saved videos. These are executable measurement commands; this implementation has not scheduled or dispatched recurring paid anchor calls.

For remote Ditto, service configuration can select `remote_renderer` with host, port, username, dedicated POSIX root, python, repo, verified_manifest and password_env. The adapter verifies host keys, uploads the signed request/input, creates an exclusive claim, launches the existing worker and fetches verified output. It never copies Planner/Critic API credentials. A remote claim without a response remains uncertain; `remote-fetch` only retrieves, and recovery never silently redispatches. Actual SSH/cluster transport is still a live prerequisite.

## Verification and remaining experiment work

The saved demonstration at `out/rsi_implementation/20261030/saved-demo/` reuses 23 historical loops, 57 generations, six sources and 21 independently scored outputs. The 21 comprise 19 Bernini outputs and two Ditto 041 outputs. It restores Bernini 024 before v3 with source/v1/v2, reads the calibrated input-selection and expression cards, and intercepts a scripted finish. Its two responses are explicitly scripted, with zero paid model and zero renderer calls.

Tests exercise three generation/review cycles, arbitrary parents and backselection, call recovery, unknowns, sequence evidence, no-knowledge isolation, frozen materials, D-only collection, prefix replay, staged proposals, paired validation, fixed-prompt controls, rejection and rollback. The final verification record accompanies this document.

Benchmark construction and dataset allocation are a separate, newly redesigned effort. RSI consumes its supplied source-disjoint assignments and task definitions; previous benchmark sizes and compute allocations are not execution inputs. Before real prototype measurements, bind those assignments to the frozen execution/comparison protocol and a calibrated Claude final judge. GPU experiments and real experience-adoption validation remain to be run.

The original 67-check receipt under `out/rsi_implementation/20261030/` predates the Opus remediation and remains unchanged. Current results, item coverage and remaining live prerequisites are recorded in [rsi-opus-review-remediation.md](rsi-opus-review-remediation.md) and `out/rsi_review_remediation/20261031/`. Scripted checks establish code behavior, not improved model decisions or generated video quality.
