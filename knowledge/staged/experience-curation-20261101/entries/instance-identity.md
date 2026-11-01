# EX-instance-identity: Describing a category does not identify the same individual

Version: 1. Status: draft; repeated historical online observations, explanatory hypothesis. Scope: recorded Bernini/Ditto near-person and fewshot edits. Reworks R6/X4 and relevant B4/D3 material.

**More identity adjectives can add reconstruction instructions without establishing correspondence to the source person.** Age, hair and glasses describe categories of appearance. The desired preservation concerns a particular individual across the transformation.

## Why the distinction matters

In the fewshot scene, environment and clothing changes succeeded while faces and eyewear changed. The prompts already named identities, heads, hairstyles or glasses. Later naming rectangular glasses sometimes restored an accessory category without restoring the face; other descriptions produced opaque eyewear or a visor. The failure therefore cannot be explained simply by an omitted word for glasses.

A plausible interpretation is that the renderer reconstructs a person consistent with the described attributes and new visual context, rather than preserving the source instance. This explains why a more detailed list can be semantically faithful to the instruction while visually unfaithful to the individual. It remains a model-behavior hypothesis, not a demonstrated internal mechanism.

## Implication for planning and revision

Inspect whether the proposed input still carries the person-specific evidence the task needs. Consider whether the chosen costume, nearby lighting or headwear creates competing transformations around that evidence. A different realization or input may address a different condition than adding more identity adjectives. A concise preservation phrase can avoid unnecessary reconstruction detail, but these records do not establish that shorter wording reliably preserves identity.

When an accessory is intentionally being changed, category generation may be exactly what the user wants. Identity, accessory category and accessory shape should be interpreted against that task. A distant unresolved face should remain unresolved rather than being counted as a failed restoration.

## Evidence and counterexample

[D-FS4-full](../evidence/D-FS4-full.json) and [D-FS4-no](../evidence/D-FS4-no.json) preserve all prompts and online findings. The historical card summary reports one faithful-glasses recovery among six attempts; it also reports facial drift and examples of opaque eyewear. The recovery is an important counterexample to 'describing glasses never helps'. The packet permits inspection of individual judgments rather than relying on the aggregate slogan.

[B-FS4-full](../evidence/B-FS4-full.json) records v3 adding thin dark rectangular eyeglasses to v2 while making several environment changes. Its review still identifies unresolved identity/accessory problems. Those simultaneous changes prevent attributing the outcome to the glasses phrase alone. These examples share a source scene and are not independent samples of all human identities. Historical Critic uncertainty is retained. No new face metric or independent identity annotation was produced.

Related: [EX-input-conditioning](input-conditioning.md), [EX-design-conflict](design-conflict.md).
