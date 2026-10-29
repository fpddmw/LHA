# Reorganization and validation

[Knowledge map](README.md) · [Approved plan](../docs/skill-reorganization-plan.md) · [Source map](source-map.json)

Edition date: 2026-10-29. Validation status: English-edition and design-application integrity checks passed; the content remains available for user review.

## What this work adds

The independent `knowledge/` package contains editorial readings for 111 complete entries, explanations of design relationships, motivated cross-links, 5 domain references and their historical variants, 7 guides, 1 conditional model-experience record, a map, a reading manual, an integration design, and machine-readable provenance.

The English pass converts all working prose, navigation, comparison reasons, instructions, and current planning documents to English. It preserves the accepted organization, stable IDs, source selectors, topic memberships, and related-entry targets. The model retains responsibility for interpreting tasks, exploring knowledge, and making creative choices.

Complete English OPUSCAR descriptions, prompts, shot texts, direction notes, reference statements, and legacy templates are reproduced from the originals. Base templates have complete English reading editions: 6 preserve already-English values and 7 translate Chinese-valued fields with explicit attribution. Domain cards and their 15 rendered variants preserve their original English wording. Images reference the original files. Original-language source files and existing runtime code are unchanged by this pass.

## Design-application revision

The follow-up reviewed all 111 entry editorials, 5 domain editorials, and the 6 existing guide bodies. It enriched 35 entry editorials and 2 domain editorials with concrete relationships between visual mechanisms and possible new designs. The other 79 editorials retained their existing explanations. Selected original prompts were inspected to substantiate the additions; complete source retention was checked across the full corpus.

The revision adds [From knowledge to a visual proposal](guides/design-expression.md), with authored walkthroughs for benchmark main/041 and fewshot/004. Each connects a request, a reading path, source relationships, current design choices, and an illustrative English draft. The drafts are new and untested. The actual experiment inputs and videos are linked separately through the [Bernini-R record](model-experience/bernini-r.md).

The reading manual now explains how to select and adapt knowledge into concrete visual expression. Four existing guides gain application or experience connections; the meaning and time guides retain their content. The map and manifest add the new guide, seven associated-entry links, and one experience record. Original topic memberships and related-entry edges remain intact.

This pass adds conditional style-expression experience from an existing probe. Semantic-preservation strategies, new evaluation calibration, runtime harness work, and generation experiments remain deferred. The source text, experiment files, and runtime code were not edited. Authoring and validation utilities in the task work directory were updated to assemble and check the added content.

## Content review and evidence status

Editorial prose was translated across all 98 OPUSCAR cases, 13 base templates, 5 domain references, 6 guides, and shared documents. The full English originals provide a source-level check on the design relationships described. The program handles extraction, mapping, assembly, and integrity checks; it does not create evidence for the editorial interpretations.

Review concerns include coherent relationships within cases, concrete support for comparisons, distinguishable author advice and curatorial analysis, and the task and model conditions behind historical observations. Clawd, color values, cross-film handovers, and card replacement directions retain their original context. Differences between general prompts and specific timings, including cases 070 and 087, remain visible.

Historical figures come from existing handoffs, reviews, descriptions, or code comments. This pass did not rerun videos, recompute metrics, or rewatch every historical result. Artistic references retain their status as author statements. Content and provenance checks establish the working edition's integrity; Planner behavior and video gains require subsequent runtime evidence.

## Integrity checks

The English-edition validator independently reads original JSON records, template AST values, and rendered domain-card variants. It compares the source map with the pre-conversion baseline as well as current files, so a newly computed hash cannot conceal a change to an original source.

Checks cover:

- One-to-one coverage of all 111 templates and 98 OPUSCAR records.
- Exact preservation of English source fields, all 302 ordered shots with names and durations, and original record hashes including bilingual fields.
- All 98 reference-image files, paths, JPEG signatures, and hashes. This verifies file integrity rather than visual quality.
- Complete base-template keys, value shapes, explicitly translated fields, and unchanged already-English fields.
- All 5 structured cards and 15 complete base, `decisive`, and `execution_only` outputs.
- All original topic memberships and related-entry targets, with seven approved memberships added for the application guide and English comparison reasons.
- Local file links, heading anchors, catalog reachability, and direct entry access from every associated guide.
- Exact quotation of all ten experimental prompts; case-to-input correspondence, completed result metadata, and hashes for experiment sources and delivered videos.
- English working content throughout `knowledge/` and both current planning documents, including folded blocks and JSON values.

The machine-readable check result is saved in the task work directory at `out/skill_reorganization/en/validation.json`. Authoring and checking utilities also remain there. Reading and tracing the delivered package requires only the package and its repository sources, independently of those utilities.

## Verified results

| Check | Result |
|---|---|
| English working files | 131 checked; 0 contain Chinese characters, including folded blocks and JSON values |
| Template coverage | 111 / 111, with stable IDs and source selectors |
| OPUSCAR records | 98 / 98, with complete original English fields and unchanged bilingual source-record hashes |
| Shots | 302 / 302, preserving order, names, durations, and English text |
| Reference images | 98 / 98, with paths, signatures, and hashes checked |
| Base reading editions | 7 attributed translations and 6 unchanged English records; keys, value shapes, and already-English fields preserved |
| Domain material | 5 original structured cards and 15 exact rendered variants |
| Guides | 7 / 7, with all associated entries directly accessible |
| Reading graph | 239 original topic memberships and 239 related-entry edges preserved; 7 application memberships added |
| Local navigation | All file and heading links checked across the package and its two planning documents; current count in the machine-readable result |
| Original source preservation | 321 source references verified against hashes captured before conversion |
| Bernini evidence chain | 10 / 10 condition inputs and prompt quotations; 61 source/media references checked, including all delivered video hashes |

The original English text and source hashes were checked exactly. Translation meaning was reviewed during authoring; these integrity checks do not independently certify every interpretive sentence. The follow-up review covers all existing editorial readings and guide bodies; final readback covers the updated manual, application paths, experience record, and representative revised entries. The review coverage and revised IDs are recorded at `out/skill_reorganization/style_application/review-coverage.json`, alongside a pre-revision archive. The checks establish content and source integrity; they do not independently certify every interpretive sentence.

## Later work

Planner tools, dynamic task state, actual autonomous reading behavior, reflection and evaluation, and video output still require design and implementation. Prompt-expression strategies can now consult the conditional Bernini findings and refine them through later tests. The next phase will consider the broader harness and agent loop. Thin base and domain material retains its stated scope and gaps.

