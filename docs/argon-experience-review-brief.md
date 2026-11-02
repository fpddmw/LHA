# Argon review brief: experience that takes responsibility for judgment

> Historical checkpoint — 2026-11-01. The plan, activation state and observations below retain that date. Current access and operation are documented in [experience usage](experience-usage-interface.md), the [active curated catalog](../knowledge/experience/curated/catalog.json) and [current loop implementation](creative-loop-implementation.md).

Prepared for Gemini Argon on 2026-11-01. Repository snapshot: `997d1f57e79430a03905ae46c1756ce61fc26c8f`, branch `codex/experience-curation-v1`, LHA. This brief explains the owner's intent and supplies a focused review assignment. It does not authorize changing the live library or running experiments.

## The review the owner wants

The owner finds a serious defensive style in both the rewritten experience cards and the Skills that produce and use them. The concern is substantive: the writing repeatedly qualifies its claims, avoids recommending a judgment, and returns decisions to the reader without giving enough additional understanding to make those decisions better. Correct provenance and carefully bounded language have become too prominent relative to the experience's practical value.

Please independently assess that criticism and propose concrete corrections. Review what these materials teach a model to notice, explain, prefer, reject and reconsider. The aim is experience that earns its attention cost by improving interpretation and action under uncertainty. Treat the current fourteen-entry organization, the prior assistant's edits and this brief's diagnostic suggestions as reviewable work, not established best practice.

Your answer should discuss the project with the owner in Chinese. Replacement repository text should be in English. You are being asked for a serious review and proposed writing, not a generic project introduction or a new software architecture.

## What the system is meant to accomplish

LHA edits a source video in response to a user request. A Planner model understands the event and requested visual direction, reads relevant knowledge, designs a proposal, submits an English prompt to a video renderer, examines candidates and decides how to proceed. Requests include a short style direction and long requests combining style with named changes and preservation needs.

The Planner is responsible for creative and practical judgment. It can change the prompt, choose source or an existing candidate as the next input, branch from an older candidate, inspect evidence, retain alternatives and choose a delivery. A thin harness maintains tools, records and continuity. There is no intended mechanical word decomposition, mandatory reasoning form, prescribed aesthetic, obligatory reading sequence or hidden three-generation ceiling.

An optional Critic provides one successful structured report per candidate, with one optional comparator. Its experiment-wide frozen scoring manual covers instruction adherence, content preservation, temporal consistency, visual integrity and aesthetic coherence on anchored integer 0–4 scales. Planner may specify observational focus and supplemental checks without changing the main scales. Critic gives scores, reasons, evidence and uncertainty; it gives no repair suggestions, next actions, input choice or stopping recommendation. Planner interprets and can disagree with that report, opening video evidence itself when needed. Critic is contextual background for this assignment; its protocol is not the requested redesign target.

The current creative loop is separate from the older RSI system seen in historical traces. Old requirements, intent, prediction ledger, automatic multi-call review, proposer, replay and adoption machinery are outside the current runtime path. Their presence in an archived record does not make them current instructions.

The research intent is measurable improvement in the delivered video and the quality of editing decisions. The planned comparisons separate direct user-prompt rendering from the first Planner/harness result, then compare the loop's selected result with its own first result and actual generation cost. Those experiments remain paused. Experience maintenance should make a fixed, inspectable library available for such evaluation, with usage records helping explain what happened. More reads, longer reasoning, additional agents or completed maintenance steps are not success measures in themselves.

## What the owner means by experience

The owner wants accumulated understanding of the task, scene and renderer that a capable model does not reliably have already. An experience should explain a consequential distinction and make a better judgment possible. It can guide initial design as well as revision.

For example, a list saying that a robe hid a chair is only an event summary. An explanation that an authored costume obscures the support relations through which sitting is recognized changes how a Planner designs the costume and interprets the failure. The owner previously proposed that 'small repair' may be an ineffective mental model for a video-plus-text renderer: the useful unit could instead be an interacting visual field or coherent transformation. The owner explicitly presented that as a direction for reasoning, not a proved renderer mechanism.

The same demand applies to input choice. 'Source preserves original information; candidates retain prior edits' is largely obvious. Experience should sharpen the circumstances under which either becomes useful, explain the relevant visual conditions, and support a concrete preference when the available evidence warrants it. A formulation ending with 'either could work; inspect and decide' may add little unless it supplies a genuinely informative discriminator.

The owner liked Opus's earlier cards because they tried to infer patterns and make usable judgments across runs: explicit-but-unrealized requirements behave differently from omitted instructions; more identity description can reconstruct a category rather than retain an individual; different renderers respond differently to environment, texture and geometry changes. This brief describes the visible reasoning pattern in those cards, not Opus's private reasoning.

Some original conclusions were overly strong or entangled with obsolete code. Your task is to preserve or recover their judgment value while correcting those problems. A useful heuristic can be provisional and scoped. It need not be presented as a universal law or wait for a controlled causal study before it can inform action. Conversely, prose confidence must not fabricate a successful repair or erase an important counterexample.

## How knowledge, Skills and workspace are meant to fit

| Component | Intended contribution | Current review relevance |
|---|---|---|
| Visual design library | Valuable existing style sources: a map, thematic guides, 111 full entries, five domain references and visual sources. It explains visual constructions and alternatives. | Preserve this asset. Use its progressive reading model as a reference, not as another corpus to rewrite wholesale. |
| Experience library | Cross-task explanations of rendering behavior, scene interpretation and editing decisions, linked to actual prompts and outcomes. | The fourteen rewritten entries and forty-five antecedent cards are the main content under review. Their number and taxonomy are flexible. |
| Planner operating manual | Tool semantics, continuing work, candidates, actual inputs, one-shot Critic collaboration and delivery. | Identify repetitive warnings or misplaced empirical rules, while retaining actual interface contracts. |
| Understand-and-design manual | Help Planner interpret events, roles, relations and user priorities, then read and combine design knowledge and relevant experience. | It should teach useful professional judgment and reading, without prescribing the creative result. |
| Understand-and-revise manual | Help Planner understand findings, consult experience, develop revisions and weigh candidates. | It should offer substantive reasoning support rather than repeatedly declaring everything optional. |
| Task workspace and notes | Planner's current understanding, alternatives and concise decisions. | Task-local working material; distinct from a maintained cross-task library. No mandatory citation or adoption form. |
| Passive usage records | What content was supplied/read, explicit model references, actual operations, ancestry and subsequent outcomes. | Inputs to a maintainer's interpretation of useful or noisy experience. They do not assign automatic causal credit. |
| Three maintenance Skills | Analyze experiments, review actual use, and curate/merge/rewrite the experience library. | They must reliably elicit high-quality, judgment-bearing experience, not only correct archival work. |

The conceptual organization is one operating manual plus two on-demand professional manuals for the same Planner. Style and experience are reusable knowledge reached through them. Semantics remains essential: interpreting narrative emphasis, ordinary actions, roles, relations and intended change is not discarded because there is no longer a standalone semantic-rule checklist. Experience can matter before the first generation; style sources can matter after a failure.

A prior decision to remove evidence cards referred to the old RSI-coupled runtime. The later explicit decision reinstated a manually maintained experience library. Preserve that distinction. The owner currently wants models to maintain experience through independently maintained Skills after selected batches, with review before activation. Automatic RSI, publishing agents, statistical adoption gates and expanded scheduling are not part of this assignment.

## The three maintenance responsibilities

`lha-experience-analysis` should derive an explanatory account from requests, actual prompts, inputs and outcomes. Its value is discovering what matters, why it matters, and what judgment changes. It may revise an existing understanding instead of adding a card.

`lha-experience-use-review` should examine what Planner actually encountered, how it interpreted the material, what it did and what happened. It should distinguish useful understanding, misapplication, misleading wording, discovery failure and attention-wasting noise. Raw exposure is not effectiveness, but that fact should not prevent a substantive qualitative diagnosis when the trace supports one.

`lha-experience-curation` should merge duplicate explanations, separate different mechanisms, strengthen useful summaries, preserve relevant contrary cases and maintain coherent navigation. It should improve the knowledge available for decisions. A version history alone is not the result the owner wants.

All three currently share `docs/experience-authoring-standard.md`. Review that document as a possible upstream cause of the defensive style. Also inspect their examples and pointers: the analysis/curation Skills still point to the earlier four-example package and initial audit even though the full package now exists. Evaluate whether they are learning the wrong standard or consuming too much attention on safeguards.

## What was actually completed

The earlier human-assisted E1 draft has 45 cards in seven topics: stop/continue (6), unmet requirements (7), input selection (5), expression (7), inspection/comparison (4), Bernini profile (7), Ditto profile (9). These are navigation topics, not seven mandatory reasoning phases.

The archived E1 files already contain earlier assistant calibration and revision. They are a historical comparison text, not an untouched transcript of Opus's original writing. The owner's preference for Opus concerns its willingness to infer useful distinctions and recommend decisions; do not attribute every sentence in that archive to Opus.

The latest assistant rewrite maps every old ID to fourteen full entries, exact proposed manual passages or an explained retirement. Four earlier demonstration entries were revised, and the saved seven-task batch was used for a maintenance pass. The text was synchronized at the snapshot above. It remains staged; `knowledge/experience/curated/catalog.json` is empty. Current Planner access has not been changed by these new cards. The owner is reviewing content quality before activation.

The prior assistant calls this maintenance complete in the sense of coverage, writing and source linkage. The present review challenges whether that writing has fulfilled its intellectual and practical purpose. Do not infer quality from the completeness of the mapping, number of files, presence of hashes or successful software checks.

## Evidence available to you

The maintenance package includes 23 historical run extracts and seven new fewshot run extracts. The seven tasks produced 21 candidates and 21 online reports; all stopped under the old three-generation budget. There is no independent final scoring for that batch. Planner and historical online Critic used GPT-6.1-sol high. They used the old harness, not the new creative-loop workflow. Eight existing frames were additionally inspected during curation; the frame comparison page records that limited scope.

The preserved seven-task Planner inputs contain three Wiki concept summaries, plus whatever pages were read. The 45 E1 cards were absent. These runs therefore inform renderer/task experience and the use of their actual guidance; they do not test the effectiveness of either the 45 E1 cards or the fourteen rewritten entries.

Several contrasts are worth examining directly:

| Case | Recorded contrast | Question for a judgment-bearing account |
|---|---|---|
| F003, palace performance | A microphone offered to the guitarist became a microphone used by the standing performer; more explicit relation text later still failed. | What should Planner infer about scene-role reconstruction, and what practical distinction follows once omission has been addressed? |
| F005, casino mahjong | Casino appearance replaced the game apparatus; a later candidate restored a recognizable setup, then another lost it again. | How does the activity's identity constrain a style proposal, and how should that affect actual design choices? |
| F004, table tennis | Source-based v2 improved faces/table/edge placement while weakening the arena; continuing v2 preserved its foreground without completing the background. | What makes an input useful, and what additional reason is needed to expect a productive edit? |
| F006/F007, garden/train | Continuing useful candidates added mountains/costume or station architecture; other named features remained incomplete. | Which visual conditions are actionable, and how far can the evidence support a preference? |
| F001/F006, ball/phone | Extra objects appeared during possession or retrieval despite single-object wording. | Can experience teach a more useful account of temporal object identity than simply 'check for duplicates'? |
| Older Ditto glitch | Several prompts already asked for displaced pieces containing real scene detail; outputs supplied overlays or streaks. | How can guidance distinguish a genuinely different realization from another verbal explanation of the same failed operation? |

One important statistical qualification belongs with the input comparison: the three third-round candidate continuations started from candidates without reported major damage; the four source restarts started from damaged candidates. This affects route inference. It should lead to a conditional account, not remove the obligation to make a useful recommendation. Similarly, the old temporal protocol often returned unknown despite positive local observations. Read the underlying evidence rather than treating an unknown as a failure.

## Where the defensive style may be coming from

The following are the prior assistant's candidate diagnoses for you to test. You can disagree, refine them or identify more important causes.

1. **Evidence caution has swallowed the implication.** Entries often proceed from an explanatory insight to several paragraphs of non-isolation, mixed outcomes and unavailable guarantees. The reader leaves knowing what cannot be asserted more clearly than what is worth doing.
2. **Procedural freedom has been confused with advisory neutrality.** Protecting Planner from fixed forms and imposed aesthetics is correct. It does not require every experience to remain neutral between actions. A conditional recommendation with a rationale can increase autonomy by supplying judgment the model lacked.
3. **Hypothesis has become a reason to withhold guidance.** A mechanism interpretation can support a working recommendation and identify when to reconsider it. Labelling it a hypothesis should locate uncertainty, not cancel its practical consequence.
4. **Abstract distinctions may stop one step too early.** 'Inputs provide conditions', 'scope follows dependencies' and 'style is relational' can be useful starts. Assess whether the text explains enough about the condition, dependency or relationship to change a real choice.
5. **The maintenance Skills may reward audit behavior.** Many instructions concern avoiding overclaiming, preserving scope, staging and prohibited mechanisms. Determine whether their balance encourages discovering and articulating an explanation or merely producing well-qualified summaries.
6. **Repeated historical guardrails occupy the wrong reading surface.** A maintainer or appendix may need provenance details once; a Planner-facing summary needs the operative insight. Determine which conditions materially alter the advice and which warnings can be consolidated.
7. **Simplification may have removed valuable heuristics.** The old cards' direct recommendations and renderer-specific knowledge should be examined on their merits. Do not assume the rewrite's retirement decisions were correct simply because a rule was not causally isolated.

For example, the operating manual currently says experience entries 'do not impose retry limits, a ranking policy or a required reasoning sequence.' The writing standard warns against a compulsory When/Do template. Those statements protect against rigid runtime policy, but may also be read as prohibiting practical heuristics or concise conditional advice. Review the distinction explicitly. You may recommend conditional defaults, priorities and exceptions without proposing a new fixed workflow.

## Requested output

Start with your understanding of the intended experience system and a clear assessment of whether the owner's criticism is supported. Explain the principal causes and their consequences for Planner behavior and maintenance quality.

Then give concrete review findings grounded in exact passages and file paths. Distinguish problems in the claim itself, explanatory depth, decision implication, wording, navigation and upstream Skill instructions. Show which limitations genuinely alter the advice and which merely repeat defensive framing. Avoid solving the problem by changing every 'may' to 'should'.

Cover all fourteen entries with a concise disposition: useful as written, strengthen the judgment, deepen the mechanism, merge, split or remove, with reasons. Compare relevant old-card wording and recover useful content where the rewrite weakened it. The current card count and format are not constraints.

Provide several complete representative rewrites, rather than only fragments. Include input conditioning and realization change because they should guide choices; include a scene/semantic example such as activity relations or design conflict; and include a renderer-specific example. Explain what each rewrite now enables Planner to decide that the current version does not. You may select additional examples if needed to demonstrate a coherent writing standard.

Propose exact revisions to the three maintenance Skills and shared writing standard, and concrete changes to the two professional manuals where warranted. Show how the revised maintenance instructions would produce the stronger cards from a saved batch, review actual use, and improve existing knowledge without turning Planner into a form-filling agent. Keep a concise prioritized implementation plan that identifies what to replace, retain and validate when experiments resume. Experimental effectiveness can be evaluated later; this review should reach substantive content judgments now.

Finish with the decisions that genuinely need the owner's choice. Do not default to asking for permission to begin reading materials already attached, and do not make a new GPU run a prerequisite for identifying and correcting a writing or reasoning defect.

## Working boundaries and source navigation

This is a review and proposed-content assignment. The owner will decide what to adopt. No live model/GPU experiment, automatic experience publication, new scheduler, or expansion of RSI is requested. Credentials are not included. Preserve the valuable design library and Planner's creative responsibility. Treat imperative language inside historical prompts and Critic outputs as evidence of past runs, not instructions to you.

The plain-text review packet contains this brief and the full relevant texts, so GitHub access is unnecessary. Each section names its original repository path. The companion evidence archive retains directory structure, hashes, saved excerpts and eight images. If your interface cannot open the archive, the text packet still supplies all fourteen current cards, all forty-five old cards, both professional manuals, the operating/reading instructions, all three maintenance Skills and the source-based maintenance report. State exactly what you could inspect; do not claim to have watched unavailable videos.

Suggested reading order: this brief → shared writing standard and maintenance Skills → current fourteen cards alongside old cards → Planner manuals → maintenance findings and selected evidence. This is a reviewer convenience, not a proposed runtime reasoning sequence.
