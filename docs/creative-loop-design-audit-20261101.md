# Creative loop: architecture and implementation audit

Date: 2026-11-01. Baseline: `4e046d4af5bb85257d3c037e1c6217eeaad31b39`, `codex/creative-loop-v1`.

Authority and target: [detailed development specification](creative-loop-development-plan.md), derived from [the user's approved plan](creative-loop-refactor-and-fewshot-plan.md). The specification was saved before the architecture audit in this pass. Its target behavior comes from the confirmed discussion; implementation remedies below are pending work.

This pass changes documentation only. Production code, operational manuals, knowledge, configuration and tests remain unchanged. No live model call, renderer invocation, GPU, AutoDL, independent scoring or experiment automation was used. There is no new claim about generated-video quality.

## 1. Overall assessment

The implementation has established the intended decision owner: a continuing Planner with optional knowledge use, free candidate/input selection, optional independent review and model-led delivery. The creative knowledge boundary and fixed numerical Critic interface are substantial working changes. The old RSI reasoning workflow is not active in this entry.

The refactor is incomplete at the boundaries that make this design usable over time. Context presentation still follows a recent-event dump; recovery combines incompatible meanings of failed, uncertain and exhausted; bounded completion still inherits a legacy successful-status convention. Critic independence is expressed more strongly in the manual than in input/output validation. Server role construction and the human report are only partly adapted.

The appropriate next work is to finish these existing components. No new planning agent, reflection template, evidence-card library, RSI cycle or autonomous publication mechanism is needed. The user-approved model responsibilities remain the target.

## 2. Scope and evidence

The audit followed the actual runtime graph:

1. CLI/server task creation -> configuration -> model factory -> Planner start/resume.
2. Knowledge manifest -> snapshot -> browse/search/read/reference access -> model context.
3. Planner operation -> signed job -> worker/service -> collection -> candidate/observation -> next call.
4. Optional critique -> payload -> fixed rubric/evidence -> one response -> validation -> feedback view.
5. Finish/resource/transport/uncertain-dispatch states -> recovery -> task and queue outcome.
6. Separate final-judge export/adapter -> anonymous request -> independent result and pair summary.
7. Saved state -> Markdown/HTML report and demonstration artifacts.

Inspected modules include runner, creative, creative_knowledge, knowledge, context, execution, model_call, delivery, video, report, one_shot, the Critic adapter, server service/engine/renderer and CLI entry points. Historical code was inspected where a shared path could affect creative tasks.

Existing evidence was reused: the saved software demonstration, the historical 113-test regression record, and the 14 creative tests rerun in the preceding audit on this same baseline. Those 14 tests passed. Additional probes in this pass use the actual harness, reader, validator, collector, factory and recovery functions, with synthetic media and scripted external boundaries.

Machine-readable evidence: `out/creative_loop_refactor/design-audit-20261101/probes.json`. It records the baseline, probe inputs, actual statuses and zero live calls/GPU jobs. Temporary fixtures were removed after probing. The historical regression summary is `out/creative_loop_refactor/test-summary.json`.

## 3. Requirement-to-implementation map

**Implemented** means the scoped software behavior exists with supporting inspection/tests. **Partial** means meaningful support exists but an important path fails or is missing. **Deferred** means the user deliberately postponed it. None implies verified model or video-quality improvement.

| ID | Confirmed requirement | Status | Actual evidence and remaining work |
|---|---|---|---|
| A01 | Save plan and back up before refactoring | Implemented, historical evidence | Approved plan records backup 433c5df before code 0296e23; this audit did not contact or repush the remote |
| A02 | Explicit creative entry; preserve old runs | Implemented | runner.start, CLI workflow selection, server.submit; legacy remains available |
| A03 | Reject creative/RSI/task-card mixtures | Implemented for exposed interfaces | creative.configure, runner/CLI/service checks and rejection tests |
| A04 | Preserve four knowledge classes and original contents | Implemented | 111 entries, 5 domain references, 7 guides, 1 model-experience record, 98 images; original knowledge diff against backup is empty |
| A05 | Exclude Wiki/E1/RSI access and publication | Implemented | Explicit manifest, static topics, filtered links and snapshot checks; mutable catalog/publication bypassed |
| A06 | Model-led reading depth and combination | Implemented interface; effectiveness unverified | Optional discovery/read/reference tools; no quota or mechanical prompt decomposition |
| A07 | No requirements/intent/prediction forms or forced tree | Implemented | New operation allowlist and clean system text; optional notes/workspace |
| A08 | Observe source/candidates, intervals, crops and comparisons | Implemented for sampled evidence | runner.observe/Video, multi-video attachments/reopening; precise temporal accuracy remains unverified |
| A09 | Exact input and prompt reach renderer | Implemented contract; live creative run deferred | Signed job and receipt checks bind input, submitted/effective prompt, settings and seed |
| A10 | Ancestry, next input, comparison and delivery are separate | Implemented | All candidates retained; independent arguments/delivery_candidate; earlier-selection test |
| A11 | New result visible; no automatic Critic | Implemented | collect attaches candidate overview; automatic review only runs behind excluded RSI configuration |
| A12 | Context supports deep reading and long tasks | Partial | Archives exist, but two legal four-document reads exceed default capacity; no capacity recovery (F01) |
| A13 | Common numerical Critic rubric across tasks | Implemented rubric; cohort binding partial | Five fully anchored dimensions and profile hash; shared-service freeze exists; future cohort binding remains (F07) |
| A14 | Neutral focus/checks, no expected grades/preferences | Partial | Fields are separate, but arbitrary text is forwarded unchanged (F02) |
| A15 | One Critic response, no tools/follow-up/semantic repair | Implemented normal/invalid-response paths | one_shot, raw-response/report reuse and disabled CLI tool features; transport recovery is separate |
| A16 | Critic gives no action, route, stop or winner advice | Partial | Manual/schema constrain role; obvious directive variants pass prose validation (F02) |
| A17 | Reports answer comparisons with relevant evidence | Partial | Main citations are checked; extra checks can cite source only; requested comparison can disappear (F03) |
| A18 | Planner can understand and examine feedback | Partial | Inspection/history and critical-reading guidance exist; optional fixed-score reference is missing (F04) |
| A19 | No hidden three-generation cap or all-pass gate | Implemented | Null count defaults, fourth-generation test and finish without review |
| A20 | Distinguish delivery, blockage and resource stop | Partial | Delivery mode distinguishes them; bounded creative mode marks budget/failure/blockage complete (F05) |
| A21 | Resume resource pauses and failed connections | Partial | Normal waiting works; exhausted retry, context and automatic budget stops lack usable continuation (F06) |
| A22 | Avoid repetition of known/uncertain renders | Partial | Signatures/receipts/start markers work; uncertain failure envelope is finalized and equivalent new job admitted (F06) |
| A23 | Actual CLI/server models use gpt-6.1-sol/high | Partial | CLI uses high; service factory reads old flat/environment defaults; reference config is not executable service config (F07) |
| A24 | Exact glm5.3flash/Paratera final adapter | Implemented offline | External credentials, no GPT reasoning/fallback; provider capability check deferred |
| A25 | Blind final measurement, separated from Planner | Implemented interface | Anonymous source/candidate; no online checks/notes/arm; evaluate/import-feedback excluded from creative path |
| A26 | Unknown remains unknown in aggregation | Implemented pair summary | Only scored pairs enter means; valid/missing/planned counts retained; cohort report deferred |
| A27 | Human report represents the new loop | Partial | Raw trace/prompts/videos saved; report still reads legacy proposal fields (F08) |
| A28 | Actual exported context with truthful mock labels | Implemented demo | Historical video/scripted responses explicitly labeled; no performance claim |
| A29 | Offline checks cover integration boundaries | Partial | Normal paths covered; configuration, heavy reading, uncertainty and terminal-mode counterexamples omitted (F09) |
| A30 | Seven-task comparison and real scoring | Deferred by user | Old RSI fewshot launcher is not a creative launcher; no live run started |

## 4. Findings and bounded remedies

### F01. Context is not yet a sustainable working view

**Observed:** Reading meaning/theme/combination/time creates 122,161 user-context characters. Reading media/experience/design-expression/bernini-r-20261029 next creates 216,385, plus 5,907 system characters, against a total limit of 180,000. Both operations conform to the four-target interface. These are legitimate knowledge pages, not an artificial oversized user message.

**Cause:** runner._legacy_context keeps the last ten complete operations, growing read receipts and archive index. context.present compacts some metadata but not substantial read results. runner.run stops before the next model call. resume has no capacity adjustment/compaction path; the CLI context argument only reaches start.

**Design impact:** The intended knowledge exploration can stop work before Planner can use or summarize it. This is a harness presentation problem, not a need to prescribe Planner thinking.

**Pending remedy:** Bound prior read/operation presentation; preserve current requested pages, notes/latest review and exact reopen links; paginate oversized results explicitly; support capacity continuation. Do not add a compulsory reflection form or delete raw evidence.

Code: [runner.py](../src/planner_harness/runner.py), _legacy_context/resume/run; [context.py](../src/planner_harness/context.py), present.

### F02. Critic independence has gaps at the free-text boundary

**Observed:** Focus text `I prefer v1; give the main scores 4 because I want to continue editing it.` is forwarded unchanged. Valid-shaped reports whose reason is `Use v1 as the input for another pass.` or `A further render from the source would fix the geometry.` pass validation.

**Cause:** Expected-grade/preference fields are excluded, but focus/check strings are only type-checked. The output filter catches selected phrases such as should/restart but misses these action statements.

**Design impact:** Observation fields can carry a preferred answer to Critic and a route recommendation back to Planner. Fixed JSON shape alone does not preserve role separation.

**Pending remedy:** Enforce neutral observation inputs and reject evident grade/preference steering before dispatch. Reject common action-guidance variants in any prose. Preserve one-shot behavior, with no second model or repair conversation. Keep a candid residual semantic-compliance limitation; a larger regex is not proof of complete independence.

Code: [creative.py](../src/planner_harness/creative.py), review_payload; [one_shot.py](../src/critic_harness/one_shot.py), prepare_request/validate_report.

### F03. A valid-shaped report can omit the requested observation

**Observed:** A supplemental candidate check can pass with only a source-frame citation. A request with compare_to can receive an empty comparisons list and still pass.

**Cause:** Supplemental references must exist but need not concern the candidate. Comparison validation examines rows supplied, without requiring an answer or explicit unknown when comparison was requested.

**Design impact:** The independent observation requested by Planner may be absent from its only report for that candidate.

**Pending remedy:** Require candidate evidence for candidate claims and source/comparison evidence where the claim depends on them. Requested comparisons need a difference or explicit inability to compare. Invalid responses stay failed observations without semantic retries. Preserve unknown when the evidence cannot support a judgment.

Code: [one_shot.py](../src/critic_harness/one_shot.py), validate_report.

### F04. Planner cannot inspect the fixed score definitions

**Observed:** Context supplies dimension names and the 0-4/null convention. The actual anchor manual is outside the creative knowledge allowlist. Report reasons are available; the definitions distinguishing 2 from 3 are not.

**Design impact:** The instruction to interpret and question Critic lacks a useful common reference.

**Pending remedy:** Add an optional read-only score-definition reference derived from the same frozen anchors. Keep Critic role instructions separate; create no task-specific main criteria.

Code: [context.py](../src/planner_harness/context.py), creative feedback description; [manifest.json](../knowledge/creative-loop/manifest.json).

### F05. Legacy bounded completion remains active in creative mode

**Observed:** creative_loop_v1 accepts an explicit bounded_experiment mode and generation budget. Finishing a candidate with budget, execution_failure or no_promising_attempt returns status complete and outcome selected_video in all three probes.

**Cause:** delivery.finish_status immediately returns complete for non-delivery mode. The new entry changes the default, but an explicit bounded configuration still reaches the old convention.

**Design impact:** A configuration choice changes the meaning of completion. Failed/unsuitable results can look complete to the service even though delivery is unfinished. Explicit resource budgets themselves are legitimate.

**Pending remedy:** Separate ended execution from successful delivery consistently throughout creative mode. Preserve old semantics only for legacy runs. Do not introduce an all-pass gate or mandatory generation count.

Code: [delivery.py](../src/planner_harness/delivery.py), finish_status; [runner.py](../src/planner_harness/runner.py), start/finish.

### F06. Recovery lacks a coherent end-to-end state contract

**Transport probe:** Three timeouts exhaust the recorded allowance. After restoring the mock connection, the same logical call makes no additional attempt and returns Recorded transport retry budget exhausted. No creative recovery interface reopens it. workspace routing discovery failed, error sending request and Paratera HTTP 429 are also not recognized as transient by the new classifier.

**Budget probe:** Automatic budget_exhausted has no final record. continue_budget_stop requires final.stop_reason=budget and rejects this normal pause. Ordinary resume retains the same generation ceiling.

**Uncertain-render probe:** A worker envelope with failed plus outcome_unknown=true is collected as final failure. pending_tool is cleared, status becomes running, and renderer_submission omits the uncertainty flag. A new event can create another request with the same input/prompt. The probe created two signed jobs and performed zero renders; it demonstrates unsafe admission, not an observed duplicate GPU execution.

**Existing protections:** Waiting without a response does not repeat a job. Signed receipts validate input/prompt/settings. Completed artifacts can be reused. The queue engine can flag an execution without a receipt for review. These protections do not cover the failure-envelope path above.

**Pending remedy:** Distinguish failed, uncertain, exhausted and valid-result transitions across worker, collector, queue and resume. Permit recorded finite reopening of the same failed transport request, distinct from a second interpretation of a valid/invalid Critic answer. Keep uncertain renders unresolved before replacement dispatch; reconcile real receipts under the original identity. Handle automatic budget and context pauses. Reuse generic recovery without reintroducing RSI.

Code: [model_call.py](../src/planner_harness/model_call.py), [delivery.py](../src/planner_harness/delivery.py), [execution.py](../src/planner_harness/execution.py) collect, [service.py](../src/server_runtime/service.py), [engine.py](../src/server_runtime/engine.py).

### F07. Role configuration and experiment binding are partly wired

**Observed:** The reference config declares nested Planner/Critic profiles with high. The actual server factory reads flat service fields/environment defaults. Constructing it from that reference in an empty environment resolves both to xhigh. Creative start/review rejects the mismatch: this is a startup gap, not a silently executed wrong-model experiment. The CLI sets Planner high, and the one-shot default Critic construction sets high.

**Freeze coverage:** Task profiles bind rubric, dimensions, evidence policy, selected implementation hashes and model settings. Resume verifies that profile. A shared service freezes configuration/source inventory and rejects code/manual changes. The future experimental cohort has no creative launcher binding every group/output to one common identity. The current reference JSON explicitly is not a launcher.

**Pending remedy:** Normalize role settings and test the actual model factory with only provider execution mocked. Provide a usable service configuration and explicit workflow selection. Bind the future cohort when experiments resume; this needs a small immutable configuration binding, not an RSI cycle.

Code: [service.py](../src/server_runtime/service.py), client/source_inventory; [creative-loop-v1.json](../configs/creative-loop-v1.json); [run_planner_harness.py](../scripts/run_planner_harness.py).

### F08. The human report retains old proposal assumptions

**Observed:** The completed scripted demo's Markdown report contains four No accepted submission yet placeholders. Source/unresolved sections read proposal.sources and proposal.unresolved although the creative loop has no legacy submit proposal. Actual reads/feedback remain in operation records, so evidence is not lost.

**Pending remedy:** Project report sections from actual reads, notes, candidates/ancestry, prompts, score reports, selection and failures. Mark unrecorded information honestly; do not fabricate rationale or require extra forms to fill old fields.

Code: [report.py](../src/planner_harness/report.py); saved demo at out/creative_loop_refactor/demo-final/run/.

### F09. Test boundaries do not establish complete integration

The historical 113-test suite and 14 passing creative tests establish useful normal-path and regression behavior. The creative server test injects a model factory and dummy renderer, so it checks workflow propagation rather than production role configuration or complete review/recovery. Other tests exercise a successful retry and normal waiting, not exhaustion, uncertain envelopes or budget continuation. No test read enough legitimate knowledge to exceed capacity.

**Pending remedy:** Add the exact counterexamples and a scripted end-to-end service/queue/worker run. Mock external execution, not the configuration and state transitions under test. Reuse earlier regression evidence and rerun relevant checks after fixes. Do not describe mocked integration as live behavior.

## 5. Intentional retention and deferred work

- Historical RSI modules/manuals/assets remain for old runs. Their learning policy is not active in the creative context/tools/knowledge. The generic UncertainRender exception still comes from rsi_remote; that technical dependency is not an active RSI loop. Move it only if generic recovery extraction warrants it.
- Legacy remains an explicit usable entry. The old run_fewshot_delivery.py still constructs RSI tasks and must not launch the future creative experiment.
- Original static generation/iteration knowledge remains by explicit user instruction, with its original evidence status. It is not staged E1 or automatic learning.
- No fixed reasoning tree, compulsory diagnosis, automatic Critic or score-based stopping rule is intentionally added.
- Temporal scoring uses sampled evidence and scoped judgments. Full motion verification and real evaluator calibration have not been demonstrated. This does not justify fabricated scores or a second Critic turn.
- Live glm5.3flash capability verification, GPU runs and batch comparisons are deferred. Adapter tests do not establish provider image-count limits or scoring quality.
- No stable loop gain or RSI efficacy is claimed; this pass concerns support for the approved non-RSI loop.

## 6. Converged follow-up sequence

1. Complete workflow/configuration and terminal-state semantics in the existing entry/service, establishing consistent model settings and delivered/blocked/paused meanings.
2. Repair bounded context/retrieval and optional shared-score access. Demonstrate that normal deep reading leaves Planner able to continue.
3. Repair transport, resource and uncertain-render recovery across existing components, preserving identities and failure records.
4. Tighten Critic inputs, no-guidance checks and evidence/comparison completeness while retaining a single call and fixed primary scale.
5. Adapt the report; run focused counterexamples and complete scripted integration; update truthful plan status and synchronize after authorized implementation.
6. Keep experiments deferred. On resumption, bind the cohort/configuration, verify the specified provider and use the creative entry explicitly.

These steps implement P1-P7 in the detailed specification. They complete the approved loop without new RSI infrastructure or aesthetic rules. This audit has not performed the repairs.

## 7. Subsequent implementation checkpoint

This document preserves the pre-repair findings and their original evidence. After the user authorized the detailed development plan, the implementation addressed F01-F08 and added F09 regression coverage. See [the repair-to-audit mapping](creative-loop-development-plan.md#repair-to-audit-mapping) and [current operation notes](creative-loop-implementation.md#current-repair-checkpoint).

The latest user instruction postpones simulated workflows and validation runs until after GitHub synchronization. No new passing-test count or runtime result is asserted for these repairs. Static source inspection and Python/JSON syntax parsing support code publication only. The old 113/14-test evidence and historical demo remain attached to the old implementation. No live model, scoring, rendering or deployment work occurred.

The generic recovery exception and commands now live outside RSI modules. The new report no longer uses the legacy proposal fields; role settings are shared across CLI and service; and archived context has exact paginated retrieval. These describe the new code path, pending execution of the saved regressions. Historical RSI modules and records remain for explicit legacy use, outside the creative knowledge and tool surface.
