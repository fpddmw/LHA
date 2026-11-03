<!-- meta {"id":"EX-D-env-strong-foreground-weak","title":"Ditto replaces settings strongly and tends to reconstruct people and shapes","summary":"In the historical Ditto runs, space-station walls and Earth views arrived early while faces and eyewear changed. Spend early attention on foreground identity and structure; do not escalate background instructions once the setting is already convincing.","questions":["Where does Ditto put its effort?","What should I specify first for Ditto?","Why did the setting work while the people changed?"],"renderers":["ditto"],"layer":"renderer","stages":["design","inspect"],"evidence_ids":["EV-D-FS4-full","EV-D-FS4-no","EV-renderer-profile-20261102"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-D-env-strong-foreground-weak: Ditto replaces settings strongly and tends to reconstruct people and shapes

**For Ditto, expect the setting to change readily and the foreground to change with it. Put early effort into keeping the foreground people and structures correct, and avoid adding more background instructions once the setting already reads as the new world.**

## What is on record

These observations come from the historical 2026-10-30 Ditto runs (Wan2.1-VACE-14B with Ditto LoRA). No Ditto batch has yet been run under the current harness, so treat everything below as a starting hypothesis to be revised after the training stage.

- **Setting.** On the shared table-tennis source, space-station walls and Earth views arrived early, while faces and eyewear changed ([Ditto full](../evidence/D-FS4-full.json), [no-knowledge](../evidence/D-FS4-no.json)).
- **Descriptions can backfire.** Age, hair and glasses descriptions produced changed age or eyewear; one result recovered glasses without the person. Prefer preserving the individual through the input and the edit scope ([EX-P-identity](P-identity.md)).
- **Ornament versus silhouette.** Silk, palette and embroidery appeared across costume attempts while standing collars and broad headwear stayed absent. Inspect the requested construction separately from its ornament.
- **Warm global cast.** A correction for yellow-orange skin intensified the cast. Establish distinct facial fill and background practicals in the first design ([EX-P-medium-logic](P-medium-logic.md)).

## Use

Write the foreground clothing and structure carefully the first time. Check each person and the requested silhouette in the result. Read [the prompt-writing guide](../../../creative-loop/PROMPT_WRITING.md) for how to phrase a source restart or candidate continuation.

**Evidence.** Ditto historical fewshot cases. Pre-harness runs with a different loop and different scoring.
