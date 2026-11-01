# Running the seven-topic comparison

The user opens the host before execution. Use the reviewed commit in an isolated checkout and a host-local output directory. This entry never rents, starts or stops an instance. Keep credentials outside the checkout and use server-side downloads for large assets.

## Preparation and startup

1. Install the existing Bernini deployment dependencies and pinned assets. Copy `configs/creative-fewshot-host.example.json` outside the repository, replace both asset placeholders with the verified manifest and SHA256, and name the actual one or two GPU indices. Each worker sees one GPU. Both use 40 steps, `v2v_apg`, size 848, the original time axis and no prompt enhancer.
2. Supply `gpt-6.1-sol/high` through the existing Codex vision adapter for Planner and online Critic. Verify host authentication and executable availability before rendering. Optional `models` factory settings in the host file follow the existing service contract; model and reasoning settings remain enforced.
3. Set external environment variables: `LHA_PARATERA_BASE_URL=https://llmapi.paratera.com/v1`, `LHA_PARATERA_API_KEY`, `LHA_SONNET_BASE_URL=https://api.tu-zi.com/v1`, and `LHA_SONNET_API_KEY`. Never put keys in the host JSON, prompts, command arguments or Git.
4. Freeze the batch with `python scripts/run_creative_fewshot.py prepare --output /host-local/batch`. This checks all seven exact sources and long prompts, and binds runtime, manuals, both knowledge scopes, renderer conditions and judge identities.
5. Run `python scripts/run_creative_fewshot.py preflight --output /host-local/batch --host-config /private/host.json`. Check assets, original prompt token counts with the actual Bernini tokenizer/prefix, device mapping and network/model authentication. Preflight does not load the generation pipeline or generate a video.
6. Validate both provider contracts with `provider-preflight --judge glm5.3flash` and `provider-preflight --judge sonnet-5.5high`, using the same `--output`. These are synthetic CPU-made square videos, not benchmark scoring. Retain successful evidence and its identity; do not rerun an unchanged check. When transferring an existing successful receipt, preserve the synthetic media, request, raw response and hashes, and rebase only its artifact location under an explicit transfer record.
7. After startup authorization, run `python scripts/run_creative_fewshot.py run --output /host-local/batch --host-config /private/host.json`. No legacy RSI launcher is used.

## Topic scheduling and completion

Direct runs once using the exact original long prompt. Full and no-experience Loops then run on separate persistent workers if two GPUs are available. With one GPU they run sequentially. Each Loop chooses its observations, reads, prompts, optional one-shot Critic calls, inputs and final candidate. A fourth or later generation is allowed. `max_generations` and `max_turns` are null; no outer fixed-count stop replaces them.

Both Loops must reach a generated delivery candidate with `stop_reason=satisfied`. A context/resource pause, execution failure or lack of a promising next attempt remains incomplete. The coordinator keeps the current topic and records its state; it never advances by labelling a failed task delivered. Resource adjustments remain separately recorded through the existing recovery tools.

The two final judges run in parallel with at most one call per provider at a time. Each evaluates the Direct output and each Loop arm's first and final selected output using the same original request and deterministic visual evidence. Start each eligible judgment as soon as its completed video and receipt are verified, independently of generation. First/final identity matches reuse a score. Other intermediate candidates remain archived without independent final scoring. Use server-side scoring when reachable; otherwise retrieve the required media/evidence and score locally under the same frozen protocol. Reports do not contain arm, iteration, Planner notes, online Critic scores or the other judge's findings. A source/request/output/protocol/model/adapter match allows reuse of a prior score. Invalid output is retained and blocks this topic; it is not repaired by a follow-up model conversation.

Only after both judges finish does the coordinator copy videos and complete traces, construct the comparison page, verify every archived file hash and admit the next topic. Restart uses existing receipts and scores. It does not regenerate completed arms. The archive, rather than an in-memory completion flag, is the next-topic gate.

## Outputs and comparisons

`topics/<id>/archive/index.html` links the source and every candidate, exact prompts and ancestry, observations, knowledge reads/use records, online reviews and independent scores. Raw records retain their original bytes. Portable report projections link copied videos, frames and model exchanges within the archive.

Each judge has its own six paired comparisons: Direct to full-first, Direct to none-first, full-first to full-final, none-first to none-final, none-first to full-first, and none-final to full-final. Report planned and valid pairs per dimension, null/unknown judgments, gains/ties/losses, actual generation counts, known generation seconds and missing cost records. Judge disagreement is shown by dimension, without a blended score or assumed adjudicator. Results describe seven development topics, not an unseen test cohort.

## Interruption recovery

Inspect `checkpoint.json`, the current topic's arm receipts, and `workers/<device>/queue.sqlite3`. The existing `scripts/run_server_pipeline.py --service <worker> status` command uses this same database. Do not start its general runner alongside the batch owner.

- A finished response whose process died before queue commit is recovered without a new call. A stable Planner checkpoint is similarly reused.
- A Planner/Critic transport failure uses `scripts/manage_creative_run.py --service <worker> --queue-job <id>` with `retry-planner` or `recover-tool`, the original run/job, and a recorded reason. It reopens the same bounded transport call and queue job. An invalid semantic answer is retained.
- An uncertain Loop render uses `recover-tool --action receipt` for its existing signed response, or `--action not-executed` only after confirming that dispatch did not execute. Never infer non-execution merely from a missing output.
- Direct uses `scripts/run_creative_fewshot.py recover-direct --output <batch> --device <index> --topic <id> --reason <reason>` plus either `--receipt <complete-response.json>` or `--not-executed`. It reconciles the original request and records recovery; it does not render.
- Independent judge transport retries are bounded and recorded in `final-judge/<identity>/call`. An operator can use the existing `planner_harness.model_call.reopen_call` after inspecting an exhausted transport attempt. A successful score is reused. A returned invalid report remains a failed report.
- A context/resource pause uses `manage_creative_run.py resources`. Preserve the original task, knowledge and model identity; record any technical capacity increase. Then resume the same batch command.

Check long-running work normally every 10–15 minutes, or respond sooner to a failure/completion event. No cross-topic generation is prefetched. Experience maintenance and automatic adoption remain outside this experiment.

## Execution ownership amendment

The GPT-6.1-sol/xhigh execution process owns monitoring, early eligible-video judging and archival. Follow [the explicit handoff](creative-fewshot-sol-handoff.md) when migrating the already-running coordinator. The original conversation no longer performs routine experiment polling.
