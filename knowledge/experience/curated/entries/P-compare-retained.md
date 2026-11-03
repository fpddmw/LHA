<!-- meta {"id":"EX-P-compare-retained","title":"Choose the delivery among all retained candidates, judged on the whole recast","summary":"Compare every retained candidate on how fully the world was rebuilt, whether the moment is still recognizable, and how stable and clean it is. The newest or the most repaired version is not automatically the best, and a polished result that kept the old scene is not finished.","questions":["Which candidate should I deliver?","Is the latest repair better than an earlier version?","How do I weigh conversion against stability?"],"renderers":["bernini","ditto"],"layer":"principle","stages":["deliver","revise"],"evidence_ids":["EV-historical-score-extract","EV-batch-facts","EV-F003","EV-F004","EV-F006","EV-F007","EV-V5-train-cases"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-P-compare-retained: Choose the delivery among all retained candidates, judged on the whole recast

**Put every retained candidate side by side and ask three things of each: how much of the scene is rebuilt in the target world, whether it is still recognizably the same moment, and how stable and clean it is across the whole duration. Deliver the one that is best on all three together. Repairing the newest complaint can still produce a worse answer than an earlier candidate.**

## Three questions, kept together

A candidate can be clean because little changed, and a candidate can be bold with an unstable end. Neither is the goal. In the preview, a brick-world candidate whose scenery stayed photographic had steady frames and clean geometry but did not rebuild the world; a later candidate that rebuilt the world carried a short photographic panel at the start and a cluttered last frame. Weigh both conditions, and let the request's emphasis decide close calls.

A restored guitar can improve on a broken second attempt and still lose to the first attempt as an overall performance ([F003](../evidence/F003.json), [F004](../evidence/F004.json)). Four of seven earlier fewshot selections returned to an earlier candidate ([batch facts](../evidence/batch-facts.json)). In the preview's train tasks, the two Planner loops that made several attempts delivered a later round (brick-world long, round 4 of 4, and jungle-ruin long, round 3 of 4), while the other train Planner tasks delivered their only attempt. The PE loops delivered a later round in one train task (hotel-suite long) and their first round in the others. Do not assume either direction.

## Two cautions

- **A missing obsolete prop is not a defect** when the old function does not belong to the new scene. A target interaction that never becomes readable is.
- **A report's severity label is not your priority.** Use the report to find evidence, then judge against the original request.

## How to apply it

1. Keep every candidate reachable ([EX-P-spend-attempts](P-spend-attempts.md)) and compare them in one view for the first and last second and for the planes you described.
2. Judge the whole recast: world, moment, stability. Treat unknown coverage as a gap to check.
3. Record why you choose one candidate over another before you deliver.

**Evidence.** Preview train tasks (v5 scores, same judge), historical fewshot selections, F003, F004, F006, F007. The tradeoff cases are descriptive; no experiment tests the weighing.
