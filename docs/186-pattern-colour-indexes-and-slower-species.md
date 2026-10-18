# 186 Pattern and colour indexes, boosts, slower new species, hatch-screen audit (owner intake 2026-10-18)

Status: **SPEC, nothing built.** Per the feature-intake rule the owner's long message of 2026-10-18 was broken into tickets (BD-1032 to BD-1043 in [docs/07](07-kanban.md)) and ordered by priority. Numbers here are **PROPOSALS** (marked PROVISIONAL) until a simulation and a Studio check confirm them. Plain-language summary for the owner is at the end.

## 0. What the owner said (condensed)
1. Players do not know what a **pattern** is; there is no way to see which patterns exist. Make a **Pattern Index** that is easy to find, greyed out until the first dino with that pattern is found.
2. Patterns should be **more numerous and rarer in steps** (exponential), with rarity names (Common ... Mythic). A pattern gives a **boost**, so a Mythic-pattern Gold dino takes much longer than a Common-pattern Gold dino. That is wanted: players should **hope for certain patterns** while catching eggs.
3. Same for **colours**: a Colour Index, more colours, special ones (RGB-style, Chrome, others), rarity steps.
4. Early game = **hunting patterns and colours**, not new species, mutations or fusions. Getting the same Compy many times is fine if patterns and colours keep giving something to find.
5. Pattern and colour **boost the current dino**: it grows a bit faster and walks a bit faster. The index shows how much a pattern or colour is worth and how rare it is.
6. **New species must be rarer.** Rare dinos came too early (about 4 minutes). Target: roughly 5 to 6 Common, 5 to 6 Uncommon, 4 to 5 Rare species; the first Rare should take about **30 to 60 minutes**. In the first 3 minutes, 10 eggs giving 5 of the same Compy is fine.
7. QA must **click outside menus** (for example the hatch screen) and check what a player would expect.
8. **Hatch screen audit**: low-quality paint buckets (colour not shown), round pill name tags that match nothing else in the game, rarity tags, egg condition scale that changes when the egg gets a second colour, Rainbow and Astra effects that look bad (or old).
9. The **playtest build showed an old version** of the hatch screen. Always show the newest features together, with an on-screen proof of which build is running.

## 1. What exists today (read from the code on origin/main, 2026-10-18)
| Thing | Today | Source |
|---|---|---|
| Patterns | 8 ids, **all equally likely** (12.5%), no names for players, no rarity, no index. Decision of 2026-10-15 (docs/88): "patterns stay equally likely for now (fusion needs it). Revisit later." | `EggGenetics.luau` (`Genetics.Patterns`, `roll`) |
| Colours | 9 egg colours **already have rarity names** (Common to Mythic) and very uneven weights, but steps are not the 1/5 ladder and nothing in the UI lists them. Dinos carry primary + secondary colour + blend. | `ProgressionConfig.EggColors` |
| Species | 22 species in 5 tiers: Common 72%, Uncommon 24%, Rare 3.2%, Epic 0.7%, Legendary 0.1% per egg; run-size boost `{1,1.9,4.7,4.5,4}` only matters for big runs. | docs/82, `ProgressionConfig` |
| Index | The Dino Index shows species only. | `DinoIndexPanels.luau` |
| Fusion | Gold = 6 Base of the same species (any pattern); Gold keeps the most common donor pattern, ties go to the smallest pattern id. Emerald and Diamond need the same species and pattern. | docs/90 |
| Hatch screen | "Paint buckets" with a colour chip under each (swatch + name + tier badge), a pattern chip and a condition chip, all drawn as rounded dark pills. | `HatchSequence.luau`, `HatchEggV2.luau`, `HatchFx.luau` |
| Growth | `GrowthPerFood = 0.1`, **decided and unchanged** (handbook 8.5, owner Q1 2026-10-16). | docs/114 |

Time maths used below: a normal 5-minute run is about 15 eggs (docs/119), so **about 3 eggs a minute** while running (PROVISIONAL; BD-1043 measures it in Studio).

## 2. Why rare dinos come "too early" (the numbers)
Rare or better is 3.2 + 0.7 + 0.1 = **4.0% per egg**. At 3 eggs a minute the first Rare-or-better dino arrives after 25 eggs on average, about **8 minutes**, and the chance of one in the first 12 eggs (4 minutes) is **39%**. That matches what the owner saw.

## 3. Proposal A: species odds, slower (BD-1032)
LEAD decision (owner delegated 2026-10-16), PROVISIONAL: keep five tiers and the roster size (5 / 5 / 5 / 4 / 3 species, which already matches "5 to 6, 5 to 6, 4 to 5"), but move the base weights:

| Tier | Today per egg | Proposed per egg | Species in tier |
|---|---:|---:|---:|
| Common | 72% | **91.0%** | 5 |
| Uncommon | 24% | **8.5%** | 5 |
| Rare | 3.2% | **0.42%** | 5 |
| Epic | 0.7% | **0.07%** | 4 |
| Legendary | 0.1% | **0.01%** | 3 |

- Rare or better: **0.5% per egg**. Median wait for the first one: 139 eggs, about **46 minutes**. Chance in the first 12 eggs: 6%. Chance by 30 minutes (90 eggs): 36%.
- First **Uncommon**: median about 8 eggs (about 3 minutes), so the second kind of dino comes quickly and the player is still moving forward.
- Inside Common, make Compy about **40%** of the Common tier (today 36%) so repeats of the same Compy feel normal, then Raptor, then the rest.
- Run-size boost stays, but is capped so a normal run (about 15 eggs) is not lifted; a 120-egg run still lifts Rare and up about 2x (s = 0.3). The ladder rule of docs/88 (each step 4 to 6 times rarer) is **deliberately broken at the top by the owner's direction** (time-to-first-Rare goal wins); record in docs/116.
- Disclosed odds (`ShopOdds`, docs/85) and `tools/verify_rewards.py` change together; a new simulation prints "minutes to the first Uncommon / Rare / Epic / Legendary" so the owner can read the result without maths.
- Saved eggs already banked keep their committed species (docs/82 rule).

## 4. Proposal B: patterns become a real collection (BD-1033, BD-1034, BD-1035)
### Rarity (code only, ships first)
Give the **existing 8 patterns** a tier and unequal weights now (no new art needed), then add new patterns in batches. Shared six-tier ladder of docs/88 with r = 1/5: Common 80%, Uncommon 16%, Rare 3.2%, Epic 0.64%, Legendary 0.13%, Mythic 0.026% (about 1 in 3,900 eggs). Weight inside a tier is split evenly among its patterns.

**No fixed number of patterns (OWNER 2026-10-18: "not a hunt for big numbers like 24").** The goal is patterns that are *meaningfully different*: a player must see the difference between two of them on a small moving dino. The count is whatever survives the distinguishability test in BD-1034 (section 4a). The 8 existing patterns are the starting set; tiers are assigned to whatever set we end with (roughly more Commons than Epics, at least 1 Mythic only if it is truly distinct).

### 4a. How we find meaningful patterns (BD-1034, owner idea 2026-10-18)
1. Ask ChatGPT (image generation, allowed) for a **sheet of square, black-and-white, seamlessly tileable pattern tiles** (for example 4 x 4 tiles on one image, one flat shape idea per tile: dots, stripes, diamonds, stars, scales, camouflage blobs, swirls, checks, ...). Save the sheet in `docs/reference/` and list each tile in docs/77.
2. Each tile repeats, so a single square can cover the whole dino (tile scale and angle are the only knobs). Convert tiles to the same mask format the 8 existing patterns use (white = colour 2, black = colour 1).
3. **Distinguishability test:** put every tile on the same dino at the size a player really sees (the HUD dino, the index card, a dino across the cave), in two colour pairs. Score each tile: can a person tell it apart from every other tile, at that size? Also flag tiles that vanish on small dinos or look like noise. A tool (`tools/pattern_similarity.py`) prints a similarity table (downscale, compare) so near-duplicates are caught before the owner looks at them.
4. Keep only tiles that pass; the survivors become the pattern set. Report: how many we have, how many are really different, the contact sheet.


Art rule (AGENTS.md, 2026-10-14): **no code-drawn textures**. New pattern masks are Blender renders or the owner's ChatGPT images, one task and one docs/77 line each; the hatch preview, the 3D dino mask and the index card all use the same mask. Gate: `tools/verify_pattern_masks` style check that every id has a mask, a name, a tier and a boost.

### Names and kid copy
Every pattern needs a short friendly name ("Dots", "Stripes", "Diamond", "Freckles", "Stars"...). No ids in the UI. Copy follows docs/72 (short, obvious, no numbers like "1.25x"). Boost is shown as a plain line: "Grows a bit faster" with small star pips (one to five), not as a percent.

### Fusion fairness (BD-1040)
docs/90 already makes a Gold keep the most common donor pattern, so a Mythic-pattern Gold needs the Mythic pattern to be the plurality among six donors: **much harder, and wanted** by the owner. No change to the ladder (6 / 3 / 2). Add a simulation line in `tools/simulate_fusion_ladder.py`: "expected eggs to a Gold with pattern of tier T". Emerald and Diamond still need same species and pattern, so a rare pattern also makes the later tiers harder; the numbers go to the owner before anything is published.

## 5. Proposal C: colours (BD-1036, BD-1037)
- Keep the 9 colours; **retune weights to the same ladder** (they already carry tier names) and add ones so each tier has 2 to 4 colours: target **about 18 colours**.
- **OWNER 2026-10-18: start with normal colours.** Glow, Chrome, Pearl and RGB Shift are **low priority**. Reasons: (a) we have never made a good glowing or shiny surface (the Royal Nova aura and the gold fusion finish both took many tries); (b) a glow or chrome colour plus a **mutation's bold effect** on the same dino could clash or hide the mutation, and nobody has looked at that yet. Do not promise glowing colours. If they come back, first a small Studio test (BD-1046): one chrome colour and one glow colour on a dino that also has a Shiny / BIG / event mutation, look at the picture, decide.
- Specials below are kept only as **ideas for later** (PROVISIONAL names, check against the handbook finishes in 8.6 so none looks like the Gold / Emerald / Diamond tier finish):
  - **Chrome** (mirror silver, matte-friendly, Epic),
  - **Pearl** (soft white shimmer, Epic),
  - **Aurora / RGB Shift** (colour drifts slowly through the rainbow, **Mythic**). Name it "RGB Shift", **not** "Rainbow", because Rainbow is already an egg condition. It is a client-only slow tint animation, one timer for all dinos, cheap on phones.
  - Others on the table: **Glow** (soft inner light), **Sunset** (two-tone). Owner picks.
- A dino has a primary colour, a secondary colour and a blend. The **accent (secondary) colour boosts slightly MORE than the main (primary) colour** (OWNER 2026-10-18: "a crazy mythical accent colour is insane, a mythic base colour is less insane"). The colour rarity shown for a dino is the rarer of its two colours.
- Dinos already owned keep their stored colour ids; new colours are additive, nothing is rewritten in any profile.
- Art/effects: colour swatches and the Chrome / RGB Shift look need a Blender-rendered reference and a Studio check on phone budgets (`tools/qa/phone_budgets.json`).

## 6. Proposal D: the boost (BD-1038)
Points per tier (PROVISIONAL): Common 0, Uncommon 1, Rare 2, Epic 4, Legendary 6, Mythic 10.
`boostPoints = patternPoints + 0.7 * mainColourPoints + 1.0 * accentColourPoints` (PROVISIONAL weights; replaces the first draft 1.0 / 0.5 that favoured the main colour). A dino whose two colours are the same counts both. The totals are still capped (below).
- **Growth speed:** +1% per point (food gives 1.01x size growth per point), capped at **+15%**.
- **The caps are totals for one dino** (owner question answered 2026-10-18): all pattern and colour points of that dino together can never give more than +15% growth speed and +7% walk speed. No single pattern or colour has its own separate cap.
- **Walk speed:** +0.5% per point, capped at **+7%**.
- Applies to the dino the player is currently playing; a dino with a Mythic pattern and a Mythic colour is at the cap quickly, so there is nothing to farm beyond it.
- Server computes it from the stored genes (never trusts a client number); the value is part of the versioned trait formula so old profiles can be recomputed.
- **Conflicts with the handbook** (record as new rows in docs/116, owner direction of 2026-10-18 wins): "growth pacing is decided and unchanged" (handbook 8.5) becomes "base pacing unchanged, a small per-dino multiplier on top"; walk speed has fixed values per species in docs/101.
- Combat stays flag-off; the speed cap is small so a later PvP check is not blocked. Phone check before any claim.
- Not paid: patterns and colours come only from free eggs, never from Robux-linked sources. Free-egg odds disclosure stays correct (docs/43). Bought cosmetics never add boost points (docs/46).

## 7. Proposal E: the indexes (BD-1039, spec first)
Goal: easy to find, no clutter, nothing new on the HUD bar if possible.
- **Where:** the existing Index screen gets three tabs at the top, **Dinos | Patterns | Colours** (big, thumb-sized, icon plus word). No new HUD button. The tab bar remembers the last tab.
- **How it looks:** a grid of cards; found items are in colour with name, rarity border (same rarity colours as everywhere, `Theme.RarityColors`), boost pips and a small line "Found on: Compy, Raptor". Items not found yet are **grey silhouettes with a question mark and the rarity border colour dimmed** (so you can see how many remain and how rare, like the Dino Index). Top line: "Patterns 5 / 24".
- **Unlock rule:** a pattern or colour unlocks the first time a **hatched dino** carries it (not the egg picture). Dinos the player already owns count at first load of the new feature (backfill, no profile rewrite).
- **Moment:** the hatch reveal shows a small "New pattern!" or "New colour!" ribbon, and the Index button gets a small dot until the new item is seen.
- **Early-game goals** (BD-1041): the objectives system gets two or three starter goals ("Find 3 patterns", "Find 3 colours") so the first 10 minutes have a direction when no new species comes. Wording follows docs/72.
- Keep it phone-friendly (cards at least as big as the Dino Index cards, one screen scroll, no hover-only info).

## 8. QA and hatch-screen audit (BD-1042, BD-1043, BD-1045 and the existing close-path row)
- **Click outside / X / back on every screen** is already being fixed (agent working on the close paths). Add it to the player walkthrough checklist as a rule: for every popup, test X, tap outside, Esc / back button, the Open key pressed twice, and opening a second screen on top. Write the result of each as works or broken.
- **Hatch audit (BD-1042):** a table of every UI piece from "start hatch" to "dino shown": paint buckets (shape, material, colour fill, label), colour name tags, rarity tags, pattern chip, condition chip, condition overlay (cracks, dirt, stars, Rainbow, Astra), egg scale. For each: screenshot, does it match docs/114 section 4 (shapes, text and outline), docs/72 (kid copy) and docs/87 (calm, bubbly, matte)? The owner noted **round pill tags appear nowhere else in the game**; the code draws them as chunky rounded dark chips (`chipFrame`, `CornerRadius 1`); decide one chip style for the whole game. Owner also reported the **bucket colour is not shown** and the **condition scale jumps** when the egg gets its second colour; each gets a reproduction step and a fix row.
- **Stale playtest (BD-1043):** every playtest build shows a small build stamp (`BUILD redesign-020` plus short git id) and the playtest file is built only from a fresh `origin/main`. A tool (`tools/playtest_freshness.py`) compares the built file's stamp with `origin/main` and prints "up to date / N commits behind". Anything the owner sees in a window that is not the newest build is labelled "old" in the report. The owner glances at the stamp and knows what to expect.

## 9. Order of work (priority)
| Order | Ticket | Why now |
|---:|---|---|
| 1 | BD-1043 build stamp + freshness check | The owner is judging the game by what is on screen; the playtest is imminent. Small. |
| 2 | BD-1042 hatch screen audit | The hatch is the core payoff; includes real defects (bucket colour, scale jump). |
| 3 | BD-1032 slower new species + simulation | One config change; fixes "rares too early" before friends play. |
| 4 | BD-1033 pattern tiers on the existing 8 + disclosure | Code only; makes patterns matter at once. |
| 5 | BD-1036 colour ladder retune | Code only, same pattern as 4. |
| 6 | BD-1038 boost (server, caps, tests) | Needed before the index can show boost. |
| 7 | BD-1039 Pattern and Colour Index (spec, then build) | The owner's main wish; needs 4 to 6. |
| 8 | BD-1041 starter goals | Small; after the index exists. |
| 9 | BD-1034 pattern discovery (ChatGPT tile sheet + distinguishability test), BD-1037 plain new colours | Art-bound; run in parallel with the above. Specials (Chrome, Glow, RGB Shift) are low priority, BD-1046. |
| 10 | BD-1035 pattern rarity UI details, BD-1040 fusion simulation | After the data exists. |

Do not flip any release flag; the playtest profile gets the new features on, per the owner rule that test builds carry the newest built features.

## 10. Open questions for the owner (kept short, also on the dashboard)
ANSWERED by the owner 2026-10-18: (1) special colours are low priority, start with normal colours; (2) no fixed pattern count, find meaningful ones; (3) the caps are totals per dino (+15% growth, +7% walking), not per item. Still open: none.

## Plain summary
Patterns and colours become collections with an Index tab, rarity steps and a small boost to growth and speed. New dinos get slower to find (first Rare in about 45 minutes, not 8). The hatch screen gets a full audit, and the playtest shows which build it is.
