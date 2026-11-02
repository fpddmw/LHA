# Experience access, usage records and batch maintenance

This interface extends `creative_loop_v1` only. It adds passive provenance and an offline export. The existing separately budgeted post-task hook collects contributions when the frozen campaign profile authorizes it. It preserves existing Planner operations and candidate/stop semantics.

## Read-only curated catalog

`knowledge/creative-loop/manifest.json` names the dedicated `knowledge/experience/curated/catalog.json`. Its schema is `creative-experience-catalog-v1`, with `revision`, `entries` and `resources`. The 2026-11-01 user authorization activated fourteen reviewed entries and 54 resources. The 2026-11-02 authorized goal-directed revision expands the active source library to fifteen entries and 56 resources, with the new case interpretation and exact decision extract; historical snapshots retain their original membership. The 2026-11-03 refactor retains all fifteen entry bodies, adds the prior renderer profile as an immutable source (57 resources), and derives current map/profile recommendations from catalog metadata. Full scope includes their renderer profiles and evidence; no-experience scope removes these and historical experience routes while retaining shared style, semantic and operating guidance.

Each approved entry requires:

| Field | Meaning |
|---|---|
| id, title, path | Stable identity and an explicit Markdown file inside the curated directory |
| version, sha256 | Content revision and exact UTF-8 file hash |
| review_status, review_reference | `approved` and the review record authorizing this content; a declaration tied to the human workflow, not automated evidence validation |
| summary | Concise explanatory distinction shown on discovery |
| questions, renderers | Lists supporting question/renderer navigation |
| evidence_ids | Explicit resource IDs available in the same scoped catalog |

Resources require the same identity/hash/review fields and a text/image file in the curated directory. Linked prose does not grant access to new files. Duplicate IDs/paths, draft approval status, escaping paths, missing files or changed hashes are rejected. Drafts, old E1, Wiki and maintenance Skills remain excluded. `browse`, `search`, `read`, links and reference images use this same scope.

The catalog and its texts/assets are pinned in the task's knowledge snapshot. Old snapshots without a curated catalog retain their own static resources. Loading a saved snapshot does not consult today's catalog. The shared experiment profile includes the catalog file. Activating approved content is an ordinary reviewed file/catalog change; task snapshots remain read-only; candidate maintenance is isolated from active publication.

## Planner-facing operations

Knowledge use adds no required citation or card-use declaration. The operating protocol conditionally requests a free-text `generate.justification`; runtime checks only that it is nonempty. `browse(id="experience-map")` lists approved entries and existing static resources. Search matches indexed text; renderer names and relevant questions should occur in that text as well as navigation metadata. The two professional manuals are `understand-and-design` and `understand-and-revise`.

Planner can refer to an ID in normal notes/workspace when useful. These are concise task judgments, not private reasoning transcripts. No `intent`, required citations, card-use declaration or reflection form is introduced. Critic receives no usage records or new experience context. Independent final scoring remains separate.

## Call-level record

`calls/<event>/experience-exposure.json` is created beside the already-saved final `input.json`, after context fitting. It binds the input SHA256 and knowledge snapshot SHA256. The record contains source identity/version/hash, JSON pointer, supplied fields, page range and one of:

- `catalog_reference`: title/identity/navigation metadata;
- `summary`: a discovery summary;
- `search_excerpt`: returned search snippets;
- `text_page`: actual source text with explicit page bounds;
- `image_attachment`: an attached experience reference image matched to its frozen hash.

Only structurally identified material in knowledge entrances or returned operation results is counted. A paginated archive fragment that cannot be resolved structurally is listed as an unresolved page; it is not claimed as a known full read. Raw task text and a remembered ID do not become source exposure. The exact original input preserves what the receipt refers to.

The receipt represents prepared content, not attention. The offline projection distinguishes a saved response, submitted attempts without a response, and a prepared request with unconfirmed dispatch. Semantic response validity is still visible in the operation outcome. A receipt failure produces a recording warning rather than causing another model call or blocking a creative operation. One logical call ID prevents retry double-counting.

## Per-run projection

`experience-usage.json` (`experience-use-v2`) is a disposable factual projection generated with the creative report. It links call surfaces, returned reads, literal ID references in model-authored notes/purpose/workspace/finish text and `generate.justification`, subsequent operations, candidates, saved online judgments and recorded generation seconds. It reads that run's snapshot, never the current library.

`decisions` joins each generation, delivery selection and finish event to the saved model input/response, actual operation disposition, knowledge exposure and literal references. A submitted generation includes its signed request, input, exact prompt, returned candidate IDs and online-review IDs. The continuation audit binds the questions, notice and operator policy to the exact input hash. A refused operation has no submission. Prepared requests retain their dispatch/response status. Missing historical audits remain null.

`delivery_proposals` supplies the proposal, report identity, full-report exposure and confirmation links. The decision view distinguishes `delivery_proposed` and `delivery_confirmed`, including superseded proposals. Follow the report and subsequent model response to understand a changed or retained preference. `cohort` includes experience mode, renderer, continuation policy, delivery protocol and migration records. Per-call audits identify the actual conditions before a migration; the latest configuration does not retrospectively assign questions to old decisions.

These are operator/maintenance records. They never enter Planner knowledge or Critic input. They contain no automatic assessment of explanation quality. The reading projection resolves moved run-local artifacts while preserving their original paths and expected hashes; unavailable media remains explicit.

Literal references remain unclassified. Their exact text and source event are available for the use-review Skill. Paraphrased adoption, implicit rejection and causal benefit are not inferred by code. Missing historical call receipts remain missing. Stored online outcomes are attributed to their own protocol; no conversion to the current main-score scale occurs.

`project_run` can be called by an offline exporter without importing the runtime or a video/model dependency. The human-readable creative report links this record and retains raw event/model-input links. It does not inject a usage summary into Planner context.

## Batch input and output

Call the deterministic exporter with a new output directory:

```sh
python scripts/summarize_experience_batch.py --manifest /path/to/batch.json --output /path/to/new-export
```

Manifest paths are relative to the manifest file, or absolute:

```json
{
  "batch_id": "development-review-01",
  "purpose": "development_maintenance",
  "runs": [
    {"id": "task-003-full", "path": "/path/to/topic/archive/runs/full", "data_role": "development",
     "topic_archive": "/path/to/topic/archive"}
  ]
}
```

The exporter preserves every listed run, including missing/corrupt sources. It reads only explicitly `development` runs; other roles are recorded as excluded before their states are read. Duplicate IDs/directories and output locations overlapping source runs are rejected. Existing exports are not overwritten.

Output: `README.md`, `batch.json` (`experience-batch-v2`), and `runs/<id>.json` plus a readable `runs/<id>.md` for each available included run. The reading page presents the questions, explanation, actual submission, delivery message and bound report, candidate video links, saved online scores/reasons, and available-evidence notes. The joined JSON retains full reports and frame references. Counts distinguish run inclusion/state, action dispositions, exact-version availability, read events, call exposure and literal references. Incomplete, paused and failed source runs remain included. Quality values stay in their original per-run protocol/cohort, not pooled into a usefulness score. Known generation costs are retained per candidate; absence is unknown, not zero.

`topic_archive` is optional, explicit offline authorization to read a completed development topic. The exporter verifies the archive manifest and the saved summary, arm record, judgment and identity hashes and checks task/source/candidate bindings. `independent_outcomes` preserves Direct and both Loop-first/final positions, separate GLM/Sonnet reports, disagreements and saved costs. Each run's candidates link to applicable positions by output hash. Unscored intermediates have no invented grade. Without this option no independent evaluator output is read. The exporter makes no provider calls and does not scan other evaluator directories. Archive source-video fallback is accepted only at its recorded hash. A failed archive check leaves independent outcomes unavailable and records the reason while retaining the task decision material.

Maintenance reads this package and follows source links. Analysis examines the judgment behind the attempt and its actual outcome. Use review identifies where guidance was found, interpreted, applied or rejected. Curation proposes or, when explicitly authorized, applies changes to entries and discovery metadata. Manual and Skill changes are separate development work. A retrospective interpretation identifies the run, source events, relevant experience version, and whether it quotes a model statement or is the maintainer's inference. Ordinary prose with exact links is sufficient; no mandatory interpretation schema is needed.

## Authority and lifecycle

| Actor | Available work | Persistent effect |
|---|---|---|
| Online Planner | Read experience and cases, keep task notes, cite or question guidance | Current task only |
| Post-task contributor | New judgment, recommendation, clarification, comment, exact proposed revision | Append-only private contribution layer where the campaign authorizes ingestion |
| Explicit library curator | Accept, merge, supersede or decline contributions; revise entry and metadata together | New private canonical snapshot and recorded decisions |
| Authorized developer | Revise Skills, professional/operating manuals, tools and protocols | Explicitly scoped repository changes |

The current task's snapshot stays fixed. Ingestion validates provenance and structure; its receipt states that canonical entries are unchanged. Contributions are immediately readable in an authorized full library, with their source cases and target versions. A contribution can make a clear practical recommendation without impersonating reviewed canonical guidance. No-experience snapshots exclude this layer as well as canonical experience.

Campaign configuration determines when the post-task hook is enabled and which snapshot each arm reads. Skills carry no dataset counts, arm ordering or scheduling rules. Existing formal admission verifies training membership and a settled real Planner trajectory; validation/test do not automatically contribute. The explicit development exporter above remains available. Original online exposure and post-task library access remain separate.

## Seeded libraries and review families

Every batch binds a nonempty full seed before execution, including batches whose
online mode is `none`. After an eligible task settles, the maintenance Skills read
its family's full private library. The online task retains its original restricted
snapshot and never receives its later maintenance conversation.

A private library records its owning batch, review mode (`critic` or `planner`),
renderer and seed hash. The same canonical seed and knowledge-map shape can serve
several families; each family's contributions, cases and revisions remain separate.
Maintenance reads, ingestion, resume and frozen copies verify that ownership.
Accumulated snapshots carry their owner with their revision, so importing a frozen
library cannot silently switch review families. Historical unbound runs retain
their original records and require a new output directory for this policy.

Full read-only batches browse their frozen entries and contribution/case links
through the existing map. Family separation changes which snapshot is loaded,
not the writing standard or the meaning of an experience entry. Campaign rules,
not the maintenance Skills, set the training/heldout split and hook eligibility.

## Post-task actions

`skill`, `browse`, `search`, `read`, `view_image` and `note` reuse saved knowledge and records. `observe(video_id, start?, end?, count?, crop?)` inspects one of the task's saved source/candidate videos. It verifies the recorded video hash and extracts at most eight sampled frames per call using native timestamps. Inspection metadata and image hashes are retained as post-task evidence. Reading a source case also registers that case's bound videos under case-prefixed IDs, so an authorized batch maintainer can inspect a cross-task comparison. This opens useful intervals the original Planner never viewed without generating or independently scoring a video.

`contribute(text, changes?)` records the author's account and optional concrete additions:

- `create`: `id`, `title`, `text`, `summary`, optional `questions` and `renderers`.
- `comment`, `clarify`, `recommend`, `propose_revision`: `id` identifies an existing entry or contribution; `text` is the actual account; optional `summary`, `title`, `questions`, `renderers` improve discovery.

A comment can carry a counterexample, a recommendation can favor an action under a stated condition, and a proposed revision can contain exact replacement wording. None overwrites its target. `replace`, missing operation names and manual/Skill mutation targets are rejected. Suggestions about manuals belong in report prose for separately authorized development.

The runtime binds each addition to a source case and the target's version/hash. Cases include original request, actual video/event records, settlement, exact-source references and new maintenance observations. Source cases remain immutable. `contribution.json` also retains the actual model input/response hashes. A no-increment result preserves the current library.

## Discovery

`browse('experience-map')` exposes current canonical summaries plus related contributions. `browse('contributions')` lists the contribution layer; `read(id)` opens the actual text and source case. `search(query)` searches both kinds of material. Reading an entry presents linked contributions as metadata on the first returned page, rather than appending objections to the end of its body. Curation status and target version remain visible. Adopted or declined records keep their history.

Experience map and renderer entrance recommendations are derived from canonical catalog metadata. Detailed historical profiles remain source material. A curation change updates text and metadata together and regenerates those entrances. Professional manuals point to entries for revisable empirical claims; their general reading methods remain stable.

Usage receipts include experience contributions and cases by identity/version/hash. They continue to record exposure rather than infer attention or causal benefit. The use-review Skill interprets the linked decisions and outcomes.

## Explicit curation

The task action set has no curation or activation action. An authorized maintainer prepares a decision list, then invokes:

```sh
python scripts/curate_experience.py --output /path/to/batch \
  --decisions /path/to/decisions.json \
  --expected-snapshot-sha256 <current-snapshot-hash> \
  --authorization <instruction-or-review-reference>
```

Each decision identifies `contribution_ids`, `disposition` and `reason`. `accept`/`merge` also supplies `entry` with `id`, `title`, `text`, `summary`, `questions`, `renderers`, plus `expected_entry_sha256` (null for a new entry). `supersede` names `successor_ids`; `decline` retains the account and its rejection reason. A stale parent or entry hash prevents applying an outdated edit. Entry IDs use the EX- namespace; manuals, Skills and runtime policies are outside this command's authority.

The command records authorization and decisions, preserves previous canonical text, creates an immutable snapshot and moves only the private current pointer. Existing task snapshots and the repository corpus remain unchanged. Publication into the shared repository is separate authorized work. The command does no model call and starts no experiment.

Draining contributions produces a batch bundle without automatically invoking a second curator. An explicitly requested batch drafting pass remains available as a proposal-only helper. It has the same read/observe/contribute boundary and cannot apply its own proposals.

## Compatibility

Historical snapshots and receipts retain their original content and protocol. Previously ingested `training_validated` entries can still be read; that historical label does not upgrade new contributions. New post-task profiles advertise append-only operations. Old frozen jobs that request replacement fail with an explicit operation error rather than silently rewriting canonical guidance. Resume such jobs only through an explicit protocol migration or retain their old frozen runtime.
