# 102 QA playtest pass, 2026-10-16

Build: `python tools/build.py --profile playtest` from main at 3406aae (Build020-playtest), own Studio window, Play mode, one local player. Screens captured at about 1445x841. Evidence images: [docs/evidence/2026-10-16-qa-pass/](evidence/2026-10-16-qa-pass/). Judged against [docs/87](87-vision-and-feel-guide.md). **No agent heard any sound: all sound items need the owner's ears.**

Method notes (honest limits): a minimized Studio window renders the 3D world black, so the window was restored to the front for captures. Other Studio windows were left alone. The machine ran three Studio instances, so measured fps (about 15) is NOT representative. The 30 catches and the mutated egg tag were produced by writing the same `CatchScore` / `RunEggEvents` attributes the food code writes (server side, tags made with `ProgressionRules.eventEgg`), because walking gave only 3 catches in 25 s. The Volcanic Bloom event and Food x10 came from the real admin panel.

## Results per item
| # | Item | Result | Evidence |
| - | --- | --- | --- |
| 1 | Eggs screen (BD-152) | OK. Five nest slots on top, ONE large Next egg card (egg picture, Common + Dirty chips, Volcanic Bloom chip, READY, "Eggs waiting", OPEN, AUTO). Run summary "OPEN EGGS" opens it; OPEN starts the hatch. | 05, 06 |
| 2 | Hatch flow, Cracked splat | OK. A Dirty egg shows a cleaning bucket step, then crack, then reveal ("Tap for next egg"). Cracked eggs showed "Oops! Splat!" with a broken egg picture five times in one batch (UI text watcher). No errors in console. Skip all works (a few seconds late at 15 fps). | 07, 08, 09 |
| 3 | Camera on bumpy terrain (BD-164) | NOT proven. 24 s walk, 361 frames at 15 fps (max frame 73 ms): camera Y second difference averaged 0.144 studs (max 0.755) while the root's own averaged 0.020 (max 0.625). The camera is noisier than the root on this run, but frame time was uneven, so this is inconclusive. Recheck on a quiet machine at 60 fps. | 02 |
| 4 | Run end soft cue (BD-166) | Wiring confirmed, sound NOT judged. `Sfx.luau` run_end = asset 87202810278231 (the run_start chime, 0.5 s long), volume 0.2, rate 0.9. At the same moment `level_up` (asset 135894580270926, 1.4 s, volume 0.2, rate 0.95) plays, plus crystal and nest toasts: two reward cues inside about one second. **Owner must judge by ear.** | 04, 05 |
| 5 | Mutations (BD-154) | Partly. Admin panel Food x10 and Volcanic Bloom worked (logged in console). 31 egg tags arrived, one with `ember`; the UI created the "Ember egg caught!" toast (text found in the toast tree) but it never appeared in two screenshots, so its look and timing are unverified. The Eggs card showed the Volcanic Bloom badge; the Ember egg itself was not reached in the queue, so the mutation badge is unverified. | 03, 06 |
| 6 | Shops | Auras OK: coloured cards, glow ring behind the coin, no dark boxes. Conditions: lit evenly, all five eggs readable but small and pale; Rainbow and Astra visible but subtle; Cracked and Dirty marks faint. | 11, 12 |
| 7 | Console | No red errors from the game. Noise: UIBlox "FoundationProvider not found" warnings (Roblox core, repeated), a stray `MeshPart berry` print, and `GeneratedWorld is not a valid member of ReplicatedStorage` (raised by an inspection command, not by the game). | n/a |

## New findings (kanban rows BD-253 to BD-262)
See [the kanban](07-kanban.md). Top ones: foliage fills the camera and hides the dino and food (P1), the dino and Sanctuary still read as boxes (P1), camera noise not disproven (P1), lava wash covers a third of the screen (P2).
