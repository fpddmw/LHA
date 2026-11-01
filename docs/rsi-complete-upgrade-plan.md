# Complete RSI upgrade: authorized implementation

Authorized on 2026-10-31 following the complete Opus review reconciliation. This is the implementation checklist for the existing architecture, not a new parallel framework. Preserve historical evidence and running remote snapshots. Newly authored working material is English.

## A. Independent task criteria and useful local signals

- Reuse source-only evaluation-card authoring. A separate fixed call sees the request and source evidence, not Planner proposals, generated candidates, mutable experience or previous scores. Reviewed task cards are frozen before planning and shared across arms.
- Install the card into the loop. Planner can inspect it and record an objection; it cannot rewrite official criteria or core/detail grades. Creative design remains freely revisable.
- Each item states provenance, importance, pass/partial/fail boundaries, allowed variation and evidence scope. Implicit core relations require a task-identity rationale. Ambiguity stays explicit. A short style request does not inherit a preferred medium, palette or invented plot.
- Group aggregation preserves original goal weights despite item splitting. Unknown, not applicable and execution failure remain distinct. Major damage requires grounded reasons and links; incidental detail cannot be silently promoted.
- Distinguish renderer input, comparison baseline and intended delivery. Separate declared predictions, derived attainment checks and unverified mechanism hypotheses. Optional categorical predictions and card references do not impose a thought sequence.
- A revised authoritative card starts a separately versioned comparison; historical judgments are not rewritten or pooled across incompatible criteria.

## B. Cases, evidence claims and decision skills

- L0: immutable state/action/outcome records, exact inputs/prompts/settings, online and optional independent judgments, costs and missingness. Later annotations are versioned additions.
- L1: falsifiable contextual action/outcome claims, competing mechanisms, executable restricted queries, support/counterexamples and explicit scope. Code computes counts; semantic labels retain provenance. Concept definitions remain useful without invented effectiveness claims.
- L2: concise judgment guidance linked to evidence claims and Wiki cases. Actual reads and optional declared card use are observational attribution, not causal credit.
- Refresh evidence into revision/writing/retirement suggestions. Never mutate active snapshots automatically. Proposal changes are capped at three actual cards, including surrounding guidance.
- Preserve Planner access to Wiki and cases. Proposer may return no change or a concrete evidence request. Initial content concerns task identity, connected visual changes/design conflicts and wording versus substantive realization changes.

## C. Replay and delivery-based validation

- Distinguish development diagnostic, source/trajectory-disjoint held-out replay, V live validation and final T. Record exposure; a feedback-exposed point is development material.
- Include change and maintain-correct targets. Behavioral movement is diagnostic, not delivery benefit. Explicit repetition/minimum-effect settings are protocol choices, not universal guarantees.
- Branch value binds exact input, prompt, settings and observed outcomes; untried alternatives remain unknown. Prefer native RSI prefixes; legacy reconstructed prefixes are labeled.
- Primary outcomes concern the actual delivered candidate at fixed budget. Candidate-set success, selection regret, non-improving attempts and actual costs are separate. Include style/design quality in a reviewed utility contract when used, with core failures reported separately.
- Report both actual Planner selection and the common frozen selector for loop versus best-of-N comparisons. Freeze seeds, task cards, judge, Critic, model profiles, code and reference sets per cycle.
- Preserve original, assisted-Wiki and automatically proposed experience baselines. Only experience changes within a cycle. Task-grading guidance changes require another cycle.
- Independent Claude calibration uses reviewed saved examples and disagreements; historical GPT outputs are not human gold. Current seven-task delivery has no new independent scoring.

## D. Operational cycle and protections

- Reuse collect -> aggregate -> propose -> replay -> live V -> review -> adopt/reject -> next development batch; expose each transition and its evidence. No automatic publication or rollback.
- Retain queue/resource limits, isolated failures, durable bounded LLM retries, idempotent render recovery, logical attempt seeds, signed remote delivery and complete cost/unknown reporting.
- Integrate health, frozen anchor drift checks and previous-version canaries. Budget exhaustion is not successful delivery.
- Finish already-running authorized work under its existing snapshot. New paid replay/calibration/render comparisons follow reviewed experiment configurations; software completion is distinct from real efficacy.

## Opus coverage

First review: 1-2 baseline/contenders (A); 3 counters (A); 4-5 scoped complete summaries (B); 6-7 actual selection/unknown evidence (A,C); 8 paired replay (C); 9 deterministic aggregates (B); 10 frozen Critic (C,D); 11 revision cap (B); 12 retries/reconciliation (D); 13 batch/remote dispatch (D); 14 time/cost (D); 15 reports/calibration/seeds (C,D). Existing implementations are reused and regression checked.

Second review: 1 independent criteria (A); 2 decision value (B,C); 3 noise/thresholds (C); 4 leakage (C); 5 baseline identity (C); 6 delivery objective (C); 7 selector confounding (C); 8 predictions (A); 9 native decision points (B,C). Wiki audience/outcomes/concepts/mutable-guidance issues and the L0/L1/L2 lifecycle are addressed in B/C.

Additional audited defects: candidate-set success mislabeled as delivery success (C); semantic-only utility (C); post-hoc partial boundaries (A); item-count weighting (A); unsupported major-damage flag (A); pooled prediction bases (A,B); generation cap confused with satisfactory delivery (D).

## Completion evidence

For every item report implementation, relevant checks and actual execution scope. Provide three English task-card examples, exact Planner/Critic context, one saved-evidence case/claim/skill trace, staged proposal/replay/validation examples, and a final coverage receipt. Scripted-model tests do not establish behavioral or video-quality gains. Real adoption requires reviewed live validation of the exact proposal.

## Implemented mapping

The detailed account is `docs/rsi-complete-upgrade-implementation.md`. Actual verification
and artifact hashes are recorded under `out/rsi_complete_upgrade/20261031/`.

| Review concern | Implementation in the existing architecture |
|---|---|
| First 1–2: source restarts lose comparisons | `ledger.resolve_baseline`, signed comparison baseline and automatic contender inclusion; kept from the prior repair. |
| First 3: nonachievement counters | Deterministic targeted-known failures; unrelated attempts preserve counts; unknowns separate. |
| First 4–5: renderer and summaries | Actual backend identification, complete scoped navigation, existing 45-card assisted draft retained. New judgment drafts are staged separately. |
| First 6–7: wrong selector and incomplete evidence | Actual Planner selection; bounded unknowns; temporal coverage and local counterexamples; new fixed card boundaries. |
| First 8: replay confounds | Same neutral prefix and cycle environment; disjoint held-out partition; native criteria for formal probes. |
| First 9: absent statistics | Existing aggregates plus case/claim statistics, declared versus derived predictions and optional skill-use associations. |
| First 10: Critic drift | Cycle-wide frozen Critic without evolving experience; standalone new RSI snapshots also exclude experience. |
| First 11: unlimited revision | Three actual card edits, including claim metadata and surrounding guidance. |
| First 12: fragile calls | Existing bounded recorded response retries, reconciliation and idempotent render recovery reused. |
| First 13: scheduling and remote dispatch | Existing resource queue, dependency scheduling, quarantine and signed remote worker interfaces; `cycle-run` connects them. |
| First 14–15: costs, reports, calibration and seeds | Actual generation timing, paired logical seed slots, five-arm reports, reviewed calibration and raw provenance retained. |
| Second 1: Planner defines its own reward | Independent source-only card authoring, pre-run review/freeze, immutable installation, objection-only Planner interface. |
| Second 2: movement versus decision value | Behavioral probes labeled diagnostic; concrete branch library and reviewed outcome-bound value labels; live delivered-quality validation. |
| Second 3: noise-sized gates | Frozen repetition, effect and coverage budgets; source-level quality protections; exploratory scope and unknown bounds. |
| Second 4: leaked decision points | Source/trajectory-disjoint replay partition, exposure checks against proposer evidence, no V/T replay. |
| Second 5: contaminated E0 | Historical E0 preserved separately; assisted/learned catalogs cannot be labeled original. Cycle snapshots pin the chosen baseline. |
| Second 6: rewarding fewer actions | Live primary is delivered success or visually informed selected utility; counts and candidate-set success are diagnostics. |
| Second 7: selector confounding | Reports expose both Planner-selected and common-selector results, first/final changes and actual generation costs. |
| Second 8: target bookkeeping mislabeled prediction | Optional categorical predictions; declared checks, derived attainment and text hypotheses separated. No claimed Brier calibration from categorical labels. |
| Second 9: old mixed prefixes | Formal probes require native independently frozen criteria. Historical reconstructed probes stay development diagnostics. |
| Wiki / evidence / skill linkage | Immutable cases, versioned reviewed semantic annotations, restricted claim queries, counterexamples, revision todos and staged skills with linked claims. |
| Operational continuity | Cycle orchestration, monitoring receipts, anchors, canaries, explicit adoption/rejection, rollback proposals and next-version hash verification. |

Remaining real work is explicitly outside a software-completion claim: source-grounded
review of the draft task cards; selection/calibration of the independent Claude profile;
reviewed live protocol and replay partition; real paired validation and approved adoption.
The ongoing Bernini batch continues under its original snapshot and its original
no-independent-scoring authorization. No automatic publication is part of this upgrade.
