# 223 Welcome back: "Your nest is ready!" at join (BD-1168), 2026-11-11

Status: **Review / test**. Code and offline tests are done. **Not seen in Studio, not seen on a phone, the sound not heard.**
Why: [221](221-po-plan-team-and-research-2026-11-10.md) section 3 row 6 and section 4. Roblox counts "play days"; the nest timer is our reason to come back, and the return should feel like a small celebration, not a menu the child has to find.

Labels: the behaviour below is **CURRENT BUILD BEHAVIOR of the playtest profile only**. The default build is unchanged (flag off). Every number is **PROVISIONAL**.

## 1. What the player sees (flag on)

- A player joins. If one or more egg nests **became ready while they were away**, one gold toast card appears once the world has loaded:
  - 1 nest: **"Your nest is ready!"**
  - 2 or more: **"2 nests are ready!"**
  - second line (fine print): "Welcome back! Tap to open"
  - the registered nest icon (`egg_nest`, [77](77-asset-registry.md)); no new art.
- **A tap on the card opens the Nests screen** (the Eggs menu, the same path as the OPEN EGGS button of Run Complete; with the cave hub on, the stall trip rule decides as it does there).
- It never blocks play: it is a toast, not a window. It **fades by itself after 8 s** (a normal big-moment card: 4.5 s). The toast stack already holds a big-moment card back while a menu or the hatch reveal is open, so it never lands on top of one.
- One soft sound: the registered reward cue `level_up` (the same cue a nest plays when it is opened, [71](71-egg-nests-v2.md)), played in turn through `Sfx.playCue`. No new sound.
- **Once per join.** Never in the first session of a brand-new save. If nothing finished: nothing is shown.

## 2. Who decides (server)

Nest timers are server time ([71](71-egg-nests-v2.md)), so the server counts and the client only shows.

1. `ProfileRepository.load` already moves the nest queue forward to the join time inside the load transaction. With the flag on it also keeps three facts **in memory** (never in the save): was the save brand new, how many nests were `ready` in the save as it was stored, how many are `ready` after the queue moved (`ProfileRepository.welcomeInfo`).
2. `WelcomeBackService` (new, `src/server`) waits for `ProfileState = Loaded`, applies the pure rule `WelcomeBack.finishedAway(isNew, readyBefore, readyAfter)` and, when the result is 1 or more, sets the owner-only value `WelcomeBackNests` **once** for this join (PrivateState channel, [112](112-private-state.md)). No remote, no client input, no reward, no profile write.
3. `WelcomeBackCue` (new, `src/client`) reads that number and pushes one card into the existing toast stack. All words and decisions come from the pure `Shared/WelcomeBack`.

**The rule in one sentence:** a nest counts when the save said "not ready" the last time it was written and the server clock says "ready" now.

| Case | Card |
| --- | --- |
| Brand-new save (first session) | none |
| Nest still incubating at join | none |
| 1 nest finished since the last visit | "Your nest is ready!" |
| 3 nests in the queue, away 6 h (3 h each) | "2 nests are ready!" |
| A nest was ready last time and was not opened | not counted again |
| Build 020 save with old nests, first load after the migration | none for that one join (the migration marks old ready nests ready before the count) |

**Known edge (accepted, LEAD):** the save has no "last seen" time (the lease is cleared on leave), and adding one would be a new stored field. So "while away" is read from the stored nest states. A nest that became ready **during** the previous session, while the player did not open the Eggs menu or finish a run after it, is still stored as "incubating" and so counts at the next join. The player gets one happy card for a nest they have not opened yet, which is the wanted effect.

## 3. Flag and files

- `Config.WelcomeBackEnabled`: **false** in Config and in the default profile, **true** in the playtest profile (standing rule [157](157-playtest-profile-newest-features.md)), in the rehearsal list. Free, no Robux, no other flag touched.
- No save schema change. Nothing is stored.
- New: `src/shared/WelcomeBack.luau` (pure rules and words), `src/server/WelcomeBackService.luau`, `src/client/WelcomeBackCue.luau`, `tools/verify_welcome_back.py` (in CI).
- Changed: `ProfileRepository.load` (the three facts, flag-gated), `PrivateStateCore` (one owner-only name), one line in each Bootstrap, and two small additions to the toast stack that any card may use: **`action`** (a function run when THAT card is tapped; the card closes) and **`seconds`** (time on screen, capped at 10 s) in `NotifyQueue` and `Toasts`. Cards without them behave exactly as before.
- The client Bootstrap had 13 bytes of room under its size ceiling. The attach line is 68 bytes, so the trailing comment of the HudTimers line was shortened; the ceiling was **not** raised.

## 4. Copy check ([72](72-ui-copy-and-asset-standards.md))

Short, obvious words; one number at most; no time format, no rule text, no hidden threshold. Both lines fit the card without being cut (30 and 44 characters; checked for 1 to 50 nests).

## 5. Evidence (offline only)

`python tools/verify_welcome_back.py --runner <luau.exe>`: the pure rules with the real `NestQueue` (which nests count, the 3 h chain, brand-new save, bad input, singular and plural words, the show and tap rules), the toast stack additions, the real `WelcomeBackService` on mocked services (flag off = no connection and nothing sent; once per join), the real `ProfileRepository` on the mocked DataStore with a controllable clock (flag off = no facts; new save; back too early; back after 3 h; joined again without opening; several nests; nothing stored), the wiring, **37 mutants caught**.

## 6. Not verified

- **Studio:** the card on screen at join, its place next to the loading screen fade, the tap opening the Eggs menu, the cave-hub path (`HubTravelClient.press("eggs", true)`), Reduce Motion.
- **Phone:** size and place of the card, the tap target.
- **Sound:** `level_up` at join was not heard; if a tutorial or menu is open at join the card waits but the sound does not (it plays when the card is queued).
- **Real DataStore:** only the mocked store was run.

## 7. Open points (not built)

- **No X button and no Escape on the card.** The task text listed "tap, X, Escape, or it fades". A toast has no X or Escape in this game; the card fades and a tap opens the Nests screen, so there is no tap that only closes it. If the lead wants a close-only tap, the smallest change is a 48 px "X" zone at the right end of an action card (text, not art).
- A "last seen" time in the save would make "while away" exact (section 2, known edge). It needs a stored field, so it was not done.
- Telemetry: a `welcome_back` count on the anonymous session line (BD-1166) would show whether the card brings players into the Nests screen. Not built.
