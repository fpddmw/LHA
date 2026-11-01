# Seven-fewshot three-arm experiment preparation

Date: 2026-11-01. Status: code and local/provider preflight complete; awaiting the correct opened host configuration. The user authorized this plan, the complete preflight repairs, activation of the reviewed experience/manual package, software checks and Git publication. The user subsequently supplied a new host and authorized startup after checks. The supplied endpoint currently exposes one RTX 4090 D (24GB), so hardware selection is being confirmed before generation.

## Experimental contract

Use the seven exact long requests and source hashes in benchmark_data/fewshot_index.json. Each topic completes Direct, full-experience creative Loop, no-experience creative Loop, independent final judging and verified archival before the next topic is admitted. Direct submits the original request once to the same Bernini renderer. Loop arms retain the same Planner, tools, style library, semantic understanding, Critic protocol and rendering settings. The no-experience arm excludes the experience-reading guidance, curated entries, renderer profiles, evidence and historical experiment routes. Maintenance Skills never run inside either arm.

Both Loop arms use gpt-6.1-sol/high for Planner and optional one-shot Critic. Critic has the same experiment-wide five-dimensional 0–4 rubric and gives no suggestions. Independent judging uses both glm5.3flash at Paratera (API ID GLM-5.3-Flash) and sonnet-5.5high at api.tu-zi.com (API ID claude-sonnet-5-5, native adaptive thinking with output_config.effort=high), following the user's subsequent change during this preparation. Each receives anonymous source/candidate inputs without online feedback or the other judge's report. Preserve separate per-judge comparisons and explicit disagreement; do not average the judges or substitute one for the other. GLM reserves 16384 total output tokens for thinking plus the answer; Sonnet reserves 7000. These are response capacities, not task generation limits. Both judges must finish before topic archival. Score all distinct generated candidates; report Direct versus each Loop-first, each Loop-final versus its own first, and full versus no-experience first/final. Reuse a final score only for identical request/source/output/protocol/model identity. Preserve unknowns, unsuccessful tasks, actual cost and knowledge use.

Delivery determines completion. There is no three-generation or hidden turn ceiling. A technical interruption, resource pause or unsuitable result blocks this topic and remains resumable; it is never converted to delivery or silently skipped. The seven tasks are development regressions because they contributed to the experience content; findings describe this cohort.

## Bounded implementation

1. Activate the reviewed fourteen-entry package, renderer profiles and five manuals. Rebase links, retain source hashes/provenance, convert the draft catalog into the approved runtime schema and record this explicit authorization. Keep original staged/history artifacts unchanged.
2. Add full/none experience access to the creative knowledge scope and freeze it in each run. Navigation, search, read, references and context must agree. Preserve common operating/semantic/style guidance. Define exact excluded historical routes and shared design material; do not reuse the legacy no-knowledge or RSI paths.
3. Extend the experiment identity with common frozen settings and arm-specific knowledge scope. Use an explicit deterministic per-generation seed sequence shared by the arms, without requiring Planner forms. Retain job identity across recovery and actual seeds in receipts.
4. Add a small topic coordinator around existing service/queue/renderer primitives. Complete one topic's three arms, final judging and hash-verified archive before admitting the next. Permit separate single-GPU worker slots within the current topic; do not expand the scheduler or use the obsolete RSI fewshot launcher.
5. Bind Direct to the same renderer/profile/time-axis rules as the Loops. Persist exact prompts, input ancestry, observations, reads, Critic outcomes, selected/first outputs and costs. Add anonymous judge deduplication and topic/batch comparison output. Keep final scores outside Planner context.
6. Provide deployment preflight for assets, device mapping, native time axes, prompt limits, model settings and exact Paratera image/JSON capability. A local preflight must not start GPUs or queues. Mark unavailable remote hardware checks as awaiting the user's container startup.
7. Run focused offline integration and recovery checks, including a fourth generation, no-experience isolation, identical Critic identity, judge/archival gate failures and restart reuse. Perform only the bounded provider capability checks required for preflight; no video generation or benchmark scoring. Commit and synchronize the reviewed implementation, then notify the user of readiness and remaining host checks.

## Acceptance and progress

| Step | State | Evidence |
|---|---|---|
| Save authorized plan | Complete | This document |
| Activate content | Complete | 14 entries, 54 resources, 5 active manuals; staged originals preserved |
| Experience ablation and frozen identity | Complete | full/none scope, same 111 style entries and 5 domain references, experiment profile binds both |
| Topic coordinator, Direct and seed pairing | Implemented | Independent persistent GPU slots; native frames; successful-generation seeds 42, 43, ...; no generation/turn count cap |
| Independent judging, comparisons and archive gate | Implemented | Two independent judge slots, hash-based reuse, six paired comparisons per judge, disagreement and verified per-topic archive |
| Offline and provider preflight | Passed locally | 104 offline tests; synthetic image/report checks passed for gpt-6.1-sol/high, GLM-5.3-Flash and claude-sonnet-5-5/high |
| Commit and remote synchronization | In progress | Implementation branch codex/experience-curation-v1 |

No automatic RSI, proposal/replay/adoption mechanism, mandatory reasoning form, automatic Critic call, target-score guidance or per-task scoring card is introduced. Experience stays frozen throughout all seven topics; all three arms start independent task state.

## Run boundary and recovery

Use [execution instructions](creative-fewshot-execution.md). The coordinator admits one topic, renders Direct once, and runs both Loop arms on separate GPU slots when two devices are supplied. It then judges every distinct candidate with both models, writes paired comparisons and verifies the entire archive. A failed generation, incomplete delivery, invalid judgment or failed archive blocks the current topic. Completed work survives restart; uncertain rendering needs explicit receipt reconciliation.

The seven tasks contain 106–169 source frames at 30 fps. Keep the native time axis with Bernini's 4n+1 frame requirement, recording 0–3 omitted tail frames. There is no forced five-second resampling. The user-provided long request is identical across arms. Direct does not use Planner, knowledge, prompt enhancement or online Critic. Both Loops use the same successful-generation seed sequence; definite failed renders do not consume the next seed.

## Current limits

A synthetic provider contract check establishes image/request/report compatibility only. It does not establish scoring quality, agreement, editing improvement or remote-host readiness. The first real topic will supply the first current-protocol creative results. The user will open the GPUs; assets, tokenization, device mapping, authentication and network routes are checked there before any render. No instance was started and no new benchmark video was generated during preparation.

## Preflight findings and corrections

- Active knowledge checks found all 14 entries and 54 resources in full scope and zero curated entries/resources in no-experience scope. Both expose the same 111 complete style entries and five domain references. All active links and catalog hashes resolve.
- Offline tests cover a fourth generation in both scopes, early candidate selection, failed-render seed reuse, stable Planner checkpoint recovery, Direct receipt recovery, portable evidence links, dual-judge deduplication and a failed judge holding the topic gate.
- The Paratera model catalog exposes `GLM-5.3-Flash`. A 32-token identity probe returned only reasoning with `finish_reason=length`. The 7000-token visual preflight returned no answer; a configured 16384-token capacity produced a complete report (12011 output tokens, including 10708 reasoning tokens). This is a preflight capacity change; no benchmark result was retried or edited. Earlier timeouts and a native-client invocation failure remain in the local attempt record.
- Sonnet's actual model ID is `claude-sonnet-5-5`; the native Messages API accepts adaptive thinking and explicit high effort. It returned a valid report with 52 images. Model role identities are never substituted automatically.
- The GLM report cited the start/end of supplied dense windows. The original validator accepted only adjacent cited frame IDs. Validation now accepts same-window endpoints only if every intervening frame was actually included; sparse overview and cross-window gaps remain invalid. A regression test verifies a missing interior frame is rejected. The original response and original rejection are retained. No score, rubric prose or evidence was edited. The final capability records revalidate the exact original model-visible instructions and image bytes under this recorded validation repair, without another model call.
- The successful capability records live under `out/creative_fewshot_preparation/20261101/ready`; the release manifest and local preflight are prepared separately after code freeze. The final independent reports, online Critic report and software fixtures remain clearly separate from benchmark outcomes.

Protocol references for provider-specific request controls: [Claude effort](https://platform.claude.com/docs/en/build-with-claude/effort) and [GLM reasoning/output capacity](https://docs.nvidia.com/nim/large-language-models/2.1.4/get-started/advanced/get-started-glm-5.3-flash.html). Actual endpoint compatibility is established by the retained preflight responses.
