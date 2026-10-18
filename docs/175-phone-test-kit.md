# 175 Phone test kit: measure the old phone in about 30 minutes (BD-1004, 2026-10-18)

Label: **KIT AND TOOL, no measurement yet.** Nothing here was run on a phone. No game code, flag, profile or build was changed. Written for the owner (sections 1 to 6, plain words) and the lead (sections 7 to 10). Every number in the lights is **PROVISIONAL** until this very run settles it (BD-085, BD-322). Anything I could not confirm is marked **UNVERIFIED**. Related: [146 phone forecast](146-phone-forecast-2026-10-17.md), [107 budget](107-offline-mobile-budget.md) s5, [127 QA overlay](127-phone-qa-kit.md), [148 publish runbook](148-publish-runbook.md), [167 playtest report](167-reference-and-playtest-tools.md), [147 streaming](147-streaming-experiment-2026-10-17.md).

## 0. The short answer

1. The phone run is **three jobs**: (a) set the phone up once (about 10 minutes), (b) play the 12-step script (about 12 minutes), (c) fill in the form and send it with 4 screenshots (about 8 minutes).
2. You need **no developer tools** on the phone. Every number is read off the screen with Roblox's own "Performance Stats" and the chat command `/console`.
3. The lead runs `python tools/phone_session_form.py phone-form.txt`. It writes the evidence file `docs/evidence/<date>-phone-session/README.md` with green / yellow / red lights, and says what to do next for every light that is not green.
4. **Before any of this, the playtest place must be published** (docs/148 steps 1 to 3). Today nothing is published, so the phone has nothing to join. That is an owner job and it is not part of this kit.

## 1. What the lead does first (the owner does not need to read this)

| Lead job | Why |
| --- | --- |
| Check the published place is the playtest build (`ReleaseProfile` = playtest) and tell the owner its `BUILD redesign-NNN` label. | The form asks for the label; a wrong build makes every number useless. |
| Make sure the phone is the **only player** on the server during the run. | The server log has no user id and no device (privacy by design, [167](167-reference-and-playtest-tools.md) s5). With one player, every log line is the phone. |
| Copy the server log **before the server closes** (Developer Console > Server Logs, [167](167-reference-and-playtest-tools.md) s6). | The log is gone afterwards. |
| Optional second round: a **measurement build** with `QaOverlayEnabled` on ([127](127-phone-qa-kit.md) s2). | Only this gives parts, lights, emitters and per-step marks. It needs the owner to publish a special place and the flag is **never committed**, so it is a separate owner approval. The form tool reads its `[BD-QA]` lines with `--qa-log`. |

## 2. Setup on the phone (once)

Mark: **UNVERIFIED** means nobody has done this step on a phone yet; if the screen looks different, write down what you see instead.

1. **Charge the phone to at least 80%** and close all other apps. Turn Wi-Fi on (write "Wi-Fi" or "mobile data" in the form).
2. **Install Roblox** from Google Play (the real app, not an emulator). Open it once and update it if it asks. Write down the app version (your phone's Settings > Apps > Roblox > version).
3. **Log in with your own account** (the account that owns Be Dino). The owner of a private experience can play it; friends can only play after you add them as playtesters (docs/148 step 2). **Type your password only into the Roblox app.**
4. **Find the game.** Easiest (UNVERIFIED): on the PC open Creator Hub > Creations > the experience, copy the experience link, send it to yourself (email or chat), open it on the phone and tap Play (it opens in the Roblox app). Other ways: Roblox app > Home > "Recently played", or your profile > Experiences (UNVERIFIED).
5. **What the experience page must allow** (Creator Hub, docs/148 step 2): Access is Private or Limited with the tester added; **Devices must include Phone** (docs/148 says "Computer only" for the first desktop session, docs/55 and docs/125 say "Computer and Phone": for this test tick **Phone** as well); Allow Mesh & Image APIs on; max players 4; no products or passes. Whether the creator can still join from a device that is not ticked is **UNVERIFIED**, so tick it.
6. **Which experience?** `src/shared/Config.luau` records universe 10769812255, place 111259822927673, named "newbuild", written 2026-10-14. `tools/release_ids.json` is still empty and docs/148 asks the owner whether that one is the old Build 019 test experience. **UNVERIFIED:** which one the phone should join. The lead tells you the name; the in-game `BUILD` label at the top must match what the lead wrote.
7. **Switch on Performance Stats** (UNVERIFIED on a phone): once in the game, tap the Roblox menu button (top left), open **Settings**, switch **Performance Stats** on, close the menu. A small panel should show numbers. Web guides disagree on which numbers it shows on a phone (memory, CPU and GPU milliseconds, network, ping; maybe no frames per second). So the form takes **either** "fps" **or** "frame ms" (the biggest of the CPU and GPU ms numbers); the tool turns ms into fps (1000 / ms).
8. **Find the console** (UNVERIFIED): type `/console` in the chat. docs/55 says that opens the Developer Console on a phone; docs/127 says Settings > Developer Console. Open its **Memory** tab and find the **Total** number. If neither works, write "no console" in `notes` and use the Performance Stats memory number.
9. **Practice the screenshot** (on most Android phones power + volume down, UNVERIFIED for yours). Screenshots land in your gallery.
10. **Open the form** (section 6) on the PC; you fill it in from your notes after the run.

## 3. The 10-minute script (12 steps)

Play with the phone in your hands like normal. Use a stopwatch or the phone clock. After each step write the numbers on paper or in a notes app. **For every speed number, watch the panel for 10 seconds and write the LOWEST number you saw.** If you could not read it, leave it empty. Never guess.

| # | Step | What to do | Write down |
| ---: | --- | --- | --- |
| 1 | **Open** | Note the battery %. Start the stopwatch, tap Play. Stop it when you can move the dino. Then switch Performance Stats on (section 2 item 7). | `join_seconds`, `battery_start_pct`, `build_label` (the small blue text starting BUILD at the top), `ping_ms` |
| 2 | **Spawn** | Stand still where you appear (the cave) for 20 seconds. | `spawn_fps` (or `spawn_frame_ms`), `memory_mb_spawn`. **Screenshot 1** with the panel visible. |
| 3 | **Move** | Walk in a circle with the joystick, jump, turn the camera with the other thumb. 20 seconds. Look at the buttons and words. | `taps_ok` (yes / some / no), `words_ok`, `freezes` so far |
| 4 | **Eat for 2 minutes** | Walk into the glowing gate to start a run. Eat food for 2 minutes and keep moving. At about 1 minute, read the numbers. | `food_fps`, `memory_mb_food`. **Screenshot 2** while many food bits are around. |
| 5 | **Hatch** | End the run (tap HOME) so the eggs open one by one. Watch the numbers while they open. | `hatch_fps`, `memory_mb_hatch`. **Screenshot 3** during the hatch. |
| 6 | **Fusion** | Tap FUSION on the left. Look at it for 10 seconds, close it. | `opened_fusion` (yes / no). Any cut-off words? |
| 7 | **Objectives** | Open the tasks / goals button (the small pill at the top; its exact label is **UNVERIFIED**). Read one line, close it. | `opened_objectives` |
| 8 | **Dinos menu** | Tap DINOS. Scroll. Open one dino. Close. | `opened_dinos` |
| 9 | **Shop** | Tap SHOP. Scroll two tabs. Close. | `opened_shop` |
| 10 | **Weather event** | Look at the weather timer on the screen. If a weather event starts while you play, read the numbers during it. If none came in about 10 minutes, write "no". | `weather_seen`, `weather_fps` |
| 11 | **Cave hub** | Tap HOME to go back to the cave. Stand in the middle for 20 seconds. | `cave_fps`; any lights that look wrong go in `notes` |
| 12 | **Leave** | Read memory and battery. Type `/console`, open the Memory tab, take **Screenshot 4**. Touch the back of the phone. Then Roblox menu > Leave. | `memory_mb_end`, `battery_end_pct`, `temperature_feel` (cool / warm / hot), `minutes_played`, `crashed` |

If the game **closes by itself** at any step: write the step number in `crash_when`, set `crashed: yes`, and stop. That is a result, not a failure of yours. Join again once; if it crashes a second time at the same step, write that down too.

## 4. What to write down (and why)

| Item | Why the lead needs it |
| --- | --- |
| Device model, Android version, RAM (GB), Roblox app version | A result only means something for this kind of phone ([107](107-offline-mobile-budget.md) s1: about 3 GB, 2019 to 2021). |
| Battery at start and end, how warm the phone felt | Cost of the frame rate and effects (docs/55 s3 Android checklist). |
| Graphics quality setting, Wi-Fi or mobile data | Both change the numbers a lot. |
| Freezes (picture stops 2 seconds or more), and when | Tells which feature causes it. |
| Crash yes or no, and at which step | A crash at the start and a crash after 10 minutes have different causes (section 7). |
| 4 screenshots | The proof. Without them the numbers are your word only. |

**The 4 screenshots:** (1) the start with Performance Stats on, (2) the food field with Performance Stats on, (3) the egg hatch with Performance Stats on, (4) the console Memory tab with the Total visible. Name the files in `screenshot_1` to `screenshot_4` of the form.

## 5. Which numbers can be read, and where

### 5.1 On the phone (read by you, no developer tools)

| Number | Where | Status |
| --- | --- | --- |
| Frames per second or frame milliseconds | Roblox menu > Settings > Performance Stats | **UNVERIFIED** on mobile. The documentation I found says the panel shows memory, CPU, GPU, network and ping; some guides add FPS. Hence the `_frame_ms` lines. |
| Memory (MB) | Performance Stats, or `/console` > Memory > Total | **UNVERIFIED** on a phone. |
| Ping | Performance Stats | **UNVERIFIED**. |
| Join time | Stopwatch | Certain. |
| Battery, heat, freezes, crash | Your phone and your eyes | Certain. |
| Whether buttons are covered or words cut off | Your eyes plus the screenshots | Certain (BD-994 asks for exactly this at 640 x 360). |

**Not readable without a measurement build:** parts in the world, triangles, draw calls, lights, beams, emitters, particles. docs/146 s7 asks for parts and triangles; on a phone only the QA overlay ([127](127-phone-qa-kit.md)) can show parts, lights, emitters and a particle proxy. The F9 / MicroProfiler hint of docs/107 s5 is a **desktop** key; its phone equivalent is UNVERIFIED and **not needed** for this kit. Triangles stay unmeasured on a phone.

### 5.2 On the server (the lead reads, per visit, no names)

Run `python tools/playtest_report.py server.log counts.csv`. With the phone as the only player, one visit is the phone ([167](167-reference-and-playtest-tools.md) s5b, s9):

| Number | Meaning for the phone |
| --- | --- |
| `first_food_s`, `first_run_s`, `first_egg_s`, `first_hatch_s`, `first_shop_s` | Seconds from joining to each step. Slow numbers here and a slow `join_seconds` point the same way. |
| `total_s`, `runs`, `hub_s`, `run_s` | Did the 12-minute session really run; how long in the cave. |
| `movement_rejects` (`MovementGuard` sets the player attribute `MovementRejectCount`, `TelemetryService` counts it) | Anti-cheat set-backs. A touch joystick can differ from a keyboard: more than 0.5 per visit is yellow (BD-611). |
| `rate_limited` per service | Buttons pressed too fast (touch double taps). |
| `script_errors` with the text | Real server errors. |
| `hatches`, `fusions`, `shop_purchases` | Proof that steps 5, 6 and 9 happened. |
| `crashes`, `shop_opens` | The game cannot see these; `phone_session_form.py` writes them into `counts.csv` from your form. |

**Not in the log:** frame rate, memory, device, battery. The server does not know any of it.

## 6. The form (one page) and how to send it

Fill in the file below (key: value lines). Lines starting with `#` are hints. Empty means "not read" and shows grey, never green. Save it as `phone-form.txt`. (`python tools/phone_session_form.py --template` prints the same text; a test keeps the two equal.)

```text
# Be Dino! phone session form (docs/175). Fill in after the 10-minute script. Lines starting with # are hints.
# Write numbers only (units are fine). If you could not read something, leave it EMPTY. Never guess.
# Save as phone-form.txt and send it with the 4 screenshots.

# --- the phone ---
date:
tester:
device_model:
android_version:
# How much memory the phone has, in GB (Settings > About phone). Leave empty if you cannot find it.
ram_gb:
roblox_app_version:
# The small blue text at the top of the game screen that starts with BUILD.
build_label:
# Roblox Settings > Graphics: Automatic, or a number.
graphics_quality:
# Wi-Fi or mobile data.
network:
battery_start_pct:
battery_end_pct:
minutes_played:
# cool, warm or hot (how the back of the phone felt at the end).
temperature_feel:

# --- speed numbers (switch on Performance Stats first; write the LOWEST number you see for 10 seconds) ---
# Seconds from tapping Play until you can move the dino. Use a stopwatch.
join_seconds:
ping_ms:
# Frames per second at each spot. If your stats show milliseconds instead, use the _frame_ms line (the biggest ms number).
spawn_fps:
spawn_frame_ms:
food_fps:
food_frame_ms:
hatch_fps:
hatch_frame_ms:
cave_fps:
cave_frame_ms:
weather_fps:
weather_frame_ms:
# Memory in MB (Performance Stats memory number, or the Total on the console Memory tab).
memory_mb_spawn:
memory_mb_food:
memory_mb_hatch:
memory_mb_end:

# --- problems ---
# How many times did the picture stop for 2 seconds or more?
freezes:
freeze_notes:
# yes or no. Did the game close by itself, or throw you out?
crashed:
# join, run, hatch, menu, other (only if crashed is yes).
crash_when:
# yes, some or no.
taps_ok:
words_ok:

# --- what you did (yes or no) ---
weather_seen:
opened_shop:
opened_fusion:
opened_objectives:
opened_dinos:

# --- screenshots: write the file name of each one ---
screenshot_1:
screenshot_2:
screenshot_3:
screenshot_4:

# --- anything else, in your own words ---
notes:
```

**Send:** `phone-form.txt` and the 4 screenshots, in the chat (or email them to yourself and drop them in the project folder `docs/evidence/<date>-phone-session/`). Add the server log if you copied it. **The lead then runs:**

```
python tools/phone_session_form.py phone-form.txt                       # README.md + counts.csv in docs/evidence/<date>-phone-session/
python tools/phone_session_form.py phone-form.txt --qa-log phone.log    # with a measurement build's [BD-QA] lines
python tools/phone_session_form.py --template > phone-form.txt          # a fresh blank form
python tools/playtest_report.py server.log docs/evidence/<date>-phone-session/counts.csv
```

## 7. What each result means (decision table, lead)

Nothing here flips a flag or changes code. Every lever is a **decision for the lead** (record it as a LEAD decision in [115](115-decisions-log.md)); levers marked **NEW ROW** do not exist as a setting today.

| Result | Most likely reason | What the lead considers | Rows, flags, docs |
| --- | --- | --- | --- |
| **Speed below 30 at spawn** (the cave hub) | Too many lights or parts for the chip | Check the cave guards ran (12 lights, 4 beams); then lower the phone radius 190 to 160; **turn the phone food radius down** | `WorldCulling.FoodRadiusFactor` is 1.25 for **every** device class, so a phone-only value is a **NEW ROW**. BD-085, BD-495, docs/146 s1 levers |
| **Below 30 while eating** (food field) | Props and food parts in range; the triangle estimate (1,630 per generated mesh) may be too low | Phone radius 160 or 140 (-23% or -38% triangles); shrub and groundcover x0.75; food pooling | BD-322, BD-498 (food pooling plan, not built), `WorldCulling.Phone.radius`, `WorldArtDensity`, docs/146 risk 2 and 4 |
| **Below 30 only at hatch** | Hatch particles and the rare-hatch effects | Try Settings > Effects Lite and Off and write the gain; Lite as the phone default is a decision; pause weather during the reveal | BD-322, docs/146 risk 5 (b), `EffectsLod` |
| **Below 30 only in the cave** | 30 cave lights, 4 shadow lights, shaft beams | Confirm BD-495 worked (12 lights on, 4 beams); "0 shadow lights" is not built | BD-293 stays open, docs/146 risk 3 and s10 |
| **Below 30 only in weather** | Weather particles | Phone density is already 0.25 (BD-497); lower again or pause in menus | BD-497, docs/146 risk 5 |
| **Memory over 900 MB (yellow) or 1,200 MB (red)** | Textures: shipped dino textures are the biggest item (224 MiB for 6 species at RGBA8) | Dino textures at 512 px for phones, fewer species in view, build shop tabs on open; then the streaming flip | docs/146 risk 1, BD-502, docs/147 |
| **Memory grows more than 150 MB (yellow) or 300 MB (red) from step 2 to step 12** | Textures never freed (hatch, shops, Fusion) | Repeat and note what was open; find the leak | docs/107 s5 item 3, BD-322, `LowPolyImages*` attributes |
| **Crash at join** | Join memory, or the 8,600 parts that replicate at join | **Check streaming**: BD-502 gate 1 and docs/147 (default streaming alone is worse, it needs the three BD-506 fixes); food pooling; texture memory | BD-502, BD-506, BD-498, docs/146 risk 1 and 2. A crash is a P0 row; phone friends stay out (docs/125) |
| **Crash later** (after hatch, shop or Fusion) | Memory growth | Read the memory growth line and the console screenshot | docs/146 risk 1, BD-322 |
| **Join time over 120 s (red)** | Parts at join | Food pooling (join 7,061 to 4,383); streaming (about -50% at join in Studio, unproven on a phone); check the load gate | BD-498, BD-502, BD-210 |
| **Freezes** | Depends on the step | Write the step; a freeze at hatch is effects, at the start is loading | BD-085, BD-322 |
| **Battery over 10 points or a hot phone** | Frame rate and particles | Effects Lite as the phone default; a frame-rate cap | **NEW ROW**; BD-322 |
| **Ping over 250** | Probably the network | Repeat on another network; if only in the game, read join replication | docs/107 s4 |
| **Buttons covered or words cut off** | HUD pieces overlap on a small screen | Send the screenshot | BD-994 (P2, raise to P1 if it fails at 640 x 360), docs/127 s4, docs/72 |
| **Server: `movement_rejects` over 2 per visit** | The movement window and a touch joystick | Do not loosen the window without margins; repeat with a lag test | BD-611, docs/145 |
| **Server: `rate_limited` over 5 per visit** | Double taps on touch | Look at which service | BD-650 |
| **Everything green or yellow, no crash, 4 screenshots** | The old phone copes | The lead may propose a LEAD decision to allow phone friends and tick Phone; BD-085 and BD-322 can move to Review / test **with this evidence**; BD-293 also needs 12 players | BD-085, BD-322, BD-293, docs/125 |

## 8. The lights (one named table)

The table is `THRESHOLDS` at the top of `tools/phone_session_form.py`. Change a number there, nowhere else. Memory and parts read `tools/qa/phone_budgets.json` (`phone.memMb` 1,200, `phone.parts` 3,000) when it is present.

| Check | GREEN | YELLOW | RED |
| --- | --- | --- | --- |
| Speed at start, food, hatch, cave, weather | 30 fps or more | 24 to 29.9 | under 24 |
| Most memory seen | up to 900 MB (75% of 1,200) | up to 1,200 | over 1,200 |
| Memory growth, step 2 to step 12 | up to 150 MB | up to 300 | over 300 |
| Time from Play to moving | up to 60 s | up to 120 | over 120 |
| Ping | up to 150 ms | up to 250 | over 250 |
| Parts (measurement build only) | up to 3,000 | none | over 3,000 |
| Freezes | 0 | 1 to 2 | 3 or more |
| Game closed by itself | no | none | yes |
| Battery used (about 10 minutes) | up to 5 points | up to 10 | over 10 |
| Phone warmth | cool, normal | warm | hot |
| Buttons easy to tap / words readable | yes | some | no |

Overall: **RED** if any red (a crash is always red); else **YELLOW** if any yellow; else **GREY** if fewer than 3 of the 6 speed and memory readings were filled in; else **GREEN**. Every limit is a PROPOSAL or a copy of a docs/107 or docs/146 rule; none is an owner decision. The 30 fps floor is from docs/146 s7 and `tools/qa/phone_report.py`.

## 9. Mismatches and unverified points (for the lead)

- **Which experience?** `Config.luau` (PlaytestUniverseId 10769812255, "newbuild", 2026-10-14) and docs/125 s6 treat it as the playtest experience; docs/148 step 1 asks whether it is the old Build 019 one, and `tools/release_ids.json` is empty. This kit does not decide it; it is already docs/148 step 1.
- **Devices:** docs/148 step 2 says "Computer only" for session 1; docs/55 s4 and docs/125 say "Computer and Phone". This kit needs Phone ticked.
- **Console:** docs/55 says `/console` in chat; docs/127 says Settings > Developer Console on a phone. Both UNVERIFIED on a phone.
- **Performance Stats on mobile:** UNVERIFIED (section 5.1). The tool accepts fps or ms because of it.
- **Food radius:** the task brief says "phone food radius factor"; in source there is one `FoodRadiusFactor` (1.25) for all classes.
- No phone, Studio or Roblox website was used. One web search on 2026-10-18 was read for the Performance Stats panel only.

## 10. Handbook check

- 114 s0 and s12: plain words in the owner sections; the decision table is for the lead; nothing about feel is changed.
- AGENTS.md: no game code, flag, profile, economy number or asset changed; paid lines and `QaOverlayEnabled` stay off; no Studio or phone acceptance is claimed. The tool is offline and tested with in-memory forms only (`tests/test_phone_session_form.py`).
- Privacy: the form holds a device model and `tester`; no password or user id is asked for.
