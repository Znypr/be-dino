# Build 017: food visibility and preview framing

User observations: no visible food, low-resolution empty egg icons, off-center index dinosaurs, and awkward sanctuary spacing.

## Changes

- Food ground sampling includes Terrain only. Arena objects are checked separately for placement and pickup occlusion.
- Twelve labelled berry/fruit pickups are seeded in two clusters near the island entrance, in addition to the map-wide clusters. Pickup sizes are slightly larger.
- Missing ground rays fall back to the authored height field. Failed decorative resource cloning preserves the visible pickup.
- Food startup reports status, count, fallback count and traceback through Workspace attributes. Studio displays count/status in the HUD.
- Dinosaur viewports clone the actual resource and fit all bounding-box corners to the viewport aspect ratio. No invisible controller roots affect the camera.
- Egg slots render smooth built-in sphere meshes instead of enlarged 32-pixel icons.
- Sanctuary preview spacing is tightened and the partly obscured decorative Home icon is removed. Index ownership text uses correct singular/plural labels.

## Validation and limits

Source parsing, packaging, gameplay mock execution and data/layout execution checks are run locally. The gameplay tests cover normal spawning, missing-ground fallback, failed decorative art, twelve entrance pickups, and the run settlement lifecycle.

The original no-food failure has not been reproduced in Roblox Studio. Build 017 makes startup failures observable and hardens placement; actual physics, food appearance, egg rendering and responsive menu spacing still need Studio acceptance. If food remains absent, record the Studio FOOD label and FoodStartupError attribute or Output traceback.

Open build/BeDino-Build017.rbxlx and confirm BUILD redesign-017 before testing.
