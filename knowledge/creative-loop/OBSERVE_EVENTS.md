# Inspect complete events and read coverage

Use a sampled overview to locate a question. Use consecutive native frames when a decision depends on contact, movement, occlusion, an interaction or its outcome. The original request determines whether source motion should be retained or the result should realize a new event.

## View an event yourself

```json
{"action":"observe","arguments":{"video":"v1","mode":"continuous","start":1.2,"end":3.8,"count":16,"page":1}}
```

This requests the complete interval; count is the number of native frames on the current page, not a sparse sample of the whole event. Follow the returned next_arguments in another observe operation. Pages overlap by one frame, preserving boundary transitions. Reopen an observation by its ID when needed. Each response exposes the supplied frames, actual PTS, page_coverage and cumulative coverage for that video, interval and crop.

A single video allows 2–16 frames per page. A multi-video observation has at most 32 frames across its videos; the default divides that allowance. Specify crop as normalized [left,top,right,bottom] when spatial detail matters. Coverage is tracked separately for different crops. Videos retain their own timestamps and page boundaries; corresponding seconds alone do not establish motion alignment.

## Set the focus of automatic online review

Every successful generation is checked in the configured mode. In Critic mode a
separate reviewer inspects it; in Planner mode inspect it in your current task
context. Supply focus before generation to locate a question. It stays outside
the renderer payload.

```json
{
  "action": "generate",
  "arguments": {
    "input_video": "source",
    "prompt": "Create a coherent blue treatment of the scene.",
    "review_focus": {
      "focus": "Inspect the contact and release.",
      "events": [
        {
          "start": 1.2,
          "end": 3.8,
          "question": "Is the interaction coherent from preparation through its outcome?"
        }
      ]
    }
  }
}
```

Both modes use the same six-frame overview and native-frame observer. The Critic
receives the original request, submitted and actual prompts, source, current input,
candidate, focus and relevant references. It chooses observations as needed and
returns concrete findings. The Planner can make its check beside the next action.
Continuous-frame pages, crops and reopened observations have the same semantics
in both modes. Final delivery reuses those per-generation checks.

## Interpret what was actually seen

- observed_intervals describes usable decoded-frame coverage; continuous_evidence_intervals identifies time between adjacent observed native frames.
- media_missing_intervals is footage absent from the video. unreviewed_intervals exists in the video but lacks a usable observation.
- complete means coverage is complete, not that the event is correct or the task is fulfilled. An overview does not count as continuous evidence.

Read the question, findings and these ranges together. A local defect can support a local judgment; an unseen interval stays unresolved. Natural occlusion can be valid staging while leaving the concealed contact uncertain. Inspect the new event's own progression where behavior reconstruction is authorized.

Original observations and reviews remain available through history. Independent
final evaluation uses its own frozen scoring and evidence protocol and is never
returned as this task's online feedback.
