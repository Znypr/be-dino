# BD-289 walk-up prompts in the cave (2026-10-17, round 2)

Build: playtest profile (CaveHub on), Play, 1140x785. Keyboard G and real mouse clicks; the dino was walked with W/A/D key presses and `character_navigation`.

| Step | Result | Image |
| --- | --- | --- |
| Five ProximityPrompts exist (nests, potions, fusion, style, index), 10 studs, HoldDuration 0, Custom style | PASS | - |
| Standing 7.7 studs from the Potions sign, press **G**: the Potions menu opens once and the dino does not teleport | PASS | 01, 02 |
| Close the menu while still on the pad: it stays closed (no re-open) | PASS | 03 |
| Round tap button (BillboardGui `HubWalkUpFace`, 96 x 96, Enabled) exists while in range | EXISTS, NOT SEEN in the capture | 04 |
| Click on that button | NOT TESTABLE with Studio MCP: a control test with a plain 96 x 96 AlwaysOnTop BillboardGui + TextButton on the character was also not drawn by `screen_capture`, and a real mouse click on its projected position never fired `Activated`. Left for the phone | 05 |
| Settings "Teleport to shops" OFF, press a rail button: toast "Follow the glow" and moss-green glow dots on the floor toward the station | PASS | 06 |
| Teleport OFF, Run Complete "OPEN EGGS": the guide trail goes active (24 dots, 20 enabled), the card stays up | PASS (the dots are the walk-there) | 07 |

Docs note: the row text still says "0.5 s dwell opens the station"; the code and `HubWalkUpRules` say "No dwell, no auto-open" (press only), which is what was seen. Left: the tap-size face on a phone (BD-293). Row stays Review / test.
