# Experience access, usage records and batch maintenance

This interface extends `creative_loop_v1` only. It adds passive provenance and an offline export, with no model client, evaluator, scheduler or publication process. It preserves existing Planner operations and candidate/stop semantics.

## Read-only curated catalog

`knowledge/creative-loop/manifest.json` names the dedicated `knowledge/experience/curated/catalog.json`. Its schema is `creative-experience-catalog-v1`, with `revision`, `entries` and `resources`. The currently committed entries/resources are empty pending content review. Historical static resources remain readable.

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

The catalog and its texts/assets are pinned in the task's knowledge snapshot. Old snapshots without a curated catalog retain their own static resources. Loading a saved snapshot does not consult today's catalog. The shared experiment profile includes the catalog file. Activating approved content is an ordinary reviewed file/catalog change; no learning hooks or publication lock are added.

## Planner-facing operations

No new operation or mandatory argument. `browse(id="experience-map")` lists approved entries and existing static resources. Search matches indexed text; renderer names and relevant questions should occur in that text as well as navigation metadata. The two professional manuals are `understand-and-design` and `understand-and-revise`.

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

`experience-usage.json` is a disposable factual projection generated with the creative report. It links call surfaces, returned reads, literal ID references in model-authored notes/purpose/workspace/finish text, subsequent operations, candidates, saved online judgments and recorded generation seconds. It reads that run's snapshot, never the current library.

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
    {"id": "task-003", "path": "/path/to/saved/run", "data_role": "development"}
  ]
}
```

The exporter preserves every listed run, including missing/corrupt sources. It reads only explicitly `development` runs; other roles are recorded as excluded before their states are read. Duplicate IDs/directories and output locations overlapping source runs are rejected. Existing exports are not overwritten.

Output: `README.md`, `batch.json`, and one `runs/<id>.json` for each available included run. Counts distinguish run inclusion/state, exact-version availability, read events, call exposure and literal references. Incomplete, paused and failed source runs remain included. Quality values stay in their original per-run protocol/cohort, not pooled into a usefulness score. Known generation costs are retained per candidate; absence is unknown, not zero. No external evaluator directory is scanned.

Maintenance reads this package and follows source links. A retrospective interpretation belongs in a separate authored review: identify the run, source events, relevant experience version, the interpretation and whether it quotes a model statement or is the maintainer's inference. Ordinary prose with exact links is sufficient; no mandatory interpretation schema is needed.

## Content lifecycle

The maintainer analyzes, reviews use or curates according to the requested task. Exact proposed edits stay staged. The user reviews the wording and activation scope. Approved entries/resources can then be copied to the curated directory and listed with their actual hashes and review reference. Running snapshots do not change. Content acceptance does not establish an experimental benefit.

The [full maintenance package](../knowledge/staged/experience-full-maintenance-20261101/README.md) maps all 45 old cards into fourteen rewritten entries, renderer profiles and five proposed Planner manuals. The writing standard and three maintenance Skills carry the revised judgment-bearing style; the experience entries and Planner manuals remain staged. New experiments, independent scoring, simulated Planner runs and automatic global knowledge changes remain deferred. Static source/provenance checks and deterministic inspection of saved development records are permitted by the current implementation plan.
