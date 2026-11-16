- **R1 cream**: Surfaces are cream panels / plates / chips with an ink outline; no dark navy or slate plates, boxes or loading screens
- **R2 text**: Two text kinds only: dark ink on cream, white with outline on colour or the world; never text on studs
- **R3 buttons**: One green main button per screen, every other button grey, red only for the X
- **R4 rarity**: Rarity colours only on rarity things (cards, rarity words, hatch rays)
- **R5 real art**: Real art only: no code-drawn icons, stand-ins or empty boxes
- **R6 font+copy**: One font and the 28/20/16/14 scale; kid copy (no 36.4000%, no 5m 0s)
- **R7 frame**: Windows: stud frame, glossy header in the place colour, X inside the strip; the hatch is a full stage, not a window
- **R8 fits**: Everything sits inside its screen/window; nothing clipped, floating outside or overlapping

| Surface | Group | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | Now | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Loading screen | start | P | P | - | - | P | P | - | P | P | BD-1214 (ScreensCohesionEnabled, playtest on): warm green, real dino art, cream bar, one font |
| HUD in the world | play | P | P | P | P | P | P | - | P | P | cream plates, no debug lines, LEAP grey, badges on the edge (BD-1213, HudCohesionEnabled, playtest); BD-1237: Codes and Tell us! grey (docs/evidence/2026-11-16-menus-style/after-hud-codes-tellus-grey.jpg) |
| Welcome steps | start | P | P | P | P | P | P | P | P | P | BD-1214: three cream cards, real pictures, ink text, one green button |
| Home (Sanctuary) | home | P | P | P | P | P | P | P | P | P | BD-1214: dino on a cream preview, facts in ink, Explore green, OPEN EGGS grey |
| Eggs screen | home | P | P | P | P | P | P | P | P | P | on the rules (BD-1195) |
| Dino Index list | home | P | P | P | P | P | P | P | P | P | on the rules (BD-1194) |
| Dino detail | home | P | P | P | P | P | P | P | P | P | on the rules (BD-1189) |
| Crystal Shop | shop | P | P | P | P | P | P | P | P | P | on the rules (BD-1178, PR #591); BD-1237: landing tiles cream with ink words and grey OPEN, the Eggs card ink words and a grey Chances (docs/evidence/2026-11-16-menus-style/after-shop-tiles.jpg, after-shop-egg-card.jpg) |
| Potion Shop | shop | P | P | P | P | P | P | P | P | P | on the rules (BD-1205, PR #591) |
| Egg chances | shop | P | P | P | P | P | P | P | P | P | BD-1237 (MenusCohesionEnabled, playtest on): cream panel, kid chances (1 in 4), exact numbers one tap away trimmed (36.4%), grey buttons; Buy egg confirm on cream panels with one green CONFIRM (code path; the egg is Coming soon in this build) |
| Fusion | home | P | P | P | P | P | P | P | P | P | BD-1237: no empty colour bar on an older dino (the card line already says Older dino) |
| Settings | menu | P | P | P | P | - | P | P | P | P | on the rules; BD-1237: Help tab How to play grey beside the one green FOOD GUIDE (docs/evidence/2026-11-16-menus-style/after-settings-help.jpg) |
| Food guide | menu | P | P | P | P | P | P | P | P | P | BD-1237: real V3 food meshes on cream cards, ink names and grow chips; the egg mesh now gets its RotX turn (re-capture BD-1243) |
| Hatch: egg | hatch | F | F | P | - | P | P | F | P | F | window on studs, dark chip |
| Hatch: Common pop | hatch | F | F | P | P | P | P | F | F | F | text on studs, Drag pill outside |
| Hatch: Legendary | hatch | F | F | P | P | P | F | F | F | F | purple banner, other style, pill outside |
| Hatch batch end / Play again | hatch | ? | ? | ? | ? | ? | ? | ? | ? | ? | not captured yet (BD-1199 buttons) |
| Run complete | run end | P | P | P | P | P | P | P | P | P | BD-1214: facts panel + eggs panel, real art, one green button; defeat variant not captured (combat off) |
| Weather title card | play | P | P | - | P | P | P | - | P | P | BD-1237: white word with an ink outline and the weather icon, line in a cream chip, placed clear of the HUD plates and the toast |
| World labels (+3 Crystals, names) | play | P | P | - | P | P | P | - | P | P | +3 Crystals above its amber, one label per close group (BD-1213); dino names/health not judged |
| Toasts / rare-find banner | play | P | P | - | P | P | P | - | P | P | BD-1237: cream toast cards with ink words on the 20/14 scale, the kind colour only on the edge bar; the rare-find banner is white outlined words on the world (R2); the hatch purple banner is the hatch session's |
| Confirm popups (buy, replace) | shop | P | P | P | P | P | P | P | P | P | BD-1237: Go home? and Buy egg / Upgrade on cream panels, one green button, CANCEL grey; Buy / Replace potion and Buy aura were already on cream (BD-1178, BD-1205) |
| Nest open / nest ready | home | P | P | P | P | P | P | - | ? | ? | Eggs ready! chip word was under its icon (fixed in BD-1237, not re-captured); the toast in that picture is now cream; nests with eggs not captured: BD-1243 |
| Defeat | play | ? | ? | ? | ? | ? | ? | ? | ? | ? | not captured: the wild predator never bit in Studio; BD-1240 |
| Phone layout (touch) | play | ? | ? | ? | ? | ? | ? | ? | ? | ? | the MCP cannot switch the device emulator; compact 1274x481 and offline 667x375 checked only; BD-1241 |
| 3D dinos (V3 low-poly) | world | - | - | - | - | P | - | - | - | P | Blender low-poly V3 set in one style (dino-rig session); Parasaurolophus odd BD-1188; fresh Studio check BD-1243 |
| World props (trees, rocks, plants) | world | - | - | - | - | F | - | - | - | F | toon ground and round bushes (BD-1220-1224) fit; rocks and plants still the placeholder kit: BD-206, vegetation v2 queued BD-1239 (PR #615) |
| Food models in the world | world | - | - | - | - | P | - | - | - | P | V3 food meshes from the approved icons (BD-1208), the same meshes the Food guide shows now; hosts BD-1238 (PR #614) |
| Sound and music | feel | ? | ? | ? | ? | ? | ? | ? | ? | ? | needs ears; AudioPolish BD-1218/1219 in; BD-1242 |
| Motion and feedback | feel | ? | ? | ? | ? | ? | ? | ? | ? | ? | needs a screen recording; MotionPresets BD-1182; BD-1242 |
