<!-- meta {"id":"EX-B-emission-binding","title":"Glow can attach to the nearest support instead of the intended edge","summary":"On Bernini, requested emission appeared under a table or on arches instead of on the intended perimeter. Describe the glowing edge and the unlit support as a contrast, and look at where the light lands.","questions":["Why does the glow appear on the wrong object?","How do I make only one edge emit light?"],"renderers":["bernini"],"layer":"renderer","stages":["design","inspect"],"evidence_ids":["EV-F004","EV-F007"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-B-emission-binding: Glow can attach to the nearest support instead of the intended edge

**When a prompt asks for something to glow, name the glowing part and the neighboring part that stays dark, as a pair. Bernini repeatedly put the light on the support beneath the intended object.**

In the table-tennis arena, blue emission appeared below the table or on curved supports instead of on the tabletop perimeter. The round that described the four edges of the purple tabletop in perspective and said the red arches stayed unlit gained the intended edge and the saved review passed it ([F004](../evidence/F004.json) v2). Repeating the word "rim" in capitals added less than the edge's orientation, attachment and contrast. F007's roof strips and light bands showed related attachment issues ([F007](../evidence/F007.json)).

When the relation was already explicit and it still bound elsewhere, change the geometry or conditioning rather than a louder category word ([EX-P-spend-attempts](P-spend-attempts.md)). Give the surrounding light its own clause ([EX-P-medium-logic](P-medium-logic.md)).

**Evidence.** F004 v1 and v2; F007. Two source scenes; the successful prompt also changed other clauses.
