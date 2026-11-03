# Fixed-budget Planner experiment completion

User authorization: change only whether the experimental Planner may finish early.

New benchmark full/none Loop tasks use their complete configured generation
allowance before final selection, in both Critic and Planner-review modes. The
Planner still chooses prompts, inputs and the final candidate, including an early
candidate. Existing generation limits, submitted-attempt accounting, time/token
protections, review behavior, Direct/PE adapters and knowledge remain unchanged.
Real failures and deadlines retain their original interrupted/limited outcomes;
they do not claim full-budget completion. No experiment is started by this change.

Implementation: freeze the completion policy in new batch/task identities, expose
it in the existing budget context, block early model-authored finish for every
stop reason, and retain observation/review/selection after the last attempt.
Historical tasks without the new policy retain their recorded behavior. Existing
frozen runtimes are not patched or replayed automatically.

Verification: offline tests cover policy wiring, early-stop rejection, final
selection of an earlier candidate, required review, attempt accounting, deadline
settlement and resume. Evidence is saved under
`out/fixed_budget_completion/20261103`.

Status: implemented and verified locally. The active creative-loop configuration
and newly prepared benchmark Loop tasks use fixed-budget completion. The existing
four-attempt default is unchanged. Offline verification passed 99 tests across
completion, continuation, iteration, campaign, result and benchmark modules.
No live model calls, GPU runs, deployment or historical-result changes were made.
Saved verification includes the test log, scoped patch and modified-file hashes.

Follow-up authorization: align runtime instructions with fixed-budget completion,
leaving the experience library and all other mechanisms unchanged. The operating
manual, new task instructions and ongoing budget context explicitly give the
experimental completion policy precedence over early-delivery advice. Planner
chooses each prompt and source/candidate input, can explore alternative realizations
or resample, and retains adequate early candidates for final selection. Further
exploration does not require declaring those candidates defective.

Follow-up verification: 26 offline completion, continuation and iteration tests
passed. A scripted run read the unchanged EX-continuation-value entry, then captured
the actual assembled Planner input: the original experience remains visible alongside
the authoritative fixed-budget instructions in the system prompt and ongoing context.
All 74 curated experience files retained their pre-change hashes. No live model,
rendering, deployment or evaluation was started. Evidence is saved under
`out/fixed_budget_completion/20261103/instruction-alignment`.
