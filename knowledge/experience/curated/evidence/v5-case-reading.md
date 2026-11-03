# Read the complete v5 training cases

The compact [score extract](v5-train-cases.json) retains its original 38 rows unchanged. The case files below restore exact submitted prompts, known input identities, full saved reasons and stable output hashes. They include the Direct outputs cited by the prose. No model or renderer was called to assemble these records.

Open a case with `read` and continue with the returned line/character position. Open a comparison image with `view_reference` using its ID. The images are the original six-time comparison sheets; judge evidence references inside the reports retain their original coverage and are not aliases for these sheets.

| Case | Exact record | Comparison image ID | Candidates |
|---|---|---|---|
| 001 short | [v5-001-short-case.json](v5-001-short-case.json) | `EV-V5-001-short-comparison` ([sheet](frames/v5-001-short-comparison.jpg)) | 3 |
| 001 long | [v5-001-long-case.json](v5-001-long-case.json) | `EV-V5-001-long-comparison` ([sheet](frames/v5-001-long-comparison.jpg)) | 9 |
| 005 short | [v5-005-short-case.json](v5-005-short-case.json) | `EV-V5-005-short-comparison` ([sheet](frames/v5-005-short-comparison.jpg)) | 4 |
| 005 long | [v5-005-long-case.json](v5-005-long-case.json) | `EV-V5-005-long-comparison` ([sheet](frames/v5-005-long-comparison.jpg)) | 12 |
| 026 short | [v5-026-short-case.json](v5-026-short-case.json) | `EV-V5-026-short-comparison` ([sheet](frames/v5-026-short-comparison.jpg)) | 5 |
| 026 long | [v5-026-long-case.json](v5-026-long-case.json) | `EV-V5-026-long-comparison` ([sheet](frames/v5-026-long-comparison.jpg)) | 8 |

[Original steady-train observations](v5-steady-original-cases.json) preserve only the three outputs used in the original account. The 011 PE first prompt is not in that page; its wording remains unreported.

The 005 short and 026 long contrasts are especially useful: the first prompts already name the requested layout or construction. Explain subsequent changes from their exact wording and inputs, rather than treating an unrealized instruction as an omission. Full reasons remain attributed judge observations; the causal explanation belongs to the analyst.
