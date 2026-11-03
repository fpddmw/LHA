# Creative loop integration repair

Status: implementation, offline verification and GitHub delivery complete. Experiments remain paused.

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
- [x] Run focused offline checks, then the current regression suite if focused checks pass. Check tracked diff and knowledge-content hashes.
- [x] Commit scoped changes, push the existing branch, and verify the remote commit.

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


### Final verification

- Focused checks: 46 tests passed, including 10 new cross-entry cases. The existing private-maintenance integration test executes the opening action returned by search and retains online experience isolation.
- Full suite: 449 tests executed; 448 passed initially. The existing resource timeout test exceeded its five-second wall assertion in the parallel run (13.42 seconds). The complete 27-test module passed unchanged in isolation. Neither the timeout assertion nor the runtime was relaxed.
- During the full suite, another session committed `7bc8e07` (relay TLS setup retry), changing `src/vlm/chatgpt_relay.py` and `scripts/test_chatgpt_subscription.py`. That independent commit is preserved. Re-ran the affected subscription, interrupted-recovery, API and cross-entry modules: 50 tests passed, including the two new relay tests. Source/configuration hashes remained stable during these final checks. There are now 451 distinct current tests with passing results across the recorded validation passes; this is not represented as a single clean full-suite run.
- All four CLI help entries loaded. Single/dual-model plans still report 1742/3484 maximum generation attempts and 536/1072 main trajectories.
- Verified 153 tracked experience, experiment-configuration and evaluation files against the baseline: unchanged. Eleven current operator documentation pages have no missing local file links. Scoped Python syntax, diff whitespace and added-credential-pattern checks passed.
- Evidence: `out/chain_integration_repair_20261103/verification.json`, `current/summary.json`, `timing-rerun/summary.json`, `relay-integration/summary.json`, `protected-content-and-links.json`, `cli-contracts.json` and `scoped-files.json`.
- No live model call, video generation, independent scoring, deployment migration or experiment launch occurred.

### GitHub delivery

Implementation commit: `298b06affb6e0ef6210c85c4c0ce7debaed5377b`, containing the 22 scoped implementation/documentation/test files. Pushed to `origin/codex/experience-curation-v1`; `git ls-remote` returned that exact commit. The concurrent relay commit remains its parent, separate from this repair's changes. This final documentation update records the completed verification and handoff.
