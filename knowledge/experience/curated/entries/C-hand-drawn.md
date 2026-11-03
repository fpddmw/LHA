<!-- meta {"id":"EX-C-hand-drawn","title":"Carry historical drawing evidence into new medium-specific tasks","summary":"Use the historical etching and storybook evidence for concrete medium construction. Current anime, painting and comic families still need v5 training comparisons; transfer the construction relationship and choose the marks for the requested medium.","questions":["Is there guidance for anime, painting or comic worlds?","What should I check first in a drawn or painted medium?"],"renderers":["bernini","ditto"],"layer":"condition","families":["日漫与手绘动画","绘画与版画","欧美动画与漫画"],"stages":["design","inspect"],"evidence_ids":["EV-H-B-027__short__full_knowledge","EV-H-B-041__short__full_knowledge","EV-historical-score-extract","EV-semantic-goal-review"],"version":"2","review_reference":"docs/experience-content-correction-20261103.md"} -->
# EX-C-hand-drawn: Carry historical drawing evidence into new medium-specific tasks

**Build the image in the requested medium across the scene: marks, contours, washes or flat fills should describe its surfaces and light. Historical etching and storybook runs supply useful starting evidence; the new benchmark's anime, painting and comic families still lack v5 training comparisons in this library.**

## Historical evidence

The [etching run](../evidence/H-B-027__short__full_knowledge.json) used irregular black contours, parallel and crossed hatching, ivory paper and an unmarked sky. The [storybook run](../evidence/H-B-041__short__full_knowledge.json) realized pencil lines, soft watercolor and paper texture. Both have historical independent score records in the [score extract](../evidence/historical-score-extract.md), under `lha-evaluation-v1`. These observations support concrete medium construction; their preservation scores retain the older task interpretation.

For example, a wash painting can use exposed paper for light and bleeding color at wet boundaries. Choose the behavior of the requested medium from the style library; the etching and storybook cases do not prescribe those marks for every drawn world.

## Hypotheses

- A drawn medium rebuilds every plane as a drawing: outlines, flat color or brush marks on the ground and background too ([EX-P-every-plane](P-every-plane.md), [EX-P-medium-logic](P-medium-logic.md)).
- Faces and hands are the first place an unstable drawing shows. Check them first ([EX-P-worst-second](P-worst-second.md)).
- Painted or brush-mark media may flicker frame to frame; the stability layer of the scoring still applies.

If your run produces evidence for this family, record it so it can replace this entry.

**Evidence.** Historical 027 etching and 041 storybook runs and their attributed independent scores; no v5 comparison for the current anime, painting or comic benchmark families. The family-wide points above remain hypotheses.
