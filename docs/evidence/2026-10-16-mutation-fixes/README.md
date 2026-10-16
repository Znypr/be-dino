# Mutation fixes 2026-10-16 (BD-236, BD-351, BD-352, BD-353)
Seeded temp copy of the playtest build (scratchpad only, not committed), own Studio window. Before images are the 2026-10-16-mutation-qa captures; after images are cropped Studio views of this branch. Same seed: 7 mutated eggs/dinos, Ember Stegosaurus equipped.

| Surface | Before | After | Score after |
| --- | --- | --- | ---: |
| Hatch reveal (Ember, Blood Moon, Charged) | smoke clumps covered the body | smoke is behind the dino, 40% size, 50% alpha, colour glow kept; dino body fully readable | 8 |
| Drag to turn pill | over the head | left of the dino, off the head | 8 |
| Index card / My dinos / species page | 9 px text pill, one colour | 14 px chip in the mutation's own colour with a dot (no new art; no matching icon plate exists) | 8 |
| World cue at ~19 studs | thin ring, lite look only | wider brighter ground ring + slow motes, kept even when an aura/trail is equipped; Reduce Motion = still ring | 6 (visible, calm; motes small) |

Not verified in Studio: Reduce Motion ring (offline test only), 12 dinos on screen (particle-count test only), phone, Sanctuary modal preview (still shows no mutation, BD-352 leftover).
