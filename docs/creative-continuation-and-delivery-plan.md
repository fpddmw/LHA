# Continuation questions and informed delivery

Date: 2026-11-01. Status: user approved for implementation, offline verification and Git synchronization. The separate explicit pause of live experiments, reruns and polling remains in force. Prepare migration without starting GPU jobs, real model calls or heartbeat monitoring.

This plan supersedes the fresh-review-only proposal in `creative-delivery-review-amendment.md`. The existing GPT-6.1-sol/xhigh execution thread implements and checks the changes; the original conversation reviews the resulting implementation. No additional executor or scheduling system is needed.

## Approved intent

Planner remains the creative decision-maker. Continuing generation progressively requires a serious, concrete decision explanation. The runtime asks, records and checks that a response exists; it does not grade the reasoning or ask a second model to approve it. These explanations support later human-requested experience maintenance.

Planner receives factual spent-resource information and non-quantitative budget pressure. It must not receive a total allowance, remaining amount, consumed proportion, budget unit, pressure thresholds, or a statement revealing that the actual hard limit is disabled. The latest user correction explicitly removes half-consumed, near-exhaustion, critical-level and last-attempt signals that would invite estimating the allowance.

Give initial exploration room: the first two successfully generated candidates require no continuation justification. Starting with a request after those candidates, a nonempty free-text justification is required. This count is an implementation setting for operators, not a budget disclosure in Planner-facing manuals. Normal generation does not require an extra LLM round trip.

Default actual generation-count limit is null. An optional operator-configured limit can lock only `generate`; it is not a normal stopping target or a successful-delivery signal. No regression scoreboard, Planner self-scoring, mandatory reasoning form, automated RSI or knowledge publication is introduced.

## Model-visible instructions and context

The initial common manual states that the task has a limited budget and that additional generation has a cost. It also explains conditional continuation questions and two-stage delivery. It does not publish the number of free attempts, the pressure schedule, the numeric limit, or the fact that no hard limit is configured. Routine initial exploration should not be accompanied by imminent-failure warnings.

Expose only:

- Generated candidate count, separately recorded failed/uncertain render attempts, and known cumulative rendering elapsed time.
- A concise budget-awareness notice whose later wording emphasizes deliberate continuation without claiming a remaining fraction or proximity to exhaustion.
- Whether the current action requires a justification, and the questions to answer when it does.
- Actual generation availability. A real lock may be disclosed when it applies, without revealing other hidden configuration.

Do not label rendering wall time as exact GPU compute time or currency cost. Unknown failed-call costs stay unknown. Displayed facts must derive from actual receipts; prompt pressure is a separately recorded intervention.

Examples of permitted pressure wording:

- Initial: `This task operates under a limited budget. Use the available resources deliberately while developing and evaluating your proposal.`
- Continuation: `Before spending resources on another generation, answer the continuation questions using the actual candidates, previous prompts and observed results.`
- Later: `Further generation warrants a deliberate choice. Explain why another attempt is preferable to reviewing and delivering a retained candidate, and what this attempt is intended to change or establish.`

Later wording can become firmer, but must not expose labels or phrases such as `50%`, `half consumed`, `near exhaustion`, `remaining`, `last chance`, `five of six`, or `unlimited generation`. No fake runtime termination or failed outcome is recorded. The operator-only audit stores the pressure version, trigger state and exact visible text.

Audit every Planner-visible surface: system/manual text, context, execution-profile summaries, task instructions, generation receipts and tool errors. Existing `max_generations: null`, exact limits or hidden policy settings must not leak through a generic configuration dump. Restrict the audit to operational disclosure; historical evidence and visual subject matter are not grounds for new prose censorship.

## Questions and tool behavior

Use three stable questions:

1. Which retained candidate currently seems most suitable for delivery, and what unresolved issue makes you choose to continue?
2. What will this attempt change or establish, and why use this input video? State plainly if it is resampling rather than a new realization.
3. Why is the expected benefit worth another generation instead of entering delivery confirmation now?

The manual requires a serious, specific answer tied to actual observations and prompts. It does not require private reasoning transcripts, numeric predictions or a particular favored strategy.

Extend the existing `generate` operation with one optional free-text `justification` argument. When the runtime has requested justification, accept any nonempty string; do not require separate answers, keywords, a minimum substantive length, semantic novelty, or a favorable quality judgment. Enforce existing general working-language/input validity rules consistently. A missing/blank explanation returns the questions and consumes no render request, seed or GPU resource.

Pre-announce this requirement in the result/context before the next decision. A compliant model submits prompt, input and justification together in one operation. It can instead inspect, read, select or finish. If it revises the prompt while answering, bind the recorded justification to the actual dispatched input and prompt. Do not send the justification to Bernini or use it to bias Critic scores.

Preserve the exact explanation, visible pressure/questions, proposal/action identity, actual input/prompt and subsequent receipt. Repeated or poor explanations are legitimate raw records for later review, not runtime rejection criteria. Existing note/workspace remain optional.

## Actual resource control

Keep pressure settings and real generation locking independent. An operator-only configuration can enable an actual generation limit; default is disabled. Avoid ambiguous coexistence with the old limit branch that marks the whole task `budget_exhausted` as soon as `generate` is refused.

An enabled generation lock rejects only new renders and leaves observation, reading, history, optional Critic, delivery selection and confirmation available. Do not impose a one- or two-action closing allowance. Existing technical recovery/context-resource pauses remain resumable and incomplete.

Define counting explicitly in implementation: successful candidates determine the exploration-to-justification transition; actual submitted render requests, definite failures and uncertain attempts are separately recorded for consumption and any configured actual cap. Missing justification is not a submission. Recovery of the same signed request never consumes a second slot or changes the paired successful-generation seed sequence. Do not start a replacement request while an earlier outcome is uncertain.

## Two-stage delivery with review reuse

Keep `finish(video, message, stop_reason)` unchanged. The first satisfied finish always creates a delivery proposal and does not complete the task, even if Planner previously saw an ordinary Critic report.

- If a valid review already matches the selected candidate, source, original request and frozen Critic protocol/model, reuse its original complete report. Do not make another scoring call merely because this is delivery.
- If there is no valid matching report, dispatch one existing one-shot Critic request. No follow-up conversation or semantic-answer repair is added. Preserve the existing transport/reconciliation rules.
- Present the full report, with all five dimensions, reasons, evidence and unknowns, in an actual subsequent Planner model input. Do not condition the confirmation step on low scores or keyword matching in the previous message.
- Confirm delivery only from a later Planner response that finishes the same proposed candidate after that exposure. The first finish response and an automatic completion callback are not confirmation. The existing message carries the model's explanation and accepted tradeoffs, with no new acknowledgment form or semantic evaluator.
- Planner may observe, read and take notes before confirming. Changing the delivery choice or generating another candidate invalidates the pending confirmation proposal. A later proposal may still reuse the unchanged candidate's valid report, but must go through a new post-proposal exposure and decision.
- Critic has no advice, score threshold, veto or selection authority. Unknown/low scores do not prevent a valid confirmation. Technical failure or absence of a usable review leaves the task incomplete rather than silently bypassing review.

The shared delivery verifier and experiment archival gate must check this sequence. Preserve all old reports and their identities. All five independent-scoring positions and their deduplication remain as already approved; GLM/Sonnet scores never enter Planner context.

## Implementation boundaries

Use a small cohesive helper for continuation state if useful. Integrate with existing runner, context, execution/profile preparation, delivery review/verifier, recovery and reporting rather than duplicating them. Rework the uncommitted fresh-only implementation left by the withdrawn instruction.

Update both full/no-experience common manuals and tool descriptions, common semantic operation guidance where needed, experiment task instructions and configuration projections. Keep style assets, curated experience bodies, renderer conditions, model identities and Critic rubric unchanged. Maintenance Skills may receive a minimal reference explaining the new evidence record; do not rewrite the experience library or invoke a maintenance pass.

Provide passive per-generation and batch navigation connecting pressure, questions, explanation, actual prompt/input and outcome. No online usefulness grading or automatic causal attribution is added.

## Verification and migration preparation

Required focused checks:

1. Two initial successful generations work without justification; the next missing/blank explanation submits nothing. A nonempty weak or repeated explanation is accepted without semantic review.
2. A normal compliant call supplies its explanation and renders without an extra Planner call. Recovered calls reuse their identity and do not duplicate cost/seed charging.
3. Model-facing context/manual/tool results show spent facts but hide policy thresholds, total/remaining limits, ratios, disabled-limit facts and proximity-to-exhaustion phrases.
4. Null limit allows later generations. An optional real limit locks only generation; observation and a full delivery-confirmation sequence remain available.
5. Existing valid Critic reports are reused with zero new scoring calls; absent reports trigger one logical call; both paths require actual post-proposal report exposure and a later confirmation.
6. Wrong candidate/hash/profile, stale confirmation or initial finish replay cannot complete. Low/unknown scores can be confirmed. Generation or candidate changes require a new confirmation proposal.
7. Full and no-experience share the operating mechanism; Direct, independent-judge isolation, archival and resource recovery remain intact.
8. Migration can preserve an old active or completed run's exact prefix and old final record, then require the new confirmation flow without mandatory rerendering.

Use offline fixtures, saved media and mocked model responses for these checks. Show exact exported initial context, continuation context, accepted generate explanation and cached-review confirmation input. Label them software examples, not observed model improvement.

Record explicit versioned migration from the frozen runtime/profile/manual hashes; never overwrite old fingerprints to claim unchanged conditions. Prepare, but do not execute, live migration while the user's experiment pause remains active. Preserve ongoing/finished records and uncertainty; no SSH polling, real API call, GPU dispatch or automation restart is needed for this implementation turn.

Deliver the implementation commit, verification results, model-visible examples, remaining limitations and migration-ready status. Update superseded plan statuses and the paused checkpoint narrowly without relabeling the experiment as resumed. Root reviews the implementation; the Sol thread remains the sole execution owner.
