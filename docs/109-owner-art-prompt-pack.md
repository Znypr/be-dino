# 109 Owner art prompt pack (one current checklist, 2026-10-16)

The ONE deduplicated list of every art item the owner still has to make or upload, with a ready-to-paste ChatGPT prompt where ChatGPT is the maker. It consolidates docs/77 (registry), 83 (asset list), 87 (feel), 92 (mutation brief), 93 (FX direction), 95 (upload guide) and the Kanban rows BD-048, 094, 101, 113, 178, 186-190, 208, 248, 318 (the old "BD-218" label has no row; BD-318 replaces it). Status lives only in [the Kanban](07-kanban.md) (this pack is tracked by BD-336). Rules: [docs/72](72-ui-copy-and-asset-standards.md) (no code-drawn final art), [AGENTS.md](../AGENTS.md). Never invent asset IDs; every uploaded asset gets a [docs/77](77-asset-registry.md) line.

## 0. Shared style block (paste at the start of EVERY prompt)

> Be Dino! is a friendly Roblox dinosaur game for young children. Style: anime cel-shaded, bubbly and soft, saturated but harmonious colours, thick clean dark outline on icons, rounded chunky shapes, matte (no harsh shine), bright top-left light, calm and cozy, never scary or sharp. No text, letters, digits, logos or watermark. Match the existing owner images (egg nest, trophy, weather icons, potion bottles).

Two sub-blocks, pick one per item:

- **ICON block:** "One single object, three-quarter view slightly from above, centred on a square 1024x1024 canvas, whole object visible, at least 12% empty margin on all sides, TRUE transparent background (no ground, no shadow plane, no frame), readable at 64 px, broad simple shapes."
- **TX1 (narrowed, audit C-41):** the upload cap of 512 px max per side (256 px when it reads the same) in docs/115 TX1 is for **UI icons, badges and shop/egg art** only. The owner still makes the 1024 px icon masters below; the cap applies to the upload copy. **Flipbook sheets and ribbons are NOT capped by TX1: they keep this document's spec** (4 x 4 cells of 256 px = 1024 px sheet, ribbon 2048 x 512).
- **FX block (white on alpha):** "Pure WHITE shapes on a fully transparent background, no colour, no black background, soft feathered edges that fade to fully transparent before touching the image border, anime cel style with a bright core and softer outer edge. The game tints it at runtime."

Always ask ChatGPT for a **transparent PNG**. If it returns a black or white background, tell the lead; the lead can run the alpha clean-up used for the fx-v3 sheets (docs/77 fx3_* rows). Check: open the PNG, the corners must be fully transparent.

## 1. Upload order (tell the lead after each group)

1. **Group A (files exist, upload only):** Eggs page art (A1, A2). Blocks BD-208 and the Eggs-page look.
2. **Group B:** trail ribbon texture (B1) and 10 trail icons (B2). Blocks BD-178 / BD-143 trail shop.
3. **Group C:** mutation badges (C1) and paint bucket (C2). Hatch reveal polish.
4. **Group D (P1 polish):** rarity and fusion tier badges, notification icons, toast plate, aura icon, nest check.
5. **Group E (P2):** combat HUD art (BD-248), crystal pack art, Fame Wall and cave sign art, remaining FX v2 textures, potion rarity frames.

Roblox upload (all groups): Studio, View > Asset Manager > Bulk Import, owner account, as before. Upload as **Image** (not Decal). Paste back `name: rbxassetid://...` lines.

## 2. Binding legend

- **AUTO**: the lead binds with a script or one table edit, no new logic, after the owner pastes the id.
- **TABLE**: one config-table edit plus a docs/77 line.
- **CODE**: a small code change (new key or placeholder swap) by a named agent task first.

## 3. Priority 0: blocks the playtest look

### A1. Eggs page stage image (render exists, upload only)
- What: jungle waterfall stage with a stone pedestal, no egg (Blender render, owner-approved). docs/77 `egg_stage_jungle`, BD-208.
- Used: Eggs page background (pedestal top centre about x 50 %, y 72 %); replaces the code tile-floor PLACEHOLDER in `src/client/EggPicture.luau` and `EggsScreen.luau`.
- File: `resources/ui/v2/stage/egg-stage-jungle-v1.jpg` (opaque JPG, upload as is). No prompt needed.
- Bind: AUTO. The BD-208 reader is wired (Eggs page and Conditions shop); key `egg_stage`; `tools/upload_batch.py` lists the file.
- After upload: lead records the id in docs/77, spawns the BD-208 bind agent, Studio check desktop + phone, removes the PLACEHOLDER comments.

### A2. Five condition eggs (renders exist, upload only)
- What: outlined egg PNGs, transparent 1024 px: cracked, dirty, normal, rainbow, astra (docs/77 `egg_condition_layers`, BD-208).
- Used: Eggs page egg on the pedestal, Buy Egg confirm, Conditions tab (replace the tinted code egg in `EggPicture.luau`).
- Files: `resources/ui/v2/stage/eggs/egg-01_cracked.png`, `egg-02_dirty.png`, `egg-03_normal.png`, `egg-04_rainbow.png`, `egg-05_astra.png`. No prompt needed.
- Bind: AUTO. The BD-208 reader is wired: keys `egg_cond_<condition>` (ConditionStageAssetIds) via `tools/bind_assets.py`; `tools/upload_batch.py` lists all five.
- After upload: paste five ids, docs/77 lines, bind agent wires `EggPicture`, Studio screenshot of all five on the pedestal.

### B1. Shared trail ribbon texture
- What: ONE straight horizontal soft ribbon used by every trail (tinted per trail; key `ribbonSoft`). Same job as `ribbon-plain` in docs/83 item 5: do not make both.
- Used: `src/shared/EffectAssets.luau` `Requested.ribbonSoft` (id empty today); Trail/Beam texture in `FxRig`, ribbons in `FxUi`.
- Format: **2048 x 512 PNG, WHITE on transparent**, perfectly straight band (no curve, no taper), band about 55 % of the height, bright centre, top and bottom feathered to full transparency, left and right ends fade out; tiles left to right if possible. Under 400 KB (downscale to 1024 x 256 if needed, Roblox stores at most 1024 per side).
- File: `resources/effects/fx-v3/ribbon-soft.png`.
- Prompt (shared style block + FX block, then):
  > A single perfectly straight horizontal glowing ribbon band, exactly centred vertically, 2048 x 512, spanning the full width. Bright white core line, a softer wide white glow around it, faint thin lengthwise streaks inside, edges feathered smoothly to fully transparent at top, bottom, left and right. No curves, no sparkles, no background, no colour.
- Bind: AUTO/TABLE: `Requested.ribbonSoft.id = "rbxassetid://..."` in `EffectAssets.luau`. The older rendered fx-v2 `ribbonSoft` (512x64, upload pending) is a valid stop-gap for the same key.
- After upload: lead sets the id, adds docs/77 `fx3_ribbon`, runs `python tools/verify_fx.py --runner luau.exe`, Studio check on grass and on the navy under-layer, no seam when tiled.

### B2. Ten trail icons (shop cards, 64 px readable)
- What: one distinct icon per trail, a short glowing swoosh in its colour with a small motif. Same angle, outline and light on all ten.
- Used: `src/client/ShopCards.luau` via `P.trailIconId(Config.TrailIconAssetIds, item.id)`; BD-178 / BD-143. Replaces the live preview in the card slot.
- Format: **1024 x 1024 RGBA PNG, COLOURED**, transparent background, 12 % margin, readable at 64 px.
- Files (`resources/ui/v2/icons/`): `trail-white-v1.png`, `trail-fern-v1.png`, `trail-tidal-v1.png`, `trail-ember-v1.png`, `trail-violet-v1.png`, `trail-electric-v1.png`, `trail-frost-v1.png`, `trail-solar-v1.png`, `trail-nova-v1.png`, `trail-astra-v1.png`.
- Owner images that exist but are not in the repo yet: **Normal White puff** (save as `trail-white-v1.png`) and **Fern Drift** (`trail-fern-v1.png`). Use them as style references for the other eight.
- Prompt template: shared style block + ICON block + "Subject: [ROW]. Attach the Normal White and Fern Drift images as style references; same swoosh size, outline thickness and light."

| Trail id | Name | Colours (primary / accent) | Subject line |
|---|---|---|---|
| white | Normal White | white / pale blue-white | (exists) a soft white puff trail swoosh |
| fern | Fern Drift | green #62EC70 / lime | (exists) a green swoosh with two tiny fern leaves |
| tidal | Tidal Wake | aqua #50D6FF / pale cyan | an aqua swoosh curling like a small wave with three bubbles |
| ember | Ember Trail | orange #FF743E / yellow | an orange swoosh trailing three tiny glowing embers |
| violet | Violet Pulse | purple #B46AFF / pink | a purple swoosh with two soft round pulse rings |
| electric | Electric Arc | cyan #50F3FF / lemon | a cyan swoosh with a small rounded zigzag spark through it |
| frost | Frost Comet | ice blue #87E9FF / white | an ice-blue comet swoosh with a round head and two tiny snow crystals |
| solar | Solar Flare | golden #FFD55E / cream | a golden swoosh with a small round sun at the head and short rays |
| nova | Nova Ribbon | purple #B46AFF / gold | a wide purple and gold ribbon swoosh with a four-point star |
| astra | Astra | mint #70FFCD / magenta #FF82E8 | a flowing mint-to-magenta ribbon swoosh with tiny stars (the richest of the ten) |

- Bind: TABLE (AUTO once ids arrive): `ProgressionConfig.TrailIconAssetIds = { white="rbxassetid://...", fern=..., ... }` (empty today; absent key = live preview).
- After upload: lead gets the 10 `trail_<id>: id` lines, bind agent edits the table and adds docs/77 lines `trail_icon_<id>`, runs the shop verifiers, Studio screenshot of the Trail tab at 64 px and on a phone.

### C1. Seven mutation badge icons (BD-190, docs/92 batch 5)
- What: small round badges: Dewdrop = drop, Charged = bolt, Frost = snowflake, Seismic = pebble, Ember = flame, Aurora = wavy ribbon, Blood Moon = crescent moon. Base colours from `src/shared/MutationLook.luau` (docs/92): #78E2BE, #FFE278, #A0E8FF, #E2BE82, #FF8C5A, #8CFADC, #FF7896.
- Used: Eggs cards, My dinos, hatch badge (replace the plain colour dot).
- Format: **1024 x 1024 coloured PNG** (a 128 px export is fine too), one object each, readable at 64 px and 32 px.
- Files (`resources/ui/v2/icons/`): `mutation-dewdrop-v1.png`, `mutation-charged-v1.png`, `mutation-frost-v1.png`, `mutation-seismic-v1.png`, `mutation-ember-v1.png`, `mutation-aurora-v1.png`, `mutation-bloodmoon-v1.png`.
- Prompt: shared style block + ICON block + "Subject: a small round coin-shaped badge with a [drop / lightning bolt / snowflake / pebble / flame / wavy ribbon / crescent moon] symbol in the middle, badge base colour [HEX], cream rim. Same badge shape and size on all seven."
- Bind: CODE (BD-190): keys `mutation_<id>` in `UIIconAssets`, a badge-icon field read by the three badge sites.
- After upload: ids pasted, seven docs/77 lines (`mutation_badge_*`), BD-190 wiring agent, phone screenshot of an Eggs card with a mutation.

### C2. Paint bucket (BD-171, docs/83 item 31)
- What: one cartoon steel paint bucket with a wire handle, side view slightly tilted, open top showing a flat WHITE paint surface (the game tints it per colour).
- Used: `src/client/HatchSequence.luau` reads `Theme.ImageIds.paint_bucket`; replaces the UI-shape PLACEHOLDER bucket.
- Format: 1024 x 1024 RGBA PNG; paint surface pure white or very light grey so tinting works.
- File: `resources/ui/v2/icons/paint-bucket-v1.png`.
- Prompt: shared style block + ICON block + "Subject: one cartoon steel paint bucket with a wire handle, side view slightly tilted, open top showing a flat white paint surface, one small white drip on the rim."
- Bind: AUTO via `tools/bind_ui_icons.py` (key `paint_bucket`; the code already reads it).
- After upload: docs/77 row flips from "planned" to "uploaded, bound", remove the PLACEHOLDER comment, check a hatch with a colour reveal.

## 4. Priority 1: polish (the game works without)

### D1. Rarity badges (6) and fusion tier badges (3) (BD-113, BD-048)
- What: gem badges Common, Uncommon, Rare, Epic, Legendary, Mythic (grey, green, blue, purple, gold, rainbow pearl) and Gold, Emerald, Diamond tier badges.
- Used: shop cards (trail class), Index and dino details, Fusion menu.
- Format: 1024 coloured PNG, transparent, no text.
- Files: `resources/ui/v2/icons/rarity-{common,uncommon,rare,epic,legendary,mythic}-v1.png`, `tier-{gold,emerald,diamond}-v1.png`.
- Prompt: shared + ICON block + "Subject: a small faceted gem badge in a rounded shield shape, colour [grey / green / blue / purple / gold / rainbow pearl]; fancier frame and a bit more sparkle for higher rarity; same shape and angle on all six." Tier: "a round medal with a [gold / emerald-green / clear diamond-blue] gem in the middle".
- Bind: CODE/TABLE (BD-113): keys `rarity_<class>`, `tier_<name>`.

### D2. Notification icons and toast plate (docs/83 items 15-20)
- What: crystal gem, level star, task star, mutation egg, warning triangle, plus a 9-slice toast plate (the toast has an empty icon box today, BD-304).
- Format: icons 1024 RGBA (readable at 32 px); `toast-body-v1.png` **512 x 128**, white-to-light-grey rounded panel (radius about 40 px), darker 6 px rim, 9-slice centre 48 px in from each edge, no icon or text.
- Files (`resources/ui/v2/icons/`): `notify-crystal-v1.png`, `notify-level-v1.png`, `notify-star-v1.png`, `notify-mutation-egg-v1.png`, `notify-warning-v1.png`, `toast-body-v1.png`.
- Prompts: shared + ICON block + subjects "a faceted blue gem" / "a rounded gold star with a white up-chevron" / "a simple chunky five-point gold star" / "an ivory egg with a swirling coloured flame band" / "a rounded orange-red triangle with a white bar and dot". Plate: shared + "a flat empty rounded-rectangle UI panel, 512 x 128, white to light grey with a darker rim, transparent outside".
- Bind: CODE: keys `notify_*`, `toast_body` in `UIIconAssets`, toast code change (BD-304 follow-up).

### D3. Aura icons and potion frames (BD-101)
- Aura icons: owner images exist for Meadow Glow and Tidal Halo (`resources/ui/v2/items/aura-meadow-v1.png`, `aura-tidal-v1.png`, upload pending). Royal Nova is missing: file `resources/ui/v2/items/aura-royal-v1.png`; prompt: shared + ICON block + "a glowing purple and gold ring with a small crown of light above it, matching the Meadow and Tidal aura icons". Bind: TABLE/AUTO (`aura_<id>`).
- Potion icons: the 12 bottles exist in `resources/ui/v2/items/` with `potion_icon_*` registry lines. BD-101 closes when `PotionArt.luau` code bottles are no longer shown; verify each line is "in game".
- Potion rarity frames (5, P2): `resources/ui/v2/components/frame-{common,uncommon,rare,epic,legendary}-v1.png`, 512 x 512, 9-slice. Prompt: shared + "an empty rounded square card frame, thick outline, [grey / green / blue / purple / gold] candy-metal rim, small gems in the top corners, transparent centre and outside".

### D4. Egg nest icons (BD-094)
`egg_nest` (127462994652706) and `egg_nest_single` are uploaded and bound (docs/77 "in game"). BD-094 only needs a Studio check and a status move to Review. No new art. Optional P2 "bonus nest" badge: "an egg nest with a small gold plus badge".

## 5. Priority 2: after the playtest

### E1. Combat HUD art (BD-248; `grep PLACEHOLDER src/client/CombatHud.luau`)
- What: heart (HP), three class badges (docs/101 s10), Bite button, hit bubble. PLACEHOLDER shapes and text today.
- Format: 1024 coloured transparent PNG; Bite button 512 x 256 in a calm teal-orange, not alarm red (docs/87).
- Files: `resources/ui/v2/icons/hud-heart-v1.png`, `hud-class-{1,2,3}-v1.png`, `hud-bite-v1.png`, `hud-hit-bubble-v1.png`.
- Prompt: shared + ICON block + "Subject: a chubby friendly pink-red heart / a round badge showing a dinosaur footprint, a claw, a shield (three class badges) / a chunky round bite button with a friendly dino mouth outline, no teeth, calm teal-orange / a soft white speech bubble with a small star".
- Bind: CODE (BD-248).

### E2. Crystal pack art (Crystal Shop, BD-331; packs stay off while `Config.CrystalPacksEnabled = false`)
- Four icons: `resources/ui/v2/icons/crystals-{s,m,l,xl}-v1.png`, 1024 coloured transparent. Prompt: shared + ICON block + "a pile of faceted blue gems in a [small cloth pouch / bigger cloth bag / wooden chest / golden vault], more gems for bigger packs".
- Bind: CODE (crystal cards in `Bootstrap.client.luau`). This art does not enable Robux packs (docs/43).

### E3. Fame Wall and cave signs (docs/104)
- Today they are uploaded 3D props (`cave_hub_hub_sign_stone`, `hub_sign_arrow`, carved wall frame). Optional art: a "TOP DINOS" plaque and six station medallions (Nests, Potions, Fusion, Style, Index, Settings).
- Format: 1024 RGBA, no text (text is a TextLabel). Files `resources/ui/v2/icons/station-{nests,potions,fusion,style,index,settings}-v1.png`, `fame-plaque-v1.png`.
- Prompt: shared + ICON block + "a round carved-stone sign medallion showing [an egg nest / a potion bottle / two merging dino eggs / a paint brush / an open book with a dino / a gear] in warm cream and moss green".
- Bind: CODE (cave sign SurfaceGuis; needs a new task).

### E4. FX v2 leftovers (white on alpha)
- Rendered, upload only (docs/77 `fx_*`, `resources/effects/fx-v2/`): glowPlate, ringSoft, ringShock, speedLine, crystalSheet (512, 4x4: snow crystals, pebbles, droplets). `starFour` is already served by the fx3 sparkle sheet; `ribbonSoft` is B1. All AUTO: set `Requested.<key>.id` in `EffectAssets.luau`.
- Not rendered yet (BD-186..189): droplet and crescent glow variants, dense smoke and breath variants, thick seismic ring, mutation motif sheets (Aurora is the only coloured one: green, blue, violet, magenta).
- Flipbook rule (TX1 does NOT shrink flipbooks, audit C-41): **4 x 4 cells of 256 px = 1024 px sheet** (as fx-v3), 16 frames, first frame top-left, 15 % cell margin, faded borders, real alpha, under 400 KB.
- Prompt: shared + FX block + "a 4 x 4 grid sheet (16 equal cells) of [motif] animation frames, each centred in its own cell with margin, growing then shrinking". Motifs: droplets and bubbles (Dewdrop), soft zigzag sparks (Charged), six-point snow crystals (Frost), round pebbles and dust (Seismic), embers and flame wisps (Ember), ribbon wisps (Aurora), crimson motes and crescent shimmer (Blood Moon).

Sound is not art: briefs are in docs/85 and docs/87.

## 6. Placeholder inventory (grep PLACEHOLDER in src, 2026-10-16)

| Code | Placeholder | Closed by |
|---|---|---|
| `EggPicture.luau`, `EggsScreen.luau` | code tile floor and tinted egg | A1 + A2 (BD-208) |
| `HatchSequence.luau` | UI-shape paint bucket | C2 |
| `HatchSequence.luau` | puddle, yolk and shell shapes | `egg_splat` and `egg_shell` already uploaded; Studio check pending |
| `CombatHud.luau` | heart glyph, Bite text button, bars | E1 (BD-248) |
| `CombatHud.luau` | `pickup_hi` heads-up sound | sound task, not art |

## 7. After-upload steps for the lead (every group)

1. Owner pastes `name: id` lines. Verify each exists under the owner account with `search_asset` by file name (or Studio `GetProductInfo`) and is an Image; reject anything that is not a plain digit id.
2. Add or update the docs/77 line (id, source file, binding place, status "uploaded, bound").
3. Bind: AUTO items by editing `upload-bindings.json` then `python tools/bind_ui_icons.py`; TABLE items by the one-line edit; CODE items by spawning the named agent (BD-208, BD-190, BD-113, BD-248, BD-304).
4. Run the matching verifier (`tools/verify_fx.py`, the shop and UI verifiers, `verify_release`), then a Studio screenshot on desktop and phone next to neighbouring UI (docs/72 bar: matches the v2 kit, readable at 64 px, no leftover placeholder).
5. Move the Kanban rows (BD-178, BD-190, BD-208, BD-094, BD-113, BD-318) to Review / test; never claim phone acceptance without evidence.

## 8. What the lead can bind automatically

- AUTO or TABLE (no new code): B1 ribbon, B2 trail icons (`TrailIconAssetIds`), C2 paint bucket, E4 FX textures, D3 aura icons.
- Need a small agent task first: A1 and A2 (BD-208), C1 (BD-190), D1 (BD-113), D2 toast, E1 (BD-248), E2, E3.
