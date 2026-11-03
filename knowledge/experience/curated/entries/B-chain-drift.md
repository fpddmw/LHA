<!-- meta {"id":"EX-B-chain-drift","title":"Continuing from a candidate did not reliably help on Bernini; choose the input for what it still contains","summary":"On Bernini, five train-sample continuations from an earlier candidate moved stability by -1.0 to +1.1 with no consistent direction. Continue from a candidate only when it holds what you need next; otherwise restart from the source with a rewritten full prompt.","questions":["Should I continue from my last candidate or restart from the source?","Why did a repair make other things worse?","Which input keeps the information I need?"],"renderers":["bernini"],"layer":"renderer","stages":["revise"],"evidence_ids":["EV-V5-train-cases","EV-batch-facts","EV-F002","EV-F003","EV-F004","EV-F006","EV-F007","EV-B-024-full"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-B-chain-drift: Continuing from a candidate did not reliably help on Bernini; choose the input for what it still contains

**Treat the choice between continuing from a candidate and restarting from the source as a decision about information, not a default. Continue when the candidate holds what the next step needs and the remaining change is compatible with it. Restart from the source, with a freshly written full prompt, when the candidate has lost something you need, or when its defects are the kind that compound.**

## What the records show

Five continuations from an earlier Planner candidate were scored under the v5 standard on train samples (brick world long and short, jungle ruins long). Their stability change (temporal consistency plus visual integrity, relative to the parent) was +1.1, +0.7, -0.5, -0.5 and -1.0. Three of the five lowered at least one of the two dimensions. Conversion improved in some, because the child inherited the parent's gains: in the brick-world task the second round rebuilt the scenery and the fourth, continuing from it, finished the world and recolored the truck. Other children lost faces or added drift. No consistent direction appears, so this entry does not recommend either route in general.

Earlier fewshot batches point the same way. Three third-attempt continuations came from candidates with no reported major damage, and four source restarts followed damaged candidates ([batch facts](../evidence/batch-facts.json)). Four of seven selections went back to an earlier candidate. Each record also changed prompts and seeds, so route and prompt effects are not separate.

A controlled pair exists for a sample that is not part of the main comparison: the same prompt and seed rendered once from a prior candidate and once from the source. Both outputs were produced and are on disk but have not been scored, and sampled frames show both converted with no visible collapse. It cannot settle the question.

## How to decide

- **Continue** when the candidate already holds the world you want and the next change is compatible with it (a sleeve, a prop, a missing plane). State only the new change plus a short clause on what to keep.
- **Restart from the source** when a face or required action has been lost, when the candidate carries an artifact you do not want inherited (halo edges, melted contacts), or when the next change would reverse a large part of the current one. Bring the winning wording from the candidate into a new full prompt rather than restating it as a patch.
- **Recover** a lost face from the source or an earlier recognizable candidate ([EX-P-identity](P-identity.md)).
- Look at stability on the child, not just the repaired item ([EX-P-worst-second](P-worst-second.md)).
- Keep the earlier candidate available; a worse child costs nothing if you can still choose the parent ([EX-P-compare-retained](P-compare-retained.md)).

## Open question

Whether chained renders compound artifacts on average is untested here. The next training batches carry more continuation pairs; a revision of this entry should wait for them.

**Evidence.** v5 scores for train-sample parent/child pairs ([v5 cases](../evidence/v5-train-cases.json)), batch facts, F002, F003, F004, F006, F007 and the Bernini fewshot.
