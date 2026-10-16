# 127 Phone QA kit (BD-085, BD-322; 2026-10-16)

Label: **TOOLING, no measurement yet.** This is the kit that lets the owner measure a real phone in one session; it contains no phone numbers. Budgets are the **PROVISIONAL** planning numbers of [107](107-offline-mobile-budget.md) section 1 and the FX ceilings of [123](123-anime-3d-fx-research-and-plan.md) / `EffectsLod`. It changes no gameplay and touches no profile, reward, nest, cosmetic, combat, hatch, telemetry, cave or goals logic.

## 1. What is in the kit

| Piece | File | Notes |
| --- | --- | --- |
| QA overlay (client) | `src/client/QaOverlay.client.luau` | fps, memory MB, instances, parts, emitters and particles/s, beams, lights, EditableImage MiB and live count, ping, dinos. Buttons: **Mark**, **Next step**, **Hide** (each at least 44 px tall). |
| Mark logger (server) | `src/server/QaService.luau` | Re-checks authorization, rate limits (0.5 s), validates and clamps the snapshot, prints one `[BD-QA] {json}` line. Creates nothing while the flag is off. |
| Pure rules | `src/shared/QaOverlayRules.luau` | who may use it, tour step labels, snapshot validation (label limited to `[A-Za-z0-9_ .-]`, 40 chars). |
| Report | `tools/qa/phone_report.py` | `[BD-QA]` lines to a table against the budgets (section 5). `--md` for markdown, `--strict` to exit 1 on a miss, `--selftest` in CI. |
| CI check | `tools/verify_qa_kit.py` | rules in Luau, flag off in Config, wiring, no gameplay modules touched, touch targets. |

Access (owner-only, default off): `Config.QaOverlayEnabled = false` and `QaOverlayUserIds = {}` in every committed build; `release_profiles.py` requires the flag false in **every** profile (default and playtest), so a measurement build is made **locally and never committed**. The overlay appears only if the flag is true **and** (unpublished Studio **or** the player's UserId is in `QaOverlayUserIds`). The place owner is not admitted automatically. The server never trusts the client attribute.

## 2. Owner runbook (about 45 minutes)

1. On your PC: in `src/shared/Config.luau` set `QaOverlayEnabled = true` and `QaOverlayUserIds = {<your UserId>}`. Run `python tools/build.py`, open the generated place, publish it to your **private** playtest experience (see the BD-004 playtest profile). Do **not** commit or push the change; `git checkout src/shared/Config.luau` afterwards.
2. Phone: join the private place. Note device model, Android version, RAM, graphics quality (Settings) in a text file.
3. Top right shows the overlay. Tap **Next step** until the step name matches where you are, then **Mark**. It says "Marked!" and the server writes the line.
4. Get the log: Studio "Server" output cannot see a published server; use the Creator Hub > Analytics > Logs / the in-experience **Developer Console** (F9 on desktop, Settings > Developer Console on phone) Server log tab, copy the `[BD-QA]` lines into `phone.log`. (In Studio, Test > Start with a local server the lines appear in Output.)
5. `python tools/qa/phone_report.py phone.log --md` and paste the table into this doc (section 6) and the BD-085 / BD-322 rows. Add screenshots of the Developer Console Memory tab and MicroProfiler per [107](107-offline-mobile-budget.md) section 5.

The overlay's own cost: one workspace scan every 5 s (yielding) and a 0.5 s text refresh. Expect a tiny hitch on the scan. Particles are a **proxy**: Roblox has no live particle count, so it shows enabled emitters and the sum of their `Rate` (rate x lifetime 0.5-1 s is about the live count). EditableImage values come from `LowPolyImagesMiB` / `LowPolyImagesLive` (workspace attributes, docs/107); hatch v2 bakes are not in that attribute.

## 3. Scripted tour (one mark per step)

Use a Phone-class viewport (short side under 600 px, 844x390 is the reference). Mark the idle state first, then perform the action and mark **while it is on screen**.

| # | Step label | Where to go | What to tap / do | What to look at |
| ---: | --- | --- | --- | --- |
| 1 | `start_hub` | Spawn in the hub | Wait 20 s, do not touch | baseline fps, memory, ping; join time by stopwatch |
| 2 | `run_start` | Hub | Tap the run / EXPLORE button, mark 5 s after the arena loads | memory jump, part count, fps |
| 3 | `food_field` | Arena spawn (0, 30), then the SW corner (about -160, -160) | Walk 10 s, then Mark at each spot (two marks with the same step label; note which spot is which in your file) | parts in range, fps at the worst spot |
| 4 | `egg_reveal_15` | End a run with eggs (or the playtest 15-egg run) | Mark mid-reveal while eggs open one by one | fps during hatch particles, EditableImage MiB |
| 5 | `rare_hatch` | Same reveal, the first Rare or higher egg | Mark when the rarity burst plays | particles/s, lights, fps dip |
| 6 | `goals_panel` | Hub | Open the **Goals** panel, mark with it open | fps, layout fits (section 4) |
| 7 | `peaceful_button` | Before a run | Look at the **Peaceful** button, tap it twice (ON/OFF), mark | target size (section 4) |
| 8 | `settings` | Hub | Open **Settings**, toggle Effects Full / Lite / Off, mark once at Full and once at Off | particles/s drop, fps gain |
| 9 | `sound_lab` | Settings (Sound Lab page, BD-343) | Open it if the build has it; else skip and write "not in build" | target size (section 4) |
| 10 | `class_picker` | Class picker line (BD-246/BD-247), only when `CombatEnabled` is on in a Studio build | Open and mark; else skip and write "not in build" | target size (section 4) |
| 11 | `shops` | Hub | Open Crystal Shop and Potion Shop, mark in each | fps, EditableImage MiB (previews) |
| 12 | `end` | Hub | Wait 10 min of normal play, mark | memory growth since step 1 (leak check) |

Extra counts from [107](107-offline-mobile-budget.md) section 5: repeat step 2 with 2, 6 and 12 dinos on screen (second and third phone/friends), and once with `LowPolyDinos` on (playtest profile) and once off.

## 4. Touch target and text checklist for new UI (docs/114: text at least 14 px, targets at least 44 px)

Tick on the phone (844x390 or smaller); a failed line becomes a bug on the matching BD row.

- [ ] **Peaceful button** (`PeacefulToggle`, hub and Settings): the whole button is at least 44 px tall and wide when measured on screen (not the design size); its helper line reads at 14 px or more; two taps toggle ON/OFF without hitting a neighbour.
- [ ] **Goals panel** (BD-427): the open/close control and each line are at least 44 px; no line is cut at the right edge; the panel does not cover LEAP, the weather timer or the run HUD; scrolls if taller than the screen.
- [ ] **Sound Lab** (BD-343): every play / pick button at least 44 px with 8 px between them; labels 14 px or more; it can be closed with one tap.
- [ ] **Class picker line** (BD-246): each class choice at least 44 px; the selected state is readable without colour alone; it does not overlap the Peaceful button.
- [ ] **QA overlay itself**: Mark, Next step and Hide are 48 / 48 / 44 px (checked by `verify_qa_kit.py`), the readout is 14 px.

How to measure on a phone: screenshot, the screenshot is at device pixels; Roblox UI px are device-independent, so also compare with `PhoneScale` (`MinText` 14, `MinButton` 44, [114](114-handbook.md) section 8.2). A control that renders smaller than a thumb pad (about 7 mm) fails even if it passes by pixels.

## 5. Budgets used by the report

fps at least 30; memory at most 1,200 MB; parts at most 3,000 (whole workspace, a strict reading of the 107 rule); emitters at most 40 (PROVISIONAL); particles per second at most 300 (107 live particles about 300); beams at most 24 (123 T3, 3-4 per dino, Lite 6 dinos, PROVISIONAL); lights at most 16 (107, 104); EditableImage at most 24 MiB (`verify_world_budget.py`; the engine budget is 80 MiB, 105); ping at most 250 ms round trip (an assumption, 107 has no ping number). These live in `BUDGETS` in `tools/qa/phone_report.py`; the limits present in `tools/qa/phone_budgets.json` (the single phone-budget file, currently lights and beams) override them at load time, so change those there. When BD-085 returns real numbers, change them there and in 107 together. Not captured (use Developer Console / MicroProfiler): triangles, draw calls, network KB/s, Highlight count (engine cap 31, 123 T6).

## 6. Results

None yet. Paste the `phone_report.py --md` table here after the owner's session, with the device line.

## Handbook check

- 114 section 8.2 (UI bar): overlay text 14 px, buttons 44 px or more; it is a developer tool in plain Theme styling like the admin panel (72 applies to player UI).
- 114 / AGENTS.md: no gameplay, economy, save, Robux, nest, cosmetic, combat, hatch, telemetry, cave or goals change; no art asset added.
- Flags: `QaOverlayEnabled` is false in Config and pinned false in default and playtest profiles (`release_profiles.py`, `verify_release.py`).
- 107: budgets are the section 1 rules of thumb, labelled PROVISIONAL; this doc claims no measurement and does not close BD-085 or BD-322.
