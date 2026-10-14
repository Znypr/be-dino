# BD-044 + BD-045: one run egg per catch, banked reveals, bonus nests and new condition odds

> **Superseded in part 2026-10-13 (owner):** the egg rate is now 40 per 500 food (5,000 -> 400); every 15 / 150 / 300 / 600 / 219 figure below is the earlier prototype. Current values: [59-egg-rate-40.md](59-egg-rate-40.md).

Implemented 2026-10-13 on `claude/bd-044-reward-loop`, based on GitHub main `18856b4`.
Task status lives only in [Kanban](07-kanban.md) (**Review / test**). Owner intent:
[reward target](09-reward-economy.md), [AGENTS.md](../AGENTS.md) and
[BD-045 condition spec](45-owner-feedback-shop-hud-world-weather-tasks.md#a-egg-conditions-and-game-economy--bd-045).

**Verification status: offline Luau harnesses only. Studio verification is pending**
(the lead runs Studio checks). Nothing here has run against a persistent DataStore,
a published place, multiple real clients or a phone. Milestone 1 is a private playtest
in a NEW private place with fresh saves; every Robux/paid flag stays `false`.

## Owner decisions applied (2026-10-13, authoritative)

- Every earned run catch banks **exactly one run egg**. `500` food -> `15` eggs and
  `5,000` food -> `150` eggs at the unchanged `FoodCatchRate = 15/500`.
- **Exactly one dinosaur per successfully hatched egg.** The 70/25/5 1/2/3-copy split is
  removed for new eggs. A failed Cracked egg still gives 0.
- The direct `N(c)=c` settlement copies and the 10/100/500 catch-threshold eggs are removed.
- Unapproved numbers are config values labelled `PROVISIONAL` (table below).

## Data shape (additive profile fields; schema version unchanged)

| Field | Shape | Notes |
| --- | --- | --- |
| `eggs` (existing) | five-slot reveal queue | Unchanged shape. Still the only place eggs are claimed from, strictly in order. |
| `pendingChestGrants` / `pendingEggEvents` (existing) | legacy overflow | Untouched. Drained first, so legacy and purchased eggs are never overtaken. |
| `runEggBank` (new) | ordered array of egg records | Run/nest eggs waiting behind the queue. Refilled into the queue after every claim, settlement or nest opening. |
| `nests` (new) | up to `NestSlotCapacity = 5` `{nestId, readyAt, eggs[3], source}` | Separate bonus-nest slots; incubation starts when a nest takes a slot. |
| `pendingNests` (new) | ordered array of nests without `readyAt` | Capacity-blocked nests, shown to the player (`PendingNestCount`), promoted FIFO when a slot frees. Never dropped, never auto-granted. |
| `settledRuns` (new) | last `SettledRunLedgerSize = 200` run IDs | Exactly-once guard that survives `recentOperations` trimming (150 claims would otherwise push the run operation out of the 50-entry log). |

Every egg record carries the immutable, precommitted outcome: deterministic `eggId`
(`run:<runId>:<ordinal>` or `nest:<runId>:<n>:<k>`), `reward {speciesId, count=1}`,
`genes` (condition, hatch success, colors, share, pattern), `shiny`, `big`, `eventId`,
`mutationId`, `traitRollVersion = "bd045-genes-v2"` and `source {kind, runId, ordinal}`.
Old saves have none of the new fields and load unchanged; old queued eggs (including
1/2/3-copy rewards and `build020-genes-v1` genes) remain claimable exactly as committed.

## Settlement and idempotency

`ProfileRepository.commitRunSettlement(player, runId, catchScore, eggEvents)`:

1. `RewardMath.runEggCount` sanitizes the score: NaN, non-numbers, zero and negatives -> 0;
   fractions floor; anything above `RunEggMaxPerRun = 300` (including `inf`) clamps.
2. If the cached profile already has the run (`recentOperations` or `settledRuns`), it
   returns `duplicate` without preparing anything.
3. All randomness is committed **before** `UpdateAsync`: per-egg species (batch boost
   `B = 1 + (clamp(N,1,15)-1)*0.25`), genes/traits, nest contents. Eggs are sorted by
   ascending species rarity (stable by catch ordinal), matching the ordered reveal (`HatchRevealSeconds`, **1 s per egg**, PROVISIONAL owner decision 2026-10-13).
4. The transform re-checks the lease and the ledger (a lost acknowledgement or a retry by
   the same session finds its own write and reports `duplicate`), then appends deep copies
   of the batch to the bank, refills the queue, places nests, credits deterministic crystals
   and account XP, records the run in `settledRuns` and a compact operation (no egg IDs).
5. No dinosaur copies are granted at settlement. Dinosaurs only come from claiming eggs.

Repeated transforms, retries, reconnects and the existing `DuplicateSettlementProbe`
therefore credit a run exactly once. Outage or lease loss writes nothing.

**Catch-time tags.** `FoodService` no longer prepares eggs during the run. Catches made
during a weather event append a compact tag `{eventId, mutationId, n}` (catch ordinal)
to `RunEggEvents`; clear-weather catches need no tag. This keeps the replicated character
attribute small for 150-300 eggs. Genes/Shiny/BIG are rolled once at settlement (Shiny
still uses the tagged catch-time weather).

**Run-start gate (never lose earned eggs/nests).** `RunStartBlocked` is set when banked
eggs exceed `RunEggBankCapacity - RunEggMaxPerRun` (`egg_bank_full`) or pending nests
exceed `NestPendingCapacity - NestMaxPerRun` (`nests_pending_full`). `RunLifecycle.begin`
refuses a new run (`LastRunStartStatus`) until the player hatches/opens enough, so any run
that does start always fits; settlement itself never refuses or truncates.

## Reveal and claims

`claimChest` is unchanged for the player: claim the queue head, 1 s ordered reveal, then
the client auto-advances (`NextChestId`). After each claim the queue refills from legacy
overflow first, then from the bank. A 150-egg batch is 5 queued + 145 banked and reveals
continuously; closing or rejoining resumes at the exact next egg with no reroll.
One identity (`DinosaurIdentity.hatch`, count 1) is created per hatched dinosaur; failed
Cracked eggs create none. Legacy eggs with a committed count of 2 or 3 still create 2-3.

## Hatch pages: request budget (integration fix, 2026-10-13)

One `UpdateAsync` per revealed egg at the original 5 s was 12 requests/min per player, which projected to
154.7/min for 8 players (budget 140) and 210.7/min for 12 (budget 180) in `tools/verify_load.py`.
Claims are now **paged**: claiming a run/nest egg at the queue head commits up to
`HatchPageSize = 10` (PROVISIONAL; was 5 at the 5 s reveal) consecutive ready run/nest eggs in the **same** transaction
(each credited, identity-hatched and recorded as its own `chest:<eggId>` operation; legacy and
purchased eggs still claim singly). The first result is returned; the other committed results
wait in a per-player in-memory reveal buffer and `NextChestId` points at them, so the existing
client keeps revealing one egg per 1 s with **no** DataStore request for buffered entries.
Claiming a buffered egg only pops the buffer; a claim for a still-queued egg while a page is
waiting reveals the page head ("reveal next"); already-credited IDs return `duplicate`.
Reveal pacing is now 1 s/egg, i.e. 60 eggs/min per player; with pages of 10 that is 6 claim requests/min/player
(page size 5 would be 12/min and exceed the budgets again). Projection incl. renews and pickups: 8 players about 107/min vs 140 (76%), 12 players about 139/min vs 180 (77%); `verify_load.py` prints the same formula.

Consequences: credit happens at page commit, so a rejoin mid-page loses only the reveal
animation of up to 9 already-credited eggs (they are in the collection; verified in
`verify_rewards.py`). Exactly-once, one dinosaur/egg, deterministic order and the 5-slot queue are
unchanged; a page never crosses a legacy/purchased egg. Studio check pending: reveal UX when the
buffer is reconnected-lost, and `verify_load.py`'s hard-coded projection formula should be updated
to the paged model by its owner.

## Skipping selected rarities (PROVISIONAL, owner request 2026-10-13)

Instead of one skip button the player chooses which **species rarities** to skip
(Common / Rare / Legendary; default none, so Legendary is always shown unless chosen) in
Settings -> "Skip reveals". Logic lives in the pure `src/shared/RevealSkip.luau`
(normalize/toggle/shouldSkip/summarize/lines). A skipped egg is **still hatched and credited
by the server** exactly like any other; only the animation is dropped. **Notable finds are never
skipped:** Shiny, BIG, event mutation, Rainbow or Astra condition, and any outcome the client
cannot classify. Skipped eggs are collected in a compact end-of-batch "Skipped eggs" summary
(counts per rarity, hatched vs cracked, notable names). The selection is a UI preference stored in the
additive profile field `revealSkip` (array of 1-3 rarity numbers, validated by
`ProfileRepository.setRevealSkip` behind the rate-limited `SetRevealSkip` remote, mirrored in the
`RevealSkipJson` attribute); the server never reads it when granting anything. Tested in
`verify_rewards.py` (selection logic, validation, persistence, claims unaffected). Studio check
of the Settings row layout and the summary modal is pending.

## Bonus nests (PROVISIONAL rule and contents)

- Earning: first nest at 15 run eggs, then one per 27 further eggs, max 11 per run
  (15 -> 1, 150 -> 6, 300 -> 11). Separate from run eggs; never consumes queue capacity.
- Five nest slots. Extra nests are `pendingNests` (capacity-blocked, visible).
- Contents: 3 precommitted bonus eggs per nest, rolled like earned eggs with the maximum
  run-batch species boost (`NestRarityBoostEggs = 15`), clear weather, one dinosaur each.
- Incubation 300 s after slotting. `ClaimNest` (new remote, rate-limited) opens a ready
  nest: its eggs go next in line (front of the bank) and the oldest pending nest takes the
  slot. Refusals: `not_ready`, `nest_pending`, `missing`, `bank_full`, `invalid_nest_id`.
- Minimal client hook: the existing Caught Eggs modal shows "Eggs waiting", nest slot
  and pending counts and an OPEN BONUS NEST button. No HUD/touch layout was changed.

## Run crystals (PROVISIONAL, deterministic)

`crystals = min(500, 2*min(eggs,15) + floor(1.4*max(0, eggs-15)))` -> 15 eggs = 30,
150 eggs = 219, 300 eggs = 429. The random 5/15/50 run crystal box is retired
(`LastRunCrystalBox = 0`, so the client skips the box reveal). Map crystal pickups are unchanged.

## BD-045 condition odds (`bd045-conditions-v1`)

Integer weights out of `ConditionWeightScale = 10000` (exact half percents). Tier 0 is
the owner target; tiers 1-6 are a **PROVISIONAL** curve where Cracked and Dirty fall and
Normal, Rainbow and Astra rise at every tier. Prices/level gates unchanged. Cracked keeps
20% hatch success.

| Tier | Cracked | Dirty | Normal | Rainbow | Astra | Failed eggs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (owner target) | 50% | 30% | 15% | 4.5% | 0.5% | 40% |
| 1 | 42% | 29% | 22% | 6% | 1% | 33.6% |
| 2 | 34% | 27% | 29% | 8% | 2% | 27.2% |
| 3 | 26% | 24% | 36% | 10.5% | 3.5% | 20.8% |
| 4 | 18% | 21% | 43% | 13% | 5% | 14.4% |
| 5 | 10% | 18% | 49% | 16% | 7% | 8% |
| 6 | 4% | 15% | 52% | 19% | 10% | 3.2% |

The Build 020 table (20/25/45/9/1 ... 2/12/51/25/10) is kept as a comment in
`ProgressionConfig.luau` and in [41](41-egg-outcomes-contract.md) as historical. New eggs
record `traitRollVersion = "bd045-genes-v2"`; saved eggs keep their genes. `EggOutcomeOdds`
normalizes weights (unchanged enumerator), `ShopOdds` now prints normalized percentages,
the odds version and a single "1 dinosaur: 100%" quantity row, and the Condition Shop
cards/confirmation use `ShopOdds.conditionPercents`. **Balancing risk:** 40% of tier-0
eggs fail (about 6 of 15, 60 of 150 on average); flag in playtest.

## PROVISIONAL values

| Key | Value | Where |
| --- | --- | --- |
| `RunEggMaxPerRun` | 300 | `Config.luau` |
| `RunEggBankCapacity` | 600 | `Config.luau` |
| `SettledRunLedgerSize` | 200 | `Config.luau` |
| `NestPendingCapacity` | 30 | `Config.luau` |
| `NestFirstAtEggs` / `NestEggsPerExtraNest` / `NestMaxPerRun` | 15 / 27 / 11 | `Config.luau` |
| `NestEggCount` / `NestIncubationSeconds` / `NestRarityBoostEggs` | 3 / 300 / 15 | `Config.luau` |
| `RunCrystalPerEgg` / `RunCrystalTierEggs` / `RunCrystalPerExtraEggTenths` / `RunCrystalCap` | 2 / 15 / 14 / 500 | `ProgressionConfig.luau` |
| Condition tiers 1-6 | table above | `ProgressionConfig.luau` |
| Account XP | 1 per run egg (unchanged 1 per catch) | `RewardMath.computeRunReward` |

## Offline evidence (2026-10-13, Luau 0.741)

New `tools/verify_rewards.py` (added to CI) runs the real repository against a mocked
DataStore that executes every transform twice and can inject outages:

```
Reward math passed: 0/negative/NaN/inf/huge/non-number scores, 500->15 and 5,000->150 eggs, 30/219 crystals, 1/6 nests, bounded IDs
15-egg run passed: 15 banked eggs (5 queue + 10 bank), no direct copies, 30 crystals, 1 slotted nest, ascending rarity, exactly-once replays
150-egg run passed: 150 eggs revealed in committed ascending order across reconnect; 89 hatched, 61 Cracked failures; trimmed-ledger replay blocked
Failure handling passed: full outage writes nothing, transient outage commits once, lost acknowledgement retried as duplicate, lease loss blocks settlement/claims, retry after recovery is exactly-once
Nests passed: 5 slots + pending, incubation, pending/missing/invalid refusals, opening puts 3 eggs next in line, promotion, duplicate, 20 runs to nests_pending_full gate, no nest ever lost, bank_full refusal
Legacy saves passed: Build 020 profile loads additively, old queued 3-copy/2-copy eggs claim as committed, new run eggs wait behind legacy overflow, old run replay blocked
Event tags passed: catch-ordinal weather/mutation tags land on the right eggs; invalid/oversized tags and run IDs rejected; zero-catch run
Storage passed: 600 banked eggs + 22 nests/pending ~ 324531 bytes (7.7% of 4 MiB)
Identity passed: 15-egg run -> 9 identities for 9 hatched eggs, 6 failed Cracked eggs create none
Seeded draws passed: 20000 tier-0 rolls Cracked 50.11% Dirty 30.21% Normal 14.71% Rainbow 4.51% Astra 0.45%; failed 39.92%
```

Also updated: `verify_eggs.py` (exact enumeration of all seven tiers at 1/10,000
resolution, monotonic upgrades, exactly 20% Cracked success), `verify_outcomes.py`
(BD-045 disclosure: 40% tier-0 failure, every tier sums to 100%, version string, one
dinosaur per egg), `verify_progression.py` (existing repository flows on the new
contract: one copy per egg, one identity per hatch, bank FIFO, crystals 429/149) and
`verify_gameplay.py` (run-start gate). The full CI command set, `bind_artwork.py --check`,
`build.py` and all 37 unit tests pass; `build/` artifacts are rebuilt.

## Open risks / not done

- **Studio verification pending:** run end/death/disconnect settlement, 150-egg reveal
  pacing (~2.5 min at 1 s/egg; was ~12.5 min at 5 s), nest button, run-start gate message, multiplayer/rejoin.
- 150-egg pacing/skip UX and the Uncommon/Epic rarity taxonomy are still open owner
  decisions (current tiers remain Common/Rare/Legendary).
- Purchased eggs still enter the legacy overflow, so they can be revealed before the rest
  of a banked run batch.
- `DinosaurIdentity.MaxInstances = 3000` (memory-only Studio sidecar) will be reached
  faster with many hatches; identity persistence is a separate task.
- PvP catch awards still add catches without weather tags (same as before).
- All PROVISIONAL numbers need owner balance sign-off; the 40% tier-0 failure rate is a
  known playtest risk.
