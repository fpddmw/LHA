# Staged experience E1 (draft, 2026-10-30)

Status: **staged, not active.** Nothing here is in `knowledge/experience/catalog.json`. Default Planner runs do not read it; explicit candidate snapshots/replay can select it. Existing run snapshots remain unchanged. Publication follows the reviewed path in [the two-level RSI design](../../../docs/two-level-rsi-design.md).

## What changed relative to active experience v1

Active v1 pages are common-sense prose. This draft rewrites experience as **decision rule cards**: a trigger, an action, the recorded evidence, known limits and an evidence-status label. Uncertainty is carried by the status field and the evidence counts instead of repeated qualifying sentences. Each card is meant to change a concrete decision: continue or stop, which input, how to phrase, what to compare.

| Page | Kind | Scope |
|---|---|---|
| [decide-to-continue-or-stop](decide-to-continue-or-stop.md) | decision rules | any renderer |
| [respond-to-unmet-requirements](respond-to-unmet-requirements.md) | failure type → response | any renderer |
| [choose-editing-input](choose-editing-input.md) | decision rules (replaces v1) | any renderer, renderer notes inline |
| [express-edits](express-edits.md) | phrasing rules (replaces v1) | any renderer |
| [inspect-and-compare](inspect-and-compare.md) | selection rules (replaces v1) | any renderer |
| [renderer-bernini-r](renderer-bernini-r.md) | capability profile | Bernini-R only |
| [renderer-ditto](renderer-ditto.md) | capability profile | Ditto only |

`use-design-knowledge` v1 is kept unchanged. The [evidence index](evidence-index.md) resolves every short evidence ID to its state file and, where available, the independent record.

## Card format

```
### <ID> · <rule in one line>
When:   trigger condition the Planner can check from the task, ledger or reviews
Do:     recommended action (or what to avoid)
Why:    recorded outcomes with counts and evidence IDs
Limits: counterexamples, confounds, missing evaluations
Status: single | observed | mixed | validated · scope
```

- `single`: one case. `observed`: repeated in at least two recorded loops (some share a source; not independent samples) without contrary evidence. `mixed`: supporting and contrary cases both exist. `validated`: survived a controlled comparison (none yet).
- Online Critic statements are labeled "review"; independent evaluation scores are labeled "indep". Ditto has independent records only for 041.

## Provenance and role in experiments

Authored by the coding assistant from the 23 completed loops of 2026-10-30 (Bernini 11, Ditto 12) and the 19 Bernini independent records. It is **not** an output of the automated global-RSI proposer. Its intended uses:

1. Format and quality reference for the automated proposer (`collect → propose` in the design).
2. A separately labeled "assisted E1" arm, compared against the automatically proposed E1 and the active v0.

It must not be reported as the system's own self-improvement. All tasks cited here are development-exposed.

## Calibrated implementation

The user approved refinement and implementation. This assisted candidate remains staged and explicitly selected for development/replay, not validated or globally published. Cards are defaults, not an executable router. Failure distinctions may overlap. Observations, strategy hypotheses and budget policies have distinct status. Case configuration and counterexamples remain part of the evidence. All 45 metadata summaries are visible with renderer applicability; none is silently truncated. Each summary expresses its own trigger/action, while the full text retains evidence and mechanism qualifications. S1/S2 observations are scoped to Bernini; transfer is a hypothesis. The automatic proposer must produce its own evidence-linked revisions within a maximum of three actual card changes per round.

## Mechanism explanations

The calibrated cards now distinguish observations from explanations of binding, conditioning, identity reconstruction and connected visual fields. These explanations propose what the next attempt should change and why, while their causal status remains unvalidated. They are not fixed designs, aesthetic prescriptions, or a promise that verbal locality locks pixels.
