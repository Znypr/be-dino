# 232 Toybox layout rules (BD-1189), 2026-11-14

Status: **rules set, owner picked B (dark panels) on 2026-11-14.** The pilot page is being built (flag-gated).

Why: the owner saw the Toybox skin in Studio (BD-1177, docs/230) on the Compy detail page and said: "it really looks off, like the padding and buttons, the overall menu looks vibe coded not clean like other top tier roblox experiences". The skin changed the pictures, but every screen still had its old hand-placed layout. This page sets the layout rules every Toybox screen follows. Label: **OWNER TARGET** (clean like top Roblox games); the numbers below are **LEAD proposals (PROVISIONAL)** until the owner has seen them in Studio.

## 1. What was wrong (Compy detail page, `docs/evidence/2026-11-14-toybox-studio/`)

1. Uneven padding: the left column almost touches the frame, the right half is an empty stud field and the copy card floats in a corner.
2. Text sits straight on the studs (busy, low contrast); the info list is cut off and needs a tiny scrollbar.
3. Buttons in five sizes and five random colours (pink Sort/filter, grey EQUIPPED, cyan BACK, green pill).
4. Mixed type: outlined white, yellow and blue words inline, 12-14 px lines next to 28 px titles.
5. "Compy x 1" repeats the window title; the X sits on the header edge.

## 2. The rules

| Rule | Value |
| --- | --- |
| Grid | every gap, padding and size is a multiple of 4, normally 8 |
| Window inset | 16 px from the frame to the content, on every side |
| Gutter | 12 px between panels, cards and buttons |
| Studs | only the window background and margin. **No text on studs.** |
| Panels | content sits on flat inner panels: 14 px corners, 3 px dark outline, one panel tone per screen (A cream or B dark) |
| Type scale | 28 window title, 20 section heading and button words, 16 body, 14 small (floor, docs/72). Body text has no outline on a panel; titles and button words keep the 3 px outline |
| Label / value rows | label left in a muted tone, value right in bold; no inline coloured words |
| Buttons | one height (48 px, small 40 px), full width of their column or a fixed width; at most **one** coloured (primary) button per screen, every other button grey; red only for the X |
| Header | title vertically centred on the strip, 16 px from the left; small rarity pill after the title; the X inside the strip, 52 px |
| Grids | equal cells (UIGridLayout), empty slots drawn as dashed placeholders so a grid never looks unfinished |
| No repeats | a heading never repeats the window title ("Your Compies (1)", not "Compy x 1") |

## 3. A/B mock (decision aid only, not game art)

`docs/evidence/2026-11-14-toybox-layout/mock.html` (real kit pictures) and `compare-now-A-B.jpg` (now / A / B).

- **A, cream panels, dark text:** warm, calm, closest to the docs/87 "matte warm" feel and the cream rarity header.
- **B, dark panels, white text:** closer to many simulator games, stronger contrast for the dino colours.

Same grid, same buttons, same content in both. **Owner pick 2026-11-14: "dark" = B on every Toybox screen.** Panel tone: dark slate panels (#2B3140), cards #3A4358, muted labels #B9C2D6, white values; the cream header stays for Common dinos.

## 4. Next steps

1. ~~Owner picks A or B.~~ Done: B (dark).
2. Shared layout helpers in `ToyboxKit` / `ToyboxSkin` (inset, gutter, panel, row, button sizes) so screens stop placing things by hand.
3. Pilot: the dino detail page in code, flag-gated, Studio pictures at 1280x720 and a phone size.
4. Then Crystal Shop (PR #580), Eggs, Index list, Settings, Potions on the same rules.
5. Preload the kit pictures when the skin loads (a new header was blank for a moment the first time it showed).
