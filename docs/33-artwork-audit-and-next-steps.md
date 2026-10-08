# Artwork audit and guided next steps
Audit date: 2026-10-08. Branch: redesign/resources-and-core-fixes. Static source/files audit, not live Roblox verification.

## Findings and evidence
- Recovered 11 truncated GitHub PNGs (9 preferred reusable layers plus 2 historical combined thumbnails). Local originals were intact. Saved recovered blobs match original Git SHA-1; file-integrity.json records byte lengths and SHA-256. Full PNG verify/load and alpha checks now cover these files.
- Prior tests passed while missing the newly generated directories. tests/test_artwork_integrity.py now covers full decoding and source hashes. This fixes an actual incomplete-transfer failure; it does not approve visual quality.
- Shared UITheme.ImageIds is empty. The 9 layered sources have no uploaded Roblox IDs.
- Bootstrap aura cards and confirmations request generic aura, not per-product meadow/tidal/royal art. Potions request generic speed/growth. There is no layered aura/potion assembly helper. Merely uploading images will not switch these screens.
- Theme.icon supports a single uploaded image, not a multilayer item. JSON layout files are design instructions, not imported runtime settings: default.project.json syncs src and resources/roblox only. Current packager accepts Luau/RBXMX, not arbitrary PNG/JSON sources in src.
- Legacy design-system.json palette differs from runtime UITheme. Runtime UITheme must govern final panel/text/frame colors; artwork guide governs illustrations. Consolidate tokens during UI integration, rather than using both as independent themes.
- Source input is Q (Bootstrap line containing Enum.KeyCode.Q); latest requested leap key is E.
- MutationService accepts only gold, rejecting other target mutations. Diamond art is prepared, but Diamond gameplay is missing.
- Config.ChestTimerSeconds is 60, not requested 10-second test hatch time.
- FoodService calls Dinosaur.addGrowth; addGrowth changes GrowthScore/VisualScale only. CatchScore increments from PvP in PredationService, not food. Requested 500 food ~= 15 catches is missing. Clarify catch units versus actual egg count in labels before implementing reward math.
- Config.SpeciesOrder contains only Compy, Triceratops and T-Rex. Larger discovery/playable catalog is still missing.
- No explicit unlimited-crystal testing control was found in current progression config/service. Keep any future test grant limited to isolated Studio/private test sessions and independent of live persistent wallets.
- Growing Eggs/hatch flow requires live acceptance, especially one-by-one reveal. Source is not proof it matches the requested presentation.
- Original UI PNGs plus scalable fallback exist; no need for additional basic weather/leap/clock icons.
- Visible ring margins are roughly 2.5-3% at alpha >=16, not the requested 12%. Low-alpha fringe touches some canvas edges. Use conservative thumbnail inset and verify clipping at small sizes; revise masters if the fringe becomes visible. Do not claim exact canvas registration or complete source-art QA from generation.
- Historical combined aura thumbnails remain reference-only; prefer independent layers.
- Main/pan remain older Build013. Changes are on redesign branch only; downloading main will miss them.
- Rojo mapping exists; actual installed/live-sync setup is not verified here. Existing default workflow triggers only main, has legacy Prototype artifact paths and doesn't install Pillow for image tests. Current packager default emits Build018. Fix workflow/dependencies/path agreement before relying on CI delivery.
- Existing Build018 place is checked in. PNG sources aren't automatically embedded as cloud images. Rebuild and test after runtime source bindings/components change.

## Next, in order
1. Download the redesign branch via GitHub Code -> Download ZIP, extract locally. Open build/BeDino-Build018.rbxlx for the current game preview. Keep existing Studio/local work separate until synced/exported deliberately.
2. Establish one known-good image import: fossil centerpiece, Meadow ring and speed bottle first. Use Studio File -> Import (or Asset Manager import), choose the PNGs and correct creator/experience owner. Inspect warnings/moderation.
3. Right-click imported assets -> Copy asset ID. Record filename + ID in upload-bindings.json (robloxAssetId null until actual upload); don't infer an ID from GitHub.
4. Verify each image in a temporary ImageLabel (BackgroundTransparency=1, Image=rbxassetid://ID, square size with Fit) in the actual experience. Confirm alpha and permission/loading. Copy the exact image content URI if Studio exposes a separate image/texture URI.
5. Once first imports load, upload the remaining 6 preferred masters. Do not upload historical combined thumbnails or SVGs as item masters.
6. Implement shared ArtworkAssets Luau mapping and reusable AuraThumbnail/PotionThumbnail helpers. Map meadow/tidal/royal to their rings. Layer rear-ring clip -> fossil or real dino preview -> front-ring clip. Potions overlay existing speed/leaf vectors. Treat layout JSON as source design data converted into runtime Luau config.
7. Bind each screen (shop, confirm, HUD, results, mutation badge) to stable logical IDs. Preserve native fallback for not-yet-uploaded/unavailable assets. UITheme.ImageIds alone only replaces generic individual icons.
8. Update gameplay mismatches in isolated reviewable steps: E leap, food-based catches, 10-second test eggs, controlled crystal test grants, Diamond mutation, larger catalog. Never silently advertise artwork as implemented mechanics.
9. Rebuild place, run packaging/source checks, then test Play/phone emulator and published private experience. Tests: both potion types/all rarity labels, all aura thumbnails, correct occlusion, no clipping, readable 32/48/64px, owned/locked/equipped, reduced motion, image moderation/permissions, actual aura VFX versus art.
10. Only after checks pass merge the redesigned work into main and verify delivery workflow. No merge/public release performed by this audit.

## Preferred 9 PNG upload names
| Stable key | Source filename |
|---|---|
| fossil_centerpiece | fossil-centerpiece-v1.png |
| aura_meadow_ring | aura-meadow-ring-v1.png |
| aura_tidal_ring | aura-tidal-ring-v1.png |
| aura_royal_ring | aura-royal-ring-v1.png |
| potion_speed_base | potion-speed-base-v1.png |
| potion_growth_base | potion-growth-base-v1.png |
| mutation_gold | mutation-gold-v1.png |
| mutation_diamond | mutation-diamond-v1.png |
| catches_mark | catches-mark-v1.png |

All are in resources/ui/v2/layers. Potions use existing separate scalable speed/leaf symbols; these can render as native geometry rather than requiring two additional image uploads.
Do not upload each aura fossil or each potion rarity separately.

## Verification boundary
Roblox Studio/phone rendering, upload permissions, image moderation, multiplayer behavior and matching in-world aura VFX cannot be established from static repo inspection. Audit is based on GitHub sources; uncommitted local Studio work may differ.
Official import guidance: https://create.roblox.com/docs/studio/importer
Official asset manager guidance: https://create.roblox.com/docs/projects/assets/manager
