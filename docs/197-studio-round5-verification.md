# 197 Studio round 5: verification of the 2026-10-18 merges

Label: **STUDIO EVIDENCE**, written 2026-10-18 by the Studio QA helper. Playtest build of `origin/main` `c677239c` (screen label **BUILD redesign-020 c677239c**), window 500 x 465, in-game crystals only, nothing published, no flag or chance forced. Full picture list, verdicts and the food coordinates: [evidence/2026-10-18-studio-r5/README.md](evidence/2026-10-18-studio-r5/README.md) (pictures 330 to 357 in `docs/evidence/review-2026-10-17/`).

| Item | Verdict |
| --- | --- |
| 1 Hatch polish (#520) | PASS (Rainbow and Astra not seen, not forced) |
| 2 Small windows (#526, BD-1085) | BLOCKED: #526 was not merged; only the before state at 500 x 465 |
| 3 Class icons (#521) | PARTIAL: only on the reveal card; Index and My dinos have none (BD-1099) |
| 4 Starter goals (#522, BD-1080) | PASS, three claims paid, detail box fine; Patterns tab untappable (BD-1083) |
| 5 Food map and respawn (#518, #524) | PASS: even spread, none floating, 60 in collider boxes (BD-1098); berry 8.1 s, amber about 2 min |
| 6 Gene boost (#516) | PASS: 1.4 points, growth x1.014, walk 22.154 |

New rows: BD-1095 (Goals and Tasks panels overlap), BD-1096 (a run stayed in Ending after a server Script timeout in TelemetryService, seen once), BD-1097 (small-window overlaps), BD-1098 (foods in collider boxes), BD-1099 (class icons question). Notes on BD-1075, BD-1078, BD-1080, BD-1085. BD-1083 (tab under the rail button) is confirmed as a real defect, not the click tool: the rail button's own tap route closes the menu and presses EGGS.

Lesson for the next Studio agent: the mouse tool wants GUI coordinates (`AbsolutePosition` centre), not screenshot pixels; a miss lands on the dark backdrop and closes the menu, which looks like a game bug.
