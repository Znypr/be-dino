# 58. Fusion ladder 15 / 4 / 2 (BD-057 / BD-064 / BD-065; file name kept from the 50 / 10 / 3 version)

**Owner-approved 2026-10-14 (current): Gold = 15 Base, Emerald = 4 Gold, Diamond = 2 Emerald.** This replaces the 50 / 10 / 3 ladder of 2026-10-13 (Gold 50 Base, Emerald 10 Gold, Diamond 3 Emerald); pacing for the new numbers is in [57 section 12](57-fusion-ladder-options.md). Everything below describes the current 15 / 4 / 2 code; the 50 / 10 / 3 measurements are kept only as history.

Same species and same
saved egg pattern at every tier; the stage is guaranteed; every donor is consumed into **ONE NEW individual** (new ID,
freshly rolled color/condition/Shiny/BIG/mutation, no cosmetic transfer, consent rules unchanged). This supersedes the
10-donor Gold prototype in [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md). **Studio/device verification is pending**;
all evidence below is offline Luau (`verify_fusion.py`, `verify_fusion_ui.py`, `verify_identity.py`, `verify_progression.py`).

## Implementation
- `IdentityFusion.Recipes`: gold 15/base (`gold-same-species-pattern-15-v1`), emerald 4/gold (`...-4-v1`), diamond 2/emerald (`...-2-v1`); `Version = bd057-ladder-15-4-2`. Quotes require exactly the recipe count; `Fusion.MaxDonorCount = 15` (was 50). Recipe version strings changed, so quotes/ledger rows from 50/10/3 builds are not replayable; the fresh playtest store has none.
- Higher tiers: donors are fused records with saved genes; the pattern comes from `genes.patternId`. Quote digests omit a donor's embedded `origin.parents` (immutable), so a quote stays O(donors).
- Additive grouped projection: optional `collection[species].emerald` counter (nil = 0). `ProfileRepository` validation accepts it, `reconcile` and equip checks count it. Legacy Build 020 Gold -> Diamond (50 Gold) mutation path is unchanged (separate from the fusion ladder).
- `FusionOdds` normalizes by the actual donor count N (PROVISIONAL, unchanged coefficients): Shiny = 0.5 x shinyDonors/N, BIG, mutation likewise; condition/color wheels proportional to N.
- `FusionService.MaxDonorIds = 15` (exact count still enforced per recipe); [52](52-fusion-remote-contract.md) updated, backward compatible.
- Lineage is bounded and compact: `Identity.fusionRecord` accepts 2..15 parents (`Identity.MaxFusionParents = 15`); speciesId, stage and `genes.patternId` are identical for all parents so they are stored once (`origin.parentStage`; parent snapshots keep genes minus pattern, big/shiny/mutation, origin kind/eggId/operationId). Readers fall back to the result's species/pattern; Dino Details shows the first 12 parents ("Showing 12 of 15").
- `FusionSelection` / `FusionMenu`: slot count from the recipe; counts above 10 (Gold = 15) render a compact `n/N` progress counter (Android landscape safe, tap a card to deselect); Emerald (4) and Diamond (2) use slots; auto-fill plain donors up to N; Gold/Emerald/Diamond tabs ACTIVE; quote only at exactly N donors; confirm/reveal/title text generalized.

## Measured sizes (verify_fusion.py, JSON-equivalent bytes)
| Item | 15 / 4 / 2 (current) | 50 / 10 / 3 (history) |
|---|---|---|
| Gold record (compact parents) | 3,989 | 12,016 |
| Gold ledger entry | 1,251 | 2,465 |
| Archived parent egg (x15 per Gold; was x50) | 227 | 227 |
| Emerald record / ledger | 1,432 / 896 | 2,734 / 1,125 |
| Diamond record | 1,007 | 1,226 |
| ~per Gold fusion, whole sidecar | ~9.0 KB (20 sequential fusions, 300 archived eggs) | ~26.8 KB |
| Full chain sidecar (8 Gold -> 2 Emerald -> Diamond, plus fixture) | 77,065 of 3,200,000 ceiling (2.4%) | 547,567 (30 Gold -> 3 Emerald -> Diamond) |

A complete Diamond ancestry is 8 Gold + 2 Emerald + 1 Diamond ledgers and 120 archived eggs (about 27 KB of eggs, about 40 KB with ledgers), far below the byte preflight (`MaxSidecarBytes` 3.2 MB) and the profile budget (3.4 MB). The ceilings are unchanged and tested at ceiling-1 / exact ceiling for the 15-donor ledger size.

## Tests
- `verify_fusion.py`: 15/4/2 happy paths, full Base -> Gold -> Emerald -> Diamond chain with lineage, reload and replay, wrong counts (14 or 16 Base, 3 or 5 Gold, 1 Emerald), wrong stage, mixed species/pattern at higher tiers, stale quote, consent, idempotency, rollback (input byte-identical), storage limit, odds normalization for N = 15/4/2 (1 Shiny of 15 = 3.33%, of 4 = 12.5%, of 2 = 25%).
- `verify_fusion_ui.py`: recipe parity (IdentityFusion = FusionSelection = FusionService), Emerald/Diamond auto-fill from fused genes, 15-donor counter, 44 px touch audit at 740x340, quotes only at exactly N.
- `verify_progression.py`: repository and `FusionAction` remote with 15 real hatched donors, 16-donor bad request, wrong-count rejections.

## Risks / open
- Emerald is not shown in the Collection UI (client reads base/gold/diamond only) and Emerald is invisible to legacy readers; additive, nil = 0.
- Odds coefficients remain PROVISIONAL; with fewer donors each Shiny/BIG/mutation donor moves the odds more (1 Shiny of 15 = 3.33%, of 2 = 25%); revisit the coefficients if that proves too lucky. Pacing: [57 section 12](57-fusion-ladder-options.md).
- No Studio or device run yet: the 15-donor counter layout and reveal on real Android landscape are unverified.
