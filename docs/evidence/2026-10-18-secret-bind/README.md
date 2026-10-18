# Secret roster, second binding round: how each id and size was proven (2026-10-18)

**CURRENT BUILD** facts, measured in the scratch Studio place `cockatoo-scratch.rbxl` (a saved copy of Place 1; never the owner's live window; Edit mode, read only: models were loaded into a temporary folder and destroyed again, nothing in the place was changed, no Play). Creator Hub was only read (one tab, closed afterwards; nothing changed, deleted, renamed or published). No pictures: this is numbers, not a visual change.

## Method
1. Creator Hub > Creations > Models (rows per page 250) listed 244 models of the owner's account. The 180 named "Roblox Generated Object" and created 2026-10-15 or later were taken as candidates (the v3 secret birds were generated 2026-10-15 to 2026-10-17).
2. Each candidate id was loaded with `InsertService:LoadAsset`. Its `MeshPart.MeshId` values were compared with the MeshIds of the seven Place 1 models in `Workspace > Silly secret dinos v3`.
3. An id counts only when the part count (7), the part names and **all 7 part mesh ids** equal the Place 1 model. Exactly one candidate matched each species; no candidate matched two.
4. The size is the bounding box of the loaded model's mesh parts at scale 1 (the snippet in docs/173 section 5; the same convention as the 22 species and the Foxosaurus).

## Result
| Species | Model id | Parts matched | Box at scale 1 (W x H x L, studs) | Place 1 showcase box (scaled copy) |
| --- | --- | --- | --- | --- |
| Chickosaurus | 108391746824463 | 7 of 7 | 1.28 x 2.16 x 2.00 | 4.55 x 7.67 x 7.12 (x 3.55) |
| Pigeon | 83982208995212 | 7 of 7 | 1.82 x 2.31 x 2.00 | 6.04 x 7.67 x 6.65 (x 3.3) |
| Dodo | 128146035116312 | 7 of 7 | 1.10 x 1.91 x 2.00 | 4.45 x 7.67 x 8.06 (x 4.0) |
| Duck | 129901658996389 | 7 of 7 | 1.45 x 2.18 x 2.00 | 5.09 x 7.67 x 7.05 (x 3.5) |
| Penguin | 120950430829492 | 7 of 7 | 2.44 x 2.60 x 2.00 | 7.22 x 7.67 x 5.91 (x 3.0) |
| Budgiesaurus | 107910518074360 | 7 of 7 | 4.00 x 7.33 x 7.91 | 4.00 x 7.33 x 7.91 (unscaled) |
| Foxosaurus (control) | 112996440434481 | n/a (the scratch place holds the old v1 fox) | 3.84 x 8.37 x 8.00 = the recorded 3.8 x 8.4 x 8.0 | not comparable (v1: 4.94 x 8.00 x 6.80) |

Side finding: the scratch place's Foxosaurus is the OUTDATED v1 (glasses and beanie, id 119604460832523, all 8 part mesh ids matched that id). So the scratch place is older than the owner's live Place 1 for the fox; the other six showcase models matched the ids above exactly.

## Not measured
The head length of every secret (an estimate, 22% of the length, like the fox). Nothing was seen in the game or on a phone. The owner has not confirmed the v3 chicken as the final chicken.
