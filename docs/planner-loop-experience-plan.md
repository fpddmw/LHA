# Continuous Planner and experience implementation

Approved by the user on 2026-10-29: proceed with the immediately preceding reviewed design. This plan supersedes the unreviewed outer-loop strategy choices in `agent-loop-plan.md`. It preserves the working independent Planner and the complete knowledge corpus.

## Intended behavior

One Planner continues a task over observations, reading, generation and feedback. It chooses what to inspect, which knowledge to use, what proposal to develop, which source or candidate to edit, and when to finish. Tool arguments contain only information necessary to perform the operation. Natural-language notes are optional. The runtime records tool calls and artifact ancestry automatically; it does not require diagnostic forms, route applications, a fixed reading sequence, or an external acceptance decision before editing a candidate.

The model-facing material consists of a short operating manual plus semantic understanding, visual design knowledge, and generation/iteration experience. Existing maps, comparative guides, complete entries and provenance stay intact. Four new experience topics provide actionable initial common-sense preferences, distinguished from scoped experimental observations. These preferences are available immediately and can later be revised through evidence; they are not programmed routing rules.

## Work batches

1. Save this plan and preserve the existing runtime/material baseline. Add experience topics for editing-input selection, instruction expression, result inspection, and design-knowledge use. Improve semantic/request reading and the map. Keep authoring copies synchronized. Preserve the original 111 entries, domain references, source material and historical run artifacts.
2. Extend the existing Planner with one continuous task context, free-text notes, candidate observation, experience access, minimal generation/evaluation operations, and a final-result operation. Keep planning-only execution compatible. Snapshot the reading corpus used by a run so later experience changes do not silently alter or block it. Reuse actual read receipts and restore older records when needed.
3. Connect generation through a durable execution adapter, preserving exact prompts, actual effective inputs, source identity, settings and recoverable jobs. Any existing candidate can be used directly. Replace external route selection and per-round cold planning in the prior outer-loop draft. Read the separately developed evaluation interface and adapt to it without changing its metrics or implementation. Perform meaningful local checks and real Planner exercises, then live generation when the existing deployment and resources are available. Report an actual connection/resource dependency if it prevents live execution.
4. Add an experience-revision path that reads run records, proposes specific material changes with evidence, retains versions and supports reviewed publication/rollback. Initial experience is common-sense guidance, not fabricated empirical findings. Updates proposed from a task remain separate from shared active knowledge until reviewed. Do not automatically rewrite stable operating instructions, source documents or runtime code.

## Code scope and reuse

The primary implementation stays in `src/planner_harness/` and its CLI. Existing observation, knowledge access, model transports, checkpointing and reports are reused. Durable job handling from the earlier `src/agent_loop/` draft may be reused or replaced; its external decision stage, single-incumbent restriction and separate child-Planner default are withdrawn from the active path. Historical code and outputs remain identifiable. Other sessions' staged evaluation files and deployment experiments are not overwritten.

Work prose, skill material, comments and generated working artifacts are English; user conversation remains Chinese. User source requests retain their original wording. No subagents are used. The default execution model is GPT-6.1-sol with xhigh reasoning.

## Verification and delivery

Check knowledge preservation, discoverability, source tracking, resume behavior, tool-result integrity, arbitrary-candidate editing, technical failures and version isolation. Use genuine model runs to inspect freedom of reading and action, not fixed expected routes. Clearly label recorded-video/replay exercises. Live outputs, when available, must retain source, prompt, settings, output and feedback evidence. Unit checks and replay do not establish video-quality improvement.

Deliver a readable map and the actual experience text, an inspectable continuous task trace, a code/usage account, and the first evidence-linked experience revision proposal. A real loop can operate before a redesigned Critic exists by using observations and the available external evaluation interface; limitations remain explicit. New shared experience publication requires review of the concrete proposal.

## Status

Implementation is available in the active continuous Planner entry and [usage account](agent-loop.md). The initial four experience topics, semantic/request clarification, knowledge entrances and authoring copies are synchronized. The 111 complete entries and five domain references match the start-of-work baseline byte for byte.

The software checks cover 26 distinct tests across the original Planner, continuous task, worker boundary and experience publication. The knowledge validator reports all original references and local links intact. These checks use synthetic or mocked fixtures where appropriate and do not establish video-quality improvement.

Actual model records are in `out/planner_continuous/20261030/`. The first 041 task has read design sources and requested a live Ditto generation. It is queued behind existing H800 work, with bounded ten-minute availability checks. An experiment supervisor now handles remote result transfer, local evaluation jobs and automatic continuation of the same Planner; no new external route-selection stage is introduced. A separate, explicitly labeled historical-candidate review completed seven real Planner calls and three evaluator calls, with zero new generations. After reading two experience topics and inspecting both candidates, the Planner evaluated prior2, inspected a dense 0–0.75-second hand/notebook crop in response to unresolved motion evidence, then selected prior2 while retaining the full-clip motion limitation. The first experience review returned `no_change`: the supplied reading/planning records illustrate existing guidance but add no justified new empirical claim. Shared experience has not been revised by that review.

Live generation/continuation remains pending resource availability. The concrete run status and final validation account will be updated from actual receipts. No final performance gain is claimed from software checks, planning records or imported results.
