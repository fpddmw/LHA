<!-- meta {"id":"EX-B-partial-default","title":"Bernini converts what you describe and leaves the rest of the shot","summary":"Bernini can convert the subject while retaining photographic scenery, even when scenery was explicitly described. Cover the planes, then rework the construction and input support of the ones it still failed to realize.","questions":["Why is only my character converted?","Why does a plain request leave the background alone?","What does a preservation-heavy prompt cost?"],"renderers":["bernini"],"layer":"renderer","stages":["design","inspect"],"evidence_ids":["EV-V5-LEGO-planes","EV-V5-train-cases","EV-F004","EV-F005","EV-F006","EV-V5-case-reading"],"version":"2","review_reference":"docs/experience-content-correction-20261103.md"} -->
# EX-B-partial-default: Bernini converts what you describe and leaves the rest of the shot

**On Bernini, assume anything you do not describe will stay as it was. A request or a prompt that concentrates on a subject returns a converted subject in the original place. List the planes you want rebuilt ([EX-P-every-plane](P-every-plane.md)) and keep any preservation instruction to one short clause.**

## What the train records show

- **Request text alone.** For the brick-world request, the Direct result converted the figure and beams and left the truck, hedge, sky and barrier photographic. The v5 judge scored world realization 2 or lower and named an unrequested mix of toy and live-action.
- **A preservation-first loop prompt.** The PE loop's first prompt (291 words) said to preserve the camera, composition and action timing and asked for a brick pickup, but the delivered video again showed a photographic truck and yard. Its first round and the Planner's first round had the same pattern, although both already named construction for the truck and scenery.
- **Reworking the failed construction.** The later prompt led with the truck and landscape, specified their visible assembly more concretely, and continued from the already converted figure. The scenery converted; a further pass addressed the still-photographic opening panel. The [complete case](../evidence/v5-026-long-case.json) shows that input, seed and wording changed together.
- **Environment cases.** Space views and clothing appeared while gym walls and equipment persisted; a metallic train initially remained in an ordinary crossing ([F004](../evidence/F004.json), [F005](../evidence/F005.json), [F006](../evidence/F006.json)).

PE prompts across the preview averaged about seven preservation words (preserve, keep, retain, maintain, same, original) against about four for the Planner prompts. Preserved-element wording is not the same as unconverted output, but it shares the text budget with the construction clauses ([EX-B-text-budget](B-text-budget.md)).

## What this does not say

It does not say preservation wording is wrong. Identity, framing and the target action can need a short clause. It says to budget explicit design for the whole world. A described plane can still remain unchanged: then improve its realization and conditioning, rather than treating the instruction as absent.

**Evidence.** Brick-world task (train sample 026), long and short: Direct, PE and Planner ([record](../evidence/v5-lego-planes.md)); F004, F005, F006. One source video for the main finding.
