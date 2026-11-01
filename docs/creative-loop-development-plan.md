# Creative loop: detailed development specification

Date: 2026-11-01. Authority: the user's approved lightweight-loop plan and subsequent request for a plan-first, architecture-level audit. This is the technical expansion of [the approved scope](creative-loop-refactor-and-fewshot-plan.md), not a replacement research direction.

Current authorization: implement the full bounded repair plan and synchronize code/documentation to GitHub. The user explicitly deferred simulated workflows and validation runs until after synchronization. Add regression coverage but do not execute it in this pass. Static source inspection, syntax parsing and repository hygiene checks support publication; they are not behavioral validation. No GPU, AutoDL, live model invocation, evaluation, deployment or experiment automation is authorized. Repository prose is English; communication with the user is Chinese.

## 1. Design decisions recovered from the conversation

Subsequent discussion, 2026-11-01: [Skills, experience and task workspace](skill-experience-workspace-direction.md) records the agreed direction for reorganizing manuals and experience. Its technical route and experience lifecycle remain open. The contracts below describe the existing implementation; the discussion record does not activate cards or authorize the next refactor.

Subsequent approved implementation, 2026-11-01: [experience-library refactor](experience-library-refactor-plan.md) now resolves that direction. It adds two optional professional manuals, three external maintenance Skills, an explicitly reviewed curated catalog and passive usage/batch records. The old Wiki/E1/RSI exclusions below continue to apply. New explanatory entries are a separate bounded content surface; the current curated catalog is empty pending review of four drafted examples. Planner operations, Critic roles and the experiment deferral are unchanged.

| Confirmed decision | Architectural consequence |
|---|---|
| The model chooses how to understand, design and revise the video | One continuing Planner owns creative and operational decisions; no keyword decomposition, prescribed aesthetic or mandatory reasoning sequence |
| Keep the four skill classes, including the style library | Retain operating guidance, semantic understanding, visual style/design and original static generation/iteration knowledge |
| Knowledge can be explored and combined as needed | Map, thematic guides, complete entries and source references remain navigable; no reading quota or mandatory tree |
| Remove RSI and evidence-card machinery from this loop | No Wiki, E1, learned summaries, proposals, replay/adoption, requirements, intent, prediction ledger or task scoring cards in the new runtime |
| Critic is useful as an independent perspective, not an authority or substitute Planner | Planner decides when to request it and may inspect, qualify or disagree with its observations |
| Critic is partly frozen across the experiment | All main dimensions, 0-4 anchors, evidence rules, report format and model settings are common to the experiment; contextual reasons and supplemental checks vary by task |
| A task-specific goal is not a new primary metric | User requirements are interpreted under instruction adherence and preservation; no generated per-task main scoring protocol |
| Critic returns numerical structured output and gives no recommendations | Fixed score fields plus reasons/evidence/limitations; no repair, prompt, route, stop or winner advice, including in prose |
| No Critic follow-up | One logical request, one response; no tools, interrogation or semantic-repair conversation; further inspection belongs to Planner |
| Delivery is model-led, with no hidden three-generation ceiling | Source and all candidates remain usable; resource pauses, blockage and successful delivery are distinct |
| Online feedback and independent measurement have different roles | Online Critic uses gpt-6.1-sol/high; separate final judge uses exactly glm5.3flash through Paratera |
| Code and offline verification precede experiments | Direct/Loop-first/Loop-final comparisons and live API verification stay deferred |

Earlier RSI designs and reviewer proposals are historical material. They do not override these later decisions. Preserving legacy code for old runs is intentional; admitting its policy or forms to the new loop is not.

## 2. Intended runtime, from the model's perspective

The Planner receives the exact user request, a source-video overview, a concise tool manual and knowledge entrances. It can inspect a relation, read a relevant source, develop a visual direction, write a note or generate directly. These are available actions, not prescribed phases.

`generate(input_video, prompt)` sends the selected source/candidate and exact English prompt to the renderer. The harness persists that request, waits for its durable result, registers a new candidate and supplies its visual overview. The Planner continues the same task with the original request, its working notes, retained candidates and the new observation.

When an independent judgment would help, the Planner calls `critique` once for that candidate, optionally naming a comparison and neutral observation questions. The Critic receives a fixed visual evidence package and the experiment's scoring manual. Its report returns to the Planner as attributed evidence. Planner can inspect the cited video interval or another crop itself, revise its interpretation, choose another input, generate again, retain an earlier candidate, or finish.

The loop's potential benefit comes from decisions informed by the actual new video and prior candidates. Software must make this possible and traceable. Software acceptance does not establish that model decisions or generated videos improve.

## 3. Ownership and information boundaries

| Component | Owns | Receives | Must not own or receive |
|---|---|---|---|
| Planner | Task interpretation, creative proposal, knowledge use, prompt, editing input, review request, candidate tradeoffs, delivery | Original request/source, working material, candidates, online reports, tools | Independent final scores; compulsory RSI forms; a predetermined creative recipe |
| Harness | Persistence, scoped access, evidence transport, resource state, call identity, recovery, context presentation | Model operations and durable artifacts | A hidden ranking/selection policy; automatic Critic requests; fabricated semantic conclusions |
| Renderer | Video generation under recorded settings | Actual input video, exact prompt and renderer settings | Planner notes, proposed scores, Critic conclusions or hidden prompt rewrites |
| Online Critic | Fixed-dimensional observation and scoring | Request, source, candidate, optional comparison, fixed evidence, neutral focus/checks | Planner's preferred version, expected score, continuation rationale, generation history, knowledge-learning policy |
| Independent judge | Separate final measurement | Request, source, anonymous candidate, fixed main rubric/evidence policy | Arm, iteration, Planner trace, online scores, focus/checks, final-selection rationale |

Protocol parameters are experiment-owned. Planner can ask whether a visible attribute or relationship is present; it cannot replace scoring anchors or instruct a desired judgment. The shared score definitions should be inspectable by Planner without copying the Critic's role instructions into its system prompt.

## 4. Runtime contracts

### 4.1 Knowledge and manuals

- Preserve the existing map-to-guide-to-complete-source organization and reference images. Preserve original evidence status of static iteration advice. No style rewrite or new experience claims in this change.
- Use one explicit creative-loop manifest for browse, search, read, link expansion and reference images. Freeze readable text and reference-image identity for each run.
- Keep four useful entrances; class labels do not become required thought fields.
- Exclude Wiki, staged E1, publication state and RSI navigation through every access route. An inaccessible historical reference can remain attributed provenance; it must not silently open excluded material.
- Keep an inspectable main-score reference for interpreting feedback. Its wording and anchors must match the frozen scoring manual.

### 4.2 Planner tools and continuing context

| Operation | Contract |
|---|---|
| browse/search/read/view_reference | Scoped discovery and exact source retrieval, with automatic read receipts |
| observe | Source or retained candidates; time intervals, crops, chronological frames, multi-video inspection and reopening observations |
| video/history | Exact prompt, ancestry, execution receipt and archived observations/reports/operations |
| generate | Any available input video plus exact English prompt; no requirements or intent prerequisites |
| critique | One candidate, optional comparison, neutral focus and separate supplemental checks |
| note/workspace | Optional free text and model-organized nodes/links; no mandatory tree or reflection template |
| delivery_candidate | Provisional delivery choice, independent of the next render input and comparison |
| finish | Explicit selected candidate/message; preserve the distinction between delivery, blockage and resource interruption |

Persistent state contains the request, original source, all candidates/ancestry/prompts, exact calls/operations/reads, observations, optional working notes, intended delivery, online reports, pending jobs and terminal/interruption records. It contains no task requirements table, intent, prediction ledger or learned-memory update.

Model context is a view of that state, not a copy of the entire archive. Keep the original task, source overview, current working notes, candidate index and newest relevant result visible. Keep the latest valid Critic report complete; older reports retain scores, key evidence/limitations and full-record links. Large prior read results and operation payloads need bounded presentation with exact reopening paths. Preserve the freshly requested page or explicitly return a smaller page with continuation rather than making a request appear read when it was not supplied.

The context-size policy must make legal repeated reading and iteration possible. Use deterministic presentation, pagination and archived retrieval first. Do not add a compulsory model-summary call, a new thought form or silent truncation of evidence. Any unavoidable capacity stop must have a usable continuation path.

### 4.3 Rendering and candidate management

- Sign and persist the render request before execution. Capture submitted/effective prompt, input hash, renderer settings/seed and result hash.
- Resume pending work using its existing identity. A known result is collected rather than rerendered; an uncertain dispatch remains explicitly unresolved until its receipt is reconciled.
- Register every collected result as a distinct candidate with its actual parent. Generate an overview; do not trigger Critic.
- Selecting delivery, choosing the next input and requesting comparison are separate state operations. Later generation must not replace an earlier intended/final selection implicitly.
- No default three-generation rule. Explicit resource ceilings pause an unfinished delivery; they do not assert success. No all-pass review gate or mandatory review before finishing.
- The new workflow must retain these outcome distinctions even when an operator explicitly sets a bounded experimental budget. A queue attempt can end while delivery remains incomplete. Legacy snapshots can retain their old status semantics through explicit legacy dispatch.

### 4.4 One-shot Critic

The common main axes are `instruction_adherence`, `content_preservation`, `temporal_consistency`, `visual_integrity` and `aesthetic_coherence`. Each has all five integer anchors, evidence conditions and boundary examples. They apply across tasks; task context appears in reasons and examples of observed fulfillment, not new main dimensions.

`main_scores[dimension]` contains `status`, `score`, `reason`, `evidence_refs` and `limitations`. `scored` requires an integer 0-4; `unknown`, `not_assessed` and `not_applicable` require null and retain their different meanings. The complete report also contains protocol/candidate identity, descriptive comparisons, supplemental checks and unassessed scope.

Request preparation strips generation prompts, preferences, expected grades and continuation arguments. Optional focus/checks must remain observation questions subordinate to the rubric; free-text fields are not an alternative instruction channel. Obvious requests for desired grades or preferred candidates should be rejected before model dispatch, with a neutral explanation to Planner, without creating another Critic turn.

Every scored main finding must cite the candidate. Preservation also cites the source. Temporal findings cite chronological evidence and state coverage limits. A requested comparison must yield an observable difference or an explicit inability to compare. A supplemental outcome about the candidate needs candidate evidence, plus source/comparison evidence when its claim depends on them.

The initial approved evidence policy uses overview frames plus three short consecutive-frame windows per video. It is deterministic sampled evidence. It supports scoped judgments and explicit unknowns; it is not full-clip trajectory verification. Changing the evidence policy later requires a declared experimental revision.

One valid raw response is recorded and validated; no tools or semantic repair are used. A valid report is reused for the same candidate. An invalid report remains a failed observation, not a low score or an excuse for a second interpretation request. Transport failure without a valid response is a different state and may be recovered under a bounded, recorded policy for the same logical request.

There are no action/recommendation fields. Instructions and validation reject obvious action guidance in any prose. Deterministic text validation does not prove complete semantic compliance; report that limitation and reserve real behavioral validation for the authorized experimental stage. Do not claim that a regex alone establishes independence.

### 4.5 Recovery and resource state

| Event | Required runtime behavior |
|---|---|
| Renderer result already exists | Validate and collect the same result; do not generate again |
| Render dispatched, outcome uncertain | Retain job identity and reconciliation evidence; do not silently repeat |
| Temporary LLM connection/rate failure | Bounded recorded retries for the same immutable request |
| Retry budget exhausted, connectivity later restored | Explicit recorded reopening of the same logical call with finite additional allowance; no deletion of failure history |
| Valid Critic report exists | Reuse it; no follow-up |
| Semantically invalid Critic response | Retain failure; Planner inspects video itself |
| Program-enforced turn/generation limit | Pause without successful delivery; retain current candidate and allow explicit resource continuation |
| Context capacity reached | Preserve exact evidence and provide a practical continuation path rather than replaying the same oversized context |
| Planner sees no promising next attempt | Record blocked/provisional outcome and explanation; no false delivery claim |
| Planner judges a result suitable | Finish that candidate with explanation; no required perfect score |

These are system states, not extra reasoning forms for Planner. Recovery primitives belong to the shared execution layer and should not require importing the removed RSI learning workflow.

### 4.6 Configuration, freeze and independent evaluation

One usable configuration path must drive both CLI and server model construction. Planner and online Critic resolve to gpt-6.1-sol/high without depending on accidental environment defaults. Invalid legacy/creative combinations fail before a live task starts. Keep legacy entry behavior explicitly available.

An experimental cohort must reference the same frozen Critic protocol, model settings and evidence policy. Existing per-task hashes and service snapshots can supply this; a future experiment launcher must bind its whole cohort to one shared identity. A new code/manual/profile revision cannot silently join an old cohort. This is version binding, not an RSI cycle or approval workflow.

The separate final adapter fixes `glm5.3flash`, reads Paratera credentials outside the repository, does not pass GPT reasoning parameters, does not substitute models, and records its own configuration/requests/results. Keep unknowns out of numeric means and retain valid/planned counts. Live endpoint, model identifier and image/payload limits remain unverified until experiments resume.

### 4.7 Human-readable results

The report should use the new loop's actual fields: request, videos/ancestry, exact prompts, actual knowledge reads, observations, optional notes, online score reports, provisional/final selection, tradeoffs and failures. It should not look for a legacy `submit` proposal or display empty legacy fields as if no work occurred. Show clear links to complete records. Label mocked demonstrations and imported historical videos explicitly.

## 5. File-level development sequence

The audit records the baseline. The user has now authorized P1-P7 implementation, with simulated walkthroughs and verification runs deferred. Track implemented behavior separately from executed validation.

| Package | Files/components | Work and dependencies | Observable completion |
|---|---|---|---|
| P0: authoritative scope and backup | This specification, approved plan, audit; Git branches | Record the approved route and baseline before further edits; preserve existing remote pre-refactor backup | Scope/status match actual implementation and authorization; no secret or runtime artifact uploaded |
| P1: workflow and role configuration | creative.py, runner.py, run_planner_harness.py, server_runtime/service.py, creative-loop config | Keep explicit creative entry and exclusions; normalize model settings once for CLI/server; reuse existing execution | Actual production factories resolve high for both roles in offline construction tests; invalid mixtures fail early |
| P2: knowledge and context | creative_knowledge.py, knowledge manifest/navigation, context.py, runner.py | Preserve four classes; implement bounded read/history presentation; expose read-only main-score definitions; retain exact archives | Ordinary multi-page reading and repeated candidates remain usable within budget; all original material can be reopened; no excluded assets enter |
| P3: candidate execution and recovery | execution.py, model_call.py, delivery.py, worker/service recovery | Preserve signed requests and candidate ancestry; distinguish response/transport states; repair budget/context continuation | Fourth generation and early-candidate delivery work; interrupted known/uncertain renders are not duplicated; restored connectivity can resume the same allowed call |
| P4: Critic boundary and evidence contract | one_shot.py, CREATIVE_RUBRIC.md, creative.py, adapter/collection | Preserve one-shot interface and main scale; constrain focus/checks; validate requested comparisons and evidence attribution; reject obvious guidance | One valid report or one explicit failure; no follow-up; no silent omitted comparison or source-only evidence for a candidate claim |
| P5: separate final interface | evaluation/creative.py, run_creative_judge.py | Retain fixed glm5.3flash/Paratera adapter and blind inputs; verify transport/config separation offline | Anonymous exported request has no Planner/online/group data; missing scores stay missing; no live request |
| P6: reports and walkthrough | planner_harness/report.py, demo_creative_loop.py, implementation docs | Project new state directly; export actual context and feedback examples | Completed creative run has no misleading legacy-submit placeholders; readers can trace reads, prompts, evidence and selected ancestry |
| P7: acceptance and synchronization | Focused tests, saved artifacts, plan/audit, Git | Check integration boundaries using actual factories/queues with mocked external calls; update truthful status and push after authorized code completion | Requirement-to-evidence mapping and residual limits; no claim of real-model improvement |

Prefer adapting these existing components over adding a new orchestrator, agent or policy engine. Preserve legacy behavior through explicit dispatch. Extract generic recovery only where reuse removes actual RSI coupling; do not mechanically rename every old module or delete historical assets.

## 6. Verification by design property

Use actual code paths with deterministic mock model outputs and existing/synthetic media. Mock only external inference/rendering boundaries; do not bypass the factory/configuration logic being tested.

| Property | Required offline evidence |
|---|---|
| Knowledge scope | Every entrance/access route is scoped; excluded identifiers/path references fail; retained entries/guides/images remain readable and unchanged |
| Creative autonomy | Multiple legal operation orders work without old forms, automatic review or fixed creative assignments |
| Continuing work | Several substantial reads, candidate observations and reports remain usable; archives reopen accurately; explicit context pause can continue |
| Candidate independence | Generate from an older candidate, compare another candidate and select an earlier delivery; inspect actual ancestry/prompts |
| One-shot review | One successful report is reused; invalid raw output produces no semantic retry; permitted network retries retain the same request |
| Fixed main metrics | Supplemental checks cannot change score keys/anchors; unknown/null and evidence/video identity validations work |
| Independent perspective | Expected scores/preferences do not pass through focus as ordinary questions; obvious advice is rejected; Planner can access the scoring definitions and inspect evidence itself |
| Runtime recovery | Resume known and uncertain renders, a temporary provider failure, exhausted retries, program-imposed generation pause and context pause separately |
| Factory parity | CLI and service use the actual role-resolution path with provider execution mocked; both resolve the approved settings |
| Final measurement isolation | Exported final request/result has the exact model and no online/Planner/arm data; it cannot enter Planner tools/context |
| Human trace | New-loop report reflects actual reads, prompts, candidates, reviews and outcome; no legacy proposal assumptions |

Positive unit tests alone are insufficient. Include the exact counterexamples found by the audit and a scripted end-to-end task through the server queue/worker path. Keep tests focused on externally meaningful behavior rather than mirroring implementation details.

## 7. Future experiment boundary

After explicit resumption only: use the existing two-RTX-5090 container and seven fewshot long requests. Preserve Bernini's approved 40-step v2v_apg, maximum size 848, native time axis and matched initial settings/seeds.

- Direct versus Loop-first measures the joint contribution of knowledge and Planner/harness. It does not isolate knowledge alone.
- Loop-final versus Loop-first measures the additional effect of iteration and selection, with actual generation costs and incomplete outcomes reported.
- Independent glm5.3flash scoring uses anonymous inputs, the shared main rubric and explicit unknowns; online reports are not substituted for it.
- Freeze the cohort configuration and connect the new entry explicitly. Existing RSI fewshot launchers must not be reused as if they selected the creative loop.

Live model capability checks, GPU execution, cohort automation, real scores and performance conclusions remain deferred. No current software result establishes stable positive improvement.

## 8. Audit status convention

The [companion design audit](creative-loop-design-audit-20261101.md) maps each design property to code, evidence and remaining work using: implemented; partially implemented; missing; intentionally retained legacy; explicitly deferred; or unverified behavioral effect. A historical passing test or an available function is evidence of a specific property, not completion of an entire subsystem.

Implementation baseline: commit `4e046d4af5bb85257d3c037e1c6217eeaad31b39`, branch `codex/creative-loop-v1`. Existing backup is `433c5dfd9dab6dc9949c5d5111480cf34486dce0` on `codex/loop-pre-refactor-20261101`. The preceding code commit is `0296e23b88ce96ac39b9043db24e35564ea12fc6`.

## 9. Authorized repair progress

- P0: plan and baseline audit committed as `cb30fe7` before code repair; prior pre-refactor backup retained.
- P1: implemented shared role resolution, explicit constructor settings, creative service configuration and optional immutable experiment binding. CLI and service use the same gpt-6.1-sol/high settings; behavior awaits the deferred tests.
- P2: implemented bounded source pages with exact line/character continuation, compact prior operation views, paginated archive catalogs and capacity recovery. Added a shared, readable score-definition source used by the frozen rubric. Original style/semantic/static iteration sources were not rewritten.
- P3: implemented consistent creative delivered/blocked/paused meanings in both delivery and bounded modes; automatic budget continuation, finite transport reopening, uncertain-tool retention and same-job receipt reconciliation. Generic recovery has no RSI import and invokes no model or renderer.
- P4: implemented neutral-focus checks, explicit comparison coverage, candidate/source/comparison evidence attribution for supplemental checks, and additional rejection of obvious action guidance. The single-response policy and five fixed axes remain intact. Semantic compliance still needs behavioral validation.
- P5: retained the fixed glm5.3flash/Paratera adapter and anonymous final inputs; added optional shared profile binding to the separate judge entry. No scoring call was made.
- P6: implemented a creative-specific report based on actual reads, prompts, observations, candidate ancestry, online reports, selection and recovery records. Existing demo artifacts have not been regenerated and describe the older revision.
- P7: added focused audit-counterexample tests and a scripted service/queue integration case that uses the real model factory while mocking external execution. These tests, simulated integration and demo regeneration have **not been run**, as explicitly requested. Static Python/JSON parsing and Git whitespace/secret hygiene are publication checks only. The code repair was pushed to GitHub and its remote SHA verified as recorded below.

Earlier 113/14-test results describe the baseline only; they do not validate this repair revision. All P1-P6 statuses above mean code implementation and source inspection, not a demonstrated runtime outcome. The next authorized validation pass should run the focused regressions, then the relevant legacy suite and regenerate the walkthrough. Live experiments remain separately deferred.

### Repair-to-audit mapping

| Baseline finding | Implemented change | Deferred evidence |
|---|---|---|
| F01: legal reads exhausted context | Bounded fresh pages, compact history, exact archive reopening, explicit capacity adjustment | Multi-read context and pagination tests |
| F02: biased input and advice leakage | Neutral focus validation; strengthened no-guidance output checks | Contract tests and later real-model compliance |
| F03: missing comparison and wrong-video citations | Requested comparison must have a finding/unknown; supplemental evidence identity checks | Invalid-report regression cases |
| F04: scoring definitions inaccessible | Shared SCORE_DEFINITIONS.md exposed through the creative manifest and incorporated verbatim into Critic rubric | Scoped read and profile checks |
| F05: false complete in bounded mode | Creative completion uses delivery semantics regardless of explicit budget mode | Outcome and budget-continuation cases |
| F06: retry/reconciliation gaps | Recorded finite call reopening; unresolved jobs block replacement; receipt reconciliation; service queue recovery | Exhaustion, uncertain render, resource and queue recovery cases |
| F07: actual factory used wrong role settings | Shared configuration resolution, explicit constructor inputs, service example, shared profile binding | Actual factory/queue test; deployment remains deferred |
| F08: legacy report placeholders | Creative report projects actual state and links raw artifacts | Report assertion and regenerated walkthrough |
| F09: incomplete test boundaries | Added production-factory service trace and exact audit counterexamples | Execution explicitly deferred by user |

No new task criteria, intent/check forms, prediction ledger, experience card, Wiki, learning loop or automatic review was introduced. Operators' resource/recovery records are persistence controls, not additional Planner reasoning requirements.

Publication inspection: 22 Python files and 2 JSON files parsed successfully without importing application code; the 32-file repair set passed the credential-pattern scan and Git whitespace check (preserving existing CRLF files). New prose is English. No test, simulation or model invocation was executed. The user-owned staged knowledge demos, run lock and historical screening reports are outside this commit.

GitHub synchronization: implementation commit `6af64be677af876db78e0fbd23cdef4ea390eac0` was pushed to `codex/creative-loop-v1`; `git ls-remote` confirmed the identical SHA. The plan/audit commit `cb30fe7` is included in that branch. This documentation update records the verified code revision. Main and the pre-refactor backup branch were not changed. Implementation and synchronization are complete for this pass; behavioral verification and experiments remain deferred.
