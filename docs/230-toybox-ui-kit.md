# 230 Toybox UI kit and skin (BD-1177), 2026-11-13

Status: **Review / test**. The pictures, the code and the offline tests are done. **Not seen in Studio, not seen on a phone, nobody has looked at the skin in the game.** The picture ids are **not bound yet** (the upload is an open step, section 6), so today the flag changes only the text outline.

Why: [228](228-ui-toybox-proposal.md) board 1 (the kit of the "Toybox" UI proposal). Owner decisions of 2026-11-13 are in [115](115-decisions-log.md): the whole proposal goes into the game behind one switch, the kit art is Blender renders and draft A (rounder, softer) is the pick, the potion stall 3D pieces are a later task.

Labels: everything below is **CURRENT BUILD BEHAVIOR of the playtest profile only**. The default build is unchanged (flag off).

## 1. The switch

`Config.ToyboxUIEnabled`: false in Config and in the default profile, true in the playtest profile, in the rehearsal list. It stays off in the default profile until the owner has seen the skin in Studio. Client presentation only: nothing is stored, sent or decided; no server, save or economy change. With the flag off `src/shared/ToyboxSkin.luau` is never loaded.

## 2. The pictures (Blender renders, no code-drawn art)

Folder `resources/ui/v2/toybox/final/`, source `assets/blender/ui/toybox-kit-v1.blend`. Review pictures: `docs/evidence/review-2026-10-17/575-toybox-kit-drafts-A-B.png` (drafts A and B) and `576-toybox-kit-final-A-set.png` (the final set, draft A). Every picture has a line in [77](77-asset-registry.md) and a slot in `src/shared/AssetSlots.luau` (`toybox_*`, 23 slots).

| Picture | Size | Use | 9-slice centre (measured from the PNG) |
| --- | --- | --- | --- |
| `header-{amber,green,blue,purple,dark,cream,red}.png` | 512x128 | window header strip | x 150..224, y 30..98. The centre is the stripe-free band between the first and second shine stripe, and the strip is scaled to the header height, so no stripe is stretched. Corner 21 px, outline 5 px, drop 11 px |
| `button-{green,grey,gold,blue,red,purple,dark}.png` | 256x112 | every button | x 24..232, y 20..88, drawn at half size (corner 8 px). Corner 16 px, outline 4 px, drop 8 px; the two flat tones stretch as flat colour |
| `close.png` | 128x128 | the X | not sliced: drawn whole, as a square |
| `card-{common,uncommon,rare,epic,legendary,mythic}.png` | 256x320 | rarity cards (**not used yet**, BD-1178) | x 70..108, y 34..92: a stud-free patch, so the studs keep their shape |
| `panel-frame.png` | 256x256 | window frame | x 36..220, y 36..220, at half size (corner 15 px) |
| `studs-tile.png` | 256x256 | window body | tiled, one repeat = 128 px (studs 32 px apart) |

The task text named corners of "about 26 / 20 / 36 px". Measured on the opaque pixels they are 21 / 16 / 30 px; the slice margins above (30 / 20-24 / 36 px) keep every corner out of the stretching centre, and `tools/verify_toybox_ui.py` measures that on the real files.

## 3. What the skin does (flag on, ids bound)

- **Menu window** (Shop, Potions, Eggs, Dino Index, Settings and every other screen of the shared window): stud body inside the dark frame, glossy striped header, a dark 3 px drop under the title, the red gloss X as a square of at least 48 px on screen. The old code-built dots (`Theme.texture`) and the flat panel are hidden.
- **Header colour by place** (owner, docs/228): amber Crystal Shop, green Potions, blue Dinos / Index, purple Fusion, cream Eggs, dark Settings. Red is kept for the X; no place uses the red header. Every screen name has a place in `ToyboxKit.ScreenPlace`; an unknown screen is blue.
- **Fusion Menu** (its own window): same frame and studs, always the purple header, the red gloss X.
- **Buttons** (every button made by `Theme.decorate`, in every menu and on the HUD): the flat colour becomes the nearest of the seven gloss buttons (green, grey, gold, blue, red, purple, dark). The word of the button moves to a label on top of the picture and follows the button's text, size, colour and dimming, so the price-on-button cards of BD-1144 keep their layout (icon and number stay children of the same button).
- **Text**: one outlined style, 3 px outline, 4 px from 28 px text up (today 2 to 3 px). Sizes are unchanged; the docs/72 floors stay (the skin's own labels are never under 14 px).

## 4. Fallback while ids are missing

The pictures are in five groups: headers, buttons, X, window body (frame and studs), cards. A group is used only when **every** id of it is bound; otherwise that part keeps today's look. An id must look like `rbxassetid://123456`; anything else counts as missing. With no id bound (the state of this change) the flag adds no picture and hides nothing; only the text outline is thicker.

## 5. LEAD fill-ins (PROVISIONAL, docs/228 names six places only)

- Sanctuary (`home`) and the welcome page are **blue**; Run Complete, the starter card and the auto-opened eggs summary are **cream** (they are about eggs); "Go home?" and the Food page are **dark** (red stays for the X); the odds pages and purchase confirms of the Crystal Shop are **amber**.
- A colourless button (white, grey, the card colour) is the grey or the dark gloss button, never a colour.
- Text drop: only window titles and button words have it. Every other text has the thicker outline without a drop (a drop needs a second label per text).

## 6. Open steps

1. **Upload the 23 pictures** (owner's account). `python tools/upload_batch.py` now lists them as the group "Toybox UI kit"; after the upload `python tools/bind_assets.py --batch ...` writes the ids into `AssetSlots.Images` and the docs/77 lines. Nothing was uploaded in this change and no id was invented.
2. **Studio pictures** at 516x481 and 1280x720, and a phone check (the Done condition of BD-1177).
3. The screens built on the kit: Crystal Shop BD-1178 (uses the rarity cards), hatch BD-1179, HUD tiles BD-1180, potion window BD-1181.

## 7. Known limits and mismatches

- The dino detail page colours its header by rarity today. Under the skin the header is the blue strip, so that colour cue is gone on this page (C-58 in [116](116-handbook-conflicts.md)).
- The handbook (docs/114 s4.4) and `TextStyle` say "outline 2 to 3 px, never a heavy 4+"; the Toybox proposal the owner approved says 3 to 4 px. The flag decides; the handbook text stays until the owner has seen it (C-57).
- The file names have no `-v1` suffix, unlike the icons in `resources/ui/v2/icons`. The team catalogue lists game content, not UI kit pieces, so it names no folder for these; the lead's folder is kept.
- A button whose word is hidden on purpose (text transparency 1 before it is decorated) would show its word again; no such button was found in `src/client`.
- How 9-slice, tiling, negative ZIndex and UIStroke on labels really render is engine behaviour: the offline mock checks the properties, not the pixels.

## 8. Tests

`python tools/verify_toybox_ui.py --runner <luau.exe>` (in CI): the flag and the hooks; flag off = the same 435 instances, property for property, as the files without the Toybox lines; the kit numbers; the 23 PNGs measured against the slice rects (Pillow); the real `UITheme`, `TextStyle`, `ToyboxSkin`, `AssetSlots` in an engine mock with ids bound, unbound, half bound and malformed; 57 mutants. **Offline only: nothing is drawn.**
