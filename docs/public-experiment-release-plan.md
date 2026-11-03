# Public experiment entry points and offline smoke verification

Status: implementation and offline verification complete; GitHub synchronization follows.
No live experiment is authorized by this work.

## Scope

Publish a usable handoff for researchers running the existing main experiment and
self-review ablation on their own infrastructure. Keep the four-attempt design,
private experience families, reviewed knowledge and scoring standards unchanged.
Deployment files and credentials belong to the operator; their absence on the
development workstation is not a missing experiment mechanism.

## Work

- [x] Add a read-only campaign `check` command for dataset integrity, knowledge
  availability, declared host/model settings and optional asset verification.
  Report missing operator inputs without importing a renderer or contacting a model.
- [x] Document the public interfaces, environment setup, main/self-review/score
  commands, resume and result retrieval. Distinguish private configuration from
  published defaults and real provider checks from offline validation.
- [x] Provide one CPU-only smoke command using synthetic media and scripted
  responses. Exercise fixed-budget delivery, both review modes, private maintenance,
  freeze/read-only use, registry, independent scoring, comparisons and recovery.
  Block external network and GPU/model libraries. Retain machine-readable coverage
  and logs; label every synthetic result as software verification.
- [x] Test public entry points and documented commands, then run the relevant
  regression modules. Record failures and limits without changing experimental
  policy to make tests pass.
- [ ] Commit scoped changes, push the existing GitHub branch and verify its commit.

## Completion

A fresh source checkout can run the smoke command without benchmark videos,
weights, credentials, torch or a GPU. An operator can prepare their own deployment
from the public guide and run each existing experimental stage explicitly.
The smoke is evidence about software paths and contracts, not API availability,
CUDA compatibility, model quality or a completed research experiment.

## Verification, 2026-11-03

- The public smoke passed all 97 tests across nine integration modules in a clean
  source checkout with no benchmark videos, weights or private host configuration.
  Network calls and model/GPU imports were blocked in workers and Python children.
- The retained example runs four Planner trajectories (full/none x Critic/self-review),
  each with four synthetic submissions and an early-candidate selection. It executes
  post-task private maintenance, campaign freeze, read-only full use, registration,
  two scripted final judges, blind comparisons and score-cache reuse. Direct is a
  synthetic registry input; PE orchestration and both renderer adapters have their
  own integration cases in the same smoke command.
- The first development run exposed two fixture wiring problems: the none arm was
  given a full snapshot, and guarded model-module discovery raised ImportError.
  Both were fixed. The initial failures remain recorded; the final guarded run passed.
- Source ZIP exports omit knowledge images under existing redistribution attributes.
  The guide requires git clone. The clean smoke checkout restored tracked knowledge
  assets from Git, retained no benchmark videos, and used system ffmpeg instead of
  a platform-specific historical binary symlink. Publication filters were unchanged.
- All seven touched/new navigation documents have valid local file links. The
  retained example HTML has 13 local/media links, all resolving after export.
- The real local `check` reports 201 matching dataset files, 21 seed entries,
  isolated none access, both configured judges, and the absent operator host input.
  It makes no model call or GPU submission and prepares no batch.
- Evidence: `out/public_release_20261103/source-checkout.json`,
  `out/public_release_20261103/smoke-clone-equivalent/smoke.json` and its
  `tests/summary.json`, per-module logs and synthetic `example/`.
- Experience prose, experiment budgets/groups and scoring standards are unchanged.
  Live provider access, GPU environments and quality measurements remain the
  receiving operator's deployment verification, separate from this smoke.
