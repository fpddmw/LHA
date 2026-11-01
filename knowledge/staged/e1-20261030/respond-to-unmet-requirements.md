# Respond to an unmet requirement by its failure type

[Decide to continue or stop](decide-to-continue-or-stop.md) · [Express edits](express-edits.md) · [Choose an editing input](choose-editing-input.md)

Version E1 (staged). The right next step depends on why the requirement is unmet, not only on the fact that it is unmet. The Critic's process diagnosis (after `process_context`) often states whether the instruction was present in the prompt; use it.

### R1 · Use failure distinctions when they clarify the action
When: a review reports an unmet or partial core requirement.
Do: use relevant distinctions in the ordinary intent. Prompt coverage and defect ancestry can overlap:
- **omitted**: the prompt did not ask for it, or asked ambiguously.
- **explicit-unrealized**: the prompt asked for it clearly and the output lacks it.
- **inherited**: the input already lacked it (a candidate used as input).
- **introduced**: the last edit broke something that was fine in its input.
- **capability-suspected**: explicit-unrealized at least twice, or flagged in the renderer profile.
- **unknown**: the evidence does not resolve it.

Why: the recorded successful repairs and the recorded futile repeats fall into different types. Orientation repair on 003 supports correcting an omitted relationship; repeatedly unrealized geometry and identity need a different explanation.
Status: operating convention

### R2 · Omitted → state the wanted visible state explicitly
When: type omitted, especially coarse properties such as subject orientation, presence of an object, or which region receives an effect.
Do: describe the wanted state positively. Choose an input that still contains the information that realization needs; these examples used source restarts but do not isolate the advantage of restarting.
Why: B/003S v1 and D/003S v1 both turned a back-facing reader toward the camera when orientation was not stated. Stating "back to the camera" fixed it in both renderers (B/003S v2, D/003S v2).
Limits: fine geometry did not respond the same way (see R3, B/027S).
Status: observed (2 renderers)

### R3 · Prefer a different realization over stronger emphasis after explicit failure
When: type explicit-unrealized.
Do: default to one substantively different attempt before stopping this method. Consider a new visual realization, removing a conflicting design choice, or another suitable input. A seed-only retry tests sampling variability. A concrete new hypothesis can justify an exception within budget; two failures do not prove incapability.
Why: louder or longer wording never fixed an explicit-unrealized requirement in this batch:
- 024 glitch displacement, all four loops (B and D, 3 attempts each);
- D/001L standing collars and headdress silhouette (3 attempts);
- B/FS4-no glow placement on the tabletop rim (3 attempts);
- face identity and glasses in all four fewshot loops.

Later prompts were longer: B/024L-no grew from 259 to 346 tokens without independent gains.
Limits: none of the attempts held the prompt fixed and varied only the seed, so sampling noise is not separated from wording.
Status: mixed · recurring observations across two renderers; the stopping policy is unvalidated

### R4 · Prefer wanted states over lists of unwanted attributes
When: trying to remove a color cast, an extra object or an artifact.
Do: lead with the wanted state ("neutral off-white paper", "natural skin tones"). Avoid making the unwanted attribute the main visual concept. Short negatives remain available; these cases do not isolate a causal effect of negation.
Why:
- D/001S v3 asked to "neutralize the strong yellow-orange cast" on a candidate, and the faces became more yellow.
- D/027S-no v2 listed "no yellow wash, no faded edges, no added arches", and all of them appeared.
- B/FS4-no v2 asked to "remove their thick cyan glow" from supports on a candidate that had it, and the support glow persisted.

Limits: in D/027S-no v3 the successful attempt changed the seed and added positive descriptions, while some negations remained. Which change mattered is unresolved.
Status: mixed → treat as a strong default

### R5 · Introduced regression → go back to an input without it
When: type introduced, where the last edit damaged something its input had.
Do: prefer a suitable parent or sibling when the latest edit introduced the defect. Continuing that candidate needs a concrete advantage worth its inherited risk.
Why:
- D/024L-full v3 branched from v1 to avoid v2's opaque bars, and its review confirmed improved scan-line flicker over v1.
- Patching on top made things worse in D/027S-full v3 (an extra dome) and D/001S v3 (stronger cast).

Status: observed (3)

### R6 · Naming lost identity is a weak reconstruction strategy
When: type inherited, where a candidate lost an identity detail (glasses, hairline, face shape) that the source had.
Do: prefer a source or earlier candidate that still shows the identity, with fewer competing changes near the person. Naming a category such as glasses can regenerate the category without restoring this individual; treat precise identity restoration on the damaged candidate as a low-confidence hypothesis.
Why: B/FS4-full v3 added "thin dark rectangular eyeglasses" on v2; the review still found no source-faithful glasses. On Ditto, all six fewshot prompts named the glasses; one kept faithful glasses, and three produced opaque eyewear or a visor (D/FS4).
Status: observed (2 renderers)

### R7 · Drop authored additions that collide with preserved structure
When: a preserved object is hidden or replaced by something the Planner added, not by something the user asked for.
Do: remove or lighten that authored addition first, for example by recoloring an existing garment instead of replacing it.
Why:
- B/003S v2 introduced a floor-length robe that hid the chair; v3 kept the original jacket, recolored it, and the chair returned.
- B/001S v3 narrowed the edit to fabric and background, and face drift fell from fail to partial.

Status: observed (2)
