# Model-led Planner harness

[Approved implementation plan](planner-harness-plan.md) · [Knowledge integration](../knowledge/INTEGRATION.md) · [Operating guidance](../src/planner_harness/OPERATIONS.md)

The independent `planner_harness` package runs a continuing planning conversation over the source video, user request, and existing knowledge package. The model chooses observation and reading operations, maintains its own working notes, develops a visual proposal, and writes an English execution prompt. The default `plan` mode ends at a prompt handoff. The [continuous loop](agent-loop.md) adds generation, candidate observation and evaluation to this same task using `--mode loop`.

## Setup and execution

Use Python 3.10 or later. The Planner needs CPU video decoding, Pillow, and an existing model connection; it does not load video-generation or local Qwen weights.

```bash
python -m venv .venv-planner
source .venv-planner/bin/activate
python -m pip install -r requirements.planner.txt

python scripts/run_planner_harness.py \
  --source benchmark_data/main/041/041.mp4 \
  --request "Make it look like a children's storybook." \
  --output out/planner_harness/my-storybook-run \
  --backend codex --model gpt-6.1-sol --reasoning xhigh
```

On Windows, use the virtual environment's `Scripts/python.exe` with the same command arguments. The Codex backend reuses the repository's existing subscription transport and its authenticated CLI. `LOW_HIGH_CODEX_BIN` can select its executable. The compatible API backend uses `--backend litellm`, `LOW_HIGH_JUDGE_BASE_URL`, and `LOW_HIGH_JUDGE_API_KEY`. Authentication stays outside run artifacts.

The default target model is `unspecified` for Planner-only walkthroughs. `--target` records the intended renderer; it does not enable generation or imply renderer preflight. Existing Bernini experience retains its model-specific scope.

```bash
python scripts/run_planner_harness.py \
  --output out/planner_harness/my-storybook-run \
  --resume --backend codex --model gpt-6.1-sol --reasoning xhigh
```

Resume requires the recorded model/backend, unchanged source video, an unchanged per-run knowledge snapshot, and unchanged saved instructions. Pending calls reuse their recorded input; a completed response saved before interruption is consumed without another model call. To continue a run that exhausted its turn budget, explicitly add `--additional-turns N`. Completed runs are returned without rerunning. New runs never overwrite an existing checkpoint.

## Runtime responsibilities

| Component | Responsibility |
|---|---|
| `runner.py` | Stateful application-operation loop, durable checkpoints, response and submission validation |
| `knowledge.py` | Map and provenance browsing, lexical full-text search, actual line-range reads, source allowlist |
| `video.py` | CPU source-video decoding, timestamped overview and model-requested intervals/crops |
| `OPERATIONS.md` plus the knowledge reading manual | Model-facing English instructions for observation, exploration, creative decisions, and submission |
| `report.py` | Readable HTML and Markdown accounts assembled from actual events and observations |
| Existing VLM transports | Model communication and usage accounting; no style selection or prompt composition |

The existing Codex transport launches independent inference calls. The harness supplies conversation continuity explicitly: original task, current workspace, read receipts, attached-image mapping, recent complete exchanges, and a restorable earlier-operation index. This is application-owned state, not an assumed hidden provider conversation. The compatible API backend receives the same context contract.

The initial call includes six sampled source frames and the reading manual. The model may request a different interval, denser sampling, or a crop when a question warrants it. Times are derived from decoder frame indices and reported FPS; sparse frames are evidence of sampled appearance and broad progression, not proof of exact continuous motion. Knowledge reference images are labeled separately from source-video observations.

New runs snapshot the indexed readable material, including its map and complete text files. Subsequent reads use that snapshot; reference images are hash-pinned. Historical video assets are not duplicated into each reading snapshot. Search is lexical, with title weighting, and returns candidates for model judgment. Read operations supply original line numbers, source hashes, read IDs, and explicit continuation. Up to four reads can be requested together. The model chooses its reading depth; these operation sizes are transport bounds, not reading quotas.

Optional workspace nodes are model-defined questions, interpretations, directions, or decisions. The model can update, link, reparent, and remove them. The harness checks references and parent cycles. It does not prescribe clothing/prop/light fields, candidate counts, or style families.

The last ten operation exchanges appear in full in subsequent calls. Older exchanges remain indexed and recoverable through `history`. The original task, current workspace, and all read receipts remain present. Every call records its exact harness-provided text and attachment mapping. The reused Codex transport re-encodes images as JPEG at up to 1024 pixels; the recorded paths and hashes identify the source attachments supplied to that transport. If the configured character budget is exceeded, the run stops with an explicit incomplete status instead of silently cutting content. The character budget is a local resource bound, not a measured provider token count.

## Submission and evidence

A planning submission needs only the exact English prompt. The model may add an understanding, proposal, source-use explanations, self-review or unresolved points when these help communicate its choices. Source citations must name passages actually returned by `read`; source hashes are checked again at submission. An invalid prompt or supplied citation returns to the model for correction. Additional reporting fields are optional. These checks verify reference and output integrity. The model's self-review is an inspectable judgment, not an independent quality score.

The accepted prompt is saved without added template blocks or automatic truncation. `handoff.json` explicitly marks renderer tokenization/preflight as pending and renderer submission as not performed. An accepted planning handoff does not claim video-generation success, semantic preservation, or measured improvement.

The [continuous agent loop](agent-loop.md) keeps generation results, evaluations, reading history and later decisions in this same application-owned task. The Planner can edit any available candidate or the original and select any retained result. The old outer controller and its separate decision stage are retained only as historical code.

Each run contains:

| Artifact | Content |
|---|---|
| `state.json` | Request, runtime hashes, optional notes/workspace, events, read receipts, status, task videos, jobs, evaluation and final selection |
| `knowledge-snapshot.json` | Exact indexed reading text and image hashes used throughout this run |
| `system-prompt.txt` | Exact operational guidance and reading manual used by that run |
| `calls/event-NNNN/input.json` | Exact model-facing text and ordered image metadata |
| `calls/event-NNNN/response.txt` | Actual visible model response |
| `events/event-NNNN.json` | Requested operation and actual returned result, including source passages |
| `observations/` | Source frames and requested crops that were supplied |
| `proposals/` | Each submission and validation outcome |
| `proposal.json`, `prompt.txt`, `handoff.json` | Accepted design, unchanged prompt, and pending execution boundary |
| `model-usage.jsonl` | Existing transport's usage records |
| `report.html`, `report.md` | Navigable account of observations, readings, visible decisions, and final output |

On Windows, process locks live in the host's temporary directory because WSL UNC shares may not support byte-range locks. Linux uses a run-directory lock. Locks are host-scoped and released by the OS; use one execution host for a run directory. Source and checkpoint artifacts can still reside in the shared repository.

## Checks and walkthroughs

```bash
python scripts/test_planner_harness.py
```

The focused checks use explicitly scripted responses and a synthetic clip to test reference validation, response continuity, recovery, exact prompt handoff, source changes, resource limits, observation indexing/crops, workspace validation, and exclusive run ownership. Scripted checks are separate from actual model walkthroughs.

Live validation uses the existing 041 short storybook and fewshot/004 long space-station tasks, plus a curator-authored cyber-xianxia request and a narrow robe-color request on main/001. The first two are already discussed in the knowledge corpus and demonstrate integration. The other two exercise composition and scope control outside those walkthroughs; this small set is not a general performance benchmark. No hidden benchmark target prompt or target video is loaded by the harness.

All four actual runs completed and passed record verification. The [walkthrough review](../out/planner_harness/20261029/review.md) and [report index](../out/planner_harness/20261029/index.html) provide their full observations, readings, proposals, and prompts. The approved plan records completion status. Use `python scripts/verify_planner_run.py RUN_DIRECTORY` to recheck source passages, citations, supplied image hashes, model responses, and exact prompt handoff.
