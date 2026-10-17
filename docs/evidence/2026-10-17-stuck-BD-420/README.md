# BD-420 nests beyond the five free spots become crystals (2026-10-17, round 2)

Build: playtest profile, Play, 1140x785. Scratch config only: `NestIncubationSeconds = 20`. Food worth was raised in Admin (x9.5) to reach 150 eggs fast; the dino ate via `Humanoid:MoveTo` from the Client console (movement only; every reward is the real server settlement). A run ends with real clicks on HOME and GO HOME.

| Run | Telemetry `run_end` | Result | Image |
| --- | --- | --- | --- |
| 1: 247 s, 150 eggs | `nests:5, crystals:272` | five nests into the five empty slots, no overflow, Eggs screen "Nests 5/5" | 01, 02 |
| 2 and 3: 54 s and 106 s, 150 eggs | `nests:0` | no nest at all under 120 s (the 120 s qualification of the reward math), no overflow line | 03 |
| 4: 129 s, 150 eggs, slots 5/5 full | 5 nests earned, 0 free spots | Run Complete shows "Extra nests: +250 Crystals" (5 x `NestOverflowCrystals` 50) on top of +272, toast "Nests full! Extra nests became 250 crystals", crystals 1,882 (+522), Eggs screen still "Nests 5/5" | 04, 05 |

Exactly-once: the crystal total moved by 272 + 250 once per settlement (one `run_end` per run in the Output). Result: PASS for the Studio check of BD-420. Observation (documented behaviour, not a bug): runs under 120 s give no nests however many eggs were eaten.
