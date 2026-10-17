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

---

# v2 (2026-10-17, owner feedback: "the current model doesn't look right")

Owner references (all in [docs/reference](../../reference/)): [front](../../reference/budgie-owner-ref-1-front.png), [pale blue variety](../../reference/budgie-owner-ref-2-pale-blue.png), [side on a branch](../../reference/budgie-owner-ref-3-branch.png), and the [owner screenshot of v1](../../reference/budgiesaurus-v1-owner-screenshot.png). What was wrong with v1: chunky blob body, huge cream head, cheek patch as floating blue squares, orange beak, no long tail, rough wing patch, no throat spots.

Setup: Place 1 (Studio id c2e44870...), generate_mesh, text only, `segmentation=explicit` with the same 7 part names, `size` about 4 x 8 x 9, run async. Three candidates were generated into a temporary staging folder "Budgie candidates" (now deleted). Prompts are also in [prompts-v2.txt](prompts-v2.txt). Note: the first version of prompt A (about 540 characters) failed with "Character limit exceeded"; keep prompts under about 490 characters.

## Candidates (all faced -Z or +Z at random; the winner was turned 180 degrees)
| | Prompt idea | Picture | Largest visible difference versus the references |
| --- | --- | --- | --- |
| A | slim and tall, very long tail | [side](v2-candidate-A-side.jpg), [front](v2-candidate-A-front.jpg) | Side view is the most bird-like, but from the front the eyes stick out as black bars either side of a duck-like orange beak, the legs are pink, and the throat has one lilac spot, not three black ones. |
| B | slightly chunkier, friendlier | [side](v2-candidate-B-side.jpg) | Boxy rounded-rectangle body with a hexagonal disc for a wing and tiny feet; the long tail is there but the body reads as a block, not a bird. |
| C | perched, leaning forward | [front](v2-candidate-C-front.jpg), [side](v2-candidate-C-side.jpg) | Best proportions and grey-blue legs, but the wing is a glitchy yellow-black blob, the beak is orange, and the cheek patch is two blue squares. |
| C2 | C with "pale grey horn-coloured beak, not orange" | [front](v2-candidate-C2-front.jpg), [side](v2-candidate-C2-side.jpg) | The beak is still orange-peach (negation did not work), but the wing now shows yellow-black scallops, the cheek patch is a lilac streak and two black throat dots show. WINNER. |

All three candidates side by side: [v2-candidates-ABC-front.jpg](v2-candidates-ABC-front.jpg).

## Winner (C2), now at `Workspace > Silly secret dinos v3 > Budgiesaurus`
- Asset id `107910518074360` (v1 `111728956844490` model deleted). x=55.2, z=150, bottom on the baseplate (minY 0.000), 6-stud gap to the Dodo, faces -Z like the others; the Foxosaurus at x=65.5 was left untouched.
- 7 parts, each a Model holding one `<name>_geom` MeshPart: `body`, `head`, `left wing`, `right wing`, `left leg`, `right leg`, `tail feathers`. The generator returned clean names this time (the script cleaning was still run: nothing to remove).
- Pictures: [front](v2-front.jpg), [side](v2-side.jpg), [three-quarter](v2-three-quarter.jpg). Side by side with the reference photos: [front vs reference 1](v2-vs-reference-front.jpg), [side vs reference 3](v2-vs-reference-side.jpg).

## Rating: 6 of 10 against the references
It now reads as a budgie (slim upright body, yellow face, blue cere, lilac cheek patch, black throat dots, scalloped wing, grey-blue legs, long barred tail) instead of a blob, in the same flat-faceted style as the other secret birds.

Largest remaining differences:
1. Beak is orange-peach, not grey-yellow (the generator ignored the negative wording; "pale grey horn-coloured" alone was not enough). Untried fix: leave the beak colour out of the prompt, or recolour the beak texture by hand.
2. The face is a flat cream mask; the references have a bright yellow face and a finely barred crown and nape. The head is green behind the mask.
3. The tail is shorter than the body (about 60 percent), the references have a tail as long as the body.
4. Only two of the three throat dots show clearly; the cheek patch is a thin lilac streak, not the small blue-violet patch of the references.
5. The wing coverts are a coarse black-and-yellow patch plus a dark blue block, not fine scallops.

Texture control (cheek patch and throat dots): both do show, so the generator can paint them as texture, just weakly and not where a real budgie has them. No separate geometry was added; nothing in the winner floats off the mesh. The cheek patch changed from squares (C) to a streak (C2) between generations, so the result is stochastic; a regeneration with the same prompt may look different.

Camera: Place 1 ended on `CameraType = Custom` (checked after the last call, `shared.__camConn` hook still armed). The Studio window was brought to the owner's third screen topmost for captures, then released.
