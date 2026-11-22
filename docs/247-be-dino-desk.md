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
| Text and buttons | live specimens of the text styles (white word, dark label), outline weights and buttons, drawn with the game font | rendered in the app |

`tools/desk_catalog.py` builds the catalog (one JSON on stdout); the app runs it on open and on Refresh. Adding a source = one line there.

## Feedback

Per item: Like, Dislike or Upgrade, plus a note. Per group: a note. Saved on every change to `docs/feedback/asset-desk.json`
(`{"items": {id: {"verdict", "note", "at"}}, "groups": {...}}`, id = the repo-relative path). Agents read that file before art, UI
or text work and treat Dislike / Upgrade items as queue input (feature intake rules apply). The smoke test never writes it.

## Not in v1

- Uniform in-game captures of world models (trees, props, statues) with the portrait tool: v2 (same stage, model ids from docs/77).
- Side-by-side compare of two items, and sending a group straight to ChatGPT for critique.
