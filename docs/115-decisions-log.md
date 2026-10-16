# 115 Owner decisions log, 2026-10-15 and 2026-10-16

Extracted from the kanban owner log, AGENTS.md, docs and the lead sessions. "LEAD DECISION (owner may overrule)" = made on the owner's behalf. Handbook: [114](114-handbook.md). Open conflicts: [116](116-handbook-conflicts.md). History is kept; superseded items are struck through in their own docs.

## 2026-10-15 (owner)
| # | Decision | Source |
|---|---|---|
| D1 | Feel: calm, bubbly, friendly, a little magical; five pillars; quiet soft sounds | [87](87-vision-and-feel-guide.md) |
| D2 | Catch rate 4 eggs per 500 food (supersedes 40/500) | [89](89-catch-rate-4.md), BD-165 |
| D3 | Rarity exponential everywhere, r = 1/5, six-tier ladder; patterns stay equal | [88](88-exponential-rarity.md), BD-184 |
| D4 | Fusion ladder 6 Base (any pattern) / 3 Gold / 2 Emerald (supersedes 15/4/2) | [90](90-fusion-ladder-v2.md), BD-200 |
| D5 | Growth halved; nests 6-12 eggs so nests out-produce runs | [90](90-fusion-ladder-v2.md) |
| D6 | Dinos have no condition; conditions are egg-only | BD-181 |
| D7 | Dino Index remembers original egg | BD-175 |
| D8 | World model quality reset: no code-built models; generated meshes | BD-206 |
| D9 | Special foods (steak, drumstick, golden egg) | BD-207 |
| D10 | Weather v3 stronger, more colour, smoke and mist limiting view distance; soft visibility, no sudden cut-off | [84](84-weather-events-v2.md), BD-213 |
| D11 | Project needs a proper name (open) | BD-182 |
| D12 | Monetisation ideas parked, not high priority | [86](86-monetization-ideas.md), BD-160 |
| D13 | Anime-inspired but gentle FX | [93](93-anime-fx-direction.md) |

## 2026-10-16 (owner)
| # | Decision | Source |
|---|---|---|
| D14 | Base look for all dinos is low-poly faceted (generated mesh, split in parts). Skins: Plushy, Clay, Bricks (Robux later), animated/anime unlockable | [97](97-dino-skins.md) |
| D15 | Generated meshes only for final 3D art | kanban owner log |
| D16 | Four classes Ground / Fly / Water / Armored; roster 5 Fly + 5 Water + 5 more Ground | [101](101-hp-combat-classes-animations.md), BD-232 |
| D17 | HP combat replaces instant bigger-eats-smaller; hearts only, Peaceful option, no revive v1 | BD-230 |
| D18 | Cave hub: big cave with physical shops; flag off | [104](104-cave-hub-design.md) |
| D19 | Growth 5x slower again (GrowthPerFood 0.1); more and better food; low-poly limbs must not shift eyes; lobby dino uses low-poly; text readable (light fill, dark stroke) | BD-386..390 |
| D20 | Hatching redesign: real bucket and paint-splash reveal, no primitive shapes, assigned to Fable | BD-397 |
| D21 | Egg view shows hatched dino colour/pattern; aura/trail shops say which dino; conditions shop uses the Blender stage; trees must not be sunk; glow guide must be visible | BD-392..396 |
| D22 | **Fast travel is a CRYSTAL SHOP PERK** (bought with crystals, not Robux). Walking default. Additive profile field, default off, Settings toggle visible only after purchase, glow guide stays the free alternative, price PROVISIONAL. SUPERSEDES the lead choice "teleport free by default" (docs/104 15.1 item 4 and 16 item 4, now struck through) | owner answer 2026-10-16; BD-391 |
| D23 | **First two eggs safe: KEEP.** Cracked 50% applies from the third egg on | owner answer 2026-10-16; `SafeEggs = 2`, BD-365 |
| D24 | **Currency crystals are AMBER/YELLOW everywhere.** Shop crystal meshes must be regenerated amber; blue-purple crystals are cave decoration only, never in a shop or currency context | owner answer 2026-10-16; BD-400, BD-401 |
| D25 | **Cave lighting:** the inside is DIM (lamp-lit); weather never affects the inside; 3D assets must look real and grounded in the cave lighting; no overlapping assets; assets must be grounded (trees were sunk into the floor) | owner statement 2026-10-16; BD-395, BD-398, BD-399 |
| D26 | Handbook: one reference to fact-check against, owner only steers | this PR |

## LEAD DECISIONS (owner may overrule)
| # | Decision | Source |
|---|---|---|
| L1 | Species tiers and PROVISIONAL weights; five species tiers | [82](82-species-rarity-tiers.md) |
| L2 | Ladder is 6/3/2 in the Fusion Menu; 15/4/2 and 50/10/3 historical | BD-335 |
| L3 | Cave 260 x 220; rail dims DINOS/EGGS/FUSION/SHOP in a run; Settings stays a plain HUD button; lava scenic; keep 2D hatch reveal | [104](104-cave-hub-design.md) 15.1 (teleport item superseded by D22) |
| L4 | Playtest profile sets `LowPolyDinos=true`, default false | [108](108-lowpoly-playtest-profile.md), BD-225 |
| L5 | Nest drops during weather carry the weather tag | BD-156 |
| L6 | Process: keep 3-4 agents; QA agents never touch Place1.rbxl; flags off by default | kanban log, [AGENTS.md](../AGENTS.md) |
| L7 | Audience read as children 7-10 | [114](114-handbook.md) s2 |


## 2026-10-16 (late): vibe words
- OWNER: the guiding adjectives are polished, satisfying, calm, bubbly, friendly, vibrant. They describe the overall vibe of every facet (visuals, sound, animation, feel, transitions) and are NOT literal per-place rules (e.g. "calm and bubbly" never meant "the cave must be bright"). New tasks and decisions are vaguely cross-referenced against them and against the relevant handbook sections; the handbook is used more by the lead for quality and vision assessment and is updated as the owner adds or changes things; the owner will be asked more questions over time to narrow it down. Recorded in docs/114 section 0.

- OWNER (2026-10-16): luminance bands cave 0.15-0.35 and island 0.35-0.75 confirmed; cool grey stone is fine as cave decoration (BD-414/415 closed as accepted); audience, class colours, aura ownership, eyes, weather tone, nest cap, balloon skin and perk price remain open questions in docs/116.

- OWNER (2026-10-16, via coordinator): the fast-travel perk (D22, BD-391/405) is priced as a mid goal, about 500 crystals. Still PROVISIONAL (`ProgressionConfig.FastTravelPrice = 500`); supersedes the 300 / 600 / 1,200 options in docs/116 Q10.

## 2026-10-16 (night): eggs per run
- OWNER: a normal 5-minute run should give about 15 run eggs. `FoodCatchRate` is now 12/500 (PROVISIONAL, BD-418, [119](119-catch-rate-15-per-run.md)); 4/500 and 40/500 are HISTORICAL. Per-run crystals, XP and nest frequency are kept the same per food. Growth (`GrowthPerFood`, size only) is untouched. Needs a Studio food-per-minute measurement.
- OWNER (2026-10-16): bonus egg nests per run are technically unlimited (`NestMaxPerRun` removed). Only 5 nest spots exist; every nest without a free spot converts to crystals at once, inside the same exactly-once settlement transform (`outcome.nestCrystals`, private state `LastRunNestCrystals`), with the short kid-friendly toast "Nests full! Extra nests became N crystals" (docs/72). Value per extra nest is PROVISIONAL: `Config.NestOverflowCrystals = 50` (about one 4-egg run is 30 crystals, a nest is worth 6-12 eggs). The run egg cap (`RunEggMaxPerRun`) still bounds nests in practice. No profile rewrite of existing saves. Supersedes the 6 offered / 5 claimable example and the "nest storage full" drop. Resolves C-15, Q8.
- OWNER (2026-10-16): auras and trails belong to ONE specific dino instance (not species, not account) and are lost on fusion (docs/46, BD-059). Decision only recorded; the per-account to per-dino migration is not implemented (BD-059). Resolves C-12, Q3.
- OWNER (2026-10-16): the Balloon skin (defeat = pops and flutters away softly) is a **Robux skin**, like Bricks, Clay and Plushy. Answers docs/116 Q5 option (a). Release stays behind the Robux release flags until tested; no art upload is needed (procedural skin). Tracked in [120](120-pending-owner-uploads-checklist.md).
- OWNER (2026-10-16): first friends playtest: cap 4 players; everything ready ships in session 1 (rare-hatch celebration, telemetry, class feel); the cave hub is in session 1 (playtest profile sets `CaveHub = true`, default stays false). See [125](125-friends-playtest-go-no-go.md).

## 2026-10-16 (owner vision answers)
- OWNER: PvP is an optional side; the core loop is food, eggs, growing. Hunting players happens, but a Peaceful option must be easy to pick (BD-421).
- OWNER: session shape is short runs of about 5 minutes, a hatch party after each, several runs per session (BD-426).
- OWNER: long-term goal is an equal mix of completing the collection, perfecting one favourite dino (fusion to Diamond) and playing as new dinos with a different class feel (BD-427).
- OWNER: Robux line is looks plus convenience (skins, cosmetics, time-savers like potions or extra nest spots), never exclusive power. Robux flags stay off until policy is tested (BD-425).
- OWNER: eggs caught in a run are ALWAYS kept, also when eaten; being eaten just ends the run early (BD-422).
- OWNER: cave hub mood is a cosy home base: warm, safe, lamp-lit den to relax, shop and show off dinos.
- OWNER: players can play as ANY dino they own, each with its own class feel (BD-423).
- OWNER: a rare hatch (Legendary, Shiny, event mutation) gets a huge celebration: screen-wide fanfare, confetti, special sound, server announcement (BD-424).
