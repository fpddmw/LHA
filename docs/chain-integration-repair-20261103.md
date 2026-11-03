# Creative loop integration repair

Status: approved for implementation; experiments remain paused.

Baseline: `939583ac60d68cbbbc30ccb059bec143d1b06efc` on `codex/experience-curation-v1`.

## Scope and audit evidence

The read-only audit found four cross-entry inconsistencies. The existing 46 focused tests passed, while isolated probes reproduced the launch, navigation and status problems below. Preserve the reviewed experience prose and judgments, current four-generation experiment, review modes, private-library ownership, and evaluation protocol. Do not add an RSI mechanism, scheduler, model call, generation or live evaluation.

1. **Completion instructions:** the full manual describes fixed-budget completion, but the none manual still permits early delivery. Both arms already share the runtime guard. Align their operating instructions without exposing experience to none.
2. **Single-task launch:** the CLI instantiates OpenRouter despite a configured subscription factory, defaults new tasks to legacy, and rejects a CLI generation-count override because the profile retains a second hard limit. Resolve roles through the existing configuration/factory machinery, make the current entry explicit, preserve historical resume behavior, and normalize new-task overrides consistently. Correct obsolete help and carry the supported profile settings through the launch.
3. **Maintenance navigation:** search advertises the Planner's `read {targets}` shape, while maintenance accepts `read {source,id}`. Adapt the returned opening action to the receiving interface, retaining the same search, permissions and content.
4. **Progress reporting:** campaign status only reads a final checkpoint, missing active scheduler claims; serial checkpoints use `settled` while readers expect `positions`. Read the existing live status and durable settlements without adding a new state store or scheduler.

Current documentation also disagrees on early delivery, continuation protocol, self-review library ownership, task deadlines, and the active maintenance documentation. Preserve historical records while making the current entry points and descriptions consistent.

## Implementation sequence

- [x] Save the findings and this authorized plan before editing implementation.
- [x] Align full/none completion instructions.
- [x] Repair single-task role/default/override/resume configuration using existing machinery.
- [x] Connect maintenance search results to the maintenance read interface.
- [x] Connect campaign status to existing live and settled records.
- [x] Update current documentation and command descriptions; label dated verification facts as historical rather than current totals.
- [x] Add cross-entry regression tests covering these reproduced failures, including the actual CLI with scripted clients, maintenance search-to-read, and active/finished status.
- [ ] Run focused offline checks, then the current regression suite if focused checks pass. Check tracked diff and knowledge-content hashes.
- [ ] Commit scoped changes, push the existing branch, and verify the remote commit.

## Completion criteria

- Both knowledge arms receive the same fixed-budget completion contract.
- A supplied model factory and its options select the actual client; explicit model/effort overrides and historical resumes retain truthful configuration.
- A generation override has one effective value across the resource and continuation guards, without changing the campaign defaults.
- Maintenance can execute the opening instruction returned by search directly.
- Status distinguishes active work, settled outcomes and unresolved work using existing receipts; it does not report an active batch as unstarted.
- Current documentation points to current interfaces and names the separate critic/self-review libraries correctly.
- No experience entry, scoring standard, experiment design, historical runtime or result is altered.

## Verification and synchronization

Focused verification: 46 offline tests passed, including 10 new cross-entry cases. The existing maintenance integration test now executes the action returned by search rather than constructing its own read request. Full-suite and synchronization results follow after completion. All validation in this repair is offline software validation, not a new claim about model behavior or video quality.
