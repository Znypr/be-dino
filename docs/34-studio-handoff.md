# Build 019: ready for Studio acceptance

Branch: `redesign/resources-and-core-fixes`. This is the current handoff; earlier build/audit documents are historical. Source and offline checks are complete. Studio physics, rendering, mobile performance, asset permissions and multiplayer acceptance are still pending.

2026-10-08 update: connected Build 019 was verified through Studio MCP. All nine PNG
masters were uploaded under the verified experience owner, bound, and successfully
loaded in the owner Studio client. A phone navigation/joystick overlap was corrected
in source. See the canonical Build 019 evidence table in `docs/07-kanban.md` for
passed, partial and pending cases. The connected place is published and uses persistent
profiles, so it did not provide disposable wallets/copies/eggs for full acceptance.

Follow-up: a separate GameId=0 / PlaceId=0 local copy has now passed successful
purchases, aura equip, potion use/replacement, Gold/Diamond fusion, sequential
three-egg hatching and six-species short movement runs with disposable fixtures.
Seven illustrated trophy/navigation/currency originals are uploaded, bound and
verified. Archived screenshots and the canonical checklist distinguish these passes
from the remaining real-device, multiplayer, non-owner and persistent rejoin gates.
The normal build does not contain acceptance copy/catch fixtures.

Icon consistency follow-up: AURAS and POTIONS now select the shared Meadow aura
and speed-potion compositions through `NavigationArtwork.luau`. Separate layers
and native fallbacks are preserved. Desktop and phone-emulator captures are
archived in `docs/evidence/2026-10-08-navigation-compositions/`. Illustrated leap
and Clear/Rain/Thunderstorm/Blizzard remain Todo in the artwork guide; their native
symbols are not completed illustrated assets.

## Completed before Studio

- Nine verified PNG masters stay separate and reusable. `Artwork.luau` composes the three aura rings with a shared fossil, clips each ring into rear/front layers, overlays native speed/leaf symbols on bottles, and repeats the single catches footprint. Shops, confirmations, fusion and the catches HUD use the shared assembler. Empty uploaded IDs use native icons.
- `ArtworkAssets.luau` is generated from `resources/ui/v2/layers/upload-bindings.json`. All nine IDs now record actual MCP uploads, with verified owner metadata and owner-Studio loading evidence. GitHub PNGs are source files, not Roblox runtime image URLs.
- `ArtworkLayout.luau` contains thumbnail position, scale, ring seam and repeated-mark layout. `UITheme.luau` remains the source of truth for panel colors, fonts, outlines and motion. `resources/ui/design-system.json` is marked historical. Illustration/vision rules remain in `docs/32-artwork-guide-and-todo.md`; the 8–13 audience is an assumption, not measured player research.
- Desktop leap uses **E**, ordinary jump uses Space. Gamepad Y and the mobile leap button remain supported.
- **500 raw food growth points = 15 catches** before weather bonuses. Fractional catches carry between pickups in the same run. Growth potions/auras do not multiply these raw points into catches. PvP remains a separate catch source. Catches are reward score units, not a count of eggs; existing thresholds decide egg grants. Carry resets on a new run.
- Cosmetic fusion supports **50 Base → 1 Gold** and **50 Gold → 1 Diamond**. The Diamond price is provisional private-test tuning, editable in Config. Transactions persist, preserve balances during additive migration, reject insufficient copies, and protect against duplicate/conflicting tokens. Equipping a species shows its highest owned mutation; individual variant selection is not included in this build.
- Six playable/discoverable species: Compy, Triceratops, T-Rex, Raptor, Stegosaurus and Ankylosaurus. New species have feather/claw, plate/spike and armored/club silhouettes. All have native packaged models and previews, catalog names, rarity factors and chest eligibility. Chest rarity totals remain 70% Common / 25% Rare / 5% Legendary; quantity odds remain unchanged. Direct run-reward tiers retain their original three species.
- Unpublished Studio (`IsStudio` and `GameId == 0`) uses unsaved local profiles. With `StudioTestWalletEnabled`, its one-million-crystal test wallet replenishes on each progression transaction; eggs take 10 seconds each. Published Studio sessions and live servers use ordinary wallets, persistent storage and 60-second eggs. These test values can be disabled/adjusted in Config before opening Studio; there is no public grant remote.
- Hatching reveals one committed egg reward at a time. NEXT EGG claims the next ready egg only after the current reveal; growing/empty queues return to the egg view. No reward is rolled on the client.
- CI covers main, the redesign branch, pull requests and manual runs. It installs Pillow/numpy and pinned Luau tools, checks bindings, compiles all sources, executes behavior/preview/artwork checks, rebuilds the current version, runs Python tests and uploads the correct place/manifest. CI no longer makes automated build commits.

## Exactly what to do next

1. Download this branch, extract it and open **`build/BeDino-Build019.rbxlx`** in Studio. Keep it unpublished for the first F5 session. Confirm the badge says **BUILD redesign-019** and the preview notice says progress is not saved. Test currency should show 1,000,000 crystals.
2. Play the native-fallback build first. Explore, gather food, use E, buy/equip an aura, buy/use/replace a potion, return to bank rewards, and hatch eggs with NEXT EGG. Check the scrolling six-species index, phone emulator, reduced motion, terrain collisions and two-client PvP. Unknown/not-owned species should remain locked.
3. Inspect Gold/Diamond previews in the Fusion page. To test actual fusion, earn fixture copies in the disposable local profile or use the existing offline transaction harness; do not enable persistent debug grants. The offline suite covers both fusion costs, migration, retries and rejoin; visual acceptance is still needed.
4. Import the nine PNGs from `resources/ui/v2/layers/` through Studio File → Import / Asset Manager, under the experience owner. Start with fossil, Meadow ring and speed bottle. Confirm transparency, moderation and actual loading in the private experience. Upload all remaining preferred masters; keep historical combined thumbnails as references.
5. Record each copied asset ID and, if needed, its actual image content URI in `upload-bindings.json`; record owner/experience metadata too. Run `python tools/bind_artwork.py`, then `python tools/build.py`. Or sync those changed Luau files with Rojo. Do not expect editing JSON alone to change an already-open place.
6. Check all three aura seams/front occlusion, both bottle emblems, Gold/Diamond badges and catches mark at 32/48/64 px. Tune **ArtworkLayout**, not the PNG master, for positional changes. The initial ring size is .70 to leave room for glow/fringe. If an image fails permissions/moderation, clear its binding until corrected.
7. Publish to the private test experience only after the local pass. Verify real asset permissions, normal currency/60-second egg timing, save/rejoin, existing-profile migration, both fusion stages and two-client interaction there. Record results before merging into main or treating this as release ready.

## Quick adjustment map

| Change | Source |
|---|---|
| Theme colors, outlines, font, motion | `src/shared/UITheme.luau` |
| Artwork position, size, seam, symbol placement | `src/shared/ArtworkLayout.luau` |
| Navigation artwork selection | `src/shared/NavigationArtwork.luau` |
| Uploaded image IDs | `resources/ui/v2/layers/upload-bindings.json`, then run `tools/bind_artwork.py` |
| Food-catch rate, fusion prices, test wallet/timers, species and chest odds | `src/shared/Config.luau` |
| Aura/potion prices and multipliers, weather/leap settings | `src/shared/ProgressionConfig.luau` |
| Dinosaur shape sources | `tools/generate_resources.py`, then `python tools/bake_models.py` |
| Rebuild place | `python tools/build.py` |

The native wedge models avoid import permissions but are heavier than optimized MeshParts. Validate phone performance in Studio; production mesh optimization remains a measured follow-up, not an offline performance claim.

## Local verification

Use Python 3.12 with Pillow/numpy, and Luau 0.741 tools:

```sh
python tools/bind_artwork.py --check
python tools/verify_sources.py --compiler /path/to/luau-compile
python tools/verify_luau.py --runner /path/to/luau
python tools/verify_gameplay.py --runner /path/to/luau
python tools/verify_progression.py --runner /path/to/luau
python tools/verify_previews.py --runner /path/to/luau
python tools/verify_artwork.py --runner /path/to/luau
python tools/build.py
python -m unittest discover -s tests -v
```

These execute actual Luau modules with engine stubs and verify deterministic packaging/source round-trip, all generated PNG hashes/full decoding, closed nondegenerate meshes, all six preview frustums, transaction behavior and test-session isolation. They do not replace Roblox engine acceptance.
