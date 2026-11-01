# Decide whether another generation is worth it

[Respond to unmet requirements](respond-to-unmet-requirements.md) · [Choose an editing input](choose-editing-input.md) · [Inspect and compare](inspect-and-compare.md)

Version E1 (staged). In these recorded setups, a generation cost about 8–18 minutes of GPU time plus a review, and each attempt can damage something that already worked. Another attempt needs a specific reason to expect a gain.

### S1 · Finish when the first candidate already meets the core request
When: the review reports every user requirement as pass (or as an authorized stylization), and the remaining findings concern incidental structure, optional design or fine motion that cannot be verified.
Do: finish with that candidate and list the minor deviations. Do not restart to repair incidental structure on a short style request.
Why: in B/024L-no, B/027S-full and B/027S-no, v1 passed the independent check. The five further attempts never beat it on the independent evaluation, and three of them introduced major damage.
Limits: independent records exist only for Bernini; Ditto evidence is review-only. If the request names a structure, that structure is a requirement, not incidental detail.
Status: observed (3 loops) · Bernini; transfer to other renderers is unvalidated

### S2 · A later attempt is a risk, not a free retry
When: deciding whether to spend a remaining generation.
Do: estimate what the attempt can gain and what already-passing requirements it puts at risk. Prefer finishing when the expected gain is limited to detail-level items.
Why: of 11 later Bernini attempts, 2 were preferred under a preservation-prioritized interpretation and 4 introduced major damage absent from an earlier candidate (see the [evidence index](evidence-index.md)).
Limits: six development runs on three source tasks, one renderer, one seed per attempt.
Status: observed · Bernini; transfer to other renderers is unvalidated

### S3 · Continue only with a concrete, untried reason
When: some core requirement is unmet.
Do: continue if at least one of these holds:
1. the requirement was omitted or ambiguous in the last prompt (R2);
2. a different realization of an explicit requirement has not been tried yet (R3);
3. a known-good input avoids a regression introduced by the last attempt (R5).

Otherwise, finish with the best candidate and name the unmet requirement.
Why: the successful continuations followed this pattern. B/003S and D/003S restated the omitted back-facing orientation and fixed it. B/003S v3 removed an authored robe that hid the chair. Repeated rewording of an explicit request never succeeded (R3).
Limits: the list is not exhaustive; a genuinely new hypothesis can justify exploration.
Status: observed · any renderer

### S4 · Read online reviews by importance, not by verdict count
When: a review lists several "partial" findings.
Do: prioritize user requirements and major damage. Incidental detail normally favors stopping; a design defect that undermines the requested appearance may still justify a new attempt.
Why: the online review was stricter than the independent evaluation on incidental structure. In B/027S-full e0004 the review called reshaped roofs "substantial enough to justify another generation", while the independent check scored core preservation 1.0 for that v1. In B/024L-no the review called v1 "strong but partial"; the independent task-success rule passed it, while detail and time scores were 0.75.
Limits: two cases. The independent judge is also a model.
Status: observed (2) · applies to the current online Critic version

### S5 · Stop repeating a method with low expected benefit
When: a requirement has been explicitly requested and unrealized in two attempts (see R3), or the renderer profile marks it as unreliable.
Do: default to stopping this method or addressing another consequential gap. A substantively different realization can justify a further attempt, explained in the ordinary intent. This is a budget policy to validate, not a capability theorem.
Why: [renderer-bernini-r](renderer-bernini-r.md) B5 and [renderer-ditto](renderer-ditto.md) D4 and D8.
Status: observed triggers; stopping policy unvalidated

### S6 · Finish honestly
When: finishing for any reason.
Do: state the stop reason and any consequential qualification. The runtime lists unresolved requirements, so do not copy the ledger into a second form. Remaining budget is a ceiling, not a target.
Status: operating convention
