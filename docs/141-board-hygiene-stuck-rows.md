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
