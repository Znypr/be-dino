# 77 Asset registry

Every art asset the game uses at runtime. Add a line here when an asset is added. Code-drawn art is PLACEHOLDER per [docs/72](72-ui-copy-and-asset-standards.md). Status: in game / uploaded not bound / planned / placeholder.

| Name | Type | Repo file | Roblox asset ID | Used by | Status |
|---|---|---|---|---|---|
| trophy | UI icon | resources/ui/v2/icons/trophy.png | 90878052837138 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| dinos | UI icon | resources/ui/v2/icons/dinos.png | 122025247365244 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| egg (premium blank egg) | UI icon | resources/ui/v2/icons/premium-egg-normal.png | 95856282289615 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| home | UI icon | resources/ui/v2/icons/home.png | 94252047806605 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| fusion | UI icon | resources/ui/v2/icons/fusion.png | 122750027724491 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| shield | UI icon | resources/ui/v2/icons/shield.png | 108184472237302 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| amber | UI icon | resources/ui/v2/icons/amber.png | 113168177075625 | UIIconAssets.luau (UI shows 3D amber model preview instead) | uploaded not bound |
| leap | UI icon | resources/ui/v2/icons/leap-v1.png | 137570028242707 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| weather (clear) | UI icon | resources/ui/v2/icons/weather-clear-v1.png | 115952370461269 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| rain | UI icon | resources/ui/v2/icons/weather-rain-v2.png | 99264077757256 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| thunder | UI icon | resources/ui/v2/icons/weather-thunder-v1.png | 135005203451565 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| blizzard | UI icon | resources/ui/v2/icons/weather-blizzard-v2.png | 139930692113070 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| volcano | UI icon | resources/ui/v2/icons/weather-volcano-v1.png | 78071231084873 | src/shared/UITheme.luau via UIIconAssets.luau | uploaded, bound (Studio check pending) |
| aurora | UI icon | resources/ui/v2/icons/weather-aurora-v1.png | 119932884142526 | src/shared/UITheme.luau via UIIconAssets.luau | uploaded, bound (Studio check pending) |
| quake | UI icon | resources/ui/v2/icons/weather-quake-v1.png | 121965025477639 | src/shared/UITheme.luau via UIIconAssets.luau | uploaded, bound (Studio check pending) |
| bloodmoon | UI icon | resources/ui/v2/icons/weather-bloodmoon-v1.png | 123248871135913 | src/shared/UITheme.luau via UIIconAssets.luau | uploaded, bound (Studio check pending) |
| egg_nest | UI icon | resources/ui/v2/icons/egg-nest-v1.png | 127462994652706 | src/shared/UITheme.luau via UIIconAssets.luau | in game |
| egg-green-v1 | UI icon | resources/ui/v2/icons/egg-green-v1.png | - | (none yet) | planned |
| egg_splat | UI icon | resources/ui/v2/icons/egg-splat-v1.png | - | src/client/HatchSequence.luau via UIIconAssets.luau (failed Cracked egg; native shapes until bound) | planned |
| egg_shell | UI icon | resources/ui/v2/icons/egg-shell-v1.png | - | src/client/HatchSequence.luau via UIIconAssets.luau (two shell halves; native shapes until bound) | planned |
| fossil_centerpiece | UI icon (layer) | resources/ui/v2/layers/fossil-centerpiece-v1.png | 86663955990810 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| aura_meadow_ring | UI icon (layer) | resources/ui/v2/layers/aura-meadow-ring-v1.png | 80049958683098 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| aura_tidal_ring | UI icon (layer) | resources/ui/v2/layers/aura-tidal-ring-v1.png | 80241308683604 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| aura_royal_ring | UI icon (layer) | resources/ui/v2/layers/aura-royal-ring-v1.png | 118815481191196 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| potion_speed_base | UI icon (layer) | resources/ui/v2/layers/potion-speed-base-v1.png | 87695825543059 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| potion_growth_base | UI icon (layer) | resources/ui/v2/layers/potion-growth-base-v1.png | 88686902811976 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| mutation_gold | UI icon (layer) | resources/ui/v2/layers/mutation-gold-v1.png | 100614707864137 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| mutation_diamond | UI icon (layer) | resources/ui/v2/layers/mutation-diamond-v1.png | 71974162406565 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| catches_mark | UI icon (layer) | resources/ui/v2/layers/catches-mark-v1.png | 111232893185225 | src/shared/Artwork.luau via ArtworkAssets.luau | in game |
| premium egg cracks | egg overlay | resources/ui/v2/icons/premium-egg-cracks.png | 126956807167774 | src/shared/HatchPresentation.luau (see note 2) | in game |
| Condition overlay Cracked (cracked_fractures) | egg overlay | resources/eggs/conditions/BeDino_Cond_Cracked.png | 126956807167774 | src/shared/ConditionOverlays.luau, EggAppearance.luau | in game |
| Condition overlay Dirty (dirty_smudges) | egg overlay | resources/eggs/conditions/BeDino_Cond_Dirty.png | 105931497056313 | src/shared/ConditionOverlays.luau, EggAppearance.luau | in game |
| Condition overlay Rainbow (rainbow_flank_stars) | egg overlay | resources/eggs/conditions/BeDino_Cond_Rainbow.png | 117352915695915 | src/shared/ConditionOverlays.luau, EggAppearance.luau | in game |
| Condition overlay Astra (astra_opal_streaks) | egg overlay | resources/eggs/conditions/BeDino_Cond_Astra.png | 102255733208943 | src/shared/ConditionOverlays.luau, EggAppearance.luau | in game |
| Dino mesh compy | mesh | resources/models/compy.obj (original geometry; uploaded mesh is the runtime asset) | 79351996702566 | src/server/ImportedResources.luau via ResourceMeshAssets.luau | in game |
| Dino mesh triceratops | mesh | resources/models/triceratops.obj (original geometry; uploaded mesh is the runtime asset) | 90014068543889 | src/server/ImportedResources.luau via ResourceMeshAssets.luau | in game |
| Dino mesh tyrannosaurus | mesh | resources/models/tyrannosaurus.obj (original geometry; uploaded mesh is the runtime asset) | 70736222541118 | src/server/ImportedResources.luau via ResourceMeshAssets.luau | in game |
| Dino mesh raptor | mesh | resources/models/raptor.obj (original geometry; uploaded mesh is the runtime asset) | 114284137928940 | src/server/ImportedResources.luau via ResourceMeshAssets.luau | in game |
| Dino mesh stegosaurus | mesh | resources/models/stegosaurus.obj (original geometry; uploaded mesh is the runtime asset) | 92865644294705 | src/server/ImportedResources.luau via ResourceMeshAssets.luau | in game |
| Dino mesh ankylosaurus | mesh | resources/models/ankylosaurus.obj (original geometry; uploaded mesh is the runtime asset) | 74993073282146 | src/server/ImportedResources.luau via ResourceMeshAssets.luau | in game |
| Gene textures (38 neutral maps, 6 species x body parts) | texture | resources/genetics/neutral-textures/*.png (map: resources/genetics/texture-bindings.json) | 38 IDs, see src/shared/GeneTextureAssets.luau | src/shared/GeneTextures.luau, LegacyGenePatterns.luau | in game |
| World kit (41 meshes: trees, rocks, bushes, landmarks, food) | mesh | resources/worldkit/*.rbxmx; sources assets/blender/world/BD049_WorldKit.blend, BD050_FoodKit.blend, fbx/ | - | built into place by tools/build.py | in game (no uploaded IDs) |
| Meadow/world materials | texture | resources/world-materials.rbxmx (prompts: resources/visual-upgrade-bindings.json) | - | built into place by tools/build.py | in game |
| Egg/food/nature OBJ models (amber, berry, egg, fern, fruit, rock, tree) | mesh | resources/models/*.obj | - | src/server/ImportedResources.luau (native geometry fallback) | in game (fallback) |
| Fusion finish v2 (Blender study) | mesh | assets/blender/fusion/*.blend | - | none (no runtime asset yet) | planned |
| Hatch crunch sound (Creator Store, ProSoundEffects) | sound | - (Roblox hosted) | 9120490790 | src/shared/HatchPresentation.luau | in game |
| Hatch reveal chime (Creator Store, ProSoundEffects) | sound | - (Roblox hosted) | 9116394545 | src/shared/HatchPresentation.luau (see premium-egg-bindings.json) | in game |
| sfx big_thud | sound | assets/audio/sfx/big_thud.wav | - | src/shared/Sfx.luau | planned |
| sfx fusion_reveal | sound | assets/audio/sfx/fusion_reveal.wav | - | src/shared/Sfx.luau | planned |
| sfx hatch_common | sound | assets/audio/sfx/hatch_common.wav | - | src/shared/Sfx.luau | planned |
| sfx hatch_crack | sound | assets/audio/sfx/hatch_crack.wav | - | src/shared/Sfx.luau | planned |
| sfx hatch_legendary | sound | assets/audio/sfx/hatch_legendary.wav | - | src/shared/Sfx.luau | planned |
| sfx hatch_rare | sound | assets/audio/sfx/hatch_rare.wav | - | src/shared/Sfx.luau | planned |
| sfx level_up | sound | assets/audio/sfx/level_up.wav | - | src/shared/Sfx.luau | planned |
| sfx pickup | sound | assets/audio/sfx/pickup.wav | - | src/shared/Sfx.luau | planned |
| sfx pickup_hi | sound | assets/audio/sfx/pickup_hi.wav | - | (variant file, not in Sfx.Sounds) | planned |
| sfx pickup_lo | sound | assets/audio/sfx/pickup_lo.wav | - | (variant file, not in Sfx.Sounds) | planned |
| sfx run_end | sound | assets/audio/sfx/run_end.wav | - | src/shared/Sfx.luau | planned |
| sfx run_start | sound | assets/audio/sfx/run_start.wav | - | src/shared/Sfx.luau | planned |
| sfx shiny_bang | sound | assets/audio/sfx/shiny_bang.wav | - | src/shared/Sfx.luau | planned |
| sfx shop_buy | sound | assets/audio/sfx/shop_buy.wav | - | src/shared/Sfx.luau | planned |
| sfx shop_refresh | sound | assets/audio/sfx/shop_refresh.wav | - | src/shared/Sfx.luau | planned |
| sfx ui_click | sound | assets/audio/sfx/ui_click.wav | - | src/shared/Sfx.luau | planned |
| sfx weather_start | sound | assets/audio/sfx/weather_start.wav | - | src/shared/Sfx.luau | planned |
| mythic glow sigil-outer | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/sigil-outer.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: aura ground sigil, outer | placeholder |
| mythic glow sigil-inner | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/sigil-inner.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: aura ground sigil, inner (tier 2+) | placeholder |
| mythic glow runes | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/runes.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: rune motes (flipbook 4x4) | placeholder |
| mythic glow glow-dot | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/glow-dot.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: motes and sigil under-glow | placeholder |
| mythic glow ribbon-plain | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/ribbon-plain.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: trail main + navy under-layer | placeholder |
| mythic glow ribbon-plasma | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/ribbon-plasma.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: trail strand/braid, aura comets | placeholder |
| mythic glow ribbon-lightning | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/ribbon-lightning.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: Electric Arc strand | placeholder |
| mythic glow light-pillar | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/light-pillar.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: aura pillar (tier 2+) | placeholder |
| mythic glow halo-ring | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/halo-ring.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: head halo (tier 3) | placeholder |
| mythic glow twinkle | effect texture (PLACEHOLDER, Python-drawn; Blender render replaces it, docs/83) | resources/effects/mythic-glow/twinkle.png | - (upload pending) | src/shared/EffectAssets.luau via CosmeticEffects v2: sparkle pops (flipbook 4x4) | placeholder |

Notes

1. Sound pack: files exist in git, IDs are not uploaded yet, so `Sfx.Sounds` ids are empty (silent) until bound.
2. Possible duplicate: the premium-egg cracks ID (`premium-egg-bindings.json`) equals the Cracked condition overlay ID 126956807167774. Owner to confirm they are the same upload.
3. Native code-drawn fallbacks (e.g. the nest sprite in `UITheme.luau`) are PLACEHOLDER and only render when the bound ID is empty.

## Archive

All older revisions and Blender sources live OUTSIDE git in Google Drive: `My Drive/Be Dino/Art Archive/2026-10-08_Premium_Egg_all_revisions.zip` (full Premium_Egg folder as of 2026-10-13).

Rule: every new asset adds a registry line when it is added.
