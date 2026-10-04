# Build 014 verification

## Completed automated checks
- Packaging/economy/resource regression: 16 tests passed.
- Official Luau parser: all 20 source scripts parsed without syntax errors.
- Generated OBJ/MTL checks: see `tests/test_resources.py` for geometry/material/bounds checks.
- Full visual source lineup rendered and inspected; transparent icon exports created.

These checks do not establish Studio physics, device performance or published asset permissions.

## Studio checks still required
1. Open the new `.rbxlx` as an unpublished local file. F5 should start a disposable profile without enabling DataStore APIs. A permanent banner says progress is not saved.
2. Open the published private test with APIs disabled. Show a visible load error instead of leaving Roblox's default loading screen indefinitely. Do not spawn with a blank replacement save. Enable API access and confirm the existing collection returns.
3. Walk into every tree trunk and rock type from four directions. The growing torso footprint should stop; foliage and food should not. At max growth, feet remain grounded and wide lanes stay traversable.
4. Visit all 64 food sectors. Food should be small, in local clusters, with common berry +1, fruit +4 and rare amber +12. Each picked item has only one winner. A respawn moves within its original sector; no food should be inside obstacles or the starter clearance.
5. Open Dinosaurs: three 3D preview cards, rarity labels, counts, Equip and Gold controls. Equip switches the actual character. Server-rejected actions must not change inventory.
6. Open Eggs: slots, server countdowns and claim remain functional. Open Home, tutorial and run summary. No menus cover controls permanently.
7. Use phone portrait and landscape emulator, then a real phone. Modal fits the viewport; all interactive controls remain reachable. Check performance with two players and max growth.
8. Follow resources/README.md to import one mesh, then the rest. Confirm `VisualSource` changes to `Imported mesh`, materials survive import, models face the movement direction, and a non-owner tester can see uploaded geometry.

## Known limits
- The screenshot shows newer local features not present in GitHub main. The repository baseline has no separate lobby, events or paid shop. This branch updates the baseline; it does not claim to preserve code never committed there.
- All new mesh files need Studio import/upload. Native menu styling/previews work immediately; uploaded icon artwork uses optional ID bindings.
- Dinosaurs remain rigid until an animation/rigging pass.
- Bounds/geometry/static checks are not a substitute for the live tests above.
