<!-- meta {"id":"EX-P-spend-attempts","title":"Spend attempts on different realizations, and keep what you had","summary":"Use remaining generations to try a genuinely different construction, input or scope, not a restated version of what failed. Keep earlier candidates as options. In a fixed-budget task, use the full allowance before choosing.","questions":["What should I change when a second attempt fails the same way?","How do I use my remaining generations?","Should I stop after one good result?"],"renderers":["bernini","ditto"],"layer":"principle","stages":["revise","deliver"],"evidence_ids":["EV-B-003","EV-H-D-benchmark__003__short","EV-H-D-024__long__full_knowledge","EV-F003","EV-F005","EV-V5-train-cases"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-P-spend-attempts: Spend attempts on different realizations, and keep what you had

**When an attempt fails the same way as the last, change the realization: a different construction, a better-suited input, a resolved design conflict, or a fresh sample. A stronger restatement of the same prompt rarely changes the result. Keep every earlier candidate available for the final choice, and in a task with a fixed budget use all of it.**

## Why wording-only retries stall

When a required operation fails after it was already explicit, adding emphasis leaves the underlying conflict in place. A glitch effect added colored blocks without displacing the scene strips; a costume's silhouette stayed absent across restatements; a requested table edge kept lighting the supports until the edge was described relative to them ([B-003 study](../evidence/B-003.json), [Ditto glitch](../evidence/H-D-024__long__full_knowledge.json), [F003](../evidence/F003.json), [F005](../evidence/F005.json)). Use direct specification first when the relation was truly missing, and a changed realization when it was already explicit.

## What counts as a different attempt

- **A new construction.** A different way to build the same element (rows of stacked plates instead of a single block).
- **A different input.** The source, or an earlier candidate that kept what you need. See [EX-B-chain-drift](B-chain-drift.md).
- **A resolved conflict.** Remove a preservation demand that fights the target before adding more detail.
- **A resample.** A repeat with another seed is legitimate, and should be recognized as a resample.

## Early results and the full budget

An adequate early candidate is worth keeping. It is also not a reason to stop. In the preview, three of the six train Planner tasks (hotel-suite long and short, jungle-ruin short) delivered after one generation although four were allowed. In the jungle-ruin long task, which used its attempts, the summed v5 score rose from 15.5 at round 1 to 18.9 at the delivered round 3. One task cannot show that more attempts help, but it shows that a first result is not always the best one available.

Under the fixed-budget completion policy an earlier candidate stays available for final selection, so exploring alternative realizations with the remaining allowance puts nothing already earned at risk. Explore with the allowance, then choose.

**Evidence.** B-003, Ditto glitch and costume cases, F003, F005, and the preview Planner runs. Whether additional attempts improve delivered scores is not established. In the six preview train comparisons the delivered-minus-first gain averaged about 0.9 summed points over five dimensions for the Planner and 0.7 for the PE loop; most of each comes from one task, and several tasks delivered their only attempt.
