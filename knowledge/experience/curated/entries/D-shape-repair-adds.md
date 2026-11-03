<!-- meta {"id":"EX-D-shape-repair-adds","title":"On Ditto, a shape-repair pass can add an object instead of fixing one","summary":"A request to make a dome compact produced a second dome. For an important instance repair, anchor the existing object to its neighbors and footprint, or restart from an intact earlier input, rather than continuing to sculpt a duplicated one.","questions":["Why did my correction add another object?","How do I repair the shape of one object on Ditto?"],"renderers":["ditto"],"layer":"renderer","stages":["revise"],"evidence_ids":["EV-D-027-full","EV-H-D-024__long__full_knowledge","EV-H-D-027__short__no_knowledge"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-D-shape-repair-adds: On Ditto, a shape-repair pass can add an object instead of fixing one

**When you need an existing object reshaped, describe that instance relative to its base, its neighbors and the footprint it occupies. If a candidate already contains a duplicated or restructured landmark, compare restarting from an earlier intact input with continued sculpting; continuing is more attractive when the error is only a surface treatment on an intact shape.**

In the historical Ditto 027 run, a request for a compact dome produced an additional dome ([Ditto dome](../evidence/D-027-full.json), [no-knowledge](../evidence/H-D-027__short__no_knowledge.json)). A glitch edit later in the same set kept useful appearance on an earlier branch without the overlays the later pass introduced ([Ditto glitch](../evidence/H-D-024__long__full_knowledge.json)).

A world recast can deliberately remove or repurpose a structure. Choose the target role first; restoring an obsolete structure can recreate the old scene ([EX-P-moment](P-moment.md)).

**Evidence.** Three historical Ditto cases; not retested under the current harness.
