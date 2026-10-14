# 78 Project lead handoff (2026-10-14)

For a new lead session (for example a chat in the Claude project "Be Dino!"). Read AGENTS.md, docs/00-documentation-guide.md, docs/07-kanban.md, docs/72-ui-copy-and-asset-standards.md, docs/77-asset-registry.md first.

## How the owner wants it run
- Claude is project LEAD. Decide easy and medium choices (act as designer, balance, UI, audio, engineering roles). Ask the owner only big, distinct decisions, with a recommended answer. No near-identical options (not '15/3/2 vs 15/4/2').
- Owner remarks and questions are FEEDBACK, not the next top task: analyse, break down by role, add Kanban rows (BD-xxx, priority), execute by roadmap priority; challenging ideas is welcome.
- Owner's only to-do list = things only they can do (upload assets, phone test, Roblox login actions). Do everything else yourself (IDs lookup, merging, uploads via Studio MCP).
- Audience is children: short obvious text ('5 min', 'Speed +20%', never '5m 0s' or '1.25x'). Hidden rules stay hidden. No code-generated UI art as final: art = brief, 2D drafts, review, final, upload (docs/72). CHECK docs/39 and the repo/evidence BEFORE commissioning art (a wasted task happened because accepted condition looks already existed).
- Owner values a cohesive, polished, fun game over fine-tuned numbers. Numbers are provisional.
- Usage discipline: Sonnet or Haiku agents only (never Opus), at most 2 agents at once, narrow single-purpose briefs, agents run only the checks for the files they touch (CI runs the full suite), no screenshots unless needed, no long polling in the lead chat (run merge loops in the background), batch owner feedback into backlog PRs.
- Merge policy: lead squash-merges PRs once CI is green (works with `gh pr merge`). Never push to main directly. Commit as Znypr noreply (62771035+Znypr@users.noreply.github.com), trailer Co-Authored-By.

## Owner decisions on record
Milestone 1 = private playtest incl. fusion in experience newbuild (universe 10769812255, place 111259822927673), own data store BeDino_Playtest_M1_v1, all Robux/paid features off, devices desktop + one Android phone. 1 dino per egg, 40 eggs per 500 food, hatch reveal 1 s with rarity skip, potion shop restocks every 2 min with 12 potions/5 rarities, fusion ladder Gold 15 Base / Emerald 4 Gold / Diamond 2 Emerald (same species+pattern), egg nests: end-of-run loot, 10-15 eggs, 3 h each ONE AT A TIME, storage 5, hidden min run ~2 min + min food, own Nests menu, luck bonus. Refuse Home near a bigger dino. Tier-0 40% failed eggs kept. Provisional numbers are in Config and labelled PROVISIONAL.

## Current state (see Kanban for status)
- On main: playtest build, fusion (menu, server, odds), nests, potions, 12-potion shop, copy pass, condition shop (eggs on tiles), dino motion (procedural), Sfx helper (silent until IDs), goal line, world art kit (on in playtest profile), release profile + load tests, asset registry.
- Uploaded to owner's Roblox account and bound/being bound: condition overlays (Cracked 126956807167774, Dirty 105931497056313, Rainbow 117352915695915, Astra 102255733208943) and nest icon 127462994652706 (PR for binding may still be open).
- TO CHECK IN STUDIO: condition overlay decal orientation on the egg, Nests menu with a real nest (needs a qualifying run), Eggs|Nests tab idea, reveal skip UI, Condition Shop on phone size.
- Not built yet: aura/trail effects (docs/70; owner to pick a style, Candy Pop recommended; Kanban BD-110..114), growth/eggs HUD rework (BD-080), sound lab (BD-081), popups (BD-066..), mini-objectives, aura shop icons, Fusion Menu density, phone measurement (BD-085, needs owner phone), species tiers Uncommon/Epic (owner said now), 17 creature data files vs 22 listed species (verify).
- Paused/unmerged: none intentionally.

## Owner open decisions (dashboard)
Aura/trail style pick; Eggs|Nests as one tabbed menu or two buttons. Dashboard: https://claude.ai/artifact/3JRedTuhh7jtMyxZLCWw3p (db collection `decisions`; page built by the lead from a local builder script, can be recreated: sections Roadmap, Needs you (top 3 decisions), Answered (collapsed), What's new log with timestamps and tap-to-enlarge images, pinned to-do bar).

## Environment (this owner machine)
- Windows. Repo checkout used by the lead: C:\Users\znypr\AppData\Local\Temp\bd057\repo (short path; the scratch path hits MAX_PATH). Python 3.14 + PIL/numpy via PYTHONPATH=...\bd057\Lib\site-packages (venv python.exe vanished: use C:/Python314/python). Luau 0.741: ...\bd057\luau\luau.exe and luau-compile.exe. Blender 5.1 at C:\Program Files\Blender Foundation\Blender 5.1.
- MCP: Roblox_Studio (built-in Studio MCP: list_roblox_studios, execute_luau, start_stop_play, screen_capture, user_mouse_input, upload_image) and blender (mcp-for-blender 2.1.9, telemetry off) in %APPDATA%\Claude\claude_desktop_config.json. Studio quirks: execute_luau requires a different module instance than the game's; use user_mouse_input with mouseButtonDown/Up and capture y = screen y + 55; Config is frozen so flags change by editing source in an unsaved copy; only open copies of builds (GameId/PlaceId 0), never the published place.
- Art: current game-ready files in the repo (docs/77). ALL old revisions: owner's Documents\ChatGPT\be dino roblox game\Premium_Egg and Google Drive My Drive/Be Dino/Art Archive/2026-10-08_Premium_Egg_all_revisions.zip.
- Verify before PR: every python command in .github/workflows/build-generated-place.yml, tools/build.py, python -m unittest discover -s tests; build/ is regenerated and committed. Merge conflicts in build/ are resolved by rebuilding.
