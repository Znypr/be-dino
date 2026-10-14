# 58. Fusion ladder 50 / 10 / 3 (BD-057 / BD-064 / BD-065)

**Owner decision 2026-10-13:** Gold = **50 Base**, Emerald = **10 Gold**, Diamond = **3 Emerald**. Same species and same
saved egg pattern at every tier; the stage is guaranteed; every donor is consumed into **ONE NEW individual** (new ID,
freshly rolled color/condition/Shiny/BIG/mutation, no cosmetic transfer, consent rules unchanged). This supersedes the
10-donor Gold prototype in [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md). **Studio/device verification is pending**;
all evidence below is offline Luau (`verify_fusion.py`, `verify_fusion_ui.py`, `verify_identity.py`, `verify_progression.py`).

## Implementation
- `IdentityFusion.Recipes`: gold 50/base (`gold-same-species-pattern-50-v1`), emerald 10/gold (`...-10-v1`), diamond 3/emerald (`...-3-v1`); `Version = bd057-ladder-50-10-3`. Quotes require exactly the recipe count; `Fusion.MaxDonorCount = 50`.
- Higher tiers: donors are fused records with saved genes; the pattern comes from `genes.patternId`. Quote digests omit a donor's embedded `origin.parents` (immutable), so a quote stays O(donors).
- Additive grouped projection: optional `collection[species].emerald` counter (nil = 0). `ProfileRepository` validation accepts it, `reconcile` and equip checks count it. Legacy Build 020 Gold -> Diamond (50 Gold) path is unchanged.
- `FusionOdds` normalizes by the actual donor count N (PROVISIONAL, unchanged coefficients): Shiny = 0.5 x shinyDonors/N, BIG, mutation likewise; condition/color wheels proportional to N.
- `FusionService.MaxDonorIds = 50` (exact count still enforced per recipe); [52](52-fusion-remote-contract.md) updated, backward compatible.
- Lineage is bounded and compact: `Identity.fusionRecord` accepts 2..50 parents; speciesId, stage and `genes.patternId` are identical for all parents so they are stored once (`origin.parentStage`; parent snapshots keep genes minus pattern, big/shiny/mutation, origin kind/eggId/operationId). Readers fall back to the result's species/pattern; Dino Details shows the first 12 parents ("Showing 12 of 50").
- `FusionSelection` / `FusionMenu`: slot count from the recipe; counts above 10 render a compact `n/N` progress counter (Android landscape safe, tap a card to deselect); 10 and 3 use slots; auto-fill plain donors up to N; Gold/Emerald/Diamond tabs ACTIVE; quote only at exactly N donors; confirm/reveal/title text generalized.

## Measured sizes (verify_fusion.py, JSON-equivalent bytes)
| Item | Bytes |
|---|---|
| Gold record (50 compact parents) | 12,016 |
| Gold ledger entry | 2,465 |
| Archived parent egg (x50 per Gold) | 227 |
| Emerald record / ledger | 2,734 / 1,125 |
| Diamond record / ledger | 1,226 / ledger measured by the chain test |
| ~per 50-donor Gold fusion, whole sidecar | ~26.8 KB (20 sequential fusions, 1000 archived eggs) |
| Chain sidecar: 30 Gold -> 3 Emerald -> Diamond | 547,567 of 3,200,000 ceiling |

The byte preflight (`MaxSidecarBytes` 3.2 MB) and profile hard ceilings are unchanged and tested at ceiling-1 / exact ceiling for the 50-donor ledger size.

## Tests
- `verify_fusion.py`: 50/10/3 happy paths, full Base -> Gold -> Emerald -> Diamond chain with lineage, reload and replay, wrong counts (49 or 51 Base, 9 or 11 Gold, 2 Emerald), wrong stage, mixed species/pattern at higher tiers, stale quote, consent, idempotency, rollback (input byte-identical), storage limit, odds normalization for N = 50/10/3.
- `verify_fusion_ui.py`: recipe parity (IdentityFusion = FusionSelection = FusionService), Emerald/Diamond auto-fill from fused genes, 50-donor counter, 44 px touch audit at 740x340, quotes only at exactly N.
- `verify_progression.py`: repository and `FusionAction` remote with 50 real hatched donors, 51-donor bad request, wrong-count rejections.

## Risks / open
- Emerald is not shown in the Collection UI (client reads base/gold/diamond only) and Emerald is invisible to legacy readers; additive, nil = 0.
- Odds coefficients remain PROVISIONAL; 50 Base per Gold plus 10 Gold per Emerald is a large grind (see [57](57-fusion-ladder-options.md) for pacing).
- No Studio or device run yet: the 50-slot counter layout and reveal on real Android landscape are unverified.
