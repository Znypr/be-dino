# 71 Egg Nests v2 (BD-090..094)

Owner, 2026-10-14: nests are an additional loot item at the end of a run, like crystals; several random eggs inside; they need time to hatch (3 h each); 10-15 eggs; waiting for several adds up (5 nests = 15 h, about 60 eggs); nest eggs are luckier; fully separate from run eggs; separate menu. Owner answers: one nest incubates at a time (queue); a run drops 1 nest, more for big runs; a hidden minimum stops farming with instant runs.
**Update 2026-10-15 (owner, [docs/90](90-fusion-ladder-v2.md) section 5): nest size is now 6-12 eggs (average 9; was 10-15), because a run now gives only about 4 eggs. Nests may out-produce run eggs on purpose (they wait hours, which is the reason to come back); 5 slots and 3 hours each are unchanged, so at most about 8 nests (about 72 eggs) a day. The 10-15 and "5 nests = about 60 eggs" figures below are history; 5 nests are now about 45 eggs.** Every number is **PROVISIONAL** and lives in `Config.luau` (`Nest*`). Replaces the Build 020 bonus nests (3 eggs, 300 s, 5 slots + pending) from [doc 50](50-bd044-reward-loop.md). Statements marked **Seen** were verified in the repo, **Proposal** are new.

## Intake answers ([doc 64](64-feature-intake-template.md))
1. Intention: surprise and a reason to come back (progress over hours). Loop moment: settle (drop), menu (wait/open), hatch reveal (eggs). **Proposal**
2. Extension of the existing nest system (**Seen**: `nests`, `ClaimNest`, banked-egg pipeline); the old Caught Eggs nest block is removed.
3. Fit: run settlement -> `eggNests` -> menu -> `ClaimNest` -> banked eggs -> existing hatch pages/reveals. Off = no nests, run eggs unaffected.
4. Placement: 7th nav rail entry, modal like the other menus; touch rail keeps 44 px targets (tests: `verify_movement_mobile`, `NAV = 7`).
5. Visuals: v2 kit buttons/cards (`Theme.decorate`), green OPEN, native progress bar. The nest sprite is the v2 `egg-nest-v1.png` once bound; until then a code-drawn **PLACEHOLDER** (`egg_nest` in `UITheme`, BD-094).
6. Icons: one (nest). Nav and cards share it. No invented asset ids.
7. Animation: none new; bars/text update once a second; motion off changes nothing.
8. Audio: `shop_buy` on open and on the drop toast, `level_up` when a nest opens. Silent while ids are empty.
9. Copy (docs/72): "Egg Nests", "Nest: 12 eggs", chips Ready / Incubating / Waiting, "Ready in 2 h", "New Egg Nest! Hatches in 3 h", "nest storage full". No requirement text anywhere.
10. Server: authoritative, idempotent (`nestclaim:<nestId>` operation), additive `eggNests` field, a few hundred bytes (5 nests = 502 B tested), no extra UpdateAsync.
11. Performance: at most 5 cards (migrated saves scroll), one 1 s text/size update loop that stops when the menu closes.
12. Metric: sessions per day / runs per session; playtest question "did you open nests?".
13. Checks below.
14. Tasks: BD-090..094 in the Kanban.
15. Open questions: (a) keep the drop gate numbers 120 s / 8 catches? (b) nest 3 h feels right for kids? (c) is luck strong enough? Defaults below.

## Design
- Nest = `{nestId, droppedFromRun, size 6-12, luck tier, state waiting|incubating|ready, readyAt}` (legacy records also carry `eggs`).
- **Drop** at run settlement inside the same UpdateAsync as the run eggs (exactly-once: `settledRuns` + `run:<id>` operation; replay returns the committed outcome). `nestId = nest:<runId>:<n>`; `size` is a deterministic hash of the nest id, committed at drop. Count: 1 for a qualified run, +1 per 100 further catches, max 3.
- **Hidden gate** (`RewardMath.nestQualifies`): server run length >= `NestMinRunSeconds` (120) **and** validated server catch score >= `NestMinCatches` (8). Run length is measured with the server clock in `RunLifecycle` (`begin` stores the start in a server-only table; settlement passes the elapsed seconds; unknown start = 0 s). The result (nest count, `nestFull`) is committed in the run outcome, so a replay returns it unchanged. A run that does not qualify shows nothing about nests. Exploit reasoning: instant start/end loops give 0 s; AFK without food gives 0 catches; the client reports neither time nor catches that count (catch score comes from validated pickups), time is server-side so clock tampering is impossible; 3 h per nest and the 5-nest cap bound farming even with a perfect run loop (about 8 nests/day at most).
- **Storage** `NestStorageCapacity` 5 (waiting + incubating + ready). Full: the nest is not granted, the settlement still succeeds, and the run-end text says "nest storage full" **only for qualified runs** (`nestFull`).
- **Queue** (`NestQueue`, shared by server and client): one incubating nest; the next waiting nest starts the moment the previous becomes ready (not when opened), time from `os.time`, offline counts. 5 nests = 15 h. State is advanced on every load/settlement/open; the client projects the same function with the server clock for display.
- **Open** (`ClaimNest` -> `claimNest`): ready only (`not_ready`, `nest_pending`, `missing`, `bank_full` refuse without change); rolls `size` eggs inside the transaction and puts them at the **front** of the banked-egg pipeline as `kind="nest_egg"`, `source.kind="nest"`. Reveals use the normal 1 s presentation and rarity skip; the client starts the reveal after "opened".
- **Luck** (`NestLuckTiers[1]`, nest field `luck`): max run-batch rarity boost (15), +2 condition levels (Cracked 50% -> 34%), Shiny 3% (also without irregular weather), BIG 20% (normal 10%). Disclosed in the menu: "Nest eggs are lucky: better rarity, condition, Shiny and BIG odds." Measured over 3,000 eggs: Shiny 3.1%, BIG 20.3%, rare+ 2.5x. Bounded by the config tier (asserted).
- **Migration** (`migrateLegacyNests`, on load and open): Build 020 `nests` / `pendingNests` become `eggNests` records that keep their precommitted eggs (size 3, luck 1); ready ones are ready, the first unfinished slotted one keeps its `readyAt` and incubates, everything else waits in queue order; old fields are removed. Nothing is lost; migrated saves may exceed 5 nests (the cap only limits new drops). The run-start `nests_pending_full` gate is gone (the egg-bank gate stays).
- No Robux, no speed-up.

## UI
Nests menu (nav entry NESTS): header "Nests n/5", luck line, one card per nest (sprite, "Nest: 12 eggs", state chip, "Ready in 2 h", progress bar), green OPEN when ready, footer "One nest hatches at a time, 3 h each. The next starts when this one is ready, even while you are away." Empty: "No egg nests yet. Look for one at the end of a run." Drop: toast "New Egg Nest! Hatches in 3 h" (hours until the new nest is ready, counting the queue) and "1 egg nest" in the run-end line. Caught Eggs shows run eggs only ("Eggs waiting: N").

## Numbers (PROVISIONAL)
`NestStorageCapacity 5`, `NestIncubationSeconds 10800`, `NestMinSize/MaxSize 6/12` (was 10/15), `NestMinRunSeconds 120`, `NestMinCatches 8`, `NestEggsPerExtraNest 100`, `NestMaxPerRun 3`, `NestLuckTiers[1] = {15, +2, 3%, 20%}`. Removed: `NestSlotCapacity`, `NestPendingCapacity`, `NestEggCount`, `NestRarityBoostEggs`, `NestFirstAtEggs`.

## Tests
`tools/verify_nests.py` (CI): queue unit, size range, hidden gate (0 s, 119 s, 120 s, unknown time, long run with 0 or 7 catches, qualified, replay), exactly-once and reload, 5 nests = 15 h with offline jumps and exact boundaries, storage cap and partial grant, idempotent atomic open and bank_full, luck applied and bounded, Build 020 migration, 150/400-egg runs, same UpdateAsync count with or without nests, byte size. Also updated: `verify_rewards`, `verify_progression`, `verify_movement_mobile` (7 buttons; the touch notice now stays left of the wider rail).

## Studio checks (lead)
Nests entry visible on desktop and phone landscape, no overlap with HUD/thumbstick; finish a run of >= 2 min with >= 8 catches -> toast and card; a short run shows nothing about nests; countdown ticks; OPEN with a ready nest (use a profile edit or temporarily lower `NestIncubationSeconds`) -> eggs reveal at 1 s each, skip works; storage full message; motion off; sound off. Replace the PLACEHOLDER sprite after upload (BD-094).
