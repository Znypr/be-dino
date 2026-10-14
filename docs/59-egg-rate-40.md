# 59. Egg rate 40 per 500 food (owner decision 2026-10-13)

**Status: implemented in config and offline tests; PROVISIONAL values; Studio verification pending; not released.** Supersedes the 15-per-500 / 150-per-5,000 figures of BD-044 ([50](50-bd044-reward-loop.md), [09](09-reward-economy.md), `AGENTS.md`). The fusion ladder (Gold 50, Emerald 10 Gold, Diamond 3 Emerald) is implemented on another branch; pacing evidence is in [57 section 11](57-fusion-ladder-options.md).

## Owner decision

Hatching many eggs is normal: **40 catches (= 40 run eggs) per 500 food**, 5,000 food -> 400 eggs. Still exactly one egg per catch and one dinosaur per successful hatch.

## Changes and values

| Value | Old | New (PROVISIONAL) | Reason |
|---|---|---|---|
| `Config.FoodCatchRate` | 15/500 | **40/500** | owner decision |
| `Config.MaxCatchScore` | 5000 | 5000 (unchanged) | catch-count cap above `RunEggMaxPerRun`; not binding |
| `Config.RunEggMaxPerRun` | 300 | **500** (= 6,250 food) | a 5,000-food run (400 eggs) is not truncated; bounded storage |
| `Config.RunEggBankCapacity` | 600 | **1000** | ~0.5 KB/egg: full bank about 0.5 MB; run start gate `banked > 1000 - 500 = 500` (was `> 300`) |
| Crystals | `min(500, 2*min(n,15)+floor(1.4*max(0,n-15)))` | `min(300, floor((75*min(n,40)+53*max(0,n-40))/100))` (`ProgressionConfig.RunCrystal*Hundredths`) | 40 eggs -> 30, 400 -> 220 (the owner's illustrative 30/220), 500 -> 273, cap 300 |
| `NestFirstAtEggs` / `NestEggsPerExtraNest` | 15 / 27 | **40 / 72** | same shape rescaled: 40 eggs -> 1 nest, 400 -> 6 (5 slotted + 1 pending) |
| `NestMaxPerRun` | 11 | **8** (500 eggs -> 7) | pending gate `pending > 30 - 8 = 22` (was `> 19`) |
| `HatchPageSize`, `HatchRevealSeconds` | 10, 1 s | unchanged | a 400-egg run reveals in about 6.7 min |
| `DinosaurIdentity.MaxInstances` | 3000 | 3000 (unchanged, see risks) | profile bytes |

Example: 500 food -> 40 eggs, 30 crystals, 1 nest; 5,000 food -> 400 eggs, 220 crystals, 6 nests (5 claimable, 1 pending); at the 500-egg cap, 273 crystals, 7 nests.

## Evidence (offline)

* `verify_gameplay`: 500 food = 40 catches, weather x2 = 80. `verify_rewards`: 400-egg run credited in 40 hatch-page transactions, reconnect mid-page, conserved eggs, crystals 0/30/220/273, nests 0/1/6/7, nest and egg-bank run gates, full bank = 1,000 eggs ~ 502 KB profile (12% of 4 MiB; was 600 eggs ~ 325 KB). `verify_progression`: a 600-catch run clamps to 500 eggs.
* `verify_load` (8 and 12 players, gated) passes; projection with all players revealing at 1 s and 10-egg pages: 8 players x 400 eggs 76% of budget, 12 players x 400 eggs 77% (x 40 eggs: 65% / 64%).
* `simulate_fusion_ladder.py --check` asserts `FoodCatchRate = 40 / 500`.

## Risks / Studio pending

1. **Per-key write volume:** the report-only `egg-burst-400-x12` scenario writes about 5.2 MB/min to one profile key (profile up to ~0.5 MB, many writes per minute), above the 4 MB/min per-key limit. Gated 8/12-player scenarios pass; a full-bank player claiming continuously may throttle. Candidates: larger hatch pages for big banks, or a compact egg record.
2. **Identity cap:** 3,000 identity instances (about 3 MB worst case in the identity measurement, 72% of 4 MiB) are reached after about 5,000 eggs (42 casual days, 3.4 heavy days), and a 1,000-egg bank adds about 0.5 MB, close to the 4 MiB DataStore value limit. Raising the cap is not safe without a compact identity format; stacking/compaction needs an owner decision.
3. A 400-egg run is 6.7 minutes of reveals at 1 s/egg; skip/summary UX is still open.
4. Fusion pacing (57 section 11): Gold about 18 casual days, Emerald about 209, Diamond about 644 (heavy 1.4 / 17 / 52).
5. Crystal, nest, cap and gate values are provisional and need balance sign-off; Uncommon/Epic rarity tiers are still not implemented; no Studio or device acceptance has been done.
