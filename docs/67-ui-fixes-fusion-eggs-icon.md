# 67 UI fixes: fusion entry, caught eggs, growth icon, undiscovered dinos

What changed
- Nav FUSION and the Dino Index footer FUSION button call `openFusion()` (Bootstrap). `FusionSelection.navTarget` picks: the new Pattern Fusion Menu when `FusionAction` exists and does not answer `fusion_disabled` (probed once, cached); the old Build 020 page only in the `development` profile; otherwise a "not available" toast. The `FusionMenu` require was missing from Bootstrap, so the menu was unreachable; it is restored. The menu panel now keeps a left inset (`FusionMenu.setLeftInset`) so it never overlaps the nav rail (desktop ~1080x720 and phone landscape).
- Caught Eggs: slots use the real egg look (`EggAppearance` genes, plus Shiny/BIG badges). The procedural fallback egg no longer has the two green patches; empty slots are a flat gray egg; nests get a small twig-ring nest sprite row (gold egg when ready). Selection logic: `FusionSelection.eggSlotLook`.
- GROWTH HUD tile: leaf icon replaced by a native three-bar growth icon (no new asset ids).
- Dino Index: undiscovered species show a gray card, black silhouette (`DinosaurPreview` mode `"silhouette"`: no textures/effects, black ambient light), `???` name and rarity, "Not discovered", and a dimmed no-op VIEW DINO. Logic: `FusionSelection.indexCard`. The `Discovered: n/22` counter is unchanged.

Check in Studio
1. Nav FUSION and Index FUSION open the new menu (title "Pattern Fusion: 15 Base -> 1 NEW Gold"), clear of the rail at 1080x720 and phone landscape.
2. Caught Eggs: gene-colored eggs per slot, gray empty slots, nest sprites; hatch reveal unchanged.
3. GROWTH tile icon looks clean.
4. Undiscovered Index cards are black silhouettes with `???`; discovered cards unchanged.

Follow-up: undiscovered Index cards
- No VIEW DINO button at all; the silhouette and "Not discovered" are re-centered so card height stays stable.
- Soft edge: a second silhouette viewport (82% transparent, ~7% larger) sits under the solid one. Two viewports per undiscovered card, no per-frame work; the underlay is skipped when motion/effects are reduced.
