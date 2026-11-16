# World look (BD-1220, BD-1223, BD-1224, BD-1221), 2026-11-16

Studio captures of the playtest build (`tools/build.py --profile playtest`), Play mode, desktop viewport 1914 x 793. Agent-made; no phone check.

| File | Shows |
|---|---|
| `sea-01-before-from-above-fog.jpg` | Before BD-1220: the classic distance fog turns the sea into a pale square plate from above (same look as the benchmark `03-map-from-above-haze.jpg`) |
| `sea-02-after-from-above.jpg` | `RealSeaEnabled`: terrain sea to the horizon, island colours clear from 650 studs up |
| `sea-03-after-mid-height.jpg` | Mid height: deep blue open water, turquoise shelf by the beach, no plate edge |
| `sea-04-after-beach-horizon.jpg` | From the beach: the sea meets the sky at the horizon |
| `sea-05-cave-home-intact.jpg` | The cave home after the far sea: the sea blocks under the cave box are written before the cave shell, so the cave overwrites them (an earlier build flooded the cave floor) |
| `ground-00-before-photo-textures.jpg` | Before BD-1223 / BD-1224: photo grass and rock textures next to the toy props, spiky flat fronds |
| `plants-00-before-spiky-fern.jpg` | Before BD-1224: a giant flat-shaded fern frond fills the view next to round glossy trees |
| `ground-01-after-toon-ground.jpg` | `ToonWorldEnabled`: flat toon grass, earth path and grey-violet volcano rock, round bushes (same camera as `ground-00`) |
| `ground-02-after-forest-round-bushes.jpg` | Broadleaf forest: round glossy bushes where the ferns and horsetail were; small grass tufts remain |
| `ground-03-after-mid-height.jpg` | The island from mid height with the toon ground and the real sea |
| `ground-04-cave-home-grass-follow-up.jpg` | Known follow-up: the overrides are global, so the cave home's grass patches turn flat toon green while its cobblestone floor stays photo |

Counts (Play, playtest profile, desktop): BaseParts 6776 before BD-1224, 6811 after (+35, round bushes carry colliders); shrubs 573 (231 bushes,
238 ferns, 104 horsetail) -> 561 bushes. BD-1220: the 6000-stud `Ocean` part is gone (-1); the far sea is 456 terrain blocks written in about
4.5-6 s in the background after IslandTerrainReady.
| `plaza-01-hub-overview.jpg` | `PlazaHubEnabled`: NESTS, POTIONS, SHOP and DINOS stalls with big signs on the spawn plaza, between the spoke paths |
| `plaza-02-potions-stall-dino.jpg` | The dino walked up to the POTIONS stall (prompt anchor in front of the counter) |
| `plaza-03-nests-stall.jpg` | NESTS: nest ledge and the sign board |
| `plaza-04-shop-stall-first-size.jpg` | SHOP (counter, gem chest, crystal) at the first size; the stalls were then scaled about 1.4x |

BD-1221: 12 meshes, 4 hidden colliders, 4 hidden prompt anchors. The walk-up press itself could NOT be driven in this Studio session: no
ProximityPrompt showed there at all (also a plain test prompt), so the opening path is checked by `verify_world_look` and code review only.

