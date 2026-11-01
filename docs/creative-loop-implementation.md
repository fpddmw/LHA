# Creative loop implementation and offline verification

Approved scope: [implementation plan](creative-loop-refactor-and-fewshot-plan.md).
Live experiments, model calls and deployment are deferred. Independent evaluation
is configured for `glm5.3flash` at Paratera; its live API capabilities are unverified.

Status correction, 2026-11-01: this is the implementation checkpoint before the
[architecture audit](creative-loop-design-audit-20261101.md). Its tests and exported
artifacts remain valid within their scope, but completion is partial: the audit
reproduced gaps in context capacity, Critic input/output boundaries, failure recovery,
bounded outcome semantics, server profile construction and report projection. See the
[detailed development specification](creative-loop-development-plan.md) for the
confirmed target and bounded follow-up work. No repairs or live experiments were
performed in the documentation/audit pass.

## What changed

`creative_loop_v1` is an explicit Planner workflow. The existing default is `legacy`,
so historical runs keep their behavior. New creative tasks use the continuous Planner,
video observation, durable worker jobs and all-candidate access. The CLI and server
task submission both propagate the workflow. Resume retains the recorded workflow,
model, knowledge snapshot, system prompt and frozen Critic profile.

The new knowledge allowlist preserves four classes: operating manuals, semantic
understanding, visual style/design, and static generation/iteration knowledge. It
contains the 111 complete entries, five domain references, seven guides, one historical
model-experience record, four static iteration topics and their map, original sources
and 98 reference images. The class labels are entrances, not compulsory reasoning slots.
Original entry, guide and static-topic bytes remain unchanged. New map/manual editions
avoid the legacy Wiki/learning instructions. The mutable experience catalog and its
publication journals are not read by this profile. Excluded references are inaccessible
through browse, search, read and reference-image tools.

The Planner chooses input, prompt, reading, observation, optional review and delivery.
No requirements/intent forms or learning ledger are used. The newest candidate's
overview is attached after collection; there is no automatic Critic. Delivery choice,
generation input and comparison target are separate. A null count limit allows further
generations, including a fourth. An explicit resource limit pauses delivery work;
an unsuitable result with no promising next attempt remains blocked, with its candidate
retained. A successful Critic report is not required for a Planner delivery judgment.

## What the Planner sees

The actual system text is assembled from
[CREATIVE_LOOP.md](../src/planner_harness/CREATIVE_LOOP.md) and the
[reading manual](../knowledge/creative-loop/READING.md). For example:

> Your task persists across tool results. You can revise your interpretation and visual
> direction as evidence develops. Optional notes and workspace nodes can retain useful
> questions, alternatives and findings. There is no required thought sequence, form,
> reading quota, prescribed aesthetic or mandatory narrative invention.

The task context contains the original request, source overview, latest observation,
optional workspace/notes, candidate directory, intended delivery, actual reading receipts,
recent operations and historical retrieval links. The latest Critic report is present;
older reports retain dimensional scores, evidence references and a full-record link.
The Critic's internal role instructions are not copied into the Planner context.

The manual also states:

> Its findings are evidence to understand, not decisions to obey. Inspect relevant video
> intervals yourself when a score or claim affects continued generation or selection.

## One-shot Critic

[CREATIVE_RUBRIC.md](../src/critic_harness/CREATIVE_RUBRIC.md) defines every 0-4 anchor
for instruction_adherence, content_preservation, temporal_consistency, visual_integrity
and aesthetic_coherence, including scope and boundary examples. The same manual,
schema version, evidence policy, implementation hashes and gpt-6.1-sol/high profile
produce the same profile hash across tasks. Changing these requires a new frozen runtime.

Each requested review receives source, candidate and at most one optional comparison.
Evidence is prepared deterministically: eight overview samples and three windows of
six consecutive frames per video, deduplicating coincident windows for short clips.
This is sampled evidence, not exhaustive temporal verification. Main scored findings
need real evidence IDs; preservation needs source/candidate citations, and temporal
scores need consecutive candidate evidence. Unknown remains null.

Focus and custom checks are separate from the main rubric. Generation prompts, Planner
predictions and preferred winner are excluded. Output consists of dimensional scores,
reasons, evidence, descriptive comparisons, supplemental checks and limitations. There
are no recommendation/action fields. Instructions prohibit advice in every prose field;
validation rejects extra fields and common directive formulations. A deterministic text
check cannot guarantee detection of every semantically disguised recommendation; actual
model compliance remains a live validation item, not a demonstrated result.

One accepted response is persisted, parsed and validated without model-driven repair.
Repeated requests for a reviewed candidate reuse its report. Invalid reports remain
recorded failures. Transport retries are bounded and logged separately; the caller's
model object is not modified. An interrupted LLM attempt may have incurred provider
cost and is recorded as uncertain before consuming the next retry slot. Rendering uses
the existing immutable signed job/receipt path instead of this LLM retry mechanism.

## Independent final judge

`evaluation.creative.ParateraJudge` fixes the model to `glm5.3flash`, reads credentials
from `LHA_PARATERA_API_KEY`, and requires a verified HTTPS API base URL on
`llmapi.paratera.com` in `LHA_PARATERA_BASE_URL`. No credential is saved in artifacts.
The request uses model/messages/max_tokens without GPT-specific reasoning parameters.
Endpoint paths, model identifier acceptance and payload limits have not been tested live.
There is no fallback model.

`scripts/run_creative_judge.py` exports an independent request by default. Its explicit
`--execute` path is for later authorized scoring. Inputs contain the original task,
source and anonymous candidate only: no arm, iteration, Planner notes, online feedback,
supplemental checks or selection rationale. Final scores cannot enter the creative
Planner through an evaluate tool. Pair summaries retain per-dimension valid/missing
counts, deltas and wins/ties/losses, without treating unknown as zero or inventing a total.

## Offline walkthrough and checks

The reproducible command is `python scripts/demo_creative_loop.py --output <fresh-directory>`.
It uses an existing fewshot_004 source and historical candidate, scripted Planner/Critic
responses and the actual runtime's tools and context assembly. It performs zero live
model calls, renders or independent scores. Its score values and selection are software
fixtures, not findings about the video. It also exports the anonymous final-judge request.

The latest walkthrough is in `out/creative_loop_refactor/demo-final/` and test records
are in `out/creative_loop_refactor/`. Its README
links the exact system prompt, initial context, material reads, post-generation context,
post-review context, Critic request/report and independent request. Existing historical
media is not republished to GitHub.

The final suite passed 113 unique tests, with no failures, errors or skips, using the
repository's declared media dependencies. Focused regression checks cover the creative workflow, legacy Planner and worker,
lightweight context, delivery, legacy Critic, server queue/service and existing RSI tests.
They use synthetic/saved media and scripted models only. The approved plan's progress
section records actual counts and synchronization status. An initial broader discovery
also found a missing pydantic dependency in the unrelated old mechanical video Planner;
that module is outside this refactor's focused suite and was not modified.

## Later use

After experiments are resumed, the Planner CLI accepts `--workflow creative_loop_v1
--mode loop`; its default model profile becomes gpt-6.1-sol/high. Supply an explicit
renderer execution configuration. A server task can likewise declare
`"workflow": "creative_loop_v1"`. `configs/creative-loop-v1.json` records the agreed role
profiles and deferred experiment state; it is a reference manifest, not a batch launcher.
No deployment, GPU queue, heartbeat or real judge was started by this implementation.
