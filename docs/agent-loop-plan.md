> Superseded by the user-reviewed [continuous Planner and experience plan](planner-loop-experience-plan.md). The external decision stage and per-round child Planner described below are historical.

# Outer agent loop implementation plan

Date: 2026-10-29. The user asked to assemble the surrounding harness and agent loop now that the independent Planner works. A separate session owns evaluation-metric design. The previous restriction on starting video generation remains in effect for this implementation check.

## Current baseline

The independent Planner can inspect the original video, read the knowledge library, organize its own workspace, and submit a recorded English proposal. Four live planning walkthroughs are available. The legacy loop still imports the legacy Planner and modifies prompts and generation controls through its own reflection and memory logic. The Bernini loop-probe controller is a separate experiment, with its own task definitions and route comparison. Neither is the production integration of the new Planner.

## Bounded implementation

1. Add `src/agent_loop/` and a separate command. Adopt a completed Planner run without changing it. Save immutable proposal versions, original source identity, generation input ancestry, exact requested prompts, execution receipts, evaluations, and decisions. Maintain an explicit incumbent and a candidate budget.
2. Provide durable file-based jobs for renderer, evaluator, and selection-policy adapters. An adapter consumes a request and atomically supplies a response bound to its request hash. Repeated advances reuse the same request; unresolved jobs remain pending. Validate decoded output and the renderer's execution receipt. Never silently add prompt text, adjust sampling controls, replace missing evaluations with scores, or mark a candidate accepted merely because generation finished.
3. Keep evaluation and selection separate. Preserve the external evaluator's protocol/version, structured findings, evidence, uncertainty, and arbitrary metric payload. Decisions identify their policy/version, comparison basis, acceptance choice, and next action. No metric names, weights, aesthetic threshold, or universal preservation recipe are fixed here.
4. Add a revision entry to the existing model-led Planner. Supply the immutable original, evaluated candidate, incumbent, earlier design and execution input, feedback and decision as attributed context. Permit observation of each supplied video and reuse of all knowledge operations. Write a new child planning run; keep earlier runs intact. The selected renderer input and full/incremental instruction mode are explicit. Source restart and editing an accepted candidate remain available; route superiority is not assumed.
5. Validate orchestration locally with clearly labeled scripted/replayed responses, including missing evaluation, failed jobs, stale responses, candidate rejection, source restart, accepted-parent editing, budget stop, and recovery. Include an inspectable walkthrough based on the existing 041 planning handoff, with synthetic/replayed transitions explicitly distinguished from new model calls and video generation.

## Responsibilities and boundary

The Planner owns creative interpretation and revision. The outer harness owns reliable state, input identity, budgets, tool access and scheduling. The renderer adapter owns actual tokenizer/configuration preflight and generation. The evaluation session supplies metrics and evidence procedures. A separately versioned decision policy selects candidates and routes; it may be human-authored or automated once available.

This phase delivers a runnable outer controller and Planner revision connection. Live GPU worker deployment, a finalized evaluator/selection policy, and empirical evidence of video improvement remain subsequent integrations. No new GPU job or automatic knowledge-library writeback is performed. Existing experiment scripts and results remain intact. All new repository prose is English.

## Status

Plan saved before implementation. The outer controller, CLI, adapter contract, child Planner revision entry and readable run records are implemented. Twelve focused outer-loop checks and all eleven existing Planner checks passed. A saved 041 planning handoff and archived Bernini video were used for an inspectable two-candidate replay: scripted acceptance, source restart, child-plan continuation, scripted rejection and incumbent retention. The replay used zero new model inferences and zero new video generations. It deliberately reused an archived video produced by a different prompt and labels that mismatch throughout. See the [implementation account](agent-loop.md) and [replay record](../out/agent_loop/20261029_041_replay/report.md). Live GPU workers and the separately owned evaluation/selection policy remain to be connected.
