<!-- meta {"id":"EX-P-counterparts","title":"Give each source element a counterpart in the new world","summary":"Map each important source element to a specific, fitting counterpart (a glove to a C-shaped brick hand, a plank to a stack of tan plates) and name the carrier of each effect. Generic theme decoration does not do this work.","questions":["How do I translate source objects and actions into another world?","Why did the effect appear on the wrong part?","Why does the result look like decoration rather than adaptation?"],"renderers":["bernini","ditto"],"layer":"principle","stages":["design","revise"],"evidence_ids":["EV-F004","EV-B-FS4-full","EV-D-027-full","EV-H-B-fewshot_004__long__no_knowledge","EV-V5-LEGO-planes"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-P-counterparts: Give each source element a counterpart in the new world

**For each important element of the source (a person, a held object, a surface, a gesture), decide what it is in the target world and say so in terms of that world. Name which part carries each effect, relative to its neighbors. Counterparts adapt the moment; extra theme objects only decorate it.**

## Translation, not addition

A recast succeeds when a viewer who knows the source can find each element again, transformed: a gloved hand holding a plank becomes a yellow C-shaped brick hand holding a rigid beam made of plates; a bucket lifted from a river becomes a painted bucket in the same hand. A result that adds theme props around an untouched action has decorated the old scene.

## Name the carrier

When an attribute lands on the wrong part, say what the right part is relative to what is near it, before making the attribute stronger. A glowing perimeter of a table appeared under the table until the prompt described the edge and the unlit supports separately ([F004](../evidence/F004.json), v2). For a required repair of an existing object's shape, anchor that instance to its neighbors and footprint; for a replacement, describe the new construction without carrying over the old part's role. A Ditto dome edit that asked for a shape repair produced a second dome ([Ditto dome](../evidence/D-027-full.json)), and a Bernini dome request that simply named the dome also worked ([Bernini etching](../evidence/H-B-027__short__no_knowledge.json)). Both outcomes are on record; the relational wording is a recommendation, not a measured advantage.

## Say what is wanted

Describe the arrangement you want. A prompt that only suppresses a symptom leaves the competing instruction in place, so resolve the surrounding conflict as well as asking for the opposite.

## How to apply it

1. List the source elements that matter to the moment.
2. Write one counterpart for each in the target medium's terms ([EX-P-medium-logic](P-medium-logic.md)).
3. For any effect that must sit on a specific part, name that part and what is beside it.
4. Check each candidate for elements you did not map. They tend to remain source-like.

**Evidence.** F004 (table edge light), Ditto dome and etching cases, the older Bernini fewshot and the brick-world case. Wording, seed and input changed together in several of these, so the carrier wording is a working preference.
