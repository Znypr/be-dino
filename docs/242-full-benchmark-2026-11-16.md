# 242 Full benchmark vs top Roblox games (BD-1216 to BD-1235), 2026-11-16

Owner 2026-11-16: "compare every aspect of the game with famous roblox experiences, also sound effects, loading screens, map designs, assets, animations, rigging, ui, shops, etc." Owner, same day: "only compare the current data though like the proposed ones. dont get confused with old when we have new proposed changes already for it."

This page extends the standing benchmark [235](235-top-games-benchmark.md) and does not repeat it: 235 holds the retention table, and this page covers every aspect. **Be Dino side = the newest state:** main, plus PR #599 (World V3 island, landmarks, hatch stage) and PR #601 (HUD on the style tile), plus the proposals already on the board ([228](228-ui-toybox-proposal.md) Toybox UI, [240](240-cohesion-style-bible.md) style rules, [241](241-world-redesign-proposal.md) world rules). A gap that one of those already fixes is marked **covered** and is not counted again.

## Method and limits (read first)

- **Top games:** 11 YouTube videos (2025-2026) of Pet Simulator 99 (PS99), Grow a Garden (GAG), Adopt Me! (AM), Bubble Gum Simulator INFINITY (BGSI), Steal a Brainrot (SAB), Ride a Dino (RAD) and Steal an Egg (SAE), watched in the built-in browser as stills (2-5 seeks each). I also looked at the owner's local sheets in `be-dino-reference-shots` but did not copy them. **Not judged:** any audio (no sound was heard), motion timing (shake counts, idle and walk cycles), loading screens (every video starts in game), the first minute of PS99, BGSI and SAB, and Bee Swarm and Fisch (not watched). Sources are in section 3.
- **Be Dino:** playtest build of the PR #599 branch (`9ec2438b`, which already contains main up to #600), opened in Studio on 2026-11-16. Pictures are in `docs/evidence/2026-11-16-benchmark/`. The HUD look comes from PR #601's own capture (`docs/evidence/2026-11-16-hud-cohesion/after-hud-world.jpg` on that branch), and the hatch from PR #599's (`docs/evidence/2026-11-16-hatch-fullscreen/`). Sound comes from the code (`src/shared/Sfx.luau`, a live check of every sound playing), **not heard**. No phone was used.
- The playtest flags that are on were read live from Config in Studio. Among them: Objectives, StarterRun, WelcomeBack, PlayAgain, RareFindBanner, MotionPresets, ToyboxUI, FoodV3, WorldV3, HatchStage and ScreensCohesion. All paid lines are off.

## 1. Aspect by aspect

Severity: **High** = a player notices in the first minute, **Med** = notices within a session, **Low** = polish.

| # | Aspect | Top games do (source) | Be Dino newest (picture) | Gap | Sev | Fix (row) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | First 60 s | Teach by pointing at the thing: key chip, hand icon or sign on the object, almost no windows (AM-A t=60/240, GAG-A t=3-60, SAE sheet) | Lands on sand with "Eat food to grow" under the size bar (`02-first-spawn-hud.jpg`); StarterRun and Welcome are on | The hint is a line of HUD text, and nothing in the world points at the first food, the nest or a stall | Med | BD-1226 |
| 2 | Loading screen | Not captured in any video | Logo, mascot and a cream bar on green (`01-loading.jpg`, matches style rule R1) | Clean but plain: no scene art, no tip | Low | BD-1232 |
| 3 | Map: shape and readability | One colour family per zone, wide flat paths, huge signs (GAG, AM, SAE) | Round island, ring road, spokes and 4 landmarks read well (`04-island-mid-height.jpg`) | **Covered** by #599 / 241 for shape, paths and landmarks. Left: the sea is a flat pale square plate with a hard corner and thick haze from above (`03-map-from-above-haze.jpg`) | High | BD-1220 |
| 4 | Map: hub | Spawn among labelled shops (AM plaza, GAG stalls, PS99 hub) | The plaza is an empty sand circle; every shop sits behind HOME | No place to walk to; the shops are invisible in the world | High | BD-1221 (extends BD-1181) |
| 5 | 3D art consistency | One art rule per game (all blocky or all glossy-round) (GAG, AM, PS99) | Glossy round trees and bushes, faceted spiky fronds, photo-real sand and grass textures, cartoon landmarks (`05-ground-view-mixed-styles.jpg`) | Three styles on one screen | Med | BD-1223, BD-1224 |
| 6 | Food | Oversized, readable pickups (GAG fruit) | **Covered**: V3 food from the icons with a glow outline (`06-food-v3-close.jpg`, PR #598) | Still small next to a grown dino; watch in the phone check | Low | BD-1222 |
| 7 | Hero dino model | Cute rounded pets with big eyes; strong silhouette per species (AM, PS99) | Faceted green low-poly figure with blank black eyes (`07-player-dino-lowpoly.jpg`); the reveal shows the same style | **Biggest look gap**: the owner's V3 dino lineup exists (memory, docs/77) but the game does not use it | High | BD-1216 |
| 8 | Rig and animation | Rigged pets with real clips (follow, idle; timing not judged from stills) | Rigid parts moved by weld offsets (LowPolyAnimator, DinoMotion: footfall bob, eat peck, jump squash). The live check shows the default human R15 idle running under the hidden avatar | No skinned rig, no clips, no happy or emote pose | High | BD-1217 |
| 9 | Hatch and reveal | Short, in the world, beams plus a big coloured rarity word; Open 1/3/8 with a confirm (PS99-C t=60-69); public odds (AM-B t=300) | **Covered**: full stage with paint frames, rarity ribbon, pedestal, name plate, NEW badge and Skip (#599 `in-game-reveal-rare.jpg`), batch hatch, fast commons, Play again, odds in kid words | We chose a full-screen stage (owner-approved) where hits use in-world. Keep the stage but keep it short. The dino on the pedestal is still the stand-in (row 7) | Med | BD-1216 (no new hatch row) |
| 10 | HUD | One fixed frame: nav left, currency bottom-left, quests right, event top-centre; thick-outlined words (PS99-A t=70, AM-A t=60) | **Covered**: cream plates (PR #601), weather chip, goal line, LEAP / CHOMP; tile rail and wallet pill proposed (BD-1180) | None beyond BD-1180 | - | - |
| 11 | Menus, popups, toasts | Red X on every window, coloured tabs, big outlined text (BGSI t=40, SAB t=60) | **Covered** by the Toybox kit and the docs/240 steps (Crystal Shop and Potions pass, toasts in step 4) | None new. **Corrected 2026-11-17 by [243](243-menus-like-top-games.md):** our windows follow our own style tile, not the top games' menu look (owner) | - | BD-1252 |
| 12 | Shops and money | Price on the button, Owned label, one offer per row, odds visible. **Do not copy:** fake crossed-out worth prices, pay-to-skip timers, revive offers at a loss, flashing pack timers (SAB t=60, GAG-A t=110, RAD sheet) | Crystal Shop with tier cards and price on the button; paid lines off by rule | **Covered** (the kid-safe rules already ban the bad ones). Shop shelves are thin (3 cards a tab), which is content, not a look gap | Low | - |
| 13 | Sound effects | Not judged (no audio heard) | 27 cue slots: 13 filled, **14 empty and silent** (hatch rattle and burst, all 7 mutation reveals, rare fanfare, crystal cue, nest open, soft defeat, cracked fail). The dino plays Roblox's **human** footsteps | Key moments are silent and steps sound wrong. Not heard by me | High | BD-1219 |
| 14 | Music and ambience | Not judged (no audio heard) | **No music at all**: zero looped sounds playing in the live check; only weather has beds | Silence between cues reads as empty and boring | High | BD-1218, BD-1225 |
| 15 | Feedback and juice | Numbers are the juice: big +numbers rising, word banners ("GREAT RUN!"), beams (SAE sheet, RAD t=150-300, SAB t=420) | "+3 Crystals" labels, motion presets on, crystal fly-to-wallet proposed (BD-1180 / BD-1182) | Eating gives no number at the dino; growth feels silent | Med | BD-1231 |
| 16 | Progression and goals | Quest list on the right with fractions, an Index with locked "????" silhouettes (PS99-A t=70, PS99-C t=330) | Objectives on, goal line under the size bar, Index with progress; daily and playtime rows exist (BD-1197, BD-1198) | No Index milestone reward and no locked silhouettes (235 lists it missing) | Med | BD-1230 |
| 17 | Social moments | Server-wide "X hatched Y!", friend boost label, co-op events (PS99-A t=100-240, SAE t=260, GAG-B) | Other players see you as a dino; the rare-find banner shows your own finds; no friend bonus | Nothing tells you what others hatched; no reason to bring a friend | Med | BD-1227, BD-1228 |
| 18 | Retention loops | Timers, an offline banner at login, group rewards, codes (PS99-A t=100, SAE / RAD sheets) | Welcome back, weather timer, 3 h nests, Play again; daily (BD-1197) and playtime (BD-1198) planned | No badges, no codes or group chest, no "egg ready" notification | Med | BD-1229, BD-1233, BD-1234 |
| 19 | Phone | Same frame on phone, big tap targets, dense text is the weak spot (GAG-C t=120) | 6,969 parts and 3,600 food items in the World V3 build; **never measured on a phone** | Unknown frame rate and memory risk | High | BD-1222 |

## 2. Ranked backlog (added 2026-11-16, all Backlog)

1. **BD-1216 (P1)** Real V3 dinos in the game (player plus collection)
2. **BD-1217 (P1)** Rig and 6 calm clips (idle, walk, run, jump, eat, happy)
3. **BD-1218 (P1)** Background music (island, home, softer under the hatch)
4. **BD-1219 (P1)** Fill the 14 silent cues, dino footsteps
5. **BD-1220 (P1)** Real sea, no square edge, less haze from above
6. **BD-1221 (P1)** Spawn plaza as a hub with stalls and big signs
7. **BD-1222 (P1)** Phone check of World V3 with numbers
8. **BD-1223 (P2)** One ground style (toon colours)
9. **BD-1224 (P2)** Retire the spiky flat-shaded plants
10. **BD-1225 (P2)** Ambient sound per zone
11. **BD-1226 (P2)** Point at the thing (chips on first food, nest, stall)
12. **BD-1227 (P2)** Rare hatch news for the server
13. **BD-1228 (P2)** Friend bonus
14. **BD-1229 (P2)** Badges
15. **BD-1230 (P2)** Index milestones and locked silhouettes
16. **BD-1231 (P2)** Growth number pop
17. **BD-1232 (P3)** Loading scene plus a tip
18. **BD-1233 (P3)** Codes and group gift chest
19. **BD-1234 (P3)** "Egg ready" notification
20. **BD-1235 (P3)** Listening pass of the top games

Why this order: the hero dino and the silence are what a player meets in the first 10 seconds, and nothing on the board covers them yet. The world fixes come next, after #599 lands. Social and retention items need the core to look right first. Every row is flag-gated and PROVISIONAL where it has numbers, and none touches Robux.

## 3. Sources (watched 2026-11-16, stills only)

| Short | Game | URL | Seeks used |
| --- | --- | --- | --- |
| PS99-A | Pet Simulator 99 | https://www.youtube.com/watch?v=l50r07rKkYg | t=60-240 (confirm modal, 8-egg hatch, HUD, server hatch lines) |
| PS99-B | Pet Simulator 99 | https://www.youtube.com/watch?v=xkuXk56CflU | t=45, 200, 420 (machine panel, toast, trophy board) |
| PS99-C | Pet Simulator 99 | https://www.youtube.com/watch?v=mg_tER6-zms | t=60-69 (Open 1/3/8, beams), 330 (Index silhouettes), 600 (exclusive shop) |
| GAG-A | Grow a Garden | https://www.youtube.com/watch?v=n3WqE8Pzf8M | t=3-110 (start, stalls, seed shop) |
| GAG-B | Grow a Garden | https://www.youtube.com/watch?v=AVPtMhPUlmI | t=5-550 (HUD trio, egg on plot, friend boost) |
| GAG-C | Grow a Garden | https://www.youtube.com/watch?v=7dOSBWhSctM | t=120 (phone layout) |
| AM-A | Adopt Me! | https://www.youtube.com/watch?v=8_o1yHffHss | t=8-240 (plaza, right button column, tap hints) |
| AM-B | Adopt Me! | https://www.youtube.com/watch?v=efbCS3mkoMM | t=60-500 (egg price popup, odds panel, newborn pets) |
| BGSI | Bubble Gum Simulator INFINITY | https://www.youtube.com/watch?v=yc5wXJvGP4Q | t=40-700 (pass grid, hub, panels) |
| SAB | Steal a Brainrot | https://www.youtube.com/watch?v=P0W_sV66aw0 | t=60-420 (shop tabs, floor text, collect pads) |
| RAD | Ride a Dino | https://www.youtube.com/watch?v=PIet23DxjZc | t=60-300 (voxel dinos, word banners, goal bar) |
| SAE | Steal an Egg | https://www.youtube.com/watch?v=NJDWwDxbvHw | t=10-260 (event banners, server event line, zones) |

The owner's own local sheets (`SHEET-ride-a-dino-top-game-own-captures-RULER.png`, `SHEET-steal-an-egg-own-captures-RULER.png`) were looked at only; nothing was copied.

## 4. Patterns every hit shares (and where we stand)

1. One fixed HUD frame: **covered** (PR #601, BD-1180).
2. Teach by pointing at the object: **gap** (BD-1226).
3. Short, flashy reveal with a big rarity word: **covered** (#599); keep it short.
4. Rarity = one colour family everywhere: **covered** (rule R4).
5. One art rule and strong silhouettes: **gap** (BD-1216, BD-1223, BD-1224).
6. Big world signs, wide paths, a hub: paths **covered** (#599); hub **gap** (BD-1221).
7. Thick outlined text, red X, few tabs: **covered** (Toybox kit).
8. Numbers as juice: partly (BD-1231, BD-1180).
9. Timers and an offline banner bring players back: **covered** (Welcome back, weather, nests); the daily and playtime rows are planned.
10. Social proof on screen: **gap** (BD-1227, BD-1228).
