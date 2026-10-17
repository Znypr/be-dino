# BD-490 cave dressing look and luminance (2026-10-17, round 2)

Build: playtest profile (CaveHub on), Play, `screen_capture` with the ScreenGuis hidden for the camera shots (01 is the normal player camera). Luminance: `python tools/qa/luminance.py --place <cave_heart|cave_station> <image> --roi 0 0 1 1` (full frame; these captures have no Studio chrome).

| Image | Place | Mean luminance | Range | Verdict |
| --- | --- | ---: | --- | --- |
| 01-index-station-dressing | cave_heart (player camera, big dino in front of a dark wall) | 0.148 | 0.15 - 0.35 | just BELOW (p5 0.000): a dark close-up, not a lighting change |
| 02-heart-toward-forge-hall | cave_heart | 0.251 | 0.15 - 0.35 | OK |
| 03-heart-toward-shop-side-island-sign | cave_heart | 0.290 | 0.15 - 0.35 | OK |
| 04-heart-second-angle (forge glow + smoke) | cave_heart | 0.264 | 0.15 - 0.35 | OK |
| 05-dinos-station-from-heart | cave_station | 0.177 | 0.15 - 0.35 | OK |

Seen: moss on the lower wall and floor edges, hanging vines on the jambs, red mushroom clusters, amber crystals, ferns, rock groups, stalactites, the forge glow, clear lanes. Counts from the Server: 29 lights (unchanged), 3,746 MeshParts in the arena with 0 empty MeshIds (kit meshes loaded in the playtest build). No red Output lines.

Result: agent part DONE (renders, luminance in range for 4 of 5 frames, meshes load). Left for the owner: the look verdict ("no moss like before, looks bland" was the complaint), the Neon glow tone and a phone view. Row stays Review / test.
