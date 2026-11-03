# Experience for recasting a video into another world or medium

Entries are grouped by what they are about. Start with the common principles, then read the section for the renderer you are using, then the section that matches the prompt length and the kind of world or medium you were asked for. Each line is the entry's own summary; open the entry for its conditions, exceptions and evidence. Related task contributions appear beside each entry; their source cases and curation decisions remain distinct.

## Common principles

| Question | Working judgment |
|---|---|
| Which candidate should I deliver?; Is the latest repair better than an earlier version?; How do I weigh conversion against stability? | [EX-P-compare-retained](entries/P-compare-retained.md): Compare every retained candidate on how fully the world was rebuilt, whether the moment is still recognizable, and how stable and clean it is. The newest or the most repaired version is not automatically the best, and a polished result that kept the old scene is not finished. |
| How do I translate source objects and actions into another world?; Why did the effect appear on the wrong part?; Why does the result look like decoration rather than adaptation? | [EX-P-counterparts](entries/P-counterparts.md): Map each important source element to a specific, fitting counterpart (a glove to a C-shaped brick hand, a plank to a stack of tan plates) and name the carrier of each effect. Generic theme decoration does not do this work. |
| Why does the result still look like the original place?; Why does a stylized subject look pasted onto a real background?; What do I need to describe besides the main character? | [EX-P-every-plane](entries/P-every-plane.md): Describe how the target medium builds each visible plane. If a named plane still stays photographic, revise its construction, visual relationships and input support instead of adding the same object name again. |
| How do I keep the same person in a different world?; Why did the person change into someone else?; When is changing a character's look part of the task? | [EX-P-identity](entries/P-identity.md): Preserve the person at role level and keep salient attributes (age group, skin tone, build) unless the new world changes them. Keep identity wording short and spend design effort around the face; long facial inventories rebuild a different person. |
| How do I make a style read as that medium rather than a color filter?; Why did added lamps not change the atmosphere?; What should I write instead of a list of style adjectives? | [EX-P-medium-logic](entries/P-medium-logic.md): Write the construction rules of the target medium (what makes a mark, a surface, a shadow) and what the light does to each plane. Style names and adjectives alone leave the renderer to guess, and lamps alone do not change the lighting. |
| What must stay recognizable when the video moves into another world or medium?; Which source actions are performance material and which are old-world functions to replace? | [EX-P-moment](entries/P-moment.md): Before the first generation, write down who acts, what happens, in what order, where, and from which camera position. Keep that skeleton recognizable and rebuild everything else in the target world. |
| What should I change when a second attempt fails the same way?; How do I use my remaining generations?; Should I stop after one good result? | [EX-P-spend-attempts](entries/P-spend-attempts.md): Use remaining generations to try a genuinely different construction, input or scope, not a restated version of what failed. Keep earlier candidates as options. In a fixed-budget task, use the full allowance before choosing. |
| Which part of the video should I inspect before accepting it?; Why did a good-looking candidate get marked down?; What do reviewers tend to miss? | [EX-P-worst-second](entries/P-worst-second.md): Look closely at focal faces, hands, held props and contacts, the first and last second, and the planes you never described. A strong opening or a clean overview can hide melted keys, fused fingers, a source-like first half-second or a collapsing end. |

## Bernini capabilities and traps

| Question | Working judgment |
|---|---|
| Should I continue from my last candidate or restart from the source?; Why did a repair make other things worse?; Which input keeps the information I need? | [EX-B-chain-drift](entries/B-chain-drift.md): On Bernini, five train-sample continuations from an earlier candidate moved stability by -1.0 to +1.1 with no consistent direction. Continue from a candidate only when it holds what you need next; otherwise restart from the source with a rewritten full prompt. |
| Why does the glow appear on the wrong object?; How do I make only one edge emit light? | [EX-B-emission-binding](entries/B-emission-binding.md): On Bernini, requested emission appeared under a table or on arches instead of on the intended perimeter. Describe the glowing edge and the unlit support as a contrast, and look at where the light lands. |
| Why does the carried object bend or change shape?; Why do fingers merge into the keyboard or the headboard?; What should I specify to keep a grip clean? | [EX-B-held-props](entries/B-held-props.md): Under heavy conversion Bernini softens fingers into keyboards, bends or reshapes carried objects, flips face prints between frames, and lets a prop detach from the hand. Describe the grip and the prop's rigid shape, and inspect them closely. |
| Why does the person look different after I described them in detail?; Which input recovers a lost face?; How do I keep several people recognizable? | [EX-B-identity-rebuild](entries/B-identity-rebuild.md): Detailed hair, age and glasses descriptions reconstructed different people on Bernini across several tasks, and heavy scene-wide rewrites did too. Keep identity wording short, favor a source that still shows the person, and check every person after each pass. |
| Why is only my character converted?; Why does a plain request leave the background alone?; What does a preservation-heavy prompt cost? | [EX-B-partial-default](entries/B-partial-default.md): Bernini can convert the subject while retaining photographic scenery, even when scenery was explicitly described. Cover the planes, then rework the construction and input support of the ones it still failed to realize. |
| How long can a Bernini prompt be?; What should I cut when the prompt is too long?; What happens when the prompt exceeds the limit? | [EX-B-text-budget](entries/B-text-budget.md): Bernini accepts 512 encoder tokens including its official prefix. Long preservation clauses use space that construction clauses need, and prompts over the limit are refused before any render. |

## Ditto capabilities and traps

| Question | Working judgment |
|---|---|
| Where does Ditto put its effort?; What should I specify first for Ditto?; Why did the setting work while the people changed? | [EX-D-env-strong-foreground-weak](entries/D-env-strong-foreground-weak.md): In the historical Ditto runs, space-station walls and Earth views arrived early while faces and eyewear changed. Spend early attention on foreground identity and structure; do not escalate background instructions once the setting is already convincing. |
| Why did my correction add another object?; How do I repair the shape of one object on Ditto? | [EX-D-shape-repair-adds](entries/D-shape-repair-adds.md): A request to make a dome compact produced a second dome. For an important instance repair, anchor the existing object to its neighbors and footprint, or restart from an intact earlier input, rather than continuing to sculpt a duplicated one. |

## Conditions of the task

Prompt length and the kind of world or medium change what a good proposal contains.

### Short prompts

| Question | Working judgment |
|---|---|
| The request is one sentence. What do I have to add?; Why did a short-prompt result keep the theme but lose the scene? | [EX-C-short](entries/C-short.md): For a short request, anchor the target in the source's distinctive spatial relationships. When a detailed prompt still produces a generic scene, revise the discriminating geometry and staging rather than merely making the prompt longer. |

### Long prompts

| Question | Working judgment |
|---|---|
| The request lists many details. Do I need to carry them all?; How do I check a long request against the result? | [EX-C-long](entries/C-long.md): A long request names planes, costume, light and a camera behavior. Carry them in order of what makes the world recognizable, and check each named item in the delivered video, because a long list can exceed what one prompt carries. |

### By family of world or medium

| Question | Working judgment |
|---|---|
| How do I recast into a physical material such as bricks, paper or felt?; Why does my character look like a toy placed in a real scene? | [EX-C-craft](entries/C-craft.md): In a brick, paper, felt or cut-paper world the medium is made of pieces. A subject built from the material in a photographic scene reads as a collage; name how each plane is assembled from the material. |
| The set is convincing but the people are wrong. Where did it fail?; How do I recast into a film's world without replacing the people? | [EX-C-film-world](entries/C-film-world.md): In recasts into a film's production design, the environment converted readily. The failures in the train evidence were on the people: replaced, left in source look as cut-outs, or mismatched in light. |
| Is there guidance for anime, painting or comic worlds?; What should I check first in a drawn or painted medium? | [EX-C-hand-drawn](entries/C-hand-drawn.md): Use the historical etching and storybook evidence for concrete medium construction. Current anime, painting and comic families still need v5 training comparisons; transfer the construction relationship and choose the marks for the requested medium. |

[Reading guide](../../creative-loop/READING.md) · [Working routes](../../creative-loop/README.md) · [Renderer entrances](renderers.md)
