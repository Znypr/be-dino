# Budgiesaurus (parakeet) test model, Place 1, 2026-10-17

Owner request 2026-10-17: "add a parakeet bird as another new special dino to the place1". Reference picture: [parakeet-budgie.png](../../reference/parakeet-budgie.png). Kanban row BD-600, in the BD-228 secret-bird family. Species name chosen: **Budgiesaurus** (kid-friendly, same pattern as Chickosaurus).

## What was generated
- Tool: Roblox Studio MCP `generate_mesh` (text prompt only; the tool has no image input, so the picture was described in words). Published asset id `111728956844490`.
- Prompt: `budgerigar parakeet, plump round body, bright green body and belly, yellow head, black-and-yellow scalloped wing feathers, blue cheek patch, small black dots on yellow throat, small blue beak, pink-grey feet, long pointed blue-green tail, clean low-poly, few large flat facets, solid glossy black eyes with white highlight dot, not hollow, matte pastel, kids game, side pose`
- Settings: `segmentation=explicit`, size 4 x 7.7 x 7, no triangle cap. The first call timed out at the MCP layer; the second was run async and completed (the PC is slow). Only one model was left in the place.
- Location: `Workspace > Silly secret dinos v3 > Budgiesaurus` (the existing secret-bird row at z=150, after Chickosaurus, Pigeon, Dodo, Duck, Penguin). Centre x=55.15, 6-stud gap after Dodo, minimum Y = 0.000 (on the baseplate surface). The row's existing cream sign "SILLY SECRET DINOS v3" (x=-14, folder "Design signs") covers it, so no new sign was added. Facing -Z like the others.

## Part names (same shape as the split Chickosaurus: each part is a Model with one `<name>_geom` MeshPart)
`body`, `head`, `left wing`, `right wing`, `left leg`, `right leg`, `tail feathers` (7 parts, all unanchored like the other dinos). The generator split the mesh itself, so no segment_mesh step was needed. Note: the generator returned the part names with stray quote/bracket/backslash characters (the JSON-array `partNames` was taken literally); they were cleaned by script to the names above.

## Pictures
- [parakeet-front.jpg](parakeet-front.jpg): front, yellow head, blue cheek patches and nose, black solid eyes, green belly, pink legs.
- [parakeet-side.jpg](parakeet-side.jpg): side/back three-quarter, green back, black-and-yellow wing patch, blue tail feathers.

## Look versus the reference (honest notes)
Good: green body, yellow head, solid black eyes, flat facets, chunky friendly shape, tail with blue tips. Weaker: the beak texture came out orange (reference: blue); the cheek patch reads as small blue squares; the black throat dots are not clearly visible; the wing is one flat patch with a rough black-and-yellow scallop pattern; the feet are more salmon than pink-grey; the head part is a small separate mesh. A second generation or a texture touch-up could improve it; not done (each generation takes minutes on the owner's PC).

## NOT done
No game integration: no `LowPolyDinoAssets` entry, no species config, no Index entry, no drop method, no rarity tier, no class (fly), no animation tuning (the part names are only meant to let the procedural animation find them later), no Studio playtest. Open questions for the owner are in the BD-600 row.
