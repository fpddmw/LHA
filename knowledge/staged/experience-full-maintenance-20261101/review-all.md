# Complete experience entries for review

Fourteen proposed entries. Status: draft, not active. See [navigation](README.md), [old-card mapping](old-card-map.md), [maintenance findings](maintenance-report.md), and [proposed manual text](manual-passages.md).


---

## EX-design-conflict: A design can conceal the evidence that makes an activity readable

Revision 2. Draft for review. Bernini observations; explanatory interpretation. Reworks R7 and part of I3. Updated against F001/F003; no new generation.

**A successful costume, prop or lighting design can undermine the original activity by covering its support and contact relations. Repeating the preservation request leaves that design conflict in place.**

In the magical-study case, the authored long robe and the requested visible chair competed for the same image area. The second prompt named both, but the historical review reported the robe concealing the chair back, seat and legs. The loss concerned the visible person-chair-desk relationship through which sitting and reading were understood. The next proposal retained a fitted jacket and trousers, changed color and embroidery, and described the chair. The review found seating readable again. Fantasy appearance did not depend on the long robe.

This distinction changes the design question. Ask what carries the requested style, and what visual evidence the source activity needs. A robe's fabric and ornament, its silhouette and its occlusion are different contributions. Altering one of these can preserve the direction while changing the conflict. The same reasoning applies to glow crossing a face, or scenery covering a working surface.

The new batch establishes an important boundary. F003's third prompt explicitly fitted narrow sleeves to existing arms and kept the guitar unobstructed. The guitar became recognizable again relative to v2, but the microphone interaction and identities remained altered. Removing an occlusion conflict does not by itself recover a relational or temporal failure. F001 also explicitly required flowing wide sleeves: here the garment is a user requirement, unlike the optional robe in the study. It needs a compatible realization, not silent removal.

The practical contribution is to locate a conflict within the proposal rather than interpret every loss as insufficient emphasis. When the conflicting feature is optional, its realization can change. When it is requested, the tradeoff remains part of the task.

Evidence: [B-003](evidence/B-003.json), generations `event-0005` and `event-0008`, reviews `event-0006-critique` and `event-0009-critique`; [F003](evidence/F003.json), v2/v3; [F001](evidence/F001.json), original request. All study attempts used source input; several prompt details changed together. This supports a design interpretation, not an isolated costume effect. Related: [activity relations](entries/activity-relations.md), [connected scope](entries/connected-scope.md).


---

## EX-activity-relations: A coherent genre can reorganize who does what

Revision 1. Draft for review. New synthesis from Bernini F001/F003/F005; sampled visual corroboration for F003/F005. Mechanism interpretation.

**A video can retain the right people and objects while changing the activity. Genre-compatible staging can replace the particular relationships that made the source event intelligible.**

F003's source shows a standing person holding a microphone toward a seated guitarist. V1 retained a standing person, microphone and seated guitarist in a convincing palace salon, but gave the standing person the microphone at her own mouth. The scene became a plausible singer-and-accompanist arrangement. F005 similarly realized casino materials while replacing the mahjong tile walls and mechanism with a red playing surface and scattered objects. These were organized alternatives to the source scene, not simply missing decorative details.

An explanatory hypothesis is that a strong scene concept supplies a familiar activity arrangement as well as a visual style. Asking for a casino lounge or palace performance can leave the renderer free to reconstruct a plausible game or performance. An object inventory does not disambiguate this: microphone presence says little about who it serves; a table and players say little about what game their reaches address.

This changes how to interpret the source and proposal. Identify the relations that distinguish this event from another plausible event: microphone directed toward the guitarist; a hand reaching toward a particular tile wall; a defender responding to the shooter. Let style be realized through materials, architecture, costume and light around those relations when the user requests the original activity. This is a way to develop and compare proposals, not a promise that relational wording controls motion.

F005 v2 explicitly separated the mahjong playing system from the outer table frame and retained a recognizable setup, with other changes and a source restart. F003 v2 explicitly described the correct microphone relation yet damaged the performance further. Naming the distinction can remove ambiguity; once it is named and still fails, the problem has moved beyond omission. F001 also shows that narrating the shot sequence in detail can coexist with duplicated players and broken possession.

Evidence: [F003](evidence/F003.json), v1/v2 and source; [F005](evidence/F005.json), v1/v2; [F001](evidence/F001.json), v2. [Opening-frame comparisons](evidence/visual-inspection.md) corroborate the changed microphone role and mahjong layout, not complete motion. Related: [actual realization change](entries/realization-change.md), [object continuity](entries/object-continuity.md).


---

## EX-instance-identity: Appearance categories do not establish correspondence to an individual

Revision 2. Draft for review. Bernini and Ditto, historical online judgments and explanatory hypothesis. Reworks R6/X4/B4/D3; expanded with F002/F003/F004/F005/F006.

**An appearance description can faithfully specify a type of person while failing to retain this person. More identity adjectives add attributes; they do not add a correspondence constraint between source and output.**

The older Ditto table-tennis runs make the distinction visible: rectangular glasses could return while the face remained different. Other prompts naming age, hair and glasses produced older faces or opaque eyewear. The seven-task Bernini batch repeats the problem across different activities. In F002 v2, the pianist's resemblance improved while a guest's identity worsened. F003 v2 introduced glasses to the standing performer. F005 v3 enumerated each person's hair and eyewear, yet the review still found changed identities. Whole-scene descriptions can redistribute appearance among people as well as replace it.

One explanatory hypothesis is that the new social or visual context encourages reconstruction of a plausible participant. A tuxedoed lounge pianist or a palace performer can fit the new scene while failing the instance-preservation requirement. This hypothesis directs attention to what has changed around a head: clothing cut, headwear, light, nearby hands and pose. Merely describing a youthful face more precisely may continue to specify a replacement rather than recover the source individual.

The useful planning question is which input still carries recognizable individual evidence, and which proposed transformations compete with it. A person-specific source observation helps diagnose loss; converting that observation into a long prompt is a separate, unvalidated intervention. Keep identity, accessory category and accessory shape distinguishable when comparing candidates.

Counterexamples matter. F006 retained a recognizable single person's face throughout its reviews despite major costume and setting changes. F004 v2 passed the historical face judgment after a below-neck instruction and other prompt changes; F002 v3 also used a below-neck boundary and still failed. These records do not establish a reliable boundary phrase, a short-prompt cure, or a near-person prohibition. Crowding, scale, occlusion and requested transformation are plausible conditions to examine, not independently measured causes.

Evidence: [D-FS4-no](evidence/D-FS4-no.json), glasses recovery without face recovery; [D-FS4-full](evidence/D-FS4-full.json); [F002](evidence/F002.json), v2/v3; [F003](evidence/F003.json), v2; [F004](evidence/F004.json), v2; [F005](evidence/F005.json), v3; [F006](evidence/F006.json), all reviews. New inspection of F003/F005 opening frames corroborates visible appearance substitutions at those frames only; see [inspection record](evidence/visual-inspection.md). Related: [input conditioning](entries/input-conditioning.md).


---

## EX-object-continuity: A moving prop must remain the same participant across interaction states

Revision 1. Draft for review. New Bernini hypothesis from F001/F006. Based on saved sequence observations; no new motion tracking or causal test.

**A prop can be recognizable in every local view while failing to be one continuous object in the action. Counting nouns in the prompt does not establish continuity of possession, visibility and release.**

F001's first result showed an extra basketball beside the shooter while the released ball was airborne. Its second prompt explicitly described one moving basketball and empty hands after release, yet the result introduced an extra person and a shot without the ball. The third kept a recognizable jump shot but still had an additional opening ball. In F006 v1, the review found a second phone-like object during retrieval, although the ending retained one prominent phone.

These failures concentrate around state transitions: concealed to visible, held to released, one hand to another. A plausible explanation is that local visual plausibility is being reconstructed without consistently binding all those states to one participant. This is more specific than 'the model duplicates objects': it identifies the relationship that a source action supplies and a new rendition can lose.

The useful question is which transitions establish that the ball or phone is the same object. Inspect hand-object contact, occlusion, possession and the post-release state when they are consequential. A general scene summary or endpoint frame can miss the break. If the relationship was omitted, stating it clarifies the target; if it was already explicit, repeating 'one' does not materially change the proposed solution.

F006 v2 restarted with a more explicit concealed-then-retrieved phone description and no duplicate was observed. However, precise phone and hand preservation remained unknown, the costume disappeared, and multiple changes were simultaneous. This is a partial counterexample to inevitable duplication, not proof of a reliable wording fix. The novel value is a better failure interpretation and inspection target; an effective control strategy remains open.

Evidence: [F001](evidence/F001.json), v1 late-interval and v2/v3 findings; [F006](evidence/F006.json), v1 retrieval and v2/v3 outcomes. These are two source scenes, with different actions, not replicated tests of one duplication mechanism. Related: [activity relations](entries/activity-relations.md), [time binding](entries/time-binding.md), [realization change](entries/realization-change.md).


---

## EX-connected-scope: Revision scope follows visual dependencies

Revision 2. Draft for review. Interface fact plus Bernini traces; connected-scope strategy remains a hypothesis. Reworks X6 and relates to X3. Updated with F004/F006/F007.

**A revision's scope is determined by the visual relationships it changes. Calling it small supplies no spatial control; grouping everything under one background label does not make those changes coherent.**

The older table-tennis refinement changed walls, windows, lights, floor, table glow and glasses. Its description as focused hid several distinct problems. In the current video-plus-text interface, no mask or invariant region accompanies that word. A plausible planning unit is the connected set of elements that must change together for a result to make sense.

For a window, that set can include the opening, frame, exterior view, glass and nearby light. For a floating mountain, it includes an exposed sky region, a separable underside, surrounding air and its relation to foreground foliage. F006 v3 explicitly opened gaps in foliage and placed mountains above the already present pavilion. Its review reported visible mountains. The input route and costume instructions changed too, so the contribution of this spatial formulation is not isolated.

F007 continued a useful titanium-train candidate with specific correspondences: shops became an entrance, pitched rooftops became a glass concourse, utility infrastructure became transit structures. The review found a stronger station setting. F004 used similarly concrete wall/column descriptions but failed to complete the arena. A connected proposal supplies an intelligible target; the renderer can still retain the old scene.

This suggests judging revision scope by dependency rather than object count. A background replacement may legitimately require relighting reflective foreground surfaces. An unrelated eyewear restoration has a different dependency and deserves a distinct reason for joining that attempt. Whole-image media conversion can also be coherent. There is no one-object-per-attempt rule.

The alternative to a locality promise is an explicit account of what the desired visual arrangement requires. It remains a creative choice, not a mandatory planning form or a guarantee of unchanged regions.

Evidence: [B-FS4-full](evidence/B-FS4-full.json), v3 `event-0008`; [F006](evidence/F006.json), v2/v3 `event-0006`/`event-0008`; [F007](evidence/F007.json), v3 `event-0006`; [F004](evidence/F004.json), v3 `event-0005`. Related: [environment replacement](entries/environment-replacement.md), [lighting integration](entries/lighting-integration.md).


---

## EX-input-conditioning: Choose an input for the information the proposed change needs

Revision 2. Draft for review. Bernini/Ditto observational evidence; no randomized route comparison. Reworks I1/I2/I3/I4/R5. Updated with all seven fewshot runs.

**An input supplies achievements and losses together. A candidate's useful appearance can support continuation, while a source restart restores original evidence and requires the appearance to be generated again. The proposed change determines which information matters.**

In the new batch, all seven second attempts restarted from source. Before the third attempt, F004/F006/F007 had candidates with no reported major damage; Planner continued those candidates. F001/F002/F003/F005 still had major damage, and Planner restarted. All three continuations remained free of reported major damage; all four restarts still had major damage. This association starts with different candidate states and different tasks. It describes a state-dependent choice, not a causal advantage of continuation.

The distinction inside the continuation group is instructive. F006 gained mountains and a costume while retaining its pavilion; F007 gained a station around its metallic train; F004 preserved foreground achievements but gained no clear arena improvement. Keeping usable information and successfully producing the remaining transformation are separate benefits. A stable candidate is a valuable platform, not evidence that another attempt will achieve its goal.

Source-based repair is equally conditional. F002 returned to original faces but lost the tuxedo; F003 restored a recognizable guitar relative to v2 without recovering the original performance. The original pixels were available in both cases, yet the requested full transformation still reorganized them. A source restart can recover access to information; it does not remove the conflicting transformation that previously lost it.

An earlier candidate can be a better starting point than either source or latest. The older Ditto glitch run used v1 to avoid v2's opaque overlays and obtained stronger flicker, while the desired scene displacement remained unconfirmed. Conversely, editing an existing Ditto dome added another dome. Evaluate what a particular candidate enables, including whether the next change complements its appearance or contradicts its geometry.

Retain the best delivery separately from the next editing input. The operational distinction belongs in the manual; the experience here explains why it matters: useful conditioning can be distributed across candidates, and no route monotonically accumulates quality.

Evidence: [batch facts](evidence/batch-facts.json); [F002](evidence/F002.json), [F003](evidence/F003.json), [F004](evidence/F004.json), [F006](evidence/F006.json), [F007](evidence/F007.json); [D glitch branch](evidence/H-D-024__long__full_knowledge.json), v1→v2 and v1→v3; [D dome](evidence/D-027-full.json), v2→v3; [B glitch](evidence/B-024-full.json), with [historical independent scores](evidence/historical-score-extract.md). Scores and online observations remain separate cohorts.


---

## EX-realization-change: More explicit wording can still request the same failed operation

Revision 1. Draft for review. Reworks R2/R3/S3/S5/B5/B6/D4/D8/D9 and X7. Bernini/Ditto observations; no fixed retry policy.

**A new prompt is a new hypothesis only to the extent that it changes something relevant to the failure. Specifying a missing relation, relocating an effect and restating an already explicit operation test different propositions.**

The older study prompts preserved reading without naming its back-facing orientation; later explicit orientation coincided with recovery in both renderers. By contrast, the Ditto glitch v1 already requested horizontal strips containing actual scene content displaced sideways. V2 added offsets, examples and stronger emphasis; v3 called it a broken arrangement of strips and tiles. The reports found overlays, color streaks and noise rather than confirmed displacement of scene-bearing pieces. The text changed substantially while the intended image operation remained substantially the same.

That matters because the visible vocabulary and the operation can separate. Colored blocks can make an image look glitchy without moving the scene inside them. Embroidery can make clothing look historical without raising a collar. A more forceful request for the same transformation can generate additional genre cues while leaving its geometric condition unmet.

To understand a proposed alternative, compare the visible relationship it asks for and the input information it uses with what was already tried. A changed material construction, removed design conflict, different spatial placement or input with needed evidence can be a substantive change. A seed-only retry tests variability. Each can be reasonable; calling a restatement a different mechanism obscures what was learned.

The new batch sharpens the omission boundary. F003 v1 did not spell out the microphone's recipient. V2 did, yet worsened guitar and pose preservation. Once the relation is explicit, another increasingly detailed recital is not supported by the earlier orientation success. F001's elaborate choreography also failed; its shorter third prompt improved the action verdict to partial while preserving serious defects. Neither example establishes a universal length rule.

There is no established two-failure ceiling. Bernini's older long costume task eventually realized standing collars and horizontal headwear that earlier versions missed, though identity still failed. Treat repeated failure as evidence about a particular proposal and setup, and evaluate a further attempt against that evidence and the remaining user need.

Evidence: [B study](evidence/B-003.json); [D study](evidence/H-D-benchmark__003__short.json); [D glitch](evidence/H-D-024__long__full_knowledge.json), all three exact prompts; [D collars](evidence/H-D-benchmark__001__long.json); [B collars](evidence/H-B-benchmark__001__long.json), v3; [F001](evidence/F001.json), [F003](evidence/F003.json). Historical reviews sometimes contain next-step advice; only their observations are used here.


---

## EX-part-binding: Getting the attribute right can still modify the wrong referent

Revision 1. Draft for review. Reworks X3/X5/I2/B3 and the dome part of D6. Bernini/Ditto observations; relational wording is a clarity strategy with mixed outcomes.

**A correct attribute on the wrong part is a binding failure. Asking for more of the attribute can strengthen the wrong realization rather than move it to the intended place.**

The table-tennis outputs repeatedly supplied bright blue emission on curved supports while leaving the tabletop perimeter gray. The missing element was not blue light in general. F004 v2 described all four edges of the purple tabletop, its rectangular perspective, and the red arches as unchanged and unlit. The review then passed the tabletop glow and geometry. Older prompts also explicitly named the rim and failed, including capitalized wording. The evidence supports distinguishing the part; it does not establish a reliable sentence formula.

A similar problem occurs at the instance level. In Ditto 027, an instruction to make a compact dome at a specified location produced an additional dome rather than correcting the existing one. The noun successfully evoked the object category while its intended correspondence failed. This is why adding dimensions can still elaborate a new object instead of editing the old one.

Describe the relation that distinguishes the intended referent when ambiguity matters: an emitting horizontal boundary above matte curved supports; an existing landmark bounded by neighboring roofs. Inspect the actual output at that relation. If the correct part is already clearly specified, stronger category naming alone offers little new explanatory leverage. Input selection and the requested geometric reorganization deserve attention instead.

Two tempting generalizations are retired. The old 'avoid strong landmark nouns' claim has a counterexample: a Bernini dome prompt did not inflate the landmark. The new successful tabletop attempt also changed prompt order, preservation wording and input; its isolated linguistic cause is unknown. Geometry edits can succeed, as F004's source-based table comparison suggests, while precise correction on a particular candidate can still fail.

Evidence: [F004](evidence/F004.json), v1/v2; [older B fewshot no-knowledge](evidence/H-B-fewshot_004__long__no_knowledge.json), three attempts; [D dome](evidence/D-027-full.json), v3; [B etching no-knowledge](evidence/H-B-027__short__no_knowledge.json), v1. Related: [instance identity](entries/instance-identity.md), [connected scope](entries/connected-scope.md).


---

## EX-wanted-state: A correction needs a positive visual account of the replacement

Revision 1. Draft for review. Merges R4/X1 and the expression component of D5. Primarily Ditto observations, with Bernini counterexamples.

**A removal request identifies dissatisfaction, but may leave the replacement appearance underspecified or in conflict with the surrounding design. Describe how the wanted state fits that design.**

The Ditto palace correction asked to neutralize yellow-orange skin while retaining rich candlelight, gold and warm surroundings. The result intensified yellow skin and hard highlights. The prompt already included natural tones and rosy undertones, so this is not evidence that a particular negative word caused the failure. The unresolved issue includes the relationship between facial illumination and the scene's dominant palette.

In the etching case, a list excluding yellow wash, folds and faded edges did not remove all of them. A later source attempt described white paper and neutral grayscale and was judged stronger, but also changed seed and other wording and retained some negatives. A positive description can give a more useful target than an absence alone; the record does not isolate a negation effect.

The implication is to specify the replacement at the level that matters. Paper whiteness, unmarked margins and ink shadow construction together describe an alternative print surface. Neutral facial fill and warm practical lights describe a lighting relationship. Merely suppressing yellow while requesting a globally golden image can preserve the underlying conflict. Likewise, removing cyan from a support is different from giving the tabletop the emitting role.

Short exclusions remain useful for disambiguation. F004's successful prompt explicitly kept supports unlit, and the older successful etching prompt retained exclusions. No ban on negatives or candidate color correction follows from these cases. When the desired replacement was already explicit, [realization change](entries/realization-change.md) becomes the more useful question.

Evidence: [D palace short](evidence/H-D-benchmark__001__short.json), v2/v3; [D etching no-knowledge](evidence/H-D-027__short__no_knowledge.json), all prompts and reviews; [F004](evidence/F004.json), v2; [B fewshot no-knowledge](evidence/H-B-fewshot_004__long__no_knowledge.json), support-glow persistence. New seven-task records add boundaries, not a controlled test of negation. Related: [lighting integration](entries/lighting-integration.md).


---

## EX-style-realization: Style specificity is a system of visible relationships

Revision 1. Draft for review. Reworks X2/B1/D1 and the ornament/shape distinction in D4. Bernini direct probe plus historical loops; prompt length was not isolated.

**Concrete style knowledge is useful when it explains how visible elements produce the effect: how marks construct tone, material responds to light, or ornament fits a silhouette. A longer inventory can still miss the defining relationship.**

In the Bernini probe, 'children's storybook' remained largely photographic. A watercolor-and-pencil interpretation produced illustration through soft contours, transparent washes, softened shadows and paper texture. A short etching label already worked, while elaboration better specified the ink, hatching, paper and sky. The value was a more determinate visual interpretation, not word count alone.

The costume records show why specificity also requires structure. Ditto realized silk, color and embroidery while leaving the requested standing collars and horizontal headwear unrealized. F003's palace setting and ornament could be convincing while the garment only partly read as hanfu. Surface detail and structural type are separable. The style library can explain which relationships are characteristic; Planner then chooses a realization appropriate to the source rather than multiplying decorative adjectives.

For a broad request, several interpretations may be valid. Warm pastel watercolor is one storybook direction, not the definition of storybook. For an explicit long request, named structural details remain part of the task even if another plausible style has already appeared. Knowledge should help distinguish these cases and articulate the chosen direction.

Successful initial style conversion does not establish preservation. The probe's detailed preservation clauses did not reliably recover pen/notebook structure. The new batch likewise produced strong palace or Wuxia appearance while changing activities. Inspect style, requested construction and source relationships as related but different outcomes.

Evidence: [Bernini probe record](../../model-experience/bernini-r.md), with exact prompts and original result links; [D costume](evidence/H-D-benchmark__001__long.json), three attempts; [F003](evidence/F003.json), v1–v3. The old first-pass expectations are retained as scoped observations, with no compulsory stop rule. Related: [activity relations](entries/activity-relations.md), [continuation value](entries/continuation-value.md).


---

## EX-environment-replacement: Theme cues and a reconstructed place are different achievements

Revision 1. Draft for review. Expands B2/D2 with Bernini F002/F004/F005/F006/F007. Environment persistence is observed; allocation and visibility explanations are hypotheses.

**A few highly recognizable motifs can establish a theme while the source environment still determines most of the place. Judge what carries the scene, not just whether the requested nouns appear.**

Earth views, suits and cyan table lights made F004 v2 futuristic, yet cream walls, barriers and exercise equipment retained the gym. Lanterns and wood accents partly upgraded F005 while utilitarian walls and wiring persisted. F007 v1 transformed the train but left the street crossing ordinary. These results were visually on-theme in some regions and incomplete as environment replacements.

Two distinct difficulties matter. First, an existing boundary can be reskinned without rebuilding what it encloses. Second, a requested addition needs visible space. F006's first floating-mountain prompt had no visible mountains; v3 placed them above the pavilion and opened foliage gaps. F007 v3 assigned specific source structures new station roles and achieved a stronger setting. Those changes supplied spatial relationships as well as more nouns.

This leads to a more useful design question: which source surfaces, openings, silhouettes and sightlines make the location read as the old place, and which must change to make it read as the requested place? Keeping layout, geometry and camera motion does not require keeping the original wall material or equipment identity. Conversely, replacing walls may require a coherent light and reflection change elsewhere. Broad preservation wording can leave these distinctions unclear, but wording alone is not proven to cause persistence.

Continuation can build on a useful scene, as in F006/F007. F004 v3 explicitly targeted remaining walls, equipment and lighting and still failed. Do not interpret a coherent proposal as evidence that execution is now easy. An unchanged background after explicit instructions is different from a missing background instruction.

The old 'Bernini under-applies environments, Ditto completes them' contrast is narrowed. It described one table-tennis source under historical settings. New Bernini F004 v1 and F001 already achieved strong environment transformation; F004's preservation-oriented v2 lost some of it. Scene, input and simultaneous requirements matter more than a renderer-wide binary label.

Evidence: [F004](evidence/F004.json), [F005](evidence/F005.json), [F006](evidence/F006.json), [F007](evidence/F007.json), all prompts/reviews; [F001](evidence/F001.json), v1; [old Ditto fewshot](evidence/D-FS4-full.json). Related: [connected scope](entries/connected-scope.md), [input conditioning](entries/input-conditioning.md).


---

## EX-lighting-integration: A visible lamp, an emissive accent and illumination of the scene are separate

Revision 1. Draft for review. New synthesis from F002/F004/F005/F007; carries forward D5's color-interaction evidence. Bernini/Ditto historical observations.

**Lighting style depends on relationships among sources, receivers, shadows and reflections. Adding a lamp or a glowing edge can satisfy a local cue while leaving the scene under its original illumination.**

F002 displayed chandeliers and warm highlights but retained cool window-side daylight. F004 supplied cyan table and suit accents while the gym remained neutrally lit. F005's fixtures and gold materials did not consistently produce the requested warm room atmosphere. F007 combined reflective titanium with smeared highlights and incomplete station integration. In each case, a recognizable lighting vocabulary coexisted with a missing lighting relationship.

This helps explain why 'more cinematic light' can produce additional decoration. A lamp is an object; illumination is its relationship to other visible surfaces. Warm material can look golden without changing the color or direction of incident light. A reflective body is convincing partly through what its highlights imply about the surrounding world.

Develop the relationship that the proposed scene needs: where light originates, which surfaces it reaches, how shadow and fill separate faces, and what nearby material reflects. These are design choices available in the style knowledge, not required clauses in every prompt. In F007 v3, station construction and cooler canopy shading improved the scene together, while smeared reflections remained. Improving the place and improving its reflection geometry are separable outcomes.

The Ditto palace color problem supplies a counter-pressure: warm surroundings and neutral faces need not share one global cast. A correction that names natural skin but retains an overwhelming golden treatment can leave that conflict unresolved. The historical correction worsened the cast; this does not establish that candidate-based color correction is inherently ineffective.

Evidence: [F002](evidence/F002.json), lighting v2/v3; [F004](evidence/F004.json), v2/v3; [F005](evidence/F005.json), all lighting judgments; [F007](evidence/F007.json), v2/v3; [D palace short](evidence/H-D-benchmark__001__short.json), v2/v3. These are attributed judgments, not new physical-light measurements. Related: [wanted state](entries/wanted-state.md), [environment replacement](entries/environment-replacement.md).


---

## EX-time-binding: An attribute appearing in a clip is different from an attribute persisting through it

Revision 1. Draft for review. Expands B7 with Bernini F001/F005/F006 and historical palace performance. New sampled inspection of F006, no new continuous-motion score.

**Appearance, persistence and event timing answer different questions. A convincing opening can conceal a later loss; a stable-looking face can still perform a different emotional action.**

F006 v3 displayed gold embroidery early and a largely plain exposed torso and shoulders later. F005 v3 began with formal jackets but the historical review recorded the foreground jacket becoming a light shirt. F001's golden light weakened after the opening. In the older palace footage, visually stable faces could suppress a developing smile or introduce concern at the wrong time. Temporal coherence therefore includes both retaining a property and retaining the source event, where requested.

This changes interpretation of a successful style frame. An entry should not count 'embroidered hanfu present' as equivalent to 'embroidered hanfu throughout the visible costume', nor infer exact playing motion from plausible playing poses. Consider what must survive a view change, occlusion, body turn or interaction. Those transitions are where a visually plausible replacement may cease to correspond to the same source state.

For planning, express the intended persistent design where it matters, but recognize that the phrase 'throughout' is not a tracking constraint. For comparison, inspect the places in time that distinguish the claims. A local failure can refute full preservation; sparse matching frames can only support their observed interval. When the historical review leaves a whole-clip verdict unknown despite positive sampled observations, preserve both the positive evidence and its coverage limit.

The seven-run protocol marked 40 of 54 temporal requirement judgments unknown, 13 fail and one partial, with none pass. These counts expose the protocol's conservative whole-clip boundary and the difficulty of the tasks. They do not establish 54 failures or an inability to preserve time. The old recommendation to merely report expression drift and stop is retired; its significance depends on the actual requested performance and available alternative.

Evidence: [F006](evidence/F006.json), v3; [F005](evidence/F005.json), v3; [F001](evidence/F001.json), v3; [B palace long](evidence/H-B-benchmark__001__long.json); [batch facts](evidence/batch-facts.json); [sampled F006 inspection](evidence/visual-inspection.md), frames 0 and 112. Related: [object continuity](entries/object-continuity.md), [continuation value](entries/continuation-value.md).


---

## EX-continuation-value: The value of a revision depends on the gap it closes and the alternative already available

Revision 1. Draft for review. Reworks S1/S2/S4/C1/C2/D7 and parts of S3/S5. Historical independent and online cohorts kept separate; no numeric stopping policy.

**A new result may fix the latest complaint yet be a worse answer to the original request. Evaluate the consequential gap and the retained alternatives, rather than counting verdicts or following the most recent comparison.**

The old Bernini fewshot full-knowledge loop selected v2 after later comparisons centered on v2/v3; historical independent scores gave v1 stronger editing and style but weaker preservation. The choice was a tradeoff, not a straightforward refinement. In the new batch, F004 v2 recovered tabletop placement and recognizable faces while losing much of the arena; F003 v3 recovered a guitar relative to v2 but remained inferior to v1 for the selected costume-and-performance compromise. A repaired subproblem does not define the best delivery.

The significance of a discrepancy follows the user's task. Architectural elaboration can be compatible with a broad etching interpretation, yet matter greatly when a specific building's identity is requested. In historical 027, online and independent judgments disagreed about architectural severity. This disagreement motivates checking the task and image evidence, not automatically preferring either judge. A structurally valid score does not resolve the creative tradeoff by itself.

The new batch also separates stable continuation from useful continuation: F004 v3 kept the successful foreground without a clear arena gain, while F006/F007 made visible requested gains. Across seven tasks, four final selections returned to earlier candidates. All seven stopped because of budget, so their choices inform comparison but provide no test of autonomous stopping.

Another attempt is meaningful when its proposed outcome would change the delivery choice or resolve an important remaining need, and its realization has a reason to differ from failed attempts. When a usable result already answers the request, incidental or unmeasured detail may have little value to pursue. When a required activity or named edit still fails, 'best available' remains qualified. No universal preservation-first ranking or fixed retry count follows.

Evidence: [historical score table](evidence/historical-score-extract.md); [old B fewshot full](evidence/B-FS4-full.json); [old B 027](evidence/H-B-027__short__full_knowledge.json); [F003](evidence/F003.json), [F004](evidence/F004.json), [F006](evidence/F006.json), [F007](evidence/F007.json). Earlier totals such as 'two preferred later attempts' depend on preservation-prioritized interpretation, not strict multi-objective dominance. Related: [realization change](entries/realization-change.md).
