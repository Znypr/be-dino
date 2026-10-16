# 120 Pending owner uploads and asset tasks: one checklist (BD-318, 2026-10-16)

The single list of every asset still missing or not yet uploaded. It does not repeat the ChatGPT prompts: those live in [109](109-owner-art-prompt-pack.md) (section number in the "Prompt" column). Registry ids live only in [77](77-asset-registry.md); task status only in [the Kanban](07-kanban.md). Cross-checked against 77, 83, 109 and 118 on 2026-10-16 (section 4 lists what already exists). Rules: [AGENTS.md](../AGENTS.md) art rule (no Python- or code-drawn final art; effect textures are Blender renders or owner ChatGPT images; icons are Blender or owner ChatGPT), [72](72-ui-copy-and-asset-standards.md) (brief, drafts, pick, export, owner upload, Studio check; never invent ids).

**Upload flow (all rows):** Studio > View > Asset Manager > Bulk Import, owner account, as **Image** (not Decal); paste back `name: rbxassetid://...`; the lead adds the docs/77 line and binds. 3D meshes are generated or uploaded in Studio and bound by the lead.

**Binding legend:** AUTO = `tools/bind_ui_icons.py` or one table edit; TABLE = one config edit; CODE = a small agent task first (named in the row).

## 1. Files already in the repo, only an upload is missing

| Asset | BD | Maker | File (repo path) | Format | Bound in code | Bind |
|---|---|---|---|---|---|---|
| Eggs page jungle stage | BD-208, BD-394 | Blender (done) | `resources/ui/v2/stage/egg-stage-jungle-v1.jpg` | opaque JPG, upload as is | `src/client/EggPicture.luau` `stage`, `EggsScreen.luau` (replaces the code tile floor; Conditions shop BD-394); key `egg_stage` | CODE (BD-208) |
| 5 condition eggs (cracked, dirty, normal, rainbow, astra) | BD-208, BD-394 | Blender (done) | `resources/ui/v2/stage/eggs/egg-01_cracked.png`, `egg-02_dirty.png`, `egg-03_normal.png`, `egg-04_rainbow.png`, `egg-05_astra.png` | transparent PNG 1024, black outline | `EggPicture.luau`, keys `egg_cond_<name>` in `UIIconAssets` | CODE (BD-208) |
| Glow plate, soft ring, shock ring, speed line, crystal sheet | BD-186, BD-188, BD-189 | Blender (done) | `resources/effects/fx-v2/glowPlate.png`, `ringSoft.png`, `ringShock.png`, `speedLine.png`, `crystalSheet.png` | white on alpha; crystalSheet is a 4x4 flipbook | `src/shared/EffectAssets.luau` `Requested.<key>.id` | AUTO |
| Older rendered ribbon (stop-gap for the ribbon below) | BD-178 | Blender (done) | `resources/effects/fx-v2/ribbonSoft.png` (512x64) | white on alpha | `EffectAssets.Requested.ribbonSoft` | AUTO |
| Aura icons Meadow and Tidal | BD-101 (aura part) | owner ChatGPT (done) | `resources/ui/v2/items/aura-meadow-v1.png`, `aura-tidal-v1.png` | 1024 PNG | aura shop cards | AUTO |
| Two trail icons that exist outside the repo | BD-178 | owner ChatGPT (done) | save as `resources/ui/v2/icons/trail-white-v1.png`, `trail-fern-v1.png` | 1024 PNG | `ProgressionConfig.TrailIconAssetIds` | TABLE |

Note: the older fx-v2 smoke, spark and flame sheets are superseded by the uploaded fx-v3 sheets (77 `fx3_*`); do not upload both.

## 2. Still to make (then upload)

| Asset | BD | Tool | File (repo path) | Size / format | Bound in code | Bind | Prompt |
|---|---|---|---|---|---|---|---|
| Shared trail ribbon (straight, tileable) | BD-178, BD-336 | ChatGPT FX block (or Blender, same job as 83 item 5) | `resources/effects/fx-v3/ribbon-soft.png` | 2048x512 (downscale to 1024x256 ok), white on alpha, under 400 KB | `EffectAssets.Requested.ribbonSoft`; trails in `FxRig`, ribbons in `FxUi` | TABLE | 109 B1 |
| 10 trail shop icons (white, fern, tidal, ember, violet, electric, frost, solar, nova, astra) | BD-178, BD-336 | ChatGPT ICON block | `resources/ui/v2/icons/trail-<id>-v1.png` | 1024x1024 RGBA coloured, 12% margin, readable at 64 px | `src/client/ShopCards.luau` via `P.trailIconId(Config.TrailIconAssetIds, id)` | TABLE/AUTO | 109 B2 |
| 7 mutation badges (dewdrop, charged, frost, seismic, ember, aurora, bloodmoon) | BD-190, BD-352 | ChatGPT ICON block (docs/92 batch 5 allows Blender; owner picks) | `resources/ui/v2/icons/mutation-<id>-v1.png` | 1024 coloured PNG (128 px export ok), readable at 64 and 32 px | keys `mutation_<id>` in `UIIconAssets`; `MutationBadge.luau`, Eggs cards, My dinos, hatch badge (replace the colour dot) | CODE (BD-190) | 109 C1 |
| Glow plate variants (droplet, crescent) | BD-186 | Blender | `resources/effects/fx-v2/glowPlate-<variant>.png` | 256 px, white on alpha | `EffectAssets.luau`, tint from `MutationLook` | AUTO | docs/92 batch 1 |
| Smoke puff variants (dense, wispy breath) | BD-187 | Blender or ChatGPT FX block | `resources/effects/fx-v3/` (new names) | 4x4 flipbook, 256 px cells = 1024, under 400 KB | `EffectAssets.smokeSheet` family | TABLE | 109 E4 |
| Thick seismic ring | BD-188 | Blender | `resources/effects/fx-v2/ringSeismic.png` | 256 px, white on alpha | `EffectAssets.luau` | AUTO | docs/92 batch 3 |
| Mutation motif sheets (droplets, soft sparks, snow crystals, pebbles, embers, aurora ribbons, crimson motes) | BD-189 | Blender or ChatGPT FX block | `resources/effects/fx-v3/motif-<name>.png` | 512 px sheets or 4x4 flipbooks; Aurora only is coloured | `EffectAssets.luau`, `MutationLook` | TABLE | 109 E4 |
| Paint bucket icon (hatch v1) | BD-171, BD-336 | ChatGPT ICON block | `resources/ui/v2/icons/paint-bucket-v1.png` | 1024 RGBA, paint surface white so it tints | `HatchSequence.luau` reads `Theme.ImageIds.paint_bucket` (UI-shape PLACEHOLDER today) | AUTO | 109 C2 |
| Rarity badges (6) and fusion tier badges (3) | BD-113, BD-048, BD-336 | ChatGPT ICON block | `resources/ui/v2/icons/rarity-{common,uncommon,rare,epic,legendary,mythic}-v1.png`, `tier-{gold,emerald,diamond}-v1.png` | 1024 coloured, no text | keys `rarity_<class>`, `tier_<name>` (shop cards, Index, Fusion menu) | CODE (BD-113) | 109 D1 |
| Notification icons (5) and toast plate | BD-304 follow-up | ChatGPT | `resources/ui/v2/icons/notify-{crystal,level,star,mutation-egg,warning}-v1.png`, `toast-body-v1.png` | icons 1024 (readable at 32 px); plate 512x128 9-slice, centre 48 px | keys `notify_*`, `toast_body`; toast code | CODE | 109 D2, 83 items 15-20 |
| Royal Nova aura icon | BD-101 (aura part) | ChatGPT ICON block | `resources/ui/v2/items/aura-royal-v1.png` | 1024 PNG, matches Meadow and Tidal | aura shop card | TABLE/AUTO | 109 D3 |
| Potion rarity frames (5, P2) | BD-101 | ChatGPT | `resources/ui/v2/components/frame-{common,uncommon,rare,epic,legendary}-v1.png` | 512x512 9-slice, empty centre | potion shop cards | CODE | 109 D3 |
| Combat HUD art, crystal pack icons, cave sign medallions (P2) | BD-248, BD-331, docs/104 | ChatGPT | see 109 E1-E3 | 1024 PNG | CombatHud, crystal cards, cave sign SurfaceGuis | CODE | 109 E1-E3 |
| Rare hatch fanfare sound (optional, `shiny_bang` plays meanwhile) | BD-428 | Owner or sound lab (docs/110) | - | 2-3 s, .ogg/.mp3 | `Sfx.Sounds` (new `rare_hatch_fanfare`) | after upload | Bright kid-friendly celebration jingle, no harsh peak |
| Confetti sheet (optional, fx3 sparkle tinted meanwhile) | BD-428 | Blender render | `resources/effects/fx-v3/confetti.png` | 1024x1024 4x4, white on alpha | `RareHatchClient` | after upload | Squares, ribbons and stars, 16 cells |
| Cave lava crust / flow texture (BD-385, BD-294) | BD-385 | Blender render (no code-drawn art) | `resources/effects/cave-lava-crust-v1.png` | 1024 tileable, warm orange to dark crust, soft alpha edge, calm and friendly | `CaveLavaFx` falls sheet layers (today: existing swirl and flame sheets) | TODO | 104 s5 |

## 3. Hatch v2 (3D and paint flipbooks, docs/118, BD-397; flag `Config.HatchV2 = false`)

| Asset | Tool | File / key | Size / format | Bound in code | Prompt |
|---|---|---|---|---|---|
| Paint bucket 3D mesh (PLACEHOLDER: cave hub barrel 81905342774801) | Roblox Studio `generate_mesh`, owner account | `HatchV2Assets.bucket.assetId`; flip docs/77 `hatch_v2_bucket_placeholder`, clear `Placeholder.bucket` | about 1.35 studs tall; white paint surface | `src/shared/HatchV2Assets.luau` | 118 section 4 B |
| Paint splash crown flipbook | ChatGPT FX block | `resources/effects/fx-v3/paint-splash-crown.png`, key `paintCrown` (OneShot) | 4x4 cells of 256 = 1024, 15% cell margin, under 400 KB, white on alpha | `EffectAssets.Requested.paintCrown` (fallback `smoke`), read by `HatchEggV2` | 118 section 4 C1 |
| Paint drips flipbook | ChatGPT FX block | `fx-v3/paint-drips.png`, key `paintDrips` (OneShot) | same | same | 118 C2 |
| Paint droplets sheet | ChatGPT FX block | `fx-v3/paint-droplets.png`, key `paintDroplet` (Random) | same | same | 118 C3 |
| Paint gloss decal | ChatGPT FX block | `fx-v3/paint-sheet-gloss.png` | single 1024x1024, white on alpha | Decal over the egg while wet | 118 C4 |
| Egg mesh | none | reuse `world_gen_food_egg` (docs/77) | n/a | `HatchEggV2` | 118 A |

## 4. Cross-check results (docs/77, 83, 109, 118)

- **Potion icons (BD-101):** the 12 bottle PNGs are tracked in `resources/ui/v2/items/potion-*.png` on main and docs/77 has `potion_icon_*` lines with ids. No upload is pending; BD-101 only needs the Studio check that `PotionArt.luau` no longer shows code bottles, plus the P2 rarity frames above. Any untracked local copy in the owner's main checkout is not needed; do not commit extra copies.
- **Egg nest icon (BD-094):** `egg_nest` (127462994652706) and `egg_nest_single` (85647267539754) are in docs/77 as in game / bound. Remaining work is the Studio check and a status move; no art. Optional P2 "bonus nest" badge only.
- **Egg splat and shell (docs/83 items 29, 30):** uploaded per docs/109 section 6; Studio check pending.
- **Doc 83 items 1-10 (Mythic Glow textures):** the Blender session plan of 83 is partly superseded by fx-v2 renders and fx-v3 owner sheets; `ribbon-plain` (83 item 5) equals `ribbonSoft` (109 B1): make only one.
- **Doc 83 item 25 (food MeshParts) and section 4 (17 sfx):** upload-only items outside this art list; tracked in 95 and 83.
- **Old label BD-218:** has no Kanban row; BD-208 and BD-394 own the egg stage and condition eggs.
- **Balloon skin:** owner decided 2026-10-16 that it is a **Robux skin** ([115](115-decisions-log.md), [97](97-dino-skins.md)). It needs no uploaded art in this list (skins are procedural looks like Bricks, Clay and Plushy); a skin-shop icon, if wanted, is added to section 2 later. Robux release stays behind the release flags until Studio tested (docs/43). No Kanban row yet: add one when the skin is scheduled.

## 5. Order for the owner

1. Upload section 1 (existing files): unblocks BD-208, BD-394 and several FX keys at no creative cost.
2. Make and upload the ribbon plus 10 trail icons (BD-178), then mutation badges (BD-190) and the paint bucket (BD-171).
3. Hatch v2 assets (section 3) when `HatchV2` is scheduled for a playtest.
4. Polish and P2 rows last.

After each upload: the lead records ids in docs/77, binds, runs the matching verifier, takes a desktop and phone Studio screenshot next to neighbouring UI, then moves the BD rows to Review / test ([109](109-owner-art-prompt-pack.md) section 7).
