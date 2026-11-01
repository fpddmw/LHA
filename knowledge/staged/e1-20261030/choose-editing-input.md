# Choose an editing input

[Decide to continue or stop](decide-to-continue-or-stop.md) · [Respond to unmet requirements](respond-to-unmet-requirements.md) · [Express edits](express-edits.md)

Version E1 (staged, replaces v1). In this batch 48 of 57 generations restarted from the source. A restart re-rolls every property, including the ones that already worked. Choose the input for what the next change needs.

### I1 · Continue a candidate for additive or texture changes
When: the candidate supplies useful appearance and the scene information needed for an additive or texture change. Existing defects remain relevant; the supporting inputs were not fully preserved.
Do: generate from that candidate and describe only the addition, relative to what it already shows.
Why:
- B/FS4-no v1→v2 added the missing Earth view and metallic panels.
- B/024L-full v1→v2 extended glitch texture to the seats and windows (indep E.81→.88, C.88→1.0, the best candidate in that loop).

Limits: each pass can add small artifacts; B/FS4-no v2 gained extra ball-like marks.
Mechanism hypothesis: the candidate already supplies part of the desired appearance as visual conditioning. A compatible environmental or texture addition may build on that support. A request that contradicts existing geometry instead asks the renderer to reorganize it, with a different risk. The observed gain is conditional on the content that remains available, not the candidate being chronologically latest.
Status: observed (2 runs) · Bernini; transfer unvalidated

### I2 · Lower expectations for precise geometry repair on a candidate
When: the remaining change reshapes or resizes a specific object, landmark or garment silhouette.
Do: on the recorded Ditto setup, prefer retaining a usable approximation or a source-based alternative over another precise shape correction. Explicit positions and proportions did not reliably bind the correction to the intended instance; transfer remains untested.
Why:
- D/027S-full v3 asked a candidate for a "compact rounded dome", and the renderer added a second large dome instead of reshaping the landmark.
- D/001L v3 asked a candidate to raise necklines into standing collars, with no visible change.

Status: observed (2) · Ditto; Bernini untested

### I3 · Restart from the source only when the source has what the fix needs
When: the candidate lost identity, structure or action information present in the source.
Do: restart from the source, and change the realization that caused the loss (narrower scope near faces, removing the authored addition that covered the structure). Restarting with the same design re-rolls the same risk.
Why:
- B/003S v3 (restart with a recolored jacket instead of a robe) recovered the chair.
- B/024L-no v2 and v3 (restarts with longer prompts) introduced major damage absent from v1.
- B/027S-no v2 (restart) introduced major damage; v3 only tied v1.

Mechanism hypothesis: a source restart restores conditioning information, but it also removes the acquired visual treatment. It is useful when the proposed realization resolves the conflict that destroyed the needed evidence. In B/003S, replacing the authored robe with a fitted recoloring changed the occlusion problem; the example does not isolate source choice from realization choice.
Status: mixed; route and realization changed together

### I4 · Branch from an earlier candidate to escape a regression
When: the latest candidate added a defect that an earlier candidate did not have, and that earlier candidate still carries the useful appearance.
Do: generate from the earlier candidate.
Why: D/024L-full v3 from v1 avoided v2's opaque bars.
Status: single

### I5 · The best delivery and the best input can differ
When: selecting the next input.
Do: choose the candidate whose content the change depends on. It need not be the current best result; keep the best result available for delivery.
Status: operating convention
