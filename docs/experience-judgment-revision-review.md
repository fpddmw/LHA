# Experience and judgment revision: review draft

Date: 2026-10-30. Status: **proposal only; active knowledge and runtime remain unchanged. No model calls, scoring, rendering or experiments.**

This round revises judgment support in three existing experience topics. The five concerns below are independently useful reading topics, not a required sequence of thought or a response schema. The optional map, model-led planning and artistic sources remain available as before.

The new advice is common-sense guidance informed by recorded failures. The experiments establish particular actions and outcomes; they do not validate this new advice or a universal input route, prompt recipe, ranking or stopping policy. Existing Critic and independent judge outputs retain their evidence scope and uncertainty. This review adds no visual judgment or hidden reasoning reconstruction.

## Publication scope, if approved

| Active file | Proposed change |
|---|---|
| knowledge/experience/inspect-and-compare.md | Interpret unsuccessful attempts, update expectations, and compare relevant candidate tradeoffs. |
| knowledge/experience/express-edits.md | Choose coherent modification scope and distinguish necessary dependencies from optional expansion. |
| knowledge/experience/choose-editing-input.md | Select inputs by available information and achieved appearance; distinguish obscuration from replacement; make stopping contextual. |

The existing navigation and use-design-knowledge already cover these questions, so they are unchanged. Source entries, artistic and semantic guides, Planner system instructions, Critic, evaluation metrics and runtime are outside this patch.

The [complete proposed patch](../out/experience_judgment_review/20261030/proposed.patch) contains the three-file revision, including short case paragraphs and source links. It has not been applied. Each comparison below quotes active text exactly and supplies the proposed English wording. Case details and scores support review; they are not a new ranking rule supplied to the Planner.

## Evidence used

- [Bernini 024 full state](../out/agent_loop_live/20261030/phase2/completed-024-pair/tasks/024__long__full_knowledge/run/state.json): exact prompts, ancestry, purposes, critiques event-0005/event-0008/event-0010, and final v2.
- [Bernini table-tennis full state](../out/agent_loop_live/20261030/phase2/completed-fewshot-004-pair/tasks/fewshot_004__long__full_knowledge/run/state.json): event-0004-critique process diagnosis, event-0008-generate scope, event-0009-critique and final v2.
- [Ditto 024 full state](../out/agent_loop_live/20261030/ditto-phase2/completed-pre-stop-six-tasks/tasks/024__long__full_knowledge/run/state.json): source to v1, v1 to v2, v1 to v3; final v3. Independent scoring remains pending in this evidence set.
- [Bernini 027 full v1 independent record](../out/agent_loop_live/20261030/independent-evaluation-027/service/evaluations/bernini__027__short__full_knowledge__v1/record.json) and [v2 record](../out/agent_loop_live/20261030/independent-evaluation-027/service/evaluations/bernini__027__short__full_knowledge__v2/record.json): equal edit/core/detail/time scores; style 4.0 to 3.8 and aesthetic 3.90 to 3.76. The unresolved severity concern remains in the [earlier review](agent-loop-defect-review-and-refactor-plan.md).
- [041 Bernini full](../out/agent_loop_live/20261030/phase2/completed-041-pair/tasks/041__short__full_knowledge/run/state.json), [Bernini no-knowledge](../out/agent_loop_live/20261030/phase2/completed-041-pair/tasks/041__short__no_knowledge/run/state.json), [Ditto full](../out/agent_loop_live/20261030/ditto-phase2/completed-041-pair/tasks/041__short__full_knowledge/run/state.json), [Ditto no-knowledge](../out/agent_loop_live/20261030/ditto-phase2/completed-041-pair/tasks/041__short__no_knowledge/run/state.json): one generation each, select v1.

Independent semantic values below are normalized from the recorded 0-100 scale. These later judgments were not available to the online Planner as a retrospective oracle.

| Bernini table-tennis full | Edit completion | Core preservation | Time preservation |
|---|---:|---:|---:|
| [v1](../out/agent_loop_live/20261030/independent-evaluation-024-fewshot/service/evaluations/bernini__fewshot_004__long__full_knowledge__v1/record.json) | 0.7222 | 0.8611 | 0.8333 |
| [v2, selected](../out/agent_loop_live/20261030/independent-evaluation-024-fewshot/service/evaluations/bernini__fewshot_004__long__full_knowledge__v2/record.json) | 0.3889 | 0.9167 | 1.0000 |
| [v3](../out/agent_loop_live/20261030/independent-evaluation-024-fewshot/service/evaluations/bernini__fewshot_004__long__full_knowledge__v3/record.json) | 0.6667 | 0.7778 | 0.8333 |

Bernini 024 full selects v2. Its [independent record](../out/agent_loop_live/20261030/independent-evaluation-024-fewshot/service/evaluations/bernini__024__long__full_knowledge__v2/record.json) gives edit 0.875 and core 1.0, with detail/time unresolved. The [no-knowledge state](../out/agent_loop_live/20261030/phase2/completed-024-pair/tasks/024__long__no_knowledge/run/state.json) selects v1 after three source-based attempts. Its [v1](../out/agent_loop_live/20261030/independent-evaluation-024-fewshot/service/evaluations/bernini__024__long__no_knowledge__v1/record.json), [v2](../out/agent_loop_live/20261030/independent-evaluation-024-fewshot/service/evaluations/bernini__024__long__no_knowledge__v2/record.json), and [v3](../out/agent_loop_live/20261030/independent-evaluation-024-fewshot/service/evaluations/bernini__024__long__no_knowledge__v3/record.json) records show lower later edit/core/time scores. V3 uses seed 137; these are not matched-seed prompt-only comparisons.

## 1. Failure analysis

Target: [inspect-and-compare.md](../knowledge/experience/inspect-and-compare.md).

Observed basis: table-tennis full event-0004-critique states that the failed Earth-view, wall, identity, geometry and trajectory requirements were already in the submitted prompt. In 024 full, reviews describe obscuration while the v3 action purpose describes loss. Proposed advice: distinguish the actionable situations and revise the explanation as results accumulate. The explanations and advice remain hypotheses or common-sense guidance; improved decisions have not been measured.

### Before: active text

> Keep useful alternatives available. Stronger style may conceal changes that remain difficult to inspect. A plausible explanation of a defect is a hypothesis until the available evidence distinguishes it from alternatives. Seeing a failure does not by itself locate its cause in wording, sampling or model capability.

### After: proposed text

> ## Understand what an unsuccessful attempt tells you
>
> A missing result calls for different responses depending on what was actually sent and what the evidence shows. If the request was omitted or assigned to the wrong part, revise that expression. If it was already explicit, carry forward that knowledge: another attempt is a new hypothesis about realization, not simply a corrected omission. A different visual relationship, less competing content, another input, or another sample may be useful, depending on the case.
>
> Keep the visible defect distinct from an explanation of its cause. Detail hidden by glow or fragmentation may be obscured rather than replaced; an unobserved interval may leave motion unknown. Inspect further when that distinction would change the action. Otherwise make a qualified choice from the available evidence.
>
> Use a failed revision to update a relevant expectation. If extending an effect broadens coverage but obscures the subject, the new question concerns that tradeoff; it is no longer just whether the effect can be made stronger. A short note can preserve the changed understanding. These distinctions are aids to judgment, not categories to fill or a required analysis before every action.

## 2. Modification scope

Target: [express-edits.md](../knowledge/experience/express-edits.md).

Observed basis: table-tennis full event-0008-generate changes walls, window construction, lighting, floor, glow and glasses while describing the attempt as concentrated refinement. The following review reports both improvements and regressions. Floor replacement is an authored addition. Proposed advice: choose a coherent benefit, include needed dependencies, and simplify dispensable additions. The record does not isolate which change caused a regression or validate a one-feature-per-attempt rule.

### Before: active text

> A precise local request generally benefits from expression centered on the requested change and its dependencies. An open style request can benefit from developing a specific interpretation through visible relationships. Length alone does not determine which task needs more design work. Avoid expanding a narrow request simply to demonstrate creativity or use every available piece of knowledge.

### After: proposed text

> A precise local request generally benefits from expression centered on the requested change and its dependencies. An open style request can benefit from developing a specific interpretation through visible relationships. Length alone does not determine which task needs more design work.
>
> Choose a revision around a coherent benefit to the requested result. Several coupled changes may belong together: a convincing window can require its opening, frame, outside view and illumination. Changes that serve unrelated purposes need their own justification within the design. Where an optional addition creates more work or risk without helping the user's goal, simplify or drop it. Preserve the substance of a detailed request while choosing what is worth attempting next.
>
> Judge scope by what the prompt changes, not by calling it a focused refinement. A whole-frame style may require broad treatment; a remaining tabletop-light defect may admit a narrower attempt. A narrow instruction still uses the renderer's actual editing capability and can affect other regions. Repeating preservation clauses does not establish protection.

## 3. Input choice

Target: [choose-editing-input.md](../knowledge/experience/choose-editing-input.md).

Observed basis: Bernini 024 continues v1 to v2 before restarting from the source for v3, then selects v2. Ditto 024 branches from v1 after v2 introduces opaque bars. Table-tennis v3 asks for generic glasses while receiving a candidate without discernible original glasses. Proposed advice: choose for the useful information and appearance actually supplied; distinguish obscuration, replacement and invented reconstruction. The cases do not establish the relative success of restart and continuation.

### Before: active text

> ## Recover a useful starting point when essential information is lost
>
> If a candidate has substantially changed a key person, object, action or relationship, prefer an input that still contains the needed information, often the original. Repeated editing of a damaged representation can require the generator to invent missing structure. The original makes that structure available again, while the desired appearance must be generated anew.
>
> A small remaining shape error does not automatically justify discarding a successful transformation. Inspect enough of the relevant area to judge the extent of the problem. When an older candidate already contains both the needed information and useful styling, it may be a better starting point than either the original or the latest result.

### After: proposed text

> ## Recover a useful starting point when essential information is lost
>
> Choose an input that supplies what the proposed change depends on. When an earlier candidate contains both useful styling and the needed person, object or relationship, it can offer a better base than the latest candidate or the original. When the needed information has been replaced across the available candidates, returning to the original makes it available again, while the successful appearance must be generated anew.
>
> Obscured detail and replaced detail lead to different possibilities. Reducing an overlaid effect on an otherwise useful candidate is a plausible repair when the underlying structure may remain; it does not guarantee recovery. If the distinction is consequential and unclear, inspect it. Naming generic glasses in a prompt can reconstruct an accessory, but does not give the renderer the original person's missing identity information.
>
> A source restart becomes more compelling when it provides information or a starting configuration the proposed repair needs. A later failed continuation can supply new grounds for that choice. The iteration number does not decide the input. Consider the useful effects that would need to be recreated, and keep earlier results available whatever branch is attempted.

## 4. Candidate tradeoffs

Target: [inspect-and-compare.md](../knowledge/experience/inspect-and-compare.md).

Observed basis: table-tennis v2 improves recorded core/time preservation over v1 while losing edit completion; the final online comparison prefers v2 over v3. Bernini 027 selects v2 without a gain on the recorded independent dimensions. Proposed advice: revisit older candidates when their strengths could change the selection and explain the task-specific tradeoff. This does not mandate exhaustive ranking or establish a universal scalar winner.

### Before: active text

> When two candidates trade advantages, compare them against the original request using consistent observations. The user's requirements, the Planner's optional additions and the evaluator's observations are different kinds of information. Failure to realize an optional design flourish may justify dropping it; a missed user requirement deserves a different response.

### After: proposed text

> ## Compare alternatives around the same question
>
> Select for the user's requested outcome, considering the transformation and what must remain meaningful. When a candidate gains appearance but loses action or identity, relate the tradeoff to this task. An optional embellishment has a different status from an explicit requirement. If no candidate satisfies the full request, choose and describe a partial result without silently dropping the unmet requirements.
>
> An earlier candidate can remain relevant after a successful repair: the repair may improve one property while weakening another. Revisit earlier alternatives when their known strengths could change the choice. Compare the consequential difference using compatible observations; there is no obligation to rerank every saved video.
>
> Keep delivery choice separate from editing-input choice. A useful base for the next change need not be the best current result. Unknown evidence remains unknown; seek a closer comparison when resolving it could reverse the preference. Explain a consequential selection with the advantage that matters and the remaining limitation, rather than relying only on recency or a general score.

## 5. Stopping judgment

Target: [choose-editing-input.md](../knowledge/experience/choose-editing-input.md).

Observed basis: four 041 loops finish after one generation. Bernini 024 no-knowledge makes three attempts and selects v1, with later independent scores lower on several dimensions. Proposed advice: continue for plausible benefit or useful uncertainty reduction; distinguish satisfactory completion from a partial or budget-limited stop. These traces do not establish that the unsuccessful later attempts could have been rejected in advance.

### Before: active text

> ## Revisit earlier results and stop when appropriate
>
> If continued editing adds unrelated changes, return to a less damaged version and reconsider the next change. Preserve useful alternatives. Different candidates may be suitable for different next steps or final delivery; a single mandatory incumbent is unnecessary.
>
> Continue when a further action has a plausible benefit for the actual request or can resolve consequential uncertainty. Finish when the available result is suitable, when further attempts have little expected value, or when resources end. A resource stop can leave an incomplete task; describe that outcome accurately.

### After: proposed text

> ## Revisit earlier results and stop when appropriate
>
> If continued editing adds unrelated changes, a less damaged version can be a better starting point or final result. Preserve useful alternatives and reconsider the actual change still needed.
>
> Continue when a concrete next attempt has a plausible benefit for the request, or when it can resolve an uncertainty worth the cost. A missing requirement matters, but its existence alone does not make another similar generation useful. Repeated failure of an already explicit instruction can favor changing the design's realization, changing the input, inspecting a consequential ambiguity, or stopping with a qualified result. A genuinely different hypothesis can justify exploration even after a failure.
>
> Finish when the available result serves the task and the remaining differences are acceptable in that context. An open illustration request can tolerate some simplification that would be unacceptable in an explicit identity or geometry requirement. Remaining budget is an opportunity, not an obligation. When no promising attempt is available or resources end, report the selected result's unmet requirements and uncertainty; stopping does not make them resolved.

## How the advice could affect an actual decision

After the recorded Bernini 024 v2, a model using this guidance could recognize improved coverage, unresolved obscuration of face/handset detail, and the cost of recreating the style from the source. It could inspect the consequential ambiguity, try reducing an overlay on a suitable candidate, restart with a different realization, or deliver v2 with limitations. The advice supplies grounds to discriminate, not an assigned next operation.

For table tennis, it could separate requested arena components from an optional floor redesign, compare v1's stronger transformation with v2's better preserved play, and recognize that generic glasses on v2 are a reconstruction rather than evidence-grounded restoration of the source person. A coherent multi-part arena revision remains legitimate. Neither narrowing the edit nor choosing v1 is prescribed.

These are authored illustrations, not new model decisions, replay outcomes or validated improvements.

## Relation to the two RSI levels

Within a task, useful learning changes what the model expects and what it tries or selects. It may be carried in an ordinary action explanation or optional note; no additional response fields, mandatory reflection step or fixed alternative list is introduced.

Across tasks, these edits remain candidate experience. Conditions, contradictory outcomes and unknowns are retained in this review and the linked case records. If approved for use, they should be versioned as informed guidance with untested benefit; frozen historical runs retain their own material. Broader efficacy claims require later authorized validation. This round neither implements a publication pipeline nor publishes the draft automatically.

## Draft integrity

The hashes below identify the exact active text used for this proposal.

| File | Baseline SHA256 | Words before / proposed |
|---|---|---:|
| knowledge/experience/inspect-and-compare.md | cd114f955375aeb5ad6d89b0ad665b42acd1a3564e225bb4ed3af4e0b43ed284 | 443 / 816 |
| knowledge/experience/express-edits.md | 24c3b00a191974b6764a03b15ef6553ee6df45021ac425f2c207381184b795fe | 455 / 662 |
| knowledge/experience/choose-editing-input.md | bfa89cebf0bb62c9d2ca6bd18d40aff50461503618215fadf85c0d6d9377b50e | 609 / 825 |

Only this review and its proposed patch were written. Active knowledge hashes and local links were checked. These file checks establish draft integrity, not improved model behavior.
