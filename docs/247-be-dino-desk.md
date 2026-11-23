# 247 Be Dino Desk: see what is in the game, give feedback per item

Owner request 2026-11-22: "build a tool similar to footage desk, where you show me things of the game, for example the current dino assets,
dinos, statues, vegetations etc, so I get a feel what we actually have in game, same with menus, buttons etc. and I can give concrete
feedback what I like. same thing with fonts, outlines, buttons."

## What it is

A desktop app (`apps/be-dino-desk`, Electron + React + shadcn/ui, the same stack and look as the owner's Footage Desk) that shows
everything we have as browsable grids, and records the owner's verdict per item.

| Tab | What it shows | Source |
|---|---|---|
| Dinos | the uniform portrait capture of every V3 species, next to the old cutouts | `build/hatch-mock/portraits/*-v2.png` (portrait tool), `resources/ui/v2/dinos/v3` |
| World | vegetation, decoration and statues, food, cave, map pictures, newest first | `docs/evidence/*` folders by keyword |
| UI kit | icons, kit pieces, buttons, cards, hatch pieces | `resources/ui/v2/*`, `build/hatch-mock/art` |
| Screens | the newest HUD, menu, shop and hatch captures | `docs/evidence/*` folders by keyword |
| Menus | proposal vs build per spec element, owner notes per element and free pins (BD-1301, below) | `docs/menu-specs/*`, checker reports |
| Text and buttons | live specimens of the text styles (white word, dark label), outline weights and buttons, drawn with the game font | rendered in the app |

`tools/desk_catalog.py` builds the catalog (one JSON on stdout); the app runs it on open and on Refresh. Adding a source = one line there.

## Feedback

Per item: Like, Dislike or Upgrade, plus a note. Per group: a note. Saved on every change to `docs/feedback/asset-desk.json`
(`{"items": {id: {"verdict", "note", "at"}}, "groups": {...}}`, id = the repo-relative path). Agents read that file before art, UI
or text work and treat Dislike / Upgrade items as queue input (feature intake rules apply). The smoke test never writes it.

## Menus tab (BD-1301)

Owner 2026-11-23: "teach be dino desk to help identifying these small differences and let me also help input things like clicking on
elements saying whats wrong, so we get more specific changes for all menus".

- One entry per `docs/menu-specs/<screen>/` (proposal thumbnail, newest check: misses + date, open owner notes). The newest check is the
  newest `report.json` of `tools/menu_spec_check.py` under `build/menu-check/<screen>/` or `docs/evidence/*<first word>*/` (MENU_REPORTS
  in `tools/desk_catalog.py`; adding a source = one line).
- Compare view: PROPOSAL and BUILD side by side, the build scaled so its menu window sits exactly on the proposal's window; onion 50 %,
  blink (key B) and a wipe slider; wheel zoom and drag pan, both pictures locked; opens zoomed onto the menu (F). Every spec element is a
  box: green = within tolerance, red = miss, grey (dashed) = not built or not in this check.
- Click a box (or the element list): the two crops large, the measured numbers proposal vs build (box, fill, border, corner, text height,
  text colour, outline, art size, words, font; misses in red) and the note form: tags (keys 1-9), note, must fix / nice to have, "should
  be" (Enter saves, Esc closes). Click outside every element, Shift-click, or pin mode (P): a free pin, x/y in % of that side's window.
- Saved per change to `docs/feedback/menu-feedback.json` (`{"screens": {screen: {"elements": {specId: [note]}, "pins": [note + x, y,
  side]}}}`, note = `{id, tags, note, severity, should, at, check, status}`); the smoke test never writes it.
- `tools/menu_spec_check.py` lists open owner notes per element in report.json / report.html; an open must-fix note fails its element;
  `--owner-notes` makes every open note and pin a miss.
- Agents: read `menu-feedback.json` before each menu step and run the check with `--owner-notes`.
- Agents: when a note is fixed, set `"status": "done"` and `"commit": "<sha>"`; never delete or rewrite an owner note.
- Agents: a note the owner reopens in the desk is open again; it is the next step's input, not a new task.

## Not in v1

- Uniform in-game captures of world models (trees, props, statues) with the portrait tool: v2 (same stage, model ids from docs/77).
- Side-by-side compare of two items, and sending a group straight to ChatGPT for critique.
