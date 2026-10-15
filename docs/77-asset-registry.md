# 77 Asset registry

Every art asset the game uses at runtime. Add a line here when an asset is added. Code-drawn art is PLACEHOLDER per [docs/72](72-ui-copy-and-asset-standards.md). Status: in game / uploaded not bound / planned / placeholder.

| Name | Type | Repo file | Roblox asset ID | Used by | Status |
|---|---|---|---|---|---|
| potion_model_flask | 3D model (Roblox generate_mesh): round flask, blue liquid, lightning charm | - (Roblox generate_mesh, 2026-10-15) | 114182681867384 (Model) | src/shared/PotionArt.luau ModelAssets.flask: speed potions Common-Epic (shop cards, confirm, POTIONS nav button) | in game via InsertService (src/server/PotionModels.luau); vector flask fallback |
| potion_model_jar | 3D model (Roblox generate_mesh): squat jar, orange liquid, clover | - (Roblox generate_mesh, 2026-10-15) | 121478365783622 (Model) | PotionArt ModelAssets.jar: luck/loot potions Common-Epic | in game via InsertService; vector flask fallback |
| potion_model_heart | 3D model (Roblox generate_mesh): heart bottle, green liquid, sprout | - (Roblox generate_mesh, 2026-10-15) | 126942715659365 (Model) | PotionArt ModelAssets.heart: growth potions Common-Epic | in game via InsertService; vector flask fallback |
| potion_model_claw | 3D model (Roblox generate_mesh): dino-claw vial, purple sparkles | - (Roblox generate_mesh, 2026-10-15) | 100441458834806 (Model) | PotionArt ModelAssets.claw: every Legendary potion | in game via InsertService; vector flask fallback |
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
| egg_green | UI icon | resources/ui/v2/icons/egg-green-v1.png | 107129283312327 | src/shared/NavigationArtwork.luau (Eggs menu button, BD-176), src/client/DinoIndexPanels.luau (egg button, BD-175) | uploaded, bound (Studio check pending) |
| egg_nest_single | UI icon | resources/ui/v2/icons/egg-nest-single-v1.png | 85647267539754 | src/client/EggsScreen.luau (nest slots, BD-169) | uploaded, bound (Studio check pending) |
| egg_stage (tile floor) | UI art | - | - | src/client/EggPicture.luau `stage` draws a code-built tile floor | PLACEHOLDER: needs a Blender tile-floor render + upload (BD-169) |
| egg_splat | UI icon | resources/ui/v2/icons/egg-splat-v1.png | 90653261302119 | src/client/HatchSequence.luau via UIIconAssets.luau (failed Cracked egg; native shapes until bound) | uploaded, bound (Studio check pending) |
| egg_shell | UI icon | resources/ui/v2/icons/egg-shell-v1.png | 81264206118496 | src/client/HatchSequence.luau via UIIconAssets.luau (two shell halves; native shapes until bound) | uploaded, bound (Studio check pending) |
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
| World kit (41 meshes: trees, rocks, bushes, landmarks, food) | mesh | resources/worldkit/*.rbxmx; sources assets/blender/world/BD049_WorldKit.blend, BD050_FoodKit.blend, fbx/ | 40 uploaded mesh IDs (world_tree_dead_m missing) | resources/worldkit-meshes/mesh-bindings.json -> src/shared/WorldKitMeshAssets.luau (tools/bind_worldkit_meshes.py), loaded by ImportedResources.loadWorldKit | in game (MeshParts; native fallback for dead_m) |
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

Notes

1. Sound pack: files exist in git, IDs are not uploaded yet, so `Sfx.Sounds` ids are empty (silent) until bound.
2. Possible duplicate: the premium-egg cracks ID (`premium-egg-bindings.json`) equals the Cracked condition overlay ID 126956807167774. Owner to confirm they are the same upload.
3. Native code-drawn fallbacks (e.g. the nest sprite in `UITheme.luau`) are PLACEHOLDER and only render when the bound ID is empty.

## Archive

All older revisions and Blender sources live OUTSIDE git in Google Drive: `My Drive/Be Dino/Art Archive/2026-10-08_Premium_Egg_all_revisions.zip` (full Premium_Egg folder as of 2026-10-13).

Rule: every new asset adds a registry line when it is added.

## Sound effects (uploaded 2026-10-15)

The 17-sound pack from `assets/audio/sfx/` (synthesized placeholders by `tools/generate_sfx.py`; a proper sound pass is BD-081). `hatch_rattle` and `hatch_burst` have no sound yet and stay silent.

| Name | Type | Source | ID | Used by | Status |
|---|---|---|---|---|---|
| sfx_big_thud | sound | assets/audio/sfx/big_thud.wav | 88666885925372 | src/shared/Sfx.luau | in game |
| sfx_fusion_reveal | sound | assets/audio/sfx/fusion_reveal.wav | 90816090310479 | src/shared/Sfx.luau | in game |
| sfx_hatch_common | sound | assets/audio/sfx/hatch_common.wav | 123602379376075 | src/shared/Sfx.luau | in game |
| sfx_hatch_crack | sound | assets/audio/sfx/hatch_crack.wav | 135613869332284 | src/shared/Sfx.luau | in game |
| sfx_hatch_legendary | sound | assets/audio/sfx/hatch_legendary.wav | 109331854464968 | src/shared/Sfx.luau | in game |
| sfx_hatch_rare | sound | assets/audio/sfx/hatch_rare.wav | 100769608611671 | src/shared/Sfx.luau | in game |
| sfx_level_up | sound | assets/audio/sfx/level_up.wav | 135894580270926 | src/shared/Sfx.luau | in game |
| sfx_pickup | sound | assets/audio/sfx/pickup.wav | 97315544055472 | src/shared/Sfx.luau | in game |
| sfx_pickup_hi | sound | assets/audio/sfx/pickup_hi.wav | 86225160041514 | src/shared/Sfx.luau | in game |
| sfx_pickup_lo | sound | assets/audio/sfx/pickup_lo.wav | 80767583749596 | src/shared/Sfx.luau | in game |
| sfx_run_end | sound | assets/audio/sfx/run_end.wav | 127962506254484 | src/shared/Sfx.luau | in game |
| sfx_run_start | sound | assets/audio/sfx/run_start.wav | 87202810278231 | src/shared/Sfx.luau | in game |
| sfx_shiny_bang | sound | assets/audio/sfx/shiny_bang.wav | 124365194004947 | src/shared/Sfx.luau | in game |
| sfx_shop_buy | sound | assets/audio/sfx/shop_buy.wav | 102585210519734 | src/shared/Sfx.luau | in game |
| sfx_shop_refresh | sound | assets/audio/sfx/shop_refresh.wav | 91960074825710 | src/shared/Sfx.luau | in game |
| sfx_ui_click | sound | assets/audio/sfx/ui_click.wav | 77237659470894 | src/shared/Sfx.luau | in game |
| sfx_weather_start | sound | assets/audio/sfx/weather_start.wav | 120619985059497 | src/shared/Sfx.luau | in game |
| paint_bucket | UI icon (planned) | resources/ui/v2/icons/paint-bucket-v1.png | - | src/client/HatchSequence.luau (reads Theme.ImageIds.paint_bucket; PLACEHOLDER UI-shape bucket until bound) | planned (docs/83 item 31) |
| fx_glowPlate | effect texture (Blender, white on alpha) | resources/effects/fx-v2/glowPlate.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.glowPlate | rendered 2026-10-15, upload pending |
| fx_ringSoft | effect texture (Blender, white on alpha) | resources/effects/fx-v2/ringSoft.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.ringSoft | rendered 2026-10-15, upload pending |
| fx_ringShock | effect texture (Blender, white on alpha) | resources/effects/fx-v2/ringShock.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.ringShock | rendered 2026-10-15, upload pending |
| fx_starFour | effect texture (Blender, white on alpha) | resources/effects/fx-v2/starFour.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.starFour | rendered 2026-10-15, upload pending |
| fx_ribbonSoft | effect texture (Blender, white on alpha) | resources/effects/fx-v2/ribbonSoft.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.ribbonSoft | rendered 2026-10-15, upload pending |
| fx_speedLine | effect texture (Blender, white on alpha) | resources/effects/fx-v2/speedLine.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.speedLine | rendered 2026-10-15, upload pending |
| fx_smokeSheet | effect flipbook 4x4 (Blender, white on alpha) | resources/effects/fx-v2/smokeSheet.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.smokeSheet | rendered 2026-10-15, upload pending |
| fx_sparkSheet | effect flipbook 4x4 (Blender, white on alpha) | resources/effects/fx-v2/sparkSheet.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.sparkSheet | rendered 2026-10-15, upload pending |
| fx_flameSheet | effect flipbook 4x4 (Blender, white on alpha) | resources/effects/fx-v2/flameSheet.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.flameSheet | rendered 2026-10-15, upload pending |
| fx_crystalSheet | effect flipbook 4x4 (Blender, white on alpha) | resources/effects/fx-v2/crystalSheet.png | - (awaiting owner upload) | src/shared/EffectAssets.luau Requested.crystalSheet | rendered 2026-10-15, upload pending |
| egg_stage_jungle | UI stage image (Blender render, owner-approved scene) | resources/ui/v2/stage/egg-stage-jungle-v1.jpg | - (awaiting owner upload) | Eggs page background: jungle waterfalls, grass, stone pedestal, no egg (rendered from Premium_Egg/Blank_Egg_Conditions/BeDino_Blank_Conditions.blend with the egg hidden) | ready, upload pending |
| egg_condition_layers | UI egg renders with black outline (5 conditions, transparent 1024) | resources/ui/v2/stage/eggs/egg-0N_*.png | - (awaiting owner upload) | Eggs page egg on the pedestal (pedestal top centre at about x 50%, y 72% of the stage image) | ready, upload pending |
| fx3_smoke-anime | effect flipbook 4x4 (owner ChatGPT image, anime cel style, processed to white on alpha, 256 px cells, faded borders) | resources/effects/fx-v3/smoke-anime.png | rbxassetid://109810080362045 | EffectAssets smokeSheet: aura smoke puffs (all tiers), trail puffs, mutation mist, hatch burst poof, quake dust (OneShot) | uploaded 2026-10-16, bound; with alpha, replaces opaque upload (Studio 2026-10-16: 1024 px, corner alpha 0); HasAlpha true, UI uses it |
| fx3_flame | effect flipbook 4x4 (owner ChatGPT image, anime cel style, processed to white on alpha, 256 px cells, faded borders) | resources/effects/fx-v3/flame.png | rbxassetid://105817278245256 | EffectAssets flameSheet: Epic+ aura flame wisps, ember mutation motif (Random frame) | uploaded 2026-10-16, bound; with alpha, replaces opaque upload (Studio 2026-10-16: 1024 px, corner alpha 0); HasAlpha true, UI uses it |
| fx3_sparkle | effect flipbook 4x4 (owner ChatGPT image, anime cel style, processed to white on alpha, 256 px cells, faded borders) | resources/effects/fx-v3/sparkle.png | rbxassetid://71657118485647 | EffectAssets sparkSheet + starFour: Rare+ aura sparkles, trail sparks/stars, mutation pop, hatch rim/foreground sparkles (OneShot) | uploaded 2026-10-16, bound; with alpha, replaces opaque upload (Studio 2026-10-16: 1024 px, corner alpha 0); HasAlpha true, UI uses it |
| fx3_swirl | effect flipbook 4x4 (owner ChatGPT image, anime cel style, rotating energy swirl; repo copy is 1254 px RGB on black) | resources/effects/fx-v3/swirl.png | rbxassetid://84584423423015 | EffectAssets swirl: Legendary+ aura swirl lying flat at the feet (Loop, drawn additive so black never shows) | uploaded 2026-10-16, bound; with alpha, replaces opaque upload (Studio 2026-10-16: 1024 px, corner alpha 0); HasAlpha true, UI uses it |
| fx3_rays | effect single image (owner ChatGPT image, rising aura light rays, faded base; repo copy is 1254 px RGB on black) | resources/effects/fx-v3/rays.png | rbxassetid://99778248779183 | EffectAssets rays: Epic+ aura rays pillar (BillboardGui behind the dino, slow pulse) | uploaded 2026-10-16, bound; with alpha, replaces opaque upload (Studio 2026-10-16: 1024 px, corner alpha 0); HasAlpha true, UI uses it |
