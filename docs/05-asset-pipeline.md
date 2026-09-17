# Asset, UI and audio production
Goal: coherent original assets that are cheap to revise and work in Roblox. An original procedural dinosaur, arena and basic HUD now exist as movement-test placeholders; art acceptance remains pending.

## Production strategy
Use procedural Roblox parts for the first playable dinosaur/map. Codex can generate the geometry/setup scripts directly.
Then improve silhouettes with simple original low-poly meshes generated through Blender scripts or modeled manually. Reuse a rig only where anatomy supports it.
AI image generation is useful for concept sheets, icons and texture exploration; a rendered dinosaur image is not a ready-to-use rigged 3D model.
Budget is €0. Use procedural Studio assets, free local tools and already available capabilities. Paid AI 3D generation, subscriptions, asset packs and contractors are outside scope. Do not depend on limited free trials.
[Roblox's importer](https://create.roblox.com/docs/studio/importer) is the integration route; verify scale, pivot, orientation and animation in Studio.

## Minimal manifest
| Asset | Quantity | Initial method | Acceptance |
|---|---:|---|---|
| Dinosaur species | 3 | Procedural blockout, then simple original mesh | Distinct silhouette; consistent scale/pivot; readable at small size |
| Mutation | 1 shared material/VFX treatment | Gold palette + restrained particles | Clear without excessive glow |
| Animation set | idle, walk, eat, defeat | Procedural joint motion or shared rig tracks | No sliding/clipping at min/max scale |
| Environment kit | 6-8 pieces | Parts / procedural rocks, plants, nest | Traversable; no collision traps |
| Food | 2 visual types, same initial mechanic | Simple parts/mesh | Visible on floor; cheap to render |
| Egg | 1 model + cracked state | Procedural model | Queue and reveal use same identity |
| Icons | about 8 | Simple original vector/raster | Readable at small size; no text baked into artwork |
| UI | 5 primary surfaces | Native Roblox UI from Luau | Responsive; touch-safe; loading/error/empty states |
| Sound effects | 7 | Original synthesized effects or permitted Creator Store audio | Audible in published test, no clipping |
| Ambience | optional 1 | Licensed or original loop | Quiet; independently muteable |

## Art direction
Cute chunky prehistoric animals, warm stone/leaf/amber palette, clean outlines in UI, readable open ground.
Do not trace Be Fish icons or reproduce its brown panels, exact illustrations or layout.
One concept sheet is enough before blockout. Judge the in-game camera view rather than isolated renders.
Provisional budgets: around 2k triangles per dinosaur, one small texture atlas where feasible, limited transparent effects. These are project targets to profile, not Roblox limits.

## Reproducible pipeline
1. ART defines silhouette, palette, pivot, size and animation needs.
2. Codex generates source script/concept; owner approves a single representative dinosaur.
3. Create model; remove unused geometry and inspect rig/collision.
4. Export/import, verify permissions and record Roblox asset IDs.
5. Test in movement, at largest scale, beside other players and on phone.
6. Save source, generation settings and manifest; replace asset through stable IDs/config.

Manifest fields: logical ID, source path/URL, creator, rights/license evidence, generation method/tool version if relevant, Roblox ID, owner/group, import settings, moderation state, tested build, replacement notes.
Prefer creator-owned uploads under the selected experience owner. Test asset permissions in the actual published private experience.
Strip scripts from imported decorative models and inspect dependencies before use.

## UI approach
Native Frames, text, layout constraints and buttons are easier to maintain than a single AI-generated screenshot.
Codex implements reusable card/modal/button components with shared color/spacing tokens.
Use both text and color for rarity and threat. Allow UI scaling, safe-area margins, scrolling inventory and large touch targets.
Keep gameplay visible and avoid shop clutter during runs. Render icon previews from the actual dinosaur models where possible to prevent art mismatch.
Settings: SFX volume, music/ambience volume, reduced effects; no music is an acceptable first-test choice.

## Audio approach
Start with pickup, growth milestone, eating, defeat, button, egg reveal and mutation effects.
Short original synthesized chimes/pops can be generated programmatically; roars can use permitted source audio after inspection.
Roblox supports Creator Store audio and uploads where the creator has usage rights; imported audio requires appropriate experience permissions: [official audio guidance](https://create.roblox.com/docs/audio/assets).
Test sound in the published test, not only the owner's Studio session. Keep a silent fallback if an optional asset is unavailable.
No scraping audio or models from Be Fish; no paid generation subscription assumed.

## Timebox and fallback
Timebox first dinosaur visual spike to half a working day. If rigging/import stalls, keep the procedural version and focus on feel.
Do not build all three polished models before proving the controller.

## Catalog scaling
First test: three original species and one Gold treatment. Later catalog: many species per rarity, defined through data with stable IDs. Reward UI must handle stacks without rendering one object per copy. Reuse suitable rigs and palette/material treatments, but a recolor alone is a mutation, not a new species.
