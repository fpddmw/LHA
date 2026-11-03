<!-- meta {"id":"EX-C-film-world","title":"Film-world recasts: the setting is easy, the people are where it fails","summary":"In recasts into a film's production design, the environment converted readily. The failures in the train evidence were on the people: replaced, left in source look as cut-outs, or mismatched in light.","questions":["The set is convincing but the people are wrong. Where did it fail?","How do I recast into a film's world without replacing the people?"],"renderers":["bernini","ditto"],"layer":"condition","families":["电影与影视世界"],"stages":["design","inspect"],"evidence_ids":["EV-V5-train-cases","EV-F001","EV-F003","EV-F005","EV-D-FS4-full"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-C-film-world: Film-world recasts: the setting is easy, the people are where it fails

**For film-world requests (a named film's production design), the environment, wardrobe and props usually convert. What goes wrong is the people: a person swapped for someone else, a person left in source look as a cut-out against the new set, or source daylight on a figure in a different light.**

## What was observed

- Hotel suite (001): Direct long swapped both people; Direct short removed the child. A PE loop's fourth long round regenerated both people (correspondence 2.0) and was the delivered one. Planner first prompts kept the people (correspondence 2.8 to 3.9); the short one was lowered by cut-out hair edges and light mismatch instead ([cases](../evidence/v5-train-cases.json)).
- Dune courtyard (011): Direct recast one figure as a traveler, left the woman in her source look as a cut-out on a gray platform, and scored low on coherence and integrity ([cases](../evidence/v5-train-cases.json)).
- Historical development runs (F001, F003, F005) show the same: setting and costume arrive, faces and performer details change ([F001](../evidence/F001.json), [F003](../evidence/F003.json), [F005](../evidence/F005.json)).

## How to apply it

1. Give every person a counterpart that stays them ([EX-P-identity](P-identity.md)).
2. Put costume and light on every person, not only the lead ([EX-P-medium-logic](P-medium-logic.md)).
3. Check the people first in review ([EX-P-worst-second](P-worst-second.md)).

**Evidence status.** Four train tasks plus older runs on other settings; one judge for the scored ones.
