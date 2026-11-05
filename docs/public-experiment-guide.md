# Run the published LHA experiments

This guide targets a new Linux/WSL checkout. All commands run from the repository
root. The source release includes configuration, prompts, knowledge, software and
tests. Operators supply benchmark media, renderer weights, compatible GPU runtimes
and credentials. None of those private inputs is required for the offline smoke.

## 1. Inspect the source release without a GPU or credentials

Use Python 3.11+ and system `ffmpeg`/`ffprobe`. Install the controller dependencies
in an isolated environment; this does not install torch, CUDA or model weights.
Use `git clone`: GitHub source ZIP exports omit images under the repository's
existing redistribution policy, including images required by the frozen knowledge
catalog. A ZIP alone is therefore not a complete runtime knowledge checkout.

```bash
git clone --branch codex/experience-curation-v1 https://github.com/fpddmw/LHA.git
cd LHA
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.server-runtime.txt
python scripts/run_experiment_campaign.py plan --backend both
python scripts/smoke_experiment_campaign.py --output out/public-smoke
```

The smoke command creates synthetic videos and scripted model responses. It blocks
network calls, hides CUDA devices and blocks imports of model/GPU libraries in its
workers and Python children. No API key, benchmark video or renderer is used.
Use an empty output directory on each invocation; prior evidence is retained.

Artifacts:

- `out/public-smoke/smoke.json`: stage coverage and explicit verification limits.
- `out/public-smoke/tests/summary.json` and per-module logs: pass/failure evidence.
- `out/public-smoke/example/README.md`: a synthetic end-to-end handoff.
- `out/public-smoke/example/results/index.html`: synthetic Direct and both reviewer
  families, first/last/selected results, independent judge projections and comparisons.
- `out/public-smoke/example/trace-summary.json`: four-attempt trajectories that select
  an earlier candidate. Their private experience contributions remain in the example.

The handoff exercises real Planner state transitions, automatic Critic/self-review
collection, private maintenance, frozen experience use, result registration and
scoring/cache/reporting. Other integration modules cover main/ablation ordering,
both renderer adapters, failure recovery and CLI dispatch. Renderer outputs,
Planner decisions, judge answers and encoder values are fixtures. This verifies
software contracts, not model quality, API access or GPU performance. Paths inside
copied raw receipts refer to the temporary test workspace; the HTML/media view and
summary are portable. Do not import these artifacts into a research result registry.

## 2. Fixed experimental design

Each renderer uses the same 67 tasks, each with short and long prompts: 134
conditions. The 40/27 train/test division controls experience maintenance. It does
not remove training tasks from the full main-method comparison.

| Stage | Online method | Experience maintenance | Render allowance per condition |
|---|---|---|---:|
| `pre-experience` | Complete Planner, independent qualitative Critic; reads the frozen pre-experience seed | After both forms of all 67 tasks | 4 |
| `full-experience` | Same Planner/Critic, its own frozen accumulated experience | Disabled | 4 |
| `direct` | Exact user request sent directly to renderer | None | 1 |
| `pe-loop` | Renderer-specific prompt enhancement with Critic feedback; source input each round | None | 4 |
| `self-review-pre-experience` | Complete Planner reviews its result in the task context; reads the frozen pre-experience seed | After both forms of all 67 tasks | 4 |
| `self-review-full-experience` | Self-review Planner reads its own frozen accumulated experience | Disabled | 4 |

All Planner arms retain style/semantic knowledge and operating tools. Every family
starts with the same nonempty seed. The pre-experience Planner and its maintainer
read that fixed snapshot for every task. The full-experience arm uses the seed plus
the indexed contributions from the first 40 tasks. The other 27 tasks' contributions
are deferred for a later campaign. Critic and self-review families and the two
renderers own separate private increments. Maintenance records new entries,
comments, clarifications and revision proposals. Canonical curation is separate.

Four attempts are required before final Planner selection. Prompts and input
candidates remain model-led; the selected result may be an early candidate. Failed
submitted renders consume an attempt. Uncertain execution is recovered against its
original receipt. Technical interruptions retain their actual incomplete status.
There is no elapsed-time deadline for online tasks, maintenance or final scoring.
Render count remains four (Direct renders once). Token/time estimates are recorded
for planning, not enforced as deadlines. Maintenance retains its 32-call,
2-million-token and two-attempt controls. Network/connection timeouts and failed
process detection remain technical recovery controls.

Every new source is uniformly sampled over the complete clip, including endpoints,
to **117 frames at 24 fps (4.875 seconds)**. This retimes the complete source; short
clips repeat nearest frames and longer clips omit intermediate frames. Bernini,
Ditto, all six arms, and both judges use the same prepared source. Iterative inputs
and new outputs retain the 117-frame axis. Original files and hashes remain unchanged;
`inputs/sources/*/normalization.json` records all selected original indices and
both file hashes. Result archives include the prepared source. Keep the original
output root when upgrading; existing native-length videos remain complete and
retain their actual timing. The default explicit historical registry is
`out/benchmark_results`. Its matching completed method/review-family results are
reused; no directory-wide scan or cross-renderer substitution occurs.

Per renderer: main 536 trajectories / at most 1,742 render submissions; self-review
268 additional trajectories / at most 1,072 submissions. Both renderers together
allow at most 5,628 submissions. Compatible Direct reuse reduces new work. See
[analysis rules](benchmark-analysis-plan.md) for denominators, uncertainty and
source-group aggregation.

## 3. Operator-supplied interfaces

| Interface | What the operator supplies | Where it is used |
|---|---|---|
| `benchmark_data/benchmark.json` | Published source videos at the declared paths, with matching hashes | Shared source/request identity for all arms |
| `configs/experiment-campaign.json` | Frozen N, seeds, forms, online models, estimate-only budgets, maintenance | Main and self-review campaigns |
| `configs/*-campaign-host.local.json` | Device IDs, renderer paths, asset manifest/hash and model factories | One renderer's execution host |
| `configs/experiment-hosts.local.json` | Links to two local host files | Sequential two-renderer entry on one host |
| External credential file/environment | Provider key/base URL, or the supported subscription client configuration | Online clients and independent judges |
| `configs/evaluation.json` | Published independent judge identities and options | Final scoring, separate from online review |
| `--output` | New writable output root, with sufficient space | Frozen inputs, videos, private libraries, traces and scores |

The current judge identities are GLM-5.3-Flash and Sonnet-5.5/high through OpenRouter.
Online Planner/Critic use 6.1-sol/high. Copy the host examples and fill their deployment
fields; do not put keys in JSON. Model identity changes define a different experiment.
The API factory can be replaced with the documented
[subscription adapter](chatgpt-subscription.md) while keeping the declared role identities.

```bash
cp -n configs/bernini-campaign-host.example.json configs/bernini-campaign-host.local.json
cp -n configs/ditto-campaign-host.example.json configs/ditto-campaign-host.local.json
cp -n configs/experiment-hosts.example.json configs/experiment-hosts.local.json
```

Linked host-file paths are relative to the mapping file; renderer paths are relative
to the repository root or absolute on the execution host. The example device `[0]`
is a placeholder for your hardware. The campaign does not rent, create or stop GPUs.
Private local host files are ignored by Git.

### N GPUs on one host

Set `"devices": [0, 1, 2, 3]` in the host file, or use `--devices 0 1 2 3`
on `check` and `run`. `--devices auto` uses all devices visible to that process.
The campaign and lower-level `run_creative_benchmark.py` runner use the same
device selection and one host-local coordinator. Start one command, not one
copy of the campaign per card. Each selected card owns one resident renderer
and one task worker; no device has two concurrent render submissions.

All four main arms support independent tasks across N workers. Pre-experience
online and maintenance reads remain on the initial seed, even when another worker
has already contributed an increment. Only the brief append/result registration
operations serialize. Training increments accumulate without replacing the shared
corpus; test increments remain deferred. The coordinator waits for task and
maintenance settlements before freezing the full-experience input. Consequently,
increasing GPU count changes scheduling, not the experience visible to a task.

Candidate iterations within a task remain sequential. A worker performs that
task's API/maintenance work as well as rendering, so N GPUs provide up to N
concurrent task trajectories, not a promise of continuous 100% GPU utilization.
Per-task generation budgets stay at four. Provider limits can also constrain
throughput. `check` validates device syntax only; real launch resolves physical
GPU availability, visibility and duplicate index/UUID aliases.

The selected devices and scheduling dependencies are frozen when a batch starts.
Resume with the same host/selection. Historical sequential queues retain their
original task identities; a new implementation resumes their saved task manifest.

Put API credentials outside the checkout, for example `~/.config/lha/openrouter.env`:

```dotenv
OPENROUTER_API_KEY=REPLACE_WITH_YOUR_CALLING_KEY
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Set `LHA_API_ENV_FILE` to that file if using another location. Never pass credentials
as CLI arguments. See [configuration](benchmark-guide/configuration.md) for role
options and precedence. Real network/provider capability checks are separate from
the offline `check` command.

### Media and renderer assets

Obtain the benchmark media separately and place it at the paths in the manifest.
The source repository does not provide a public media download endpoint; consult
the [dataset provenance](../benchmark_data/README.md) and obtain the corresponding
release from its maintainer. Do not silently substitute videos or rewrite hashes.

Reuse a verified Bernini installation, or prepare the upstream renderer and pinned
weights in its compatible GPU environment. To fingerprint an existing installation:

```bash
python scripts/deploy/pin_bernini_runtime.py \
  --model-dir models/Bernini-R-1.3B-Diffusers \
  --code-dir third_party/Bernini \
  --model-revision YOUR_INSTALLED_MODEL_REVISION \
  --output configs/bernini-models-verified.json
```

Put the printed SHA256 in `renderer.asset_manifest_sha256`. This command hashes
existing files; it neither downloads nor initializes a renderer. Ditto's existing
pinned download/verification interface is:

```bash
python -m pip install huggingface_hub
python scripts/deploy/download_ditto_models.py \
  --spec configs/ditto_models.json --models-root models
python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('configs/ditto-models-verified.json').read_bytes()).hexdigest())"
```

The Ditto command can download large files. Run it only on the intended execution
host, with its required download dependencies. Set Ditto's `code_dir`, `models_root`
and manifest/hash in its host file. Use the renderer installation matching the code
revision in `configs/ditto_models.json`; keep its installed package versions with
the run. [Server runtime](server-runtime.md) describes the controller/worker boundary.
The lightweight controller install alone does not provision a rendering environment.
The older generation ZIP guide describes its own frozen tools, not these campaign commands.

## 4. Check without submitting work

```bash
python scripts/run_experiment_campaign.py check --backend bernini \
  --host-config configs/bernini-campaign-host.local.json
python scripts/run_experiment_campaign.py check --backend both \
  --host-config configs/experiment-hosts.local.json --verify-assets
```

`check` verifies the task matrix, source/prompt hashes, nonempty knowledge, online
exposure, declared model/profile settings and manifest identity. Without
`--verify-assets`, weight files are checked for existence/size; with it, their
contents are SHA256-checked as well. It writes no runtime, contacts no model,
queries no GPU and prints no credentials. Exit 0 means these offline checks passed;
exit 2 means operator inputs are missing or inconsistent. A fresh checkout without
the media/weights/host file is expected to report those missing inputs.

`scoring_modules_present` is informational: scoring may run on another machine.
Passing `check` does not establish provider availability, encoder cache availability,
CUDA compatibility, sufficient VRAM or disk capacity. Verify those on the actual
execution/scoring host before paid work. Never interpret placeholder model/asset
configurations as a successful live probe.

## 5. Run, resume and score explicitly

The following commands submit real work. Run them only after deployment checks.
Keep the original output root across software updates. Its saved manifests and
completed steps take precedence over current defaults. Code, knowledge, profile
and sampling differences are recorded as provenance; they do not create a new run.

```bash
# Main: pre-experience -> full-experience -> direct -> pe-loop -> independent score.
python scripts/run_experiment_campaign.py run --backend bernini --stage main \
  --host-config configs/bernini-campaign-host.local.json \
  --output out/formal/bernini --execute

# Self-review: its own pre-experience -> its own full-experience arm.
python scripts/run_experiment_campaign.py run --backend bernini --stage self-review \
  --host-config configs/bernini-campaign-host.local.json \
  --output out/formal/bernini --execute

# Score the added self-review results; reuse prior valid scores.
python scripts/run_experiment_campaign.py run --backend bernini --stage score \
  --output out/formal/bernini --execute

# Read last-recorded progress; does not resume jobs or establish process liveness.
python scripts/run_experiment_campaign.py status --backend bernini --output out/formal/bernini
```

For Ditto replace `bernini` with `ditto` in the backend, host filename and output.
On one host, `--backend both --host-config configs/experiment-hosts.local.json
--output out/formal` runs the two renderers sequentially in separate subdirectories.
Separate hosts run their single-backend commands. Main and self-review are separate
stage selections; `main` never implicitly includes the ablation.

Repeating the original command with the original output root resumes that experiment.
No resume flag or new run directory is needed. `check` and `status` include a read-only
recovery preview with method states, submitted/reserved renders and unresolved operations.
`run` checks ownership, reconciles durable receipts, and continues unfinished work:

| Interrupted work | What the same command reuses and continues |
|---|---|
| Direct / single-pass PE | The original prompt, seed, signed render request and completed video; a missing registry entry is rebuilt from its receipt |
| Direct cancelled at an old deadline, with no video | Keep its failed submission and used slot; resume the other pending tasks. Lifting the deadline does not regenerate this attempt |
| PE Loop | Completed refinement, render, review and selection phases; continue the first unfinished phase with the same four-submission allowance |
| Planner with Critic or self-review | The original task, knowledge binding, working notes, observations, candidates, pending answer/tool result and input ancestry; no task restart or budget reset |
| After the fourth render, before delivery | Continue observation/review/selection and confirmation; a saved Planner answer is replayed, and no fifth render is admitted |
| Task-post maintenance | Recover committed contributions and activation journals once; retry only an unfinished original call within its remaining transport allowance |
| Independent scoring / reports | Reuse each judge's valid output and cached automatic metrics; complete missing scoring and rebuild indexes/exports from the same results |

The four-attempt limit counts actual submitted renders, including definite failed
submissions. Recovery does not replenish it. The manifest's topics, methods, seeds,
knowledge, render settings and model settings also stay fixed. No additional topics
are admitted by restarting. Main `full-experience` depends on its own
`pre-experience` settlement; self-review retains its separate dependency and owner.

Inspect a Direct attempt without changing its queue, receipts or accounting:

```bash
python scripts/run_creative_benchmark.py recover-direct --output "$BATCH" \
  --device 0 --topic 046__short
```

`cancelled_without_output` means the signed response, hash-bound failed completion
and task-owned cancellation agree that execution stopped and released its resource,
and the attempt directory contains no MP4. The original submission remains counted.
Use the original run command to continue the remaining pending tasks. An additional
render for that cancelled position needs separate authorization and its own counted
attempt. `--receipt` still imports a completed response for the exact original request.

New uniform-117 tasks carry an explicit conditioning policy in their renderer request.
Historical native tasks keep their saved input and official frame selection, including
leading 117 frames of a 120-frame/24-fps source. Output dimensions alone do not opt a
historical request into whole-clip normalization.

An active coordinator or worker rejects a duplicate start. After stopping the old
workers, `--devices` may select different or fewer/more available GPUs. New tasks
live under `executions/<topic>/<method>`; a durable location index also reuses old
`workers/<device>` task directories. GPU reassignment does not create a new task.
For a node replacement, first fence the old node, preserve the complete output and
saved input assets, and mount them with the **same absolute paths** (including assets
and inputs). Host-local SQLite is not a distributed scheduler; do not run two hosts
against the same writable queue. Existing explicit disjoint shards remain separate.

An external submission with no conclusive receipt remains blocked. Process death
alone does not establish whether a provider finished a call. Exhausted/permanent
transport failures also retain their original allowance. Use the existing
[recovery procedures](server-runtime.md) for these recorded exceptions; do not delete
receipts or change identities to force another call. Historical code/protocols are
recorded alongside the current implementation. Original requests and receipts are
reused; upgrade differences do not authorize duplicate calls or new tasks.

To run the first stage now and continue full-experience later on the same host:

```bash
python scripts/run_experiment_campaign.py run --backend bernini --stage pre-experience \
  --host-config configs/bernini-campaign-host.local.json --devices 0 1 2 3 \
  --output out/formal/bernini --execute
python scripts/run_experiment_campaign.py run --backend bernini --stage full-experience \
  --host-config configs/bernini-campaign-host.local.json --devices 0 1 2 3 \
  --output out/formal/bernini --execute
```

The second command resolves `trained-experience.json` from this campaign's own
pre-experience stage, checks its settlements and ownership, and binds it read-only.
There is no manual snapshot flag or global experience toggle. A new output root
is a different campaign and does not silently search other runs for a library.
For self-review use its two named stages in the same root; it selects its own
`self-review-trained-experience.json`. The `main`/`all` commands already perform
these handoffs automatically. The lower-level preparation command defaults to
`pre-experience`; legacy `none` is available only when explicitly selected there.

### Independent evaluation

Install `requirements.evaluation.txt` on the scoring machine and prepare the pinned
encoder weights. Encoder dependencies are deliberately absent from the CPU smoke.
For an existing result registry, the generation host file is unnecessary:

```bash
python -m pip install -r requirements.evaluation.txt
python scripts/benchmark_results.py score-evaluation \
  --root out/formal/bernini/results --execute
```

The command creates the current evaluation identity, adds collected videos, computes
automatic metrics, calls both independent judges, performs anonymous order-swapped
comparisons and writes reports. It can run after generation. Repeating the command
retains its evaluation identity and completed scores after code/profile changes.
Missing steps use their saved requests and scoring material where present; their
actual protocol remains recorded. Deliberate rescoring requires an explicit
`prepare-evaluation --evaluation-id NEW_ID`; ordinary restart never invokes it. A copied registry must
retain all media and frozen metadata. If source media paths change, relocate the
checkout consistently before scoring.

Report the two judges separately. The five v5 scores, short/long task metrics,
automatic diagnostics, unknown/not-applicable coverage and actual cost remain
distinct. Evaluate Direct and each trajectory's first, last and selected video;
identical content reuses its scores. Final judgments never feed online planning or
training maintenance. Detailed protocol: [independent evaluation](low-high-evaluation-v2.md).

## 6. Retain and share results

Keep each campaign's configuration, host identity (without secrets), initial/frozen
experience, batch/profile manifests, model inputs/responses, actual prompts,
candidate ancestry, reviews, maintenance contributions, settlements and accounting.
The `results/` registry contains content-addressed media, imported entries,
evaluation receipts, `results.json` and `index.html`. Campaign scoring additionally
writes the Critic family's held-out `rsi.json`/`rsi.html`; the overall report also
retains self-review and cross-reviewer comparisons.

Copy complete output trees when archiving, verify file hashes, and preserve the
code commit and installed dependency versions. Source publication excludes private
credentials, weights, full runtime logs and generated results. Software-smoke
artifacts and experimental measurements use separate output roots throughout.


For a standalone Planner run, the original `run_planner_harness.py` command also
resumes automatically when its output contains `state.json`; adding `--resume`
is optional. Saved model configuration, instructions, pending work and generation
occupancy win over updated profile defaults. A completed task needs no new provider
client. Upgrade details and offline evidence are recorded in
[the continuation plan](upgrade-continuation-plan.md).
