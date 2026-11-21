# 245 ChatGPT art-direction critique of the whole game (2026-11-21)

Owner 2026-11-21: "use chatgpt for critiques more angles about the game, show him our proposals or whats currently in game and what it could look like according to chatgpt and the popular game experiences we researched like PS99 and steal an egg."

**Method.** ChatGPT (owner's account, via Claude in Chrome) was asked to act as a strict art director and product critic for top kids' Roblox games. It got three current Studio captures: the island spawn plaza with PlazaShopsV2 (`docs/evidence/2026-11-16-plaza-shops-v2/after-spawn-view.jpg`), the in-run HUD (`docs/evidence/2026-11-21-ui-hud-v6/studio-1274x481-run.jpg`) and the menus in the top-game look (`docs/evidence/2026-11-17-menus-top-look/contact-sheet.jpg`). It compared them with Pet Simulator 99 and Steal a Brainrot.

What follows is our summary of its answer. **Every number is a proposed target to try in Studio, not a measurement of those games.** The HUD got its own rounds, in PR #632 (BD-1258, v4 5/10 -> v5 7/10).

## Scores (from screenshots only; juice can't be judged from stills)

| Area | Now | Target after polish |
| --- | ---: | ---: |
| World | 5.5 | 8 |
| HUD | 6.5 | 8.5 |
| Menus | 5 | 8 |
| Juice / feedback | 3.5 | 8.5 |
| Overall | 5.2 | 8.2 |

Its main point: "PS99 makes collecting visually satisfying. Steal a Brainrot makes progression and ownership immediately obvious." We have the foundation for both, but neither one stands out yet. Make the first 30 seconds unmistakably about eating, growing, finding eggs and getting bigger.

## Ranked problems and fixes

1. **The foreground at spawn and in a run is empty sand.** Cut the bare foreground about in half. Put a pickup, a planted group or a landmark every 8-12 studs along the main routes. Food 1.5-2x the size of small decor, in clean lanes, not hidden in foliage. Planned density: 0-12 studs mostly clear path with 2-4 cues; 12-25 food groups and one obvious goal; 25-50 shops and signs; beyond that, broad tree masses.
2. **Growth, the core mechanic, barely shows.** SIZE bar 40-48 % of the width, fill #7CFF36, highlight #D9FF9D, border #252119. Name the next milestone (SMALL -> MEDIUM). At each milestone: a scale pulse, a ground ring, a "GROWN!" call-out and a stronger sound.
3. **Spawn and run lighting look like two different games.** One daylight baseline for every outdoor zone: sand #FFE09A, grass #75DB4A, sky #79D9FF, late-morning sun. Weather may shift it and then returns to the baseline. Proposed Lighting starting values: ClockTime 12.5, Brightness 2.0, ExposureCompensation 0.05, ShadowSoftness 0.4, EnvironmentDiffuseScale 0.55, EnvironmentSpecularScale 0.15, Atmosphere Density 0.16 / Haze 0.4 / Glare 0.05 / Color #D5F5FF, ColorCorrection Saturation 0.08 / Contrast 0.06 / Brightness 0.01, Bloom Intensity 0.08 / Size 12.
4. **Menus are dense in structure but empty in feeling.** Shop landing: four cards fill about 92 % of the width (no big empty studded area). Eggs: the ready egg 2-2.5x bigger, on a nest, with odds and the next action. Home: the dino preview fills 65-75 % of the panel height.
5. **The player dino reads as a flat green shape from behind.** Head about 10-15 % bigger, lighter face/belly #B3EF8C, body #38BF48, darker back #218D36. Idle head and tail motion, an eating reaction.
6. **The Dino Index hides its selling point.** Silhouettes 70-78 % of the tile; an undiscovered one stays readable (not near-black on dark grey); rarity border and badge; full-colour previews once found; a big detail area (about 30 % of the width) or a pop-out; "Found 1/22" as a 5-6 % h progress strip.
7. **Button importance is inconsistent.** Primary action green #69F345 -> #31C934, 2-3 px black border at 481 px, important buttons 7-9 % h, white FredokaOne with a black outline. Vivid green only for what can be done now; locked items muted.
8. **No dominant spawn landmark.** A centrepiece 2-3x the height of the shop huts: a giant cracked hatchery egg on a round pad with a yellow rim #FFD34D, a big objective label and a short progress bar.
9. **Run Complete undersells the payout.** The reward takes 50-60 % of the window: eggs enter one after another, crystals count up, header white/gold #FFF6D6 / #FFD138, then a clear next step (HATCH EGGS).
10. **Too much space goes to secondary information.** Priority: current action and growth > collectibles and rewards > progression and events > shops > test info (hidden in release).

## Menus, screen by screen (its scores)

| Screen | Score | Fix in one line |
| --- | ---: | --- |
| Crystal Shop landing | 5.5 | Cards fill the width, the whole card is tappable, each card looks different |
| Potion Shop | 4.5 | Bigger potion art (9-11 % h), one line "GROWTH · 5 MIN" (kid words), price button 8 % h |
| Aura Shop | 6 | Aura preview twice the size, on the player's dino, one rarity badge |
| Dino Index | 4.5 | See problem 6 |
| Fusion | 5 | Slots about 40 % of the width, big result silhouette 25-30 %, "2 / 6 DINOS" |
| Eggs | 4 | The ready egg huge and alive; empty nests quieter than the egg |
| Home / Go home | 5 | Dino at 65 % of the window height; "eggs saved" big; a big green GO HOME |
| Run Complete | 3.5 | See problem 9 |

Shared menu frame (proposed): window 70-85 % wide and 68-78 % tall, header 7-9 % h, title 4-5 % h, card gap 1.5-2 % h, outer stroke 3 px #24202A, primary button 8-10 % h, close button 7-8 % h, dim behind 30-40 %, pattern at 5-8 % contrast. Take Steal a Brainrot's chunky frames and PS99's cleaner content.

Rarity colours used everywhere (proposed): Common #E9E8DF, Uncommon #68DF4A, Rare #4ACFFF, Epic #A96BFF, Legendary #FFD247. It says to use only the tiers the game really has.

## Juice to add (each action gets its own visible answer)

| Event | Feedback |
| --- | --- |
| Eat food | Food pops; "+5 SIZE" floats for 0.6-0.8 s; 4-8 particles; short chomp |
| Growth milestone | 0.5 s scale pulse, ground ring, "GROWN!", bigger sound |
| Crystal pickup | Crystal flies to the counter, number counts up, soft chime |
| Egg found | Egg rises and spins, gold stars, big "EGG FOUND!" |
| Rare egg | Flash in the rarity colour, stronger sound |
| Hatch | Shake, cracks, burst, reveal with name and rarity ribbon |
| Fusion | Six slots fly into the centre, glow burst, big reveal |
| Potion | Coloured pulse round the dino, HUD timer appears (done in #632 v7) |
| Run complete | Rewards enter one by one, currency counts, button last |
| New Index find | Silhouette turns into the 3D art, progress ticks, "NEW!" |

Reduce Motion stays respected for the big camera effects and particles. The sound families it proposes: pops for food, bells for eggs, deeper hits for growth, short fanfares for legendary hatches.

## Order it would give the team

1. Spawn focal point and foreground.
2. One world lighting and palette baseline.
3. Eating and growth made rewarding.
4. Eggs, Dino Index and Run Complete redesigned.
5. Shared menu type, spacing and button hierarchy.
6. Boost timers and consistent reward feedback (timers done in #632 v7).

## Board

Rows BD-1281..BD-1286 (Backlog, look/feel work; each is shown to the owner as one small slice first, per the owner rule of 2026-11-18). Every look that copies a reference goes through `tools/ref_compare.py` and a ChatGPT critique round before the owner sees it (memory rule, 2026-11-21).
