# 221 Product owner plan: team, research findings, next sprints (2026-11-10)

Label: **LEAD / PRODUCT OWNER PLAN.** Owner request 2026-11-10: "take full lead as a product owner ... build a team of roles ... research ... figure out how to apply them to Be Dino". Research source: [research/2026-11-10-yt-and-game-design-research.md](research/2026-11-10-yt-and-game-design-research.md) (22 talks read from transcripts, 5 written sources, 10 GitHub tools). All balance numbers here are PROVISIONAL. Nothing was published or switched on.

## 1. The product truth today (PO read)

- Main passes every offline gate (docs/209). About **480 tasks are built but in Review / test**, and **no real player has played the game yet** (BD-1021 publish and BD-575 human run are both still open).
- Every talk the researcher read agrees on one thing: prove the loop with real new players before adding systems. So the PO rule for the next sprints is **measure first, then build**. New features go to the backlog; what ships next is what makes the first playtest readable and the first 3 minutes good.

## 2. The team (roles, what each owns, how it runs)

The owner talks to one person, the lead (PO). Roles are played by the lead or by **one helper at a time** (owner rule 2026-10-19), on Fable (budget rule 2026-10-19). Reviews are read-only helpers with self-contained briefs.

| Role | Owns | Evidence it must bring |
| --- | --- | --- |
| Product owner / lead | vision, priorities, board, owner questions, merge | this doc, board order, decisions log (docs/115) |
| Game designer | loops, pacing, first-time experience, economy proposals | spec doc + sim numbers (`tools/economy_sim.py`) |
| Retention and playtime optimiser | the signal map (section 4), funnels, D1/D7 goals, session shape | telemetry fields, before/after numbers per change |
| Architect | server authority, data safety, flags, migrations | design note, `verify_*` gates green |
| Game engineer | Luau implementation | PR, unit tests, CI |
| UI / UX designer | kid-readable screens, phone first, docs/72 rules | screenshots at phone size, "no reading" test |
| Art director / tech artist | Blender assets, icon and thumbnail, docs/77 registry | contact sheets, in-game pictures |
| Sound engineer | juice sounds, levels, no harsh cues (BD-166) | listened list, loudness numbers |
| QA tester | Studio and phone checks, regression list | PASS/FAIL table with pictures |
| Code reviewer / security | PR review, remotes, exploit checks, paid-random policy | review verdict BLOCKER/MAJOR/MINOR |
| Monetization and compliance | kid-safe offers, Roblox paid-random rules, `PolicyService` | release checklist (BD-1167) |
| Researcher | references, talks, tools | research docs with sources |
| LiveOps producer | update rhythm, banked content, event calendar | content calendar |

## 3. What the research changes for Be Dino (PO decisions)

Mapped against the board. "Exists" means a row already covers it; only the new ones got rows.

| # | Research action | Board | PO decision |
| --- | --- | --- | --- |
| 1 | Real first-session playtest with 5 to 10 children, screen recorded | BD-1021, BD-575, BD-317 exist | **P0, top.** Owner publishes; lead prepares the watch sheet (BD-1162) |
| 2 | First 3 minutes: play in 10 s, first hatch inside the bounce window | BD-440, BD-365 exist (partial) | New spec BD-1163. **Owner question** (short generous first run) |
| 3 | Hatch pacing for 40 to 400 eggs | BD-1056 exists (Skip taps) | **Owner question:** fast cascade for commons, slow for Rare and up, still one at a time and rising rarity. Spec row BD-1164 |
| 4 | Juice pass: bite, grow-up, egg crack (sound first) | BD-043 (UI only) | New BD-1165 (Blender effects only, art rule) |
| 5 | Analytics events and Roblox signal map | BD-426, docs/122 telemetry exist (run counts only) | New BD-1166: funnel events + signal map. **Sprint 1 build** |
| 6 | "Your nest is ready!" welcome-back opener | none | New BD-1168 |
| 7 | Co-play bonus (friend in server) | none | New BD-1169, P2 (after playtest) |
| 8 | Three-horizon goals; "7 of 15 for Gold" on duplicates | objectives exist (BD-078) | New BD-1170 |
| 9 | Spawn staging: two or three visible teasers | none | Folded into BD-1163 |
| 10 | Paid-random compliance checklist | BD-347, BD-453, BD-1126, BD-1136 exist | New BD-1167 one release checklist; paid flags stay closed |
| 11 | Content pipeline, banked drops, fixed release day | BD-058/654/660 partial | New BD-1171 LiveOps calendar, P2 |
| 12 | Game icon and thumbnail set (required for Home impressions) | BD-507 is HUD only | New BD-1172, P1 (owner art taste: show options) |
| 13 | Shape/colour language sheet, "no reading" test | docs/72 | Folded into BD-1163 test plan |
| 14 | Gentle daily egg, free streak freeze; never sell streak repair | daily tasks exist | New BD-1173, P2; the "never sell" rule goes into BD-1167 |
| 15 | Hunting beats camping for eggs per minute; Cracked fairness | BD-235, BD-1093 | Checked with the playtest data (BD-1162 sheet) |
| - | Reusable YouTube study tool (transcripts to notes) | none | New BD-1174, P3 (team tool) |

## 4. Signal map (retention optimiser)

Roblox Home ranking reads bounce (under 60 s and under 180 s), play days, co-play days, qualified sessions and similar signals over 28 days (research C7, W2; weights only visible in Creator Analytics). Which Be Dino feature feeds which signal:

| Signal | Be Dino lever | Row |
| --- | --- | --- |
| Bounce under 60 s / 180 s | play in 10 s, first hatch fast | BD-1163 |
| Play days | nest timer, welcome-back, gentle daily egg | BD-1168, BD-1173 |
| Co-play days | friend bonus, hatch together | BD-1169 |
| Session quality | juice, hatch pacing, goals | BD-1165, BD-1164, BD-1170 |
| Click-through | icon and thumbnail | BD-1172 |

## 5. Sprint order (one helper at a time)

1. **Sprint 1, can run without the owner:** BD-1166 funnel telemetry (so the first playtest is measurable), then BD-1162 watch sheet, then BD-1168 welcome-back.
2. **Sprint 2, after the owner answers section 6:** BD-1163 first 3 minutes, BD-1164 hatch pacing, BD-1165 juice.
3. **After the first real playtest:** re-rank everything on the data; then BD-1170, BD-1172, BD-1169, BD-1173, BD-1171.

## 6. Owner questions (asked and answered 2026-11-10, see docs/115)

1. Hatch pacing (BD-1164): ANSWERED, fast commons, slow Rare and up.
2. First run (BD-1163): ANSWERED, short and generous for the first run only.
3. Still owner-only: publish the playtest build (BD-1021).
