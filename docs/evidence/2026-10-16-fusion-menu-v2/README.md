# Fusion Menu v2 (BD-217) Studio evidence, 2026-10-16

Captured through Roblox Studio MCP in one Studio window (`build/BeDino-Fusion.rbxlx`, a copy of the playtest build from branch `claude/fusion-menu-v2`), desktop viewport 1445 x 841, Play mode, left inset set by hand (90 / 140 px).

| File | What it shows | Server |
| --- | --- | --- |
| 01-browse-real-server-one-older-compy.jpg | Browse screen against the **real** `FusionAction` server: the playtest profile owns one older Compy without saved DNA ("Older dino: can't fuse"), goal sentence "You need 6 Base dinos of one kind. You have 0.", six empty slots, "?" result, "Pick 6 more". | real |
| 02-browse-fill-for-me-odds-chips.jpg | After **Fill for me** with a fixture server (14 Base dinos): six slots with previews, numbered green ticks on the cards, "Ready! Tap FUSE.", result preview "Gold Compy", "Guaranteed: Gold!", odds chips (Shiny 0%, Ember 5%, BIG 3%, colours), green FUSE!. | fixture |
| 03-confirm.jpg | Confirm screen: "Fuse 6 Compy?", "All 6 dinos go away. You get 1 new Gold Compy.", the six dinos, effects line, chances chips, odds/recipe version line, Not now / FUSE! (6 go away). | fixture |
| 04-reveal-colour-reel.jpg | Reveal step "Colour 2" (server-committed reel, pointer in the Pink 40% segment, "Pink! (Blend 60% / 40%)"). | fixture |
| 05-ta-da-final.jpg | Final "Ta-da!" card: NEW GOLD badge, Shiny glints, result chips, "Gold stage: guaranteed. Made by you." (screenshot taken before the Skip/Next buttons were hidden on the final card). | fixture |

The fixture server was a temporary `RemoteFunction` installed in that Play session only (the real remote was renamed and restored afterwards); it answers `list` / `quote` / `fuse` with the documented contract so the real client modules could be exercised with more than one dino. Nothing was saved to the playtest profile. The gold preview model is the known runtime-mesh look (BD-219), not part of this change.
