<!-- meta {"id":"EX-C-short","title":"Short requests need a source-specific realization of the target world","summary":"For a short request, anchor the target in the source's distinctive spatial relationships. When a detailed prompt still produces a generic scene, revise the discriminating geometry and staging rather than merely making the prompt longer.","questions":["The request is one sentence. What do I have to add?","Why did a short-prompt result keep the theme but lose the scene?"],"renderers":["bernini","ditto"],"layer":"condition","tracks":["short"],"stages":["design","inspect"],"evidence_ids":["EV-V5-train-cases","EV-V5-case-reading"],"version":"2","review_reference":"docs/experience-content-correction-20261103.md"} -->
# EX-C-short: Short requests need a source-specific realization of the target world

**A short request leaves the visual realization to you. Anchor the target world in the distinctive arrangement of this source: which forms stand where, how they relate and how the camera sees them. Naming the theme and asking to keep the layout can still produce the theme's familiar scene instead of this one.**

## What was observed

In the temple-to-jungle-ruins task (005 short), the Planner and PE first candidates lost recognizable layout (correspondence 2.0 and 2.4). Their prompts were already detailed: 227 and 203 words, explicitly naming towers, a long gallery, a wide composition and a steady or fixed camera. The result was a smaller, more frontal ruin. This was failed spatial realization, not a failure to expand the short request.

The PE second prompt anchored the broad blunt-topped foreground tower, two narrower towers behind it, the gallery receding left, its continuous roofline and the courtyard footprint. Its result retained more of that configuration (correspondence 3.3). Read the [prompts, scores and comparison](../evidence/v5-005-short-case.json). A useful explanation is that the first design allowed a familiar jungle-ruin composition to displace the source-specific configuration. The later wording supplied more discriminating spatial anchors; its seed also changed.

For example, a long building seen obliquely can be anchored by its receding roofline and the foreground structure it passes behind, then rebuilt in the target world. Pick the relationships that identify this shot; tower counts and courtyard shapes belong to the observed example.

The hotel-suite short task retained the people and layout (correspondence 3.9) but had cut-out edges and a degraded laptop. There the useful next work concerns integration and structure, not additional layout instructions ([complete record](../evidence/v5-001-short-case.json)).

## How to apply it

1. Identify the relationships that distinguish this source from a generic scene of the target type, and express them with the intended transformation ([EX-P-moment](P-moment.md)).
2. Assign each source element a counterpart in the target world ([EX-P-counterparts](P-counterparts.md)). The request will not do this for you.
3. Rebuild every plane, since a short request does not enumerate them ([EX-P-every-plane](P-every-plane.md)).
4. Keep the prompt inside the renderer's text limit ([EX-B-text-budget](B-text-budget.md) for Bernini).

**Evidence.** 005 short supplies the layout contrast; 001 short supplies a different failure on the same task track. One judge and one seed per attempt. The spatial-anchor recommendation is a working explanation, not an isolated wording experiment.
