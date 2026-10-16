# Mutation QA 2026-10-16 (BD-154/155)
Seeded temp copy of the playtest build (scratchpad only, not committed), own Studio window, 765x784 viewport. Seeded: 7 mutated eggs (one per mutation), 7 mutated dinos, Gold/Emerald/Diamond stacks, all auras/trails.

Ratings out of 10 against docs/87 (colourful but calm, readable at 64 px):
| Surface | Score | Note |
| --- | ---: | --- |
| Eggs card badge + glow (Dewdrop only seen) | 7 | clear badge, soft mint glow; other 6 not seen (screen shows only the next egg) |
| Hatch reveal ribbon + effects | 7 | ribbon readable, colours calm; Ember/Blood Moon/Charged mist hides the body (BD-348) |
| Index / species page / My dinos | 5 | tint on previews good; text only 9 px, one purple chip (chip colour fixed) (BD-349) |
| World dino cue | 4 | tint subtle; mist/ring thin; was lite-only before fix (BD-350) |
| Run toast | 8 | "Ember egg caught!" visible; overlaps the SIZE bar slightly |
| Performance | 7 | desktop budget alive<=45 per dino; 12 stacked rigs: no measurable frame-time change (66.6 vs 66.7 ms; Studio window is capped near 15 fps so this is below noise); no phone test |

Not done: Gold + mutation in the world (the rules give no tint to fusion tiers anyway), a real catch of a mutated egg (tag written by hand), phone device.
