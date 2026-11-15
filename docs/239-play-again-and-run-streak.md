# 239 Play again and the gentle run streak (BD-1199), 2026-11-15

Status: **Review / test**. Code and offline tests are done. **Not seen in Studio, not seen on a phone, the new button not pressed by a person.**
Why: [235](235-top-games-benchmark.md): a session under about 6 minutes loses Day 1, hits chain runs into a loop, and our run is about 5 minutes. The simulation ([evidence 2026-11-14](evidence/2026-11-14-player-sim/)) says week 1 is fine and then nothing new happens. The first cheap step is to make the next run one tap away and to reward chaining runs a little.

Labels: the behaviour below is **CURRENT BUILD BEHAVIOR of the playtest profile only**. The default build is unchanged (flag `Config.PlayAgainEnabled` is false and pinned off). **Every number is PROVISIONAL** (owner has not approved them): window 120 s, crystals 0 / 5 / 10 / 15 / 20, minimum run 60 s. Rules kept: one egg per catch, `FoodCatchRate` 12/500 and the nest rules are untouched; the owner-approved run crystals are unchanged, the bonus is added on top. Free, no Robux, no paid line.

## 1. What the player sees (flag on)

- At the **end of a hatch batch** (the last egg is revealed, nothing left to open, not a splat) two buttons appear where DONE was:
  - **PLAY AGAIN**: one big green button (300 x 64 px, text 34 px, dark ink on the accent green, contrast above 4.5).
  - **HOME**: a small grey button (150 x 48 px, a thumb target), beside it.
  - Touch, mouse and gamepad: both are normal buttons; **A / Enter presses PLAY AGAIN** while it is on screen. Escape and X still close the screen as before.
- **PLAY AGAIN starts the next run through the normal path**: the same code as TRY AGAIN after a splat. It closes the hatch party and fires the one existing `RequestStartRun` remote, only while the dino is in the Sanctuary; the server still checks everything (profile loaded, world ready, egg bank room, Sanctuary state). There is **no server shortcut**.
- **HOME** closes the party and starts nothing.
- **No timer, no countdown, no auto-start.** Nothing happens until the child presses a button.
- A splat keeps DONE / TRY AGAIN, and an egg with more to come keeps NEXT EGG or the tap hint.
- **Run streak**: a run that starts within 120 s of the **end of the previous run** continues a streak 1, 2, 3, 4, 5 (a longer streak stays at 5). From streak 2 a soft toast says **"Run streak 3!"** when the run starts, and the same words sit under the level on **Run Complete**. Streak 1 shows nothing. Waiting longer, or leaving the game, starts again at 1 and **says nothing** (never "you lost your streak").
- **Bonus**: the settlement of a run adds crystals for its streak step, `Config.RunStreakCrystals = {0, 5, 10, 15, 20}` (PROVISIONAL). It sits inside the crystals row of Run Complete, so no new number to read. A full five-run streak adds 50 crystals in total (one 12-egg run pays 30).

## 2. Who decides (server)

1. `RunLifecycle.begin` (flag on) asks `RunStreakService.onBegin(player, runId, serverTime)`: the streak of THIS run from the previous run end (pure rule `PlayAgain.nextStreak`), kept per run id in server memory, published to the owner only as `RunStreak`.
2. `RunLifecycle.tryEnd` (flag on) tells `onEnd` the end time and the owner-only `LastRunStreak` for Run Complete.
3. `ProfileEggs.commitRunSettlement` (flag on) asks `bonusFor(player, runId, catchScore, runSeconds)` BEFORE the transaction and adds it to `outcome.crystals`, so the stored outcome carries it and the existing run-id ledger makes it **exactly once**: a replay of the same run id is answered "duplicate" with the original outcome and pays nothing more. After a committed (not duplicate) settlement `committed` marks the run paid (a second belt) and sets the owner-only `LastRunStreakCrystals` for display.
4. The bonus needs a **real run**: one or more eggs and at least `RunStreakMinRunSeconds = 60` s (PROVISIONAL), so starting and ending runs at once never pays.
5. The call is protected (`pcall`): a bug in this optional bonus never blocks a settlement (BD-1096 rule); the result is then simply no bonus.
6. **The client cannot claim**: `commitRunSettlement` has no streak argument, the client never sends a streak or a bonus, `RequestStartRun` still accepts no argument, the three new names are owner-only values set only by the server.

## 3. Saved data

**Nothing is saved.** The streak is session-only memory (weak table keyed by the Player object): leaving and rejoining starts at 1, the bonus is plain crystals in the existing progression. No new profile field, no schema change. With the flag off the module is never loaded and no value is set: the settlement is byte for byte the old one (`verify_play_again.py`, section flag off).

## 4. Numbers and why (all PROVISIONAL)

| Number | Value | Why |
| --- | --- | --- |
| `RunStreakWindowSeconds` | 120 | a child who hatches (about 15 eggs) and presses PLAY AGAIN is back in well under 2 minutes; a fast Common batch takes about 15 s ([226](226-hatch-pacing.md)). May be too tight if a child reads every reveal: watch it in the playtest. |
| `RunStreakCrystals` | 0, 5, 10, 15, 20 | small: one 12-egg run pays 30, so the step is a nod, not a reason to hurry; no egg, no odds and no nest change. |
| `RunStreakMinRunSeconds` | 60 | no free crystals for an instant restart. |

Calm feel ([87](87-vision-and-feel-guide.md)): no pressure, no clock on screen. The window is invisible; only the word "Run streak 3!" appears, softly, and only when it went well.

## 5. Evidence (offline only)

- `python tools/verify_play_again.py --runner <luau>`: rules (buttons, sizes, contrast, streak, table, words), the real service, the real `ProfileRepository` on the mocked DataStore (flag off identical; flag on: bonus once per run id, replay pays nothing, a late run is plain, a run that ends at once pays nothing, a broken service never blocks), static wiring and mutants. In CI.
- `python tools/simulate_players.py --play-again` (what-if, [evidence 2026-11-15](evidence/2026-11-15-player-sim/)): see the numbers there. The simulation counts a persona's runs per session +1 when the button exists and a streak 3 / 5 moment as a small "new" thing; it is a design tool, not a prediction ([235](235-top-games-benchmark.md): only real players give retention).
- Switch-on rehearsal ([152](152-switch-on-rehearsal.md)): `PlayAgainEnabled` is in the rehearsal list, so every offline suite also runs with it on.

## 6. Not verified

Studio and phone look of the two buttons on the 824 x 402 card (row at y 334, the play button 64 high); that A / Enter on a real gamepad lands on PLAY AGAIN; the toast "Run streak 3!" in a real run; the 120 s window against real hatch times; whether children use HOME. These need the owner's Studio and phone pass (CLAUDE.md: never claim acceptance without evidence).

## 7. Not built

Lobby goals (the third part of the BD-1199 row), a PLAY AGAIN on the Run Complete window itself (the hatch end is where the child looks next), a streak display that lasts (HUD), any sound for the streak.
