<!-- meta {"id":"EX-C-short","title":"Short requests name the world only; decide the counterparts and layout yourself","summary":"A short request gives the target world and little else. Two preview short tasks lost the source's layout and camera position when the prompt followed the request's level of detail; write the source's arrangement and its counterparts into the prompt.","questions":["The request is one sentence. What do I have to add?","Why did a short-prompt result keep the theme but lose the scene?"],"renderers":["bernini","ditto"],"layer":"condition","tracks":["short"],"stages":["design","inspect"],"evidence_ids":["EV-V5-train-cases"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-C-short: Short requests name the world only; decide the counterparts and layout yourself

**A short request names the target world and the moment in one sentence. Everything that makes the result a recast of this source, namely where things stand, what plays each role and where the camera is, is yours to specify. A prompt that stays at the request's level of detail gets a world, not this moment in it.**

## What was observed

In the preview's temple-to-jungle-ruins task (train sample 005, short), the Planner's first candidate and the PE loop's first candidate both received low correspondence scores (2.0 and 2.4). Both judge reasons say the same thing: the source's tiered towers, long gallery, lawn and wide locked camera had no identifiable counterpart, and a smaller single ruin seen from closer and lower appeared instead. The PE loop's second candidate rose to 3.3. In the hotel-suite task (001, short) the Planner's first candidate kept the people and layout (correspondence 3.9) while its visual integrity (2.4) and coherence (2.8) were lowered by cut-out hair edges and a degraded laptop ([cases](../evidence/v5-train-cases.json)).

## How to apply it

1. Write the source's arrangement in the prompt: what stands where, the camera position and movement, the main beats ([EX-P-moment](P-moment.md)).
2. Assign each source element a counterpart in the target world ([EX-P-counterparts](P-counterparts.md)). The request will not do this for you.
3. Rebuild every plane, since a short request does not enumerate them ([EX-P-every-plane](P-every-plane.md)).
4. Keep the prompt inside the renderer's text limit ([EX-B-text-budget](B-text-budget.md) for Bernini).

**Evidence status.** Two to three train tasks, one judge, one seed per condition. The pattern fits both methods in 005 and not 001 or 026. Treat it as a working pattern, not a measured effect.
