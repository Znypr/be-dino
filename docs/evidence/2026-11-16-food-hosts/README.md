# BD-1238 food at matching hosts (docs/241 W6 + W7), Studio 2026-11-16

Own playtest build of this branch (not the owner's Place1), Play mode, server side. "before" = the same build with `FoodHostsEnabled = false`
patched into the unsaved test copy (the plain V3 food map); "after" = the playtest profile (flag on). Same cameras.

| picture | what it shows |
| --- | --- |
| `bush-02-before.jpg` / `bush-02-after.jpg` | before: blueberries and raspberries scattered on open ground; after: the berries ring the foot of the round bushes |
| `bush-03-after-close.jpg` | close: blueberries round a bush, visible (not hidden in the dome) |
| `bush-01-rim-inside-REJECTED.jpg` | first try, berries at 92% of the bush footprint: the dome hid most of them, so the ring moved 0.9 stud outside the edge |
| `rock-01-before.jpg` / `rock-01-after.jpg` | after: ambers and nested eggs against the rock (a find, W7) |
| `tree-01-before.jpg` / `tree-01-after.jpg` | after: fruit and a nested egg under the crown and at the trunk foot |
| `map-hosts.png` | `tools/verify_food_hosts.py --picture`: bushes light green, tree crowns outlined, rocks grey, food dots by kind |

Numbers (server, Play mode, BaseParts within 300 studs of the plaza centre (0, 30); NPCs move, so a few parts of noise):

| | parts within 300 studs | food parts within 300 studs | FoodCount | relocated / dropped by FoodService |
| --- | --- | --- | --- | --- |
| before (V3 map) | 4,937 | 2,764 | 3,600 | 6 / 0 |
| after (hosts map) | 4,941 | 2,746 | 3,600 | 5 / 0 |

No parts added (the hosts already stand on the island). Host shares from the world geometry: berry 82% (V3 map 26%), fruit 68% (18%),
egg 68% (2%), amber 73% (1%). NOT checked on a phone.
