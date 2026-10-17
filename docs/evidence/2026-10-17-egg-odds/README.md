# BD-365 / BD-301 Egg Odds panel after-picture (2026-10-17)

Build: `python tools/build.py --profile playtest` from origin/main (includes #391). Studio Play, fresh memory-only profile (1 Compy, 0 eggs), RenderStepped 59-60 frames/s before each capture, screen_capture only. Path: SHOP > Eggs tab > ODDS / DETAILS, scrolled to "Is the egg Cracked?".

| Image | Shows |
| --- | --- |
| 01-egg-odds-fresh-profile-safe-eggs-line.jpg | "Is the egg Cracked?" 50 / 30 / 15 / 4.5 / 0.5 and under it "Your first 2 eggs from runs are always safe." (18 px) |
| 02-egg-odds-fresh-profile-line-and-notes.jpg | the same line above the three general notes, Total: 100% |

BD-301: the same panel (hatch group 20% / 80% above, from the same config) agrees with the Buy Egg sentence; see also [menu-fixes](../2026-10-16-menu-fixes/). Offline proof for the line: `python tools/verify_safe_eggs_line.py --runner <luau.exe>`. Note: the Eggs tab says "Coming soon" in this build but the odds button works.
