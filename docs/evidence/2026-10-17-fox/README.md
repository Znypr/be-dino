# Foxosaurus (BD-602), Place 1 test model, 2026-10-17

Reference: [reference/fox-secret-dino.png](../../reference/fox-secret-dino.png) (owner request "this fox as a silly secret dino"). Stylised cartoon creature only.

- Model: `Workspace > Silly secret dinos v3 > Foxosaurus` (x=65.5, z=150, row of the secret creatures, after Budgiesaurus; the sign at x=-14 already covers the row). 4.9 x 8.0 x 6.8 studs, sits on the baseplate.
- Tool: `generate_mesh` (text prompt only, no image input), segmentation explicit, size 5 x 8 x 7, asset id 119604460832523 (mesh 95078207920445).
- Prompt: "cute chunky low-poly faceted cartoon fox dinosaur standing on two short legs, flat-shaded big facets, friendly rounded proportions. Light-blue fluffy fur, white face and white belly, two large triangular ears with white insides, round blue glasses, sleepy half-closed eyes drawn as solid black, small black nose, a yellow knit beanie hat with a grey pom-pom on top, a big bushy light-blue tail with a white tip, small stubby arms, calm silly sleepy expression"
- Parts (each a Model holding one `<name>_geom` MeshPart, like the other split dinos): body, head, beanie, left ear, right ear, left leg, right leg, tail. Names came back clean.
- Pictures: `fox-front.jpg`, `fox-side.jpg` (camera view from the +x side, the fox faces +z).

## NOT done
- No game integration: no `LowPolyDinoAssets` entry, species config, Index entry, drop method, rarity tier or class (owner answers on BD-228 open questions needed).
- No separate arms (8-part limit): the stubby arms are part of the body. No glasses part: glasses are on the head mesh.
- The beanie came out pale cream-yellow, the tail tip white is faint; a re-generation is optional.
- Not tested with the walk/idle animation rig.
