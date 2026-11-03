# Write a rendering prompt for the selected input

Write a concrete English prompt for the user's original task using the source,
selected input, viewed evidence and relevant available knowledge. The task is a
recast of this source moment into the requested world or medium. Express the result
you intend the renderer to produce, including the relationships and changes that
matter to this request.

`generate.input_video` selects the actual conditioning video. The renderer receives
that video and the submitted prompt; it does not receive your workspace, earlier
prompts or review conversation. Carry the information needed for this attempt in
its prompt. Decide its detail and scope from the selected input and your design.

After generation, compare the actual result with the request, selected input and
submitted wording. Use the available observations and review to decide the next
input, prompt and candidate choice. Source, earlier candidates and the current
candidate remain distinct options.

Bernini accepts 512 encoder tokens including its official prefix; Ditto accepts
512 text-encoder tokens. Over-limit prompts are refused before rendering. Planner
receives the refusal and revises its own prompt; it has no automatic compaction or
truncation step. Keep working notes and references in the workspace, and put the
actual rendering instruction in `generate.prompt`.
