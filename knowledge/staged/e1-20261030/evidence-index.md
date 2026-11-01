# Evidence index for staged E1

ID format: `<renderer>/<task>-<arm>`, where renderer is `B` (Bernini-R) or `D` (Ditto), task is `041S`, `027S`, `024L`, `FS4` (fewshot_004 long), `001S`, `001L`, `003S`, `003L`, and arm is `full` / `no` (knowledge). Benchmark 001/003 ran only with full knowledge. Event IDs such as `e0009` refer to that run's `events/`.

Root: `out/agent_loop_live/20261030/`.

| ID | State | Independent records |
|---|---|---|
| B/041S-full, B/041S-no | `phase2/completed-041-pair/tasks/041__short__{full,no}_knowledge/run/state.json` | `independent-evaluation/` (041) |
| B/027S-full, B/027S-no | `phase2/completed-027-pair/tasks/027__short__{full,no}_knowledge/run/state.json` | `independent-evaluation-027/service/evaluations/bernini__027__short__*` |
| B/024L-full, B/024L-no | `phase2/completed-024-pair/tasks/024__long__{full,no}_knowledge/run/state.json` | `independent-evaluation-024-fewshot/service/evaluations/bernini__024__long__*` |
| B/FS4-full, B/FS4-no | `phase2/completed-fewshot-004-pair/tasks/fewshot_004__long__{full,no}_knowledge/run/state.json` | `independent-evaluation-024-fewshot/service/evaluations/bernini__fewshot_004__long__*` |
| B/001S, B/001L | `phase2/completed-benchmark-001-tracks/tasks/benchmark__001__{short,long}/run/state.json` | none |
| B/003S | `phase2/completed-benchmark-003-short/tasks/benchmark__003__short/run/state.json` | none |
| D/041S-full, D/041S-no | `ditto-phase2/completed-041-pair/tasks/041__short__{full,no}_knowledge/run/state.json` | `ditto-independent-evaluation/` (041 only) |
| D/027S-full, D/027S-no, D/024L-full, D/024L-no, D/001S, D/003S | `ditto-phase2/completed-pre-stop-six-tasks/tasks/<task>/run/state.json` | none |
| D/FS4-full, D/FS4-no | `ditto-phase2/completed-fewshot004-{full,no}/tasks/fewshot_004__long__{full,no}_knowledge/run/state.json` | none |
| D/001L | `ditto-phase2/completed-benchmark-001-long/tasks/benchmark__001__long/run/state.json` | none |
| D/003L | `ditto-phase2/completed-benchmark-003-long/tasks/benchmark__003__long/run/state.json` | none |

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

## Generation cost recorded in execution receipts

- Bernini-R on the RTX 5090: 490–530 s per clip for benchmark 001, 640–760 s for the other tasks.
- Ditto on the RTX PRO 6000: about 755 s per clip for benchmark 001 and 930–1060 s for the other tasks.
- Online Critic: 80 reviews averaged 8.55 model calls each; 14 reviews did not complete and were retried by the Planner.

## Retained disagreement

The 027 preservation/severity concern remains unresolved. The historical independent labels and online observations are retained as separate evidence. A later calibration must inspect that disagreement against the frozen task boundary; these records do not turn either judge into ground truth.
