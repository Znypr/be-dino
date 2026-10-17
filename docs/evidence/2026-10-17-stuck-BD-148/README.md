# BD-148 Eggs screen: lead script A run in Studio (2026-10-17)

Build: `python tools/build.py --profile playtest` to an own file, Studio Play, single player, 1140x785 game view, memory-only profile, admin = the Studio user. Config edit in THIS scratch copy only: `NestIncubationSeconds = 20` (never saved to the repo). Input: real mouse clicks and drags (admin sliders, rail buttons, OPEN, tap-through); the dino was walked to food with `Humanoid:MoveTo` from the Client console (same effect as holding a movement key). Nothing was written by hand: no attribute, queue or profile value.

Run: Food worth x7, 172 s, 2000 food, 48 eggs, 2 nests, 93 crystals (BD-TELEMETRY `run_end`). Output: no red lines (UIBlox FoundationProvider warnings only).

| Script A step | Result | Image |
| --- | --- | --- |
| Welcome card, LET'S PLAY | PASS | 01-welcome-card.jpg |
| 1 EGGS before any run: five dim "Empty" nests, dimmed egg card "Go find eggs on the island!", EXPLORE ISLAND, AUTO | PASS | 03-eggs-screen-empty.jpg |
| 2 Empty slot tap: toast "Finish a run to earn a nest!"; EXPLORE ISLAND closes the screen and starts the run | PASS | 04-empty-slot-toast.jpg, 05-island-run-start.jpg |
| 3 Admin, Food worth, eat, HOME, RETURN: Run Complete "Eggs found 48", "+2 nests" | PASS | 06-run-complete-feedback-button-goal-line.jpg |
| 4 EGGS: slot 1 countdown, slot 2 "Queued", 3-5 "Empty", ONE egg with rarity + condition chips, "Eggs waiting: 48", READY!, OPEN, AUTO "Auto-open: off" | PASS | 07-eggs-screen-after-run.jpg |
| 5 Slot 1 turns green READY, tap it: "Nest opened!" toast, eggs waiting 48 -> 58 (the 10 nest eggs), OPEN runs the batch ("Egg 1 of 58", "Egg 2 of 58"), dinos listed afterwards | PASS | 08, 09, 10, 12 |
| 6 OPEN loop: DIFFERENT from the script. OPEN starts ONE hatch party: Next egg stays inside the sequence (BD-170) until the batch ends; it does not return to the card after every egg. "Skip the rest" (176x48) and "Egg N of M" counter present (BD-444). The "Some eggs can crack!" line under the status pill was NOT looked for | PARTIAL | 10, 11, 12 |
| 7 AUTO opens Settings > Help with five rarity toggles; Common set to AUTO; OPEN once; a "Auto-opened eggs" summary lists counts per rarity ("56: 2 Rare, 17 Uncommon, 37 Common, 20 cracked", from the earlier Skip the rest) with COLLECTION / DONE | PASS (see the anomaly below) | 13, 14, 15 |

Not covered: 844x390 (phone-size) repeat of steps 1-3, a second player, a real save.

Anomalies (new rows): (a) with only Common on AUTO, a plain Common Gallimimus (no BIG, Shiny, mutation, Rainbow/Astra) was still shown as "Egg 8 of 11" while eggs before it were skipped: BD-525. (b) the first hatch of a session once drew the egg at the top-left of the screen instead of the panel centre: BD-519 (image in the BD-170 folder). (c) the "Tell us!" button covers the EGGS plate bottom-left once a run has ended (06, 07): BD-524.

Other rows seen in the same session (images here):
- BD-440: the first screen has no goal line (02, 16); the goal line ("Level 2: 60/300 XP", later "Gold: 4/6 Raptor") appears after the first run, not mid-run (06, 07).
- BD-441: no "Tell us!" on the first screen or during the run; it appears bottom-left once the run has ended (06). Phone not covered.
- BD-442: EXPLORE ISLAND reads "TAP TO GO!" with a lit rim on the first screen (16, 02).
- BD-094 / BD-169: nest slots draw the real nest icon, the egg card shows the bound jungle stage with the egg, chips, OPEN and AUTO (03, 07, 08).

## Round 2: phone-size repeat (836 x 390 game view, 2026-10-17)

How: Studio's MCP cannot set a device. `StudioDeviceEmulatorService` is not reachable from the command bar (the service lookup returns nil) and no tool changes the Device Emulator, so the Studio window itself was resized with SetWindowPos until the game view (`Camera.ViewportSize`) read 836 x 390 (about the 844 x 390 landscape phone). This tests the layout at that size with mouse and keyboard input only: `TouchEnabled` stays false, so the touch-only branches (bigger tap targets, the phone thumb controls) did NOT run. The real phone check stays with the owner (BD-085).

Scratch config: `NestIncubationSeconds = 20`. Real clicks throughout. Images 20 to 30 here.

| Script A step at 836 x 390 | Result | Image |
| --- | --- | --- |
| Hub first screen: rail is a top row (DINOS / EGGS / FUSION / SHOP / POTIONS / SETTINGS), Admin button covers its left end, "Gold ready:..." and GOALS chips stack over the weather chip, TAP TO GO bottom centre, Tell us! bottom left | PARTLY: usable, but chips overlap (BD-531) | 20 |
| 1 EGGS before any run: five "Empty" nests in one row, readable | PASS | 21 |
| 1 the egg card, "Go find eggs on the island!", EXPLORE ISLAND and AUTO "Auto-open: off" are below the fold (the screen scrolls) | PASS with a scroll (BD-531) | 22 |
| 2 empty slot tap: toast "Finish a run to earn a nest!" | PASS | 23 |
| 2 TAP TO GO / EXPLORE ISLAND: the run starts | PASS | 24 |
| 3 in a run: the EGGS plate (bottom left) is not on screen at this size, only HOME, SIZE bar, rail (MENU / POTIONS / SETTINGS) | FAIL, see BD-531 (seen in screenshots, not queried by property) | 24 |
| 3 HOME opens the confirm; GO HOME is below the fold (scroll) | PASS with a scroll | 25 |
| 3 Run Complete (eggs found, crystals, growth; 150-egg run adds "+5 nests") | PASS | 26 |
| 4 Eggs screen after the run: slot 1 "READY", slot 2 "20 s", slots 3 to 5 "Queued", "Eggs waiting: 150", READY! pill, egg card with chips, OPEN, AUTO | PASS | 27, 29 |
| 5 tap the READY slot: toast "Nest opened!", eggs waiting 150 to 162, slot 5 "Empty", slot 1 countdown | PASS | 28 |
| 6 OPEN: the first egg of the party was a Cracked egg: "Oops! Splat!" with "Egg 1 of 162" and "Skip the rest" | PASS | 30 |
| 6 the "Some eggs can crack!" line | NOT SEEN: it only shows after 2 hatched eggs and before 7 (`FtueP1.crackedHintShown`); this first run was in a session that had already hatched about 100 eggs, so the window was over (that is why the first egg here could be Cracked). A second phone-size run on a fresh profile was started but Studio's viewport stopped rendering (1 x 1 view, MCP "Connection closed") before it reached the third egg | - |

Left for BD-148: the "Some eggs can crack!" line (hatch 2 eggs, open the Eggs card, look under the status pill) and AUTO on the phone-size Help tab; the real phone.
