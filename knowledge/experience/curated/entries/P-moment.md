<!-- meta {"id":"EX-P-moment","title":"Define the moment before choosing what to rebuild","summary":"Before the first generation, write down who acts, what happens, in what order, where, and from which camera position. Keep that skeleton recognizable and rebuild everything else in the target world.","questions":["What must stay recognizable when the video moves into another world or medium?","Which source actions are performance material and which are old-world functions to replace?"],"renderers":["bernini","ditto"],"layer":"principle","stages":["design"],"evidence_ids":["EV-F001","EV-F001-creative-first","EV-semantic-goal-review","EV-F003","EV-F005"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-P-moment: Define the moment before choosing what to rebuild

**Write the skeleton of the source in one or two sentences before you write any style: who acts, what happens and in what order, how the space is arranged, and where the camera is. Keep that skeleton recognizable. Rebuild everything else in the target world, including how the action is carried out when the new world changes what the action means.**

## Why start here

The task is a recast: the same moment, made as part of another world or medium. Two opposite errors both fail it. A result that keeps the source almost untouched is a filter. A result that invents a new scene loses the moment. The skeleton separates what you must hold fixed from what you are free to replace.

Sort the source into three groups.

- **The skeleton.** The roles, the order of beats, the main interactions and the camera arrangement. A viewer who knew the source should recognize it.
- **Performance material.** Poses, gestures and timing. Use them where they serve the target action. A hand lifting a bucket can become a minifigure's C-shaped hand lifting a brick bucket.
- **Old-world functions.** Props or activities that exist only because of the source's setting. When the target world changes what people are doing, let the old function go and give the gesture a purpose that fits the new world. Keeping a source prop's function can hold the old scene in place under new surfaces.

## How to apply it

Name the beats with the source in view. Then ask of each item whether it belongs to the skeleton, is performance material, or is an old-world function. Write the first prompt around the skeleton and the target world together.

An explicit instruction in the request outranks this sorting. If the request says to continue a named action, that action is part of the skeleton.

Do not turn a preserved element into a list of conditions to maintain. A prompt that spends its length on "keep the same X, keep the same Y" has less room for the target world, and the renderer follows the longer description. One short clause for the skeleton is usually enough. [EX-B-text-budget](B-text-budget.md) records how this played out in one batch.

**Evidence.** [F001](../evidence/F001.json) and its [goal review](../evidence/semantic-goal-review-20261102.md): preserving basketball contacts under a martial-arts world kept the old event. [F003](../evidence/F003.json), [F005](../evidence/F005.json): a source prop's function persisted under new surfaces. Train-split development cases only. The sorting method is a working default; no controlled comparison isolates it.
