# Crystal Shops and Egg Genetics Acceptance

> **HISTORICAL Build 019 private-test acceptance snapshot.** Original seven-color palette, six-creature weights and other configurations below describe the tested earlier build, not the expanded 22-creature/nine-color/eight-pattern Build 020 on main. Read [Build 020 integration](44-main-integration-checklist.md), [current egg outcome contract](41-egg-outcomes-contract.md) and [owner condition changes BD-045](45-owner-feedback-shop-hud-world-weather-tasks.md). Preserve these test observations; do not treat them as current paid-random disclosure.

2026-10-08; branch `redesign/resources-and-core-fixes`, Build redesign-019.
Canonical task status remains [Kanban](07-kanban.md). This is private-test
implementation evidence, not release certification or approved economy balance.

## Implemented

- One authoritative crystal wallet: existing validated map pickups, run crystals
  and a run-end crystal-box reveal. Nonzero runs grant min(catches * 2, 500),
  plus a box of 5/15/50 with provisional 70/25/5% weights. Zero catches give zero.
- Persistent account XP earned from catches, never crystal receipts. Level is
  min(60, 1 + floor(sqrt(XP / 100))). Purchased currency cannot buy account levels.
- Crystal Shops tabs: existing Auras, ten Trails, random Eggs, Conditions, Crystals.
  White is free; paid trails escalate from Fern at level 3/100 crystals to Astra
  at level 60/8500. Speed rises 1.00 to 1.18x. Existing Fern/Tidal/Nova ownership
  and explicit unequip choices survive migration. Walking ribbons/glitter and
  world Shiny effects respect reduced-effects mode and distance/player budgets.
- Existing Potion Shop retains six consumables. Speed Common costs 20 crystals,
  lasts 300 seconds and gives 1.2x speed; replacement/expiry remain server-owned.
- Random eggs cost 150 crystals, use the existing queue, cannot bypass capacity,
  and commit their reward/genetics once. Retry tokens and atomic wallet debits
  prevent rerolls or duplicate charges. Purchased eggs have no event/Shiny roll.
- Six escalating condition upgrades require levels 3/8/16/28/45/60 and cost
  100/300/800/1800/4000/8500. Only future eggs change distribution. Default weights
  Cracked/Dirty/Normal/Rainbow/Astra are 20/25/45/9/1; final weights 2/12/51/25/10.
- Cracked succeeds 20% of the time. Successful Cracked and Dirty give .8x speed
  and growth, Normal 1x, Rainbow 1.2x, Astra 1.8x, before final shared caps.
  Failed Cracked consumes the egg with no dinosaur/refund; retries remain failed.
- Independent two-slot palette: White 5000, Blue 3000, Green 1200, Pink 500,
  Gold 250, Violet 49, Black 1 out of 10000 each. Blend is an integer 0-100%
  uniformly selected and saved. Black/Black is 1 in 100 million with this balance.
  Egg and hatched dinosaur use the same stored blend; colors are cosmetic.
- BIG is 10%, independent of Shiny, and changes visual scale by 1.2x only.
  Earned irregular-weather Shiny remains 5%; world and preview sparkles add no
  stats. Event mutation stays separate from condition, size, Shiny and colors.
- Explicit fusion previews retain Gold/Diamond rather than inheriting owned genes.

## Artwork and Runtime Fixes

The original painted maps overpowered MeshPart.Color. Exported **38 neutral
512px RGBA masters**, retaining painted luminance/detail and alpha, and uploaded
under verified Studio owner **User 7285577648 / znyprs**. Real image IDs and
original source IDs are in `resources/genetics/texture-bindings.json`.
`tools/bind_visual_assets.py` generates both reusable Luau bindings and authored
`resources/roblox/GeneSurfaces.rbxmx` templates packaged in the place.

Actual LocalScripts cannot assign SurfaceAppearance.ColorMap (Plugin capability).
The client clones authored templates and only changes their permitted Color tint.
Unavailable templates/images preserve original textures. All 38 uploaded images
passed typed ImageLabel preload in the owner client. Bare URI preload caused
false failures; mesh previews likewise now preload MeshPart instances rather
than bare strings, retaining native fallback without discarding valid meshes.

Concurrent shared UI-motion and premium egg composition changes are preserved,
including their separate normal/cracks layers. Full BD-035 pattern/condition/
mutation art is not certified by these two egg images or neutral dinosaur maps.

## Actual Studio Evidence

Only **BeDino-VisualUpgrade.rbxlx**, Studio
`4aa9faee-9d45-4ff3-8780-e046093db182`, GameId/PlaceId 0, was modified.
The published `newbuild` instance was untouched. Tests used disposable in-memory
profiles and temporary server-only fixture scripts, not debug remotes or saved
player grants. Fixture scripts are removed after testing; Studio is stopped.

- Started from an ordinary zero wallet with the preview top-up disabled. Astra
  rejected at level 1 even when a separate early test had a large wallet.
- 100 fixture settlements at 5000 catches advanced XP to 500000 / level 60.
  These are synthetic acceptance runs, not evidence of natural leveling pace.
  Bought all nine paid trails and all six condition upgrades; every expected
  debit matched. Bought/used Speed Common: 20 crystals and 300 seconds.
- Clicked random-egg confirmation through UI: 150 crystals debited and immutable
  Rainbow/BIG genetics joined the same queue (earlier ledger 12315 -> 12165).
- Forced six-species/condition fixtures exercise failed Cracked, Dirty, Normal,
  Rainbow, Astra and successful Cracked. Initial failed Compy gives no extra
  copy; starter Compy remains. Subsequent Raptor, Triceratops, Stegosaurus,
  Tyrannosaurus and Ankylosaurus claim successfully. Low-to-high queue order and
  sequential intervals observed: 5.083, 5.067, 5.050, 5.425, 5.511, 5.064 seconds
  in the seven-egg pass including the purchased egg. Final-source six-egg replay
  finishes with blue/white 80/20 BIG Shiny Ankylosaurus and .8x label.
- Astra + Ember mutation + Astra trail + potion: speed caps at 2.2x / WalkSpeed
  48.4, growth 2.124x, BIG scale 1.2. Dirty + Ember with white/no buff gives
  speed .832 / WalkSpeed 18.304, growth .944. Offline tests cover plain .8x.
- Final live client shows neutral-map blue dinosaur in desktop/phone reveals and
  black/black dinosaur in world. Actual ColorMap/tint probes confirm authored
  templates. Walking Astra shows ribbons, Shiny rate 8 and glitter rate 14.
- Real RunLifecycle fixture with 10 catches shows +5 crystal box, +25 banked
  total and wallet 12270 -> 12295 before hatching. No grant happens in the reveal.
- Desktop custom 1366x768 (camera 1365x768) and iPhone 17 Pro landscape
  (camera 750x381) inspected; MCP screenshots may be scaled to Studio widget.
  No clipping/overlap in final shop, condition and hatch captures. Physical touch,
  hardware performance and portrait are not certified.
- Final replay console: only `[Be Dino] redesign-019 ready. Resource redesign.`
  Earlier PBR capability errors were diagnosed and fixed, not counted as passes.

Screenshots and machine-readable observations: [evidence archive](evidence/2026-10-08-crystal-shops-genetics/README.md).

## Automated Verification

**Feature commit: `2d3b637`. All 29 Python tests pass; 61 Luau sources compile.**
Real Luau execution checks progression/profile atomicity,
duplicate/conflicting tokens, queue capacity, failed-hatch retry/rejoin, future-only
upgrades, receipt retry deduplication, published/local isolation, migration,
policy fail-closed behavior, cap/debuff composition, all seven distributions,
20% hatch success, weighted palette, independent traits and size-only BIG.
Gameplay, geometry/framing, artwork and generated-binding checks also pass.
Python asset/build tests validate masters, actual IDs, authored PBR templates and
source/build roundtrip. See the final test result in the evidence manifest.

## Remaining Gates

- **Robux packs:** six real DeveloperProducts are configured, from 500 crystals /
  49 Robux to 90000 / 4999; managed pricing enabled. Creator Hub and Studio lookup
  verified. `CrystalPacksEnabled=false` prevents prompts until release review.
  Product image uploads are blocked by browser file chooser tooling; in-game
  crystal rows reuse the existing amber illustration. Actual payment, receipt
  delivery and spending leaderboard are not tested.
- **Paid randomness:** release flag defaults false. If product IDs are configured,
  random eggs and condition upgrades require the explicit flag plus server
  PolicyService eligibility; unknown/restricted policies deny. Factorized odds
  UI exists, but complete combined-outcome disclosure and policy review are not
  certified. Keep disabled until compliant. See [Roblox paid-random-item rules](https://create.roblox.com/docs/production/monetization/paid-random-items).
- Actual two-client shop isolation/locks/retry passed using disposable local
  profiles. [Follow-up evidence](evidence/2026-10-08-pending-gates/README.md).
- Saved-profile restart, broader multiplayer/load, non-owner asset access,
  real phone/load tests and release rollback need a controlled private experience.
  No published persistent data was accessed for this acceptance run.
- Approve/tune provisional crystal/XP/price/condition/color curves. Full modular
  condition/pattern/mutation artwork remain separate work. Premium art fallback
  now passes forced-missing-image/reveal-cleanup in the owner client.
