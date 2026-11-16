# 2026-11-16 UI feedback: play cues (BD-1226, BD-1231, BD-1234)

Studio 2026-11-16, own built playtest place (`python tools/build.py --profile playtest`), Play mode, 1914 x 793 window. Flag `PlayCuesEnabled` on (playtest profile); the default build is unchanged (flag off, every script returns on its first lines).

| Picture | What it shows | How it was made |
| --- | --- | --- |
| `point-at-first-food.jpg` | BD-1226: "Eat me!" chip on the nearest food in a new player's first run | real join, starter run, nothing staged |
| `point-at-stall.jpg` | BD-1226: "Potions!" chip over the stall at home for a new player | walked to the stall with `Humanoid:MoveTo`; the chip is AlwaysOnTop in the game, which Studio's capture cannot draw, so for the shot a copy with AlwaysOnTop off and the 15-stud lift (now in the rules) was shown |
| `growth-pop-and-banner.jpg` | BD-1231: "+1" rising beside the head (clear of the health bar) and the "Big dino!" banner above HOME | GrowthScore raised on the server like a bite; the pop and banner were cloned and frozen (they fade in 0.9 s / 1.6 s, faster than a capture) |
| `growth-banner-before-fix-overlap.jpg` | BEFORE the fix: banner over the hint line, number on the health bar (kept to show why they moved) | as above |
| `egg-ready-toast-badge-nest-chip.jpg` | BD-1234: toast "Your egg is ready!" / "Tap to open it", the green "1" badge on EGGS, the "Eggs ready!" chip over the nests | the ready nest was staged as display data only (a NestsJson message to this client); the stored profile was not touched. Taken before two later fixes: the nest chip is now 200 px wide (the icon covered the "E") and lifted 15 studs |

Not checked: phone layout, Reduce Motion on (offline-tested only: `tools/verify_play_cues.py`), sound of the toast (existing `level_up` cue, unheard). The toast is the existing navy toast card (docs/240 step 4 restyles toasts; not this change).
