<!-- meta {"id":"EX-B-held-props","title":"Hands, held props and contact points are where heavy conversions break","summary":"Under heavy conversion Bernini softens fingers into keyboards, bends or reshapes carried objects, flips face prints between frames, and lets a prop detach from the hand. Describe the grip and the prop's rigid shape, and inspect them closely.","questions":["Why does the carried object bend or change shape?","Why do fingers merge into the keyboard or the headboard?","What should I specify to keep a grip clean?"],"renderers":["bernini"],"layer":"renderer","stages":["design","inspect"],"evidence_ids":["EV-V5-train-cases","EV-V5-LEGO-planes","EV-F001","EV-F006","EV-F006-v3-000112"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-B-held-props: Hands, held props and contact points are where heavy conversions break

**Write the grip and the prop into the prompt: which hand holds which part of the object, what shape the object keeps, and where the contact happens. Then check these places in the result. Heavy conversion most often fails at contact points.**

## Failure patterns on record

Under the v5 judge, on train samples:

- A carried beam in the brick-world task bowed intermittently and its end changed from square to a rounded knob. Another round showed it warp in angle during a short interval while the minifigure's face print alternated between smile designs and the hairpiece vanished and reappeared.
- A glove surrogate (a gray mitt standing in for the glove) changed silhouette between frames and blended into a white barrier.
- In the hotel-suite scene a woman's fingers fused where they met the laptop keyboard, and in another candidate the laptop keys lost definition and melted into the bed and the hair merged into the headboard pattern.
- A phone or ball being retrieved was duplicated or faded in earlier cases ([F001](../evidence/F001.json), [F006](../evidence/F006.json)).

## What helped

The brick-world rounds that kept the beam rigid and continuous, named the C-shaped hand that cups the far end and the other that supports near the middle, and described the beam as straight assemblies of plates with regular seams had clean contacts for most of the clip, though the last short interval still showed a partly detached prop in one run. Specify:

1. The grip (which hand, which part of the object).
2. The prop's rigidity and shape: straight, constant length, regular joints.
3. The contact surface: what the hand rests on and what is behind it.
4. The face or print the figure keeps, short and stable.

Check afterwards ([EX-P-worst-second](P-worst-second.md)); a prompt cannot guarantee it.

**Evidence.** Brick-world and hotel-suite train tasks, F001, F006. Single judge, sampled frames. Which wording prevented which defect is not isolated.
