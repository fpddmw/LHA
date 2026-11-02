# Turn the task into a visible design

For each `generate` action, use the original request and the viewed source and
selected-input frames to write a complete, concrete English rendering prompt.
Develop broad requests into a coherent visual direction; realize detailed requests
through their specified objects, attributes and relationships. Choose what to
preserve or transform according to the task.

Anchor the design in the actual scene: identify which subject or surface carries
each important change, where it appears, and how it relates to nearby elements.
Express the requested style through the relevant shapes, materials, colors,
lighting, spatial layers and action relationships. Choose details that work
together to create the intended appearance and event. Give the most consequential
changes the clearest wording.

Apply useful relationships from the knowledge and references you have read to
these concrete choices. A material's response to light can determine its surface
description and illumination; a staging principle can determine placement and
interaction. Use retained readings as you develop both the first prompt and later
revisions.

After generation, compare the Critic's findings or your own review with the
original task, selected input and submitted prompt. Decide which visual changes
address the important findings. Carry forward successful choices and integrate
the chosen changes into the next complete prompt, including dependent changes in
surroundings, light or action where relevant.

Write the intended result for the input you select, whether the source or a
retained candidate. Make the prompt self-contained, with the desired scene and
important changes stated directly. Keep it concise within the renderer's text
capacity: Bernini accepts 512 encoder tokens including its official prefix;
Ditto accepts 512 text-encoder tokens. Combine repeated descriptions and spend the
available text on distinctive visual relationships. Keep optional working notes
and source references in the task workspace; submit the rendering description in
`generate.prompt`.
