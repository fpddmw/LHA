# Agent-loop defect review and bounded refactoring proposal

Date: 2026-10-30. Status: **the lightweight first round below is approved for implementation and local software checks; the broader packages remain a roadmap. No experiments are authorized.**

## Latest scope adjustment: a thin first round

The user approved this narrower implementation after reviewing the risk of engineering-heavy reflection and candidate workflows. Harness support should make evidence and experience easier to use without making the model a form-filler. Experience and judgment revision is the next substantive priority.

Implement now:

1. Extend the existing `observe` operation to inspect several task videos together and reopen recorded observations. Keep explicit identities/times; do not infer motion alignment. Reuse existing `video` and `history` access for full provenance and feedback.
2. Reduce repeated provenance/feedback in new-run context. Keep the original task, optional notes, candidate identities, the latest relevant feedback, and exact retrieval links. Older feedback summaries are attributed excerpts, with uncertainty and full findings available on demand. Notes remain optional and can accompany an ordinary operation; no new reflection stage is required.
3. Add concise question/scope descriptions to existing knowledge entrances. Preserve full entries, empirical claims, decision advice, retrieval freedom, and frozen material versions.

Compatibility: record the new context presentation version for new runs. Older runs retain their old context path and saved instructions; do not migrate archived states or pending calls. Keep original raw feedback and events unchanged. Preserve model freedom to generate immediately, choose any existing input, stop early, or omit notes.

Deferred: candidate-ranking machinery; fixed reflection forms; compulsory alternative comparisons; automatic memory summarizers; broad Critic changes; Claude configuration/calls; global-RSI validation/publishing automation; all substantive experience/judgment rewrites; live rendering and model experiments. The larger packages below describe intended later work, not this round's implementation checklist.

Verification and delivery: run deterministic/scripted local software checks for comparative evidence labels, retrieval fidelity, optional note continuity, old-run compatibility, frozen entrances, and unchanged rendering requests. Produce an explicitly offline preview of actual context construction using saved artifacts. Do not present that preview as a new model decision or measured quality gain.

Implementation status: the lightweight first round is complete, with 48 distinct local software checks passed. The [implementation account and exact model-input preview](lightweight-harness-round1.md) show the changes and limitations. No model experiment or renderer run was performed. Substantive experience and judgment revision remains the next priority.

The [approved direction](agent-loop-rsi-direction.md) is saved separately. This review uses existing task states, tool requests, online feedback, independent evaluation records, and implementation. It adds no rendering, model evaluation, or new visual judgments. Descriptions of video defects below are attributed to the recorded reviewers. All original experiment artifacts remain unchanged.

## 1. Decision and scope

Retain the continuous model-led Planner, arbitrary-candidate editing, knowledge corpus, durable jobs, evidence provenance, and frozen runs. Improve how the system learns from an attempt, compares its options, uses knowledge, and carries validated experience to later tasks. Stop treating completion of the old evaluation queue as the immediate objective.

This proposal has four implementation packages:

1. Planner task memory, candidate comparison, and decision support.
2. Decision-focused online Critic and separate Claude independent evaluation.
3. Scoped decision experience and better knowledge entrances.
4. Executable global RSI: evidence, candidate revision, validation, reviewed adoption, and rollback.

They share one small prototype. No replacement renderer, vector-database migration, autonomous code rewriting, universal preservation prompt, or full benchmark expansion is included.

## 2. Evidence coverage and interpretation

The four development topics are 041 short, 027 short, 024 long, and fewshot_004 long. Both full/no-knowledge loops finished on both renderers: 16 loops and 39 candidates, comprising 19 Bernini and 20 Ditto videos. Existing independent judgments cover all 19 Bernini candidates and only the two Ditto 041 candidates. Other Ditto conclusions below concern recorded behavior and online feedback, not independently measured improvement.

The separate single-pass ablation contains eight planning runs reused across two renderers, yielding 16 videos; 13 have completed independent records. Its eight Planner states each contain only `submit` and zero active reads. In contrast, all eight full-knowledge four-topic loops performed active reads. All eight also consulted the prior Bernini probe page, including the Ditto loops. Reading counts alone therefore neither establish knowledge benefit nor describe a universal failure to retrieve.

All 16 loop states have empty dedicated `notes` and `workspace` fields. Several consequential actions contain useful `purpose` explanations, and prior feedback remains available. This establishes that the explicit task-memory facilities were unused; it does not establish that the model performed no reasoning or forgot every prior result.

The four topics already appear in prior probe/guide material. Their use here is developmental. Reading same-task historical material and transferring Bernini observations to Ditto require explicit scope in later claims.

### Representative outcomes

Independent semantic scores below are normalized to 0–1; style and aesthetic scores retain the recorded 1–4 scale. They are existing model judgments, with their original uncertainty and protocol limitations.

| Case | Actual behavior and evidence | What it motivates |
|---|---|---|
| 041, both renderers and arms | All four loops stop after one generation. Style succeeds; Bernini full/no detail scores are 0.50/0.33, while Ditto's recorded semantic scores are 1.00. | Preserve the ability to stop early. Style simplification and incidental detail changes need task-sensitive interpretation. A mandatory revision would add work without an established benefit. |
| Bernini 027 full | Source → v1; source → v2; select v2. Existing independent scores show style 4.0 → 3.8 and aesthetic 3.90 → 3.76, with core/detail unchanged at 1.00/0.75. | The visible rationale for another attempt and the final preference need comparison with earlier successes. These coarse scores do not prove v1 is superior on every relevant detail. |
| Bernini 024 full | Source → v1 → v2; source → v3; select v2. Edit scores 0.8125/0.8750/0.8125, style 3.1/3.7/3.1, aesthetic 2.94/3.10/2.64. | Continuing an existing result can help, and returning to an earlier result can be sensible. The restart rationale deserves scrutiny without declaring every restart a defect. v2 detail/time remain unknown; its core score is 1.00. |
| Bernini table tennis full | Source → v1; source → v2 → v3; select v2. Edit 0.7222/0.3889/0.6667; core 0.8611/0.9167/0.7778; time 0.8333/1.00/0.8333. | This is an edit-versus-preservation tradeoff. v2 is not dominated by v1 on all metrics. A final comparison must explain why its preservation advantage warrants losing requested transformation. |
| Ditto 024 full | Source → v1 → v2; v1 → v3; select v3. Planner explicitly avoids v2's added opaque bars while reusing v1's successful color. | The user's proposed older-candidate branch already works technically. The gap is the quality and support of its use, rather than an absent route. Independent scores for these candidates are pending. |
| Ditto table tennis full/no | Each uses three source-based attempts and selects v1/v2 respectively. Online feedback still reports identity/geometry defects. | Rewording and additional preservation demands do not demonstrate a reliable repair strategy. These are useful failure cases, not independently scored gains. |

### The 024 restart, inspected directly

Bernini full `event-0005-critique` says v1 has strong subject-level glitch styling, weak coverage on seats/windows/jacket, and obscured facial/handset detail. The Planner reads `choose-editing-input` and generates v2 from v1 (`event-0007`) to extend coverage and improve handset visibility.

`event-0008-critique` says v2 adds background posterization, but convincing displaced scene content remains weak, independent RGB offsets are unconfirmed, and face/handset readability does not visibly improve. The Planner's next recorded purpose is:

> Restart from the source to recover facial and handset detail lost in both candidates, and test a global raster-and-displacement treatment against the observed concentration of neon patches on the man.

This is an actual explanation, not a reconstruction of hidden reasoning. It has an intelligible basis: the attempted continuation did not restore readability, and the original retains details unavailable or obscured in both candidates. The third-generation prompt also changes how the displacement is described. However:

- The record does not compare this option with a new branch from v1, another focused edit of v2, or stopping with v2.
- The rationale says detail is "lost" where the feedback often establishes obscuration or insufficient readability. These are different recovery situations.
- Original-input choice and prompt changes occur together; this one run does not isolate their effects.
- The final-generation benefit was uncertain. The record gives no clear account of why its expected benefit justified the cost and risk of regenerating the successful style.

After v3, the online Critic reports more natural upper-face detail but poorer horizontal glitch expression and recommends v2. The Planner selects v2. All candidates remain retained; they were not deleted or excluded. Independent scores support v2 over v3 on edit/style/aesthetic, while some preservation dimensions remain unknown.

Conclusion: the route was plausible and unsuccessful at improving the final delivered result. The defect is insufficiently discriminating branch justification, not an established universal rule that the third attempt must use v1 or v2. Ditto's same-task branch from v1 supplies a concrete contrasting example, with no controlled cross-renderer route comparison implied.

## 3. Defects mapped to responsibility

| ID | Evidence-backed finding | Responsible parts | Proposed repair and remaining uncertainty |
|---|---|---|---|
| D1 | Explicit task memory is unused in all 16 loops. The current context carries all feedback plus the latest ten operations; earlier entries require history lookup. Source and latest observation images are attached by default. | Planner, harness | Keep an editable task brief and a compact factual candidate view visible, with exact evidence links. Reuse notes/purpose instead of adding forms. Whether this improves decisions remains to be tested. |
| D2 | Candidate decisions sometimes explain a desired benefit without comparing feasible alternatives. Bernini 024 is one example; final fewshot full comparison discusses v3 versus v2 while v1 remains a relevant tradeoff. | Planner, harness, decision experience | Give the model easy same-question comparison of source, parent, earlier alternatives, and final contenders. Encourage short evidence-linked explanations for consequential choices. No fixed route selector or numeric acceptance gate. |
| D3 | Bernini fewshot v3 is described as focused refinement but its prompt changes walls, window construction, lighting, floor, tabletop glow, and glasses together. Feedback then reports geometry/ball regressions. | Planner, Critic, expression experience | Choose a coherent priority for the next attempt; identify optional additions and expected collateral effects. Multi-change requests remain valid. This trace does not identify which edit caused each regression. |
| D4 | Feedback can correctly list missing requirements but leave their actionability unresolved. Fewshot v1 process diagnosis explicitly says many failed properties were already requested; later prompts largely restate them. | Critic, Planner, renderer-scoped experience | Distinguish an omitted request, an unrealized explicit request, uncertain observation, inherited damage, and a proposed recovery. Explanations of mechanism remain hypotheses. Repeated rewording needs a substantive reason to expect a different result. |
| D5 | Candidate-only edits sometimes seek restoration of source identity information absent from the selected candidate. Fewshot v3 adds generic thin rectangular glasses to v2, whose original glasses were not discernible. | Planner, harness, semantic/decision experience | Expose the actual renderer input capabilities. Separate invented reconstruction from evidence-grounded restoration. Source-based editing, an earlier candidate, inspection, or acceptance of limits remain model choices. |
| D6 | Knowledge use differs between single-pass and loop runs. All full loops read the old Bernini page; that does not establish successful transfer to Ditto or novel tasks. Search is lexical and title-weighted. | Skill assets, knowledge access, Planner | Surface questions a page can answer, renderer/settings scope, limitations, and links to complete material. Retain model-led search/composition. Diagnose actual use before replacing search infrastructure. |
| D7 | Independent 027 severity differs for comparable upper-left architectural changes; online 024 feedback leaves RGB separation unknown where the independent rubric supplies positive edit scores. | Independent scoring, Critic calibration, report interpretation | Review matched evidence and requirement interpretation under a new Claude protocol. Preserve disagreements. A disagreement is not automatic proof that online Critic is wrong. Unknown observations should prompt inspection or a qualified decision, rather than a default failure label. |
| D8 | Existing global experience code can propose/publish one topic but lacks a validation/adoption loop. Its packet uses first/latest images and raw absolute paths; exported runs retain remote paths. | Global RSI, harness | Resolve verified exported assets, select relevant evidence, connect proposals to isolated validation results and runtime versions, and gate shared publication on actual review. Existing publication/rollback machinery is reusable. |

Operational cost is also visible: Bernini fewshot full Critic reviews used 11, 11, and 10 calls; no-knowledge reviews used 9, 16, and 16. Dense inspections are sometimes necessary for motion claims. These counts motivate reuse and decision-focused inspection, not an arbitrary shorter limit or weaker evidence standard.

## 4. Package A: Planner and task-level RSI

### Concrete changes

1. **Expose a task working brief without adding a mandatory form.** Reuse the existing free-text notes facility; permit an optional note update alongside an ordinary operation so maintaining it does not consume a separate model turn. Guidance asks for only consequential discoveries, changed assumptions, and useful unresolved questions. Original request/source remain immutable anchors. Existing `purpose` remains the place for a concise action explanation; no private reasoning transcript is requested.
2. **Add a deterministic candidate view.** Derive available video IDs, real parents, prompts, seeds, feedback availability, and links from recorded state. Display recorded feedback summaries with attribution and uncertainty. Do not generate an automatic quality ranking, infer an unrecorded preference, or label a candidate discarded without the model's decision. Keep source and older candidates accessible.
3. **Support comparative inspection.** Add a lightweight multi-video comparison operation using existing evidence infrastructure. The Planner chooses videos, interval, crop, and question. Show explicit timestamps and mapping limitations; matching frame indices do not establish motion alignment. Let the Planner pin relevant observations for subsequent decisions instead of being limited to source-plus-latest attachments.
4. **Keep useful material available with bounded context.** Persist the working brief, candidate view, and selected evidence. Link to full reports and original reads; reuse already returned summaries verbatim with provenance. Detailed findings remain retrievable. Record what was present versus available on demand, so a later review can distinguish failure to access from failure to use evidence. No new summarizer model is required in the first implementation.
5. **Improve decision guidance.** Before a consequential revision, consider what it is intended to change, why the selected input still supports that change, what already works, and what result would alter the next decision. Write a brief explanation where it matters. Permit stopping and keeping an earlier result. Treat remaining budget as a ceiling, not a target.

Primary files: `src/planner_harness/runner.py`, `video.py`, `execution.py`, `OPERATIONS.md`, and `report.py`. Add one small context/evidence helper only if needed to keep the runner readable. Keep `generate(input_video, prompt, seed?)` unchanged and retain planning-only behavior.

### Proposed manual wording, for review only

> Use each result to update your understanding of this task. Keep a short working note when a finding changes your next decision. For a consequential revision, explain the evidence that motivates it and why the chosen input is useful. Consider retaining a successful result, editing an earlier candidate, or returning to the source as the task warrants. A new attempt should pursue a plausible improvement or resolve an important uncertainty. State tentative explanations as tentative. The generation budget is a limit; finishing early is available.

This is decision guidance, not a required output schema or a program that rejects unexplained creative choices. Review decision quality through traces and outcomes; do not substitute verbose justifications for good decisions.

### Task-level RSI in operation

Understand the source and request → consult useful knowledge → choose a proposal → generate → inspect/receive feedback → revise the task brief and strategy when warranted → choose the next operation or final result.

For 041, a convincing first result can lead directly to completion. For fewshot, repeated missing tabletop glow can lead to an investigation of attribute placement and collateral changes rather than another larger list of demands. For 024, feedback can motivate a new input, but the working note should distinguish obscured detail from confirmed missing structure and explain the actual tradeoff. These are possible uses, not preassigned task scripts.

The demonstrable RSI unit is an observed finding linked to a changed later decision. A failed attempt can contribute information, while quality improvement remains a separate measured outcome. Model weights and shared knowledge are unchanged within a task.

## 5. Package B: Critic and independent scoring

### Online Critic, still GPT-6.1-sol

Retain evidence-seeking observations, native timestamps, source anchoring, uncertainty, and outcome assessment before execution-prompt access. Focus its decision-facing response on:

- attainment against the original request;
- gains and regressions relative to the relevant candidate(s), including inherited defects;
- consequential uncertainty and the observation that could resolve it;
- possible explanations and next-step implications, with their evidential status.

Existing finding/comparison records already represent much of this. Improve guidance and output composition before inventing a new rubric. A partial implementation can have several causes; the Critic should not turn a missing property into a confident claim that stronger wording will fix it.

Allow multiple relevant alternatives in `critique`, preserving compatibility with the current single `compare_to`. With the current three-generation budget, source plus three candidates fits the existing four-video evidence capability. Parent, comparison candidate, and original source retain distinct identities. The Planner decides the comparison set; the harness validates IDs and supplies it.

Reuse verified prior observations and findings when their media, region, interval, and purpose match. Reinspect when the question or uncertainty warrants it. Keep the original assessment and add a separately attributed comparison or diagnostic qualification. A targeted online decision need not request a full independent benchmark review. If a full-clip motion claim is made, its coverage requirements still apply.

A short final summary should separate observed improvements, remaining defects, and plausible actions. Detailed evidence remains linked and available. Candidate preference, when requested, should name its tradeoff and comparison set. The Planner retains the decision.

Files: `src/critic_harness/runner.py`, `adapter.py`, `evidence.py`, `OPERATIONS.md`, and `guides/judgment.md` / `guides/evidence.md`; corresponding Planner job construction in `execution.py`.

### Independent scorer, Claude family

Add a separate provider adapter/configuration in `src/evaluation/backends.py` and the existing evaluation entry point. Exact Claude model, transport, access, supported image limits, and reasoning configuration are implementation-time choices to verify. No credentials or paid calls are needed for this plan. Do not assume GPT `xhigh` settings transfer to another provider.

Preserve original requirements, source/output evidence, uncertainty, and separate edit/preservation/style measures. Use fresh independent contexts; keep Planner prompts, online recommendations, method labels, and candidate order cues out of scoring. New judgments carry a new evaluator/protocol version. Old frozen GPT results remain historical.

Review a small set of existing disagreements before relying on the new scorer: 027 severity; 024 readable versus obscured phone/RGB effects; fewshot table-rim versus support glow and identity loss; 041 authorized simplification. No new renderer call is needed for this initial calibration. The reference is reviewed visible evidence and task meaning, not automatic agreement with old GPT scores.

For later prototype comparisons, report generation gains separately from final-choice quality. Compare first/selected and the tradeoffs among actually generated alternatives; avoid inventing a scalar "best candidate" when dimensions conflict. Preserve unknowns and actual costs.

## 6. Package C: skill and knowledge changes

Preserve the 111 complete entries, five domain references, original sources, and existing cross-links. The first revision targets interpretation and use, not wholesale rewriting of artistic knowledge.

| Location | Actual planned revision | Basis and evidence status |
|---|---|---|
| `knowledge/README.md`, `READING.md`, `INTEGRATION.md` | Update stale loop-stage descriptions; provide entrances for understanding a scene, developing a visual relationship, resolving an execution failure, comparing candidates, and learning from attempts. Keep paths optional and cross-linked. | Current map still describes generation feedback as subsequent work. Single-pass and loop reading differ substantially. |
| `knowledge/guides/meaning.md` | Distinguish appearance change, readable action/role, source identity, incidental structure, obscuration, and confirmed loss. Support ordinary activities without invented narrative. | 041 simplification, 024 obscured handset, fewshot lost glasses/identity. |
| `knowledge/guides/design-expression.md` | Separate a coherent visual proposal from the modifications needed for the actual input. Explain object/attribute/part binding; preserve freedom in short prompts and fidelity to specified details in long prompts. | Concrete style cues helped earlier probes; missing effects can persist despite explicit wording. No universal prompt length or preservation wording is established. |
| `knowledge/experience/choose-editing-input.md` | Add scoped route cases: useful current result; local regression that suggests an older branch; unavailable source information; overall direction change; repeated failure with uncertain cause. Include costs, counterexamples, and evidence limits. | Bernini 024, Ditto 024, and fewshot trajectories. Initial route preferences remain common-sense hypotheses until compared. |
| `knowledge/experience/express-edits.md` | Explain coherent revision scope, optional additions, repeated unrealized instructions, and reconstruction versus restoration. Avoid presenting "focused" as an assurance of locality. | Fewshot v3 changes many components and requests generic glasses; output regressions are confounded. |
| `knowledge/experience/inspect-and-compare.md` | Compare relevant older alternatives under the same question; preserve multi-objective tradeoffs; distinguish unknown from failure and style-authorized distortion from unintended damage. | Fewshot final selection and 027/024 disagreement cases. |
| `knowledge/experience/use-design-knowledge.md` | Explain how a design or execution question can motivate a guide, full entry, or model-experience lookup; keep useful relationships without copying optional scene details. Display cross-model transfer limitations. | All full loops read the Bernini page; reading does not itself establish benefit. |
| New proposed `knowledge/experience/learn-from-attempts.md` | Provide concise guidance for updating task beliefs, recognizing repeated failure, revising a hypothesis, and deciding when further work has little expected value. Link to actual cases and counterexamples. | Bridges task-level RSI to later evidence extraction. Initial guidance is labeled as proposed/common sense. |
| `knowledge/experience/catalog.json` and `source-map.json` | Index approved new topics and expose scope/status/renderer metadata for experience, while retaining stable IDs and provenance. | Current catalog distinguishes origin/version but supplies limited applicability information at discovery time. |

Expose applicability and questions in `knowledge.py` browse/search results. Retain lexical retrieval initially, with question-oriented entry text and model-led query reformulation. A vector index is deferred until trace evidence shows that the relevant content cannot be found using the simpler interface.

Experience pages should distinguish: recorded observations, tentative explanations, actionable starting advice, and validated scope when available. These are editorial conventions for reusable material, not forms imposed on the Planner. A good page explains when an action is promising and what could make it inappropriate. It does not require a fixed aesthetic mapping.

New material is first staged for review/validation. The active corpus and ongoing frozen runs remain isolated from unreviewed proposals. Original source pages stay intact; changing an empirical interpretation updates its editorial experience layer with provenance.

## 7. Package D: executable global RSI

### Reuse what exists

`src/planner_harness/experience.py` already supports evidence packets, one-topic proposals or `no_change`, reviewed publication, base-hash checks, archived versions, a recoverable publication journal, and rollback proposals. `Knowledge.freeze()` isolates run materials. Extend these components rather than building another agent controller.

### Missing executable chain

1. **Build a decision-centered evidence packet.** Resolve exported media through the verified export catalog and SHA256 identities, without rewriting raw remote paths. Include the original request, relevant candidate ancestry, exact edits, observed feedback, known independent outcomes, knowledge reads, visible decisions, and failures. Attach images/intervals relevant to the proposed claim rather than automatically only the first/latest observations. Missing independent judgments stay missing.
2. **Propose a scoped revision.** Reuse the current proposer, allowing a small coherent set of experience/manual changes where warranted. Include the actual diff, reason, applicable renderer/task conditions, contrary cases, and the anticipated behavioral change. A `no_change` result remains valid. Stable contracts or runtime changes produce a separate development proposal; the experience publisher cannot execute code edits.
3. **Stage an isolated candidate version.** Create a manifest of base version, proposed files, affected instructions/runtime revision, and evidence sources. Existing runs continue on their original snapshots. New topic creation must be explicitly included in the reviewed change; do not broaden the publisher to arbitrary paths.
4. **Validate at the right level.** Deterministic checks establish link integrity, snapshot isolation, media identity, and reproducibility. Existing-media replay checks whether evidence is accessible and decisions use it; it does not establish a video-quality gain. A later bounded live comparison tests a behavior-affecting revision using the same renderer settings, budget, scorer, and paired seeds where feasible. Tasks used to write the experience are labeled development; at least one related unseen task is needed to investigate transfer.
5. **Adopt or reject with traceability.** Bind validation receipts and actual human review to the proposed version. Publication uses the existing versioned mechanism after authorization. Record rejected or inconclusive proposals without activating them. Manual/runtime changes use a reviewed development diff; their version joins the same manifest. Subsequent runs record which active version they used.
6. **Watch for regressions and prepare rollback.** Compare later applicable cases with the claimed scope and retained counterexamples. Produce a rollback/revision proposal when needed. Preserve rejected hypotheses so the next proposal does not repeat the same unsupported conclusion.

Implement the evidence resolver/extractor and validation-manifest/report logic as small deterministic helpers near `experience.py`, with a thin extension of `scripts/revise_planner_experience.py`. Suggested CLI stages are `collect`, `propose`, `validate`, `publish`, and existing rollback proposal support. Their names and record schemas serve the operator/runtime, not extra Planner forms. Validation requires an explicit experiment specification and authorization; creating a proposal must not auto-launch generations or paid calls.

The first global-RSI demonstration should take one evidenced problem, produce a concrete candidate revision, evaluate its intended behavioral change, and either adopt it with review or retain the baseline. Selection of that first problem follows this review; it is not precommitted to the 024 restart. A broad multi-component rewrite cannot establish which individual experience was effective, so component claims require scoped comparisons.

## 8. Practical sequence after review

| Step | Work and dependency | Reviewable result |
|---|---|---|
| 1 | Implement the shared task/candidate evidence view and lightweight memory support from A; draft the corresponding C manual/experience changes in an isolated version. | The same saved task can expose older candidates, relevant findings, actual input capabilities, and concise task updates without additional mandatory forms. |
| 2 | Implement B's comparative Critic support, evidence reuse, concise feedback, and separate Claude adapter. | Inspectable source/parent/alternative comparisons; old run compatibility; independent scoring configuration that cannot leak into online roles. |
| 3 | Complete D's resolver, scoped proposal packaging, validation receipts, and reviewed version activation. | One end-to-end software path from an exported run to a staged revision and a traceable adopt/reject decision. Synthetic/replay checks are labeled. |
| 4 | After implementation review and a bounded run specification, calibrate on selected saved cases and run a small live prototype. | Evidence about task-level strategy updates, first-versus-selected tradeoffs, knowledge contribution, cost, and transfer of a specific global revision. |

Only steps needed to validate the intended change should be run. Software checks cover candidate identity, context/evidence restoration, uncertainty retention, original-source anchoring, old-run resumption, provider isolation, version/publisher boundaries, and rollback. They do not assert a required creative choice. No test should hard-code that 024 must restart or that fewshot must select a particular version.

The prototype specification will select a few complementary cases: a short task where early completion can be correct, a long task with interacting edits, a case with a genuine input-choice tradeoff, and a related unseen task. It will cap generations and model calls and keep settings comparable. It is not the old full benchmark queue. Expanding experiments depends on a reviewed improvement in actual outcomes and decision quality, including regressions and cost.

## 9. Evidence index

- [Four-topic independent summary](../out/agent_loop_live/20261030/four-topic-review/review.html), [normalized records](../out/agent_loop_live/20261030/four-topic-review/records.normalized.json).
- Bernini loop states: [041 full](../out/agent_loop_live/20261030/phase2/completed-041-pair/tasks/041__short__full_knowledge/run/state.json), [027 full](../out/agent_loop_live/20261030/phase2/completed-027-pair/tasks/027__short__full_knowledge/run/state.json), [024 full](../out/agent_loop_live/20261030/phase2/completed-024-pair/tasks/024__long__full_knowledge/run/state.json), [fewshot full](../out/agent_loop_live/20261030/phase2/completed-fewshot-004-pair/tasks/fewshot_004__long__full_knowledge/run/state.json); sibling no-knowledge states retain their complete traces.
- 024 full online feedback: [v1](../out/agent_loop_live/20261030/phase2/completed-024-pair/tasks/024__long__full_knowledge/run/jobs/event-0005-critique/active-critic/feedback.json), [v2](../out/agent_loop_live/20261030/phase2/completed-024-pair/tasks/024__long__full_knowledge/run/jobs/event-0008-critique/active-critic/feedback.json), [v3 versus v2](../out/agent_loop_live/20261030/phase2/completed-024-pair/tasks/024__long__full_knowledge/run/jobs/event-0010-critique/active-critic/feedback.json).
- Fewshot full online feedback: [v2](../out/agent_loop_live/20261030/phase2/completed-fewshot-004-pair/tasks/fewshot_004__long__full_knowledge/run/jobs/event-0007-critique/active-critic/feedback.json), [v3 versus v2](../out/agent_loop_live/20261030/phase2/completed-fewshot-004-pair/tasks/fewshot_004__long__full_knowledge/run/jobs/event-0009-critique/active-critic/feedback.json).
- [Bernini 024/fewshot independent records](../out/agent_loop_live/20261030/independent-evaluation-024-fewshot/service/evaluations/).
- 027 severity evidence: [full v2](../out/agent_loop_live/20261030/independent-evaluation-027/service/evaluations/bernini__027__short__full_knowledge__v2/judge/semantic.raw.json), [no-knowledge v2](../out/agent_loop_live/20261030/independent-evaluation-027/service/evaluations/bernini__027__short__no_knowledge__v2/judge/semantic.raw.json). Similarity and severity disagreement warrant matched review; this document does not supply a new visual adjudication.
- [Ditto verified export catalog with all actual state paths](../out/agent_loop_live/20261030/ditto-phase2/shutdown-export-catalog.json).
- [Eight single-pass planning states](../out/ablation_probe/20261030_no_knowledge/planning/), [single-pass evaluation completeness](../out/evaluation_runs/20261030_ablation/partial-recovery-index.json).
- [Current Planner implementation](../src/planner_harness/runner.py), [knowledge access](../src/planner_harness/knowledge.py), [experience revision implementation](../src/planner_harness/experience.py), [Critic implementation](../src/critic_harness/runner.py), [Critic integration](../src/critic_harness/adapter.py), [independent evaluator backend](../src/evaluation/backends.py).

## 10. Historical retrospective boundary

When this retrospective was first prepared, only the approved direction, historical-plan supersession, and proposal were saved. No runtime, active skill/manual, evaluator setting, experiment result, or automation was changed during that documentation turn. The later lightweight first-round authorization and its limits are stated at the top of this document. Its implementation is described in [the first-round account](lightweight-harness-round1.md). Remaining old evaluations are retained as incomplete historical work; they are not prerequisites for the current development work.
