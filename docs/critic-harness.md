# Active online Critic

The implementation is `src/critic_harness/`. It is explicitly enabled and does not replace `src/evaluation/` or the legacy Critic. Formal benchmark cards, scores and running evaluation jobs retain their own protocol. The online Critic uses English, observes existing media and returns grounded feedback to a model-led Planner.

## Responsibilities

The Critic chooses observations and reads, distinguishes task outcomes from process diagnostics, and explains strengths, defects, tradeoffs and unknowns. The Planner chooses the next input, prompt, operation or stopping point. The runtime resolves provenance, verifies evidence references and handles durable jobs. No Critic score selects a route or overwrites a candidate.

Its inputs are the original request/source, candidate, actual input and an optional alternative. A candidate's immediate parent is distinct from a comparison candidate. The original source anchors preservation, even if an intermediate input already contains damage. Other ancestors remain recorded provenance.

## Operating guidance and evidence

`OPERATIONS.md` is the short tool and evidence contract. `guides/judgment.md` explains task-specific partial attainment, style latitude, semantic roles, object binding, inherited defects and aesthetic interpretation. `guides/evidence.md` explains sparse versus continuous observation, crops, motion questions and calibration. The guides are labeled initial guidance; they are not measured guarantees. The Critic also has read-only access to the existing knowledge map, topics and full sources through a run snapshot.

Available operations: `observe`, `guide`, `browse`, `search`, `read`, `note`, `assess`, `process_context`, `finish`. The model decides which ones are useful. Outcome assessment is recorded before access to the actual execution prompts. Process diagnosis can then discuss missing instructions, optional choices and uncertain causal explanations without rewriting the original task.

Observations use PyAV native PTS. Sparse observations contain 2-12 frames per video. Dense observations return every frame in the selected interval, capped at 24 frames per video per operation with explicit `next_start` pagination. Up to four videos can be compared. Crops retain their normalized coordinates and video identities. No tail padding is performed. All images, timestamps and hashes are recorded. Native temporal evidence availability is checked; correctness of the model's visual interpretation requires calibration.

Each determined finding cites actual candidate evidence. Preservation findings additionally cite original-source evidence. Determined continuous claims declare videos, interval and spatial scope; the runtime rejects insufficient continuous coverage. Whole-clip temporal scores require full-frame coverage of the entire task interval. Unknown remains available after inspection. Partial judgments state the specific fulfilled/unfulfilled boundary. Optional 1-4 decimal ratings are descriptive online feedback, not a replacement for the frozen benchmark metric table.

Each inference call receives the original overviews and latest observation images. When changing views, the model can attach a brief `observation_note` to its next operation; the runtime records the current observation ID and carries the description forward. This is visible evidence memory rather than private reasoning. Earlier images remain available for reinspection. An initial live run exposed repeated overview/crop switching when only the latest images were attached and no visual findings were carried forward; the revised path preserves both overview context and attributed notes. The unsuccessful initial trace remains available for inspection.

## Standalone review

Create a JSON spec with `request`, `candidate`, `duration_seconds`, optional `question`, and `videos`. Each video contains `path`, optional verified `sha256`, known `parent`, exact `prompt` and provenance. Use ID `source` for the original. Parents must be available in a standalone review; record unavailable ancestry separately rather than inventing it.

```json
{"request":"Make it look like a children's storybook.","candidate":"candidate","duration_seconds":5,
 "videos":{"source":{"path":"benchmark_data/main/041/041.mp4"},
 "input":{"path":"existing-first-edit.mp4","parent":"source","prompt":"Actual first prompt"},
 "candidate":{"path":"existing-second-edit.mp4","parent":"input","prompt":"Actual second prompt"}}}
```

```bash
python scripts/run_critic_harness.py --spec review.json --output out/critic/run01
python scripts/run_critic_harness.py --output out/critic/run01 --resume --additional-turns 4
```

Use the existing model-client environment and install `requirements.critic.txt`. It selects PyAV 19.0.2 on Python 3.12 or later, and PyAV 15.1.0 for the existing Python 3.11 Bernini deployment. The exact runtime version is retained with each deployment and its validation results. No GPU evaluator or renderer is required. The backend is the existing `CodexVisionModel`, configured with role `online_critic`; default model is GPT-6.1-sol with xhigh reasoning. Environment overrides use the existing VLM configuration. Exact inputs, raw responses, observation records, frozen instructions and knowledge snapshot are saved. `report.html` links videos, images and every operation. `feedback.json` is signed and explicitly labeled online feedback.

## Planner integration

Enable it in the execution profile:

```json
{"critic":{"max_turns":18,"duration_seconds":5}}
```

The Planner then sees a concise additional operating section and can call:

```json
{"action":"critique","arguments":{"video":"v3","compare_to":"v1","question":"Did edge placement improve, and which successful effects remain?"}}
```

`execution.py` builds a signed job using the actual candidate and parent. `run_planner_worker.py` dispatches this job to the active Critic; `evaluate` retains the existing formal-evaluator adapter and is unchanged. The result returns through the same durable collection/resumption path. Pending generation/evaluation jobs and frozen instructions of existing tasks are unaffected.

Existing feedback can be imported at task creation with `--critic-feedback PATH` (repeatable). Import verifies original source/request, video hashes, report signature and evidence image hashes, and maps review IDs to task IDs. Imported videos can carry actual `parent`, `prompt` and `time_mapping`; import the parent before its child. The Planner may inspect evidence, read experience, propose an edit, choose an earlier result or finish.

## Demonstration and limits

`scripts/demo_critic_existing.py --directory out/critic_harness/20261030` uses the prepared 041 and table-tennis specs. It performs real Critic and Planner calls sequentially. Generation proposals are left as pending signed requests; no renderer is dispatched. Reports make that boundary explicit. Existing video prompts remain historical provenance.

The revised validation uses `out/critic_harness/20261030_v2` and `--runtime-source out/critic_harness/20261030_v2/runtime/src`. Its source imports, operating material and knowledge snapshots are pinned separately from ongoing development. The earlier directory records the visual-memory failure and the Planner's request for a broader review; it is not presented as a completed full evaluation.

Focused tests: `python scripts/test_critic_harness.py`. Additional compatibility checks use the existing continuous-Planner and worker suites. Synthetic test fixtures are not experimental judgments. The live demonstration establishes actual feedback use; it does not measure downstream video improvement or replace independent visual calibration. New empirical skill updates remain separately reviewed.
