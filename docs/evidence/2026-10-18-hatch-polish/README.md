# Hatch polish, Studio pictures (BD-1069 to BD-1073)

Label: **STUDIO EVIDENCE** (desktop Studio, one player, unpublished copy of the playtest build, memory profile, test wallet). Taken 2026-10-18 on the merge of PR #520 (screen label "BUILD redesign-020 4a9cd285"). Nothing published, no flag changed in the repo. Only for the test copy: the "test chests" switch was turned on in the open Studio copy to get eggs (plain eggs), and the hatch clock was slowed to one fifth so the quick paint stage could be photographed. Real run eggs (40 and 54 eggs, admin "food worth x10") gave all the pictures with colours. No chance was forced: the Rainbow egg in 290 and 291 came up by itself as egg 26 of 40.

Same pictures are in `docs/evidence/review-2026-10-17/` with the same names.

| Nr | What it shows | Row |
| --- | --- | --- |
| 280 | desktop window (1156 x 793): "Egg 1 of 7" now in the yellow header left of X; the bucket | BD-1073, BD-1069 |
| 281 | desktop: the egg cracking, counter in the header | BD-1073 |
| 282 | desktop: reveal card: whole dinosaur visible, nothing over its head, no "BIG" on the plinth | BD-1073 |
| 283 | blue bucket, blue chip with a square blue dot and a COMMON tag, the 3D egg already the same size | BD-1069, BD-1070, BD-1071 |
| 284 | the steel bucket with blue paint over the rim and drips | BD-1069 |
| 285 | blue chip: the dot is exactly the Blue of the colour list | BD-1069 |
| 286 | cream bucket (pale paint still reads on the steel) | BD-1069 |
| 287 | Cream chip with a cream dot (it used to show green), pattern chip "Freckles" | BD-1069, BD-1070 |
| 288 | reveal: a BIG dinosaur, the tag "BIG! / Skip stops here", the BIG ribbon | BD-1073 |
| 289 | the Cracked condition chip (gold, same chunky style) | BD-1070 |
| 290 | a Rainbow egg: purple "Rainbow" tag, rainbow-coloured sparkles | BD-1072 |
| 291 | the soft rainbow rings behind the Rainbow egg | BD-1072 |
| 292 | a failed (Cracked) egg: the splat | not changed |
| 293 | the flat egg picture at the start (about 104 px wide in this window; the 3D egg in 283 is about 107 px) | BD-1071 |

## Window size

Pictures 283 to 293 were taken in a small Studio window (viewport 500 x 465), which switches the game to its small-window layout (docs/192, BD-1067): the hatch card is cut at the right and the glow and rainbow circles sit left or right of the egg. That is the old small-window problem, not new. Pictures 280 to 282 are from the 1156 x 793 window.

## Egg size (BD-1071)

Measured in picture pixels in the same window: flat egg 104 px wide (203 to 307), 3D egg with the new zoom 105 to 108 px wide (203 to 311), a 3 to 4 percent difference. Before the zoom was corrected (1.65) the 3D egg was 121 px next to 104 px (16 percent bigger), which gave the final numbers in `src/shared/HatchEggSize.luau` (zoom 1.42). Not measured: the egg size at every wobble moment, phone.

## Not seen or not verified

* Astra egg: not seen. Splat with the new chip style: the chips are gone at the burst, so 292 only shows the old splat.
* Desktop-size pictures with chips and two colours: the window shrank during the session; 283 to 291 are small-window.
* The rainbow's centre is off the egg in the small window layout (same cause as above); on the desktop layout it follows the egg like the other glow rings (not photographed).
* Phone, gamepad, sound: not tested.
