# Historical outer-loop draft

Superseded by [the continuous Planner](agent-loop.md). Retained for interpreting old replay records. Its command is now `scripts/run_legacy_agent_loop.py`.

# Outer agent loop

The independent Planner now connects to a durable outer controller. This implementation can adopt an existing planning result, publish a generation job, collect a candidate, request evaluation and selection, run a new child Planner with feedback, and publish the next generation request. Each step can resume from disk. Live renderer workers and the separately developed evaluation/selection policy connect through the adapter contract below. The local integration checks use explicit replay fixtures; no new GPU generation or measured improvement is established.

## Workflow and responsibility

```text
Completed Planner proposal
  -> render request -> renderer execution receipt + candidate video
  -> evaluation request -> versioned findings, metrics and uncertainty
  -> decision request -> accept / reject / undecided; stop / revise
  -> child Planner with original, candidate, incumbent and feedback
  -> new proposal -> render request ...
```

The model chooses questions, knowledge, visual direction and revision content. The harness preserves inputs, executes application operations, records evidence and enforces resource limits. The evaluator provides observations and measurements. A separately versioned decision policy selects candidates and the next input. It can be human-authored initially and automated later. The controller has no built-in aesthetic score, weighted metric, quality threshold or preferred route.

The original is immutable. An incumbent exists only after an explicit `accept` decision. A rejected or undecided candidate remains inspectable. `input=original` restarts from the source; `input=incumbent` edits the explicitly accepted result. `full` and `incremental` describe what the instruction must mean for that actual input. The model remains responsible for the wording. The generator has no implicit access to earlier turns or to an original it was not given.

## Use

Use the lightweight environment in [planner-harness.md](planner-harness.md). No additional controller dependencies are needed. A renderer config records its backend, requested settings and exact output contract:

```json
{
  "backend": "ditto",
  "settings": {"seed": 42, "steps": 50},
  "output": {"frames": 121, "fps": 24}
}
```

This is an illustrative configuration shape, not an approved model-specific preset. The adapter must check supported frame counts, sampling, dimensions, model configuration and tokenizer limits before rendering. The controller checks reported frame count/FPS and decodes output endpoints; full temporal quality remains evaluator work.

```bash
python scripts/run_agent_loop.py --run out/agent_loop/my-run init \
  --planner-run out/planner_harness/20261029/041_storybook \
  --renderer-config renderer.json --max-candidates 3 --max-render-jobs 3
python scripts/run_agent_loop.py --run out/agent_loop/my-run status
python scripts/run_agent_loop.py --run out/agent_loop/my-run respond --file response.json
python scripts/run_agent_loop.py --run out/agent_loop/my-run advance
python scripts/run_agent_loop.py --run out/agent_loop/my-run revise
```

`init` and `advance` publish requests and consume already supplied responses. They do not launch remote processes, render videos, run an evaluator or call the planning model. `revise` explicitly calls the model and defaults to GPT-6.1-sol/xhigh. It reuses the Planner's knowledge tools, durable context and resumable calls. `--additional-turns` can extend a stopped child planning budget. `retry --reason ...` is an explicit retry after a failed/rejected response; it creates a new job identity and retains the old failure. Render retries consume the render-job budget.

The controller exits when external work is pending; it does not busy-poll. A worker or supervisor can call `advance` after a completion event. For manual monitoring, use the user's 10–15 minute cadence for long jobs. Only one controller process should own a run on one host. The existing host-local run lock is not a cross-host distributed lock; remote workers exchange request/response files rather than opening the controller state.

## Adapter contract

Each `jobs/<id>/request.json` contains `id`, `kind` (`render`, `evaluate`, `decide`), `mode` (`live`, `replay`), `payload` and a canonical `sha256`. Adapters must use the job ID/hash for idempotency and recover an existing job after an interruption. The controller republishes the same identity until a response arrives; duplicate prevention inside a remote worker is that adapter's responsibility.

Every final response has this envelope:

```json
{
  "request_sha256": "exact request hash",
  "mode": "live",
  "status": "complete",
  "payload": {}
}
```

For a failure, use `status=failed` and nonempty `error`. A pending worker publishes no final response. Use the CLI `respond` command or `agent_loop.core.publish_response`; responses are written atomically and cannot be silently overwritten. A stale/mismatched response is rejected. Invalid payloads leave a visible failure that can be explicitly retried after correction. No missing score or success result is synthesized.

### Renderer response payload

```json
{
  "video": {"path": "/controller-accessible/output.mp4", "sha256": "actual file hash"},
  "execution": {
    "backend": "ditto",
    "requested_prompt": "Exact request prompt",
    "effective_prompt": "Exact text used after documented renderer preprocessing",
    "prompt_transforms": [],
    "input_sha256": "actual conditioning video hash",
    "settings": {"seed": 42, "steps": 50},
    "preflight": "passed",
    "token_count": 123,
    "token_limit": 512,
    "model_revision": "verified model revision or manifest hash",
    "code_revision": "renderer code revision",
    "tokenizer_revision": "tokenizer identifier and revision"
  }
}
```

The adapter records any model-required prefix, cleaning or other transformation in `prompt_transforms`. The controller never appends critique text, preservation clauses, negative prompts or hidden parameter adjustments. Backend/settings and requested prompt/input must match the request. The adapter is responsible for truthful execution provenance; controller receipt validation does not independently reproduce GPU execution. Additional fields such as conditioning frame indices and runtime versions are preserved. Transfer remote media to an accessible path before publishing completion.

`mode=replay` requires a nonempty `replay_provenance` in the payload and allows a clearly marked `preflight=not_run`. Replay cannot be consumed by a live run. It is used for orchestration checks only.

### Evaluation response payload

```json
{
  "protocol": {"id": "chosen-by-evaluation-session", "version": "version-id"},
  "findings": [],
  "metrics": {},
  "uncertainties": []
}
```

The request supplies the original, actual generation input, candidate, incumbent when present, user request, proposal and execution receipt. `findings` and `uncertainties` are arrays; their content and all additional metric, scale, coverage, timestamp and evidence fields remain owned by the evaluation protocol. Missing observations can remain unknown. No score aggregation is imposed here. Frame alignment, temporal sampling and evidence sufficiency must be stated by that protocol; the controller does not assume videos align.

### Decision response payload

```json
{
  "policy": {"id": "human-review-or-automated-policy", "version": "version-id"},
  "evaluation_sha256": "hash supplied in the decision request",
  "selection": "accept",
  "next_action": "revise",
  "input": "original",
  "instruction_mode": "full",
  "reason": "Evidence-based reason for this selection and next step"
}
```

`selection` accepts `accept`, `reject`, `undecided`; `next_action` accepts `stop`, `revise`. A revision specifies `original` or `incumbent` and `full` or `incremental`. Unknown evidence stays available to the policy and Planner. Candidate and render-job limits still stop further generation requests. A terminal `stopped` state records why it stopped and the selected incumbent, if any; it does not assert task success.

## Records and revision context

- `state.json` and `report.md`: current state, ancestry, incumbent, budget, prompts, receipts, evaluations and decisions.
- `jobs/`: frozen requests, adapter responses and consumed-response snapshots.
- `candidates/`: copied proposals, collected videos and technical decode observations.
- `planning/revision-NNN/`: frozen revision context, source/candidate/incumbent overviews, complete child Planner calls, reads, proposals and report.

The child receives the original request and source, prior proposal, candidate execution, evaluation, decision, incumbent proposal and selected next input. It can `observe` any supplied video by `video_id`, read knowledge again, and develop its own workspace. Sampled overviews are explicitly labeled and independently sampled; precise trajectory claims need stronger evidence. Original planning files and earlier candidates are never overwritten. The loop has no automatic writeback into the knowledge library or long-term memory.

## Validation and remaining integration

Run `python scripts/test_agent_loop.py` and `python scripts/test_planner_harness.py`. The outer checks cover stable pending jobs, unknown metrics, source restart, accepted-parent editing, rejection/rollback, budgets, stale receipts, failed jobs, decoder checks and child-Planner recovery. Tests use scripted model operations and synthetic media. They establish controller behavior, not live revision quality.

Existing Bernini and Ditto probe scripts provide useful worker precedents: explicit tokenizer checks, recorded conditioning and model/configuration identity. Their ongoing experiments and outputs are left unchanged. Production connection still needs a worker adapter that maps the selected deployment's request/receipt to this contract and the evaluator based on the other session's metric design. Automated selection and continuation policy can then be calibrated against that evidence. The controller and revision path can be exercised now while those definitions are finalized.

An [inspectable 041 replay](../out/agent_loop/20261029_041_replay/report.md) adopts the completed live Planner handoff and uses the archived Bernini long-prompt video as a transition fixture. It records acceptance, a source restart, scripted child planning, rejection and retention of the earlier incumbent. It makes zero new model inferences and zero new video generations; the archived video's actual earlier prompt is saved alongside the simulated request. Reproduce in a new directory with `python scripts/demo_agent_loop_replay.py --output out/agent_loop/replay-new`.
