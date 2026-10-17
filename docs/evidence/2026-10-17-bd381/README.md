# BD-381 evidence (Studio, playtest build of this branch, one local player)

All images are Studio `screen_capture` frames. A probe ViewportFrame was made with the real `DinosaurPreview.add` on the HOME/Welcome
screen (the same call every dino card uses). It is the grey square at the top left; the welcome card behind it is unchanged.

| File | What it shows |
| --- | --- |
| `before-viewport-legacy-after-template-arrived.jpg` | BEFORE the fix (origin/main): the Compy template was missing when the card was built (the server loads the 22 low-poly models one by one, about 25 s). The card took the legacy rounded model and still showed it 3 s after the template arrived. |
| `reference-lowpoly-viewport.jpg` | A card built after all templates are loaded: the low-poly Compy (what every card should show). |
| `after-viewport-lowpoly-built-while-pending.jpg` | AFTER the fix: the card was built while the Compy template was missing (flat picture, no legacy model), the template arrived, the card rebuilt itself as the low-poly Compy 1.5 s later. |

Read-backs (same session): loader attribute `LowPolyDinosLoaded` = 22; pending card: world model absent, flat picture present; after arrival: `LowPoly=true`,
flat picture gone; loader finished but template really missing (Raptor removed): legacy fallback shown (allowed); local character mesh `LowPoly=true`.
Not captured: the Fusion list and the pad as images (the same `DinosaurPreview` / `ResourceVisuals` paths; the pad self-heals and was checked by attribute read-back).
