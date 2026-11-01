# Renderer profile: Ditto

[Bernini-R profile](renderer-bernini-r.md) · [Evidence index](evidence-index.md)

Version E1 (staged). Configuration in the 2026-10-30 loops: Wan2.1-VACE-14B rev `539c162` with Ditto LoRA rev `b0337f2`, 50 steps, CFG 5.0, LoRA alpha 1.0, empty negative prompt, no prompt enhancer, tiled bf16, seed 42 unless the Planner set one, 101 frames at 20 fps, 848×480, 512-token limit. About 12.5–17.5 minutes per clip on an RTX PRO 6000. Independent scores exist only for 041; the other observations come from online reviews.

| ID | Behavior | Planning consequence | Evidence | Status |
|---|---|---|---|---|
| D1 | Short style requests succeed on the first attempt. | Apply S1. | D/041S both arms (indep pass); D/003L v1 review: no defect | observed |
| D2 | Large environment replacement is **strong and complete** on the first attempt (Earth, metal walls, rim glow in every fewshot v1), the opposite of Bernini B2. | On this source, environment strengthening was not the main remaining need; prioritize the actual preservation tradeoff (D3). | D/FS4 both arms | observed |
| D3 | People are re-rendered during large scene edits: face shape, hairline and apparent age changed in all six fewshot candidates. Prompts naming "middle-aged" or "receding temples" produced older or grayer people (2 of 2), while "thinning hair" in D/FS4-no v2 produced thicker hair. Eyewear in the six attempts: opaque glasses or visor 3, absent 2, faithful glasses restored 1 (D/FS4-no v2). | Identity loss is the main cost of Ditto's strong edits. Use X4 as a strategy hypothesis; descriptive constraints were insufficient here. | D/FS4 | observed |
| D4 | Garment silhouette changes are not realized (standing collars, broad horizontal headdress: 0 of 3), while ornament, embroidery and color are. | Lower expectations for wording-only silhouette repair; one failure does not establish incapability. | D/001L | observed (one task) |
| D5 | Warm or candle lighting tints skin yellow-orange (6 of 6 candidates on 001). A correction pass on a candidate made it worse. | Ask for neutral face light in the first prompt; do not try to correct the cast on a candidate (R4, I2). | D/001S, D/001L | observed |
| D6 | Editing a candidate to correct one object adds instead of modifies (an extra dome), and asking for added glitch blocks produced opaque overlay rectangles. | Avoid candidate-based geometric correction (I2). | D/027S-full v3; D/024L both arms, v2 | observed |
| D7 | Short structures (antenna, tower cap, parapet) are embellished into ornate features even when the prompt asks to keep them plain. | Expect architectural embellishment on etching-like styles; report it. | D/027S both arms | observed |
| D8 | Glitch displacement of scene content was not confirmed by any review (0 of 6 candidates); scan lines and RGB fringes were achieved. | Lower expectations for wording-only retries, as in B5; unconfirmed is not proof of universal incapability. | D/024L both arms | observed |
| D9 | The subject orientation flip and its fix match Bernini B6. | State orientation in the first prompt. | D/003S v1→v2 | single |
