# Low-friction context and Luna pilot

Approved on 2026-11-05. Implementation baseline: `7c8add9`, branch
`codex/experience-curation-v1`.

## Scope

Reduce avoidable API round trips and repeated input while retaining model-led
planning. Keep four render submissions, input/prompt choice, earlier-candidate
selection, existing review/delivery rules, knowledge content, maintenance scope,
independent scoring and same-command recovery. Do not alter running experiments.
Complete history stays on disk; historical tool results do not become a new
permanent prompt buffer. No new RSI system, scheduling system, mandatory notes,
reasoning sequence or delivery gate.

## Implementation sequence

1. Align documented tools and validation. Normalize unambiguous equivalent forms,
   preserve original responses and normalization records, support batch reads of
   existing objects, and return actionable errors. Keep attached notes/workspace
   updates optional. Never guess a missing render input or candidate identity.
2. Associate each candidate with its actual prompt, parent and saved review through
   existing video/history interfaces. Present useful facts without interpreting
   their quality. Keep complete raw records accessible.
3. Deduplicate read pages and repeated context objects. Keep the current read
   complete, project older knowledge through existing summaries and exact reading
   links under a soft display allowance, and keep all originals on disk. Compact
   JSON and omit operational metadata from model-facing views. Keep the request,
   model-authored notes, latest review and visual evidence intact. Do not add a
   summarizer or change frame sampling/resolution.
4. Reconcile logical calls, HTTP attempts, retry ownership and returned usage.
   Separate Planner, Critic, maintenance and final evaluation. Preserve unknown
   usage/cost. Report input/output/cache/reasoning separately without double
   counting nested attribution. Record context component sizes locally.
5. Run offline regression and historical-input checks: parameter equivalence,
   retrieval, context savings, four attempts with earlier selection, interrupted
   recovery without duplicate work, role configuration and usage accounting.
   Commit and synchronize GitHub before deploying the pilot.
6. Pilot on existing authorized idle capacity only: 005 long (jungle ruins) and
   026 short (brick animation), PE Loop versus pre-experience Loop. Four trajectories,
   at most 16 render submissions, 117 frames, paired seeds, existing Bernini 40-step
   v2v_apg max-size-848 profile. Complete both arms, final judgments and archive for
   one topic before admitting the other. Private maintenance retains the frozen
   online seed and cannot change a production library. No new rentals or interruption
   of existing work. Use a separate pilot registry so completed Sol runs cannot
   satisfy a new Luna task. Reuse the pilot's original output on interruption.

## Model and evaluation boundary

User requested 6luna. Exact gateway model name and supported parameters must be
verified against the selected connection before execution; no silent fallback.
The role choice (Planner/maintenance only, or also online Critic) is pending the
user's outstanding answer. Existing independent judges and scoring protocol stay
unchanged. Local implementation and software checks can proceed independently.
Archive first, last and selected candidates; deduplicate identical evaluation
targets through the existing evaluation pipeline. Retain raw failures and unknowns.

## Evidence and acceptance

Software checks use existing records and scripted responses, without GPU/model
calls. Report actual context sizes before/after, preserved object identities and
retrievability. Real pilot results report per-role logical calls, HTTP attempts,
input/output/cache/reasoning token coverage, format/operation failures, repeated
reads, renders, quality judgments and complete traces. Compare PE/pre-experience
and first/selected outcomes. Historical Sol runs are descriptive references: both
model and context implementation change in this pilot.

## Progress

- [x] Plan saved before implementation.
- [x] Interface compatibility and candidate retrieval.
- [x] Context projection and exact archive access.
- [x] Provider accounting and explicit per-role model configuration support.
- [x] Offline verification and historical context comparison.
- [ ] Commit and verified GitHub synchronization.
- [ ] Confirm role scope and available authorized pilot host.
- [ ] Complete and archive the pilot, including final evaluation.

No production experiment was started or modified when this plan was created.

## Implementation record

`tool_interface.py` provides the tool signatures used by new Planner instructions
and deterministic equivalent-argument normalization. Original output and each
normalization remain in call receipts. Candidate retrieval returns actual submitted
prompts, parent IDs and saved reviews together, including batch retrieval and an
optional textual prompt diff. It does not interpret which candidate is better.

`context.py` and `working_memory.py` project a compact working view. The current
read remains complete; older pages use their existing summaries and reading/archive
links under a soft 24,000-character display allowance. Current reading can exceed
that allowance. The policy does not summarize conditions away or require the model
to perform memory-management operations. Complete history, notes and source pages
stay local. Repeated complete source lines, frame transport metadata and repeated
catalog fields are omitted from the prompt; the underlying records are unchanged.
Maintenance applies the same presentation principle to repeated image catalogs,
read pages and loaded Skills, without changing publication or contribution scope.

LiteLLM records every HTTP attempt, including failed/unknown calls and returned
usage. The adapter owns bounded transport retries; the caller no longer multiplies
that allowance for new logical calls. Existing pending inputs and recovery receipts
remain authoritative. Cached/reasoning attribution is reported as a subset of
input/output usage; unknown cost or missing usage stays unknown. No extra model
calls are introduced to compress context or judge tool arguments.

PE Loop previously rejected every model except Sol/high even when a different
model was explicitly configured. It now freezes and uses the supplied role options,
as the Planner arm already does. Production defaults remain Sol/high. Offline tests
verify that PE and pre-experience accept the same explicit pilot identity, the
maintenance role inherits it, and pre-experience starts with a nonempty private seed.

### Offline evidence

The same saved states were projected through baseline `7c8add9` and the new code.
No model was called and no video was decoded or rendered for this comparison.

| Saved state | Previous user-context characters | New characters | Reduction |
| --- | ---: | ---: | ---: |
| 005 long | 91,147 | 50,467 | 44.6% |
| 026 short | 102,744 | 53,894 | 47.5% |

Both comparisons retain identical image selections (12 images), original requests,
notes and evaluation content. The saved state files remain unchanged. These are
character measurements, not measured Luna token savings or evidence of unchanged
generation quality. The current system-reference expansion is separately visible
in saved inputs; the comparison holds the original system prompt constant.

Focused tests cover tool aliases and conflicts, optional notes, exact original
receipts, batch candidate retrieval, one-object format tolerance, reading projection,
image/coverage identity, maintenance projection, HTTP accounting and durable-answer
reuse. Existing current-path checks cover four renders with early-version selection,
same-command recovery, original pending calls, device changes, private maintenance,
formal-score isolation and public command entry points.

Expanded legacy tests expose 21 pre-existing failures: 12 in old delivery/migration
expectations, eight in the old remediation module, and one pre-fix PE interruption
expectation. All 21 reproduce on the unmodified `7c8add9` snapshot. They are retained
as known baseline debt, not reported as passing. The online image-contract test now
checks the actual attached file hashes and video/frame coordinates rather than
requiring transport hashes inside the model-visible JSON.

Local evidence lives under `out/low-friction-context/20261105/`. Reproduce the
read-only usage summary with:

```bash
python scripts/summarize_model_usage.py RUN_DIRECTORY --output USAGE_REPORT.json
```

The historical 005 check reconciles 29 Planner calls (825,296 tokens) and nine
Critic calls (130,571 tokens). Historical inner HTTP multiplicity is not instrumented;
the report labels it accordingly. No provider cost was returned.

### Pilot commands and resume boundary

The authorized idle host and role choice are still pending. Resolve the actual
gateway model name before creating the pilot batches. Put role options in an external
model-config JSON and matching host configuration; keep credentials in the process
environment or existing private credential mechanism. Do not replace production defaults.

For 005 long, use a fresh pilot directory and result registry:

```bash
python scripts/run_creative_benchmark.py prepare \
  --output out/luna-pilot/005-long --results-root out/luna-pilot/005-long-results \
  --backend bernini --split train --sample-ids 005 --prompt-form long \
  --method pe-loop pre-experience --max-generations 4 \
  --seed-start 42 --seed-step 1 --model-config "$LHA_LUNA_MODEL_CONFIG"
python scripts/run_creative_benchmark.py preflight \
  --output out/luna-pilot/005-long --host-config "$LHA_LUNA_HOST_CONFIG"
python scripts/run_creative_benchmark.py run \
  --output out/luna-pilot/005-long --host-config "$LHA_LUNA_HOST_CONFIG"
python scripts/run_creative_benchmark.py status --output out/luna-pilot/005-long
```

Confirm both arms' settlement, all four submissions, original candidate ancestry,
model-led final selection and private maintenance receipts. Then run the unchanged
independent evaluation pipeline for that isolated registry:

```bash
python scripts/benchmark_results.py prepare-evaluation \
  --root out/luna-pilot/005-long-results --evaluation-id luna-pilot-005-long
python scripts/benchmark_results.py score-evaluation \
  --root out/luna-pilot/005-long-results --execute
python scripts/benchmark_results.py export-shard \
  --root out/luna-pilot/005-long-results --run out/luna-pilot/005-long \
  --output out/luna-pilot/005-long-export
python scripts/summarize_model_usage.py out/luna-pilot/005-long \
  --output out/luna-pilot/005-long-usage.json
```

Retrieve and verify the export and evaluation records before proceeding to 026
short. Use separate `026-short` paths and `--sample-ids 026 --prompt-form short`;
both topics begin with the same frozen seed, while maintenance remains private to
their respective outputs. On interruption rerun the original command and directory;
do not prepare a new identity, reset budgets, or rerender completed work. Real
model calls, GPU generation and independent scoring have not started in this change.
