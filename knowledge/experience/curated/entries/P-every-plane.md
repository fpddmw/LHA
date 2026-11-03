<!-- meta {"id":"EX-P-every-plane","title":"Rebuild every plane, not just the subject","summary":"Describe how the target medium builds each visible plane. If a named plane still stays photographic, revise its construction, visual relationships and input support instead of adding the same object name again.","questions":["Why does the result still look like the original place?","Why does a stylized subject look pasted onto a real background?","What do I need to describe besides the main character?"],"renderers":["bernini","ditto"],"layer":"principle","stages":["design","inspect"],"evidence_ids":["EV-F001","EV-F004","EV-F005","EV-F006","EV-F007","EV-D-FS4-full","EV-V5-LEGO-planes","EV-V5-case-reading"],"version":"2","review_reference":"docs/experience-content-correction-20261103.md"} -->
# EX-P-every-plane: Rebuild every plane, not just the subject

**Before writing the prompt, list every plane that is visible and, for each, say how the target medium builds it: the subject, held props, the ground, the middle distance, the background, the sky, and the light that falls on all of them. A plane you leave out stays source-like, and the result reads as a collage or as the old place with a theme on top.**

## What goes wrong

A converted character can dominate the result while the surrounding scene stays photographic. In the brick-world task, this happened even though the first Planner prompt explicitly described an interlocking-brick pickup, tiled bed, brick barrier, studded ground and toy hedges and trees. The PE first prompt also specified the pickup and scenery. The failure was incomplete realization of stated construction, not missing object names. The same visible imbalance occurs in the older arena cases: space-view windows and clothing arrived while gym walls and equipment persisted ([F004](../evidence/F004.json), [F005](../evidence/F005.json)).

The later attempt put truck and landscape construction first and edited a candidate that already held the minifigure. It specified staggered brick rows on the opening truck panel, studded plates in the bed and stepped brick stacks in the hedge. Much more of the scene converted, although the opening white panel persisted. A later continuation rebuilt that panel as red bricks and separated the tan cargo from the red vehicle. These changes are visible in the [exact prompts and full reports](../evidence/v5-026-long-case.json).

When a plane was omitted, add its construction. When it was already specified, give the failed plane a stronger role in the design: change how its surfaces, adjoining objects and appearance over the shot are built, and choose an input that supports that change. For example, a close vehicle panel can be expressed through staggered joints and its transition into a load-bearing bed; contrasting vehicle and cargo construction can keep them distinct. Develop the equivalent relationships for the current scene.

## How to apply it

1. List the planes in the shot, including the ones in the first second and the last second. A close foreground surface at the start of a moving shot counts.
2. Write one construction clause for each plane in the target medium's own terms. See [EX-P-medium-logic](P-medium-logic.md).
3. Give light its own clause: what it falls on and what it does ([EX-P-medium-logic](P-medium-logic.md)).
4. If the prompt is already near the renderer's text limit, shorten the preservation language before shortening a plane. See [EX-B-text-budget](B-text-budget.md).
5. Review every requested plane. Compare each failed region with its actual prompt clause: supply a missing construction, or revise an explicit construction that the renderer did not realize.

A request that asks for a mixture of live action and a stylized element, such as an animated character in a real room, is the exception. Then keep the real planes real and say so.

## Exception for appearance-only requests

If the request changes only a surface treatment of one subject, the other planes are meant to stay. Check the request's wording before listing planes you should rebuild.

**Evidence.** Brick-world task, train sample 026, long and short prompts: Direct, a PE loop and a Planner loop, v5 judge reasons and sampled frames (see [the v5 case record](../evidence/v5-lego-planes.md)). [F004](../evidence/F004.json), [F005](../evidence/F005.json), [F006](../evidence/F006.json), [F007](../evidence/F007.json) and the Ditto table-tennis case. One source video for the brick finding; input, seed and wording changed together. The environment cases are older and used other renderer setups.
