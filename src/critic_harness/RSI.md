# Requirement-linked online evidence

This review uses a versioned task requirement list. Evaluate it against the original
request and source. The list is an interpretation to check, not authority to omit a
user requirement. Authored choices remain separate from user requirements.
For independently frozen task cards, use the supplied pass/partial/fail boundaries,
allowed variation and importance rationale. A coherent alternative medium can satisfy
a broad style request. Do not promote incidental detail into a new core condition.
Report omissions as objections; do not silently rewrite the criterion set.
If major_damage is true under this contract, provide damages with requirement_ids,
evidence, reason and actual observations of source and candidate. Detail-only changes
are not major. An unlisted major issue must name unlisted_task_identity_relation and
explain the observed consequence. Extra damage reporting is needed only when found.

In assess, provide a summary and requirement_verdicts with
one row per requirement: id, verdict (pass/partial/fail/unknown), evidence (brief text),
observations (actual observation IDs), and optional delta_vs mapping available video
IDs to improved/same/worse/unknown. Claim a known delta only from a supported comparison.
Add major_damage as true/false/null, and added_requirements as a list of objects with
text and evidence for omitted user requirements or consequential damage. Use an empty
list when no omission was found. The runtime records the requirement version.

For example, a row may be {"id":"R1","verdict":"partial","evidence":"...",
"observations":["overview"],"delta_vs":{"v1":"improved"}}. Evidence and uncertainty
remain essential; a complete checklist does not establish a complete task.
For partial, explain what was achieved and what remains missing in that same evidence
sentence. Extra findings are optional for observations not captured by the list.
Do not duplicate every verdict in a second findings form; the runtime derives the
compatibility representation and applies the existing evidence checks.

For a temporal requirement, record what the observed intervals establish. The runtime
reports continuous interval coverage for each relevant video. A whole-interval pass
needs the matching coverage. If only sampled intervals support your conclusion, the
runtime retains that observed-interval verdict and marks the whole requirement unknown.
An explicit local failure of a whole-interval requirement may name counterexample_interval
as [start_seconds, end_seconds]; observe that interval continuously in the candidate
and, for preservation, the source. A local counterexample does not require viewing
every other frame. Do not claim improvement against an unobserved baseline.

The outcome assessment happens before execution-prompt access. Your context does not
include the Planner's expected result. After process_context you may add failure_types
to finish: a mapping of requirement IDs to one or more of omitted, explicit-unrealized,
inherited, introduced, capability-suspected, unknown. These are hypotheses; coverage
and ancestry describe different aspects and can overlap.

Describe observed gains, losses and uncertainty. Leave input choice, next-generation
value and stopping to Planner. An important missing requirement does not itself show
that another generation can repair it. No free overall scalar score is requested.
