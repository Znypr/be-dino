# BD-146 equip swap with patterns and the aura rig (2026-10-17, round 2)

Build: playtest profile, Play, 1140x785, real mouse clicks (Dinos, species page, EQUIP). A batch of 93 hatched eggs gave a Round Spots Stegosaurus; the Shop was used first to buy and equip the Tidal Halo aura on Compy.

| Step | Result | Image |
| --- | --- | --- |
| Tidal Halo aura bought (470) and equipped on Compy | PASS | 00 |
| Open the blue Round Spots Stegosaurus page and press EQUIP | PASS: toast "Equipping..." | 01, 02 |
| In the world: the Stegosaurus with its blue round-spot pattern, no old Compy underneath | PASS | 03 |
| Client check: exactly ONE `LocalMeshVisual` on the character, the server `DinoVisual` shell has 7 mesh parts and all 7 are Transparency 1, `SpeciesId=stegosaurus`, genes `03_round_spots`, `EquippedAuraId=tidal` kept | PASS | - |
| Swap back to Compy: again one `LocalMeshVisual`, `SpeciesId=compy`, aura still `tidal` | PASS | 04 |

Result: PASS, including the pattern and aura-rig swap the row said was never exercised. Not covered: the old failure path (a client mesh clone that fails), which needs a forced failure; it is covered by `tools/verify_equip_visual.py`.
