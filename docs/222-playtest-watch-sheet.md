# 222 Playtest watch sheet: what to look at when a child plays (BD-1162)

Label: **LEAD / PRODUCT OWNER tool**, 2026-11-11. Use it with the publish pack ([182](182-publish-pack-friends-playtest.md); its section 9.3 is the owner's own first look) and the report tool ([167](167-reference-and-playtest-tools.md) part B). Why: [221](221-po-plan-team-and-research-2026-11-10.md) action 1. Every talk in the research says the same: watch new players before building more.

## 1. Setup (5 minutes)

- 5 to 10 children who have **never** played Be Dino. Siblings, cousins, friends' kids; ages 7 to 12 is the target.
- A phone or tablet if possible (most Roblox children play on one), otherwise a PC.
- Record the screen (phone: built-in screen recording; PC: Xbox Game Bar, `Win+G`). Sound on, so their words are recorded too. Ask a parent first.
- Say only: "This is a new game. Play it however you like, and tell me what you think." **Do not explain anything, do not help**, unless they are stuck for more than 30 seconds (write down where).
- Let them stop whenever they want. When they stop is the most important number.

## 2. The sheet (one row per child)

Write the time from joining, in minutes:seconds.

| Child (first name or A, B, C) | Age | Device | First bite | First run ends | First egg hatched | Laughed or said "wow" at | Stuck or confused at | What they did last before stopping | Stopped at | Asked to play again? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | | | | | | | | | | |
| B | | | | | | | | | | |
| C | | | | | | | | | | |

Good signs: first bite under 0:10, first hatch under 3:00, plays past 10:00, asks to play again.
Bad signs: stops before 1:00 or 3:00 (Roblox counts these as bounces), reads a text out loud and still does not know what to do, looks at the screen without moving.

## 3. Three questions afterwards (keep it short)

1. "What was the best part?"
2. "What was boring or annoying?"
3. "What do you think happens if you keep playing?" (tells whether the long-term goal is visible)

## 4. Two things to check in the recordings (lead, later)

- **Hunting vs standing still:** does a child who chases food and other dinos get more eggs per minute than one who stays at one food spot? Hunting must win ([221](221-po-plan-team-and-research-2026-11-10.md) action 15).
- **Cracked eggs:** when a Cracked egg fails, does the child laugh (the splat, PR #58) or look sad or cheated? Write the face down.

## 5. The game's own numbers

The playtest build records the same moments by itself (BD-1166, [122](122-session-telemetry.md)): first bite, first run end, first hatch, first shop and Index open, the screen when leaving, under 60 s / 180 s, days since the last visit, friends in the server. Before closing the test server, copy the server log (F9, "Server Logs", [167](167-reference-and-playtest-tools.md) section 6) into a text file, then:

```bash
python tools/playtest_report.py server-log.txt --out docs/evidence/playtest-1-report.md
```

Hand the sheet (a photo is fine), the recordings and the report to the lead. The lead compares the sheet with the numbers, re-ranks the board ([221](221-po-plan-team-and-research-2026-11-10.md) section 5, step 3) and writes the findings as rows.

## 6. Privacy

No surnames, no faces in what goes into the repository, no recordings committed (they stay on the owner's PC). Only the anonymous numbers and the written sheet go into `docs/evidence/`.
