# Pending-Gate Follow-Up

2026-10-08, Build redesign-019. Only unpublished VisualUpgrade Studio
`4aa9faee-9d45-4ff3-8780-e046093db182` was modified. Persistent player data was untouched.

## Real Product Definitions

Universe 10769812255; User 7285577648 / znyprs, verified against published Studio
metadata and Creator Hub. Private experience remains named `newbuild`; no publish
or name change. Six actual products are recorded in
`resources/monetization/crystal-products.json`; `tools/bind_products.py --check`
validates generated Config mappings without changing release flags.

| Crystals | Default Robux | Product ID |
| --- | --- | --- |
| 500 | 49 | 3717200374 |
| 1500 | 129 | 3717200467 |
| 4000 | 299 | 3717200523 |
| 10000 | 699 | 3717200920 |
| 25000 | 1499 | 3717200940 |
| 90000 | 4999 | 3717200979 |

[Creator Hub screenshot](crystal-products.png) shows all six products. Managed
pricing is enabled. Studio Marketplace lookup resolves all six names and returns
localized prices 45/117/270/630/1350/4500; these are not default-price mismatches.
Creator IDs in this API response are zero and are not used as ownership evidence.
IconImageAssetId 88963008124478 is Roblox's default cube, not our crystal artwork.
Two browser file chooser attempts failed; no crystal product image upload succeeded.
The intended illustrated master is `resources/ui/v2/icons/amber.png`; the in-game shop already
uses this illustration, now also repeated beside each pack button.

No paid purchase or receipt delivery was performed. Both `CrystalPacksEnabled`
and `PaidRandomItemsEnabled` remain false. With configured products, existing
fail-closed policy also pauses random egg and condition-upgrade purchases,
including earned-currency ones, until disclosure/release checks are complete.
Deterministic trail/potion/aura purchases remain available. Products being created
and marked for sale in Creator Hub does not certify in-game release readiness.

## Actual Multiplayer Test

`StudioTestService:ExecuteMultiplayerTestAsync(2,"shops-private-v1")` ran actual
clients -2 and -1, with test wallet replenishment disabled and GameId/PlaceId 0.
Reusable guarded harnesses in `tools/qa/` are never packaged in the game.
To replay, temporarily set the local Edit Config wallet flag false and product
catalog empty before startup, install server/client harnesses in ServerScriptService
and StarterGui, run the named StudioTestService test, then restore Config and remove
fixtures. This is earned-only testing, not a paid-policy bypass or real receipt test.
[Machine-readable result](multiplayer.json): passed, actualClients=true, persistent=false.

- Only A received server fixture grants; client grant attempts changed neither wallet.
- Both clients received `level_locked` for Astra at level 1.
- 100 synthetic run settlements advanced A to level 60; B remained level 1.
- A bought/equipped Astra and bought Speed Common; B stayed unchanged.
- Concurrent identical egg tokens returned `egg_purchased` and `duplicate`,
  debited 150 once, and produced one A queue entry versus zero B entries.
- Final wallets A 52350, B 0; speeds A 1.18x, B 1x. Broader load/physics is not certified.

## Native Hatch Fallback

Actual LocalScript probe preloaded the normal shell/cracks successfully and forced
empty asset bindings for a second egg. Native viewport remained visible; crack
images/fragments stayed hidden for missing artwork. Reveal cleanup passed after
one second. Preload cannot re-show the shell once opening begins.
[Screenshot](hatch-fallback-phone.png) shows both eggs in a 583x763 Studio widget;
the filename is historical and does NOT certify a phone emulator or responsive
shop layout. This is a temporary presentation probe, not the production hatch panel.
Console contained a startup `BeDinoRemotes` infinite-yield warning before server
ready; no fallback exception. Do not label this run a clean-console pass.
Probe/fixtures removed and Studio stopped afterward.

## Final Crystal Shop UI

Final source was synced to unpublished Studio. [Upper packs](crystal-shop-owner-widget.png)
and [lower packs](crystal-shop-larger-packs.png) show the existing illustrated crystal
beside each option, localized prices, all six scrollable rows and `COMING SOON`.
All six purchase buttons report Active=false with the release flag closed.
Final replay console contains only the Build 019 ready message. These 583x763
widget captures are not additional desktop/phone-emulator certification.

Verification: 31 Python tests pass, 61 runtime Luau sources compile; real Luau
progression and hatch-fragment checks pass. Build 019 regenerated from source.

Physical-phone performance, non-owner asset permissions, real payment delivery,
saved-profile restart and complete combined-outcome paid-random disclosure remain
open. Modular pattern/condition/mutation artwork is not approved by this pass.
