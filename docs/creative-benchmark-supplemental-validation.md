# Supplemental review of a descriptive-word validation false positive

Date: 2026-11-01. Disposition: agent independent review / supplemental validation.
The main chat reviewed the full original GLM answer, exact original request,
frozen validator and hash-bound review material under the user's existing
execution/recovery and independent-review division. This is not individual human
approval of an answer. The disposition establishes role compliance for the
reviewed sentence; it does not independently confirm visual scoring accuracy.

## Exact retained case

- Topic: `fewshot_001`; full-experience first candidate.
- Candidate SHA256: `c6f560c789a45a2cc234bca88962503c2bdc3836ce59cca6d1ee935972ecc1d2`.
- Judge: `GLM-5.3-Flash`; cache key
  `2c958b7b75461881254aafb0ae49c0253393908a8d5ea94c1fcc8ac090c8a09c`.
- Raw answer SHA256:
  `e1539b448b0d97bb21f3804b06292e2414396281356a71dc0e298aed0473cada`.
- Original frozen result: `Critic output contains prohibited action guidance`.
- Exact field: `main_scores.instruction_adherence.limitations[2]`.
- Exact matched word: `should`.

The complete reviewed sentence is:

> The request does not state whether the basketball hoop should be removed, so its retention is treated as an ambiguity rather than a clear violation.

The sentence explains ambiguity in the original request and the interpretation
used for this existing candidate. The original request does not specify hoop
removal. Independent review found no proposed subsequent action in this sentence
and confirmed that it was the only match of the prohibited-guidance pattern.
The original score vector remains 3/3/3/2/3 in frozen dimension order. The original
answer, provider attempt, rejection and all supplied evidence remain intact.

## Bounded implementation

`scripts/creative_final_validation.py` is an outer cache adapter. No frozen source,
model-visible instruction, evidence-selection policy, scale or fingerprint is
changed. Its explicit review record binds the original response, full identity,
evidence packet, immutable model input, original rejection and frozen validator.
It requires the exact field, original sentence, reviewed match and independent
review provenance.

The adapter first reproduces the exact frozen error on the full original report.
It then masks only the reviewed modal in a validation-only copy and executes the
complete frozen validator again. Every other check must pass; real action
guidance elsewhere still fails. The stored/cached report contains the full
original sentence and all original scores. No model call or semantic rewrite is
added. The original rejection remains a rejection; the new accepted disposition
is explicitly `supplemental_review_passed`.

The record and validation result live in the original candidate's
`supplemental-review/` directory, so the existing archive copies them with its
unaltered raw judgment evidence. Position records and `scoring-scope.json` label
`native_passed` and `supplemental_review_passed` separately. They retain reviewer
provenance, rationale, exact exemption, other-check results and adapter version.
The same role-compliance standard applies to every arm and both judges. Similar
new cases remain retained for review; score magnitude is not a release criterion.

Three additional offline checks passed: exact-sentence acceptance with original
text/rejection and zero new calls; rejection after a response-hash or field
change; and rejection of actual action guidance. The thirteen focused scheduling
and coordinator checks also passed. These fixtures establish bounded software
behavior and do not measure benchmark quality.
