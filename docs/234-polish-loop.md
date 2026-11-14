# 234 Polish loop (BD-1191), 2026-11-14

Owner 2026-11-14: "i shouldnt have to tell you all of this, critique your own game as a reviewers player etc make up roles to keep refining polishing and making the game better" and "don't rely on rules, make systems and loops". This page is the system: a loop that finds what is weak before the owner does, ranks it and feeds the fixes.

## The loop

1. **Capture.** Build the playtest profile, open a copy in Studio, Play. For every screen of `python tools/polish_loop.py screens` call the Studio-only `BeDinoScreenTour` hook (Bootstrap, exists only when `RunService:IsStudio()`), then `screen_capture`. Save to `docs/evidence/<date>-polish-loop/<screen>.jpg` with `tour.json` (screen -> file, viewport, build sha). 1280x720 and a phone size.
2. **Review.** The `polish-reviewer` agent (`.claude/agents/polish-reviewer.md`, read-only) looks at every picture as six roles: kid player, Roblox reviewer, art director, UX/layout (docs/232), sound and feel (docs/87), QA. It writes `findings.json` (concrete issue + fix, severity and reach 1-3) and `scores.json` (1-10 per screen, 10 = top Roblox game).
3. **Rank.** `python tools/polish_loop.py ingest <folder>/findings.json --scores <folder>/scores.json`: stable ids, duplicates merged, fixed items that come back are reopened, the ranked table lands in `docs/be-dino-queue.md` (generated block). History of scores in `docs/polish/scores.json`.
4. **Ticket.** `python tools/polish_loop.py rows -n 5 --apply`: the top open findings become kanban rows. Taste forks (`needs_owner`) are not rows: they go to the owner as one batched ask with pictures.
5. **Fix.** One helper at a time takes the top row (worktree, flag-gated, its own checks). The lead reviews, merges when checks pass, `polish_loop.py close <id> --note "PR #n"`.
6. **Again.** The next run's captures prove the fix (a fixed finding that shows again is reopened automatically) and the scores must go up.

## When it runs

- At the start of every work block on Be Dino!, and after every merged change that touches UI, art, world or sound.
- The target is every screen at **8+**. A screen under 6 blocks new features on that screen until it is fixed.

## Roles (the panel)

| Role | Asks |
| --- | --- |
| Kid player (8) | Do I get it in 3 seconds? Is it fun, clear, not scary? |
| Roblox reviewer | Does it stand next to Pet Simulator 99 / Adopt Me / Grow a Garden? What looks cheap or unfinished? |
| Art director | One style; real art, not code shapes or stand-ins; colour and outline harmony |
| UX / layout | docs/232 rules: grid, inset, gutter, no text on studs, one button height, one primary colour, nothing clipped, X inside the header |
| Sound and feel | docs/87: calm, soft, a little magical; feedback and reward moments |
| QA | overlaps, clipped text, wrong numbers, debug text, empty states, phone size |

## Not covered yet

- Screens that need game state (hatch reveal, purchase confirms, run complete) are not in the tour; they need a Studio state script (next step of BD-1191).
- Sound cannot be judged from pictures; a sound pass needs the owner's ears or a recorded clip.
