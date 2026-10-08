# Main Integration Checklist

Updated 2026-10-08. This is the integration snapshot/checklist, not a replacement
task board. [07-kanban.md](07-kanban.md) remains the canonical task tracker.

## Baseline And Scope

Previous GitHub main: `b8e3824`, visual-kit-013. Integration source: Build 020,
redesign history through `7d4b9e4`, plus UI-motion branch reconciled in `1799536`.
Main now receives this integration and its evidence. GitHub source promotion is
not Roblox experience publication; the published game can still be an older build.

Checked below means code/assets committed and included in main, not fully certified
for public release. Retest these against the same generated Build 020 rather than
mixing scripts from older Studio windows.

## New Since Previous Main

- [x] Mountain island, sanctuary/run flow, food-placement and startup fixes.
- [x] Responsive HUD, shops, collection, egg queue and framed dinosaur previews.
- [x] Layered illustrated navigation/trophy/currency/aura/potion artwork, weather
  and leap icons, owner bindings, configurable layouts and native fallbacks.
- [x] Leap/cooldown and weather countdowns; ordinary weather plus Volcano,
  Northern Lights, Earthquake and Blood Moon with bonuses and inherited mutations.
- [x] Aura shop and enhanced aura, trail, mutation and Shiny effects.
- [x] Crystal map pickups, atomic run-end crystal rewards and crystal-box reveal.
- [x] Crystal random-egg shop, queue capacity protection and immutable purchases.
- [x] Catch XP/account levels and ten level/price/speed/VFX-gated trails.
- [x] Crystal potions, including five-minute Speed Common, with server expiry.
- [x] Cracked/Dirty/Normal/Rainbow/Astra egg conditions; 20% Cracked hatch success,
  condition speed/growth effects and escalating future-egg condition upgrades.
- [x] Independent two-color genes, nine palette families and eight patterns,
  inherited from egg to creature; old saved keys remain valid.
- [x] Independent BIG (size-only 1.2x) and Shiny, stackable with event mutations.
- [x] Five-second ordered hatch reveals, low-to-high rarity and batch rarity bonus.
- [x] Gold/Diamond fusion handling and distinct fusion appearance.
- [x] Map rarity/playtime/Robux-spending leaderboard implementations.
- [x] 22-creature catalog, authored models/UV textures/bones and bounded runtime
  effects/fallbacks. Flying and marine creatures currently use ground movement.
- [x] Final-outcome Details: exact configured combinations, numerical rare odds,
  aggregate failure, filters, lazy pages, rounding notice and next-tier links.
- [x] Six real crystal DeveloperProducts, 49-4999 Robux; reusable product bindings
  and five archived amber pack image masters. Product images are not uploaded yet.
- [x] UI-motion history/evidence merged. Existing latest motion/loading/preview
  behavior retained; newer genetics, failed-hatch and authored-model fixes preserved.
- [x] Reproducible Build 020/Latest delivery, binding checks, tests and evidence.
- [x] Studio sync tool uses explicit UTF-8, with a source roundtrip regression test.

## Current Integration Acceptance

- [x] All 226 Luau sources compiled. Gameplay, progression, genes, growth, outcomes,
  previews, artwork and hatch geometry execution checks passed.
- [x] 37 Python tests pass on an isolated committed integration snapshot.
- [x] All 226 source scripts synced into unpublished disposable Studio copy
  `e3eb431e-61b3-4f56-a5d6-d8dcb40576af`; previous scripts backed up, disabled.
- [x] Fresh client/server Build 020 boot: 22 species, Loaded memory-only profile,
  no persistent player data, both paid release flags false.
- [x] Actual GUI navigation opens final-outcome Details: 37,683,361 outcomes,
  16% failure at tier 0; visible labels fit the actual 583x784 widget viewport.
- [x] Actual upgrade-confirmation navigation shows tier 1's 13.6% failure while
  the player's conditionLevel remains 0; no upgrade purchased.
- [x] FocusLost helper clamps an excessive page to 18,841,681. Real typed page-entry
  acceptance is still open; keyboard text injection did not change the value.
- [x] Actual GUI random-egg purchase denied `random_items_unavailable`, as intended
  by the disabled paid-random release gate; no egg/no debit. Not a purchase pass.
- [x] Disposable server settlement fixture produced one earned egg; normal client
  auto-claim/reveal awarded `1x compy`, Normal, Cream/Blue 53/47, round spots,
  and drained the queue. This is not a full food/run test or persistence test.
- [x] Screenshots archived in [integration evidence](evidence/2026-10-08-main-integration/README.md).
- [x] Play stopped; temporary runtime probes are absent from Edit and generated build.

## Remaining Gates

- [ ] Full same-build end-to-end gameplay, all weather/leap states, ten-trail gates,
  potion expiry, fusion, multi-egg ordering and every creature visual acceptance.
- [ ] Desktop/phone emulator and physical-device layout, frame time, memory and
  thermal checks. Widget captures are not phone-emulator certification.
- [ ] Final odds filtering/page-entry acceptance and paid-random policy approval.
  Random-egg purchases and condition upgrades currently fail closed with registered
  developer products while PaidRandomItemsEnabled is false, including this copy.
- [ ] Real paid receipts/retries, spending leaderboard and Creator Hub product icons.
  CrystalPacksEnabled and PaidRandomItemsEnabled remain false.
- [ ] Published latest non-owner asset/editable API access and owner security setting;
  no new uploaded creature mesh IDs are invented. Studio success is insufficient.
- [ ] Persistent 22-species migration, earned reward save/rejoin, competing sessions,
  real same-server multiplayer and long-session/load verification.
- [ ] Modular egg artwork and authored 3D shell splitting; production balance,
  food-to-egg reward ratio and species-specific flight/swimming/abilities approval.
- [ ] Separate local egg-nest/navigation changes and marketing files being authored
  concurrently are not this tested Git snapshot; integrate after their own commit.

## Maintenance

Update this checklist and 07-kanban with each real acceptance result, naming its
commit/build, profile mode, viewport/device, screenshot and limitations. Keep
unchecked release gates unchecked until actual evidence exists. Never enable paid
flags or publish an experience merely because main was updated.
