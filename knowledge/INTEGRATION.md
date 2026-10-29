# Connecting a new Planner and harness

[Knowledge map](README.md) · [Reading manual](READING.md) · [Approved scope](../docs/skill-reorganization-plan.md)

The independent Planner harness has been implemented and exercised on four actual planning tasks under the [approved runtime plan](../docs/planner-harness-plan.md). Its [usage and architecture account](../docs/planner-harness.md) describes the implemented tools, durable workspace, model connection, and inspectable planning outputs. The [live walkthrough review](../out/planner_harness/20261029/review.md) links actual observations, knowledge reads, proposals, and exact prompts. The [outer agent loop](../docs/agent-loop.md) now adds durable renderer/evaluator/decision jobs, candidate management and child Planner revision with feedback. It has local replay validation; live worker deployment and the separately developed evaluation/selection policy remain pending. The design below remains the architectural basis.

## Responsibilities and current status

| Component | Responsibility | Current status |
|---|---|---|
| Long-term knowledge | Map, guides, complete material, domain references, and source relationships | Available in `knowledge/` |
| Reading manual | Explain layers, discovery, comparison, and source status | Available in `READING.md` |
| Planner model | Understand the video and request, ask questions, explore knowledge, compare directions, and form a proposal | Independent runtime implemented; four actual planning tasks completed |
| Harness | Provide observation, browsing, and search tools; retain working material and execution boundaries; record actual calls | Independent operation loop, tools, durable state, and run records implemented |
| Prompt delivery | Express the selected design in inputs supported by the video model and expose actual submitted content | Exact prompt handoff implemented; renderer preflight and generation remain pending |
| Generation and evaluation loop | Improve proposals using actual results and feedback, retaining each iteration and its evidence | Outer controller and Planner revision implemented and replay-tested; live adapters and evaluation policy pending |

The interface supports the new model-led Planner independently of the old style classifications, keyword dimensions, template rankings, and fixed call stages. The corpus directory is a reading structure, and the model chooses its exploration order.

## Working language across the interface

English is the language of knowledge tools, operational guidance, visible workspace notes, design proposals, and prompt drafts. Original requests and source records retain their provenance and original wording; the model can maintain an English interpretation alongside a request in another language. User-facing conversation follows the user's language preference.

Tools should identify whether content is an English original, an English translation, editorial analysis, or a historical experimental input. The independent harness carries this convention through operational guidance, tool responses, and persisted task material. Working notes and final planning output are checked for Chinese text; original task wording remains source data.

## Minimal reading capabilities

The initial tool wrappers can use the current files and `source-map.json` directly. Full-text search is sufficient to start; a vector store or large database is optional.

| Capability | Input | Return | Purpose |
|---|---|---|---|
| Browse an entrance | Map, guide, or material ID | Substantive introduction, readable links, and comparison reasons | Understand the question space and differences among sources |
| Search knowledge | Natural-language question or terms; optional source scope | Matching passages, locations, complete-page links, and content status | Let the model pursue its own questions |
| Read a complete entry or section | Stable ID or path; optional section | Content and provenance; explicit notice of portions not returned if the text is too long | Retain complete design relationships and allow deeper reading |
| Trace and compare | Source ID or related entry | Original record, template, images, adjacent material, and reasons for links | Check detail and compare beyond summaries |

Search ranking supplies reading candidates. The model can revise its question, open a directory, follow links, or judge that further retrieval adds little. Reference images can be read when useful; the semantic organization does not require a new multimodal index.

## Task workspace and dynamic structure

The workspace should retain the original request, source-video observations and their evidence, material read, unresolved questions, candidate directions, and the current proposal. It provides extensible working text. Its organization can grow from the task rather than fixed design slots for clothing, props, or lighting.

The model organizes a dynamic tree during the task; the harness stores and presents it. Nodes may represent a relationship to understand, a direction, a comparison, or a decision. They can merge, reopen, cross-link, or be abandoned. A source can support several nodes, and a node can lead into several guides. Lists and relationship graphs are also possible. Task material and citations persist independently of the particular exploration view, which remains separate from the long-term knowledge directory.

A used source can point to the actual passage or entry read, with a brief account of its effect on the proposal. These references support review; source names need not appear in the final video prompt. Actual tool records allow reading claims to be checked against the material returned.

## A long request: deepen a design already specified

The following illustrates integration behavior. It is not a recorded model run or a prescribed prompt format.

Example request: “Give it a cyber-xianxia style. Preserve the two people's conversational actions and positions. Turn the city outside the window into a floating district. Change the coats into long garments with circuit patterns. Keep the cups on the table.”

The model has the request and actual video observations. It may investigate how the floating district relates to the existing space, how circuitry relates to the garments, and what overall interpretation connects the combined style. The specified cups and relationships remain visible in context. It can directly read [xianxia](entries/base-xianxia.md) and [cyberpunk urbanism](entries/base-cyberpunk_dystopia.md), or enter the [combination guide](guides/combination.md) to compare coexistence, transformation, and viewpoint allocation. Where the source and request have an unclear correspondence, it can articulate the question or its chosen interpretation.

The eventual direction may use a spatial or material relationship from those sources, or emerge through a different comparison. The model selects decoration, color, and object changes within the task's scope. The harness carries the selected design and its evidence, and the subsequent prompt layer handles its expression for execution.

## A short request: develop reasoned alternatives

Example request: “Give it a cyber-xianxia style.” Understanding the source still matters. The model can enter through the [subject guide](guides/theme.md), comparing assumptions about cultivation, urban technology, and biomechanical worlds. It can also begin with the video's most consequential relationship and seek a suitable form. Its temporary exploration may ask how technology and cultivation relate, how that relationship could become visible in the scene, and which distinct directions it supports. The model generates and revises these questions during the task.

An interest in one subject changing state may lead to [070](entries/opuscar-070.md). Two worlds visible together may lead to [028](entries/opuscar-028.md) and [067](entries/opuscar-067.md). Several components within one language may lead to [060](entries/opuscar-060.md). The model can borrow their relationships or judge them unsuitable. The proposal should communicate its own choices and make newly invented details recognizable as proposals.

Both inputs use the same reading and observation tools. Information density, specificity, and consequential ambiguity determine exploration depth. A one-sentence precise edit may need very little exploration.

## Prompt delivery and the later loop

The Planner's design, the concrete text submitted for execution, and what the execution model actually receives should be separately inspectable. Prompt delivery needs explicit handling of known length and modality limits, recording compression, edits, and control inputs. Consequential losses should return to the model for revision or be explained to the user. The [Bernini-R experience record](model-experience/bernini-r.md) now provides conditional findings about concrete style expression. The [application guide](guides/design-expression.md) shows how the model can connect source relationships to a new proposal and draft wording. These pages can be read through the same search, browse, and source-tracing capabilities. They leave prompt length and sentence order open, while further experiments can refine the expression strategy. These knowledge pages leave semantic-preservation prompting recipes and evaluation calibration to further evidence; the outer-loop implementation and its current limits are documented separately.

The outer loop supplies prior designs, actual execution receipts, candidate and incumbent observations, and attributed feedback together so the model can decide which question to revisit. It retains the same knowledge operations in a new child planning run. The controller records versioned external evaluation and selection responses, explicit generation inputs, candidate acceptance and resource stops. Formal evaluation and automated selection policy remain to be finalized; local replay checks establish the connection, not improved generated videos.

Content integrity, source preservation, and link checks remain available for the knowledge package. The independent harness additionally passed focused reliability checks and four actual planning walkthroughs. Those runs demonstrate complete-case reading, task-specific design, and exact prompt handoff; all used the initial six-frame overview. Adaptive re-observation, difficult long-session behavior, and generated-video improvement require further live evidence.

