# EX-object-continuity: A moving prop must remain the same participant across interaction states

Revision 1. Draft for review. New Bernini hypothesis from F001/F006. Based on saved sequence observations; no new motion tracking or causal test.

**A prop can be recognizable in every local view while failing to be one continuous object in the action. Counting nouns in the prompt does not establish continuity of possession, visibility and release.**

F001's first result showed an extra basketball beside the shooter while the released ball was airborne. Its second prompt explicitly described one moving basketball and empty hands after release, yet the result introduced an extra person and a shot without the ball. The third kept a recognizable jump shot but still had an additional opening ball. In F006 v1, the review found a second phone-like object during retrieval, although the ending retained one prominent phone.

These failures concentrate around state transitions: concealed to visible, held to released, one hand to another. A plausible explanation is that local visual plausibility is being reconstructed without consistently binding all those states to one participant. This is more specific than 'the model duplicates objects': it identifies the relationship that a source action supplies and a new rendition can lose.

The useful question is which transitions establish that the ball or phone is the same object. Inspect hand-object contact, occlusion, possession and the post-release state when they are consequential. A general scene summary or endpoint frame can miss the break. If the relationship was omitted, stating it clarifies the target; if it was already explicit, repeating 'one' does not materially change the proposed solution.

F006 v2 restarted with a more explicit concealed-then-retrieved phone description and no duplicate was observed. However, precise phone and hand preservation remained unknown, the costume disappeared, and multiple changes were simultaneous. This is a partial counterexample to inevitable duplication, not proof of a reliable wording fix. The novel value is a better failure interpretation and inspection target; an effective control strategy remains open.

Evidence: [F001](../evidence/F001.json), v1 late-interval and v2/v3 findings; [F006](../evidence/F006.json), v1 retrieval and v2/v3 outcomes. These are two source scenes, with different actions, not replicated tests of one duplication mechanism. Related: [activity relations](activity-relations.md), [time binding](time-binding.md), [realization change](realization-change.md).
