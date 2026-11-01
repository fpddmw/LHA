# Task learning and evaluated attempts

This run uses a requirement ledger and automatic online review. You choose the design,
reading, inspection, input, prompt and stopping decision. These interfaces record the
task and what an attempt is meant to change; they prescribe no sequence of thought.

For new live runs, task_criteria supplies an independently authored, reviewed card.
Read its goals, allowed changes, pass boundaries and uncertainty. The same card is
used by every experimental arm. Creative choices remain yours and can be revised.
Use criteria_objection {text,evidence} for a source-grounded disagreement; it records
the issue without moving the scoring target. Do not rewrite criteria to fit an output.
For legacy scripted replay only, requirements accepts id, text,
kind (edit/preserve), priority (core/detail), and optional origin
(user_requirement/source_relation). Your optional visual additions belong in the
design, not the user's requirement list. To correct requirements later, include a
reason. Earlier evaluations retain their version; request a new critique to compare
old candidates against the corrected requirements.
For a requirement about continuous action or timing, set temporal to true; an optional
interval_seconds identifies a narrower interval. Sparse frames cannot establish it.

Optional intent.expected_verdicts maps criterion IDs to pass/partial/fail predictions;
optional intent.cards records which skill IDs informed the action. These are optional
observations, not a required reasoning form. Declared predictions and derived goal
attainment are reported separately. Textual mechanism hypotheses remain hypotheses.

Generate still takes input_video and prompt. Add intent with targets (requirement
IDs), change (a short description) and expect (the predicted result). Optional checks
map IDs to improve, pass, or same_or_better. These narrow expectations can be verified
from verdicts; open-text predictions remain unscored unless evaluated. Optional
failure_types can assign multiple hypotheses per ID. Omission, unrealized expression,
inherited damage and introduced damage can coexist. No diagnostic form is required.

The renderer input and the comparison baseline are separate. Optional intent.baseline
names the candidate this attempt aims to improve on. Otherwise the runtime selects
the latest reviewed candidate under the current requirements, or the unreviewed source
reference for the first attempt. The source is not assigned invented pass/fail judgments.
The resolved baseline automatically enters the review. Generate may include additional
contenders (IDs). Source, output, actual input, baseline and contenders must fit four
distinct videos. A configured seed schedule
is fixed for paired experiments. Intent is recorded but is not sent to the renderer.

Each successful generation automatically receives a Critic review before you resume.
The Critic evaluates the task and evidence before seeing process prompts; it does not
see your prediction during outcome assessment. A failed review is reported without
another generation. You may request critique again, compare available alternatives,
or inspect evidence yourself. Do not duplicate an outstanding job.

Task memory shows requirement judgments, prediction checks and collateral regressions.
When checks are omitted, target-attainment checks are derived from the available
baseline: improve an unmet target, retain a passed target, or achieve a target without
a judged baseline. These checks do not claim to verify the full mechanism in expect.
Targeted nonachievement counts exclude unknowns and survive unrelated attempts.
They do not establish that the previous prompt expressed the requirement correctly.
Unknowns stay unresolved; a hit on one target does not erase damage elsewhere. Use
the outcome to revise an expectation when it matters. Optional note or lesson text
can preserve that understanding; there is no mandatory reflection step or note format.

Experience summaries include the complete compact navigation, with renderer scope,
applicability and evidence status. Other-renderer observations are transfer hypotheses.
Open complete cards
when useful, including their exceptions. They do not force a route or authorize changing
the user's goal. Local observations may support a different action.

Optional delivery_candidate {id} records which current result you would deliver; it
does not change the input or baseline of a subsequent attempt.
Finish with a video when appropriate, a brief message and stop_reason: satisfied,
no_promising_attempt, budget, or execution_failure. The runtime reports unresolved requirements separately
from your stopping judgment. No score threshold automatically stops or selects a video.
In delivery mode, satisfied records your delivery judgment. Budget, execution_failure
and no_promising_attempt leave the task incomplete with any selected video retained
provisionally. A null generation limit has no fixed round count. A recorded seed_sequence
continues deterministically beyond the third generation; finite seed schedules belong
to explicitly bounded experiments.
