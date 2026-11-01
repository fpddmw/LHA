# Live agent-loop execution plan

> Superseded execution priority, 2026-10-30: the user has approved the [two-level RSI development direction](agent-loop-rsi-direction.md) and the [lightweight first harness round](agent-loop-defect-review-and-refactor-plan.md#latest-scope-adjustment-a-thin-first-round). Only that local implementation and software verification are current work. Do not resume old scoring/benchmark queues, launch model experiments, publish shared experience, or restart GPU work under the historical authorization below. Historical protocols and results remain preserved. The future independent scorer is to be from the Claude family; Planner and online Critic remain GPT-6.1-sol. The older judge-efficiency proposals below are historical and are not the current model-selection direction.

Approved by the user on 2026-10-30 (Asia/Shanghai). This plan supersedes the earlier proposal to validate Ditto first.

## Current execution priority

The user's later 2026-10-30 instruction prioritizes the existing four topics: 041 short, 027 short, 024 long and fewshot-004 long. Finish their two-renderer knowledge comparisons, first-versus-selected evaluation and generation-cost reporting before admitting unrelated new tasks. Keep already in-flight generation running. The established full-benchmark cohort and its unsubmitted denominator remain recorded for later continuation.

Use exactly one shared local independent-judge slot. The loop owner first finishes its already running twelve Bernini 024/fewshot candidate evaluations, then verifies every result, queue snapshot, model subprocess exit and the identical Windows OS lock before scoring the sixteen deduplicated single-pass ablation results. Remaining four-topic Ditto independent judgments follow the verified completion and real process exit of that single-pass batch. CPU evidence preparation and fixed-encoder computation may continue within existing limits.

The user subsequently withdrew session (2) from managing this work and assigned this 4090/5090 loop thread sole scheduling responsibility. The former session stopped its own preparation/gate/release processes without acquiring the shared scoring lock. Preserve its partial preparation and withdrawal record; complete and verify those inputs before using them. The obsolete inter-thread handoff watcher is stopped. Do not wait for or request a release from the withdrawn session.

The logical lock is the absolute Windows UNC path to `out/agent_loop_live/20261030/benchmark/source-annotation-owner`, using the existing `RunLock` implementation. The active lease is `benchmark/scoring-slot-lease.json`. A Linux flock on a similar path is a different lock and does not satisfy this lease. Keep online Critic diagnostics separate, preserve frozen cards and raw judgments, and use the current compatibility layer for unified reporting. Relative originality remains tied to each actual frozen reference cohort.

## Execution order

1. Use the existing single RTX 5090 and Bernini to complete one genuine three-generation integration run. First finish deployment wiring, then fix defects exposed by the real run. Preserve the original requirement and model-led decisions throughout.
2. After that run succeeds, proceed autonomously with the established loop evaluation and ablation tasks on Bernini, using the existing persistent renderer and bounded CPU/LLM/GPU pipeline.
3. Only after the initial Bernini loop works, inspect AutoDL through Edge for one RTX PRO 6000 or RTX 6000D. If one is available, deploy Ditto, verify its integration, and run the corresponding evaluation work. If neither specified card is available, abandon acquisition until the user returns. Do not substitute another card type.

The allocation is at most one card for Bernini and one card for Ditto. Existing H800 work belongs to its current owner and is not a destination for this new run.

## Initial real run

- Select one existing task outside the recent 041, 027, 024 and fewshot-004 debugging set. Preserve its source and exact original request, and record why it was selected.
- Use GPT-6.1-sol / xhigh for Planner and Critic. Freeze the runtime, manuals, knowledge and renderer configuration before starting.
- Run the complete sequence: source observation and knowledge access; a model-authored plan and English prompt; real Bernini generation; real Critic observation and feedback; continuation of the same Planner; two further real generations with feedback; final candidate selection.
- Request three generations as the validation task's explicit experimental instruction. The Planner still chooses the prompt and whether to restart from the source or edit a retained candidate. Do not fabricate feedback or force a particular creative route.
- Retain all attempts and failures. Distinguish three completed generations from retries, model turns and archived-video replays. Repair runtime defects before claiming the sequence works.
- Record exact submitted and encoded prompts, input hashes, parent relationships, source-time mappings, output media, model/settings revisions, observations, knowledge reads, Critic feedback and the final selection. Deliver a readable report joining these records.

## Deployment and resource handling

- Inspect the existing 5090 environment and current owner before deploying. Let its current batch finish; never kill or restart another session's work.
- Use a separate frozen runtime and run directory. Reuse verified model assets and the existing environment where suitable. Keep authentication private and outside tracked files.
- Check GPU availability at most once every 30 minutes while waiting. Active fault diagnosis may use shorter checks; unchanged status does not warrant repeated notifications.
- Resume from signed requests and verified completed responses. Do not duplicate a pending render or an uncertain model invocation.
- The existing resource scheduler uses one GPU slot per host and overlaps CPU preparation with bounded LLM work. Assign cross-host LLM capacity explicitly; preserve full video evidence and approved generation quality settings.
- Save and verify results before stopping a newly rented instance once its approved work is complete. Do not release the user's existing 5090 or H800 without the relevant authorization.

## Evaluation and ablations after integration

Reuse the established task manifests, evaluation protocol and ablation definitions after checking their current versions. Keep the integration example identifiable and separate from scored samples. Freeze the cohort and exact arms before launching a batch. Do not expand the experiment with invented arms or silently replace a frozen protocol.

Online Critic feedback guides the Planner. Independent final evaluation uses its own context and the original requirement, source and result; keep generation prompts and online feedback out of blind scoring. Preserve individual measures, uncertainty and evidence coverage. Existing formal evaluation jobs and their files remain under their current owner.

## Completion and reporting

The user scheduled the existing AutoDL RTX PRO 6000 instance to shut down at 17:50 Asia/Shanghai on 2026-10-30 (09:50 UTC), and explicitly requested continuity and organization. Finish and locally verify remaining video, trace and recovery-metadata exports before that deadline. Save actual unfinished or uncertain model calls without labeling them complete. No further GPU tasks, new rental or automatic instance restart are authorized by this shutdown instruction. Independent final scoring of saved outputs continues locally and does not require keeping the renderer GPU running. The shutdown handoff and export catalog belong under `out/agent_loop_live/20261030/ditto-phase2/` and are referenced by the operational checkpoint.

First report whether the real three-round loop succeeded, what defects were fixed, and the actual videos and decision trace. Then report batch progress and results separately. Software checks, integration outputs and benchmark evidence have distinct meanings. RSI publication is outside this execution scope.

The operational checkpoint is `out/agent_loop_live/20261030/checkpoint.json`. The thread heartbeat checks waiting resources every 30 minutes and advances only work authorized above.

## Judge efficiency follow-up after the current batch

On 2026-10-30 the user asked whether the independent GPT scorer uses excessive reasoning effort, suggested medium for future work, and asked to retain this consideration after the current tasks finish. Keep GPT-6.1-sol / xhigh for all remaining judgments in the current frozen comparisons, including failed-call recovery. This note does not change Planner or online Critic settings.

At batch closure, record actual scoring latency, available token/image usage, capacity failures and completeness alongside the results. Treat GPT-6.1-sol / medium as the first proposed configuration for the next evaluation batch. A cheaper image-capable model, currently GPT-6-Luna, is a candidate for routine scoring; stronger-model review of uncertain or consequential cases is a separate proposed use. These are follow-up recommendations, not validated quality-equivalence findings or an instruction to launch another experiment now.

Before adopting a cheaper judge, compare its key preservation/edit judgments, damage severity, unknown handling and candidate ordering on a small set of existing outputs with reviewed evidence. Existing xhigh judgments are a comparison baseline, not ground truth. Retain separate scorer identities and raw results; do not mix a replacement judge silently into this batch's primary tables. Subscription usage and API list prices are different cost measures. Lower reasoning effort affects reasoning work; dense image inputs, repeated evidence and three scoring calls per video also contribute to latency and cost.
