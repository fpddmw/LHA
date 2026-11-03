<!-- meta {"id":"EX-B-text-budget","title":"The 512-token text limit makes every sentence compete","summary":"Bernini accepts 512 encoder tokens including its official prefix. Long preservation clauses use space that construction clauses need, and prompts over the limit are refused before any render.","questions":["How long can a Bernini prompt be?","What should I cut when the prompt is too long?","What happens when the prompt exceeds the limit?"],"renderers":["bernini"],"layer":"renderer","stages":["design"],"evidence_ids":["EV-V5-train-cases","EV-PE-token-limit","EV-H-B-benchmark__001__long"],"version":"2","review_reference":"docs/experience-content-correction-20261103.md"} -->
# EX-B-text-budget: The 512-token text limit makes every sentence compete

**Bernini encodes at most 512 tokens including its official prefix. Spend them on the planes and the construction rules, and say what to keep in one short clause. A prompt over the limit is refused before rendering and the attempt is not charged.**

## What the records show

Brick-world prompts that listed every plane and rendered ran 271 to 313 words. In the preview, the PE loop's first prompts of 340 and 351 words (brick-world long and short) were refused by the tokenizer with "Prompt exceeds tokenizer limit; automatic truncation is disabled", and no render started. The PE baseline has its own recovery path: it can request up to two compressed rewrites after a length refusal and retain an earlier candidate if no further render succeeds. Planner does not use that automatic compactor. It receives the refusal and writes its own revised prompt before resubmitting. A 313-word Planner prompt passed, so the word count alone is not the limit: tokens are, and names, punctuation and rare words consume more of them.

PE prompts in the preview carried more preservation wording than Planner prompts (about seven preservation words per prompt against four). That wording shares the budget with the construction clauses.

## How to use it

1. Write the prompt in this order: the target world's planes and construction, the light, the key action, then one clause for what must stay.
2. If you are near the limit, shorten preservation and repeated adjectives first. Merge repeated descriptions of the same thing.
3. Keep identity short ([EX-P-identity](P-identity.md)).
4. A refusal costs no render, but it costs a turn of the clock; check length before submitting a long prompt.

The limit counts tokens, not words; unusual names and punctuation consume more.

**Evidence.** Preview prompts for train samples (word counts from the records), the PE token-limit evidence, the historical palace long prompt. The cutoff itself is in the renderer configuration; the effect of dropping preservation clauses on results is not isolated.
