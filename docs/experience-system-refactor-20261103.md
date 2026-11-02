# Experience system refactor

Status: implemented and offline verified. Authorized on 2026-11-03 following the read-only architecture review.

## Purpose and scope

Make experience useful to the next Planner without giving a task contributor authority to rewrite existing guidance. Keep the reviewed conditional judgments, style library and thin creative loop. Separate contribution, library curation and system development. Do not add an automatic RSI cycle, scheduler, experiments or model calls.

The approved scope includes the three maintenance Skills, their shared writing/interface references, experience navigation, private contribution storage and discovery, explicit curation, and saved-video observation for maintenance. Preserve existing runs, frozen snapshots and concurrent experiment work.

## Implementation

1. Record the starting hashes and back up touched files. Inspect existing callers and campaign boundaries before changing interfaces.
2. Replace post-task mutation authority with an append-only contribution layer. Support new judgments, recommendations, clarifications, comments and proposed exact revisions. Bind each contribution to its source case and referenced entry version. Private ingestion may be automatic where the campaign already authorizes it; it does not revise canonical entries or manuals.
3. Expose contributions and cases through the existing browse/search/read interface. Show related contributions beside the original entry, including on its first page. Preserve conditions, practical advice, provenance and dissent. Keep no-experience snapshots isolated.
4. Provide an explicit curation operation for an authorized maintainer to accept, merge, supersede or decline contributions and revise entry text and discovery metadata together. Task contributions cannot invoke it. Skills, manuals and runtime policy remain development changes, outside the task contribution and library curation APIs.
5. Rewrite the three maintenance Skills around analysis, use review and curation. Share writing and authority contracts through references. Remove duplicated campaign policies and obsolete review instructions. Keep clear conditional advice, goal interpretation, renderer-specific explanations and continuation-question evidence.
6. Add bounded observation of hash-verified saved source/candidate videos to maintenance. Reuse existing observation code; attach actual inspected evidence to the contribution. Do not render or judge new outputs.
7. Verify contribution authority, linked discovery, immutable historical evidence, explicit curation, no-experience isolation, video observation and existing maintenance integration using offline software tests. Save a readable example and a scoped change report.

## Completion conditions

- A task can create a useful searchable judgment/comment/proposed correction, but cannot overwrite an existing entry, a Skill or a manual.
- Each new contribution opens its source case; an entry exposes related support, disagreement and clarification without burying it in the last page.
- Curation is a separate explicit call with source-version checks and recorded decisions. No ingestion implicitly approves a claim or changes a recommendation.
- Map and search derive contribution metadata from the frozen catalog. Canonical entry summaries are revised with their text during explicit curation.
- Maintenance can inspect a relevant saved video interval beyond frames seen by the original Planner.
- Three concise Skills share one interface/writing contract. Stable Skills contain no dataset counts, arm ordering or obsolete experimental policy.
- Frozen runs and online experiments are not modified or started by this task.

## Completed implementation

- Captured the before-state of the affected files under `out/experience_system_refactor/20261103/before/`.
- Added append-only contributions and immutable linked cases. Existing entry bodies and manuals are outside the task API's mutation authority.
- Added first-page related contributions, catalog/search discovery, source cases, frozen-snapshot and usage-index support.
- Added explicit version-bound private curation with retained history, dispositions, pointer recovery and a standalone command. Contribution draining no longer launches a curation model automatically.
- Derived current map and renderer recommendations from one catalog. Preserved the earlier detailed renderer profile as an indexed historical source. All 15 entry bodies and 55 original evidence files retained their original hashes.
- Rewrote the three maintenance Skills and shared references; removed conflicting campaign policies and retained substantive goal/scene/renderer reasoning.
- Added bounded saved-video observation, including source-case videos opened during maintenance. Evidence records distinguish original online exposure from post-task observation.
- Passed 81 related offline software tests, three Skill format checks and authored-link validation. No model/provider/rendering experiment was run.

See `out/experience_system_refactor/20261103/implementation-review.md`, `verification.json`, `discovery-example.json` and `scoped-changes.patch` for the implemented comparison and exact evidence. Changes remain local in the concurrently edited checkout; historical runtimes and experiment snapshots were not migrated.
