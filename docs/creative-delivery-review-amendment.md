# Mandatory delivery review and Planner confirmation

Date: 2026-11-01. Status: withdrawn before deployment and superseded by [continuation questions and informed delivery](creative-continuation-and-delivery-plan.md). The fresh-review-only proposal below is retained as history. Current delivery reuses a valid matching report and requires a new post-proposal Planner input and decision. Live experiments and polling remain paused.

## User decision and scope

The user requires an actual review at the point where Planner proposes delivery. An earlier optional Critic call does not satisfy this requirement. The same change applies to current code, both Loop arms in the running seven-topic experiment, and any Loop that already finished: reopen its final delivery sequence while retaining all existing candidates and evidence. Direct has no Planner and remains unchanged.

The new sequence is:

`Planner proposes delivery -> fresh one-shot online Critic report -> report returned to Planner -> a subsequent Planner decision confirms delivery or continues work`.

Critic retains the same frozen five-dimensional rubric, model settings, evidence rules and descriptive-only role. It has no score threshold, veto, advice, input choice or stopping authority. Independent GLM/Sonnet final scores remain outside Planner context.

## Thin harness implementation

Keep the existing `finish(video, message, stop_reason)` interface. Do not add a required acknowledgment form, requirements, intent, prediction ledger or RSI mechanism.

- The first `finish` with `stop_reason=satisfied` records a delivery proposal, not completion. The runtime starts a dedicated online Critic request for the proposed generated candidate and returns a waiting result. Ordinary review caches cannot fulfill it.
- Bind the proposal, review request, exact candidate hash, original request, source identity and frozen Critic profile. Use a distinct delivery-review job identity. This is a newly authorized role-specific review, not a follow-up conversation asking Critic to explain an old answer.
- Submit one logical Critic call for that proposal, without internal tools or semantic response repair. Keep existing bounded transport recovery and durable request identities. A retry/resume of the same proposal reuses its request/result rather than creating another review.
- Critic receives the existing neutral evaluation input. Do not forward Planner's delivery rationale, preferred scores or expected outcome. A minimal final check uses the original request, original video and proposed candidate; keep the established rubric and structured report unchanged.
- After collecting a valid report, explicitly include its complete content and proposal identity in the next Planner context. Preserve the actual saved model input that contained it. The program must not finish automatically, nor replay the initial finish response as confirmation.
- A later Planner `finish` can confirm that same candidate only when its actual model input contained the completed proposal's report. Use the existing message for a concise delivery explanation, including consequential findings or accepted tradeoffs. Record the proposal/report/model-input/confirmation relationship automatically. Do not pretend this trace proves private understanding.
- Planner can inspect evidence, read, write a note, or reconsider. Changing the proposed delivery candidate or submitting another generation ends the pending proposal's applicability. A later delivery proposal starts a fresh one-shot review. Failed validation or transport never creates a confirmed delivery.
- Normal optional `critique` remains available during work. Its ordinary per-candidate cache stays separate from the dedicated delivery review. Existing valid reports remain available as evidence.
- Resource pauses and `no_promising_attempt`/`execution_failure` retain their existing incomplete semantics. They do not need a successful-delivery review and must not be relabeled as delivery.

The shared runtime and completion verifier must both enforce the sequence. Saving a manually assembled `final.json`, an old `satisfied` flag, an earlier ordinary review or an unconsumed newly completed report must not bypass the requirement.

## Code and manual touchpoints

Keep the state logic in a small cohesive helper where practical. Integrate it with:

- `src/planner_harness/runner.py`: finish interception, model-input exposure, final confirmation, proposal invalidation and resumable state.
- `src/planner_harness/execution.py` and `creative.py`: dedicated review job identity and collection; ordinary-cache isolation.
- `src/planner_harness/context.py`: complete pending delivery report and an unambiguous next-action explanation.
- `src/planner_harness/delivery.py`: verify the actual proposal-review-confirmation chain.
- Shared full/no-experience operation manuals and runtime/tool descriptions: explain that first finish requests review and later finish confirms, with no grade gate or extra form. Remove conflicting wording that implies optional review is the only route or one review total per candidate now covers delivery review.
- Experiment task instructions, frozen-profile/version handling, scheduling/archival/reporting code and focused tests: use the same rule for both Loop arms. Keep Direct and blinded final judging unchanged.

Do not expand this into a new scheduling framework. Reuse existing durable jobs, model-call records, queue recovery and the five-position independent-judging adapter.

## Safe migration of the running experiment

The new rule changes Planner-visible protocol and control flow. Record it as an explicit user-authorized amendment, with previous and new runtime/profile/manual hashes, effective time, affected tasks and existing candidate prefix. Preserve the old snapshot; do not silently replace its fingerprint or claim that every historical action used the new rule.

The current execution owner must hold old-protocol delivery acceptance and next-topic advancement while preparing migration. Allow in-flight rendering and model calls to settle before moving their state; reconcile receipts and actual process ownership. An already-returned old-model finish is a proposal to be reviewed under the new rule, not confirmation.

For active Loops, retain the request, videos, prompts, seeds, notes, observations, knowledge snapshot and call history. Introduce the new shared delivery instructions at a recorded safe boundary and continue the same task without rerendering an existing candidate.

For completed Loops, snapshot the old final state and retain the old completion record. Reopen the selected video as a delivery proposal, obtain a fresh Critic report and run a real subsequent Planner decision. Planner may reconfirm, choose another candidate or generate further work. Extra generation is conditional on its decision, not a mandatory replay of the entire task.

Existing Direct and first-output scores stay valid. Reuse final independent scores by the existing exact media/request/protocol/model identity. If the final selection changes, score only the newly required selected output; retain the previous score with its original role/history. Version any completed topic summary/archive that depended on superseded delivery selection, and preserve its old manifest rather than overwriting it.

Keep the seven-topic, three-arm, five-scored-position contract. Both Loop arms must complete the new delivery sequence, both independent judges and verified archival before the next topic. Keep generation/turn caps null. No new rental or shutdown authorization is introduced.

## Necessary verification and completion evidence

Focused tests must establish:

1. An old optional review cannot complete delivery; initial finish creates a new request and remains incomplete.
2. A valid final review alone cannot complete delivery; confirmation requires a later Planner model input containing it.
3. A same-candidate confirmation succeeds with low scores or explicit unknowns, without a grade threshold.
4. Changed candidate or further generation requires a new proposal/review; recovery of one unchanged proposal does not duplicate its call.
5. Invalid/failed review or stale/tampered binding cannot pass; recovery preserves original attempts.
6. Reopening a previously completed Loop retains old final evidence and candidates, then runs a fresh review and Planner confirmation without automatic generation.
7. Full and no-experience arms share the mechanism; Direct and independent judging retain their existing scope and isolation.
8. Topic receipts, verifier and archive gate reject old completion claims and accept only the new confirmed chain.

Commit and push the implementation, manual updates, focused checks and migration instructions. Provide the actual live proposal, fresh report and post-report Planner decision when the first such sequence completes. Report software readiness and live completion separately. The original conversation reviews the design and targeted issues; the Sol execution thread remains the sole process/experiment operator.
