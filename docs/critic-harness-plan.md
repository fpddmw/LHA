# Active Critic implementation plan

Approved scope: 2026-10-30. Implement the combined Critic design and evaluation refinements, then demonstrate the complete evidence-to-feedback-to-Planner path on existing 041 and table-tennis videos. Working language is English.

## Purpose and responsibilities

The Critic observes, compares and diagnoses. The Planner chooses a design, input video, next operation and stopping point. The runtime supplies media, ancestry, knowledge and durable records. No score threshold selects a creative route. The original source and user request remain the outcome reference, including when editing an imperfect intermediate candidate.

Three comparisons have different meanings: candidate versus original task; candidate versus its actual input; candidate versus an alternative. Inherited defects and new regressions remain distinguishable. User requirements, optional Planner choices and hypotheses about failure causes remain distinguishable.

## Implementation boundary

- Add an independent `src/critic_harness/` with a short operating manual, focused evaluation guidance, PTS-based overview/crop/continuous-interval observation, read-only knowledge access, feedback validation and an inspectable report.
- Provide a standalone CLI and an opt-in Planner worker adapter. Existing evaluation jobs keep their current path unless explicitly configured for the new Critic. Existing Planner runs retain their frozen instructions.
- Reuse shared knowledge through a run snapshot. Evaluation guidance is separately versioned; source examples inform interpretation without becoming mandatory aesthetic targets.
- Preserve `src/evaluation/`, frozen cards, formal judge prompts, formal run directories and running processes. No GPU generation is part of this validation. New demonstration runs have separate directories.
- Existing formal metrics remain available through their existing evaluator. The online Critic reports grounded task judgments, quality dimensions when supported, explicit unknowns and comparison evidence. Its feedback is not relabeled as independent benchmark scoring.

## Evaluation refinements

1. Bind requirements to objects, attributes, locations and relevant intervals. Define partial success for the actual requirement rather than using a generic partial rule. Keep core semantics and incidental detail distinct.
2. Permit authorized style transformations. A short style request does not inherit the details of a long request or a Planner's optional design. Distinguish simplification, occlusion, object changes and unresolved visibility.
3. Separate preserved source actions from output flicker, structural instability and motion plausibility. Small source motion is not a defect. Continuous claims cite sufficient intervals; local crops support only their inspected scope.
4. Keep style attainment, aesthetic coordination and scene-specific design distinct. Decimal scores remain descriptive; tiny differences do not establish improvement. Relative originality needs a fixed comparison set and is not a routine repair objective.
5. Identify observable effects first. Consult the actual execution prompt only for process diagnosis after an outcome assessment has been recorded. Cause hypotheses are explicitly uncertain.
6. Give the Planner strengths, remaining problems, comparison tradeoffs and useful unresolved questions, without prescribing the next input or rewriting the prompt.

## Tools and records

The Critic can inspect one or more available videos using overview frames or all native frames in a bounded interval, with optional normalized crops. Each observation records true timestamps, frame indices, image hashes, video identity, crop and evidence scope. Continuous evidence remains separate from sparse samples. It can browse/search/read frozen knowledge, consult its evaluation guidance, record an outcome assessment, inspect process context, and finish a feedback report. These are capabilities rather than a mandatory reading sequence.

Every model call, returned tool action, evidence image and final feedback is saved. Run resumption verifies immutable inputs, source material and instructions. Runtime checks protect evidence references and scope; they do not decide visual labels. Unknowns remain when evidence or capacity is insufficient.

## Planner integration and demonstration

The opt-in `critique(video, compare_to?, question?)` operation resolves actual ancestry from task records. Completed feedback returns through the existing durable tool result mechanism. A standalone review can also be imported into a new Planner task after verifying original request/source and candidate hashes.

Use existing 041 storybook and table-tennis station videos with exact original requirements and recorded prompts/parents. For each, show original and candidate media, requested review question, actual observations and knowledge reads, outcome assessment, optional process diagnosis, final feedback and a real Planner continuation. Stop before dispatching any requested generation; present the model-selected input and exact English prompt or its decision to inspect/finish. A demonstration of information use does not establish that the next edit improves the video.

## Verification and completion

- Focused tests for PTS/crop evidence, continuous coverage limits, evidence references, prompt isolation, ancestry/comparison distinction, resume integrity, opt-in routing and feedback import.
- Run existing relevant Planner/worker tests to check compatibility.
- Record protected evaluation-file hashes before and after; attribute concurrent external changes rather than overwrite them.
- Run real model reviews sequentially to limit contention with the separate formal evaluator. Preserve failed attempts and uncertainty. Review actual evidence for important claims; keep original model reports intact.
- Deliver a combined report linking media, observation trace, guidance/knowledge reads, feedback and Planner decisions. State supported conclusions and remaining calibration limitations. No automatic publication of new empirical skill rules.
