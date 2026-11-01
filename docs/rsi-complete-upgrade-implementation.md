# Complete RSI upgrade: implementation and execution scope

This implements `rsi-complete-upgrade-plan.md` on the existing Planner, Critic, queue,
evaluation and knowledge interfaces. The running seven-task Bernini batch retains its
remote frozen snapshot. This work changes the local implementation, not that batch.

## The central correction: who defines success

New live RSI runs require a reviewed independent task card before Planner starts.
`criteria-draft` uses the existing source-card authoring path in a separate call. Its
model input is the user request, source timestamps and source images. Prior criteria,
Planner proposals, generated candidates, mutable experience and scores are excluded.
`criteria-freeze` records the source-grounded review and hashes the complete card.

The card states the original goals, authorized changes, source relations, importance
rationales, observation scope, pass/partial/fail boundaries and allowed variation.
Implicit core relations require a task-identity explanation. Incidental detail stays
detail. An observation being visible in the source does not by itself make its exact
geometry a core requirement. Uncertain importance or correspondence remains explicit.
Group weights belong to original goals; splitting one goal into several observations
does not increase its weight.

Planner receives this card in task memory. It can formulate any compatible design,
look at evidence, read knowledge and choose an input. `criteria_objection` records a
reason and source/request evidence without changing the scoring target. The old
`requirements` operation remains for legacy scripted replay and is rejected for an
independently frozen run. Correcting an authoritative card creates a new version and
comparison scope. Historical judgments are preserved.

The Critic receives the same frozen criteria and actual videos. It applies the stated
boundaries, records observations and uncertainty, and can report a missing task-defining
relation. It does not receive Planner's intent during outcome assessment and does not
select the next input, prompt or stopping action. A major-damage flag requires linked
criteria or an identified unlisted task relation, observed source/candidate evidence
and an explanation. Detail alone and passing linked criteria do not justify it.

Three English review drafts are at
`out/rsi_complete_upgrade/20261031/task-cards/`. They are proposals based on saved source
reviews, not newly reviewed or frozen experiment standards:

| Task | Core interpretation | Explicit remaining boundary |
|---|---|---|
| 041 short | Coherent storybook treatment and recognizable writing interaction | No mandatory watercolor/pastel recipe. Pen, notebook and loose-paper structure is reported separately. |
| 027 short | Etching and recognizable town-view relationships | Fine contour simplification is allowed; the historical landmark-severity dispute still needs source-grounded review. |
| fewshot 004 long | Explicit space-station properties and requested preservation | Blue emission belongs to the tabletop perimeter. Small-ball timing stays unknown without adequate sequence evidence. |

## Task-local RSI

The local loop is request/source + frozen criteria -> Planner's chosen intervention ->
render -> automatic evidence review -> updated task memory -> Planner's next decision.

The runtime keeps three different concepts: renderer input, comparison baseline and
intended delivery candidate. A source restart is compared with the resolved reviewed
baseline, which also enters automatic review. The first source is an unreviewed
reference; the runtime does not fabricate an edit-fail/preserve-pass assessment.

Each generation retains the existing short intent: targets, change and expectation.
No new required reasoning form was added. Optional `expected_verdicts` declares
pass/partial/fail predictions; optional `cards` records referenced skill IDs. Declared
predictions, derived attainment checks and open-text mechanism hypotheses are reported
separately. Categorical prediction accuracy is not probability calibration or proof of
a correct mechanism. Known targeted failures accumulate across unrelated attempts;
unknown evidence is counted separately.

`delivery_candidate {id}` optionally records the current preferred result. `finish`
still lets Planner select an earlier candidate. The resulting delivery status separates
satisfied criteria, unresolved criteria, budget exhaustion and execution failure.
Generation limits are resource limits; reaching a limit is not task success.

An exact context package from the production harness is at
`out/rsi_complete_upgrade/20261031/software-context/`: Planner inputs in `run/calls`,
signed jobs and Critic inputs in `run/jobs`, observations and final task memory. The
video and model responses in this package are synthetic fixtures. `scope.json` records
the original temporary path and relocation; no real model behavior is claimed.

## L0 cases, L1 evidence, L2 skills

`rsi_evidence.py` connects these layers without replacing the existing Wiki:

* L0 binds state/action/outcome, exact prompt, input, settings, seed, observations,
  optional independent judgment and costs. The decision prefix identifies information
  available before the action. Run-wide read indexes are labeled retrospective.
* L1 contains a contextual claim, mechanism, comparison, limitations and a restricted
  query. Code computes matching cases, support, counterexamples, missing observations
  and source counts. A descriptive attempt interval is explicitly not a clustered
  confidence interval or an adoption rule.
* L2 provides concise judgment guidance and references claim IDs and Wiki cases.
  New counterevidence creates a revision suggestion. Supported evidence without a
  corresponding skill creates a writing suggestion. Neither changes the active library.

`case-annotate` adds a separately reviewed semantic interpretation with an original-case
hash, rationale and cited artifact hashes. These sidecars can distinguish, for example,
substantive realization change from rewording using `label.realization_change` queries.
Conflicting interpretations require an explicitly selected revision. Raw facts stay
unchanged; semantic interpretations retain their authorship and uncertainty.
Failure-type filters refer to recorded Planner hypotheses; separately reviewed semantic
labels are versioned interpretations. Neither is silently converted into observed causality.

The three new drafts under `knowledge/staged/rsi-complete-20261031/` concern task
identity, connected visual relations and substantive intervention changes. They are
human-assisted hypotheses. Their guidance discusses visual carriers, contact, emission,
occlusion, design conflicts and the information available in an input. It supplies no
mandatory creative substitution, fixed prompt template or spatial-preservation promise.

The saved-data demonstration packages 23 historical runs and 57 attempts. The three
new claims are unmeasured because the historical data lack their required semantic
labels and structured local predictions. No successful repair or causal credit was
inferred from a card being read. Full data are in `saved-evidence-refresh.json` and
`saved-branches.json` under `out/rsi_complete_upgrade/20261031/`.

## Cross-task RSI and experiment validity

`cycle-run` reuses collect/aggregate, proposal, paired replay, validation preparation,
the existing batch scheduler and independent scoring. It stops at a concrete review
point before publication. A proposer can return no change or an evidence request.
Each proposal has at most three actual card changes; hidden surrounding text and claim
metadata count toward the cap. Definitions remain useful even without an empirical
efficacy claim. Operational manuals and task grading are outside automatic revision.

Development replay is diagnostic. Formal validation requires a frozen, source/trajectory
disjoint held-out replay partition from reserved development sources. The code checks
actual source hashes and proposer exposure. Feedback-exposed cases cannot be relabeled
held-out. Native independently frozen prefixes are required for formal replay; old
reconstructed prefixes remain diagnostic material.

Repetition, minimum effect and decision coverage are declared in `protocol.replay_gate`.
Formal replay rejects lower budgets. A correct decision may be a maintain target;
there is no universal desired direction for stopping or source selection. Reviewed
realization/value labels bind exact decisions and cited outcome files. Observed branch
records bind actual input, prompt, seed and renderer settings. Untried prompts or input
routes have unknown value. A successful behavioral probe still needs live V outcomes.

Live V adoption uses actual delivered success or reviewed delivery utility. Utility
must include a declared visual-quality component when used. It protects source-level
core preservation, delivered success and major damage with predeclared tolerances.
Candidate-set success, selection regret, non-improving attempts and actual costs are
diagnostic fields. Reports include Planner selection and common-selector results for
the loop/best-of-N comparison, plus short/long and source-macro summaries. Unknowns
retain logical bounds; the small-sample adoption gate is exploratory.

Only Planner experience varies inside an experiment cycle. Code, task cards, reference
sets, seeds, budget, model profiles, independent judge and non-experience Critic material
are frozen. Labeling an assisted/learned active library as original is rejected. The
historical E0 snapshot is preserved separately from the current assisted Wiki version.
An automatically proposed version retains its provenance and becomes usable only after
the exact validated publication is approved. Test sources are used after E_final is fixed.

## Operation, monitoring and recovery

`cycle-monitor` joins existing health, frozen Critic anchors, independent-judge drift
and previous-version development canaries. Monitoring tolerances belong to the frozen
cycle protocol; result paths belong to the round configuration. Missing observations
remain pending. Bootstrap cycles have no automatically adopted predecessor; subsequent
development uses the previous-version canary. Reviewed adoption requires a passing
monitoring receipt bound to that validation. Regression creates a review/rollback
proposal, never automatic publication.
`cycle-run` can repeat explicitly configured Critic and independent-judge anchor jobs
through their existing durable interfaces. An empty `anchor_jobs` list dispatches no
extra measurement. `cycle-monitor` itself only joins already available observations.

The existing queue provides GPU and LLM slots, dependencies, resumable work and isolated
failures. Bounded LLM retries preserve individual attempts and leave shared clients
unchanged. Render recovery preserves the signed job and logical seed slot. Remote
dispatch/fetch, timing and physical cost accounting remain on the existing interfaces.
`cycle-progress` reports evidence through adoption and actual next-version use, checking
the next development run's experience hashes against the published library.

The independent judge remains a separately calibrated Claude configuration for future
formal runs. `calibration-prepare/run/review` binds saved cases and reviewed disagreements.
Historical GPT judgments are comparators, not human gold. This upgrade dispatched no
new paid model call, calibration job, GPU experiment or knowledge publication.

## Entry points and review artifacts

Operator commands are on `scripts/run_rsi.py`:

| Purpose | Commands |
|---|---|
| Independent criteria | `criteria-draft`, `criteria-freeze`; Planner CLI `--task-card` |
| Evidence and semantic interpretation | `collect`, `case-annotate`, `evidence-refresh`, `branch-library` |
| Disjoint decision probes | `replay-partition`, `paired-replay`, `review-replay`, `round` |
| Frozen real cycle | `freeze-cycle`, `cycle-run`, `cycle-monitor`, `cycle-progress` |
| Scoring and controls | `calibration-*`, `run-control`, `judge-run`, `report`, `validate` |
| Reviewed change/recovery | `adopt --monitoring`, `reject`, `rollback`, `reconcile-call`, `recover-tool` |

Planner does not fill these operator manifests. Its ordinary surface remains reading,
observation, design/notes, generation and delivery, with optional objections and predictions.

Verification results are saved in `out/rsi_complete_upgrade/20261031/verification.json`
and `verification.log`. The companion review contains exact English criterion examples.
`software-cycle/` retains the staged proposal, held-out scripted replay and V/T manifests
from the contract integration test. Its synthetic adoption binding is clearly labeled
test-only and did not publish anything to the active library.
The final implementation receipt distinguishes software coverage, saved-evidence reuse,
active experimental work and pending real validation. A complete software chain is not
an automatically learned, validated E_final or evidence of improved video quality.

## Verification outcome, 2026-10-31

The broad regression executed 215 unique tests: 214 passed and one exposed a legacy
reporting compatibility issue (`cycle: null`). After fixing that issue and completing
the configured-anchor connection, all 34 affected/new contract and integration tests
passed on the final source revision. Their IDs and results are in
`postfix-verification.json`; the first broad result remains unchanged for audit.
Syntax checks passed, newly authored working files were checked for English, and the
diff check passed with the repository's existing CRLF endings treated as line endings.
No paid model call, GPU render, independent calibration or active experience publication
was dispatched by this implementation verification.
