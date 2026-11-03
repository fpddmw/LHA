<!-- meta {"id":"EX-P-medium-logic","title":"Describe how the medium builds the picture, and light as part of it","summary":"Write the construction rules of the target medium (what makes a mark, a surface, a shadow) and what the light does to each plane. Style names and adjectives alone leave the renderer to guess, and lamps alone do not change the lighting.","questions":["How do I make a style read as that medium rather than a color filter?","Why did added lamps not change the atmosphere?","What should I write instead of a list of style adjectives?"],"renderers":["bernini","ditto"],"layer":"principle","stages":["design"],"evidence_ids":["EV-F002","EV-F004","EV-F005","EV-F007","EV-H-B-027__short__full_knowledge","EV-V5-LEGO-planes","EV-H-D-benchmark__001__short"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-P-medium-logic: Describe how the medium builds the picture, and light as part of it

**For the medium you were asked for, write the rules that make its image: what a mark, an edge, a surface and a shadow look like when this medium makes them. Then say what the light does to each plane. A style name sets a direction; construction rules and light behavior are what the renderer can follow.**

## Construction rules, not labels

The same request word means different things in different media, and a label such as "cel-animated" or "oil-painted" leaves the renderer free to apply a color grade. Say what the medium does:

- **Bricks and toys:** studs on top faces, visible seams between pieces, hard plastic highlights, hinge joints, a minifigure's C-shaped hands, shallow miniature depth of field.
- **Ink and wash:** line weight that varies, pale washes that bleed at the edges, bare paper as light, negative space for water and sky.
- **Cel animation:** a dark contour, flat fill with one shadow tone, painted backgrounds that are simpler than the characters.
- **Painted film worlds:** a construction of architecture, costume and light together, kept photographic if the request is live-action cinema.

Choose details from this source and this request, not from a catalog. A short compact construction usually beats a long list of adjectives. In the Bernini probe a few lines of pencil contour, wash, soft shadow and paper texture produced a clearly illustrated result where style words had not ([Bernini record](../../../model-experience/bernini-r.md)).

## Light is a plane too

Lamps, glowing accents and a color word do not by themselves change how a scene is lit. Say what the light falls on and what it does: warm sunlight grazing upper carvings, a cool fill in the shadows, light catching gold fragments, a perimeter that glows while the supports beneath it stay dark. In the table-tennis and palace cases, blue light appeared below the table or lamps appeared with the old lighting unchanged ([F004](../evidence/F004.json), [F005](../evidence/F005.json), [F007](../evidence/F007.json)). When faces are important, give them their own fill. A global warm cast can take over skin tones, and a later correction can intensify it ([historical Ditto palace](../evidence/H-D-benchmark__001__short.json)).

## How to apply it

1. Pick one visual system and write its construction rules for the planes you listed ([EX-P-every-plane](P-every-plane.md)).
2. Give lighting a clause for what it hits and what it does.
3. Keep medium rules consistent within the shot. Unrequested mixtures of two systems read as a design conflict.
4. If the first result already has the intended system, spend attention on the remaining gaps rather than on more style words.

**Evidence.** Bernini probe prompts and outcomes, F002, F004, F005, F007, Ditto palace and etching cases, and the brick-world case ([record](../evidence/v5-lego-planes.md)). The probe changed length and specificity together, so the effect of construction rules alone is not isolated.
