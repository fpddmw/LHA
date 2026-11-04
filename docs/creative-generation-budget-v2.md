# Current generation budget

Current protocol: campaign v6, creative-continuation-v5 (2026-11-04).

Each sample, prompt form, method and seed has its own four submitted render
attempts. Direct uses one. Known unsubmitted validation failures do not consume an
attempt; submitted execution failures do. Recovery collects the original job and
never charges a second attempt for it. Unknown submissions retain ownership.

New online tasks, maintenance and final scoring have no elapsed-time deadline.
After four attempts only generation is disabled. Observation, review and final
selection remain available, and the Planner can select an earlier candidate.
Technical interruptions remain recoverable and do not imply successful delivery.

Phase reminders depend on submitted generations / configured generation limit.
Elapsed time and token usage remain operator records, with no default task time
or token stop. Explicit monetary controls and maintenance call/token allowances
retain their existing meaning. Network timeouts and dead-process detection handle
technical failure. Existing frozen runs retain explicit historical deadlines.

All new experiment inputs and generated outputs use 117 frames at 24 fps. See
[preparation and verification](fixed117-count-budget-plan.md) and the
[public launch guide](public-experiment-guide.md).
