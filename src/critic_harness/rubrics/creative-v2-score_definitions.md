# Shared video scoring definitions

Read-only scoring reference for interpreting reports. The fixed dimensions and anchors apply across the experiment.

## Status and evidence

Use status scored with integer score 0, 1, 2, 3 or 4 only when the supplied evidence
supports the judgment at the described scope. Otherwise score is null: unknown means
insufficient/ambiguous evidence; not_assessed means a technical omission;
not_applicable means the dimension has no meaningful application, with a reason.
Scores describe observed quality; they are not probabilities or calibrated measurements.
Never turn an unseen interval into an observed failure or an observed success.

Reference supplied evidence IDs. Source/output preservation judgments require evidence
from both. A local counterexample can establish a local defect without full coverage.
Temporal scores may describe sampled continuity supported by consecutive frames, with
the unsampled intervals stated as limitations. Exact trajectories or full-duration
identity preservation need sufficient observations; use unknown where the requested
precision is unavailable. Dense windows and overview frames are explicitly different.

## Main dimensions and integer anchors

### instruction_adherence

Evaluate execution of the user's requested changes, including their object, part,
region and requested visual relationships. User-emphasized goals matter; your own
design preference does not add requirements.

0: The requested transformation is absent or contradicted throughout visible evidence.
1: Only a minor part is recognizable; principal requested changes are absent or wrong.
2: A substantial part is present, with consequential omissions or wrong bindings.
3: Principal changes are present with minor omissions or imprecision.
4: Requested changes and their consequential bindings are convincingly realized in
the supplied evidence.

Boundary: glowing table legs do not fulfill a glowing tabletop rim. A short style
request allows several valid interpretations; do not score against an invented template.

### content_preservation

Compare source and result for continuing subjects, identity, action and scene
relationships that the request expects to retain. Account for explicitly allowed
changes and transformations inherent in the requested medium.

0: Essential source content/action/identity is lost or replaced.
1: Major unintended changes undermine several essential relationships.
2: The scene remains identifiable but has consequential unintended changes.
3: Essential content remains with minor local deviations.
4: Expected content and relationships remain consistent within the observed scope.

Boundary: watercolor marks replacing photographic texture are allowed stylization.
An extra player, missing instrument or altered object interaction is a content change.
Do not assume every source contour must be pixel-identical or silently make it a core goal.

### temporal_consistency

Assess visible motion coherence, object persistence, transitions and unwanted flicker.
Use chronological/dense evidence, reporting its actual temporal coverage.

0: Observable discontinuities make the sequence or action incoherent.
1: Frequent severe jumps, identity switches or flicker disrupt the sequence.
2: Motion remains understandable with clear intermittent discontinuities.
3: Sampled motion is coherent with minor transient artifacts.
4: Supplied chronological evidence shows coherent persistence and smooth changes,
with no observed consequential temporal defect; report unsampled coverage limits.

Boundary: a requested glitch effect may intentionally disrupt appearance; judge
unintended instability and whether meaningful action survives. Sparse stills alone
cannot support precise ball trajectories or lip synchronization. Use unknown for those.

### visual_integrity

Assess anatomical, geometric, object, occlusion and image-construction defects relative
to the requested medium, distinguishing deliberate stylization from unintended damage.

0: Severe structural breakdown prevents a coherent reading of the image.
1: Major anatomical/object/spatial defects dominate important regions.
2: Recognizable structure contains clear, consequential local defects.
3: Mostly coherent structure with minor visible defects.
4: No consequential unintended structural defect is visible at the supplied resolution.

Boundary: flat perspective in an illustration can be intentional. Fused hands, a
duplicated phone or contradictory occlusion are defects when unsupported by the request.

### aesthetic_coherence

Assess coherence and legibility of the achieved visual language: materials, palette,
lighting, composition and integration. Judge relative to the requested style, without
equating photorealism, ornament density or personal taste with quality.

0: Conflicting or broken visual treatment prevents a coherent result.
1: Strong unresolved inconsistencies dominate the appearance.
2: A recognizable visual direction has substantial inconsistencies or poor integration.
3: A coherent direction has minor inconsistencies or awkward visual emphasis.
4: Visual relationships work together convincingly for the requested direction.

Boundary: coordinated flat colors can be excellent storybook art. More texture or
realistic shading is not automatically an improvement. A coherent wrong style can
score well here while scoring poorly on instruction_adherence.

