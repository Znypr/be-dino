# Hatch v2 (BD-397) Studio evidence, 2026-10-16

Own temp copy of the playtest build (`python tools/build.py --profile playtest`, then `Config.HatchV2 = true` patched into the copy in my scratchpad only, never committed), the owner's Studio on the owner's PC, Play Solo, one local player (admin). Eggs were earned by a real run (a client loop of `Humanoid:MoveTo` to the nearest food until 3 catches, then `RequestEndRun`); nothing was granted. Captures: `PrintWindow` of my own Studio window every 250-300 ms (two other agents' Studios were open and were not touched). Each still is the 824 x 402 hatch panel region at window scale. Judged by the agent's eye only; owner eye check pending. Not verified: phone hardware, published place (asset ownership and "Allow Mesh & Image APIs"), multiplayer, sound (agents cannot listen; no new cues were added).

Absolute folder: `C:\Users\znypr\Documents\be-dino\docs\evidence\2026-10-16-hatch-v2\` (on the branch worktree while in review).

## Pass 1 (first build): Green / Horizontal Bands, Normal egg
`pass1-contact-sheet.jpg` = 40 frames at 300 ms; `pass1-NN.jpg` = single frames.

| Frame | Beat | What it shows |
|---|---|---|
| 04 | settle | the 3D generated egg (own cream texture) on the dark stage, condition chip hidden (Normal) |
| 06 | bucket 1 arrives | PLACEHOLDER barrel hovering left, over its chip spot |
| 07 | impact 1 | chip "Green - UNCOMMON" pops; the green splat blooms on the egg's upper-left flank with the crown puffs |
| 08 | coat 1 floods | about half the egg green, soft wet edge toward the right flank |
| 09 | coat 1 done | the whole egg green, squash settled |
| 10, 12 | bucket 2 | barrel on the right tipping; the liquid arc reads as a thin dotted line (fixed in pass 2) |
| 13 | impact 2 | cream splash, "Cream - COMMON" chip; 2D drip streaks under the splash |
| 14 | coat 2 | cream bands painted onto the green egg; "Horizontal Bands" chip |
| 16, 19 | rattle | glow rings grow, the egg rattles (no crack lines: needs the crack decal, docs/118 s4 D) |
| 21 | burst | the egg leaves, v1 shell fragments and sparkles |
| 22, 24 | reveal | Gallimimus, name, odds, detail line, tap hint: unchanged v1 |

Defects found in pass 1 and fixed before pass 2: the tipping bucket swung above the panel edge (hover height .8 -> .45 studs); the liquid arc was a dotted line (blob size 2.4x -> 3.4x, radius 13 -> 15 px).

## Pass 2 (hover and arc fixes): Cream / Emerald Islands, Rainbow egg
`pass2-contact-sheet.jpg` = 46 frames at 250 ms; `pass2-NN.jpg` = single frames.

| Frame | Beat | What it shows |
|---|---|---|
| 06 | first frame | DEFECT: the egg is black for one frame (the EditableImage had no write yet). Fixed for pass 3: a flat write at create() |
| 07, 09 | bucket 1 | barrel at the right height now (no clipping), hovering over the "Cream - COMMON" chip |
| 10, 11 | impact 1 | cream crown; the coat is invisible on the cream shell (Cream gene on a cream egg). Fixed for pass 3: the bare shell is a neutral pale grey-white |
| 12 | drips | 2D drip streaks under the left splash |
| 15, 16 | bucket 2 pours | the thick GREEN liquid arc from the lip to the egg, crown droplets, "Green - UNCOMMON" chip |
| 17, 18, 19 | coat 2 paints the pattern | green emerald islands spreading over the egg from the right flank with wet edges, drips; "Emerald Islands" chip; the "Rainbow" condition chip below |
| 21 | condition + dry | the Rainbow star overlay fades in on the egg (faint at this size), gloss dried |
| 24 | rattle / glow | rings and glow behind the painted egg |
| 26, 27 | burst | fragments, flash |
| 30 | reveal | Raptor |

Numbers (passes 2-4, Play Solo client, this PC with two or three Studios open): bake 256 px = 256 KiB (one image per panel), source read once (egg texture 1024 px + egg mesh), no `[Be Dino] hatch v2` warning in the client log (bake path, not a fallback), 15 fps during the reveal (three Studio instances on one PC: not representative; pass 1 of the v1 look measured the same in docs/113), client memory 3,435 MB total (Studio session).

## Pass 3 (black-frame and neutral-shell fixes, final code of this PR): Blue / Blue (same family) / Wavy Stripes, Dirty egg
`pass3-contact-sheet.jpg` = 46 frames at 250 ms; `pass3-NN.jpg` = single frames.

| Frame | Beat | What it shows |
|---|---|---|
| 06 | first frame | the bare pale shell from the first frame (no black frame any more); "Dirty" chip |
| 07, 08 | bucket 1 | barrel arrives from the left with its overshoot, tips |
| 09, 10 | impact 1 | "Blue - COMMON" chip, blue crown, blue flood from the upper-left flank; drip streak under the splash |
| 11 | coat 1 | the whole egg blue, wet edge gone, gloss drying |
| 13, 14 | bucket 2 | right barrel tips, the blue arc flows to the egg |
| 15, 16 | impact 2 | crown, chip (same-family genes: the accent is the darker blue) |
| 17, 18, 19 | coat 2 | darker wavy stripes painted over the blue, "Wavy Stripes" chip |
| 21, 22 | condition | the Dirty smudge overlay fades in on the painted egg (brown marks) |
| 24 | rattle + glow | |
| 26, 27 | burst | fragments and reveal (Raptor) |

## Pass 4 (same code, next egg): Blue / Cream / Freckles, Normal egg
`pass4-contact-sheet.jpg` = 24 frames at 250 ms; `pass4-NN.jpg`. The tap meant to fast-forward landed during the pending hold (taps are ignored until the server answer arrives, by design), so the egg played in full: 02-03 "Tap for next egg", 05-08 bucket 1 and the blue flood, 12-15 bucket 2 with the cream arc and the cream freckles painted dot by dot, 17-21 freckles done, glow, 23 burst. Fast-forward and Skip all are covered by the pure tests (`tools/verify_hatch_v2.py`, `verify_hatch_sequence.py`), not by a still.

## Honest rating against docs/87 (agent's eye, out of 10)

**6 / 10 as built, with the placeholder barrel and smoke-cell paint.** What already works and fits "calm, bubbly, a little magical": a real 3D egg that squashes on impact, a bucket that flies in with a soft overshoot and tips, a visible liquid arc, paint that spreads over the egg's own texture from the impact with a wet edge and drips, the pattern visibly painted by the second coat, chips in the game style, calm timing (6.7 s build-up, skippable), the unchanged warm v1 reveal. What holds the rating down: (1) the bucket is a barrel (reads as a barrel, not a paint bucket) until the generated bucket mesh exists; (2) the arc, crown and puddle are the fx3 smoke cells tinted, so the "thick glossy paint" reads as soft blobs rather than liquid (needs the paint FX sheets, docs/118 s4 C); (3) the 2D drips are plain gradient streaks; (4) no crack lines on the 3D egg during the rattle (needs the crack decal); (5) the wet gloss (reflectance 0.28) is barely visible in the viewport light; (6) the Rainbow/Astra overlay is faint on the painted egg. With the owner's bucket mesh and paint sheets bound (table edits only, no new code) I expect 8 / 10; the remaining gap is a crack decal and a proper paint-sheen decal.

## What still needs owner-made assets
1. Paint bucket mesh (generate_mesh prompt in docs/118 s4 B) -> `HatchV2Assets.bucket`.
2. Paint splash crown, drips and droplet flipbooks + wet-sheen decal (ChatGPT prompts in docs/118 s4 C) -> `EffectAssets.Requested`.
3. Crack lines decal, three stages (docs/118 s4 D).
4. Optional: a cuter egg mesh (s4 A; the reused generated egg is acceptable).
