# BD-101 potion icons (2026-10-17, round 2)

Build: playtest profile, Play, 1140x785, real mouse clicks.

| Step | Result | Image |
| --- | --- | --- |
| All 12 `PotionArt.Images` ids load: `ContentProvider:PreloadAsync` on 12 ImageLabels, 1.4 s, every `GetAssetFetchStatus` = Success (no blank / Decal upload) | PASS | - |
| Potion Shop cards: real bottle icons, rarity-tinted, 6 offers per restock, crisp at card size (about 58 px) | PASS (the 6 offered of 12) | 01, 03, 05 |
| Buy confirm with the big icon | PASS | 04 |
| Bought a Treasure Draught: owned-potion USE button with its small icon (34 px) | PASS | 06 |
| After USE: HUD lines "Loot potion 9 min / Eggs +25%" with the small chip bottom-right, the timer text does not run under it | PASS | 07, 08 |

Note on 03: "Not enough Crystals" in that frame comes from the scratch config (`StudioTestCrystals = 0` forces the server wallet to 0 while the HUD showed run crystals); not a game bug.

Left in the row: the 5 rarity frames (P2, `frame_*` slots) and the phone-landscape look of the chips. All 12 icons are confirmed loading, but only 6 of 12 were on screen in one restock. Row stays Review / test for those items.
