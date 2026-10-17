# BD-154 unseeded mutation walk-through (2026-10-17)

Build: `python tools/build.py --profile playtest` (own copy, 420 scripts), Studio Play, single player, 1140x785 game view, admin = the Studio user. Nothing was written by hand: no attribute or tag was set by a script. Input: real mouse clicks and drags on the admin panel and menus; the dino was walked to food with `Humanoid:MoveTo` from the Client console (same effect as holding a movement key), and the HUD, menus and server code did the rest.

Setup used: Volcanic Bloom, 10 min (admin Weather buttons + Start now), Food worth x10 and Mutation chance x10 (admin sliders). Side effect: one stray drag set the "Jump power" feel slider to 90 (live only, not saved; harmless).

Result of the run: 85 eggs caught in about 110 s, 51 carried the Ember tag (the tag list is written by `FoodService` through `RunEggTags`: first mutated ordinals 1, 2, 3, 6, 8), so about 60 percent, the Volcano chance x10 as expected.

| Step | Check | Result | Image |
| --- | --- | --- | --- |
| 0a | Admin panel: weather started (Volcanic Bloom 9 min, banner "Volcanic Bloom started!") | PASS | 01-admin-weather-started.jpg |
| 0b | Admin panel: Food worth x10 and Mutation chance x10 (server attribute `Admin_mutationChanceMultiplier` = 10) | PASS | 02-admin-food-x10-mutation-x10.jpg |
| a | Catch toast while the weather is active: "You found 7 eggs! A weather egg! Hatch it at Home" | PASS (nit: with several eggs in one tick the mutation name is not shown, BD-508) | 03-catch-toast.jpg |
| b | Eggs card: orange "Ember" badge on the next (mutated) egg | PASS | 04-eggs-card-badge.jpg |
| c | HOME, confirm, Run Complete "Eggs found 85", then OPEN EGGS | PASS | 05-settled-run-complete.jpg |
| d | Hatch reveal: EMBER ribbon with the flame, "Ember - Speed +4% - Growth +18%", tinted Compy | PASS | 06-hatch-ribbon.jpg |
| e | Dino Index card chip (flame + EMBER) and Dino Details list chips (two Ember copies, one Plain) | PASS | 07-dino-index-chip.jpg, 08-dino-details-chip-and-preview.jpg |
| f1 | Preview: flame mark and orange motes around the dino in the Details preview | PASS | 08-dino-details-chip-and-preview.jpg |
| f2 | World: equipped Ember Compy has the warm tint and the orange ground ring (`EventMutationId=ember` on the character) | PASS | 09-world-ember-ring-tint.jpg |

Output: no red lines (only the usual UIBlox FoundationProvider warnings and "Asset content representation is being generated").

Not covered: a non-mutated control dino side by side, a second player, a phone window, a real save (playtest profile is memory-only). Closing the hatch window with the X credited the rest of the batch without a reveal (a "You hatched a Mutant Microraptor!" toast appeared), which is existing behaviour.
