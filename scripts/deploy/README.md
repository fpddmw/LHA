# OpenBayes runtime

## RTX PRO 6000 and direct prompt exploration (2026-10-29)

The current 96 GB Blackwell instance inherits the persistent locations below.
The direct probe uses the revised `benchmark_data/` (50 main + 7 fewshot clips),
saved prompts, and the official Bernini renderer. Its commands do not invoke
the existing planner or agent loop. Keep its outputs in a separate run directory.

```bash
cd /openbayes/home/LHA
proxy-on
bash scripts/deploy/setup_openbayes.sh
bash scripts/deploy/setup_blackwell.sh
source scripts/deploy/env_openbayes.sh
bash scripts/deploy/prepare_ditto.sh
HF_HUB_DISABLE_XET=1 python scripts/deploy/download_ditto_models.py \
  --spec configs/ditto_models.json
```

Setup selects CUDA 12.8 for Blackwell and CUDA 12.6 for older GPUs, with
`LHA_TORCH_FLAVOR` as an explicit override. The Blackwell check runs CUDA and
FlashAttention kernels. Python, installed packages, caches, source clips, model
weights and outputs remain under `/openbayes/home`; restarting the same workspace
reuses them. System packages such as FFmpeg are restored by setup when missing.

Ditto uses the pinned official code and `Wan-AI/Wan2.1-VACE-14B` with the public
`ditto_global.safetensors`, specified in `configs/ditto_models.json`. The selected
weights and tokenizer total about 75.4 GB. Downloads resume partial files and
verify published weight hashes, writing `ditto-models-verified.json` beside the
chosen spec. The 200 GB workspace has to accommodate the inherited Bernini data,
both models and package caches; the shared filesystem's `df` capacity is not the
workspace quota. Resolved environment versions are recorded in
`out/deployment/blackwell/requirements-with-ditto.txt`.

The prepared probe manifest is `out/prompt_probe/20261029_bernini/cases.json`:

```bash
python scripts/deploy/run_prompt_probe.py \
  --manifest out/prompt_probe/20261029_bernini/cases.json
python scripts/deploy/judge_prompt_probe.py \
  --manifest out/prompt_probe/20261029_bernini/cases.json
python scripts/deploy/render_prompt_probe_report.py \
  --manifest out/prompt_probe/20261029_bernini/cases.json
```

The runner checks source hashes, prompt token counts, frame count, frame rate and
output hashes. Completed matching cases are reused. Formal clips generate 101
frames at 20 fps and deliver their first 100 frames (5 seconds). The upstream
sampler uniformly selects 133 of the table-tennis clip's 134 frames to meet its
4n+1 frame requirement, and exports at the source's 30 fps (4.433 vs 4.467 seconds).
`frame-mapping-audit.json` in this run records the actual conditioning-frame map.
The exploratory judge uses GPT-6.1-sol/xhigh via the saved subscription login,
with 12 sampled frames from each video, and reports style, preservation and
unjudgeable items separately. The original full-clip sampling has at most a
one-frame source offset for the trimmed formal clips; the table-tennis samples
align with the upstream conditioning-frame map. Full videos and explicit frame
alignment remain necessary for exact motion review.

After the Bernini GPU process exits and all Ditto weights are verified, check
actual Ditto inference with:

```bash
python scripts/deploy/verify_ditto_runtime.py \
  --verified-manifest configs/ditto-models-verified.json \
  --output-dir out/deployment/blackwell/ditto-smoke
```

Use the actual verification-manifest path if the download spec was in a run
directory. This check loads the full model and LoRA but generates only 13 frames
with 2 diffusion steps at 448×256. Its output is a runtime check, not a video
quality result. Download/import completion and successful inference are recorded
separately. Run only one video-generation process on this GPU at a time.

Verified on the RTX PRO 6000 on 2026-10-29: all 16 selected model files
(75,388,794,751 bytes) passed size/hash verification. The full Ditto runtime
check completed with torch 2.7.1+cu128, applied LoRA to 80 tensors, generated and
decoded all 13 requested frames, and used a peak 35.30 GB of allocated GPU memory
at the smoke settings. See `out/deployment/blackwell/ditto-smoke/runtime-check.json`.
The direct Bernini probe produced all 10 outputs; decoded output counts and
transfer hashes are in the run's `local-output-verification.json`.

## Earlier 4090 integration

This deployment uses Bernini-R-1.3B for video editing and GPT-6.1-sol / xhigh for
both the planner and critic. Each hosted call has its own context and role prompt.
The critic's visual evaluator uses GPT; the reflection/routing stage keeps the
repository's existing rules when no trained local reflector checkpoint is present.

Persistent locations:

- Project: `/openbayes/home/LHA`
- Python, environment, package cache and Codex CLI: `/openbayes/home/.lha-runtime`
- Model: `LHA/models/Bernini-R-1.3B-Diffusers`
- Private Codex login cache: `/openbayes/home/.codex` (outside the project)

## Install or restore after restarting the container

In an interactive SSH shell:

```bash
cd /openbayes/home/LHA
proxy-on
bash scripts/deploy/setup_openbayes.sh
source scripts/deploy/env_openbayes.sh
python scripts/deploy/probe_vlm.py
```

The setup uses Python 3.11.14, torch 2.7.1, the version pins in
`requirements.openbayes.txt`, VeOmni v0.1.11 (pinned commit), and the official
FlashAttention 2.8.3 wheel matching Python 3.11 / torch 2.7 / CUDA 12. The vendored
Bernini code imports full-model attention utilities even on its renderer path,
so FlashAttention is installed without a local CUDA compilation.
The model downloader pins its revision and resumes partial downloads. Download
completion is recorded in the model's `download-manifest.json`. The installed
package versions are saved to `out/deployment/installed-requirements.txt`.

The platform proxy is needed for this instance's ChatGPT connection and official
Hugging Face downloads. Set `HF_ENDPOINT=https://hf-mirror.com` if a mirror is
needed. Downloads keep partial files and retry interrupted transfers.

If the server's download connection remains unstable, `download_via_ssh.py` can
fetch the same pinned files on another computer and upload them. It verifies the
published weight hashes and the SHA-256 of each uploaded file, and reuses matching
files already on the server. Install `huggingface-hub==0.35.1`, `hf-xet==1.7.0` and
`paramiko` locally, then run (the password is prompted interactively):

```bash
python scripts/deploy/download_via_ssh.py --host ssh.openbayes.com --port 32299 \
  --cache /tmp/lha-model-download --manifest out/model-transfer.json
```

Confirm the SSH host key before using the fallback. After a completed download,
the setup script reuses the pinned model from its local manifest without a network
request. Keep the model's configuration files and tokenizer alongside its weights.

## Run the full loop

```bash
LHA_RUN_DIR=out/openbayes_e2e/my_run bash scripts/deploy/run_e2e.sh
python scripts/deploy/verify_e2e.py out/openbayes_e2e/my_run
```

The initial integration profile uses smoke sample 2, 17 frames, 20 fps and at most
two attempts. Bernini uses 40 diffusion steps before any existing memory controls.
Set `LHA_SAMPLE_ID`, `LHA_MAX_ATTEMPTS`, `LOW_HIGH_BENCH_NUM_FRAMES`, or
`LOW_HIGH_BENCH_FPS` to change those choices. Use a fresh `LHA_RUN_DIR` for each run.
For another source and prompt:

```bash
LHA_RUN_DIR=out/openbayes_e2e/custom bash scripts/deploy/run_e2e.sh \
  --low-video /absolute/path/input.mp4 --prompt-file /absolute/path/prompt.txt
```

Each run saves planner state, generated videos, critic scores, reflection,
attempt trace, run-specific memory and hosted model call metadata. `verification.json`
is written only after the verification script succeeds. It distinguishes
`accepted` from `max_attempts_reached`; a completed workflow does not by itself
mean that the generated video met the critic's quality target. The renderer can
preserve the input aspect ratio, so output metadata is measured from the actual file.

## Authentication and optional gateway

The Codex backend uses the CLI's saved ChatGPT login. If it expires, authenticate
with `codex login --device-auth`, or use the official documented SSH transfer of
your own login cache. Keep the cache private and outside the repository.
Transport failures are retried up to three attempts with increasing delays;
authentication and quota failures are reported immediately. Adjust
`LOW_HIGH_AGENT_CODEX_ATTEMPTS` or `LOW_HIGH_AGENT_CODEX_TIMEOUT` if needed.

To use an OpenAI-compatible gateway, create a private `.env.openbayes` (ignored by
Git; keep it out of any source archives):

```bash
LOW_HIGH_AGENT_VLM_BACKEND=litellm
LOW_HIGH_JUDGE_BASE_URL=https://YOUR_GATEWAY/v1
LOW_HIGH_JUDGE_API_KEY=YOUR_KEY
LOW_HIGH_AGENT_LITELLM_MODEL=gpt-6.1-sol
LOW_HIGH_AGENT_LITELLM_REASONING_EFFORT=xhigh
```

Apply `chmod 600 .env.openbayes`. The gateway must support vision input and the
requested model. There is no automatic switch to a local Qwen model on failures.

Official authentication reference: https://learn.chatgpt.com/docs/auth

## Verified on this instance (2026-10-28)

Run `out/openbayes_e2e/20261028T0953Z` completed two real Bernini generations and
11 subscription calls across the planner and critic. Both videos decode fully:
640 x 368, 17 frames, 20 fps. Critic scores were 0.52 and 0.49; the loop stopped at
its configured attempt limit. The workflow passed integration verification; this
short-clip run does not establish video quality or full-length performance.

Inspect `verification.json`, `loop/loop.result.json`, the per-attempt videos and
responses, and `memory.json` under that run. During review, a pre-existing hold
parser bug was fixed: a bare `HELD` row could consume the following dimension.
The original run is preserved as executed. A fresh critic evaluation of the first
video and replay through the existing memory tool are saved in `critic_recheck/`;
`parser-fix-verification.json` confirms all four hold rows and the propagated props
violation. The regression suite passes 9/9. These recheck artifacts are separate
from the original two-round trace and its scores.
