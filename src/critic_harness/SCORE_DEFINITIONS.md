# Low-to-high video scoring standard v5: recasting across worlds and media

## Shared task interpretation

The task recasts an existing video into another world or artistic medium as one
coherent work. A successful recast keeps the source moment recognizable (who acts,
what happens, in which order, in which spatial arrangement and viewing position) and
rebuilds the visible scene in the requested world or medium: subjects, props,
environment, light, materials and, where the request implies it, the way actions
are performed. The result must also hold together as a stable, clean sequence.

Evaluate the original user request and source/candidate videos using this shared
handbook. Task-specific hidden answers, intent cards and supplemental conversion
requirements are not inputs. Explicit user instructions take priority. Planner-written
prompts, chosen implementations, difficulty, knowledge entries and online focus do
not add requirements. Short/long tasks share these anchors and each uses its actual
original prompt; long-only details are not hidden short-task targets. A style or era
label alone does not demand deletion of modern objects or replacement of an activity.
A source cut is contextual evidence, not itself an output defect.

The five dimensions answer separate questions. Score each question only in its own
dimension:

- How fully was the requested world or medium realized? IA.
- Is it still recognizably the same moment? CP.
- Is the resulting sequence stable and continuous? TC.
- Are the visible structures well formed for the medium? VI.
- Does the result read as one designed, integrated work? AC.

Closeness to the source beyond recognizable correspondence earns no extra credit in
any dimension. Stability or clean geometry in regions that remain unconverted is
still credited in TC and VI; the missing conversion itself is scored in IA, and an
unrequested live-action/stylized mixture is scored in AC.

## Status, scope and evidence

Single judgments use 0.0 through 4.0 in 0.1 steps. The integer levels below are
anchors; intermediate tenths express the observed degree between adjacent anchors.
Use status scored only with sufficient evidence. Otherwise use
unknown (insufficient/ambiguous evidence), not_assessed (technical omission), or
not_applicable (no meaningful application), with score null and a specific reason.
Cite supplied frame IDs and state observed scope and uncovered intervals in
limitations. Source correspondence requires source and candidate evidence.
Sparse overview images do not establish motion continuity. Temporal scoring needs
reviewed native consecutive frames; a local event supports a local conclusion.
Natural occlusion is allowed; invisible contacts or actions are not assumed correct.
A static result can be temporally stable while failing required action under IA/CP.

Begin every reason with one sentence naming the decisive observation for that score.
Then give the supporting observations and the gap to the next higher anchor as a
description, not as advice.

## instruction_adherence (IA): requested world/medium realization

Judge how much of the visible scene is actually rebuilt in the requested world or
medium, weighted by prominence and duration, together with every central request
element. Name the regions or intervals that remain source-like or live-action.

4: Subjects, props, environment and light are rebuilt in the target world/medium
   across the whole duration, with its construction logic visible (for example
   bricks and studs, ink line and wash, cel outline and flat fill); all central
   requested elements and relations are realized.
3: Main subjects and the dominant environment are converted and coherent; a
   secondary region, brief interval or minor requested detail is incomplete.
2: The target is recognizable but a central requirement is missing or partial: a
   main subject or dominant environment remains source-like, the medium appears
   only in part of the duration, or the change is mostly grading, texture or
   ornament. Within this band, use 2.0-2.4 when only a subject or prop is converted
   and 2.5-2.9 when most of the scene is converted and one central element is partial.
1: Only superficial or local target cues appear.
0: Requested target is absent or fundamentally contradicted.
A consequential central omission caps IA at 2. Colour grading or surface filters
alone do not realize a requested medium. Decorative cues do not fulfill a requested
world or behavior reconstruction. Do not reward added complexity.

## content_preservation (CP): recognizable source correspondence

Judge whether the recast is still the same moment: its roles, story beats and their
order, spatial staging, camera intent and key interactions. For world/medium recasts,
a translated counterpart is full correspondence: a gloved hand becoming a minifigure
hand, a photographed bucket becoming a painted bucket, a walk becoming a stylized walk.
Pose, texture or pixel closeness beyond recognizable correspondence earns no extra
credit.

4: Every role, beat, spatial relation and key interaction has a recognizable
   counterpart in the requested world.
3: Main correspondence is intact; one minor beat, prop or interaction is weakened.
2: Recognizable correspondence remains, but one central role, beat, interaction or
   explicitly retained action is lost or unreadable.
1: Only weak superficial correspondence remains; most important anchors are lost.
0: Source correspondence is absent or contradicted.
Broken central correspondence caps CP at 2. Removing required interaction by
freezing, hiding or deleting it is a CP/IA error. Authorized replacement is not.

Identity rule, applied identically to every candidate: deleting a central character
or replacing them with a clearly different person caps CP at 2. Changing a salient
attribute (apparent age group, gender presentation, skin tone, body type) without a
reason in the requested world or request caps CP at 3. A change the requested world
implies, such as a person becoming a toy figure or a stylized face, is not an
identity error.

## temporal_consistency (TC): stability of the resulting sequence

Judge the candidate's own sequence. Use the source only to establish which events
should occur; agreement with source timing or poses is not TC evidence.

Check for: medium switching within the shot (live-action and stylized frames
alternating or a delayed conversion), boiling or flowing background texture,
elements popping in or out, character or costume drift, props vanishing, contacts
detaching, and end-of-clip collapse. Weight each by duration and by whether it
affects the focal subject.

4: Reviewed events have coherent onset, transition and outcome; the medium,
   identities, contacts and motion remain consistent from start to end.
3: Main progression is coherent; small transient jitter or drift has little impact.
2: The event remains interpretable, but an important discontinuity disrupts it:
   a medium switch, focal end-of-clip collapse, identity switch, teleportation,
   vanished prop, detached contact or broken causal transition.
1: Repeated severe discontinuities make the event difficult to follow.
0: The sequence is incoherent or the central temporal progression breaks down.
An important break caps TC at 2; a focal collapse counts even when brief or near
the end. Controlled motion idioms of the requested medium, such as stop-motion
stepping or limited-animation holds, are not defects when consistent; uncontrolled
line or texture boiling is. Unconverted but stable regions are credited normally.
Sparse evidence alone yields unknown. Mention exactly which intervals were observed.

## visual_integrity (VI): structural and rendering correctness in the medium

4: Subjects, objects, geometry, boundaries and contacts are well formed for the
   intended medium; no consequential defect is visible.
3: Minor local artifacts exist outside focal structures, without impairing
   important subjects or interactions.
2: A visible consequential defect affects a focal structure (face, hand, held prop,
   contact) or the scene: melting, merging of subject into background or hair into
   pattern, blotches or colour patches, illegible clutter, or a cutout halo/seam
   between stylized and live-action regions. The scene remains interpretable.
1: Major widespread deformation or merging seriously damages legibility.
0: Essential structures collapse; the scene/central interaction is not interpretable.
A focal structural defect caps VI at 2. Assess stylization against its own medium,
not photorealism. Concealed parts are unobserved, not evidence of correct geometry.

## aesthetic_coherence (AC): integrated, designed finish

4: Composition, lighting, palette, materials, subjects, environment and effects form
   one deliberate visual system appropriate to the requested world and moment;
   source elements are adapted into fitting counterparts.
3: Overall integration is convincing; minor imbalance, generic choice or local
   inconsistency remains.
2: A consequential clash weakens integration: an unrequested mixture of stylized
   subjects and live-action surroundings, conflicting visual systems, generic theme
   decoration in place of adapted elements, cluttered hierarchy, or design that
   contradicts the moment's mood.
1: Fragmented, poorly coordinated treatment dominates the result.
0: Visual organization and integration collapse across the central scene.
A consequential integration conflict caps AC at 2. More detail, saturation, effects
or photorealism does not automatically score higher. Source simplicity is not low
quality by itself. Realization of the requested medium belongs to IA; design and
integration craft belong to AC.

## Attribution and reporting

Score each dimension separately with its own evidence. An observation can affect
multiple dimensions only with a specific explanation of each consequence. Do not
apply a blanket penalty or average the five dimensions into a default overall score.
Individual model ratings use 0.1 steps. Computed means retain their full precision.
