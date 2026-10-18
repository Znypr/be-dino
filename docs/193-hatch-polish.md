# 193 Hatch screen polish (BD-1069 to BD-1073)

Written 2026-10-18. Label: **CURRENT BUILD** after this change (offline proof plus Studio pictures, see the evidence folder); the owner judges taste. Source of the defects: Studio QA round 4, [192](192-studio-round4-qa-close-paths-walkthrough-hatch-audit.md) part C and section 4 (pictures 213, 239, 243 to 249). The release flag `HatchV2` stays off, so this is the normal hatch (the flat egg, then the 3D egg).

## What changed (plain words)

| Row | Before | Now |
| --- | --- | --- |
| BD-1069 | The bucket was a flat grey rectangle with a thin band. The dot in the colour chip was a mix of the egg's two colours (a "Cream" chip showed a green dot). | The bucket is a chunky tin bucket with the paint dipped over the rim and three drips, filled with the colour's own palette colour. The chip dot is a small rounded square in exactly that colour. The pour stream, splash and drops use it too. |
| BD-1070 | Round pills, thin lines, different from the rest of the game. | One shared helper, `src/shared/ChipStyle.luau`: rounded rectangle (corner 9 px), 3 px dark outline, flat palette fill, text at least 14 px. The colour chip, tier tag, pattern chip, condition chip, rarity line and the ribbons use it. |
| BD-1071 | The egg was 188 px wide, then 114 px, then 147 px when the second colour arrived. | `src/shared/HatchEggSize.luau` decides the size once (the flat egg picture is the reference, about 189 px). The 3D egg's camera is zoomed and centred to match. A check fails if the two sizes differ by more than 3 percent. |
| BD-1072 | Pale thin streaks and white crosses. | A soft rainbow behind the egg: six rings from red (outside) to violet (inside), built from the existing `ringSoft` effect texture, plus rainbow rim sparks and rainbow confetti at the burst. Calm limits, one static glow with Reduce Motion. |
| BD-1073 | "Egg N of M" over the dino's head, head cut off, "BIG" on the plinth, no reason when Skip stops. | The counter is in the header, left of the X. The dino view starts at the top of the card, ends where the name starts, and is zoomed less. The view's own BIG label is hidden (the ribbon already says it). A small tag in the left margin says why Skip stopped ("Rainbow egg! / Skip stops here"). |

## What is still open

* **Paint bucket art is a PLACEHOLDER.** It is built from UI shapes in the game's style (docs/72 allows that only as a marked placeholder). The final `paint_bucket` icon (docs/83 item 31, `resources/ui/v2/icons/paint-bucket-v1.png`) is still **Missing** in the catalogue; when it is uploaded and bound the shapes switch off by themselves.
* **Rainbow sheen texture** is still **Missing** for a really good look: the `rainbowStrip` slot (docs/120) is empty. This change makes the best use of the effect textures that exist.
* The egg zoom (1.42) and fill (0.497) were measured in Studio on this change (3 to 4 percent difference between the flat and the 3D egg; see the evidence README). The first guess from the QA pictures (1.65) made the 3D egg 16 percent too big.
* Studio pictures: `docs/evidence/2026-10-18-hatch-polish/` (numbers 280 to 293 in the review folder). A real Rainbow egg appeared and shows the rainbow rings; an Astra egg did not appear.
* Other places that still use their own pill-shaped tags (shop rarity tags, Dino Index tags, fusion tags) are not converted yet: follow-up row.
* A secret dinosaur does not show a stop tag (the hatch result does not carry the secret flag); Shiny, BIG, event, Rainbow and Astra do.
* Not tested: phone, gamepad, Astra egg.

## Checks

`python tools/verify_hatch_polish.py --runner <luau.exe>`: pure numbers (one egg size, chip spec, exact colour for every EggColors row, Rainbow budget, card layout), the real hatch screen in the close-path mock (bucket paint and swatch equal the palette rgb, every chip is a px-corner rounded rectangle with a 3 px outline, counter in the header, dino view inside the card), and 9 mutants (each old defect put back must fail). The close-path rules of [181](181-ui-close-paths-audit.md) still pass.
