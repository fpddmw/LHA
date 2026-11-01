# Historical score extract

Verbatim excerpt of the original curated index; not a new recount.
Source: `knowledge/staged/e1-20261030/evidence-index.md`; SHA256: `c07a15fd3c151c74730c621c511b81001a0bc270894bf8b87ed74ec5f0fa9708`.

## Bernini independent scores used in this draft

Semantic scores 0–1 (E edit, C core, D detail, T time); style 1–4; "major" = major unrequested damage. Recorded by GPT-6.1-sol under `lha-evaluation-v1`; these are model judgments, not ground truth.

| Run | v1 | v2 | v3 | Selected |
|---|---|---|---|---|
| B/024L-full | E.81 C.88 style 3.1 major | E.88 C1.0 style 3.7 | E.81 style 3.1 major | v2 |
| B/024L-no | **E1.0 C1.0 style 3.9 pass** | E.88 C.62 style 3.4 major | E.81 C.62 style 2.8 major | v1 |
| B/027S-full | **E1.0 C1.0 style 4.0 pass** | E1.0 C1.0 style 3.8 pass | — | v2 |
| B/027S-no | **E1.0 C1.0 style 4.0 pass** | E1.0 C.88 style 3.8 major | E1.0 C1.0 style 4.0 pass | v3 |
| B/FS4-full | E.72 C.86 T.83 style 3.1 major | E.39 C.92 T1.0 style 2.8 major | E.67 C.78 style 3.5 major | v2 |
| B/FS4-no | E.39 C.92 style 2.0 major | E.67 C.81 style 2.9 major | E.56 C1.0 T1.0 style 2.7 | v3 |
| B/041S-full, B/041S-no | pass (single attempt) | — | — | v1 |

Derived counts used by several cards (Bernini, six multi-attempt loops above):

- 11 later attempts (v2/v3). 2 were preferred under a preservation-prioritized interpretation, not strict multi-objective dominance (B/024L-full v2, B/FS4-no v3). 4 introduced major damage while an earlier candidate had none (B/024L-full v3, B/024L-no v2 and v3, B/027S-no v2).
- Under the reported preservation/style interpretation, v1 was best or tied-best in 3 of 6 loops (B/024L-no, B/027S-full, B/027S-no).
- Online review of v1 in those three loops still reported actionable shortcomings ("partial", or "substantial enough to justify another generation" in B/027S-full e0004).


The unresolved 027 severity disagreement remains open. These GPT scores use the historical protocol and must not be pooled with the creative-loop rubric.
