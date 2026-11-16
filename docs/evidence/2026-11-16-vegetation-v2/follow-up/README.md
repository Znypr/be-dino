# BD-1239 follow-up: berry size and bush walls (lead review of the #619 pictures, 2026-11-16)

1. The blue and purple bushes had berries bigger than the food pickups, so they read as blue blobs.
2. The berry bushes formed solid walls along the paths and round the plaza.

## Fix
- The three berry bushes are regenerated with small berries (Roblox `generate_mesh`): red 77978853272967, blue 99690382623326, grape 139210058341686 (docs/77). A blue bush with a stem (129160076759236) was rejected. `berry-bushes-old-front-new-back-with-food-berry.jpg`: front row = #619 bushes, back row = new, with a real blueberry pickup between them.
- `VegetationV2.BushRule` (BiomePlacement.BushV2 while VegetationV2Enabled): round bushes are 3-5.5 kit studs tall instead of the 4-12 stud band, and the dome shows at 80% height. Of the shrub-layer bush picks, 75% stay bushes, 15% become a flower or grass clump and 10% are open ground. Ground cover keeps 50%.
- The food map of that island is its own: `FoodLayerDataV3HostsVeg2` (`tools/food_hosts.py --veg2`, checked by `verify_food_hosts.py --veg2`). It keeps the same 3,600 foods, the same count of every kind in every zone and the same starter patches. 75% of the berries sit at a bush (target 75%; 82% on the #619 island), and the v2 reach for a berry to its bush is 36 studs instead of 30.

## Numbers (Studio PC, playtest build, not a phone)
| | main 49b97faf (#619) | this branch |
|---|---|---|
| client parts within 300 studs of spawn | 4,680 | 4,647 |
| WorldKit parts | 2,076 | 2,065 |
| round bushes (shrub layer) | 561 | 503 |
| ground cover in game | 770 | 808 |

Same camera for `before-*` (main) and `after-*` (this branch): spawn looking at the plaza, then one view per zone.
