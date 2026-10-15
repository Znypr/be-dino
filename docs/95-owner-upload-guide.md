# 95 Owner upload guide (what to upload, in what order)

Everything below exists in the repo and works with fallbacks until it is uploaded. Uploading never breaks the game. Do these in Studio (Asset Manager) with the same account as before. After each group, tell the lead (chat) and, for images, paste the Roblox asset ids.

## A. Models: Bulk Import (54 FBX)
Folder: `assets/blender/world/fbx_v2/`
- food (16): food_berry_a-d, food_fruit_a-d, food_nut_a-b, food_amber_a-b, food_mush_a-d
- rocks (12): world_boulder_a/b, world_boulder_mossy_a/b, world_slab_a, world_pebble_a, world_sandstone_a/b, world_lava_a/b, world_basalt_a, world_crystal_a
- plants (11): world_bush_berry_a, world_bush_flower_a, world_bush_plain_a, world_fern_c, world_reeds_a, world_clover_a, world_flower_pink/yellow/blue/white, world_grass_c
- trees (9): world_tree_broad_a/b, world_tree_pine_a/b, world_tree_birch_a, world_tree_palm_a, world_tree_willow_a, world_tree_baobab_a, world_tree_burnt_a
- landmarks (6): world_landmark_dino_statue_b, world_landmark_totem_a, world_landmark_pillars_a, world_landmark_ribs_a, world_landmark_egg_monument, world_landmark_obelisk_a
How: Asset Manager > Bulk Import > select all 54 > import. Tell the lead which Studio window has them. The lead binds them (resources/worldkit-meshes/mesh-bindings.json via tools/bind_worldkit_meshes.py) and an agent places them per biome. Note: the 6 food names berry_a/b, fruit_a/b, amber_a/b replace the old models.

## B. Images (effect textures, 10 PNG, white on transparent)
Folder: `resources/effects/fx-v2/`: glowPlate, ringSoft, ringShock, starFour, ribbonSoft, speedLine, smokeSheet, sparkSheet, flameSheet, crystalSheet. Upload as Images, paste the 10 ids as `name: id`.

## C. Image (Eggs page floor)
`resources/ui/v2/icons/egg-stage-v1.png` (rounded tile-floor render). Paste the id.

## D. Still needed from art / sound (not in the repo yet)
- UI icons via ChatGPT or Blender: trail icons (10), aura icons (3+), potion icons (12), crystal pack icons, rarity badges (6 tiers), original-egg button icon, mutation icons, fusion tier badges, paint bucket, undiscovered silhouettes.
- Sounds (weather beds and cues, softer run-end and spawn sounds): briefs in docs/85-weather-audio-briefs.md. Style rule: docs/87 (calm, soft, bubbly, quiet).
