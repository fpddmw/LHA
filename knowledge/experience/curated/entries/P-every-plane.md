<!-- meta {"id":"EX-P-every-plane","title":"Rebuild every plane, not just the subject","summary":"List each visible plane (subject, props, ground, background, sky, light) and say how the target medium builds it. A rebuilt figure inside an untouched photographic scene reads as a collage, and a few theme props leave the old place intact.","questions":["Why does the result still look like the original place?","Why does a stylized subject look pasted onto a real background?","What do I need to describe besides the main character?"],"renderers":["bernini","ditto"],"layer":"principle","stages":["design","inspect"],"evidence_ids":["EV-F001","EV-F004","EV-F005","EV-F006","EV-F007","EV-D-FS4-full","EV-V5-LEGO-planes"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-P-every-plane: Rebuild every plane, not just the subject

**Before writing the prompt, list every plane that is visible and, for each, say how the target medium builds it: the subject, held props, the ground, the middle distance, the background, the sky, and the light that falls on all of them. A plane you leave out stays source-like, and the result reads as a collage or as the old place with a theme on top.**

## What goes wrong

When a prompt concentrates on the main character, the renderer converts the character and keeps the rest. In a brick-world recast of a man unloading a truck, a prompt that built the minifigure and the beam but not the truck, hedge, sky or ground produced a plastic figure standing in a photographed yard. The figure, beams and truck bed were converted in some videos and the hedge, trees, barrier and sky were not. This happened with the plain request, with a Critic-guided loop, and with a Planner's first prompt. The same pattern appears for environments: space-view windows and clothing arrived in a gym while the gym walls and equipment persisted ([F004](../evidence/F004.json), [F005](../evidence/F005.json)).

The fix was to enumerate. The version that named the truck side as staggered white bricks with studs, the bed as black studded plates, the timber as tan plates with visible seams, the hedge as green brick stacks, the trees as segmented trunks with clustered leaf pieces, the barrier as chunky interlocked bricks and the ground as gray baseplates came out as a fully built world. The prompt got longer, but every sentence named a plane and its construction.

## How to apply it

1. List the planes in the shot, including the ones in the first second and the last second. A close foreground surface at the start of a moving shot counts.
2. Write one construction clause for each plane in the target medium's own terms. See [EX-P-medium-logic](P-medium-logic.md).
3. Give light its own clause: what it falls on and what it does ([EX-P-light](P-medium-logic.md)).
4. If the prompt is already near the renderer's text limit, shorten the preservation language before shortening a plane. See [EX-B-text-budget](B-text-budget.md).
5. When you review a result, look at the planes you did not describe first. They are the ones most likely to be unchanged.

A request that asks for a mixture of live action and a stylized element, such as an animated character in a real room, is the exception. Then keep the real planes real and say so.

## Exception for appearance-only requests

If the request changes only a surface treatment of one subject, the other planes are meant to stay. Check the request's wording before listing planes you should rebuild.

**Evidence.** Brick-world task, train sample 026, long and short prompts: Direct, a PE loop and a Planner loop, v5 judge reasons and sampled frames (see [the v5 case record](../evidence/v5-lego-planes.md)). [F004](../evidence/F004.json), [F005](../evidence/F005.json), [F006](../evidence/F006.json), [F007](../evidence/F007.json) and the Ditto table-tennis case. One source video for the brick finding; the environment cases are older and used other renderer setups.
