# 240 Cohesion: style tile and matrix (BD-1206), 2026-11-15

Owner 2026-11-15: "so many things looks vibe coded and it doesn't look like a single cohesive game", then "extend it more so every angle of the video game is covered and checked for cohesiveness".

Root cause: screens were fixed one by one (BD-1189 rollout, polish loop runs 1-8) with no single rule set for the whole game; the loop scored screens, not the game. Fix: one style tile (the rules), mockups of every surface in it, and a matrix that checks every surface against every rule and is redrawn after each change.

Status: **proposal for owner approval.** Nothing in the game has changed because of this page yet.

## 1. The rules (style tile v1, `docs/evidence/2026-11-15-hatch-now/style-tile-v1.jpg`)

| Id | Rule |
| --- | --- |
| R1 | Surfaces are cream panels / plates / chips with an ink outline; no dark navy or slate plates, boxes or loading screens |
| R2 | Two text kinds only: dark ink on cream, white with an outline on colour or the world; never text on studs |
| R3 | One green main button per screen, every other button grey, red only for the X |
| R4 | Rarity colours only on rarity things (cards, rarity words, hatch rays) |
| R5 | Real art only: no code-drawn icons, stand-ins or empty boxes |
| R6 | One font and the 28 / 20 / 16 / 14 scale; kid copy (no "36.4000%", no "5m 0s") |
| R7 | Windows: stud frame, glossy header in the place colour, X inside the strip; the hatch is a full stage, not a window |
| R8 | Everything sits inside its screen or window; nothing clipped, floating outside or overlapping |

## 2. Mockups (every surface in the one look)

- v2 (`docs/evidence/2026-11-15-hatch-now/style-tile-v2.jpg`): HUD in the world, hatch egg / Common / Legendary, batch summary, run end, toast + confirm popup.
- v3 (`docs/evidence/2026-11-15-cohesion/style-tile-v3.jpg`): loading, welcome, home (Sanctuary), egg chances in kid words, food guide with the real food art, weather title card, world labels (pickups, names, health, warnings), daily gifts + goals (planned BD-1197), gentle defeat.
- Numbers in the mockups are examples, not balance. Generators: `tools/style_tile_mock.py` (v2), the v3 boards extend it.

## 3. The matrix (`docs/polish/cohesion.json`, rendered by `python tools/cohesion_matrix.py`)

Picture: `docs/evidence/2026-11-15-cohesion/cohesion-matrix.jpg`; table: `cohesion-matrix.md` next to it. Current pictures of each surface: `docs/evidence/2026-11-15-cohesion/current/` (Studio, playtest build, 2026-11-15).

Today: **6 surfaces pass, 13 fail, 11 not checked** (30 surfaces: start, play, home, shop, menus, hatch, run end, world, feel).
- Pass: Eggs, Dino Index list, Dino detail, Crystal Shop, Potion Shop, Settings (the screens rebuilt on docs/232; shop and potions in PR #591).
- Fail: loading, HUD, welcome, home, egg chances, Fusion (one bar), food guide, the three hatch moments, run complete, weather card, toasts / rare banner.
- Not checked: hatch batch end, confirm popups, nests, defeat, phone layout, 3D dinos, world props, food models, sound, motion.

## 4. Order (after owner approval)

1. Hatch as a full stage (BD-1179) with the batch summary and Play again (BD-1199) in it.
2. HUD plates and world labels.
3. Run complete, home, welcome, loading.
4. Egg chances, food guide, weather card, toasts / banners, popups.
5. Capture and judge the "not checked" rows (nests, defeat, phone, 3D, sound, motion).

Progress 2026-11-16: steps 1-3 merged (hatch stage, HUD BD-1213, screens BD-1214); step 4 and the UI fixes of step 5 in BD-1237 (`MenusCohesionEnabled`, pictures `docs/evidence/2026-11-16-menus-style/`, matrix there: 20 pass, 4 fail, 6 not checked). Every row that is not a pass has a board row: hatch rows BD-1211, props BD-206 / BD-1239, defeat BD-1240, phone BD-1241, sound and motion BD-1242, 3D re-captures BD-1243.

## 5. In the loop (docs/234)

Every polish run re-renders the matrix; a change that turns a surface red does not merge. The target is every row green. The per-screen score stays, but the matrix is the whole-game check.
