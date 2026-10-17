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
- Prompts: shared + ICON block + subjects "a faceted AMBER / golden-yellow gem, never blue (corrected 2026-10-17 per handbook s5.3; it said \"a faceted blue gem\" before)" / "a rounded gold star with a white up-chevron" / "a simple chunky five-point gold star" / "an ivory egg with a swirling coloured flame band" / "a rounded orange-red triangle with a white bar and dot". Plate: shared + "a flat empty rounded-rectangle UI panel, 512 x 128, white to light grey with a darker rim, transparent outside".
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
- Four icons: `resources/ui/v2/icons/crystals-{s,m,l,xl}-v1.png`, 1024 coloured transparent. Prompt: shared + ICON block + "a pile of faceted AMBER / golden-yellow gems (corrected 2026-10-17 per handbook s5.3; it said \"blue\" before) in a [small cloth pouch / bigger cloth bag / wooden chest / golden vault], more gems for bigger packs".
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

## 9. BD-077: the 4 objective icons (brief ready, art pending: owner or Blender, 2026-10-17)

Source: [66](66-intake-mini-objectives.md) section 9 names the four new icons of the objectives panel: **chevron toggle, tutorial arrow, crystal and star** (crystal and star are shared with the notification toasts of [65](65-intake-notifications.md), so they are made ONCE). Nothing is drawn in code: [72](72-ui-copy-and-asset-standards.md) and [AGENTS.md](../AGENTS.md) say final icons come from Blender or from the owner with ChatGPT. Status lives only in the Kanban (BD-077; the wiring is BD-561). **Never invent asset ids.**

**Today** (`src/client/ObjectivesPanel.luau`, BD-075): the panel draws the registered `trophy` icon and plain text only. It has no icon-id slot of its own; it has no chevron, arrow, gem or star. With the four ids empty the panel must stay exactly as it is now (trophy, text, chip).

### 9.1 What the owner makes (4 files, 512 x 512 transparent PNG each)

| # | Icon | File (`resources/ui/v2/icons/`) | Slot name (`Theme.ImageIds` key) | Slot today | Made by |
|---|---|---|---|---|---|
| 1 | Chevron toggle | `objective-chevron-v1.png` | `objective_chevron` | NEW, empty-id slot added by BD-561 | ChatGPT or Blender |
| 2 | Tutorial arrow | `objective-arrow-v1.png` | `objective_arrow` | NEW, empty-id slot added by BD-561 | ChatGPT or Blender |
| 3 | Crystal (shared with [65](65-intake-notifications.md), made once) | `notify-crystal-v1.png` | `notify_crystal` | exists in `AssetSlots.Images`, id empty (BD-304) | ChatGPT or Blender |
| 4 | Star (shared with [65](65-intake-notifications.md), made once) | `notify-star-v1.png` | `notify_star` | exists in `AssetSlots.Images`, id empty (BD-304) | ChatGPT or Blender |

If icons 3 and 4 are already made for the toasts (D2 above, [83](83-playtest-asset-list.md) items 15 and 17), do NOT make them again: the same file serves both. This section is the better spec for them, because it adds the 24 px rules and the amber colour.

**Colour conflict to know about (handbook wins).** [83](83-playtest-asset-list.md) item 15 and D2 above still say "faceted BLUE gem" for the crystal. [114](114-handbook.md) section 5.3 (owner 2026-10-16) and [136](136-owner-art-and-sound-quick-prompts.md) say crystal currency art is **AMBER / yellow, never blue**. This brief uses amber. The old "blue" words in 83 and D2 are superseded by 114 s5.3. **Corrected 2026-10-17 (BD-561):** the "blue" words in [83](83-playtest-asset-list.md) item 15, D2 above, E2 (crystal packs) and [65](65-intake-notifications.md) now say amber, each with a "corrected 2026-10-17 per handbook s5.3" note; this paragraph keeps the old wording as the record of what the conflict was.

### 9.2 Rules for all four

- **Size and format:** the repo file is **512 x 512 RGBA PNG** (TX1 in [115](115-decisions-log.md): UI icons at 512 px max; the art reads the same at 256 px, so 256 is also allowed if the lead agrees). ChatGPT will give 1024 x 1024; downscale to 512 for the repo and upload copy. TRUE transparent background: the four corner pixels are fully transparent (no checkerboard, no white or black box, no ground, no drop-shadow plane).
- **Readable at 24 to 44 px:** the icons show tiny (chevron 24 px, crystal 20 to 24 px, arrow and star 28 to 32 px, never above 44 px). So: ONE object, 3 to 4 big shapes, no fine detail. No lines thinner than 4% of the canvas (about 20 px at 512). No sparkle bursts, no tiny stars or glints, no text, digits or letters. Keep at least 12% empty margin on every side (the outline counts as part of the shape).
- **Own silhouette each:** the four must be told apart by SHAPE alone at 24 px, in grey-scale. Chevron = open V, no body. Arrow = solid block arrow with a tail. Crystal = pointed faceted kite/diamond. Star = round-ish five-point star.
- **Outline:** thick clean outline in outline/dark text **#0D0F14** (docs/114 s5.1), about 4% of the canvas wide (about 20 px at 512), even all round, rounded corners. The icons sit on the dark panel **#2A2835** and on cards **#3D3A49** (s5.1), where a dark outline alone disappears, so the FILL must be bright and light (gold, green, white highlight) and the shape reads by its fill; also add a thin white-ish rim just inside the outline.
- **Look:** anime cel-shaded, chunky, rounded, matte (no gloss), bright light from the top-left, one flat highlight patch, one soft shade patch bottom-right. Same hand as the trophy and the mutation badges.
- **Palette (docs/114 s5, hex values only from there):** outline **#0D0F14**; gold **#FFD22B** (s5.1); accent green **#5DED1F** (s5.1); white **#FFFFFF** (s5.1); amber **#F1A024** (s5.3, "Amber egg colour"). No blue, purple or red in any of the four (blue is for Rare and for water; red is Mythic). Colour is never the only clue.
- **Check before sending (docs/72 bar):** put each PNG on a `#2A2835` rectangle, shrink to 24, 32 and 44 px, put the four in a row: all four must be clearly different, crisp, and not blurry. Each file under 100 KB.

### 9.3 Icon 1: chevron toggle (`objective-chevron-v1.png`)

- **Purpose:** the "open or fold me" hint on the objectives header. The whole 44 px header is already the tap target; the chevron is only the picture of it.
- **Where it shows:** right end of the objectives header, folded pill AND open panel, 24 px. Drawn **pointing DOWN** ("tap to open"). The game rotates it 180 degrees when the panel is open, so the shape must be left-right symmetric and have no tail or body.
- **Silhouette:** one bold rounded chevron "V", arms about 24% of the canvas thick, round ends, opening angle about 100 degrees, 76% of the canvas wide and 44% tall, centred. No plate, no circle, no shadow.
- **Colours:** gold **#FFD22B** fill, **#0D0F14** outline, one white **#FFFFFF** highlight stripe on the upper-left of each arm, a soft **#F1A024** shade on the lower edge of each arm. (The baked top-left light flips when the game rotates it; at 24 px that is fine.)
- **Prompt (copy-ready):**
  > Be Dino! is a friendly Roblox dinosaur game for young children. Style: anime cel-shaded, bubbly and soft, saturated but harmonious colours, thick clean dark outline, rounded chunky shapes, matte (no harsh shine), bright top-left light, calm and cozy, never scary or sharp. No text, letters, digits, logos or watermark. Match my existing icons (trophy, egg nest, weather icons). One single UI icon on a square 1024 x 1024 canvas, TRUE transparent background (real alpha channel, no ground, no shadow plane, no frame, no checkerboard), at least 12% empty margin on all sides, readable when shrunk to 24 pixels, broad simple shapes. Subject: one bold chunky rounded chevron pointing DOWN, like a thick letter V with rounded ends and no tail, left-right symmetric, centred. Golden yellow fill #FFD22B, thick near-black outline #0D0F14, one white highlight stripe on the upper-left of each arm, soft amber #F1A024 shade on the lower edge. Flat front view, no 3D tilt, no extra decoration.
- **Blender alternative:** extrude a 2D V outline with a round bevel (flat orthographic front view), matte material in #FFD22B, one top-left key light, a thin outline from an inverted-hull or Freestyle line in #0D0F14; render 512 x 512 with a transparent film. Same pattern as `tools/blender/build_mutation_badges.py` and `build_trail_icons.py` (point-list outlines, soft pillow bevel, white rim plus thin dark line).
- **Good looks like:** at 24 px it is plainly a down-pointing chevron, not a smudge; thick enough that the dark outline is still one pixel wide.

### 9.4 Icon 2: tutorial arrow (`objective-arrow-v1.png`)

- **Purpose:** points the new player at "do this next" during the first tutorial tasks (T1 to T9, [66](66-intake-mini-objectives.md) s5). It is the only hint picture the tutorial gets.
- **Where it shows:** left of the name of the first unfinished TUTORIAL row in the open panel, and next to the folded pill's task while a tutorial task is first, 28 to 32 px; the game bobs it 3 to 4 px and rotates it to point where needed (off with Reduce Motion, [114](114-handbook.md) s4.5). Never on Short or Daily rows.
- **Silhouette:** a chunky solid block arrow pointing **RIGHT**: a fat rounded head and a short stubby tail about 45% as thick as the head; 84% of the canvas wide, 56% tall; every corner rounded; no curve, no feathers, no dashed line. It must not look like the chevron (that one is an open V; this one is solid with a tail).
- **Colours:** accent green **#5DED1F** fill (s5.1), **#0D0F14** outline, white **#FFFFFF** highlight patch on the upper-left of the head, soft darker-green shade on the lower edge (a shade of #5DED1F, not a new hue).
- **Prompt (copy-ready):**
  > Be Dino! is a friendly Roblox dinosaur game for young children. Style: anime cel-shaded, bubbly and soft, saturated but harmonious colours, thick clean dark outline, rounded chunky shapes, matte (no harsh shine), bright top-left light, calm and cozy, never scary or sharp. No text, letters, digits, logos or watermark. Match my existing icons (trophy, egg nest, weather icons). One single UI icon on a square 1024 x 1024 canvas, TRUE transparent background (real alpha channel, no ground, no shadow plane, no frame, no checkerboard), at least 12% empty margin on all sides, readable when shrunk to 28 pixels, broad simple shapes. Subject: one chunky solid block arrow pointing RIGHT, a fat rounded arrowhead with a short stubby rounded tail, all corners rounded, centred, flat front view. Bright lime green fill #5DED1F, thick near-black outline #0D0F14, one white highlight patch on the upper-left of the head, a soft darker-green shade on the lower edge. No motion lines, no sparkles, no extra decoration.
- **Blender alternative:** same as the chevron: a 2D arrow outline, extrude with a soft round bevel, matte green, orthographic front view, dark outline line, 512 x 512 transparent film.
- **Good looks like:** at 28 px nobody needs to be told it is an arrow, and it is clearly not the chevron.

### 9.5 Icon 3: crystal (`notify-crystal-v1.png`, shared with 65)

- **Purpose:** "crystals" (the currency) in small spaces, so the word does not have to be spelled out each time.
- **Where it shows:** objectives panel: after the "+10" on each task's prize line, and in the claim answer in the header ("+10", then the gem), 20 to 24 px; also the crystal toast and the "Need 150" warning of [65](65-intake-notifications.md), 28 to 32 px.
- **Silhouette:** one faceted gem, a tall kite/diamond with a flat top "table", a slightly wider crown and a pointed bottom, 3 or 4 big facets only (no tiny facets: they turn to mud at 20 px), 66% of the canvas wide and 80% tall. Friendly low-poly, rounded edges.
- **Colours (handbook s5.3, crystals are AMBER, never blue):** body amber **#F1A024**, light facets gold **#FFD22B**, one white **#FFFFFF** glint patch on the upper-left facet, **#0D0F14** outline. Not blue, not purple, not red.
- **Prompt (copy-ready):**
  > Be Dino! is a friendly Roblox dinosaur game for young children. Style: anime cel-shaded, bubbly and soft, saturated but harmonious colours, thick clean dark outline, rounded chunky shapes, matte (no harsh shine), bright top-left light, calm and cozy, never scary or sharp. Crystals and gems are AMBER / golden yellow, never blue. No text, letters, digits, logos or watermark. Match my existing icons (trophy, egg nest, weather icons). One single UI icon on a square 1024 x 1024 canvas, TRUE transparent background (real alpha channel, no ground, no shadow plane, no frame, no checkerboard), at least 12% empty margin on all sides, readable when shrunk to 20 pixels, broad simple shapes. Subject: one faceted amber gem, a kite-shaped diamond with a flat top and a pointed bottom, only 3 or 4 big chunky facets, rounded edges. Amber body #F1A024 with lighter golden facets #FFD22B, one white highlight patch on the upper-left facet, thick near-black outline #0D0F14. Front view, centred, no sparkle bursts, no shine rays.
- **Blender alternative:** a low-poly gem (a cylinder with 6 sides, top cut flat, bottom to a point, flat shading so each facet is one colour), matte, two amber tones from #F1A024 and #FFD22B, orthographic camera, outline in #0D0F14, 512 x 512 transparent. This is the same gem language as the cave and shop crystals (amber only, s5.3).
- **Good looks like:** at 20 px it is a small golden gem; it does not look like the star next to it.

### 9.6 Icon 4: star (`notify-star-v1.png`, shared with 65)

- **Purpose:** "done" and "well done" (a finished task, a completed objective), the picture of a small win.
- **Where it shows:** left of the "Done!" chip on the folded pill when a task can be claimed; on a finished task row beside its prize; and as the icon of the "objectives done" toast of [65](65-intake-notifications.md), 28 to 32 px. (The one-line goal text "Done! Claim in Tasks" stays text only.)
- **Silhouette:** a chunky five-point star with rounded points, fat (inner radius about 55% of the outer), pointing up, 80% of the canvas wide, centred. NO chevron inside it (that is the separate `notify_level` star). NOT a sparkle or a burst.
- **Colours:** gold **#FFD22B** face (s5.1), **#0D0F14** outline, white **#FFFFFF** highlight patch on the upper-left point, a **#F1A024** shade on the lower-right edge.
- **Prompt (copy-ready):**
  > Be Dino! is a friendly Roblox dinosaur game for young children. Style: anime cel-shaded, bubbly and soft, saturated but harmonious colours, thick clean dark outline, rounded chunky shapes, matte (no harsh shine), bright top-left light, calm and cozy, never scary or sharp. No text, letters, digits, logos or watermark. Match my existing icons (trophy, egg nest, weather icons). One single UI icon on a square 1024 x 1024 canvas, TRUE transparent background (real alpha channel, no ground, no shadow plane, no frame, no checkerboard), at least 12% empty margin on all sides, readable when shrunk to 28 pixels, broad simple shapes. Subject: one simple chunky five-point star with fat rounded points, pointing up, centred, flat front view. Golden yellow face #FFD22B, thick near-black outline #0D0F14, one white highlight patch on the upper-left point, soft amber #F1A024 shade on the lower-right edge. Nothing inside the star, no sparkles, no rays, no glow.
- **Blender alternative:** a five-point star outline with generous rounding, extrude with a soft pillow bevel, matte gold #FFD22B, top-left key light, dark outline #0D0F14, orthographic, 512 x 512 transparent.
- **Good looks like:** at 28 px it is a solid, happy gold star, distinct from the gem and from the green arrow.

### 9.7 Where the panel reads the ids, and the empty-id gate

- **Reader:** all four go through the existing `Theme.ImageIds` table (`UITheme.luau` merges `AssetSlots.Images` into it; an empty id is not merged, so the key is simply absent). Slot names: `objective_chevron`, `objective_arrow` (new, added to `AssetSlots.luau`, `tools/asset_slots.json` and the [120](120-pending-owner-uploads-checklist.md) table by BD-561) and `notify_crystal`, `notify_star` (already exist, empty). Bind after upload with `python tools/bind_assets.py ids.txt` (lines `objective_chevron=rbxassetid://N`).
- **Gate (WRITTEN by BD-561, 2026-10-17, offline only; text below is the spec it follows):** `ObjectivesPanel` gets one local helper, in words: "if `Theme.ImageIds[key]` is nil or empty, draw nothing and reserve no space; else `Theme.icon(parent, key)`". The header keeps `Theme.icon(header, "trophy")` always. So with all four ids empty the panel's Instance tree, text widths and `TouchLayout` rects are identical to today (`tools/verify_objectives_panel.py` gets one case for that), and each icon appears on its own as soon as its id is bound.
- **Tight widths:** the folded pill is 190 to 300 px wide on phones (trophy 36 px + chip 68 px already); the chevron needs about 28 px more. BD-561 checks the text fit at 190 px and may shorten the title; it never shrinks the 44 px tap target or the 14 px text floor. **As built (BD-561):** with the chevron the 190 px pill gives the task name about 52 px, so the name is cut at a WHOLE word ("Hatch...", "Finish...") by `ObjectivePanelRules.fitWords` (one fallback word "Task" when not even the first word fits); the chip and the chevron always stay. The tutorial arrow and the Done-chip star sit in the folded pill only when the name keeps at least 72 px (`Rules.MinTitle`), i.e. on pills of about 242 px and wider: today that is the desktop and 836 x 390 pill (300 px); the 667 x 375 pill (203 to 220 px) shows the name and chip instead, and the arrow and star still show in the open rows (the arrow only if the name still fits two lines beside it). Gem: after the prize number on every row ("+10" then the gem; the words "+10 crystals" when the gem does not fit) and after the number in the claim answer. Star: left of the Done chip, and left of the prize on a finished row. The chevron turns 180 degrees when the panel is open; the arrow bobs 3 px every half second unless Reduce Motion is on.

### 9.8 After the owner has the PNGs

1. Save the four files at the paths in 9.1; send them to the lead (or run the Blender session). Check them with the 24 / 32 / 44 px test of 9.2.
2. Lead: upload (Studio, Asset Manager, Bulk Import, owner account, as **Image**), then `python tools/bind_assets.py ids.txt`; the four [77](77-asset-registry.md) "planned" lines become "uploaded, bound".
3. BD-561 wires the panel (can be built and merged before the art exists, because empty ids change nothing).
4. Studio screenshot of the folded pill and the open panel at desktop and 836 x 390 (BD-078); move BD-077 to Review / test only with that picture.
