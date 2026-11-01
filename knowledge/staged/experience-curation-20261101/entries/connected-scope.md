# EX-connected-scope: A focused revision is a coherent visual change, not a locality promise

Version: 1. Status: draft; interface fact, one motivating trace and an untested strategy hypothesis. Scope: current video-plus-text rendering interface; observed failure from Bernini. Reworks X6; relates to X3 without merging part binding into scope.

**Calling a revision small does not constrain which pixels the renderer changes.** The interface provides a video and a text prompt, with no mask or invariant region. The proposal's actual visual dependencies provide a more useful way to understand its scope.

## What the motivating attempt changed

The fewshot v3 instruction was presented as a refinement of v2. It requested brighter table glow, replaced walls and obstacles, added window construction and overhead lights, changed the floor, and reinstated glasses. Some changes belonged to the arena realization; others acted on a separate identity problem. The review found new structure/ball problems. 'Focused' described the intention, while the actual prompt specified transformations across much of the image.

## A possible way to concentrate a revision

A window treatment involves the opening, frame, exterior view, glass and nearby light. Those elements need to agree perceptually. Treating them as one connected visual change may be more coherent than asking for an isolated window noun plus an absolute promise that everything else remains identical. Unrelated changes, such as restoring eyewear, have different dependencies and deserve their own justification.

This is a proposed way to formulate the desired visible state, not a proven preservation technique or a demand to change one object per attempt. A global medium conversion can be coherent even though it affects every pixel. A request for a glowing rim also raises a separate part-binding problem: naming the table alone may bind the property to its supports. Scope coherence does not solve that binding automatically.

## Evidence and limits

[B-FS4-full](../evidence/B-FS4-full.json), v3 / `event-0008`, preserves the full refinement prompt and its v2 input. The resulting historical online findings are in `event-0009-critique`. They motivate examining actual requested changes rather than trusting the word 'focused'. There was no paired test of a connected-field prompt against this prompt. The connected-field alternative must therefore remain a hypothesis. Unchanged-region guarantees are unavailable from this interface; future mask/control interfaces would change that premise.

For an actual conflict between authored content and an activity, see [EX-design-conflict](design-conflict.md). For what the chosen input already supplies, see [EX-input-conditioning](input-conditioning.md).
