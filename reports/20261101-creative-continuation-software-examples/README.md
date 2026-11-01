# Software examples: continuation and informed delivery

These are exact saved inputs and a response from mocked-model harness calls over CPU synthetic media. They establish software behavior, not observed model improvement. No provider API or GPU was used.

- [Initial model input](initial-model-input.json): common instructions and spent facts.
- [Continuation input](continuation-model-input.json): pre-announced questions before the next decision.
- [Accepted generate](accepted-generate.json): input, actual prompt and free-text explanation in one response.
- [Cached-report confirmation input](cached-report-confirmation-input.json): the complete report with its original comparisons and supplemental checks, bound to the new proposal.
- [Confirmation proof](cached-report-confirmation-proof.json) links that input to the later finish response.

The mocked Critic was invoked once during work and zero additional times for delivery. Paths identify the retained local fixture; the exported text is unmodified.
