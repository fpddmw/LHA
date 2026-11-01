# Lightweight harness, first implementation round

Implemented on 2026-10-30 under the user's narrowed authorization. No external model calls, renderer runs, scoring jobs, deployment changes, or experience publication were performed. Local software checks use scripted responses and synthetic media. The saved-video preview constructs inputs without running a Planner.

## What changed

| Support | Implementation | Model-facing behavior |
|---|---|---|
| Comparative evidence access | Extend the existing `observe` operation to accept one video ID or up to four, and to reopen saved observations after checking their image hashes. | The model can view source and selected candidates together, or return to a prior crop. IDs and timestamps remain explicit. Sampled frames do not establish continuous motion alignment. |
| Context continuity with less repetition | New runs record `context_version: 2`. Compact video metadata points to `video`; the latest review stays complete. Earlier online reviews quote their existing summary, unresolved points, unknown findings and comparison unknowns, with `history` links. | Useful facts remain accessible without automatically expanding every old review and execution receipt. Full records are preserved. No ranking or replacement judgment is generated. |
| Optional task notes | A tool call may carry a top-level `note` string. Existing `note(text, append:false)` replaces or clears notes. | There is no required note format, update schedule, reflection phase, or additional call before generation. |
| Knowledge orientation | Freeze concise question/scope descriptions from `knowledge/entrances.json`; show three optional starting points in the default context. Full browse/search/read remain available. | The model can see why a topic might help and the scope of empirical material, then choose its own reading. Existing availability filters remain respected. |

The original requirement and source identity remain in state. Context supplies source metadata and the source overview; the complete source receipt is accessible through `video`. Observation groups remain attached until a new observation or generated overview replaces them. Earlier groups can be reopened by ID. Full records, signed jobs, prompts, feedback, and historical events are not rewritten by context presentation.

## The model's actual interface

The existing operation envelope is retained. For example:

```json
{"action":"observe","arguments":{"video":["source","v1","v2"],"start":1,"end":2,"count":4}}
```

The result contains sampled images from those videos at their own recorded times. There is no automatic verdict or next action.

```json
{"action":"history","arguments":{"feedback":"event-0005-critique"}}
```

This opens the complete saved feedback, with numbered pages and explicit continuation when needed. The model can also reopen an exact event, or use `video` for an input's full prompt and provenance.

The manual now includes this wording:

> You may attach an optional top-level `note` string to any call to retain a useful finding without a separate operation. Notes have no required structure or update schedule.

It retains the existing freedom to generate directly, select any available input, leave notes empty, read selectively, and stop early. It adds no compulsory reasoning questions, route approval, fixed aesthetic mapping, or learning form.

Default knowledge orientation offers meaning, design expression, and generation/iteration experience. Browsing the input-choice topic returns, among its existing metadata:

```json
{
  "id": "choose-editing-input",
  "use_for": "Consider an original input, an earlier candidate, or continued editing for the current change.",
  "scope": "Initial common-sense route preferences; no controlled route advantage has been established."
}
```

This is an entrance description. The existing advice and underlying source material remain unchanged. The Bernini probe entrance explicitly identifies Bernini-R, four source clips, ten conditions, seed 42 and 40 steps, with transfer to Ditto and multi-round input choice unverified.

## Inspect the actual constructed inputs

The [offline preview](../out/harness_lightweight/20261030/preview-024/review.html) uses the historical Bernini 024 full-knowledge task immediately after v2's feedback. It shows:

- [Exact new system instructions](../out/harness_lightweight/20261030/preview-024/model-system.txt).
- [Constructed context at that point](../out/harness_lightweight/20261030/preview-024/model-context.json).
- [Actual comparative observation request and result](../out/harness_lightweight/20261030/preview-024/comparison-operation.json), with 12 sampled frames from source/v1/v2.
- [Context and image identities after that observation](../out/harness_lightweight/20261030/preview-024/comparison-context.json).
- [A reopened earlier feedback page](../out/harness_lightweight/20261030/preview-024/reopened-feedback-page.json).
- [Provenance and explicit zero-call boundary](../out/harness_lightweight/20261030/preview-024/provenance.json).

The constructed same-state context decreases from 101,051 to 79,530 characters, approximately 21%. This measures presentation size only; it is not a latency, video-quality, or reasoning-performance result. Historical notes remain empty. The comparison operation was requested by the author for the software preview, not chosen by a new Planner run. The original archived state remains unchanged.

## Compatibility and validation

Runs without `context_version: 2` use the previous context construction. Resume continues to load the saved operating instructions and frozen knowledge. Old snapshots do not import newly added entrance descriptions. Pending calls retain exact saved inputs. Current knowledge snapshots include the new entrance descriptions in their hashed data.

Focused checks cover multi-video identities/times, observation reopening and integrity, a new generated overview replacing an old focus, full paginated feedback retrieval, retained unknowns, optional notes, full provenance access, old-context continuation, frozen entrances, and knowledge availability filtering. Existing Planner/worker/Critic checks exercise execution and resume compatibility with scripted models. All 48 distinct checks passed, including nine new focused checks. The broad test loader repeated imported fixture tests; repeats are excluded from this count. See the [verification receipt](../out/harness_lightweight/20261030/verification.json) and [software-check records](../out/harness_lightweight/20261030/).

All 122 protected knowledge Markdown pages (111 complete entries, five domain references, five experience/map pages and one model-experience page) match the pre-change hashes. Substantive experience and judgment guidance is the next priority. Critic judgment, Claude integration, and global-RSI validation/adoption mechanisms remain subsequent work.

## Code scope

- `src/planner_harness/runner.py`: versioned context dispatch, optional inline notes, comparative/reopened observations, feedback history access.
- `src/planner_harness/context.py`: deterministic presentation and image-group selection; no model inference or ranking.
- `src/planner_harness/knowledge.py`: frozen entrance descriptions and compact orientation.
- `src/planner_harness/OPERATIONS.md`: explanations of the extended existing operations.
- `knowledge/entrances.json`: access metadata for existing pages.
- `scripts/test_lightweight_harness.py`: offline regression checks.

The plan adjustment is recorded in [the approved direction](agent-loop-rsi-direction.md) and [the narrowed refactoring plan](agent-loop-defect-review-and-refactor-plan.md#latest-scope-adjustment-a-thin-first-round).
