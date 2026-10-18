# Studio acceptance round 2, 2026-10-18 (BD-996): the five newly switched-on features

Label: **STUDIO EVIDENCE, desktop Studio only, one player, unpublished copy (memory profile, everyone is admin), game viewport 1156 x 793.** Build: `python tools/build.py --profile playtest` on `origin/main` `04047216` (docs/157 is in it), checked with `python tools/verify_release.py --profile playtest --place ...` (passes, 40 keys), copied to `C:/Users/znypr/dtmp/playtest-build2.rbxlx`, opened as a new Studio (process 32160, studio id `7292e22a-...`, title `playtest-build2.rbxlx`). `Config` read in the open place: `Build` redesign-020, `ReleaseProfile` playtest, **`ObjectivesEnabled`, `CombatEnabled`, `SpecialFoodsEnabled`, `PerDinoCosmeticsEnabled`, `FastTravelPerk` all true**, `CrystalPacksEnabled` false, `PaidRandomItemsEnabled` false, `QaOverlayEnabled` false. Nothing was saved or published; Studio was left in Edit mode. Round 1 is in [../2026-10-18-studio-acceptance/README.md](../2026-10-18-studio-acceptance/README.md) (those flags were off there).

## Read this first

1. **Viewport: 1156 x 793.** The Studio window is maximised (1936 x 1048, read with GetWindowRect, not moved). That is above the 800 x 450 floor, so round 1's tiny-window problem (BD-995) is gone for this window. 640 x 360 phone size was NOT tested.
2. **Frame time at this size is smooth: 60 per second** (p50 16.6 ms, p95 19.9 ms, max 24.7 ms) on the island in a thunderstorm; server 60 per second (p95 17.6 ms). Studio desktop numbers only, not a phone.
3. **One player only.** No second client exists, so a bite between two real players, friend shields and team-up were NOT tested. Combat was tested against the wild predators (calm NPC dinos) that `CombatEnabled` adds.
4. Tool notes: mouse clicks use GUI coordinates (picture y minus 58). `character_navigation` returned "Success" without moving the dino far (the dino stayed 300 studs from the wild predators), so I walked it with `Humanoid:MoveTo` in a script. The test wallet resets crystals to 1,000,000 after every shop action in Studio (by design, `StudioTestWalletEnabled`), so crystal balances only moved from claims and run payouts.

## Results

| # | Feature | Result | Exact observation | Picture |
| --- | --- | --- | --- | --- |
| a1 | Objectives: panel opens, tasks show | PASS | The pill "TASKS +60 crystals" sits left of GOALS in the Sanctuary (hidden during a run, as designed). Tap opens: three tasks with progress bars and CLAIM when done. Tutorial tasks come one after the other (seen: Eat 10 food, Finish a run, Equip a dino, Use leap once, Buy a potion, Collect a second species, Open the Fusion menu; Reach level 3 was paid too) next to the daily and 30-minute tasks (seen: Hatch 10 eggs, Hatch 60 eggs, Use leap 3 times, Buy any potion, Catch an event egg, Finish a run). "New tasks in 26 min" shows when all are done. | 139, 140 |
| a2 | Progress counts food, runs, hatches, leaps, potion | PASS | After a 14-item food pass and a manual run end: "Eat 10 food" and "Finish a run" turned claimable. Later hatches moved "Hatch 10 eggs" to 5 of 10 after the first 5 eggs and both "Hatch 10 / 60 eggs" turned claimable after a 150-egg batch; "Buy a potion" and "Use leap" counted. Leap 2 of 3 counted. | 139, 140 |
| a3 | A claim pays once | PASS (single tap) | Each CLAIM added exactly its listed amount: Equip a dino 10 (1,000,272 to 1,000,282), Use leap once 10 (1,000,000 to 1,000,010), Buy a potion 25 + Collect a second species 30 + Open the Fusion menu 20 + Reach level 3 20 (1,000,000 to 1,000,095), Buy any potion 30 (to 1,000,125), Hatch 10 eggs 15 + Hatch 60 eggs 50 (1,000,125 to 1,000,190). Three fast taps on one CLAIM button early on moved the rows on (the next task slid under the finger), so a deliberate same-id double claim was NOT proven; the server rule is covered offline (`verify_objectives`). | 140 |
| a4 | Fusion-menu task needs a real fusion/list (BD-616) | PASS (T9), NOT TESTED (D5) | "Open the Fusion menu" (+20) turned claimable only after the Fusion menu had really been opened (the server answers the `list` first). I never saw it claimable before opening. "Add a dino toward a fusion step" (D5, paid only by a real fusion) was not among today's three daily tasks, so its payout after the 6-Compy fusion could not be checked. | |
| a5 | Window change | NOTE | The 30-minute window rolled while I played: the unfinished "Use leap 3 times 2/3" came back as 0/3 and a new set appeared (Catch an event egg, Use leap, Finish a run). That is the documented design, but a child may lose a nearly finished task. | |
| a6 | Console | PASS | see Console | |
| b1 | Combat: bite works | PASS | CHOMP button (F) shows. F at 3.3 studs from a wild predator: `LastBiteStatus` hit, its `HpByte` 255 to 244 (11 per bite, about 4 percent). A bite with no one in front gives `no_target`; a bite at the cooldown gives `cooldown`. Bites through the remote every 1.2 s took a predator 255 to 25 in about 20 s. | 142 |
| b2 | Health bars | PASS | A green "heart" bar over my dino and a purple one over the predator, visible on screen. | 142 |
| b3 | Wild predator fights back | PASS | A predator in alert state, then it bit twice: my `HpByte` 255 to 237, later 224; it then lost interest (calm NPC rules, 2 bites per aggro). The run stayed Active. | 142 |
| b4 | Defeating a predator | PASS | Predator reached 0, `NpcFading` true, it faded; my growth went 9.68 to 10.12 (about 5 percent of my own growth, as docs/101 says); eggs and crystals unchanged by the kill. | 143 |
| b5 | No instant predation | PASS (source) | `PredationService.start` returns at once while `CombatEnabled` is true; the only damage I saw came from bites. A real "big eats small" check needs two players: NOT TESTED. | |
| b6 | Two real dinos biting each other, friend shield, team-up | NOT TESTED | only one client | |
| c1 | Fast travel: price | PASS | Shop, Eggs tab, bottom row: "Fast travel: zip to the shops", button "500 Crystals" (shown at level 3; hidden at level 1 by design, BD-447). No R$. | 144 |
| c2 | Fast travel: buy | PASS | Tap: toast "Done!", button turned to "YOURS" (grey, not tappable); telemetry `shop_purchases buyPerk`. | 145 |
| c3 | Fast travel: use and return | PASS | Rail buttons Fusion, Potions, Eggs now travel inside the cave hub (log `hub travel znyprs -> fusion / potions / nests / style / index (spot 1)`); "Back to the middle" chip appears and returns to (-14, 8.8, 575) near the heart. | 146 |
| d1 | Special foods appear | PASS | 33 `golden_drumstick` pickups on the island of 3,563 food (about 1 percent, matches `SpecialFoodChance` 0.01). Each is a generated drumstick mesh, attributes `SpecialFood=true`, `Points=60`. | 141 |
| d2 | Special foods give their points | PASS | Walking onto one: `GrowthScore` 0 to 6 (60 points x 0.1) and eggs 0 to 1 (60 x 0.024 is 1.4); the pickup then left the world. | 141 |
| d3 | Kid-friendly names | FAIL | The words "Golden Drumstick" and "A giant tasty snack!" exist in `SpecialFoods.luau` but nothing on screen ever shows them: no pickup toast, no label, no hint (the only text search of PlayerGui for "drumstick" and "snack" found nothing). A child sees a gold chicken leg and a small number change. Row BD-1002. | |
| e1 | Per-dino cosmetics: pages open | PASS | Shop, Auras and Trails tabs open with a banner "For: Compy / Switch dinos in Dinos to style another one". Prices in Crystals only (Meadow Glow 60, Tidal Halo 470, Royal Nova 3,700; trails 100, 280, ...). | 147 |
| e2 | Nothing buyable with Robux | PASS | Every price is Crystals; the Crystals tab and Eggs tab are "Coming soon"; no R$, "robux" or "buy pack" in the shop tiles (see 156). `CrystalPacksEnabled` and `PaidRandomItemsEnabled` are false. | 156 |
| e3 | Buy, equip, unequip | PASS | Buy Meadow Glow: confirm "Buy Aura?", toast "Done!", the card became "Owned" then "Equipped" with "UNEQUIP"; `EquippedAura` meadow, `GrowthMultiplier` 1.15. Unequip: `EquippedAura` empty. | 147 |
| e4 | Per dino, not per account | PASS | After equipping Raptor the banner reads "For: Raptor", Meadow Glow shows "60 Crystals / BUY" again and `EquippedAura` is empty, while Compy kept its aura. | 148 |
| e5 | Fusion confirm lists cosmetics loss | PASS (shown) | The 6-Compy confirm says "No bought auras or trails will be lost." (the fused Compy set had no bought cosmetics on those instances) and lists all 6 donors. A donor with a bought aura was NOT forced into the set, so the itemised loss warning with a real aura was not shown. | 149 |
| f | Kid-friendly text, clipping | PASS with 3 nits | At 1156 x 793 no words clipped on the HUD, rail, objectives panel, shop, hatch or fusion screens. Nits: the equip toast "Something went wrong. Try..." is cut off (BD-1000); the fusion roll bar label ("Cream 83.3%") is crossed by the yellow marker line (BD-1003); "Cracked • hatches 1 in 5" is small (about 14 px). | 152, 150 |
| g1 | Regression: run start, eat, end run | PASS | Gate walk starts the run (Island, run Active); food pass; HOME asks, "Run Complete": 150 eggs, +272 crystals, growth 743 (the 150-egg run used Food worth x10); a second 3-egg run gave 3 eggs, +7 crystals, "+1 nest". An empty run settles (+0). | 153 |
| g2 | Hatch reveal | PASS with a defect | "Egg 1 of 150": Compy, "Common - 26% of eggs", name, colour, pattern, "Tap for next egg". Tap works; "Skip the rest" works but stops at every cracked egg (about half the eggs at the default weights): the 150-egg batch took roughly 80 taps (BD-1001). Dino Index afterwards "Collected 12 of 22". | 151, 152 |
| g3 | Cracked egg | PASS | "An egg is hatching" cracked, then "Oops! Splat!" with shell halves; "Cracked - hatches 1 in 5". | 152 |
| g4 | Fusion | PASS | Menu "Make a Gold dino" 6 Base / 3 Gold / 2 Emerald; Fill for me; confirm with odds; 6 rolls; "Gold Round Spots Compy" with traits, prestige "Crafted Gold (earned)", lineage "Fused from 6 dinos, recipe gold-same-species-6-v2". Telemetry `fusions 1`. | 149, 150 |
| g5 | Shop "Coming soon" | PASS | Eggs tile "Coming soon" and the buy button reads "COMING SOON"; Crystals tab same. | 156 |
| g6 | Potion buy | PASS | "Buy Potion?" with price and balance after; the potion is listed under "Your potions (tap to use)". | 155 |
| g7 | Weather | PASS | Rain, Thunderstorm and a sunny spell came by themselves (timer chip "Weather in 4 min", "Thunderstorm 51 s"); dark clouds, rain lines, tint, bonus line "Speed +15% - Growth +10% - Eggs +40%". Sound and camera shake not judged. | 154 |
| g8 | Dino swap | PASS | Equipping Raptor in the Dinos menu worked; Diamond Scales and Round Spots Compy swapped. The plain starter Compy could not be equipped (BD-1000). | |
| h | Frame time | PASS (desktop) | see Numbers | |

## Console

Client log, whole session (about 40 minutes of play): 5 `UIBlox - Warning: FoundationProvider not found` (Roblox's own boot warning, same as round 1), **0 errors**. Server game lines only: `[Be Dino] redesign-020 ready`, admin lines, hub travel lines, `[BD-TELEMETRY]` for run_end, hatches, shop_purchases, fusions. **0 errors, 0 warnings from the game.**

## Numbers (Studio desktop only)

| What | Value |
| --- | --- |
| Viewport | 1156 x 793 (window 1936 x 1048) |
| Client RenderStepped | 60.2 per second in the hub, then 60.1 per second on the island in a thunderstorm: p50 16.6 ms, p95 19.9 ms, max 24.7 ms |
| Server Heartbeat | 60.0 per second, p50 17.0 ms, p95 17.6 ms, max 19.3 ms (one player) |
| Studio memory | 3,814 MB (hub) to 4,145 MB (island) |
| Workspace descendants | 10,553 on the island |
| Special food | 33 of 3,563 pickups (0.9 percent) |
| Combat | bite 11 of 255 HP (4 percent), cooldown about 0.9 s; wild predator killed with about 24 bites |

## Defects found (kanban rows)

| Row | P | What |
| --- | --- | --- |
| BD-1000 | P2 | Tapping the plain starter Compy and EQUIP does nothing; toast says "Something went wrong. Try..." and is cut off |
| BD-1001 | P2 | "Skip the rest" stops at every cracked egg: a 150-egg batch needs about 80 taps |
| BD-1002 | P2 | Golden Drumstick (special food) has no name or pickup message on screen |
| BD-1003 | P2 | Fusion roll: the marker line crosses the colour label text |

## Not tested and why

* A bite between two players, friend shield and team-up, the instant-predation rule against a real second dino (needs a second client).
* 640 x 360 and phone shapes, touch zones, the CHOMP button on a touch screen, Android or iPhone frame time.
* D5 "Add a dino toward a fusion step" payout (not in today's daily set), a deliberate double-claim of one objective, the loss warning with a donor that really owns a bought aura, a defeat of my own dino by a wild predator (they give up after 2 bites; at 255 HP I only lost 31 HP).
* Sounds of the bite, predator and weather, camera shake (measured nothing, heard nothing).
* Rejoin after a run end, fusion or purchase; a published server.

## Files

Pictures 139 to 156 are in this folder and in `docs/evidence/review-2026-10-17/` (also copied into the main checkout folder as `NNN-studio-r2-....jpg`).
