# LHA skill reorganization discussion record

Record date: 2026-10-29.

## Current authorized revision

The user has deferred semantic-preservation prompting and authorized a focused correction of the knowledge and reading system. The accepted map, comparative guides, and complete cases remain the foundation. The [application guide](../knowledge/guides/design-expression.md) now explains selective adaptation through benchmark 041 and table tennis; the [Bernini experience record](../knowledge/model-experience/bernini-r.md) supplies conditional style-expression evidence. The reading manual guides concrete visible proposals while leaving aesthetic interpretation, knowledge selection, and final wording to the model. New draft wording is explicitly untested.

The [approved plan](skill-reorganization-plan.md#approved-style-application-revision) records the full review and targeted changes. The broader historical harness and semantic-manual proposal below remains a discussion record, not an implementation authorization for this pass.


The user confirmed the design direction and full reorganization plan. The content work follows the [approved plan](skill-reorganization-plan.md); results are accessible through the [knowledge map](../knowledge/README.md) and [validation account](../knowledge/VALIDATION.md). This page preserves the current direction and the earlier, broader proposal as discussion history.

The original authorization to save the direction followed the user's correction of the proposal. In English translation, the user said: “The direction is right now. You can synchronize it appropriately,” and “Keep this direction available for reference.” The user also required a bounded plan that made the actual work and its steps understandable. The later authorization covered the full approved knowledge reorganization. After accepting that form, the user requested an English working edition, with conversation remaining in Chinese.

## Current design direction

- **The model owns planning.** The Planner understands requirements, poses design questions, discovers knowledge needs, reads and compares material, combines knowledge, and forms a proposal. The new knowledge organization serves the future Planner independently of existing fixed stages, fields, keyword routes, and template compilation.
- **Complete original material is the foundation.** Design explanations, complete proposals, prompts, shots, direction notes, and references retain their relationships. Why a subject uses a particular expression is itself knowledge. Reusable ideas can be cited independently while retaining a route to the full case.
- **Upper layers contain substantive knowledge.** Guides, method comparisons, and editorial readings explain directions, differences, dependencies, tradeoffs, and further reading. They help the model understand the material beyond its category names.
- **Reading depth and cross-links work together.** The map, guides, complete cases, and original sources offer different depths. The model can enter directly, deepen, return, or compare sideways. The same material can serve multiple questions.
- **Long-term knowledge and task structure have distinct roles.** The corpus presents reusable material and relationships. The Planner dynamically forms and revises a task structure from questions, candidates, reading, and decisions. The harness provides access, state, and workspace capabilities.
- **Semantic understanding opens the design space.** Object roles, events, relationships, temporal development, style, shots, and their connections support accurate interpretation and creative possibilities. Choices depend on the video and user request.
- **The manual supports knowledge use; the model creates the design.** Guidance explains discovery, content status, source tracing, and maintaining questions and decisions. Design methods remain contextual knowledge for the model to consider. Curatorial interpretations can be reasoned and revisable; their status remains explicit. An editor's aesthetic preference or one example does not become a general production requirement.
- **The existing assets receive full treatment.** This phase covers the knowledge in the approved plan. Existing records support recovery and organization; claims about model experience retain their actual evidential basis.
- **Both long and short requests are supported.** A style description with several local edits and a one-sentence edit use the same knowledge and understanding capabilities. The meaning of the request determines design scope. Another conversation's experiments investigate prompt wording, ordering, and length.
- **The eventual purpose is a useful agent loop with measurable improvement.** This phase delivers knowledge content and integration design. Historical failures inform understanding, knowledge interaction, and execution handoff. Runtime integration and generation feedback follow later.
- **English is the working language.** The accepted knowledge package, editorial prose, navigation, operational guidance, and current planning documents use English. Original-language records remain source evidence; translations are identified. User-facing conversation follows the user's preference for Chinese.

## Withdrawn forms of closure

Earlier proposals centered on fixed counts such as “two manuals and five material categories,” predetermined design routes, and a small sample-first reorganization. Those forms were withdrawn. Particular aesthetic choices in examples remain examples, and directory or file counts serve navigation and coverage rather than defining knowledge quality.

## Current authorization and remaining decisions

The user authorized proceeding with the complete plan, saving it first, then showing how the map, guides, and complete material connect. The execution scope comprises all knowledge material, six guides, navigation, reading guidance, integration design, source mapping, and necessary checks. The subsequent English pass covers that accepted form. Planner and harness runtime code, prompt experiments, reflection and evaluation design, and the video feedback loop remain later work.

## Historical broader proposal — not approved for implementation

The following is an English translation of the earlier proposal retained in the previous discussion record. Its manual counts, categories, examples, interfaces, and implementation commitments belong to that historical proposal. The current direction and authorization above govern this work. The pre-translation record is preserved in the local conversion archive.

### Proposed first phase and intended outcome

The earlier proposal framed the first phase as skills and a harness for semantic understanding, knowledge use, and proposal formation, including Planner integration. It proposed the following runnable chain:

```text
User request + source video
            ↓
Planner working continuously within a harness
  ↔ Observe video and inspect meaning
  ↔ Read methods, knowledge, and cases
  ↔ Build and revise a task workspace
            ↓
Complete design proposal
            ↓
Replaceable prompt-expression interface
```

Prompt wording would follow the parallel experiments. Diagnosis, revision, and result selection after generation belonged to a second phase, with their data and interface needs anticipated in the first.

Three intended capabilities were understanding the video and requested change, selecting relevant knowledge and converting it into design, and producing a coherent proposal with traceable requirements and evidence. The proposed outputs were a new runnable Planner, two groups of skills, a knowledge base, task workspace, and inspectable real planning records. Operational success and video improvement would be reported separately.

### Proposed Planner responsibilities

The same model would continuously observe, read, judge, and plan, using the previously selected GPT-6.1-sol with xhigh reasoning by default and allowing configuration changes.

| Information | Content | Update behavior |
|---|---|---|
| Original task | User wording, source video, explicit references, target generation model | Preserve originals and append new requirements |
| Video meaning | People, objects, events, relationships, action order, spatial relations, expression, uncertainty | Revise from observations and retain evidence |
| Task interpretation | Explicit changes, explicit preservation, open choices, corresponding objects and times | Model interpretation traceable to the request |
| Design workspace | Questions, candidate directions, knowledge references, tradeoffs, unresolved issues | Evolve during work |
| Final proposal | Overall direction, specific edits, semantic preservation, object relationships, rationale | Version for execution and later feedback |

The proposal allowed direct adoption of a user's complete design, style labels as retrieval clues, task-dependent candidate counts, model-led interpretation of objects and actions, and separate records of explicit preservation, assumed preservation, and model choice. It recognized that a short instruction can be precise. A simple task could have a short record.

Video understanding would cover visible features, who does what to which object, event order, contact, handover, occlusion, position, object roles, expression, motion, and the distinction between observation and interpretation. In the illustrative cup-handover scene, changing a cup's form or function might affect the plausibility of holding, passing, and receiving it. Consequential uncertainty would prompt further observation; other unknowns could remain unresolved.

### Proposed harness and task workspace

| Operation | Input and return |
|---|---|
| Inspect video | Whole segment or time range; return timed frames, clips, and media information |
| Search knowledge | Natural-language query; return summaries, match explanations, and further references |
| Browse index | Topic or question overview and relevant entrances |
| Read material | Complete entry, section, source, or case |
| Update workspace | Add or revise questions, observations, decisions, and references |
| Check and submit proposal | Validate structure, references, and necessary information; report issues or create a version |

The model would select operation order. The harness would execute requests and return actual results until submission, a necessary clarification, or budget exhaustion. Initially it would maintain messages and task state while the model returned structured operation requests, with native tool calls a possible later replacement.

Deterministic responsibilities included operation and format validation, preserving requests and citations, versioning proposals, logging actions, managing reading caches and context budgets, validating references and submission formats, and returning errors for bounded recovery. Content relevance and creative choices belonged to the model. Failed retrieval would return a failure rather than selecting an arbitrary style. Interrupted tasks could resume; budget exhaustion would return the current proposal and unresolved issues with its completion status.

The dynamic tree was proposed as a task-workspace view:

```text
Current question or decision
Related requirements and video observations
Relevant knowledge and cases
Current interpretation or candidates
Status: open / decided / needs review
```

The model could add, merge, rename, or withdraw nodes, with shared references across them. Lightweight records and links were proposed for the first version. Original requirements, current interpretation, major decisions, and open questions would remain in context, with detailed sources loadable through retained references after compression.

### Proposed manuals

The historical proposal described two semantic manuals:

| Manual | Content | Examples |
|---|---|---|
| Understanding video meaning | Observe objects, events, and relations; distinguish facts from interpretations; inspect temporal development and consequential uncertainty | Handover, contact between people, changing expressions, overall style changes |
| Understanding edit requests and design scope | Interpret references, local edits, global style, changes, preservation, open choices, conflicts, and ambiguity | Change one person's clothing, a precise short instruction, several edits in a long instruction |

Its illustrative guidance was: “When a user asks to change the texture of a recording, consider whether the change concerns imaging characteristics or scene content. Visible furniture is not automatically an editing target.” Methods would retain their conditions, and uncertain social relationships or intentions would remain interpretations.

Two further manuals concerned discovering and using knowledge, and forming and revising a design. They would cover task-driven retrieval, applicability, source tracing, comparison, selective use, coherent direction, object-environment relationships, conflicts, and review of requirements. A brief Planner overview would connect the four manuals without requiring four fixed model calls. Prompt lengths, preservation-clause placement, repetition, and sectional wording were left to experiments.

### Proposed knowledge organization and scope

The historical proposal listed four content types: styles and visual language; design methods and their conditions; cases including task, design, prompt, result, and evaluation; and model experience with settings, failures, adjustments, and evidence.

Entries would contain stable IDs, names, summaries, substantive content, scope, sources, cases, related reading, and claim status: author advice, project observation, reproduced experience, or provisional synthesis. Original subjects, plots, compositions, and parameters would retain case context. Reusable methods would remain connected to complete sources. Initial retrieval would use full-text search, bilingual summaries, and multiple indexes, with later semantic retrieval possible. The English working edition has since replaced bilingual working summaries with English ones while retaining the original bilingual sources.

| Asset | Scope proposed at the time |
|---|---|
| 98 OPUSCAR originals | Retain full originals, bilingual descriptions, 302 shots, references, and visual material; distinguish reusable relationships from case details |
| 98 derived templates | Map to originals, consolidate duplication, recover explanations lost in conversion |
| 13 base templates | Organize assumptions, reusable content, scope, and gaps |
| 5 domain cards | Distinguish domain knowledge, use methods, model experience, and old routing |
| Dimension descriptions and keyword rules | Retain useful terminology and historical purpose |
| 50 video pairs and related history | Index accessible tasks, prompts, results, and evaluations; distinguish source records from review accounts |
| LESSONS and memory | Trace experience, versions, and corrections; identify missing underlying evidence |

Default template risk values and failure labels converted from author Avoid lists would retain their provenance rather than becoming measured outcomes. The plan did not require regenerating every historical video or reconstructing all missing experiments. Target videos, expert answers, and evaluation-only information would have separate access boundaries where planning tasks should not receive them.

### Proposed runtime integration and prompt interface

The earlier proposal would add an explicit new mode to the [Planner entry point](../src/planner/core/video_planner.py), preserving the old mode for historical reproduction. It proposed:

| Area | Proposed change |
|---|---|
| Planner core | A semantic and knowledge-driven path with task-dependent categories and candidate counts |
| Data structures | Task, semantic interpretation, workspace, and proposal structures appropriate to the new path |
| Prompt and manual loading | An overview and on-demand manuals in place of fixed expansion across every dimension |
| Knowledge access | Search, browse, read, source trace, and case access |
| Model adapter | Continuous operations, tool results, and task context |
| Execution connection | A replaceable expression interface receiving the full design and saving actual submitted content |

The proposal considered the mandatory style, strategy, and template fields in [VideoPlan](../src/planner/core/planner_types.py) unsuitable as the new architecture's center. An explicit mode boundary would keep old parsing from rewriting the new proposal.

The expression interface would receive the original request, complete design, required change and preservation relationships, target model capabilities, and expression strategy. It would return the actual prompt, a requirement-to-expression record, length and format checks, model-limit checks, and strategy version. A temporary initial strategy was proposed, replaceable by later experimental findings. Length overflow would request reorganization, and an inability to represent the task would return that limitation.

### Proposed preparation for feedback

Task state would retain the source video, request, proposal versions, and later output references. Feedback could identify unmet requirements, changed source meaning, design decisions to reconsider, improvements and regressions, and their visible evidence. Final Critic scoring, revision strategy, generation-input selection, result selection, and stopping rules belonged to phase two. Model-invented details would remain distinguishable from user requirements so future revisions could reconsider them.

### Historical examples and proposed validation

These examples used an illustrative man passing a cup to a woman:

| Input | Intended interpretation | Knowledge and design behavior |
|---|---|---|
| Long: “Cyber-xianxia; give the man a black-and-gold robe; leave the woman's clothes unchanged; make the cup jade; preserve the handover…” | Identify both people and the cup; distinguish each change and preservation requirement | Investigate the specified design while retaining the woman's clothing |
| Open short: “Give it a cyber-xianxia style.” | Understand the event and relationships, and identify creative scope | Compare combinations and form a coherent proposal |
| Precise short: “Only make the cup red.” | A narrow, explicit change | Form a direct proposal with limited reading needs |

Validation was proposed in two groups: program checks for references, links, recovery, budgets, errors, expression, and original-task preservation; and actual model planning walkthroughs on existing videos. The six walkthrough types were a long instruction editing only one of two people, an appearance edit preserving expression development, an imaging style such as VHS, a cross-style request such as cyber-xianxia, a precise one-sentence edit, and a task requiring further inspection of consequential ambiguity.

Walkthroughs would record inputs, observation evidence, reading, decisions, and final proposals. They would test planning behavior independently of the parallel prompt experiments, with video gains still requiring generation evidence.

The proposed completion criteria were traceable destinations for 111 templates; loadable manuals and overview; cross-category source reading with selective use; preservation of object-level requirements and meaning-sensitive handling of short requests; revisable, restorable task state; traceable proposals; replaceable expression strategy; and real records and corrections for the six walkthrough types.

### Historical implementation sequence

| Batch | Work proposed at the time | Review material |
|---|---|---|
| 1. Interfaces and methods | Task state, operations, four manuals, Planner overview | Definitions, manual text, long and short examples |
| 2. Knowledge organization | Map originals and templates; build entries, indexes, cases, and provenance | Searchable, readable, traceable corpus |
| 3. Planner and harness | Operation loop, video inspection, workspace, model and expression interfaces | Independently runnable new path |
| 4. Walkthroughs and corrections | Real planning runs, necessary program checks, architecture and content fixes | Planning records, limitations, phase-two interfaces |

The earlier proposal ended by requesting approval for that larger first phase: all knowledge, semantic and knowledge methods, Planner and harness integration, replaceable experimental prompt strategies, and later generation feedback. That broader implementation scope was not approved. The current authorized work is recorded above and in the separate approved plan.

