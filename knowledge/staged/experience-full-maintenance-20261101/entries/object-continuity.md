# EX-object-continuity: Preserve a moving prop's role across state changes

Revision 2. Draft for review. Bernini; F001/F006.

**For an existing action, prefer a concise account of the prop's continuous role over rewriting its choreography. Inspect retrieval, occlusion and release, where a recognizable object can become an extra instance or disappear from the action.**

## The vulnerable relationship is continuity of participation

F001 showed an extra ball while another was airborne. A later detailed shot description still produced broken possession and an extra player. F006 v1 showed a second phone-like object during retrieval even though the ending had one prominent phone. A correct endpoint or a correct object category therefore misses the critical question: did the same object stay involved through the transition?

A useful working model is that locally plausible states can be rendered without consistently binding possession, visibility and release. Long prose describing several states adds more conditions to realize. Temporal descriptions becoming simultaneous instances is one possible explanation to investigate; the practical priority is to avoid unnecessary re-choreography of motion already supplied by the source.

## Describe the binding that matters

For a preserved action, make the existing ball or phone the participant and tie it to the relevant source interaction. An illustrative direction is: preserve the source ball's possession and release during the existing shot. Add transition detail when it resolves a particular ambiguity, such as whether the hands remain occupied after release. Stop adding repetitions of 'one' once the singular object and relation are already explicit; revise the competing transformation or select an input with clearer continuity instead.

Sequence wording can be useful. F006 v2 explicitly described the phone as concealed, retrieved and raised, and the saved review observed no duplicate. That result favors using needed sequence information selectively. It does not support a blanket ban on temporal language or a general short-prompt cure.

Inspect just before and after the relevant contact or occlusion, not only the opening and final frame. When a duplicate is already part of a candidate, favor an earlier input with the original interaction for a fresh realization. If other useful edits depend on continuing the candidate, treat continuity as the specific uncertain repair and inspect that transition after generation.

**Evidence.** [F001](../evidence/F001.json), v1-v3; [F006](../evidence/F006.json), v1 retrieval and v2/v3. Saved online observations across two source scenes; precise phone/hand motion remained unknown after the observed duplicate disappeared. Concise source-linked phrasing is a proposed working default. Related: [activity](activity-relations.md), [time](time-binding.md).
