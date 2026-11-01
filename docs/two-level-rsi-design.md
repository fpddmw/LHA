# Two-level RSI for the agent loop: design and experiment plan

Date: 2026-10-30; revised 2026-10-31 after the Opus code review. Status: **authorized software remediation; live measurements remain a later stage.** The item-by-item implementation record is [rsi-opus-review-remediation.md](rsi-opus-review-remediation.md). The staged experience draft is in [`knowledge/staged/e1-20261030/`](../knowledge/staged/e1-20261030/README.md).


## Approved calibration and implementation contract

The user authorized implementation of this complete architecture, including the experience rewrite, inner RSI, and outer collection, proposal, replay and validation/adoption support. Preserve all prior runs and unrelated working changes. Code and local scripted verification come first; do not launch the full GPU experiment matrix as part of software implementation.

- New opt-in RSI runs use context version 3. Existing runs and planning-only defaults retain their prior interfaces. Requirements and a compact generation intent are required only in RSI mode; no fixed thought sequence or alternative-ranking form is required.
- Requirements have stable IDs, source-grounded text, kind and priority. Revisions preserve prior versions and invalidate cross-version score comparisons until re-assessment. Planner additions remain design choices. Critic omissions/damage suggestions are visible and cannot be silently hidden by a complete checklist.
- Intent contains targets, a short change and an expected result. Optional per-target expectations use improve/pass/same_or_better for deterministic checking. Free-text predictions remain unscored unless supported by a structured judgment. Failure types are optional, may overlap, and are hypotheses. Prediction attainment and collateral regression are separate fields; unknown evidence stays unresolved.
- Each successful generation schedules one logical automatic review. Response-only model calls have bounded logged retries; a completed response is reused. Rendering keeps a separate execution guard and explicit recovery. The comparison baseline defaults to the latest candidate reviewed under the current requirements, independently of the rendering input. Source, output, actual input, baseline and optional contenders fit four videos; no contender is silently dropped.
- Freeze Critic instructions, non-experience knowledge and model configuration for the entire experiment cycle, across all experience versions and held-out tasks. Later experience changes only affect Planner. The Critic observes outcomes before opening process prompts and does not receive intent in its outcome context. It describes findings and leaves the next route to Planner.
- The ledger computes item scores and bounds from judgments, with core/detail and edit/preserve kept distinct. Bounds caused by unknown items are logical ranges, not confidence intervals. Its history is a factual memory, not proof that a model changed its beliefs.
- Experience navigation includes all 45 concise card summaries with explicit renderer applicability and links to complete cards. Renderer identity comes from execution.renderer.backend. No-knowledge removes both read access and summaries. Metadata is frozen with text. The assisted E1 remains an explicitly selected snapshot until validated publication.
- Strong experience defaults remain actionable. Two-failure stopping is a proposed budget policy, not a proven capability limit. Negative-wording and route preferences are hypotheses with exceptions. Unsupported universal claims and mismatched trigger/evidence conditions are corrected in the staged cards.
- Outer proposal uses development data and deterministic aggregates, retains counterexamples/rejections, and changes at most three actual cards per round. Each change names saved decision points and a behavioral metric. Paired replay gives base and candidate the same current harness and knowledge-neutral historical prefix, samples each repeatedly, and stops before rendering. Missing historical intents remain missing.
- Validation manifests freeze source splits, cycle, seeds, budget, independent judge and a primary decision metric. Loop adoption gates use Planner's actual selected candidate. The frozen lower-bound selector serves direct/best-of-three controls and a separate diagnostic. Same logical attempts use the same seeds across arms; infrastructure recovery resumes the same job. Report generation and model costs separately. Best-so-far curves describe the candidate set; final choice and compute-matched controls test adaptation value.
- Report non-improving attempts as retrospective outcomes, not necessarily avoidable errors. Multi-objective comparisons require an explicit ordering and retain unknowns. The previous two-of-eleven superiority summary is a priority-based interpretation, not strict dominance. Six multi-attempt runs represent three source tasks.
- Adoption binds exact proposal/base/candidate hashes, complete paired validation evidence and the predeclared gate. The initial gate is an exploratory selection rule, not a statistical non-inferiority claim. Human review remains the final publication action. Rejection and rollback are executable and journaled.

Implementation checklist:

- [x] Calibrated design and assisted E1 cards/metadata.
- [x] Inner requirements, intent, ledger, frozen automatic Critic and context.
- [x] Outer collect, multi-card propose, prefix-only replay and validation manifests.
- [x] Paired validation receipt, reviewed adoption/rejection and rollback.
- [x] CLI wiring, compatibility/recovery tests and saved-context demonstration.
- [x] Implementation account with actual checks and remaining experimental work.

This contract supersedes conflicting details in the original proposal below. C1 and C2 are research hypotheses to test, not achieved claims.

## 0. Claims and constraints

- **C1, task-level RSI:** within one task, the loop improves its own working hypotheses from evaluated attempts. Its final result is better than single-pass planning and better than compute-matched sampling.
- **C2, global RSI:** decision experience revised from task evidence, then validated and adopted, improves decisions and results on held-out tasks across experience versions. It transfers across renderers.
- **Constraint:** keep the existing workflow: one continuous Planner, `generate` / `critique` / `finish`, durable signed jobs, frozen snapshots. All changes are additive and versioned (`context_version: 3`). Old runs keep their paths.

## 1. Why the current loop is not yet RSI

The 2026-10-30 runs (23 loops, 57 generations) show a generate → review → reword cycle. It lacks four elements:

| RSI element | Current state |
|---|---|
| An explicit object that is improved | Prompts, inputs and candidate choices change; dedicated notes were empty in 23 of 23 runs. No persistent requirement-linked prediction verification exists. |
| A stable signal | Each review is free prose. No requirement-level score accumulates across attempts. |
| Modification with a prediction | 30 of 57 generations have a purpose. These explanations are not consistently matched to later evidence or retained as verified expectations. |
| Verification and adoption | Nobody checks whether an attempt achieved what it intended. The global proposer exists but is never validated, and experience v1 never changed. |

We operationalize RSI at both levels with the same four parts:

| | Task level (inner loop) | Global level (outer loop) |
|---|---|---|
| Improved object | Task belief state: requirement ledger, attempt records, lessons, candidate set | Experience library `E_k`: decision rule cards and renderer profiles |
| Signal | Online Critic requirement verdicts (frozen during an experiment) | Aggregated attempt records and validation outcomes |
| Modification | Next attempt = intervention with declared targets and expected effect | Card diff (add/revise/retire) with a predicted behavioral change |
| Verification | The next review scores the prediction: hit / partial / miss / regression | Decision replay plus held-out validation, then adopt or reject |
| Memory | Attempt ledger in context | Versioned library plus a log of rejected proposals |

The evaluator is frozen within each experiment, so improvements cannot come from a drifting reward. The independent judge is separate and never seen by the Planner.

## 2. Task-level changes

### 2.1 Requirement checklist (Planner, once)

New operation, required before the first `generate` when `rsi.requirements` is enabled:

```json
{"action":"requirements","arguments":{"items":[
  {"id":"R1","text":"Earth visible through large windows","kind":"edit","priority":"core"},
  {"id":"R2","text":"Far player's face and glasses unchanged","kind":"preserve","priority":"core"}]}}
```

These are the Planner's model of the goal, written from the request and the source. The Planner's own optional design choices are not requirements; they belong in intents. Items can be revised later with a recorded version. The independent evaluation card is never shown, which avoids leakage.

### 2.2 Generation intent

`generate` gains a required `intent`. The intent is stored in the job but never sent to the renderer.

```json
{"action":"generate","arguments":{"input_video":"v2","prompt":"...",
  "intent":{"targets":["R1"],"failure_type":{"R1":"explicit-unrealized"},
            "change":"frame the Earth panorama with metal window structure","expect":"R1 partial -> pass; R2 unchanged"}}}
```

This turns each attempt into a testable hypothesis and makes the attempt's predicted effect explicit.

### 2.3 Automatic, requirement-anchored review

- RSI mode enqueues a review after every completed generation. It includes the actual parent and resolved comparison baseline, with optional contenders within four total videos including source/output. This saves a Planner call and preserves comparisons on source restarts.
- The Critic receives the requirement list. Its `assess` adds `requirement_verdicts` with entries `{id, verdict, importance, evidence, delta_vs:{<video>: improved|same|worse|unknown}}`, and `added_requirements` for unlisted user requirements or major damage. This guards against an easy checklist.
- After `process_context`, `finish` adds `failure_types: {Rid: omitted|explicit-unrealized|inherited|introduced|unknown}`, labeled as hypotheses.
- Guidance change: the Critic describes but does not route. Phrases such as "justify another generation" are removed, so that decisions, and therefore the effect of experience, belong to the Planner. Importance must follow the request's specificity: incidental structure on a short style request is detail-level.
- Cost: `max_turns` 24 → 12, and source dense observations are cached within a task. Compare `high` and `xhigh` reasoning on saved cases before choosing one. The configuration stays frozen for a whole experiment.

### 2.4 Ledger (new deterministic module `ledger.py`)

From requirements and verdicts, the ledger builds:

- **Matrix** of requirement × candidate, with pass / partial / fail / unknown.
- **Online attainment** per candidate: edit and preserve scores computed with the evaluation-protocol rule (pass 1, partial 0.5, fail 0, unknown as lower/upper bounds), plus a major-damage flag. This is the "score" the Planner sees. It is computed from verdicts, never a free VLM scalar.
- **Attempt records:** for each generation, input, targets, expected change, the observed change on the targets, collateral regressions on other items, and a prediction outcome (`hit`, `partial`, `miss`, `regressed`).
- **Targeted nonachievement counts:** known partial/fail results when an attempt explicitly targeted the requirement. Unrelated attempts do not erase the count; pass resets it; unknowns are counted separately. This measures unsuccessful targets, not whether the prompt expressed them correctly.

Context v3 shows the ledger table and attempt records compactly. Full reviews stay available through `history`. The ledger is a factual summary; it neither ranks nor selects.

### 2.5 Experience reaches the decision

The harness adds an **experience digest** to the default context: one concise condition/action summary per card (45 in assisted E1), frozen with scope/status and the run snapshot. Other-renderer cards remain visible as transfer hypotheses. Full cards remain readable on demand.

Without this, the effect of `E_k` depends on whether the model happens to read a page. Reads are concentrated early, with some reads after the second generation. Only three explicit observe calls occurred, but source and latest-result overviews were automatically attached. The `no_knowledge` arm removes the digest as well.

### 2.6 Finish and task memory

- `finish` adds `unmet: [ids]` and `stop_reason` (`satisfied` / `no_promising_attempt` / `budget`).
- The harness writes attempt records into `task_memory` automatically, so the task memory is never empty. A model-written `lesson` (an alias of `note`) stays optional.

## 3. Global RSI

### 3.1 Library format

Experience pages consist of rule cards (ID, When, Do, Why, Limits, Status, scope); see the staged draft. Renderer profiles are separate cards scoped to one renderer. Statuses are `single`, `observed`, `mixed`, `validated` and `retired`. Stable manuals, tool contracts, the art corpus and evaluation protocols are outside RSI.

### 3.2 One round `k` (`src/planner_harness/rsi_round.py`, through `scripts/run_rsi.py`)

1. **Run:** the development pool `D` runs with `E_k` frozen.
2. **`collect`** (deterministic) writes:
   - one sealed collection containing complete per-run/per-attempt records: task, renderer, track, actual input, prompt, intent when recorded, reviews, ledger, candidate ancestry and independently scored outputs;
   - `aggregates` in that collection: targeted repair improvement, route outcomes, first-attempt success, prediction hit/unknown counts and Critic/independent major-damage agreement. Itemwise agreement requires reviewed version-bound criterion mappings. Unknowns retain denominators. Selection regret and generation costs are computed from bound experiment receipts.
3. **`propose`:** a model reads compact aggregates/case summaries and can request full records. It returns at most three actual card changes with evidence, counterexamples, saved decision IDs and a predicted metric/direction, staged under `knowledge/staged/E<k+1>/`. It never sees `V` or `T`.
4. **`paired-replay`** (no rendering): at each saved prefix, run base and candidate repeatedly with identical current instructions and available evidence; remove historical knowledge-read text and derived notes symmetrically. Prior actual prompts/results remain fixed history. Gate on the declared behavioral distribution shift. Changed visual realization requires reviewed labels; a changed string is insufficient. Legacy one-sided `replay` remains a diagnostic only.
5. **`validate`:** paired live comparison of `E_k` versus `E_{k+1}` on `V` (same seeds, budget and Critic). Decision and quality metrics are measured with the independent judge.
6. **`adopt`:** the existing reviewed publication, extended to multi-file diffs and new topics, binds the validation receipt and version. Otherwise the proposal is rejected and logged. Rollback reuses the existing journal.

Adoption rule (fixed before running): adopt if `V` shows non-inferior quality (paired difference in success rate ≥ −1 task, and core preservation not lower) together with an improvement in one primary decision metric selected before the run (non-improving generations, selection regret, or success@budget). The rule is stated in advance to avoid post-hoc selection.

## 4. Experiments

### 4.1 Dataset interface

Benchmark construction is being redesigned separately, per the user's 2026-10-31 scope update. This RSI document defines how supplied datasets are used; the new benchmark work will supply source membership, task definitions, split assignments and experiment size. Previous benchmark counts and allocations are withdrawn.

| Split | Role in RSI |
|---|---|
| `D` development | Evidence collection and experience proposals |
| `V` validation | Paired comparison for the adoption decision |
| `T` test | Final evaluation, kept separate from experience development |

Assignments are frozen from the supplied metadata with source-level separation and development exposure recorded. Reports retain the supplied task tracks and effective sample counts.

### 4.2 Arms on `T`

| Arm | Generations | Purpose |
|---|---|---|
| Direct: user request to renderer | 1 | Renderer baseline |
| Single-pass Planner (`E0`) | 1 | Planning without iteration or global experience learning |
| Best-of-3: same single-pass prompt, 3 seeds, common frozen selector | 3 | **Compute-matched control for C1**. Seed 1 equals the single-pass arm. |
| Loop `E0` (active v1 experience) | ≤3 | Task-level RSI before global RSI |
| Loop `E_final` (after global RSI rounds) | ≤3 | Both levels |
| Optional: loop without the online Critic (Planner `observe` only) on `V` | ≤3 | Tests what the Critic contributes |
| Optional: loop with assisted E1 (the staged draft) on `V` | ≤3 | Human-assisted reference; reported separately |

Seed schedule: attempt *i* uses seed 41+*i* in every arm without Planner overrides in paired experiments. Attempt seeds are therefore paired across arms.

### 4.3 Metrics

- **Quality** (independent Claude-family judge under a new protocol version): calibrate on a declared subset of the 21 saved records (19 Bernini, two Ditto) and known disagreements before use. Historical model judgments are comparators, not human gold. Preserve exact profile, evidence, comparison and explicit calibration review. Report edit, core, detail, time, style, success and major damage for first/selected candidates and candidate sets.
- **Decisions:**
  - selection regret: best-in-set minus selected, as scored by the judge;
  - wasted generations: attempts after the eventual best, or after a passing candidate;
  - generations to success, and success@budget;
  - prediction hit rate of intents;
  - repair rate by failure type;
  - repeated rewordings of explicit-unrealized requirements.
- **Cost:** GPU minutes, Planner and Critic calls, and judge calls.
- **RSI curves:** best-so-far quality against attempt index (task level), and metrics against experience version on `D` and `V` (global level).
- **Statistics:** paired by task, source-clustered bootstrap confidence intervals, short and long tracks reported separately, all missing data reported.

## 5. Execution topology

Experiment size and compute budgets will be set with the redesigned benchmark. RSI has no active renderer allocation or duration estimate inherited from the previous dataset.

The controller, Planner and Critic can run with API access while signed render jobs execute on a remote GPU worker (`jobs/<id>/request.json` → `run_planner_worker.py` → `response.json` plus video). Results return with hashes under the existing worker contract. Independent tasks can use the resource queue.

A remote execution package contains the frozen code commit, supplied task list with source hashes, execution profile, verified model manifest, seed schedule, worker command and output verification procedure.

## 6. Implementation order

1. Task-level harness (no GPU): `requirements`, `intent`, auto and multi-contender review, Critic verdict schema, `ledger.py`, experience digest, `finish` fields, context v3. Scripted tests, including old-run compatibility, and an offline context preview on saved runs.
2. Global tooling (no GPU): `collect`, `propose`, `replay`, `validate` spec writer, multi-file `adopt`.
3. Replay of the staged E1 and of an automatically proposed E1 on the saved decision points of the 23 loops (Planner calls only). This gives the first offline global-RSI evidence and checks that the proposer can match the assisted draft.
4. Independent Claude judge: adapter and calibration on saved records.
5. Bernini rounds, then `V` and `T`. Ditto in parallel through the colleague, once the package is frozen.

## 7. Risks

- **Experience could be dismissed as prompt engineering.** Position it as in-context policy improvement with versioning, a fixed adoption rule, held-out validation and rollback. Report rejected proposals.
- **The Planner could write an easy checklist.** The Critic's `added_requirements` and the independent judge guard against this.
- **The Critic as frozen reward could be over-fitted.** Report Critic–judge agreement for every version.
- **Small numbers of sources.** Use source-level clustering and pre-registered rules, and do not pool across renderers.
- **The current development tasks are exposed** and never count as test.

## Implementation verification (2026-10-31)

The original 67-check implementation receipt remains historical evidence; Opus's review identified missing behaviors beyond those checks. Current remediation tests and saved-data results are recorded in [rsi-opus-review-remediation.md](rsi-opus-review-remediation.md). No paid model call, new GPU generation, or active experience publication belongs to this remediation. The concrete independent judge, calibration review and held-out dataset configuration remain prerequisites for prototype measurements.
