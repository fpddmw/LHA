<!-- meta {"id":"EX-P-identity","title":"Keep who they are, change what they are wearing and doing","summary":"Preserve the person at role level and keep salient attributes (age group, skin tone, build) unless the new world changes them. Keep identity wording short and spend design effort around the face; long facial inventories rebuild a different person.","questions":["How do I keep the same person in a different world?","Why did the person change into someone else?","When is changing a character's look part of the task?"],"renderers":["bernini","ditto"],"layer":"principle","stages":["design","revise"],"evidence_ids":["EV-F002","EV-F003","EV-F004","EV-F005","EV-F006","EV-D-FS4-full","EV-D-FS4-no"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-P-identity: Keep who they are, change what they are wearing and doing

**Keep each person recognizable as the same individual at the level the task needs, including salient attributes such as apparent age group, skin tone and build, unless the target world or the request changes them. State identity briefly, and spend your design effort on clothing, setting and light around the face.**

## What is and is not an identity change

The world may change a person: a human becoming a toy figure or a painted face is the task, not an error. What is not licensed is an unexplained swap. Deleting a character, replacing someone with a visibly different person, or shifting skin tone, apparent age or build for no reason in the request or the world are changes a viewer reads as a different subject. In the preview's hotel-suite request (train sample 001), the Direct long result replaced the curly-haired woman and the toddler with a straight-haired woman and an older boy, the Direct short result deleted the child, and a PE round (round 4 of its loop) rebuilt both people with a different face, hair color and apparent age. The judge capped correspondence for each of those. A Planner round from the same request kept the same two people in the new room, and the judge scored its correspondence 3.5 of 4 with only minor beats weakened. These are the difference between a recast and a swap.

## Why long descriptions backfire

Age, hairstyle and glasses are categories. A renderer can satisfy the words while reconstructing a different individual. Ditto recovered glasses in one result without recovering the face, and other descriptions produced older faces or opaque eyewear ([Ditto full](../evidence/D-FS4-full.json)). Bernini improved the pianist's resemblance while worsening a guest ([F002](../evidence/F002.json) v2), and an enumeration of hair and glasses did not recover the original identities ([F005](../evidence/F005.json) v3).

## How to apply it

1. Say who must be kept in one short clause. Do not itemize their features.
2. Keep requested costume changes explicit, and say where they stop if the face should be left alone. A below-neck boundary helped once ([F004](../evidence/F004.json) v2) and failed once ([F002](../evidence/F002.json) v3), so use it as part of a coherent design.
3. Reduce unneeded reconstruction near the face: a new collar, headwear, pose or facial lighting can invite a new person.
4. If a candidate has already lost a face, restart from the source or an earlier recognizable candidate and also reconsider what invited the change ([EX-B-chain-drift](B-chain-drift.md)).
5. In scenes with several people, check each one and their accessories. A better main subject can hide a substitution elsewhere.

**Evidence.** F002, F003, F004, F005, F006 and Ditto fewshot cases; preview runs for samples 001 and 005 (see [v5 train cases](../evidence/v5-train-cases.json)). Scene density and head-region interaction are conditions to examine, not isolated causes.
