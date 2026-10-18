# 196 Art batch 1: food, paint bucket and tier icon candidates (2026-10-18)

Status: **candidates only. Nothing is uploaded, nothing is bound, nothing is in the game.** The owner picks, then the lead uploads (needs the Decal-to-image-id step, [docs/120](120-pending-owner-uploads-checklist.md)). Task row: BD-1094. Related: BD-1078 (paint bucket), [docs/catalog/Home.md](catalog/Home.md) (Missing list), [docs/109](109-owner-art-prompt-pack.md) C2.

## What was made
Three ChatGPT image sheets, made with the owner's ChatGPT account in his browser (Claude in Chrome), in the style of his class icon sheet (chunky, round, soft matte, thick dark outline, no text). Each sheet came out as a clean grid on the first try; nothing was regenerated.

| Sheet | Original | Ruler copy (A, B, C ... / 1, 2, 3 ...) | Evidence picture |
|---|---|---|---|
| Food, 4 x 4: rows berry, fruit, egg, amber | `docs/reference/art-batch1-food-chatgpt-v1.png` | `...-labelled.png` | `evidence/review-2026-10-17/38` |
| Paint bucket, 4 x 4: 16 ideas | `docs/reference/art-batch1-bucket-chatgpt-v1.png` | `...-labelled.png` | `39` |
| Tier badges, 4 x 3: rows Emerald, Gold, Diamond; columns footprint, coin, shield, sparkles | `docs/reference/art-batch1-tiers-chatgpt-v1.png` | `...-labelled.png` | `40` |

One contact sheet groups every candidate per item (with 64 px copies, flags): `docs/evidence/review-2026-10-17/37-art-batch1-contact-sheet.png`.
The 44 cut pictures (transparent PNG, 512 px) are in `resources/ui/v2/candidates/art-batch1/`. Ids: `food-<berry|fruit|egg|amber>-<A-D>` (column letter on the food sheet), `bucket-<A-D><1-4>` (the cell on the bucket sheet), `tier-<emerald|gold|diamond>-<A-D>` (A = footprint alone, B = coin, C = shield, D = sparkles).

## Prompts (sent in one chat, in this order; shortened here, the full text is in `docs/reference/art-batch1-prompts.txt`)
1. Food: "one landscape sheet, clean 4 by 4 grid, cute chunky game icons of FOOD for a calm bubbly children's dinosaur game, round-ish chunky shapes, soft matte cartoon finish, thick dark-brown rounded outline, one object per cell, flat light-grey background, no text. Row 1 BERRY, row 2 FRUIT, row 3 EGG, row 4 AMBER, each column a different idea."
2. Bucket: "same format and style, 16 different PAINT BUCKET ideas: steel bucket, wire handle, open top with flat plain WHITE paint and one white drip; vary tilt, steel colour, handle, stripe, dent, brush, splash."
3. Tiers: "same style, 4 columns by 3 rows, fusion TIER BADGES shaped like a chunky three-toed dinosaur footprint: Emerald, Gold, Diamond; per row: footprint alone, in a round coin, on a shield, with three sparkles."

## How the cut was checked (tools/cut_icon_sheet.py, tools/art_contact_sheet.py)
- Objects are found where they are drawn (the sheet grids are not exactly equal: the bucket rows nearly touch), cut out, and the flat grey background (229,228,228, the same on all three sheets) is flood-filled to transparent. A 1 px shave removes the light fringe.
- **44 of 44 backgrounds removed cleanly.** Flags: EMPTY 0, MUDDY 0, CLIPPED 0, BG-NOT-CLEAN 0. One note: **bucket-D1** has ragged light-grey leftovers inside the handle arc (a shaded gap, GAP-CLEARED): not usable without a hand clean-up.
- Low colour by design (not flaws): bucket-A1, C2, D3 (silver steel).

## Recommendation (look at the contact sheet at 64 px too)
| Item | Best | Second | Why |
|---|---|---|---|
| Berry | **food-berry-A** (blueberry) | food-berry-C (red berries) | One round shape reads at 64 px; blue is the only blue among the four foods, so berry never looks like fruit. Raspberry (B) is cute but has fine bumps. |
| Fruit | **food-fruit-A** (apple) | food-fruit-B (peach) | Red apple is the clearest fruit. Orange slice and mango are too close in colour to Amber. |
| Egg | **food-egg-A** (cream egg, teal spots) | food-egg-D (egg in a nest) | Same cream and teal as the game's eggs; the cracked egg (B) looks like a failed hatch, the gold egg (C) looks like Amber. |
| Amber | **food-amber-C** (fossil leaf and bug inside) | food-amber-A (raw chunk) | Says "amber" at a glance and cannot be mistaken for the crystal currency. The crystal cluster (D) is almost the crystal icon (`resources/ui/v2/icons/amber.png`): avoid. The bug is small; at 64 px the chunk A is the safer read. |
| Paint bucket | **bucket-A1** (silver, brown grip, one drip) | bucket-B4 (light blue) | Silver is neutral, so the tinted paint is the only colour; clean silhouette, white paint is plain. Coloured buckets fight the tint. B4 only if the owner wants a colour. Avoid D1 (ragged gap) and D3 (brush hides the paint). |
| Emerald tier | **tier-emerald-A** (footprint alone) | tier-emerald-B (coin) | Matches the existing Diamond footprint (faceted gem, dark outline). The Gold and Diamond files that exist already (`layers/mutation-gold-v1.png`, `mutation-diamond-v1.png`) are the same footprint family; keep them. If the owner wants a perfectly matching set, tier-gold-A and tier-diamond-A come from the same sheet as emerald-A. Coin and shield versions are there for a plate look. |

## Open and not done
- Rainbow sheen texture is not in this batch (it needs a Blender render).
- Not checked in Studio or on a phone; 64 px readability was only checked on the contact sheet.
- Ruler ids on the labelled sheets (A1, B3 ...) are the sheet cells; the file ids above are per item.
- Next: the owner picks; the lead uploads as an Image through Studio (docs/120), binds `food-*`, `paint_bucket` and `tier_emerald`, and adds one docs/77 line per chosen picture. No asset id exists yet.
- Side effect to know: while starting the first chat, one click landed on a suggestion chip and started a chat titled "Assemble Appeal Evidence" in the owner's ChatGPT history (a Roblox appeal draft). Nothing was sent anywhere; the owner may delete that chat.
