# 249 Dino model ranking and style anchors (2026-11-22, BD-1291 step 1)

BD-1291 step 1: rank every species by quality against the house style, so the owner can pick which models get upgraded. Input: the 31 portraits in one consistent Studio capture (`docs/evidence/2026-11-22-dino-ranking/all-v2-sheet.jpg`, same light, camera and outline).

**Method.** ChatGPT (owner's account, via Claude in Chrome) as a strict 3D character art director for top Roblox pet games, text only. What follows is our summary of its answer. Scores are visual judgments from one capture, **not mesh or texture measurements**; every number is a proposed target, to be checked in Blender and Studio.

## Scores (each 1-10: A cohesion, B face, C silhouette at 64 px, D texture cleanliness; total of 40)

Set overall: **6.9 / 10**.

| Species | A | B | C | D | Total | Biggest problem |
| --- | --: | --: | --: | --: | --: | --- |
| T-Rex | 9 | 9 | 9 | 9 | 36 | (anchor) eye highlight could be brighter |
| Stegosaurus | 9 | 9 | 9 | 9 | 36 | (anchor) spikes crowd the head a little |
| Plesiosaurus | 9 | 9 | 9 | 9 | 36 | (anchor) body close to the T-Rex |
| Duck | 8 | 9 | 9 | 9 | 35 | very soft body |
| Penguin | 8 | 9 | 9 | 9 | 35 | smoother than the faceted dinos |
| Triceratops | 9 | 7 | 9 | 9 | 34 | tiny eyes under a big frill |
| Pteranodon | 8 | 8 | 9 | 9 | 34 | eye could be bigger |
| Pigeon | 8 | 8 | 9 | 9 | 34 | small eyes at 64 px |
| Spinosaurus | 8 | 8 | 9 | 8 | 33 | sail competes with the head |
| Archaeopteryx | 7 | 7 | 9 | 9 | 32 | small eyes |
| Parasaurolophus | 8 | 7 | 9 | 8 | 32 | crest competes with the face |
| Ankylosaurus | 8 | 7 | 9 | 7 | 31 | uneven tan patches |
| Quetzalcoatlus | 7 | 7 | 8 | 9 | 31 | thin neck, dark wings |
| Chickosaurus | 7 | 7 | 9 | 8 | 31 | weak eye detail |
| Cockatoosaurus | 7 | 7 | 9 | 8 | 31 | small eye, big crest |
| Foxosaurus | 7 | 6 | 9 | 8 | 30 | narrow, unfriendly eyes |
| Raptor | 7 | 5 | 9 | 8 | 29 | square black eyes |
| Ichthyosaurus | 6 | 7 | 7 | 9 | 29 | reads as a land crocodile |
| Mosasaurus | 7 | 6 | 8 | 8 | 29 | long snout |
| Dodo | 7 | 6 | 9 | 7 | 29 | recessed eye, big beak |
| Microraptor | 6 | 5 | 8 | 9 | 28 | face vanishes at thumbnail size |
| Pachycephalosaurus | 7 | 7 | 8 | 6 | 28 | muddy olive patches |
| Eaglesaurus | 6 | 5 | 9 | 7 | 27 | aggressive beak and eyes |
| Baryonyx | 5 | 5 | 7 | 8 | 25 | box head, square eyes |
| Brachiosaurus | 7 | 7 | 9 | 2 | 25 | dark purple smears on head and back |
| Compy | 5 | 4 | 7 | 8 | 24 | small head, generic body, blank eyes |
| Dimorphodon | 6 | 6 | 8 | 3 | 23 | dark blotches on the head |
| Therizinosaurus | 5 | 5 | 7 | 6 | 23 | dark muddy head, weak eyes |
| Gallimimus | 5 | 4 | 6 | 6 | 21 | tiny head on a long neck |
| Budgiesaurus | 4 | 3 | 8 | 4 | 19 | broken face markings |
| Elasmosaurus | 5 | 4 | 5 | 4 | 18 | dirty face, tiny head, long neck |

## Proposed upgrade list (owner picks the cut)

Order proposed: **Compy first** (main starter, owner: "the main compy one I don't like that much"), then Elasmosaurus, Budgiesaurus, Gallimimus. Brachiosaurus and Dimorphodon are **repaints only** (quick wins, shape is fine). Then Therizinosaurus, Baryonyx.

| Species | Proposed fix |
| --- | --- |
| Compy | redesign: head +30 %, neck -20 %, torso -10 %, eyes 20 % of head height with highlight, legs +15 %, lime #72D85F + cream #F5EDD8 (apart from the T-Rex teal) |
| Elasmosaurus | head +30 %, neck -25 %, legs +20 %, clean round eye (19 %), teal #39C9AE, cream #F5EFD9 |
| Budgiesaurus | remove the broken face decals, body #62D94D, wings #3159B4, one cheek #F4A63A, round eye 18 % |
| Gallimimus | head +30 %, neck -20 %, torso +12 % wide, one simple mouth line, #E79783 / #F5EDD9 |
| Dimorphodon | repaint the dark cap/shoulder blotches: #895CE8, wings #6943C6; head +10 %, eye 18 % |
| Therizinosaurus | head +25 %, neck -12 %, eye forward and 19 %, tan #B88C62, cream #F3E8CE |
| Brachiosaurus | repaint the dark head/back stains: #8D71E7, #7354CC, cream #F3EBDD; neck -10 %, eye 18 % |
| Baryonyx | muzzle -15 %, upper head +20 % wide, rounded muzzle, round eye 18 %, #65BD50 / #F1EBD5 |

Texture check first (may be UV/texture faults, not paint): Dimorphodon, Brachiosaurus, Elasmosaurus, Budgiesaurus. Visual-only: Therizinosaurus, Gallimimus, Pachycephalosaurus, Dodo.

## Style anchor rules (from T-Rex, Stegosaurus, Plesiosaurus)

Proposed targets for every new or upgraded model:

1. Head 40-55 % of total height for compact bipeds; quadrupeds head length 30-45 % of torso length (long necks may differ).
2. Eyes round, near-black #10151A, 18-24 % of head height, one white highlight of 10-18 % of the eye.
3. At most 3 main colour areas: main, second, cream. Main colour saturation about 55-85 %.
4. Cream belly from chin to stomach, about 20-35 % of the visible front.
5. Short sturdy legs, about 18-30 % of height for compact ground species; no thin joints.
6. Large readable planes, about 6-12 main facets per head; no random small bumps.
7. Clean colour areas: no unexplained dark mottling, no colour bleeding round the eyes, no broken UV islands.

## Next

- Owner picks which species get upgraded (Design Board).
- **Compy pose sheet v1** (BD-1291 step 2, ChatGPT image, same chat as the ranking): `docs/evidence/2026-11-22-dino-ranking/compy-sheet-v1.jpg`. Front, 3/4, side, back plus happy idle, run, jump; lime with cream belly, big glossy eyes, chunky faceted toy look like the anchors. Lead check: in the set's style and clearly not the T-Rex teal; the head is still T-Rex-like (blocky snout), a slimmer Compy snout is the one thing to ask for in v2 if the owner wants it. **Waits for the owner's OK** before any Blender rebuild (final art = Blender or owner, never code-built).
- No GPU or Blender work in this step.
