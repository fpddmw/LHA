# Creative loop refactor and deferred fewshot comparison

Approved by the user on 2026-11-01. This plan implements the preceding reviewed conversation, including the user's correction that all four skill classes remain available. Execution is limited to documentation, backup, code, offline software verification and GitHub synchronization. GPU deployment, paid model calls, generation experiments and independent scoring are deferred until the user resumes experiments.

## Accepted design

One continuing Planner understands the request and source, reads knowledge, creates visual proposals, observes candidates, chooses inputs and prompts, requests optional independent review, and selects a delivery. A thin harness provides tools, evidence, continuity and durable execution. It does not prescribe a thought sequence or require diagnostic forms.

Preserve four classes: operating manuals; semantic understanding; visual style and design knowledge; static generation and iteration knowledge. Preserve the map, comparative guides, complete entries, domain sources and provenance. Static advice retains its original common-sense or empirical status. This change does not invent or publish experience findings.

The new `creative_loop_v1` entry excludes Wiki, E1 evidence cards, RSI summaries and updates, proposers, replay, adoption, requirements forms, intent/prediction ledgers and task-specific scoring cards. Legacy code and historical runs remain identifiable and usable. Explicitly reject mixed creative-loop/RSI configuration.

Planner and online Critic use `gpt-6.1-sol` with `high` reasoning. Newly authored repository material and model working instructions are English. Communication with the user is Chinese. The independent judge is exactly `glm5.3flash` through Paratera; no automatic model substitution.

## Ordered implementation

1. Save this plan. Inspect changed and untracked code, documents, knowledge and configuration. Exclude secrets, runtime logs, weights and large outputs. Push a pre-refactor snapshot to a separate GitHub branch and verify its remote commit before code changes.
2. Implement the isolated creative-loop profile and an explicit, snapshotted knowledge manifest. Navigation, search, reading and reference access share that allowlist. Provide clean operating instructions and navigation without excluded mechanisms; preserve original source assets.
3. Reuse the continuous Planner and durable jobs. Support knowledge/observation tools, `generate(input_video, prompt)`, `critique(video, compare_to?, focus?, extra_checks?)`, optional notes/workspace, `delivery_candidate(video)` and `finish(video, message)`. New candidates receive observation material, not automatic reviews. Keep current delivery choice, next input and comparison target separate. Retain exact prompts and all candidates. No implicit three-generation cap or all-pass gate. Paused, blocked and delivered states remain distinct and resumable where applicable.
4. Implement one-shot Critic review with a frozen experiment-level manual, schema, evidence policy and model profile. Main axes are instruction_adherence, content_preservation, temporal_consistency, visual_integrity and aesthetic_coherence. Define all integer anchors from 0 through 4, evidence requirements and boundary examples for each. Unknown scores are null; distinguish unassessed and not applicable. No task-specific main rubric generation.
5. A Critic request contains the original user request, source, candidate, optional comparison, deterministic visual evidence and optional focus/custom checks. It excludes Planner expectations, preferred winner and continuation rationale. Main scoring always uses the complete fixed rubric; supplemental checks cannot alter it. Output contains protocol_id, candidate_id, main_scores (status/score/reason/evidence_refs/limitations), descriptive comparisons, extra_checks and unassessed. No advice, repair directions, prompt rewriting, input selection, stopping or winner recommendations. One logical request and report; no tools, follow-up or semantic repair calls. Reuse a successful report for the same candidate. Invalid reports remain recorded failures. Bounded transport retries are recorded; durable render receipts prevent duplicate execution.
6. Implement the separate Paratera final-judge adapter/configuration for `glm5.3flash`. Credentials remain outside the repository and request artifacts. Do not pass GPT-specific reasoning options. Independent scoring uses the frozen main rubric without Planner focus/checks, online reviews, condition labels, iteration number or selection reasoning. Live endpoint/model-capability validation is deferred.
7. Run offline checks with saved videos/records and mock model responses. Export actual code-built Planner contexts, knowledge reads, post-generation context, Critic request/report and final-judge request. Clearly label this software demonstration, not observed model behavior or a quality result. Push the implementation and documentation and verify the remote revision.

## Required software acceptance

- All four skill classes are readable; excluded content cannot re-enter through navigation, summaries, links or reference tools.
- Observation, reading, generation and finish work without old requirements/intent forms.
- A successful Critic report uses one logical request; no follow-up or model-driven JSON repair. Supplemental checks do not alter main dimensions or score anchors.
- Any retained candidate can be edited or selected; input ancestry, delivery choice and comparison remain distinct.
- A fourth generation is allowed; interruptions do not duplicate completed or uncertain renders.
- Unknown is never zero, video/evidence identities are checked, and old feedback is not silently rejudged.
- Independent scoring stays separate and is configured only for the specified model.
- Original knowledge and historical behavior receive focused regression checks.

## Deferred experiment

After later user authorization, use the existing two-RTX-5090 AutoDL container and seven original fewshot long requests. Compare Direct (unchanged user prompt to Bernini) with Loop-first (joint knowledge and Planner/harness effect), then Loop-final with Loop-first (iteration and selection effect). Preserve the established 40-step v2v_apg, maximum size 848, native time axis and matching initial seeds/settings. Independent scoring uses `glm5.3flash` with anonymous inputs and frozen axes, without feeding scores back into the Planner. Report per-task results, unknowns, costs, actual generation count, ancestry and incomplete deliveries. Deployment, model calls, scoring and experiment automation remain deferred in this implementation pass.

## Progress and verification

- Plan saved: complete.
- Pre-refactor remote backup: verified at `433c5dfd9dab6dc9949c5d5111480cf34486dce0` on `codex/loop-pre-refactor-20261101`, before code changes. Runtime proposal logs and generated reports stayed local. Existing baseline line endings were preserved.
- Isolated knowledge and Planner integration: implemented; CLI and server entry preserve `creative_loop_v1`. Original style/guide/static-topic files are unchanged. Snapshot checks retain 111 entries, 5 domain references and 98 reference images.
- Frozen one-shot Critic: implemented with all five anchored dimensions, deterministic visual evidence, recorded bounded transport retries, successful-report reuse and no semantic repair calls.
- Paratera final-judge adapter: implemented for exactly `glm5.3flash`, with anonymous input and separate results; no live capability check or fallback.
- Offline tests and inspectable demonstration: final focused suite passed 113 unique tests with zero failures, errors or skips under `requirements.critic.txt` (OpenCV 4.13.0.92, NumPy 2.5.4, Pillow 12.3.0, PyAV 19.0.2). Saved fewshot_004 media and scripted responses produced `out/creative_loop_refactor/demo-final/`, with zero live model calls or renders. The demonstrated original request, successful reads, single Critic job, four classes and exported files were verified. Final test details are recorded in `out/creative_loop_refactor/test-summary.json`; [implementation details](creative-loop-implementation.md) explain the scope and limits.
- Implementation remote synchronization: verified at `0296e23b88ce96ac39b9043db24e35564ea12fc6` on `codex/creative-loop-v1`. This implementation commit includes the new code, manuals, configuration, tests and walkthrough generator. Main was not overwritten. The final documentation checkpoint records this verification.
- Live experiments and API capability verification: deferred by user.

Update this section after each substantive implementation step with actual checks and commit references. Report a consequential departure from the accepted design before implementing it.
