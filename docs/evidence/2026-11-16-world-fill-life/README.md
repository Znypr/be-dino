# BD-1244 life on the island + BD-1247 warmer light (2026-11-16)

Owner 2026-11-16, spawn screenshot: "game still looks empty", then "Yes, build all" (rows BD-1244 and BD-1247, PR #621).

## Critters (Roblox Studio `generate_mesh`, published to the owner's account, docs/77)
| key | Model id | what |
|---|---|---|
| life_butterfly_orange | 119423844496923 | toy butterfly, orange and yellow wings with cream spots (300 tris cap) |
| life_butterfly_blue | 92211125946330 | toy butterfly, sky blue and pink wings with white spots (300 tris cap) |
| life_dragonfly | 90347036204952 | toy dragonfly, teal body, pale blue wings (300 tris cap) |
| life_gull | 102465106637124 | toy seagull gliding, white and grey (400 tris cap) |

`critters-lineup-studio.jpg`: the four in Studio. The baby dinos are the existing V3 low-poly dinos (herbivores only) at 0.55 size.

## In game (playtest profile, my own Studio window build/BeDino-life-test.rbxlx, Studio PC, not a phone)
- `before-*.jpg`: main 2aa58810. `after-*.jpg`: this branch. Same cameras: `*-spawn` = from spawn down the main path toward the giant tree (the owner's view); `*-zone-<meadow|forest|pine|beach|volcano>` = on each zone's spoke path 105 studs out, looking outward.
- `close-butterflies.jpg`, `close-dragonfly.jpg`: the critters in game (butterflies tipped into a V so they read from the low camera).
- Babies are posed with the BD-1217 clips (eat while grazing, look-around, walk / idle cycles, a happy hop when a player walks up): measured, not watched (head joint angles change between eat and look in Studio).
- Weather: with WeatherId = rain the grade, bloom, rays, motes, butterflies and dragonflies go to 0; back to clear they return over about 3 s (Studio numbers).

## Numbers
| | before (main) | after |
|---|---|---|
| client parts within 300 studs of spawn (XZ) | 4,643 | about 4,730 (4,714-4,763 as life moves); 4,593 after merging #623 (BD-1245/1246 dropped ground cover) |
| life parts alive (desktop caps: 8 babies, 4 flocks of 4, 3 dragonflies, 3 gulls) | 0 | 67-84 measured, 94 max |
| life parts on a phone (caps 4 / 2x3 / 2 / 2) | 0 | 46 max (offline, tools/verify_island_life.py) |
| ParticleEmitters with Rate > 0 | 18 | 19 |
| live particles (Rate x mean lifetime, all emitters) | about 239 | about 339 (motes +100 desktop; phone +50, tablet +75) |

Still above the docs/107 phone rule of thumb (about 3,000 parts in range, BD-1222); this adds about 2%. No phone check yet.

## Lead review 2026-11-16 (before the PR)
- Spawn view: three babies (triceratops, stegosaurus, parasaurolophus at 0.7 size) 40-48 studs from spawn either side of the main path, and the two plaza butterfly flocks 1.5x bigger, 16-22 studs from spawn: all in the spawn frame (`after-spawn.jpg`, Studio screen positions checked).
- NESTS and POTIONS showed twice (a word on the stone sign plus a floating word, already on main): fixed by #625 (BD-1248 plaza shops v2, one signboard per shop), so this PR leaves the plaza signs alone.
