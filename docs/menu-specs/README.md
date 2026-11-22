# Menu specs: build menus step by step against the owner's proposal

Owner 2026-11-23: "we need a better comparison system ... build menus step by step", "more accurate, more specific per element, like texts, outlines, boxes", "including words".

One folder per screen: `proposal.jpg` (the owner's picture from the Design Board) and `spec.json` (every element of that picture):
- `box` [x, y, w, h] in % of the window (card children in % of their card), measured on the proposal and checked with an overlay;
- `kind` box / text / image; `fill` colour; `words` (regex the element's Text must match) or `words_text` (the label inside it); `font`;
- `steps`: the build order. Each step's elements must pass before the next step starts.

The build marks each element with the attribute `SpecId` (same names as the spec, e.g. `card2.price`, `rail.eggs`).

Per step:
1. Build only that step's elements (keep the rest as in the previous step).
2. Studio Play, open the screen, run `tools/studio/dump_menu_geometry.luau` (execute_luau, Client) and save its JSON as `geom.json`; take a screen capture of the same frame.
3. `python tools/menu_spec_check.py docs/menu-specs/<screen>/spec.json --geom geom.json --shot capture.jpg --step N`
   It measures both pictures the same way per element: box, fill colour, border thickness, corner rounding, text letter height,
   text colour, text outline thickness and colour, drawn art size; reads words, font, stroke and colours from the live GUI;
   writes `build/menu-check/<screen>/report.html` with a side-by-side crop per element and a list of misses.
4. 0 misses (tolerance in the spec, default 1.5 % of the window) = next step. Misses = fix the numbers it names, repeat.
5. After the last step: the whole-screen pair and the report go to the owner.

Owner rules beat the picture and are written into the spec's words: kid words, no multipliers ("Grow faster!", never "x1.4"); a count like "x3" is allowed.
`python tools/menu_spec_check.py SPEC --self-test` checks a spec against its own proposal (must be 0 misses).
