# Model-led Planner harness implementation

Approved: 2026-10-29. The user authorized saving this plan, implementing the new Planner harness, and running real tasks with inspectable observation, reading, design, and English prompt records. Generation feedback and the post-generation loop are a subsequent phase.

## Objective and design

Build an independent planning path in which the model understands the source video and request, chooses observation and knowledge operations, develops and revises its own proposal, and submits an English execution prompt. The existing knowledge map, guides, complete entries, and conditional model experience supply readable material. The model controls interpretation, reading depth, creative decisions, and task-workspace organization.

Video understanding covers visible events, relationships, temporal development, and uncertainty. Semantic-preservation prompting remains deferred. The harness implements reliable access, durable state, operation validation, context accounting, recovery, and inspectable outputs. It does not impose aesthetic defaults, mandatory style categories, fixed design dimensions, reading quotas, or candidate counts.

## Implementation sequence

1. Add a separate Planner package and command with explicit model/backend configuration. Reuse the existing model transports while maintaining the full planning conversation and durable task state in the harness. Keep the original Planner available for historical reproduction.
2. Implement timestamped video overview and targeted observation; knowledge browse, search, complete/section reads, and provenance access; revisable task notes and model-organized question nodes; and final submission. Return actual source passages and explicit pagination. Preserve tool calls, results, images, source hashes, and proposal versions.
3. Provide concise English operational guidance using the current reading manual. Keep the request, current working state, unresolved questions, and source references available. Validate citations, submission shape, and known execution limits; return problems for model correction. Surface interruption, budget exhaustion, and transport failure without silently substituting a template or truncating a prompt.
4. Add focused checks for tool access, citations, continuation, error handling, and submitted-text integrity. Run real planning on benchmark main/041 and fewshot/004, followed by a composition request and a narrow edit outside the application examples. The first two are known integration examples, not independent evidence of generalization or video improvement.
5. Deliver readable run reports showing frames actually supplied, knowledge actually returned, the model's visible decisions and revisions, final design, and exact English prompt. Record the difference between a planning handoff and a renderer submission. The user's latest clarification limits this phase to Planner validation: do not start video generation on Bernini or Ditto, and do not connect the post-generation loop.

## Scope and implementation locations

- New runtime: `src/planner_harness/` and a separate command under `scripts/`.
- Model connection: reuse existing Codex subscription / compatible API transports, defaulting to GPT-6.1-sol with xhigh reasoning, with only necessary adapter/import changes.
- Reproducible lightweight environment: dedicated Planner requirements and setup instructions, independent of GPU generation dependencies.
- Run artifacts: `out/planner_harness/`, with source request, state, event records, delivered observations, actual model inputs/outputs, proposal, prompt, and readable report.
- Documentation: this plan and a usage/architecture account linked from the existing knowledge integration document.

All new repository prose, operational guidance, code comments, and working artifacts use English. Original user wording remains an attributed input. Existing experiment outputs and source knowledge remain intact. Planner validation runs locally without GPU generation or SSH access. The user briefly suggested H800/Ditto validation and then explicitly deferred generation; the latest instruction governs this phase.

## Completion evidence

Completion requires a runnable, recoverable harness and actual model-driven planning records. Reports distinguish observed source evidence, retrieved material, model-authored choices, deterministic checks, and untested assumptions. Content checks and successful planning establish working capability; generated-video improvement requires separate evidence.

## Status

Plan saved before implementation. The independent harness and command are implemented. Eleven focused reliability checks passed, with the Windows/WSL lock adjustment separately rechecked. Four actual GPT-6.1-sol/xhigh planning runs completed on three source clips, totaling ten model calls. Every run passed record verification against its actual source reads, image attachments, model responses, citations, and unchanged prompt handoff.

The [walkthrough review](../out/planner_harness/20261029/review.md) and [interactive report index](../out/planner_harness/20261029/index.html) show all four tasks. The [usage account](planner-harness.md) explains execution, continuation, context handling, and boundaries. All four live runs used the initial six-frame overview. No GPU generation, renderer submission, or post-generation loop was started, following the user's latest clarification.
