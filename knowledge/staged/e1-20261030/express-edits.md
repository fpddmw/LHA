# Express an edit for its actual input

[Respond to unmet requirements](respond-to-unmet-requirements.md) · [Design expression](../../guides/design-expression.md) · [Bernini probe record](../../model-experience/bernini-r.md)

Version E1 (staged, replaces v1). The renderer sees only the input video and the prompt. It does not see notes, reviews or other candidates.

### X1 · Describe wanted states, not prohibitions
When: writing any instruction intended to prevent, remove or protect something.
Do: write the wanted visible state ("clean off-white paper reaching every edge"). Keep negative lists short; never rely on them alone.
Why: R4 (D/027S-no v2, D/001S v3, B/FS4-no v2).
Status: mixed → strong default

### X2 · Make a short style request concrete
When: the request names only a medium or genre ("children's storybook", "etching").
Do: develop one interpretation into visible marks, materials and palette (for example, pencil visible under transparent wash on cream paper).
Why: the Bernini probe (short storybook label stayed photographic; the concrete versions illustrated). In the loops, the concrete first prompts passed the independent check on 041 and 027 on Bernini, and the 041 review passed on Ditto.
Limits: a bare label also worked for 027 etching in the probe.
Status: observed · any renderer

### X3 · Bind local effects to the part, and say what stays unlit
When: an effect belongs on one part of an object (rim and not legs, collar and not robe).
Do: name the part, its position and its neighbor's contrasting state in one sentence.
Why: B/FS4-full v1 used "glowing strip along the outer tabletop rim; lower supports in non-emissive matte metal" and the rim glowed. All three B/FS4-no attempts put the glow on the supports, including two that named the rim in capitals.
Limits: mixed; part placement is not reliable on Bernini (B3).
Mechanism hypothesis: a material property can bind to the object category rather than the intended boundary. Describe a contrast within one spatial relation: the thin horizontal perimeter emits light while the vertical supports remain matte. That gives the effect a location and a contrasting neighbor; it is not a spatial mask or a preservation guarantee.
Status: mixed

### X4 · Do not try to preserve a person by describing them
When: the request requires faces or identity to be preserved during large surrounding changes.
Do: prefer a concise identity constraint and a compatible realization over expanding age, hairline and accessory lists. The concise alternative remains a strategy hypothesis, not a demonstrated identity lock.
Why: on Ditto, prompts naming "middle-aged" or "receding temples" produced visibly older or grayer people (D/FS4-full v2, D/FS4-no v3). Every one of the six fewshot attempts named the glasses; only one kept faithful glasses, and three produced opaque eyewear or a visor. Long identity lists did not preserve faces on Bernini either (B/001L, 3 attempts).
Limits: D/FS4-no v2 ("rectangular eyeglasses") restored the glasses but not the face; its "thinning hair" produced thicker hair.
Mechanism hypothesis: semantic identity descriptors can invite a new representative of a category rather than preserve this individual. More identity adjectives may therefore add reconstruction instructions without adding instance correspondence. Choose environmental changes compatible with the existing face when possible; the renderer must still be checked visually.
Status: observed (2 renderers); mechanism unvalidated

### X5 · Refer to small landmarks by place and size, not by a strong noun
When: the scene contains small architectural landmarks that should stay small.
Do: refer to them by position and relative size ("the small rounded tower at the far right") instead of a salient category word used alone.
Why: the prompts that named "central dome" in B/027S-full v1 and D/027S-full v1 produced inflated or added domes.
Limits: B/027S-no v1 named a dome without inflation; this is a hypothesis.
Status: mixed

### X6 · Keep each revision's scope coherent
When: revising after a review.
Do: group changes that depend on each other (window, frame, view and light). Drop authored additions that cost preservation (R7). Count what the prompt actually changes, rather than calling it "focused".
Why: B/FS4-full v3 was described as a focused refinement but changed walls, windows, lighting, floor, glow and glasses at once, and gained new geometry and ball artifacts.
Mechanism hypothesis: the editing interface has no enforced meaning for "small repair". A verbal locality claim supplies neither a pixel mask nor an invariant region. A more useful unit may be a connected visual field: for a window replacement, the opening, frame, exterior view and nearby reflected light must agree. Express that coherent target state while avoiding unrelated changes; test whether it concentrates the transformation. This is a proposed rendering strategy, not an established capability or a required plan format.
Status: single; connected-field strategy unvalidated

### X7 · Longer is not better on its own
When: a revision tempts you to add more detail.
Do: add only information the renderer lacked. Use the actual frozen renderer token limit; these historical profiles used 512.
Why: in the loops, later prompts were usually longer than earlier ones, and later candidates were rarely better on the independent evaluation (S2).
Status: observed
