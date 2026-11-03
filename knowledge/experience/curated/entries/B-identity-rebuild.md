<!-- meta {"id":"EX-B-identity-rebuild","title":"Bernini rebuilds a face from a long description of it","summary":"Detailed hair, age and glasses descriptions reconstructed different people on Bernini across several tasks, and heavy scene-wide rewrites did too. Keep identity wording short, favor a source that still shows the person, and check every person after each pass.","questions":["Why does the person look different after I described them in detail?","Which input recovers a lost face?","How do I keep several people recognizable?"],"renderers":["bernini"],"layer":"renderer","stages":["design","revise"],"evidence_ids":["EV-F002","EV-F003","EV-F005","EV-F006","EV-V5-train-cases"],"version":"1","review_reference":"docs/experience-rebuild-20261103.md"} -->
# EX-B-identity-rebuild: Bernini rebuilds a face from a long description of it

**On Bernini, a detailed facial description tends to produce a new face. Give identity one short clause, move the design effort to clothing, setting and light around the person, and inspect every person after each pass.** The general principle is [EX-P-identity](P-identity.md); this entry records how Bernini behaved.

## Bernini on record

- F002 and F005: explicit preservation plus enumerated hair and glasses did not recover the original identities, and one pass improved a pianist's resemblance while worsening a guest.
- F004 and F006 show recognizable identities surviving substantial conversion, so the loss is not inevitable. F006's single prominent subject kept a recognizable face through major scene changes.
- In the hotel-suite train task, a PE round with a long scene-wide rewrite regenerated both people with different faces and apparent ages (the judge capped correspondence), while a Planner round with the same room kept both recognizable ([v5 cases](../evidence/v5-train-cases.json)).
- In the Dune courtyard task (train sample 011, short prompt), the Direct result kept the woman in her source position but as a cut-out with hard edges over the new backdrop, and replaced the second figure with a different traveler; a PE first round kept both figures in their source places, dressed as desert travelers, and scored higher on all five dimensions. That PE round did not show a citadel (the judge noted the setting was carried by clothing and backdrop), so the comparison is about the people, not the architecture ([v5 cases](../evidence/v5-train-cases.json)).

## How to use it

Say who stays in one short clause. Describe the garment, what it covers and where the costume ends. Keep a scene's other transformations away from the head region when possible. In scenes with several people, review each one. If a face is lost, go back to a source or earlier candidate that still shows it ([EX-B-chain-drift](B-chain-drift.md)).

**Evidence.** F002, F003, F005, F006 and the train-sample hotel-suite and Dune cases. Scene density and head-region interaction are conditions to inspect, not isolated causes.
