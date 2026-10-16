# 136 Owner art and sound quick prompts: paste, generate, send back the slot name (2026-10-16)

**Purpose:** make the owner's job as fast as possible. Every still-pending art or sound item from [120](120-pending-owner-uploads-checklist.md) has a ready-to-paste prompt (ChatGPT image generation for 2D, a Blender or `generate_mesh` brief for 3D, Creator Store search words for sounds), an exact size and layout, a "good looks like" line and the **slot name** to send back in chat as `slot = id` (for example `trail_tidal = 123456789`; ids are never invented by agents). **Docs only; nothing is built or bound by this file.**

**How this relates to other docs (nothing is duplicated, this is the single prompt sheet):**
- It **merges and replaces for prompting purposes** the ChatGPT text of [109](109-owner-art-prompt-pack.md) (B1, B2, C1, C2, D1-D3, E1-E4), the Blender session of [83](83-playtest-asset-list.md) (ribbon item 5 = B1, notification items 15-20 = D2) and BD-336 (the prompt-pack task). 109 stays as the history and the after-upload steps; if a prompt here and in 109 differ, **this file wins** (it adds the handbook look and exact layouts).
- Status lives in [the Kanban](07-kanban.md); ids in [77](77-asset-registry.md); the full pending list and binding columns in [120](120-pending-owner-uploads-checklist.md); sound rules in [124](124-sound-style-guide.md). Look rules: [114](114-handbook.md) section 0 and 4 (polished, satisfying, calm, bubbly, friendly, vibrant; friendly low-poly, matte, chunky; amber crystals; icons readable at 64 px; kids 7-10).
- Binding after you send ids: `python tools/bind_assets.py ids.txt` with lines `slot=rbxassetid://N` (slot names below are the `bind_assets.py` names; `python tools/bind_assets.py --list` shows all).

## 0. Paste blocks (put the STYLE block first in EVERY ChatGPT prompt)

**STYLE block**
> Be Dino! is a friendly Roblox dinosaur game for young children. Style: polished anime cel-shaded, bubbly, soft and chunky rounded shapes, saturated but harmonious vibrant colours (no muddy greys), thick clean dark outline, matte look (no harsh shine), bright light from the top left, calm, cosy and friendly, never scary, sharp or edgy. Crystals and gems are AMBER / golden yellow unless I say otherwise. No text, letters, digits, logos or watermark. Match my existing images (egg nest, trophy, weather icons, potion bottles).

**ICON block** (colour icons)
> One single object, three-quarter view slightly from above, centred on a square 1024x1024 canvas, whole object visible, at least 12% empty margin on all sides, TRUE transparent background (a real alpha channel: no ground, no shadow plane, no frame, no checkerboard), readable when shrunk to 64 pixels, broad simple shapes.

**FX block** (white tint textures)
> Pure WHITE shapes on a fully transparent background, no colour, no black background, soft feathered edges that fade to fully transparent before touching the image border, anime cel style with a bright core and a softer outer edge. The game tints it at runtime.

**FLIPBOOK add-on** (any "sheet" below)
> A 4 x 4 grid (16 equal cells of 256 px, the sheet is exactly 1024 x 1024), first frame top-left reading left to right then down, each frame centred in its own cell with a 15% margin, nothing touching a cell edge, the animation grows then fades over the 16 frames.

**Always ask for a transparent PNG.** If ChatGPT gives a black or white background, say "remove the background, keep a real alpha channel" or tell the lead (we have an alpha clean-up). Corner pixels must be fully transparent. **Consistency trick:** after the first good image in a group, attach it to every next prompt: "Same style, outline thickness, light direction and size as the attached image."

**Upload:** Studio > View > Asset Manager > Bulk Import, owner account, as **Image** (not Decal); send `slot = id` lines in chat. Sounds are uploaded as **Audio** (section 7).

## Batch order (priority; session-1 visible first)

| Batch | What | Items | Blocks |
|---|---|---|---|
| 1 | Upload only (files already in the repo) | egg stage, 5 condition eggs, glow/ring/speed/crystal FX, ribbon stop-gap, 2 aura icons, 2 trail icons | BD-208, BD-394, BD-186..189 look |
| 2 | Trails | 1 ribbon + 8 new trail icons | BD-178, BD-336 |
| 3 | Hatch reveal | 7 mutation badges, paint bucket icon, class icons, rarity + tier badges | BD-190, BD-171, BD-113 |
| 4 | Hatch sounds | 5 reveal stings, rare fanfare, mutation sounds, burst/rattle/cracked | BD-081, BD-428, BD-437, BD-162 |
| 5 | FX sheets | glow/smoke/ring/motif sheets, confetti, anime FX P0 | BD-186..189, BD-430 |
| 6 | Polish icons | notifications, toast plate, Royal aura, potion frames | BD-304, BD-101 |
| 7 | Hatch v2 + cave | paint FX, bucket mesh, lava crust, gate arch, cave sounds, weather sounds | BD-397, BD-385, BD-132 |
| 8 | P2 | combat HUD, crystal packs, station medallions, golden drumstick, anime FX P1/P2 | BD-248, BD-331, BD-207 |

---

## BATCH 1. Upload only (no prompt, files exist in the repo)

Save nothing new; just bulk-import these files and send the ids.

| File (repo path) | Slot name to send back |
|---|---|
| `resources/ui/v2/stage/egg-stage-jungle-v1.jpg` | `egg_stage` |
| `resources/ui/v2/stage/eggs/egg-01_cracked.png` ... `egg-05_astra.png` | `egg_cond_cracked`, `egg_cond_dirty`, `egg_cond_normal`, `egg_cond_rainbow`, `egg_cond_astra` |
| `resources/effects/fx-v2/glowPlate.png`, `ringSoft.png`, `ringShock.png`, `speedLine.png`, `crystalSheet.png` | `glowPlate`, `ringSoft`, `ringShock`, `speedLine`, `crystalSheet` |
| `resources/effects/fx-v2/ribbonSoft.png` (stop-gap; skip if you do B1 below) | `ribbonSoft` |
| `resources/ui/v2/items/aura-meadow-v1.png`, `aura-tidal-v1.png` | `aura_meadow`, `aura_tidal` |
| your two owner trail images saved as `resources/ui/v2/icons/trail-white-v1.png`, `trail-fern-v1.png` | `trail_white`, `trail_fern` |

Good looks like: the egg stage JPG is opaque; the five eggs have transparent corners.

---

## BATCH 2. Trails (BD-178, BD-336)

### B1. Trail ribbon (ChatGPT; or Blender, same job as 83 item 5)
- **Slot:** `ribbonSoft`. **File:** `resources/effects/fx-v3/ribbon-soft.png`. **Format:** 2048 x 512 PNG (1024 x 256 is fine), white on alpha, under 400 KB.
- **Prompt:** STYLE + FX block + "A single perfectly straight horizontal glowing ribbon band, exactly centred vertically, spanning the full width of a 2048 x 512 canvas. Bright white core line, a softer wide white glow around it, faint thin lengthwise streaks inside, edges feathered smoothly to fully transparent at top, bottom, left and right. No curves, no sparkles, no background, no colour."
- **Good looks like:** one straight soft band, no taper or curve, no hard edge, left and right ends match so it tiles without a seam.

### B2. Eight new trail icons (the white and fern ones are yours already; attach them as references)
- **Slots:** `trail_tidal`, `trail_ember`, `trail_violet`, `trail_electric`, `trail_frost`, `trail_solar`, `trail_nova`, `trail_astra`. **Files:** `resources/ui/v2/icons/trail-<id>-v1.png`.
- **Format:** 1024 x 1024 RGBA PNG, coloured, 12% margin, readable at 64 px.
- **Prompt template:** STYLE + ICON block + "Subject: [ROW]. Attach my Normal White and Fern Drift images as style references; same swoosh size, outline thickness and light direction."

| Slot | Subject line |
|---|---|
| `trail_tidal` | an aqua (#50D6FF) swoosh curling like a small wave with three bubbles, pale cyan accents |
| `trail_ember` | an orange (#FF743E) swoosh trailing three tiny glowing embers, yellow accents |
| `trail_violet` | a purple (#B46AFF) swoosh with two soft round pulse rings, pink accents |
| `trail_electric` | a cyan (#50F3FF) swoosh with a small rounded zigzag spark through it, lemon accents |
| `trail_frost` | an ice-blue (#87E9FF) comet swoosh with a round head and two tiny snow crystals, white accents |
| `trail_solar` | a golden (#FFD55E) swoosh with a small round sun at the head and short soft rays, cream accents |
| `trail_nova` | a wide purple (#B46AFF) and gold ribbon swoosh with a four-point star |
| `trail_astra` | a flowing mint (#70FFCD) to magenta (#FF82E8) ribbon swoosh with tiny stars (the richest of the ten) |

- **Good looks like:** the ten read as one family at 64 px (same swoosh size and outline), each clearly its own colour, rarer ones a little fancier.

---

## BATCH 3. Hatch reveal icons

### C1. Seven mutation badges (BD-190)
- **Slots:** `mutation_dewdrop`, `mutation_charged`, `mutation_frost`, `mutation_seismic`, `mutation_ember`, `mutation_aurora`, `mutation_bloodmoon`. **Files:** `resources/ui/v2/icons/mutation-<id>-v1.png`. **Format:** 1024 RGBA PNG (128 px export ok), readable at 64 AND 32 px.
- **Prompt:** STYLE + ICON block + "Subject: a small round coin-shaped badge with a [SYMBOL] in the middle, badge base colour [HEX], cream rim. Same badge shape, rim width and size on all seven."

| Slot | SYMBOL | HEX |
|---|---|---|
| `mutation_dewdrop` | water drop | #78E2BE |
| `mutation_charged` | lightning bolt (rounded) | #FFE278 |
| `mutation_frost` | six-point snowflake (chunky) | #A0E8FF |
| `mutation_seismic` | round pebble | #E2BE82 |
| `mutation_ember` | small flame | #FF8C5A |
| `mutation_aurora` | wavy ribbon | #8CFADC |
| `mutation_bloodmoon` | crescent moon | #FF7896 |

- **Good looks like:** one friendly symbol each, thick outline, still recognisable at 32 px, nothing scary (Blood Moon is a soft pink-red crescent, not gory).

### C2. Paint bucket icon (BD-171)
- **Slot:** `paint_bucket`. **File:** `resources/ui/v2/icons/paint-bucket-v1.png`. **Format:** 1024 RGBA; the paint surface must be pure white or very light grey (the game tints it).
- **Prompt:** STYLE + ICON block + "Subject: one cartoon steel paint bucket with a wire handle, side view slightly tilted, open top showing a flat WHITE paint surface, one small white drip on the rim."
- **Good looks like:** chunky bucket, white (not coloured) paint so it tints cleanly.

### C3. Class icons (owner 2026-10-16; never made)
- **Slots:** `class_ground`, `class_flyer`, `class_water`, `class_armored`. **Files:** `resources/ui/v2/icons/class-<name>-v1.png`. **Format:** 1024 RGBA, round badge, readable at 48 px. **Colour per class** (no colour table exists, [114](114-handbook.md) conflict C-18: these are suggestions, the owner may change them): Ground earthy green-brown, Flyer sky blue, Water teal, Armored warm steel-orange.
- **Prompt:** STYLE + ICON block + "Subject: a round coin badge with a [SYMBOL] in the middle, rim colour [COLOUR], cream inner ring. Same badge on all four."

| Slot | SYMBOL | COLOUR |
|---|---|---|
| `class_ground` | chunky dinosaur footprint | earthy green-brown |
| `class_flyer` | two rounded wings | sky blue |
| `class_water` | water drop over two small waves | teal |
| `class_armored` | rounded shield with a small spike row | warm steel-orange |

- **Good looks like:** a kid can tell the four apart by shape alone, not just colour.

### D1. Rarity badges (6) and tier badges (3) (BD-113, BD-048)
- **Slots:** `rarity_common`, `rarity_uncommon`, `rarity_rare`, `rarity_epic`, `rarity_legendary`, `rarity_mythic`, `tier_gold`, `tier_emerald`, `tier_diamond`. **Files:** `resources/ui/v2/icons/rarity-<name>-v1.png`, `tier-<name>-v1.png`. 1024 RGBA, no text.
- **Prompt (rarity):** STYLE + ICON block + "Subject: a small faceted gem badge in a rounded shield shape, colour [grey #808E9E / green #5DED1F / blue #2ECEFF / purple #C256FF / gold #FFD22B / rainbow pearl]; a fancier frame and a bit more sparkle for each higher rarity; same shape and angle on all six."
- **Prompt (tier):** STYLE + ICON block + "Subject: a round medal with a [gold / emerald-green / clear diamond-blue] gem in the middle; Diamond has the fanciest rim."
- **Good looks like:** rarity colours exactly match the game colours; the ladder reads at a glance.

---

## BATCH 5. FX sheets (white on alpha; BD-186..189, BD-162, BD-428, BD-430)

All use STYLE + FX block (+ FLIPBOOK add-on for sheets). **Good looks like (all):** soft, calm, no hard edges, no flicker between frames, real alpha, under 400 KB.

| Slot(s) | File | Format | Prompt subject line |
|---|---|---|---|
| `glowPlateDroplet`, `glowPlateCrescent` | `resources/effects/fx-v2/glowPlate-droplet.png`, `-crescent.png` | 256 px single | "a soft round glow plate in the shape of a water droplet" / "...a crescent moon", bright core, feathered edge |
| `smokeDense`, `smokeWispy` | `resources/effects/fx-v3/smoke-dense.png`, `smoke-wispy.png` | flipbook 1024 | "puffy rounded cartoon smoke puff growing and fading" / "thin wispy breath of smoke curling up and fading" |
| `ringSeismic` | `resources/effects/fx-v2/ringSeismic.png` | 256 px single | "a thick soft round ring, wide band, bright inner edge fading outward" |
| `motifDroplets` | `resources/effects/fx-v3/motif-droplets.png` | flipbook | "round water droplets and tiny bubbles floating up and popping" |
| `motifSoftSparks` | `...motif-softsparks.png` | flipbook | "soft rounded zigzag electric sparks twinkling, no sharp points" |
| `motifSnowCrystals` | `...motif-snowcrystals.png` | flipbook | "chunky six-point snow crystals drifting and fading" |
| `motifPebbles` | `...motif-pebbles.png` | flipbook | "round pebbles and soft dust puffs hopping up and settling" |
| `motifEmbers` | `...motif-embers.png` | flipbook | "round embers and tiny flame wisps rising and fading" |
| `motifAurora` | `...motif-aurora.png` | flipbook, **the ONE coloured sheet** | "flowing aurora ribbon wisps in green, blue, violet and magenta" (drop the FX-block "white only" rule for this one) |
| `motifCrimson` | `...motif-crimson.png` | flipbook | "crimson motes and a small crescent shimmer, soft" |
| `confetti` | `resources/effects/fx-v3/confetti.png` | flipbook | "tumbling confetti squares, ribbons and stars, 16 cells" (BD-428; colour is added in game) |
| `flameTongue` | `resources/effects/fx-v4/flame-tongue.png` | flipbook | "a calm soft flame tongue swaying, no flicker, rounded tip" (anime FX P0, BD-430) |
| `starPop` | `resources/effects/fx-v4/star-pop.png` | flipbook, 8 distinct frames repeated | "a four-point star twinkle that pops in, glows, then fades" |

Notes: the older fx-v2 smoke, spark and flame sheets are superseded by the uploaded fx-v3 sheets; do not upload both. Several of these can be Blender renders instead (Claude via Blender MCP on the owner's PC) if ChatGPT frames wobble; say so and the lead renders them.

---

## BATCH 6. Polish icons

### D2. Notification icons and toast plate (BD-304 follow-up)
- **Slots/files** (`resources/ui/v2/icons/`): `notify_crystal` = `notify-crystal-v1.png`, `notify_level`, `notify_star`, `notify_mutation_egg`, `notify_warning`, `toast_body` = `toast-body-v1.png`.
- **Icons** (1024 RGBA, readable at 32 px): STYLE + ICON block + subject: "a faceted AMBER gem" / "a rounded gold star with a white up-chevron" / "a simple chunky five-point gold star" / "an ivory egg with a swirling coloured flame band" / "a rounded orange triangle with a white bar and dot" (calm, not alarm red).
- **Toast plate** (512 x 128, 9-slice, centre 48 px in): STYLE + "a flat empty rounded-rectangle UI panel, 512 x 128, white to light grey, rounded corners about 40 px, darker 6 px rim, transparent outside, no icon, no text".
- **Good looks like:** the plate stretches without distorting corners.

### D3. Royal Nova aura icon and potion rarity frames
- **Slot `aura_royal`**, file `resources/ui/v2/items/aura-royal-v1.png`, 1024 PNG: STYLE + ICON block + "a glowing purple and gold ring with a small crown of light above it, matching my Meadow and Tidal aura icons (attached)".
- **Slots `frame_common`, `frame_uncommon`, `frame_rare`, `frame_epic`, `frame_legendary`**, files `resources/ui/v2/components/frame-<rarity>-v1.png`, 512 x 512, 9-slice, transparent centre and outside: STYLE + "an empty rounded square card frame, thick outline, [grey #808E9E / green #5DED1F / blue #2ECEFF / purple #C256FF / gold #FFD22B] candy-metal rim, small gems in the top corners, centre fully transparent".
- **Good looks like:** the five share one shape; only rim colour and gem count change.

---

## BATCH 7. Hatch v2, cave and world (BD-397, BD-385, BD-284)

### Paint FX (white on alpha, STYLE + FX block + FLIPBOOK add-on)
- `paintCrown` (`resources/effects/fx-v3/paint-splash-crown.png`): "a thick liquid paint splash seen from the front: a fat drop hits and spreads into a round crown with rounded blobby tips, the crown opens, droplets fly off, then it settles into a flat puddle; thick glossy liquid."
- `paintDrips` (`paint-drips.png`): "three rounded paint drips starting as a bulge at the top and running down with round swelling ends, growing longer frame by frame."
- `paintDroplet` (`paint-droplets.png`): "single round paint droplets of different sizes, each with a small bright highlight."
- `paintGloss` (`paint-sheet-gloss.png`, a single 1024 x 1024, NOT a flipbook): "a soft glossy wet-paint sheen: a wide diagonal bright highlight band with feathered edges and two small round specular dots."
- **Good looks like:** thick, bubbly liquid, never thin or splatter-gory.

### 3D briefs (Roblox Studio `generate_mesh`, owner account; or Blender export)
- **Slot `hatch_bucket`: paint bucket mesh.** "a chunky cute cartoon paint bucket, slightly wider at the top, thick rolled rim, a round wire handle standing straight up, simple matte painted-metal look with one wooden band, open top, the inside filled with a flat smooth paint surface in pure white, soft rounded low-poly shapes, no text, no logo". About 1.35 studs tall. Good: matte, chunky, white paint surface.
- **Slot `golden_drumstick_mesh` (+ `golden_drumstick_icon`, ICON block "a plump cartoon drumstick with a bone end"): food mesh.** "a plump cartoon roast drumstick, golden brown, chunky rounded low-poly, matte, one small bone end, friendly". Under 500 triangles; the gold glow is added in game.
- **Slot `shock_dome_mesh` (anime FX P0), `shaft_cone_mesh`, `aura_shell_mesh` (P1)** are Blender FBX jobs for Claude via Blender MCP, no owner prompt needed: dome about 120 tris, cone about 80, shell about 150 ([123](123-anime-3d-fx-research-and-plan.md) section 3). Textures `domeGradient` (512 white on alpha soft radial), `speedStreaks` (512 x 512, four soft white streaks), `rainbowStrip` (1024 x 64 grey ramp), `rimRingUi` (1024 ring, white on alpha) use STYLE + FX block.
- **Cave gate arch (`cave_hub_hub_gate_arch`, id 90142774443313 exists but reads as a near-square niche, not a proper arch).** Optional re-generate: "Low-poly worn stone archway, tall rounded top, thick chunky stones with moss on top, cave entrance, matte, warm cream stone with a few amber crystal accents, friendly and cosy", 30 x 20 x 6 studs. Good: clearly an arch from far away, open in the middle, sits on the floor. Send back as `gate_arch_new = <mesh id>` (the lead binds it in `CaveHubProps`).
- **Slot `lavaCrust`: lava crust texture** (Blender render or ChatGPT; no code-drawn art). `resources/effects/cave-lava-crust-v1.png`, 1024 x 1024 TILEABLE, opaque or soft alpha edge. Prompt: STYLE + "a seamless tileable cartoon lava flow texture, glowing warm orange (#FF8C46) cracks between dark charcoal-brown crust plates, rounded soft shapes, calm and cosy, no sharp spikes, no scary red, tileable on all four edges".
  Good: no visible tile grid, warm (amber not hot red), calm.
- **Cave props (optional, `TODO_cave_den_rest_props`, `TODO_cave_showoff_pedestal_art`):** generate_mesh "a cosy low-poly den rest area: a round woven nest bed with a leafy blanket, matte" and "a round low-poly stone show-off plinth with a shallow dish top, warm cream stone, matte". Name them `cave_den_rest` and `cave_showoff_plinth` when you send ids.

---

## BATCH 8. Priority 2

- **Combat HUD (BD-248).** Slots `hud_heart`, `hud_class_1`, `hud_class_2`, `hud_class_3`, `hud_bite`, `hud_hit_bubble` (files `resources/ui/v2/icons/hud-*-v1.png`, 1024 RGBA; bite 512 x 256). STYLE + ICON block + "a chubby friendly pink-red heart" / three round badges "a dinosaur footprint", "a claw", "a shield" (reuse the class icons if you prefer) / "a chunky round bite button with a friendly dino mouth outline, no teeth, calm teal-orange (not alarm red)" / "a soft white speech bubble with a small star".
- **Crystal packs (BD-331).** Slots `crystals_s`, `crystals_m`, `crystals_l`, `crystals_xl` (`crystals-<s|m|l|xl>-v1.png`). STYLE + ICON block + "a pile of faceted AMBER / golden-yellow gems in a [small cloth pouch / bigger cloth bag / wooden chest / golden vault], more gems for bigger packs". Good: AMBER, never blue (handbook 5.3). Does not enable Robux packs.
- **Station medallions and Fame plaque (docs/104).** Slots `station_nests`, `station_potions`, `station_fusion`, `station_style`, `station_index`, `station_settings`, `fame_plaque`. STYLE + ICON block + "a round carved-stone sign medallion showing [an egg nest / a potion bottle / two merging dino eggs / a paint brush / an open book with a dino / a gear] in warm cream and moss green"; plaque: "a wide carved stone plaque with a small trophy and star, no text".
- **Anime FX P1/P2:** see the table in Batch 5 and the 3D line in Batch 7.

---

## 7. Sounds: Roblox Creator Store audio search words (free sounds)

**How:** Creator Hub > Creator Store > **Audio** (or Studio Toolbox > Audio), filter **Free** and Sound Effects (or Music for loops), listen, and pick ones that match the words. Check the length, avoid anything with a sharp start, hiss or siren (handbook 7: soft, round, bubbly; marimba, kalimba, glass bubble, soft pop; nothing harsh above about 8 kHz). Upload or copy to your account if the Store requires it, then send `slot = id`. Agents cannot hear: you are the judge ("unheard" until you listen). Slot names are the `bind_assets.py` names from [120](120-pending-owner-uploads-checklist.md) section 6. Pick 2-3 candidates for the reveal stings and let the lab (Settings > SOUND > SOUND LAB) tell you by ear.

| Slot | Length | Search for | Good sounds like |
|---|---|---|---|
| `sfx_hatch_reveal_common` | about 0.7 s | "soft pop chime", "marimba note short", "bubble pop cute" | one friendly warm note |
| `sfx_hatch_reveal_uncommon` | about 0.8 s | "kalimba two notes", "magic chime small" | a small happy two-note rise |
| `sfx_hatch_reveal_rare` | about 1.5 s | "harp glissando short", "sparkle chime rising" | a sparkly rise that settles |
| `sfx_hatch_reveal_epic` | about 2.4 s | "magical reveal bells", "fantasy chime swell" | richer bells and a gentle swell |
| `sfx_hatch_reveal_legendary` | about 2.5 s | "magical fanfare soft", "choir pad sparkle", "treasure discover" | warm, big, soft timbre; richer, not just louder |
| `sfx_rare_hatch_fanfare` | 2-3 s | "kids celebration jingle", "happy win fanfare soft", "confetti pop cheer" | huge joyful swell with bells and sparkle tail, no brass blast |
| `sfx_hatch_burst` | 0.3-0.5 s | "egg crack pop soft", "bubble burst cute" | a round pop with a tiny sparkle |
| `sfx_hatch_rattle` | 0.4-0.6 s | "wobble rattle cute", "egg shake soft", "wooden shaker short" | a gentle wobble, not a bang |
| `sfx_cracked_fail` | 0.5-1 s | "cartoon bonk soft", "sad trombone cute short" is too sad: try "boing soft wobble" | gentle and funny, never sad or harsh |
| `sfx_shiny_bang` | about 1 s | "sparkle shimmer magic", "glitter chime" | bright glittery shimmer |
| `sfx_big_thud` | about 0.6 s | "cartoon soft thump", "bouncy boing heavy" | a friendly big bounce, not a crash |
| `sfx_mutation_dewdrop_reveal` | 0.5-1.2 s | "water drop plink", "bubble plip magic" | watery plink |
| `sfx_mutation_charged_reveal` | 0.5-1.2 s | "cute zap soft", "electric chime short" | soft zap with a chime tail |
| `sfx_mutation_frost_reveal` | 0.5-1.2 s | "ice tinkle", "glass chimes small" | cold bright tinkle |
| `sfx_mutation_seismic_reveal` | 0.5-1.2 s | "soft low thump rumble short", "stone tap cute" | low gentle thump |
| `sfx_mutation_ember_reveal` | 0.5-1.2 s | "warm crackle soft", "fire crackle small" | warm crackle, no roar |
| `sfx_mutation_aurora_reveal` | 0.5-1.2 s | "shimmer pad magic", "ethereal sparkle swell" | airy shimmer |
| `sfx_mutation_bloodmoon_reveal` | 0.5-1.2 s | "deep soft bell", "low gong gentle" | deep, soft, not spooky |
| `sfx_crystal_cue` | 0.3-0.6 s | "gem collect chime", "coin sparkle soft" | bright amber-gem tink |
| `sfx_nest_open_cue` | 0.5-0.8 s | "wooden chest open cute", "soft reward swell" | a warm open, small sparkle |
| `sfx_pickup` (3 variants) | 80-150 ms | "leaf pop", "bubble pop short", "soft blip cute" | tiny bubbly pop, quiet |
| `sfx_ui_click` (3 variants) | 50-150 ms | "wood tick soft", "ui tap cute", "bubble click" | dry friendly tick |
| `sfx_defeat_soft` | 0.5-1 s | "cartoon soft bonk", "aww cute descending" | gentle and funny, not sad |
| `cave_bed` | loop 20-40 s | "cave ambience calm", "dripping water cave soft", "warm hum ambience" (Music or SFX, filter Loop) | soft drips, a warm distant hum, faint crackle, NO wind or weather |
| `weather_rain_bed` | loop 20-40 s | "gentle rain loop", "soft rain ambience" | soft steady rain, no thunder |
| `weather_thunder_bed` | loop | "distant storm ambience soft rain" | rain with a faint far rumble |
| `weather_thunder_roll` | 1-2.5 s | "distant thunder roll soft" | far, rounded rumble |
| `weather_thunder_strike` | 0.8-1.5 s | "thunder clap soft distant" | a soft clap, never a sharp crack |
| `weather_blizzard_bed` | loop | "soft snow wind loop", "gentle winter wind" | breathy soft wind, no howl |
| `weather_volcano_bed` | loop | "low rumble ambience soft", "lava bubbling gentle" | deep warm bubbling, calm |
| `weather_volcano_boom` | 1-2 s | "soft distant boom", "low thump explosion small" | a rounded boom, not a blast |
| `weather_quake_bed` | loop | "earth rumble low soft" | steady low rumble |
| `weather_quake_burst` | 0.8-1.5 s | "rocks tumble soft", "stone crumble short" | soft rubble, no crash |
| `weather_bloodmoon_bed` | loop | "night ambience crickets soft", "mysterious pad calm" | calm night hum, kid-safe |
| `weather_aurora_bed` | loop | "magical ambient pad shimmer", "ethereal drone soft" | glowing airy pad |

Tips: a sound that is too loud is fine (the game turns volumes down), a sound with a sharp start or hiss is not. For loops pick ones the Store marks as looping, or ones you can hear start and end smoothly. Reveal stings and fanfare: send 2-3 candidate ids per slot if unsure, the lead wires them as A/B/C in the Sound Lab.

## 8. After you send ids

The lead adds the [77](77-asset-registry.md) lines, runs `python tools/bind_assets.py ids.txt`, then `python tools/build.py`, `python tools/verify_asset_slots.py`, `python tools/verify_release.py`, and checks each in Studio on desktop and phone next to neighbouring UI ([120](120-pending-owner-uploads-checklist.md) section 5; [109](109-owner-art-prompt-pack.md) section 7). Rows then move to Review / test in the Kanban; nothing is claimed accepted without a screenshot.
