# 206 Pattern tiles that really repeat (BD-1034 part 1b, 2026-10-19)

Status: **done offline (no Studio, nothing uploaded). Part 2 (Studio look at real dino size) is still open.** Follows [190](190-pattern-discovery-part1.md): only 1 of 32 first-round tiles repeated cleanly. This round asked ChatGPT again, with a better question, and got **22 tiles that repeat cleanly, for all 10 recommended ideas** (plus a bonus idea: diamonds). Owner picture: `docs/evidence/review-2026-10-17/457-pattern-tiles-seamless-contact-sheet.png` (ruler: letters across, numbers down; every tile shown 2 x 2 so the seams would show; the 7 patterns in the game next to them).

## 1. What was done
- **5 sheets, 3 rounds** (80 cells), ChatGPT image generation, owner's account, one chat. Prompts as sent: `docs/reference/pattern-tiles-chatgpt-v2-prompts.txt`. Sheets: `docs/reference/pattern-tiles-chatgpt-v2-a.png` to `-e.png`.
- **Round 1 (sheets a, b)** asked "edges match exactly, shapes cut by an edge continue on the opposite edge". The tiles look right but most do not wrap exactly (shapes cut at the edge land in the wrong place).
- **Round 2 (c, d) found the trick that works**: ask for a **perfectly regular grid with an empty margin of exactly half a gap** all round, so no shape touches the edge and nothing has to continue across it. Straight grids of dots, plus signs, triangles, hearts, stars and paws then repeat cleanly. Checks and the fine speckles were asked in their own way (even number of whole squares; specks that continue).
- **Round 3 (e)**: leaves, checks with whole squares, giraffe again, harlequin diamonds.
- Every cell was cut with a **new window finder** (`tools/tile_window_cut.py`, tests in `tests/test_tile_window_cut.py`). It keeps a plain crop (no mirror, no blending) of the part of the cell that repeats best and skips the white frame ring that the sheet leaves round each cell. Checkerboards: it keeps an even number of whole squares. Then: `tools/tile_seam_check.py` on every tile, the new shape test, `tools/pattern_similarity.py` against the 7 patterns in the game and against each other, and **my own eyes on a 3 x 3 repeat of every tile**.
- **Two seam-test traps found** (so the old test alone would have passed bad tiles): (1) a 1 px white frame ring round a tile matches itself, so the column test says PASS while copies show a white cross of lines; (2) a shape cut at the seam and glued to its neighbour can still look like "an ordinary strip". New `tools/tile_seam_strict.py` (tests `tests/test_tile_seam_strict.py`) checks frame rings and cut or glued shapes (labels the blobs in a 3 x 3 repeat). It is a filter, not a proof: it cannot see a flattened shape, so the eye check stays.
- **Mirrored tiles: none used.** Two tiles got the tool's trim repair (2 px off the edge, same look): paws-2 and diamonds-2.

## 2. Results per idea (all PASS in `tile_seam_check`, threshold 1.25; shape test OK; looked at 3 x 3)
Files: `resources/patterns/seamless/seamless-<idea>-<n>.png` (256 px, white = colour 2, black = colour 1). Numbers: `resources/patterns/seamless-report.json`. Source = sheet letter + cell.

| Idea | Tiles | Source cells | Worst seam (1.0 = like any other place) | Note |
| --- | ---: | --- | ---: | --- |
| big dots | 2 | c-A1, c-B1 | 0.5 | straight grid; same look, two sizes |
| checks | 2 | a-B2, a-A2 | 1.1 | 6 x 6 and 4 x 4 whole squares; ChatGPT squares are not perfectly equal (about 1 to 2 %) |
| stars | 3 | d-A1, d-B1, d-D1 | 0.7 | d-D1 is a staggered scatter, the others straight grids |
| giraffe patches | 1 | a-C4 | 0.5 | organic; the only giraffe tile with no visible seam (3 other giraffe tiles show a line) |
| plus signs | 2 | c-A2, c-B2 | 0.8 | |
| triangles | 2 | c-A3, c-C3 | 0.7 | c-C3 mixes up and down |
| fine speckles | 2 | d-A3, d-B3 | 0.8 | scatter of dots and blobs, continues across the edges |
| hearts | 2 | c-A4, c-B4 | 0.5 | |
| paws (maybe) | 2 | d-A4, d-B4 | 1.2 | |
| leaves (maybe) | 2 | e-A1, e-C1 | 0.8 | |
| diamonds (extra) | 2 | e-D4, e-C4 | 0.5 | harlequin; sits close to the checks |

**22 tiles, 11 ideas. Every recommended idea has at least one.** No idea had to be given up.

## 3. What did NOT work (honest list)
- **Staggered ("half-drop") layouts** of dots, plus signs, hearts, triangles and paws: ChatGPT cuts shapes at the edge and they do not continue (only the star scatter d-D1 passed). So the shape tiles are straight grids, a neat, slightly stiff look. A staggered look is a Blender / owner job (not drawn by a script).
- **Organic patterns (giraffe, speckles) are not exact.** They are crops where the wrap looks right; no seam is visible at 3 x 3, but the Studio look on a real dino (UV islands) is still needed. Only 1 giraffe tile survived; dense speckles (d-D3) crumble into a moire and were dropped.
- **Checks from ChatGPT** are not mathematically equal squares; the crop keeps an even count of whole squares. If the owner wants a perfect checkerboard it should be built in Blender or by him.
- Raw ChatGPT cells always carry a white frame ring and rounded white corners: never use a cell uncropped.

## 4. How different are they really? (`tools/pattern_similarity.py`, threshold 0.75)
- **At the 16 px size a player sees on a dino, most shape grids are one look**: dots, plus signs, stars, hearts, paws, triangles and leaves all score 0.9 and above against each other ("blobs on black"). The shape only shows when the tile is big. Tile size is a free knob, so this is a warning for the owner's choice, not a bug.
- **Really different families** (by the machine and by eye): (1) shapes on black (pick one or two), (2) checks and diamonds (hard two-tone squares; checks and diamonds-2 are 0.94 alike), (3) giraffe network (0.56 to the nearest tile, but turns grey at 16 px), (4) speckles (0.61 to the nearest, almost all black).
- Tool shortlist (clean and different from the game's 7 and from each other): **speckles, stars-3, plus-2, hearts-2, checks-2**. Giraffe is left out only because it turns grey when tiny (flag GREY), not because of its seam.
- The 7 patterns in the game are not all different either (bands and wavy stripes 0.81, feeds BD-1033).

## 5. Recommendation
1. **Owner picks by the contact sheet (ids like E3 = speckles-1, A2 = giraffe-1).** My suggestion for 4 to 6 really different looks: **giraffe-1, speckles-1, checks-2 (or diamonds-1, not both), stars-3, one of plus-2 / hearts-2.** Paws and leaves only if the owner likes the shapes (small detail, check in Studio).
2. Part 2 (Studio): the picked tiles on one dino at HUD, index and cave sizes, two colour pairs; look at the UV-island seams; choose tile scale per pattern.
3. For any wanted look that failed (staggered shapes, perfect checks): **needs owner / Blender**, not a script.
4. Then one docs/77 line per tile that stays (the set has one line already), names and tiers (BD-1033, BD-1035).

## 6. Tools (offline, Pillow and numpy only)
`tools/tile_window_cut.py` (new: cut a sheet by the repeating window), `tools/tile_seam_strict.py` (new: shape and frame test), plus the earlier `tile_seam_check.py`, `pattern_similarity.py`, `label_grid_sheet.py`, `cut_pattern_sheet.py`. Example: `python tools/tile_window_cut.py docs/reference/pattern-tiles-chatgpt-v2-c.png out v2c-` then `python tools/tile_seam_strict.py out`.
