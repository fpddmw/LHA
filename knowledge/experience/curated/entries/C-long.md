<!-- meta {"id":"EX-C-long","title":"Long requests list many details; carry the ones that define the world, within the text limit","summary":"A long request names planes, costume, light and a camera behavior. Carry them in order of what makes the world recognizable, and check each named item in the delivered video, because a long list can exceed what one prompt carries.","questions":["The request lists many details. Do I need to carry them all?","How do I check a long request against the result?"],"renderers":["bernini","ditto"],"layer":"condition","tracks":["long"],"stages":["design","inspect","deliver"],"evidence_ids":["EV-V5-train-cases","EV-V5-LEGO-planes","EV-PE-token-limit","EV-V5-case-reading"],"version":"2","review_reference":"docs/experience-content-correction-20261103.md"} -->
# EX-C-long: Long requests list many details; carry the ones that define the world, within the text limit

**A long request is a checklist of what the judge will look for: the planes it names, the costume, the light, a camera behavior. Turn each into a clause in the prompt, in the order that makes the world recognizable, and check each against the delivered video. The prompt has a size limit, so compress source description before you drop a requested detail.**

## What was observed

- In the hotel-suite task (001, long), the Planner's two first candidates (236 and 246 words) carried the request's items and all of its instruction labels passed.
- In the temple task (005, long), the request asks that the original camera movement gradually reveal the temple's scale. The Planner's first and second candidates were marked partial on correspondence (2.5, 2.3) and the judge said the viewing position and layout were abandoned. The third candidate passed every labeled requirement (correspondence 3.6, 15.5 to 18.9 summed over five dimensions) ([cases](../evidence/v5-train-cases.json)).
- In the brick task (026, long), naming each plane was not sufficient in the first prompt. A later continuation foregrounded the failed environmental construction and converted more of the scene ([plane record](../evidence/v5-lego-planes.md)). The PE loop's first brick-world prompts of 340 and 351 words were refused by the tokenizer, while a 313-word Planner prompt passed ([limit record](../evidence/pe-token-limit.md)).

## How to apply it

1. List the request's named items and mark which define the world (planes, costume, light) and which define the moment (camera behavior, interaction).
2. Write the world items as construction clauses ([EX-P-every-plane](P-every-plane.md)) and the moment items as the skeleton ([EX-P-moment](P-moment.md)).
3. If the prompt exceeds the limit, shorten source description first.
4. When reviewing, go through the request item by item rather than reading the video once.

**Evidence status.** Three train tasks, one judge, one seed per condition; cumulative changes across rounds, so no single clause is isolated.
