# Low-to-high video scoring standard v4

## Shared task interpretation

Evaluate the original user request and source/candidate videos using this shared
handbook. Task-specific hidden answers, intent cards and supplemental conversion
requirements are not inputs. Low-to-high means realizing the requested visual or
narrative target with coherent source correspondence, motion and production quality.
Appearance-only edits normally retain the activity and important relationships.
World/narrative reconstruction permits reinterpretation supported by the actual
request; assess the resulting behavior and its correspondence without prescribing a
replacement story. A style or era label alone does not demand deletion of modern
objects or replacement of an activity. Explicit user instructions take priority.
Planner-written prompts, chosen implementations, difficulty, knowledge entries and
online focus do not add requirements. Short/long tasks share these anchors and each
uses its actual original prompt; long-only details are not hidden short-task targets.
Material/medium transformations are assessed in their requested medium. Unspecified
incidental detail changes are judged by their actual effect on task meaning and quality.
Task-fit errors belong to IA; structural VI penalties need observable shape/geometry
or contact defects. A source cut is contextual evidence, not itself an output defect.

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

## instruction_adherence (IA): requested transformation

4: All central targets and their required relationships/behavior are realized;
   no consequential omission is visible within the assessed scope.
3: Main transformation is complete and coherent; minor local imprecision remains.
2: Target is recognizable, but a central requirement, binding or required behavioral
   reconstruction is missing, wrong or only partly realized.
1: Only superficial/local target cues appear; most of the principal transformation fails.
0: Requested target is absent or fundamentally contradicted.
A consequential central omission caps IA at 2. Decorative style cues alone do not
fulfill a requested world/behavior reconstruction. Do not reward added complexity.

## content_preservation (CP): required source correspondence

4: All required subjects, spatial/interaction relationships, event functions and
   task-specified continuity are preserved through permitted reinterpretation.
3: Main correspondence is intact; minor non-central drift does not change meaning.
2: Recognizable source correspondence remains, but one important relation, subject,
   event role or explicitly retained action is lost or altered.
1: Only weak superficial correspondence remains; most important anchors are lost.
0: Required source correspondence is absent or contradicted.
Broken central correspondence caps CP at 2. Preserve exact objects/actions only
where the task requires them. Authorized replacement is not a CP error; removing
required interaction by freezing, hiding or deleting it is a CP/IA error.

## temporal_consistency (TC): continuity of the resulting sequence

4: Reviewed events have coherent onset, transition and outcome; identities, contacts,
   motion and physical/stylized causality remain consistent throughout observed intervals.
3: Main event progression is coherent; small transient jitter/drift has little impact.
2: The event remains interpretable but an important discontinuity, identity switch,
   teleportation, inconsistent contact or broken causal transition disrupts it.
1: Repeated severe discontinuities make the event difficult to follow.
0: The sequence is incoherent or the central temporal progression breaks down.
An important event break caps TC at 2. Judge newly authorized behavior on its own
logic. Source motion matching is a separate conditional diagnostic. Sparse evidence
alone yields unknown. Mention exactly which intervals were observed.

## visual_integrity (VI): local structural and rendering correctness

4: Subjects, objects, geometry, boundaries and contacts are well formed for the
   intended medium; no consequential defect is visible.
3: Minor local artifacts exist, without impairing important subjects/interactions.
2: A visible consequential defect affects a key structure, anatomy, object, boundary
   or contact, while the scene remains interpretable.
1: Major widespread deformation or merging seriously damages legibility.
0: Essential structures collapse; the scene/central interaction is not interpretable.
A key structural defect caps VI at 2. Assess stylization against its own medium,
not photorealism. Concealed parts are unobserved, not evidence of correct geometry.

## aesthetic_coherence (AC): coordinated production finish

4: Composition, lighting, palette, materials, subjects, environment and effects form
   a deliberate, polished whole appropriate to the requested target.
3: Overall integration is convincing; minor imbalance or local inconsistency remains.
2: A consequential clash in lighting/material/style/composition or effects weakens
   integration despite recognizable design intent.
1: Fragmented, poorly coordinated treatment dominates the result.
0: Visual organization and integration collapse across the central scene.
A consequential integration conflict caps AC at 2. More detail, saturation, effects
or photorealism does not automatically score higher. Source simplicity is not low
quality by itself. Requested stylistic success belongs to IA; craft belongs to AC.

## Attribution and reporting

Score each dimension separately with its own evidence. An observation can affect
multiple dimensions only with a specific explanation of each consequence. Do not
apply a blanket penalty or average the five dimensions into a default overall score.
Individual model ratings use 0.1 steps. Computed means retain their full precision.
