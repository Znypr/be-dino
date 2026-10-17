# BD-382 one tap on another rail button with a station menu open (2026-10-17, round 2)

Build: playtest profile (CaveHub on), Play, 1140x785, real mouse clicks. Proof of each hop: the Output line `[Be Dino] hub travel znyprs -> <station>` and the dino position.

| Step | Result | Image |
| --- | --- | --- |
| Potions menu open, ONE click on SHOP: menu closes, travel to the Shop station, Shop opens | PASS (log `potions` then `style`) | 01 |
| Shop open, ONE click on EGGS: travels to the nests station, Eggs screen opens | PASS | 02 |
| Eggs open, ONE click on FUSION: Fusion (own ScreenGui and scrim) opens | PASS | 03 |
| Fusion open, ONE click on SHOP: Fusion closes, Shop opens at its station | PASS | 04 |
| "Back to the middle" chip clicked while the Shop menu is open: the menu closes and the dino returns to the Heart spot (-14, 575) | PASS (twice) | 05 |

Not covered: a touch tap (phone), the chip's dimmed look behind the scrim (the chip received the click, which is the acceptance). Result: PASS.
