# Build 015: mountain island and completed resource exports

## User direction, 2026-10-04
Use the selected prehistoric island image as the visual direction. Expand to a large map with mountains, paths, crystals as high-value food, eggs as lower-value food, and jumping. Finish the resource folder so assets can be inspected directly on GitHub. The original primitive kit is no longer accepted as final art.

## Implemented code and delivered artwork
- Arena expands from 180x180 to 520x520 studs. Smooth terrain heightfield has four authored mountain masses and a low central spawn meadow; ramps remain below the configured walk slope along the checked approach routes.
- Rock/tree/fern groves follow terrain elevations, with stone arch, spring/waterfall and low jump stones. Server-owned obstacles block the growing torso.
- 256 food sectors and up to 1,536 small pickups, grouped in local clusters with positions raycast onto actual terrain. Water, steep faces, solid obstacles and spawn clearance are excluded.
- Values: berry +1, fruit +4, spotted egg +15, amber crystal +50. These are tunable private-test values, not validated balance. Food eggs are distinct from persistent earned reward eggs.
- Native desktop/mobile jump enabled, JumpPower 50, walk speed 22. Shared movement validation separates horizontal movement from legitimate jump/fall motion, while rejecting large position jumps.
- Real OBJ/MTL mesh data and icon RGBA data are embedded in generated shared modules. The client attempts EditableMesh/EditableImage creation, using one cached source per asset with shared clones. Server gameplay/collision stays authoritative. This avoids a mandatory manual OBJ import for supported Studio/API sessions.
- Added layered Home, Collection, Egg Nest surfaces and 3D previews. UI controls remain native and editable.
- GitHub resource folder contains 14 transparent PNG/SVG icons, nine reusable panel/button/card/rarity PNG/SVG pairs, transparent logo, design preview sheets, original illustrated background and expanded mountain-island concept. Generated scene art is explicitly not claimed as the actual game rendering.

## Completed checks
- 16 Python packaging/economy/resource regression tests passed.
- Official Luau parser accepted all 28 scripts.
- Actual Luau numeric/data execution passed: terrain bounds over the complete sampled map, meadow spawn, authored mountain approach slopes, legitimate jump/fall motion, rejected horizontal/vertical teleports, geometry/material lookup and all 14 icon pixel-buffer lengths.
- UI preview/asset sheet and both generated scene illustrations inspected.

## Still dependent on Studio
This environment cannot run Roblox Studio or publish assets under the experience owner. Engine physics, EditableMesh vertex-color display/pivot behavior, replication, touch controls, runtime memory/performance and permission settings remain to be played and checked. Permission denial retains fallback art and reports `LocalMeshStatus`; no claim that live checks passed. For published usage, enable Mesh/Image APIs or import/upload permanent assets. The full-resolution background is provided on GitHub, with optional Roblox ID binding; no fake asset ID is assigned.

## Test steps
Open the new generated place; F5; inspect Home's mesh status. Jump and walk around all mountain paths. Collect berry, fruit, egg and crystal food. Verify pickups appear on slopes, obstacle collision and terrain raycast occlusion, including at max growth. Open Dinosaurs and Egg Nest on desktop/mobile; equip, mutate and claim. Run two clients to confirm the same server-owned food can only be claimed once and remote dinosaurs have mesh visuals. Test published permissions and device performance before release.
