# RSI review remediation

Authorized: 2026-10-31. Scope: repair the complete Opus review against the audited implementation. Preserve historical runs, unrelated changes and the staged status of assisted E1. Software verification and saved-evidence analysis are authorized; this implementation run does not dispatch paid models or GPU experiments.

## Implementation order and acceptance

1. Inner signal (review 1–5, 7): separate render input from comparison baseline; include the baseline in automatic review; count targeted known failures without erasing history on unrelated attempts; retain unknowns; resolve the renderer from execution; show every concise card summary with scope; distinguish sampled temporal scope, local counterexamples and whole-interval claims. Automatically record target-attainment checks without claiming to verify arbitrary prose predictions.
2. Recovery and accounting (12, 14, 15): bounded recorded language-model attempts without mutating shared clients; explicit reconciliation for old uncertain calls; render receipts remain idempotent; preserve logical attempt seeds on infrastructure recovery; record generation wall time and reused/failed costs separately.
3. Outer validity (6, 8–11): gate on Planner selection; retain independent bounds and partial metrics; freeze one experiment cycle including Critic across versions; deterministic evidence aggregates; cap semantic card revisions at three; paired base/candidate replay with identical harness and sanitized prefix, repeated samples and declared behavioral targets; no historical-action attribution shortcut.
4. Operation (13, 15 and review section IV): integrate with the existing resource queue; signed remote renderer transfer; all test arms and reporting; reviewed calibration artifacts; health/drift reports and reviewed rollback recommendations. Quarantine one failed task without stopping unrelated tasks. No automatic adoption or rollback.

## Scope decisions

- Source-relative preservation is a reference relation, not a fabricated empirical review. No blanket edit-fail source verdicts.
- Unknown or failed reviews do not count as confirmed repair failures. A local temporal counterexample can support failure; sampled evidence supports explicitly sampled claims only.
- The full 45-card navigation stays compact. Summaries contain actionable conditions; mechanisms, qualifications and evidence remain in full cards.
- Replay measures behavior conditional on the preserved prefix. It does not establish video-quality gain. Independent final scoring and live paired validation remain necessary.
- Three changed cards is a configurable experiment budget frozen per cycle, not a theory of optimal learning. Proposal envelopes constrain publication, not Planner thought.
- Model response generation can retry under a finite recorded budget; accepted tool actions execute once. Old ambiguous submissions require explicit reconciliation. Render recovery never silently creates another sample.
- Health thresholds diagnose missing evidence; they never coerce known judgments. Historical GPT scores are comparison material, not human gold labels.

## Completion ledger

| Opus item | Implemented behavior and entry points | Verification focus |
|---|---|---|
| 1 | `ledger.resolve_baseline`, signed `comparison_baseline`, optional `intent.baseline`; latest reviewed candidate is distinct from render input. | Source restart detects gains and collateral damage; no fabricated source verdict. |
| 2 | `rsi_support.auto_review` includes baseline automatically. | Source/v1/v2 reach the same review on a source restart. |
| 3 | Targeted known nonachievement and unknown counters in `ledger.build`. | Unrelated attempts preserve counts; pass resets; unknown stays separate. |
| 4 | `execution.renderer.backend` and complete scoped experience navigation. | All 45 cards remain visible, including S2/S3/S4/X1/X4. |
| 5 | All assisted E1 catalog summaries rewritten as self-contained condition/action guidance; S1/S2 body scope matches metadata. | Exact summary presence, renderer applicability, no empty cross-reference summaries. Still staged/assisted. |
| 6 | `record_arm` and `validate` use Planner-selected metrics for loops. | Planner deliberately chooses a different/worse result than the common selector; receipt/gate retains that actual choice. |
| 7 | Lower-bound control selection; partial independent metrics/bounds; interval coverage and local temporal counterexamples. | Unknown alternative does not erase a known selected score; sampled pass retains its narrower scope. |
| 8 | Repeated `paired-replay`, neutral prefix, identical cycle environment/model/manuals, alternating order and declared behavioral targets. | No-shift result fails readiness; cached replay makes no duplicate calls; V rejects unrelated cycle evidence. |
| 9 | `rsi_statistics.aggregate`, compact proposer navigation and paged full evidence. | Historical missing intents remain missing; source-specific and renderer-specific denominators retained; criterion alignment is explicit. |
| 10 | `rsi_cycle` freezes Critic and excludes evolving experience for all rounds; pins non-experience Planner knowledge. | Active experience/manual changes do not alter cycle snapshots; real repository Critic snapshot loads without experience entrances. |
| 11 | `rsi_cards.changed_cards`, maximum three actual edits, target decision IDs/metrics. | Four hidden body edits are rejected; retiring a topic also retires its read entrance without modifying active knowledge. |
| 12 | Durable bounded response retries and explicit `reconcile-call`; separate render-started guard and `recover-tool`. | Shared client unchanged; exhausted/legacy calls blocked until reconciliation; same response reused; uncertain render never silently resampled. |
| 13 | `rsi_batch` on existing `server_runtime` queue; `rsi_remote` signed SSH Ditto handoff/fetch. | Dependency/resume/isolated failure tests and exact input/prompt/seed receipt checks. Actual cluster transport remains untested. |
| 14 | `generation_seconds`, fresh/reused output accounting, logical seed trace and physical response-attempt counts. | Existing render timing contracts plus receipt integration. Missing physical/token costs remain unknown. |
| 15 | D/V/T manifests, five-arm reports, reviewed calibration chain, same-job failure isolation before the next seed. | Formal V gate/T adoption binding, saved E0 controls, calibration tamper rejection, all-arm missing-data report and failed-slot preservation. |
| Operational additions | `health`, independent `drift`, `critic-anchor/critic-drift`, D-only `canary`, reviewed adoption/rollback. | Frozen anchor bindings and unknown transitions; queue health revisions; no automatic publication or rollback. |

The existing model-facing operations remain requirements, generate, critique, read/observe, optional notes and finish. The only new optional Planner field in this remediation is intent.baseline. Retry envelopes, cycle manifests, calibration reviews and batch state are operator/runtime responsibilities.

## Saved evidence check

The deterministic development reconstruction covers 23 historical runs, 57 generation requests, six source videos and 21 independently scored outputs (19 Bernini and two Ditto). This is a reuse of existing evidence, not an additional experiment. All 57 generations predate the structured RSI intent contract; prediction checks and targeted repair-rate estimates are unavailable for them. No free-text purpose was silently converted into a verified prediction. Online and independent criterion sets also need an explicit alignment before itemwise agreement can be computed.

The complete assisted navigation has 45 summaries and 6,442 summary-text characters, excluding IDs/scope/navigation metadata. It remains an explicitly selected draft. Scope labels keep Bernini/Ditto observations distinct.

## Verification and remaining live prerequisites

The receipt and logs live under `out/rsi_review_remediation/20261031/`. Local tests use scripted models and synthetic media. Snapshot checks also read the actual repository knowledge tree; aggregate checks read preserved historical traces. These checks establish implementation behavior and provenance handling.

Live prerequisites are the redesigned source-disjoint dataset assignment, concrete independent Claude profile and reviewed saved-case calibration, frozen budgets/health thresholds/anchor cadence, and real renderer/SSH deployment connectivity. Real behavioral replay, generated-video quality, cycle efficacy and transfer remain unmeasured. No paid model call, GPU generation, rental or active experience publication was made during remediation.

Status: software remediation complete and locally verified.

Verification: 123 checks passed in the compatibility/resource/integration suite, followed by six final affected checks (three additional unique cases): **126 unique checks passed**, with zero failures, errors or skips. The final CLI help and Python syntax checks passed. Git whitespace verification passed with the repository's existing CRLF endings recognized. The actual repository Critic snapshot contained 402 readable IDs and zero decision-experience IDs. Saved-data aggregation and these checks used zero paid model calls and zero GPU generations.

Artifacts: `out/rsi_review_remediation/20261031/implementation-receipt.json`, `verification.json`, `verification.log`, `final-affected.json`, `final-affected.log`, `snapshot-check.json`, `development-final.json`, `aggregates-final.json`, and `planner-experience-navigation.json`. The original 20261030 receipt and historical experiment outputs remain preserved.
