# 141 Board hygiene 2026-10-16: stuck rows and the lead's Studio check scripts

Label: **BOARD AUDIT (docs only).** Six rows sat at `In progress` / `In review` with no open PR and no agent working on them (checked 2026-10-16 20:30 UTC against `gh pr list --state open`: PRs 286, 291, 297, 305, 306; none touches these rows, and none of their branches carries a commit for them). The board summary shows exactly these six (4 In progress, 2 In review), so the whole-board scan found no others. Rule used: code merged + only Studio / phone / owner checks left = `Review / test`; nothing is marked Done without recorded evidence (AGENTS.md). Status itself lives only in [07-kanban](07-kanban.md).

## 1. Decisions

| Row | Was | Now | Evidence (merged PRs, folders) | What is left, and who |
| --- | --- | --- | --- | --- |
| BD-019 device/load | In progress | Review / test | #13 (release profile, `verify_load`), #199 (`verify_multiplayer_sim`, 12 mock players, docs/111). Offline only. | **Owner:** publish the playtest place (docs/55 s4), one Android phone run (docs/55 s3 checklist, same as BD-085/BD-322). **Lead:** Test > Clients and Servers 2/4/8 rows (BD-319/BD-364, docs/111 s5). |
| BD-043 UI motion | In progress | Review / test | #2 (UI motion, premium egg/crack art, 2026-10-08), #25 (docs/62 polish), `docs/evidence/2026-10-08-main-integration`, `2026-10-16-hud-rework`, `2026-10-16-phone-ui-scale` (desktop-size emulation). | **Lead:** docs/62 "Pending" list in Studio (goal line on a phone-size view, flash/shake/banner, motion OFF). **Owner:** approve the premium egg + crack PNGs; phone feel via BD-085. New polish goes in its own rows (BD-396, BD-397, BD-428), not here. |
| BD-130 Weather v2 | In progress | Review / test | #48 (code), #193 (7 events seen in Studio, rated 6-8, 2 fixes), #196 (Full/Lite/Off/Calm counted, BD-349), #296 (BD-055 clouds), #302 (clear-daylight haze). `docs/evidence/2026-10-16-weather-qa`, `-weather-live`. | **Owner:** eye judgement of the 7 events (rain, aurora, quake, blood moon were 6/10), real phone view, weather bed sounds (ids empty, docs/120). **Lead:** 60 fps check in a non-capped window and the cave weather gate with `CaveHub` on (BD-398/BD-403). |
| BD-148 Eggs screen | In review | Review / test | #62 (screen), #200/#210 (BD-369 copy), #214, #274. Seen in Studio only as a first-run walk: `2026-10-16-integration-smoke/07-eggs-screen.png`, `2026-10-16-ftue/04,14`, `2026-10-16-qa-pass/06`. | **Lead:** script A below (nest states, READY nest tap, OPEN loop, AUTO shortcut). Never seen: a READY nest being opened, an empty-slot tap, Auto-open on. |
| BD-154 Mutation audit | In review | Review / test | #61, #133 (docs/99, toast gap fixed), #197 (`RunEggTags`), #194 (mutation QA, seeded), `2026-10-16-mutation-qa` and `-mutation-fixes`. | **Lead:** script B below (one UNSEEDED catch of a weather-tagged egg through the real FoodService, then toast, card badge, hatch, Index, world ring). **Agent:** BD-237 (see section 5). BD-235 is decided (section 5). |
| BD-225 low-poly profile | In progress (lead) | Review / test | #142, #145, #149, #165, #169, #180, #183; evidence `lowpoly-spike`, `-patterns`, `-playtest`, `-clickthrough`, `-fixes`, `-atlas`; docs/108. 22 of 22 species load in the playtest Studio copy. | **Owner:** look at the low-poly dinos and approve flipping the default `LowPolyDinos` (profile already ships it ON for playtests). **Owner phone:** BD-322 pass (dino cost, memory, `LowPolyImages*`). **Owner/lead on the PUBLISHED place:** EditableImage / EditableMesh bakes need asset ownership, never proven live. Not an agent task. |

## 2. Script A: BD-148 Eggs screen (about 10 minutes, lead, Studio)

Setup (2 min). `python tools/build.py --profile playtest`, open `build/BeDino-Build<NNN>-playtest.rbxlx` with File > Open from File (unpublished: memory-only profile, test wallet, Admin button on). In Explorer open ReplicatedStorage > Shared > Config and set `NestIncubationSeconds = 20` in THIS scratch copy only (never save it into the repo or touch Place1.rbxl). Press Play (F5), single player, desktop-size window; later repeat steps 1-3 once at 844x390 (Device emulator, landscape phone).

1. Welcome card: tap LET'S PLAY. Tap the **EGGS** rail button (or press **B**) before any run. Expect: five dim nest slots in a row, each reads "Empty" with a faded nest icon; below, a dimmed egg card with the status "Go find eggs on the island!" and a green **EXPLORE ISLAND** button. No "Eggs waiting" line.
2. Tap an empty slot: toast "Finish a run to earn a nest!". Tap **EXPLORE ISLAND**: the screen closes and you are on the island (no dead end).
3. Open Admin (**F2** or the purple Admin button top-left) > set **Food worth x3**, close it. Eat until the EGGS plate shows 4 or more (about 1 minute). Tap **HOME**, then **RETURN** on the confirm. Check the run summary shows eggs found and a "1 egg nest" style line.
4. Tap **EGGS** again. Expect: slot 1 shows a countdown (20 s, falling), slots 2-5 "Empty"; the big card shows ONE egg with a rarity chip and a condition chip, "Eggs waiting: N" with N equal to the eggs you caught, a status pill ("READY!" or "Ready in ..."), a green **OPEN** button and a blue **AUTO** button with a line "Auto-open: off". Text readable, nothing clipped or overlapping at both window sizes.
5. Wait 20 s. Slot 1 turns green "READY". Tap it: the hatch sequence for the nest eggs plays (6-12 eggs, one at a time). Finish or skip; the screen returns, slot 1 is "Empty" again. The hatched dinos show up under DINOS.
6. Tap **OPEN** on the card. Expect: the hatch sequence for ONE egg, then back to the Eggs screen with the NEXT egg on the card and "Eggs waiting" one lower. Repeat 3 times; after the first two eggs a short "Some eggs can crack!" line shows under the status pill.
7. Tap **AUTO**: Settings opens on its Help tab with "Auto-open eggs" rarity toggles. Turn on Common only, close, tap **OPEN** once: Common eggs hatch without a reveal and a tidy "Auto-opened eggs" summary lists counts. Turn it back off.
8. Pass = steps 1-7 as written, no red Output lines. Record in the BD-148 row: date, window size, PASS / the failing step, screenshots in `docs/evidence/<date>-eggs-screen/`. Failure goes in as a new BD row, not a silent fix.

**2026-10-17 run (agent, own Studio window, [evidence](evidence/2026-10-17-stuck-BD-148/README.md)):** steps 1-5 and 7 pass. Step 6 is outdated: OPEN now starts ONE hatch party and Next egg stays inside it (BD-170); it does not return to the card after every egg. Not yet checked: the "Some eggs can crack!" line (step 6) and the 844x390 repeat; BD-525 (Common auto-open still revealed one plain Common egg), BD-519 (egg drawn top-left once) and BD-524 ("Tell us!" covers the EGGS plate) came out of it.

## 3. Script B: BD-154 mutations, one real catch (about 10 minutes, lead, Studio)

Why: every mutation QA so far used a hand-seeded tag. docs/99 "Not verified" still asks for the real path: weather -> FoodService catch -> tag -> toast -> Eggs card -> hatch -> dino -> world.

Setup. Same playtest build, unpublished, Play (F5). No Config edits needed.

1. Open Admin (**F2**). Weather section: set the length to **10 min**, tap **Blood Moon** (8% per egg, the highest), tap **Start now**. Set **Food worth x10**, close the panel. Expect the weather title card and the red sky.
2. Run: tap LET'S PLAY / EXPLORE ISLAND and eat about 15 food. The EGGS plate climbs fast (cap 150 per run). Watch for a toast "Blood Moon egg caught!" (it can overlap the SIZE bar a little, known). Note its time. Expect roughly 8 of 100 eggs to mutate; if nothing after 60 eggs, repeat the run once (P(none in 60) is about 0.7%).
3. Tap **HOME**, **RETURN**, then **EGGS**. Tap **OPEN** repeatedly (use "Skip the rest" if offered). On every card with a coloured chip at the top-left of the egg, stop and look: chip text "Blood Moon", chip colour pink, soft pink glow behind the egg. That is the Eggs card badge (the item never fully seen before). Mutated eggs are never auto-opened.
4. At the hatch of a mutated egg: ribbon with the mutation name, tinted dino, soft burst; dino body readable (BD-351). A Cracked egg that fails to hatch gives nothing and loses its mutation (owner decision BD-235), so just try the next mutated egg.
5. Open **DINOS**: the new dino card shows a 14 px "Blood Moon" chip; open its species page and the Original-egg popup, both show the badge. Equip it, Explore, look at the ground ring + slow motes about 19 studs away.
6. Pass = toast, card badge, ribbon + tinted dino, Index chip, world ring all seen from ONE real catch. Record in the BD-154 row with screenshots in `docs/evidence/<date>-mutation-real-catch/`. Repeat once with **Volcanic Bloom** (7%, Ember) if time allows.

## 4. Weather eye pass (BD-130, about 6 minutes, lead then owner)

Admin > 3 min > Start now for each of the 7 events, standing in the meadow; for each: title card below the toast, sky and haze readable, the dino readable in a 25-30 stud ring, ends with a soft fade. Run once with Effects = Lite and once with Calm motion (Settings > Look): fewer particles, no shake. Then an owner score per event (the 2026-10-16 QA gave rain 6, thunder 7, blizzard 8, volcano 8, aurora 6, quake 6, blood moon 7). The row stays Review / test until the owner has said the weather is good enough.

## 5. Findings found while checking

- **BD-237 (admin "Mutation chance x10") is marked Review / test with "Merged: #197" but the code does not exist**: `src/shared/AdminRules.luau`, `src/server/AdminService.luau` and `src/client/AdminPanel.client.luau` have no mutation switch (#197 shipped BD-236 `RunEggTags`, BD-351..353). Row moved to Backlog. It would make script B a 2-minute check; it is a small agent task (server flag in the admin settings, playtest build only, test in `tools/verify_admin.py`).
- **BD-004 (Blocked, "IDs pending") conflicts with the code and docs/125, and the owner is unsure which experience it is**: `Config.PlaytestUniverseId` 10769812255 / `PlaytestPlaceId` 111259822927673 are recorded as the private experience "newbuild" on 2026-10-14, and docs/125 s5 tells the owner to publish there. But docs/55 s2 says these exact numbers are the LEGACY experience (docs/42, Build 019 tests) and "not the Milestone 1 place". Owner 2026-10-16: not sure which it is. The row stays Blocked and no id was changed. Owner check (2 minutes): Creator Hub > Creations, open each experience; the experience id is in the address bar, the name is on the page; note name + id for each, and the start place id from Places. Then BD-004 is either Done (ids confirmed, docs/55 s2 corrected) or the ids in Config are replaced.
- **BD-235 decided 2026-10-16** (docs/115): (a) a failed Cracked egg gives nothing, no consolation: the code already matches (a failed outcome has count 0 and credits no event mutation; `tools/verify_mutations.py` asserts it). (b) a nest carries the weather from when it was FOUND during the run: the code does NOT do this, it stamps the weather at settlement on every nest of the run (`Bootstrap.server.luau` -> `commitRunSettlement`), so Backlog row BD-479 holds the change. Not built here.
- The "Board audit 2026-10-16: Merged: #NNN" tags on rows list PRs that mention the BD id, not proof the row is done; rows with a "Merged" tag still need their Studio / phone evidence.

## 6. Owner hands-on list (nothing here can be done by an agent)

1. Check in Creator Hub which experience the recorded IDs belong to (section 5, BD-004), then publish the playtest `.rbxlx` to the right private experience (docs/55 s4) (BD-020, BD-019).
2. One Android phone session (docs/55 s3 Android checklist, BD-085/BD-322): 20 minutes, 3 runs, a 15+ egg reveal, frame rate, memory, heat, background/resume.
3. Look at the low-poly dinos in the playtest build and say yes/no to making them the default (BD-225).
4. Score the weather events and listen to nothing (weather beds are silent until you upload sounds, docs/120).
5. Approve or reject the premium egg and crack PNGs of the UI-motion pass (BD-043).
6. (Done 2026-10-16) BD-235 is decided; see section 5.

## 7. Agent-runnable Studio checks, ranked (2026-10-17)

P0/P1 rows in Review / test whose only open item is a Studio check one agent can do alone (no phone, no second player, no owner taste call, no publishing). Ranked by priority, then by how many rows the check unblocks. Method: own playtest build, new Studio window, real mouse input, Studio screen_capture only (BD-154 method, [bd154-unseeded](evidence/2026-10-17-bd154-unseeded/README.md)).

| Rank | Row | Pri | Unblocks | Result 2026-10-17 |
| --- | --- | --- | --- | --- |
| 1 | BD-148 Eggs screen (script A above) | P0 | BD-152, BD-153, BD-169, BD-094, BD-369, BD-444, BD-092 | Steps 1-5, 7 pass; step 6 outdated; left: phone-size repeat, cracked hint line. [evidence](evidence/2026-10-17-stuck-BD-148/README.md) |
| 2 | BD-170 hatch flow (same session) | P0 | BD-171, BD-397 | Done. [evidence](evidence/2026-10-17-stuck-BD-170/README.md); BD-519 found |
| 3 | BD-365 first eggs never Cracked | P0 | BD-371, BD-369 | Live on 5 fresh profiles; left: odds-panel line. [evidence](evidence/2026-10-17-stuck-BD-365/README.md) |
| 4 | BD-441 / BD-440 / BD-442 first-screen clutter (same session) | P0 / P1 | BD-368 follow-ups | 440 and 442 Done; 441 desktop pass, phone left; BD-524 found |
| 5 | BD-169 + BD-094 (same session) | P0 / P1 | BD-208 look check | Done |
| extra | BD-371 after the splat (needs a Cracked egg) | P1 | none | Done. [evidence](evidence/2026-10-17-stuck-BD-371/README.md) |
| extra | BD-155 "pale Ember dino" check | P1 | BD-162 | Found and fixed BD-518 (tint never rendered on low-poly). [evidence](evidence/2026-10-17-ember-tint/README.md) |

### Round 2 (2026-10-17, branch claude/stuck-studio-round2)

Same method (own playtest build, new Studio window, real mouse and keyboard, `screen_capture` only; scratch config `StudioTestCrystals = 0`, `NestIncubationSeconds = 20`, never committed). Order of the candidates above, plus the phone-size repeat of rank 1.

| Row | Pri | Result 2026-10-17 | Evidence |
| --- | --- | --- | --- |
| BD-445 / BD-372 Shop at 0 crystals | P1 | Hint and hidden CONDITIONS tab (levels 1, 2) PASS; two small bugs found and fixed (BD-529 hint over the footer, BD-530 BUY EGG confirm with a negative balance); left: the CONDITIONS tab at level 3 | [BD-445](evidence/2026-10-17-stuck-BD-445/README.md) |
| BD-382 one tap with a menu open | P1 | **Done**: Potions to Shop to Eggs to Fusion to Shop in one tap each, chip works with a menu open | [BD-382](evidence/2026-10-17-stuck-BD-382/README.md) |
| BD-420 more than five nests | P1 | **Done**: 5 nests into 5 empty slots, then "Extra nests: +250 Crystals" and "Nests full!" once; runs under 120 s give no nests | [BD-420](evidence/2026-10-17-stuck-BD-420/README.md) |
| BD-101 potion icons | P1 | 12 of 12 ids load, cards, confirm, USE button, HUD chip PASS; left: 5 rarity frames, phone look | [BD-101](evidence/2026-10-17-stuck-BD-101/README.md) |
| BD-146 equip swap | P0 | **Done**: Compy to Round Spots Stegosaurus and back with an aura, one visual each time | [BD-146](evidence/2026-10-17-stuck-BD-146/README.md) |
| BD-289 walk-up prompts | P1 | G-key walk-up, no re-open, Teleport OFF glow trail PASS; the 96 px tap face cannot be clicked through the MCP (a plain control billboard also fails): phone only | [BD-289](evidence/2026-10-17-stuck-BD-289/README.md) |
| BD-490 cave dressing | P1 | Renders, meshes load, luminance 0.25 to 0.29 at the Heart, 0.177 at a station (one dark close-up 0.148); owner look left | [BD-490](evidence/2026-10-17-stuck-BD-490/README.md) |
| BD-148 phone-size repeat | P0 | Steps 1 to 6 PASS at 836 x 390 with scrolls; BD-531 (HUD at small heights); the "Some eggs can crack!" line still unseen | [BD-148](evidence/2026-10-17-stuck-BD-148/README.md) |

**Phone size from Studio:** the MCP cannot set a device. `StudioDeviceEmulatorService` is not reachable from the command bar and no tool drives the Device Emulator. A usable stand-in is resizing the Studio window with SetWindowPos until `Camera.ViewportSize` reads about 844 x 390; it checks layout only (touch is off), so touch targets, thumb controls and Billboard tap faces still need the owner's phone (BD-085). Studio also stopped rendering (viewport 1 x 1, MCP "Connection closed") after about 30 minutes with six Studio windows open; the cure was a fresh window.

New rows from round 2: BD-529, BD-530 (fixed), BD-531 (phone HUD), BD-532 (BUY EGG gate in the playtest).

Next candidates, not run: BD-372 level-3 Conditions tab, the BD-148 crack hint line, BD-164/255 (camera rattle needs a quiet machine). Not agent-runnable: anything with a phone, 2+ players or an owner look.

## 8. Review / test sweep of the P0 and P1 rows (2026-10-17, docs only)

Label: **BOARD AUDIT (docs only).** Every P0 and P1 row in `Review / test` (243 rows on origin/main ab0da09) was read against its acceptance items and the evidence it cites. Checked: every `docs/evidence/...` path exists on main, every `#N` is a merged PR (`gh pr list --state all`), the named verifier is in `.github/workflows/build-generated-place.yml` (the five latest main CI runs are green), and the cited picture or README really shows the acceptance item (the cave, menu-fixes, bd524 and lowpoly-clickthrough pictures were opened). Rule (same as s1 and [114](114-handbook.md) s12): never Done because something probably works; code merged plus only a Studio, phone or owner check left stays `Review / test`.

| Class | Meaning | P0 | P1 | Rows | What was done on the board |
| --- | --- | ---: | ---: | ---: | --- |
| (a) DONE-READY | every acceptance item has evidence on main | 8 | 13 | 21 | moved to **Done**, with a "Board hygiene 2026-10-17" note naming the evidence |
| (b) 1-2 items left | an agent or the lead can close it (a Studio check, a small fix, a doc line) | 12 | 42 | 54 | left in Review / test; a "Left" note on every row that had none |
| (c) stale or superseded | a later row or decision replaced it | 0 | 3 | 3 | marked **Superseded** with a pointer |
| (d) needs owner or phone | upload, eye or ear judgement, publish, real phone, 2+ players, live server | 39 | 126 | 165 | left in Review / test; a "Left" note on every row that had none |
| Total | | 59 | 184 | 243 | Review / test P0 59 to 51, P1 184 to 168 (`python tools/board_summary.py`) |

### 8.1 Rows moved

**Done (21):**

| Row | Evidence |
| --- | --- |
| BD-066 | `src/shared/NotifyQueue.luau`, `tools/verify_notify.py` (CI), [80](80-notifications.md); scope of the row is the pure module |
| BD-093 | `tools/verify_nests.py` (CI); its docstring lists gate, exactly-once, 15 h queue, offline, cap, luck, migration, budget |
| BD-183 | [87](87-vision-and-feel-guide.md), AGENTS.md line 59, [00](00-documentation-guide.md) line 12, soft-sound rule in [62](62-polish-sfx-goal-juice.md) and [63](63-sfx-pack.md) |
| BD-239, BD-240, BD-241 | `CombatStats`, `CombatState`, `CombatTeamUp` modules with `verify_combat_stats/state/teamup.py` (CI); scope is the pure modules, wiring is BD-243+, balance stays BD-252 |
| BD-279, BD-280 | `CaveHubLayout.luau`, `SpawnGeometry.luau`, `BiomePlacement.useHub`, `verify_cave_hub.py`, `verify_spawn.py` (CI); stations walked in `evidence/2026-10-16-cave-acceptance/` |
| BD-295 | `evidence/2026-10-16-cave-lighting/07-lava-falls-32-high-under-ceiling.jpg`; the sheet height and the 18 wide non-walkable disc are pinned by `verify_cave_lighting.py` and `verify_cave_hub.py` |
| BD-323 | `evidence/2026-10-16-lowpoly-clickthrough/` (hatch, Index, Fusion, Shop, Settings, 12-dino line-up), [108](108-lowpoly-playtest-profile.md) "Click-through update"; problems filed as BD-326..BD-332 |
| BD-335 | decision [115](115-decisions-log.md) D4 and L2, [116](116-handbook-conflicts.md) C-7 RESOLVED; AGENTS.md line 44, [114](114-handbook.md) s9 and [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md) say 6/3/2 (15/4/2 text is marked historical) |
| BD-383, BD-398 | `evidence/2026-10-16-cave-look-v2/after-03-heart-under-blizzard-warm.jpg`; `evidence/2026-10-16-cave-polish-3/` (blizzard, thunder, volcano in the hall); `verify_cave_lighting.py` (CI) |
| BD-401, BD-403 | `verify_shop_crystals.py`, `verify_cave_weather.py` (CI; the second also ran locally without Luau) |
| BD-404, BD-409, BD-410, BD-411, BD-413 | the QA gates of [117](117-asset-quality-audit.md) (`tools/qa/*`, `verify_world_overlap.py`, `verify_world_budget.py`, CI) with the measured before/after tables in 117 s2 |
| BD-419 | `git ls-files build` has no Build020 file; `.gitignore` lines 15-16 |

Deliberately NOT moved although the row says the offline half is finished: BD-412 (the luminance bands are the lead's guess, owner must confirm, 117 s6 Q1), BD-357..BD-359 (a real server was never used), BD-494..BD-497 (phone forecast and guards, phone run open), BD-250/BD-251 (the verifier named in the row did not exist then; it does now, see s8.3), BD-301 (no after-picture of the Egg Odds panel).

**Superseded (3):** BD-056 by BD-080 (BD-080 is the "BD-056 spec" HUD rework, HudV2, PR #166, `evidence/2026-10-16-hud-rework/`); BD-163 by BD-432 (docs/93 plan table row 2 and docs/123 moved aura/trail anime depth to BD-432; the row's base, PR #45, was closed unmerged); BD-424 by BD-428 (built as BD-428, PR #243; the earlier audit already called it a duplicate).

### 8.2 Rows left (the "Left" note is on the row itself)

(b) one or two items left, 54 rows: BD-082 BD-091 BD-092 BD-100 BD-102 BD-141 BD-145 BD-150 BD-151 BD-153 BD-161 BD-171 BD-174 BD-175 BD-176 BD-180 BD-181 BD-185 BD-202 BD-208 BD-226 BD-229 BD-265 BD-266 BD-267 BD-269 BD-270 BD-281 BD-282 BD-283 BD-287 BD-301 BD-310 BD-313 BD-365 BD-366 BD-367 BD-369 BD-370 BD-372 BD-373 BD-377 BD-389 BD-390 BD-392 BD-395 BD-402 BD-418 BD-423 BD-439 BD-445 BD-460 BD-522 BD-524

(d) needs owner or phone, 165 rows: BD-006 BD-016 BD-017 BD-019 BD-020 BD-023 BD-024 BD-025 BD-026 BD-027 BD-028 BD-029 BD-030 BD-031 BD-032 BD-033 BD-034 BD-036 BD-037 BD-038 BD-039 BD-040 BD-041 BD-042 BD-043 BD-044 BD-045 BD-046 BD-047 BD-049 BD-050 BD-051 BD-052 BD-053 BD-054 BD-057 BD-059 BD-060 BD-061 BD-062 BD-064 BD-065 BD-067 BD-069 BD-079 BD-080 BD-081 BD-090 BD-095 BD-101 BD-103 BD-120 BD-130 BD-131 BD-142 BD-143 BD-144 BD-147 BD-148 BD-149 BD-152 BD-155 BD-162 BD-164 BD-166 BD-168 BD-172 BD-173 BD-177 BD-178 BD-179 BD-184 BD-186 BD-187 BD-188 BD-189 BD-190 BD-195 BD-196 BD-197 BD-200 BD-203 BD-204 BD-206 BD-207 BD-210 BD-213 BD-217 BD-225 BD-227 BD-230 BD-231 BD-242 BD-243 BD-244 BD-245 BD-246 BD-247 BD-248 BD-249 BD-250 BD-251 BD-252 BD-253 BD-255 BD-263 BD-264 BD-268 BD-284 BD-285 BD-286 BD-288 BD-289 BD-290 BD-291 BD-292 BD-296 BD-305 BD-306 BD-309 BD-311 BD-312 BD-316 BD-318 BD-319 BD-321 BD-326 BD-333 BD-336 BD-357 BD-358 BD-359 BD-368 BD-386 BD-387 BD-388 BD-391 BD-393 BD-394 BD-396 BD-397 BD-399 BD-400 BD-412 BD-428 BD-429 BD-430 BD-431 BD-432 BD-433 BD-437 BD-438 BD-441 BD-443 BD-444 BD-462 BD-490 BD-494 BD-495 BD-496 BD-497 BD-500 BD-507 BD-518 BD-531

Every (d) row either needs the owner (uploads, ears, eyes, publish, a yes/no), a real phone, two or more players or the published place, or has no Studio evidence at all and sits in the Build 017-020 era that [44](44-main-integration-checklist.md) still lists under "Remaining Gates". The 23 oldest rows (BD-006 to BD-042, except BD-019) cite no evidence; they got a one-line "Left" and stay.

### 8.3 Findings

- **BD-179 duplicates the still-Backlog BD-140** (crystal pack cards, built under BD-179); BD-140 is P2 and was not touched.
- **BD-081 and BD-343, BD-391 and BD-405** were marked "near-duplicate, kept" by the 2026-10-16 audit and left alone here. **Pair check (claude/verify-motion-poses, 2026-10-17): both pairs are one job each, so BD-343 is Superseded by BD-081 and BD-405 by BD-391.** BD-343 is the same Sound Lab page and the same open job (owner picks by ear, uploads); its only extra, the A/B/C variants of the 22 docs/110 candidates, moved into BD-081's row. BD-405 is the same perk with the same code and tests (`FastTravelPerk`, every file says "BD-391/405"); the owner answer it waited for is already recorded (docs/115 D22, docs/116 C-1 RESOLVED), and BD-391 carries the open items (price 500 PROVISIONAL, Studio/phone acceptance, shop card layout).
- **BD-091 text is stale**: it says 8 catches for the hidden nest gate, code uses `NestMinCatches` 1 (BD-147 audit).
- **BD-248 art does not exist** (BD-247 still says PLACEHOLDER); BD-250/BD-251 cited `verify_motion_poses.py`, which was never created. **Now created (2026-10-17, claude/verify-motion-poses):** `tools/verify_motion_poses.py` (CI) checks every offline item of both rows against the real `LowPolyPose` and the real `LowPolyAnimator`, and it found that the animator never stored `character` in the player rig, so no jump, leap, land, Water surge or defeat pose had ever played; fixed in one line. Both rows stay Review / test for the Studio/phone look only.
- The ID lists in the small table above the board in 07-kanban (Backlog / Ready / ... columns) are old and were not touched; `python tools/board_summary.py` is the live count.
- No code, no Studio, no Place1.rbxl were touched; the CI evidence is the five latest green runs on main plus `verify_cave_weather.py` run locally (the other verifiers need Luau, which this PC lacks).
