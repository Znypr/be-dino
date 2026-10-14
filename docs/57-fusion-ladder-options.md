# 57. Fusion ladder cost options (Emerald and Diamond) - BD-057 / BD-058

**STATUS: simulation for an OWNER DECISION (owner request 2026-10-13: "Simulate options and show me").
No Emerald/Diamond cost is chosen or approved.** `Fusion.Recipes.emerald/diamond.donorCount` stay `nil` until the owner picks.
**UPDATE 2026-10-14: the owner approved Gold 15 Base / Emerald 4 Gold / Diamond 2 Emerald; see section 12 (sections 1-11 are the history of the options and the superseded 50/10/3).**
**This is a model, not measured gameplay.** Tool: `python tools/simulate_fusion_ladder.py` (deterministic; `--check` is a CI guard).
Source rules: [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md) section 1, [49](49-identity-fusion-phase1.md), [53](53-bd064-fusion-server.md).

## 1. Assumptions (all labelled; change them with the CLI flags)

| # | Assumption | Source / label |
|---|---|---|
| A1 | 22 species, weights from `Config.ChestSpeciesWeights` (Compy 25, Raptor 20, Triceratops 10, ... Tyrannosaurus 1, Therizinosaurus 0.5; sum 100) | read from repo |
| A2 | 8 patterns, uniform | doc 46 |
| A3 | Tier-0 conditions 50/30/15/4.5/0.5 (`ConditionWeights[1]`), Cracked hatch success 20%, so hatch success ps = **60%** (40% of eggs fail) | owner target + repo |
| A4 | Exactly **1 dino per hatched egg** | owner decision 2026-10-13 |
| A5 | Egg supply per run: **15** eggs (500 food) or **150** eggs (5,000 food) | AGENTS.md owner examples |
| A6 | **Casual** = 1 session/day = 3 runs x 15 = **45 eggs/day**. **Heavy** = 10 runs/day (7 x 15 + 3 x 150) = **555 eggs/day** | ASSUMPTION (CLI parameters) |
| A7 | Every fusion needs same species AND same pattern; the output keeps both, so d Gold per Emerald and e Emerald per Diamond cost exactly **10 x d x e Base dinos of one species+pattern** | doc 46 recipe lock |
| A8 | **Baseline only**: no pattern research (BD-063), no trading, no Robux, no weather/species-boost effects, no donors lost to protection/locks, condition upgrade tier 0 (sensitivity in section 5) | scope |
| A9 | A player fuses as soon as a cell reaches the needed count; nothing wasted | simplification |
| A10 | "Days" = eggs / eggs per day, play every day | simplification |

Two goals are shown. **Targeted** = one chosen species+pattern ("I want a Wavy-Stripes Compy"). **Any one** = whichever of the 176 species+pattern cells first reaches the required Base count (birthday-style; best case for a player who fuses whatever they collect). Real players sit between the two. Monte Carlo: 5000 targeted trials, 1000 any-one trials, seed 57. p10/p50/p90 are percentiles across simulated players (luck).

## 2. Candidate recipes

Emerald = **d** Gold donors (d = 2, 3, 4, 5). Diamond = **e** Emerald donors (e = 2, 3, 4). Total Base-equivalents to reach the tier from scratch:

| Emerald d \ Diamond e | e=2 | e=3 | e=4 |
|---|---:|---:|---:|
| d=2 (Emerald costs 20 Base) | 40 | 60 | 80 |
| d=3 (Emerald costs 30 Base) | 60 | 90 | 120 |
| d=4 (Emerald costs 40 Base) | 80 | 120 | 160 |
| d=5 (Emerald costs 50 Base) | 100 | 150 | 200 |

## 3. Results: "any one" species+pattern (headline)

Gold and Emerald:

| Recipe | Base | eggs p10 | eggs p50 | eggs p90 | runs p50 (casual) | days p50 casual (p10-p90) | days p50 heavy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gold = 10 Base | 10 | 226 | 306 | 387 | 20 | 6.8 (5.0-8.6) | 0.6 |
| Emerald = 2 Gold | 20 | 606 | 745 | 861 | 50 | 17 (13-19) | 1.3 |
| Emerald = 3 Gold | 30 | 1029 | 1214 | 1374 | 81 | 27 (23-31) | 2.2 |
| Emerald = 4 Gold | 40 | 1481 | 1687 | 1890 | 112 | 37 (33-42) | 3.0 |
| Emerald = 5 Gold | 50 | 1916 | 2171 | 2394 | 145 | 48 (43-53) | 3.9 |

Diamond (total from Base; includes the Gold and Emerald stages on the way):

| Recipe | Base | eggs p10 | eggs p50 | eggs p90 | runs p50 (casual) | days p50 casual (p10-p90) | days p50 heavy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Diamond = 2 Emerald (Emerald = 2 Gold) | 40 | 1481 | 1687 | 1890 | 112 | 37 (33-42) | 3.0 |
| Diamond = 3 Emerald (Emerald = 2 Gold) | 60 | 2366 | 2648 | 2899 | 177 | 59 (53-64) | 4.8 |
| Diamond = 4 Emerald (Emerald = 2 Gold) | 80 | 3304 | 3612 | 3907 | 241 | 80 (73-87) | 6.5 |
| Diamond = 2 Emerald (Emerald = 3 Gold) | 60 | 2366 | 2648 | 2899 | 177 | 59 (53-64) | 4.8 |
| Diamond = 3 Emerald (Emerald = 3 Gold) | 90 | 3745 | 4103 | 4433 | 274 | 91 (83-99) | 7.4 |
| Diamond = 4 Emerald (Emerald = 3 Gold) | 120 | 5168 | 5597 | 5987 | 373 | 124 (115-133) | 10 |
| Diamond = 2 Emerald (Emerald = 4 Gold) | 80 | 3304 | 3612 | 3907 | 241 | 80 (73-87) | 6.5 |
| Diamond = 3 Emerald (Emerald = 4 Gold) | 120 | 5168 | 5597 | 5987 | 373 | 124 (115-133) | 10 |
| Diamond = 4 Emerald (Emerald = 4 Gold) | 160 | 7083 | 7632 | 8100 | 509 | 170 (157-180) | 14 |
| Diamond = 2 Emerald (Emerald = 5 Gold) | 100 | 4220 | 4605 | 4956 | 307 | 102 (94-110) | 8.3 |
| Diamond = 3 Emerald (Emerald = 5 Gold) | 150 | 6598 | 7102 | 7571 | 473 | 158 (147-168) | 13 |
| Diamond = 4 Emerald (Emerald = 5 Gold) | 200 | 9064 | 9654 | 10147 | 644 | 215 (201-225) | 17 |

## 4. Results: targeted species+pattern

**Compy (25% of species, the easiest target; each Compy pattern is 3.1% of hatches):**

| Recipe | Base | eggs p10 | eggs p50 | eggs p90 | runs p50 (casual) | days p50 casual (p10-p90) | days p50 heavy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gold = 10 Base | 10 | 333 | 517 | 759 | 34 | 11 (7.4-17) | 0.9 |
| Emerald = 2 Gold | 20 | 772 | 1047 | 1382 | 70 | 23 (17-31) | 1.9 |
| Emerald = 3 Gold | 30 | 1231 | 1583 | 1992 | 106 | 35 (27-44) | 2.9 |
| Emerald = 4 Gold | 40 | 1712 | 2127 | 2586 | 142 | 47 (38-57) | 3.8 |
| Emerald = 5 Gold | 50 | 2201 | 2653 | 3164 | 177 | 59 (49-70) | 4.8 |

| Recipe | Base | eggs p10 | eggs p50 | eggs p90 | runs p50 (casual) | days p50 casual (p10-p90) | days p50 heavy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Diamond = 2 Emerald (Emerald = 2 Gold) | 40 | 1712 | 2127 | 2586 | 142 | 47 (38-57) | 3.8 |
| Diamond = 3 Emerald (Emerald = 2 Gold) | 60 | 2681 | 3182 | 3731 | 212 | 71 (60-83) | 5.7 |
| Diamond = 4 Emerald (Emerald = 2 Gold) | 80 | 3677 | 4254 | 4875 | 284 | 95 (82-108) | 7.7 |
| Diamond = 2 Emerald (Emerald = 3 Gold) | 60 | 2681 | 3182 | 3731 | 212 | 71 (60-83) | 5.7 |
| Diamond = 3 Emerald (Emerald = 3 Gold) | 90 | 4176 | 4787 | 5443 | 319 | 106 (93-121) | 8.6 |
| Diamond = 4 Emerald (Emerald = 3 Gold) | 120 | 5694 | 6389 | 7135 | 426 | 142 (127-159) | 12 |
| Diamond = 2 Emerald (Emerald = 4 Gold) | 80 | 3677 | 4254 | 4875 | 284 | 95 (82-108) | 7.7 |
| Diamond = 3 Emerald (Emerald = 4 Gold) | 120 | 5694 | 6389 | 7135 | 426 | 142 (127-159) | 12 |
| Diamond = 4 Emerald (Emerald = 4 Gold) | 160 | 7703 | 8519 | 9400 | 568 | 189 (171-209) | 15 |
| Diamond = 2 Emerald (Emerald = 5 Gold) | 100 | 4676 | 5319 | 6001 | 355 | 118 (104-133) | 9.6 |
| Diamond = 3 Emerald (Emerald = 5 Gold) | 150 | 7203 | 7982 | 8813 | 532 | 177 (160-196) | 14 |
| Diamond = 4 Emerald (Emerald = 5 Gold) | 200 | 9737 | 10665 | 11619 | 711 | 237 (216-258) | 19 |

**Rarer targets (selected recipes only).** Targeted cost scales with 1/weight: Triceratops (weight 10) is 2.5x the Compy cost, Tyrannosaurus (weight 1) is 25x. A *specific* rare species+pattern is therefore a very long goal at any of these recipes; BD-063 pattern research matters more than donor count if rare-species fusion should be reachable.

Triceratops:

| Recipe | Base | eggs p10 | eggs p50 | eggs p90 | runs p50 (casual) | days p50 casual (p10-p90) | days p50 heavy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gold = 10 Base | 10 | 827 | 1292 | 1900 | 86 | 29 (18-42) | 2.3 |
| Emerald = 2 Gold | 20 | 1926 | 2620 | 3458 | 175 | 58 (43-77) | 4.7 |
| Emerald = 3 Gold | 30 | 3076 | 3958 | 4986 | 264 | 88 (68-111) | 7.1 |
| Diamond = 2 Emerald (Emerald = 2 Gold) | 40 | 4275 | 5317 | 6478 | 354 | 118 (95-144) | 9.6 |

Tyrannosaurus:

| Recipe | Base | eggs p10 | eggs p50 | eggs p90 | runs p50 (casual) | days p50 casual (p10-p90) | days p50 heavy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gold = 10 Base | 10 | 8250 | 12921 | 19031 | 861 | 287 (183-423) | 23 |
| Emerald = 2 Gold | 20 | 19232 | 26190 | 34596 | 1746 | 582 (427-769) | 47 |
| Emerald = 3 Gold | 30 | 30725 | 39591 | 49884 | 2639 | 880 (683-1109) | 71 |
| Diamond = 2 Emerald (Emerald = 2 Gold) | 40 | 42707 | 53172 | 64801 | 3545 | 1182 (949-1440) | 96 |

## 5. Sensitivity: condition upgrades (any-one, p50 eggs / casual days)

Hatch success rises from 60% (tier 0) to 79.2% (tier 3) and 96.8% (tier 6) on the provisional `ConditionWeights` curve (`--tier 3`, `--tier 6`):

| Recipe | tier 0 | tier 3 | tier 6 |
|---|---:|---:|---:|
| Gold | 306 eggs / 6.8 d | 231 / 5.1 d | 189 / 4.2 d |
| Emerald = 2 Gold | 745 / 17 d | 563 / 13 d | 461 / 10 d |
| Diamond = 2 x (Emerald = 2 Gold) | 1,687 / 37 d | 1,277 / 28 d | 1,043 / 23 d |

Upgrades shorten everything by at most about 40%; pacing is dominated by Base counts.

## 6. Reading the numbers

* Gold (10 Base): about a week any-one (5-9 days p10-p90), about 11 days (7-17) if the player insists on one Compy pattern.
* Emerald d=2 (20 Base): about 17 days (13-19) any-one, 23 days targeted-Compy, casual; about 1.3 days heavy. d=3 is about 4 weeks; d=4-5 is 5-7+ weeks casual.
* Diamond d=2,e=2 (40 Base): about 37 days (33-42) casual any-one, 47 days targeted-Compy; about 3 days heavy. d=2,e=3 (60 Base): about 59 days casual, 4.8 days heavy. 80+ Base is 80+ days casual.
* Any-one spread is narrow (about +-15% p10-p90); targeted Gold is wide (p90 about 1.5x p50).
* Heavy vs casual is about 12x (555 vs 45 eggs/day): a milestone for casual players is quick for heavy ones, so BD-058 caps/weekly rules must be set with that gap in mind.

## 7. Recommendation (PROPOSED, NOT owner-approved)

Proposed target feel for a baseline casual player (**proposal, not approved**): Gold in days, Emerald in 1-2 weeks, Diamond in 1-2 months.

* **Gold = 10 Base** (existing): about 5-9 days any-one; fits "days".
* **Emerald = 2 Gold (20 Base):** the only candidate near "1-2 weeks" (about 17 days any-one, 13-19). d=3 (about 27 days) and above miss it for casual players.
* **Diamond = 2 Emerald (40 Base total):** about 37 days any-one (inside "1-2 months"). Diamond = 3 Emerald (60 Base, about 59 days) is the longer-end alternative if Diamond should feel clearly late-game. 4 Emerald (80 Base) or more is a 3-month goal.
* Trade-off: **2/2 gives heavy players Diamond in about 3 days**, possibly too fast. If that matters, prefer 2/3 and use BD-058 stat gating or non-donor materials for heavy players rather than bigger donor counts that punish casual players.
* Rare-species targets should be helped by pattern research (BD-063), not by lowering donor counts.

## 8. Exact config to set once the owner picks (do not apply before approval)

`src/server/IdentityFusion.luau`, `Fusion.Recipes` (version strings are placeholders naming the choice):

```lua
emerald = {targetStage = "emerald", sourceStage = "gold", donorCount = <d>, version = "emerald-same-species-pattern-<d>-v1"},
diamond = {targetStage = "diamond", sourceStage = "emerald", donorCount = <e>, version = "diamond-same-species-pattern-<e>-v1"},
```

Recommended candidate would be `<d> = 2`, `<e> = 2` (or `<e> = 3`). Before enabling Emerald also: the additive grouped-collection change noted at `Fusion.GroupedProjection` (Emerald is not representable yet), updated donor-count expectations in `tools/verify_fusion.py` / `tools/verify_fusion_ui.py`, and the BD-064 odds disclosure for the new donor counts. `Config.DiamondMutationCost = 50` is the older Build 020 mutation path and needs its own owner decision.

## 9. Caveats

* **Model, not measured gameplay.** Real eggs/run depend on the unmeasured BD-044 run loop; rare-species boosts for 15+ egg batches lower Compy's share and are not modelled; weather, events, bonus nests and trading are omitted (nests would shorten real times).
* Players do not fuse optimally or concentrate on one cell: targeted tables are pessimistic, any-one tables optimistic.
* Pattern research, vouchers and Robux are excluded by design (A8).
* Percentiles are across simulated players, not across days for one player.

## 10. Reproduce

```
python tools/simulate_fusion_ladder.py                     # tables above
python tools/simulate_fusion_ladder.py --tier 3 --targets compy
python tools/simulate_fusion_ladder.py --casual-runs 2 --heavy-big-runs 5
python tools/simulate_fusion_ladder.py --check             # CI: 2k trials, monotonicity, ~1 s
```

## 11. Previous ladder 50/10/3 at 40 eggs per 500 food (2026-10-13; SUPERSEDED by section 12)

**Owner decisions 2026-10-13 (authoritative):** Gold = **50 Base**, Emerald = **10 Gold**, Diamond = **3 Emerald**, always the same species + pattern; and **40 eggs per 500 food** (5,000 food = 400 eggs, see [59](59-egg-rate-40.md)). Sections 1-10 above are the earlier candidate comparison (15/150 eggs, Gold = 10 Base) and are kept as history; they are reproducible with `--gold-donors 10 --emerald-donors 2 3 4 5 --diamond-donors 2 3 4 --eggs-small 15 --eggs-big 150`. `python tools/simulate_fusion_ladder.py` now defaults to the owner ladder. **Model, not measured gameplay**; assumptions A1-A4 and A7-A10 unchanged (tier-0 hatch success 60%, one dino per hatched egg).

Cost in Base dinos of ONE species+pattern cell: Gold 50, Emerald 10 x 50 = **500**, Diamond 3 x 500 = **1,500**.

Egg supply (ASSUMPTIONS, CLI flags): **casual** = 3 runs x 40 eggs = **120 eggs/day**; **heavy** = 10 runs/day, 3 of them 400-egg (5,000-food) runs and 7 x 40 = **1,480 eggs/day**.

### Any one species+pattern (best case, first of 176 cells to reach the count)

| Tier | Base | eggs p10 | eggs p50 | eggs p90 | days casual p10 / p50 / p90 | days heavy p50 |
|---|---:|---:|---:|---:|---|---:|
| Gold | 50 | 1,902 | 2,141 | 2,386 | 16 / 18 / 20 | 1.4 |
| Emerald (from scratch) | 500 | 24,203 | 25,050 | 25,801 | 202 / 209 / 215 | 17 |
| Diamond (from scratch) | 1,500 | 76,012 | 77,271 | 78,706 | 633 / 644 / 656 | 52 |

### Targeted Compy (25% of species; one pattern = 3.1% of hatches)

| Tier | Base | eggs p10 | eggs p50 | eggs p90 | days casual p10 / p50 / p90 | days heavy p50 |
|---|---:|---:|---:|---:|---|---:|
| Gold | 50 | 2,207 | 2,644 | 3,158 | 18 / 22 / 26 | 1.8 |
| Emerald | 500 | 25,095 | 26,683 | 28,160 | 209 / 222 / 235 | 18 |
| Diamond | 1,500 | 77,352 | 79,957 | 82,694 | 645 / 666 / 689 | 54 |

### Targeted rare species (weight 10 Triceratops; weight 1 Tyrannosaurus), p50

| Tier | Triceratops eggs | casual days | heavy days | Tyrannosaurus eggs | casual days | heavy days |
|---|---:|---:|---:|---:|---:|---:|
| Gold | 6,612 | 55 | 4.5 | 66,096 | 551 | 45 |
| Emerald | 66,710 | 556 | 45 | 667,118 | 5,559 | 451 |
| Diamond | 199,899 | 1,666 | 135 | 1,999,003 | 16,658 | 1,351 |

(p10-p90 for Triceratops Gold: casual 46-66 days; Tyrannosaurus Gold: 459-659 days.)

### Sensitivity: condition upgrades (targeted Compy p50 casual days)

Tier 3 (79.2% hatch success): Gold 17, Emerald 169, Diamond 505. Tier 6 (96.8%): Gold 14, Emerald 138, Diamond 413. Upgrades shorten the ladder by at most about 35-40%.

### Plain-language summary

* **Is Gold quick?** For a casual player (one short session, 120 eggs/day), no: about **18 days** for the first Gold of any species+pattern (16-20), about 22 days if they insist on one Compy pattern. A heavy player (1,480 eggs/day) gets it in **about 1.5 days**. 50 Base is 5x the old 10-Base Gold; the egg-rate rise (2.7x) only partly offsets it.
* **Emerald?** Casual about **7 months (209 days)** any-one, 222 days for a Compy pattern; heavy about **17 days**. Emerald needs 500 Base of one cell.
* **Diamond?** Casual about **21 months (644 days)**; heavy about **52 days** (about 7.5 weeks). Diamond needs 1,500 Base of one cell.
* Casual vs heavy is about 12x apart. A rare-species Diamond (Triceratops about 135 heavy days, Tyrannosaurus years) is effectively out of reach without pattern research (BD-063), trading or non-egg materials. These are **owner-set costs**; this section reports pacing and does not change them. The levers are the egg rate or the 50 / 10 / 3 counts.
* Storage implication: Diamond needs 1,500 same-cell Base dinos, but a player also holds every other hatched dino. `DinosaurIdentity.MaxInstances = 3000` is reached after about 5,000 eggs (60% hatch success): about 42 casual days or 3.4 heavy days. See [59](59-egg-rate-40.md) risks.

Reproduce: `python tools/simulate_fusion_ladder.py --any-trials 150 --trials 3000` (6 s); `--tier 3|6`; `--check` (CI, about 1 s, also asserts the 40/500 conversion and owner-ladder monotonicity).

## 12. Owner-approved ladder 15/4/2 (2026-10-14)

**Owner decision 2026-10-14 (current, authoritative):** Gold = **15 Base**, Emerald = **4 Gold**, Diamond = **2 Emerald**, same species + pattern at every tier. This replaces the 50/10/3 of section 11; code and tests now use 15/4/2 ([58](58-fusion-ladder-50-10-3.md)).

Cost in Base dinos of ONE species+pattern cell: Gold 15, Emerald 4 x 15 = **60**, Diamond 2 x 60 = **120**.

**Assumption: 1 hour of heavy play = 180 hatched dinos** (at 60% tier-0 hatch success that is 300 eggs per hour). Model, not measured gameplay.

Median (p50) hours until the FIRST Gold / Emerald / Diamond of any one species+pattern (best case: first of 176 cells to reach the count; 3,000-trial seeded `any_cell` run):

| Stage | Base dinos of one cell | Dinos hatched (p50) | Median hours at 180 dinos/h |
|---|---:|---:|---:|
| Gold (15 Base) | 15 | about 310 | **1.7 h** |
| Emerald (4 Gold) | 60 | about 1,590 | **8.8 h** |
| Diamond (2 Emerald) | 120 | about 3,360 | **18.7 h** |

Reproduce: `python tools/simulate_fusion_ladder.py --hours` (about 1 s). `--check` (CI) asserts the recipes in `IdentityFusion.luau` are 15/4/2 and that the three medians stay inside 1.3-2.2 h, 7.0-10.5 h and 15.0-22.0 h. A specific target (a chosen species and pattern) is much slower, as in section 11: rare species stay out of reach without pattern research (BD-063) or trading.

Storage: a complete Diamond is 8 Gold + 2 Emerald + 1 Diamond ledgers and 120 archived parent eggs, about 40 KB in the sidecar versus the 3.2 MB ceiling ([58](58-fusion-ladder-50-10-3.md)).

