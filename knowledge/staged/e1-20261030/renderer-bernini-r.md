# Renderer profile: Bernini-R

[Ditto profile](renderer-ditto.md) · [Probe record](../../model-experience/bernini-r.md) · [Evidence index](evidence-index.md)

Version E1 (staged). Configuration in the 2026-10-30 loops: `ByteDance/Bernini-R-1.3B-Diffusers` rev `ff4c5d4`, 40 steps, `v2v_apg`, max image size 848, empty negative prompt, no prompt enhancer, seed 42 unless the Planner set one, 101 frames at 20 fps, 512-token limit. About 8–13 minutes per clip on an RTX 5090. Cards describe these cases and configuration only; exact frames and timing remain task-specific in receipts.

| ID | Behavior | Planning consequence | Evidence | Status |
|---|---|---|---|---|
| B1 | Whole-image medium or style changes from a concrete prompt succeed on the first attempt (storybook, etching). | Expect success on short style requests; apply S1 strictly. | B/041S both arms, B/027S both arms: v1 indep pass | observed |
| B2 | Large environment replacement is **under-applied**: original room elements persist (column, floor, barriers in all six fewshot candidates), and Earth was missing in both first attempts that asked for it. | Expect partial environment change. Continuing a candidate can add the missing elements (I1). Whole-room replacement was incomplete on this source; transfer remains untested. | B/FS4 both arms | observed |
| B3 | Local emissive effects land on the wrong part inconsistently: the glow was on the tabletop rim in 2 of 6 candidates and on the supports in 3 of 6. | Treat part placement as uncertain; one rephrased attempt at most (R3). | B/FS4 | mixed |
| B4 | Faces change under large edits near people: identity, apparent age and expression changed in all three B/001L candidates (replacement headwear). Small accessories are lost: the far player's glasses were lost or unresolved in 5 of 6 fewshot candidates, and the one exception had almost no environment change. | Strong transformation and identity preservation trade off. Narrowing the edit near faces helped (B/001S v3: fail→partial). Naming the identity details did not. | B/001L, B/001S, B/FS4 | observed |
| B5 | Glitch: color fringing, posterization, neon blocks and scan textures appear readily. The online review never confirmed displaced strips of scene content (0 of 6 candidates). Chasing it lowered independent scores (B/024L-no: E1.0→.88→.81 with new major damage). | Lower expectations for wording-only displacement retries; a different realization remains testable. Report the unmet or unknown effect. | B/024L both arms | observed |
| B6 | An unstated subject orientation can flip (back-facing reader turned to face the camera); stating it fixes it. | State the orientation and pose of key subjects in the first prompt. | B/003S v1→v2 | single (same on Ditto) |
| B7 | Facial expression timing drifts during costume edits (a smile appearing early or disappearing). | Expect expression drift on close-ups; report it rather than chase it. | B/001S, B/001L | observed |
