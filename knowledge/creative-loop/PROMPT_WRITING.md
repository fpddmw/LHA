# Turn the design into a rendering prompt

For each `generate` action, use the original request and the viewed source and
selected-input frames to write a concrete English rendering prompt for a
recast: the same moment, built as part of the target world or medium.

When generating from the source, open with the world and the moment in a sentence: what the scene is and what the
people in it are doing. Then give each visible plane its own clause, saying how the
target medium builds it: each person and costume, held props, vehicles or furniture,
ground, middle distance, background, sky, and the light that falls on all of them.
Name the construction (the marks,
materials and surfaces of the medium) rather than a list of style adjectives.

Give each person a counterpart that stays that person, in few words. Say where the
camera is and how it moves, because the prompt describes this video, not a generic
scene. State the most consequential changes with the clearest wording.

When continuing from a retained candidate that already holds the desired world,
state the new change and a short clause for what to keep. Name the affected planes,
parts and their construction directly. Let the selected video carry the established
design instead of describing the whole scene again. If that foundation is unusable,
choose the source or an earlier intact input; a source restart needs a freshly
written full prompt incorporating the successful design.

After generation, compare the findings (the Critic's or your own) with the original
task, selected input and submitted prompt. Decide which visual changes address the
important findings. Carry successful choices forward and integrate the chosen
changes into the next input-specific prompt, including dependent changes in
surroundings, light or action. Use the complete construction for a source restart
and the focused change for a compatible candidate continuation.

Keep the prompt within the renderer's text capacity: Bernini accepts 512 encoder
tokens including its official prefix; Ditto accepts 512 text-encoder tokens. A
prompt over the limit is refused before rendering. Combine repeated descriptions and
spend the available text on distinctive visual relationships. Keep optional working
notes and source references in the task workspace; submit the rendering description
in `generate.prompt`.
