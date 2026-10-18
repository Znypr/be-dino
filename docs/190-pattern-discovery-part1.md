# 190 Pattern discovery, part 1: which patterns are really different? (BD-1034, 2026-10-18)

Status: **part 1 done offline (no Studio). Part 2 (look at real dino size in Studio) is open.** Spec: [186](186-pattern-colour-indexes-and-slower-species.md) section 4a. Owner words 2026-10-18: not 24 patterns, not a hunt for big numbers; can you even see the difference between a star and some other pattern; ask ChatGPT for a sheet of black and white repeatable tiles and see how many are meaningfully different.

## 1. What was done
- Two ChatGPT sheets, 4 x 4 tiles each, 32 tiles in all (dots, stripes, waves, camouflage, scales, diamonds, stars, swirls, checks, zig-zag, leopard, chevrons, speckles, honeycomb; paws, hearts, plus signs, triangles, rings, bricks, maze, tiger stripes, giraffe patches, snake diamonds, arrowheads, drops, moons, leaves, weave, bubbles). Originals: `docs/reference/pattern-tiles-chatgpt-v1-a.png` and `-b.png`; copies with a ruler (letters across, numbers down) next to them (`-labelled.png`) and in `docs/evidence/review-2026-10-17/195` and `196`. Tile name = sheet letter + column letter + row number: **a-D3** = first sheet, column D, row 3. Prompts: `docs/reference/pattern-tiles-chatgpt-v1-prompts.txt`.
- Tiles cut and set to pure black and white: `resources/patterns/candidates/` (white = colour 2, black = colour 1, same as the existing masks). The 7 existing non-blank gene patterns, drawn by their real code with the Luau runner: `resources/patterns/existing/` (comparison aid only, not new art). Blank has no ink.
- **Seam check** (`tools/tile_seam_check.py`): 1 of 32 tiles repeats cleanly as delivered (b-B2 bricks), 1 more after trimming 2 stray pixels, **30 do not** (a shape is cut at the edge, or a stripe comes out too wide where two copies meet). ChatGPT does not make seamless tiles; do not assume it did. Pictures: `198` (3 x 3 repeat of every failed tile, wrap lines in red) and `199` (before and after the repair).
- **Repairs** (copies in `resources/patterns/candidates-fixed/`, originals untouched, method per tile in `repairs.json`): 21 mirrored 2 x 2 (always seamless, but flips the shapes: a kaleidoscope look), 3 trimmed or cropped to the real period (same look), 7 cross-faded (can crumble shapes, flagged BLEND-FIX and never shortlisted). A mirrored tile is a new layout of the same kind of shapes: judge the final art by eye.
- **Similarity** (`tools/pattern_similarity.py`): every pair compared at 16 and 32 px and as a 3 x 3 repeat, turned and flipped, slid sideways, and also "same shape, other size" (size is a free setting on the dino) plus a texture "feel" number (how much ink, how much detail, how fine). Flags tiles that vanish (EMPTY/FULL), turn grey (GREY), are as busy as noise (BUSY) or have a seam. Contact sheet: `197-pattern-tiles-contact-sheet.png`.

## 2. Numbers (threshold 0.75 = "looks alike")
| | count |
|---|---:|
| candidate tiles | 32 |
| seam test: pass as delivered / pass after trim / fail | 1 / 1 / 30 |
| repaired copies | 31 (21 mirror, 7 cross-fade, 2 period crop, 1 trim) |
| clean after repair (no flag: not empty, not grey mush, not noise, seam ok) | 15 |
| **survive: clean and different from the 7 existing patterns and from each other (tool shortlist)** | **11** |
| recommended shortlist (hand-trimmed, below) | 8, plus 2 maybe |

Tool shortlist (best first): a-B1, b-A1, b-C1, a-C3, b-A3, a-A3, b-B1, a-C4, b-D1, b-B4, a-A2. Recommended 8: **a-B1 big polka dots, a-C3 checks, a-A3 stars, b-A3 giraffe patches, b-C1 plus signs, b-D1 triangles, a-C4 fine speckles, b-B1 hearts**. Maybe: b-A1 paws, b-B4 leaves (small detail, check at real size). Dropped from the tool list: a-A2 (waves: in the owner's group below, and 0.84 alike to the bands a-D1). **Not padded: 8 new ideas, not 24.** The other 21 of 32 did not make the tool list (seam only fixed by cross-fade, or vanish / grey mush at 16 px, or look like another tile).

## 3. The owner's own check
Owner looked at the first sheet: a-A2 (waves), a-D3 (zig-zag) and a-D4 (honeycomb) look really similar. **The machine agrees for two of three**: a-A2 and a-D3 are 0.76 alike by "feel" (both fine two-colour lines). **It does not see a-D4**: honeycomb is thin white lines on black (22 % white) against 50 % bold bands, shape match 0.19 to 0.47, feel 0.00 to 0.10; no honest setting joins it without joining half the sheet. The owner's call wins: `resources/patterns/owner-groups.json` ties the three together, so only one (a-A2) can be on the tool shortlist. The "feel" number was tuned with this one statement; treat the shortlist as advice.
Also found: the existing patterns are not all different either: horizontal bands and wavy stripes are 0.81 alike, round spots and diamond scales 0.73. That feeds BD-1033 (rarity per existing pattern).

## 4. What part 2 needs (Studio, BD-1034 part 2, not done here)
1. Put the recommended tiles (repaired copies) on the same dino at the sizes a player sees (HUD dino, index card, dino across the cave), two colour pairs, and look. The 16 px numbers only say "too fine for a tile that small"; the tile scale on the dino is a free knob.
2. The seam test cannot see **how the tile lands on the dino's UV islands**: a perfect tile still shows a seam where two islands meet. Only Studio shows that.
3. A proper seamless source for the keepers (mirrored tiles are a stand-in): ask ChatGPT again for "exactly repeating, one tile, edges must continue", or accept the mirror look.
4. Then one docs/77 line per surviving tile, names, tiers and boost (BD-1033, BD-1035).

## 5. Tools (all offline, Pillow and numpy only)
`tools/cut_pattern_sheet.py` (cut a sheet), `tools/tile_seam_check.py` (seam test, picture, repair), `tools/pattern_similarity.py` (similarity table, shortlist, contact sheet), `tools/label_grid_sheet.py` (ruler on a sheet), `tools/render_existing_patterns.py` (existing masks to pictures). Tests: `tests/test_tile_seam_check.py`, `tests/test_pattern_similarity.py`, `tests/test_label_grid_sheet.py`.
