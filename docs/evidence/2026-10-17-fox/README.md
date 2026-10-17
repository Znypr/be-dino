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

---

# v2 (2026-10-17, owner request: "turn the fox model we have in place1, into this one")

Reference: [reference/foxosaurus-v2-owner-ref.webp](../../reference/foxosaurus-v2-owner-ref.webp): a blue fox-dinosaur hybrid in a theropod stance on two legs, small raised arms, shaggy light-blue hair, two big ears with dark-blue tips and white insides, two small horns, long white muzzle, sleepy half-lidded eyes, white chest ruff and belly, dark-blue triangle stripes, dark-blue spine and tail spikes, bushy white-tipped tail, white toes with dark-blue claws. No glasses, no beanie. The name stays Foxosaurus. v1 above (glasses and beanie) is replaced.

Setup: Place 1 (Studio id c2e44870...), `generate_mesh` (text only), `segmentation=explicit`, 8 parts (the tool maximum): `body, head, hair, left ear, right ear, left leg, right leg, tail` (no separate arms, so the small arms are part of the body). Run async; each prompt is under 490 characters. Candidates were generated into a staging folder "Fox v2 candidates" (z about 172 to 198, now deleted).

## Candidates
| | Prompt idea | Pictures | Asset id | Largest visible difference versus the reference |
| --- | --- | --- | --- | --- |
| A | closest to the picture: theropod stance, long white muzzle, shaggy hair | [front](v2-candidate-A-front.jpg), [side](v2-candidate-A-side.jpg) | 75143643041822 | Colours: back, tail and legs came out near-navy instead of light blue with dark stripes (the stripes are lost in the dark), and the pose is a slim upright standing fox with arms hanging, not a theropod. |
| B | chunkier, friendlier, big round head | [front](v2-candidate-B-front.jpg), [side](v2-candidate-B-side.jpg) | 129519111611608 | The head is a blank round blue ball with a small mouth: no eyes, no muzzle, no hair; the ears are a flat slab from the side. Cute, but not this character. |
| C | more upright and simpler | [front](v2-candidate-C-front.jpg), [side](v2-candidate-C-side.jpg) | 112996440434481 | WINNER. Reads as the fox-dino: sleepy black half-lid eyes, white muzzle, ears with dark tips and white insides, white chest and belly, dark triangle stripes and spine spikes, white-tipped tail, white toes with dark claws. The biggest gap is no shaggy hair mass (only a small tuft). |
| C2 | C with "big fluffy shaggy hair mane covering forehead and cheeks" (one change) | [3/4](v2-candidate-C2-threequarter.jpg) | 88702223860559 | Rejected. The hair became a square block on the head, the pose turned chibi (no theropod lean) and the horns vanished; C is closer to the picture. |

All three side by side: [v2-candidates-ABC-front.jpg](v2-candidates-ABC-front.jpg) (taken before the candidates were spread apart; left to right A, B, C).

Prompts (exactly as sent):
- A: `blue fox-dinosaur hybrid, theropod stance on two legs, small front arms raised, big pointed fox ears with dark-blue tips and white insides, fluffy light-blue shaggy hair over forehead, two small blue horns, long white muzzle with small nose, sleepy half-closed eyes with black lids, white fluffy chest ruff and belly, light-blue body with dark-blue triangle stripes, dark-blue spikes along spine and tail, bushy blue tail with white tip, white toes with dark-blue claws, low poly, faceted` (size 6 x 9 x 9)
- B: `cute chunky blue fox dinosaur, big round head, standing on two thick legs, tiny arms raised, huge triangular ears with dark-blue tips and white insides, big shaggy light-blue hair tuft, two tiny blue horns, short white muzzle, small nose, sleepy half-closed eyes solid black, fluffy white chest and belly, light-blue body with dark-blue triangle stripes, dark-blue spine spikes, fat bushy tail with white tip, white toes with dark claws, low poly, flat-shaded big facets, matte, kids game` (size 6 x 8 x 8)
- C (winner): `simple friendly blue fox dinosaur standing upright on two legs, small raised arms, tall pointed ears with dark-blue tips and white insides, light-blue hair tuft on forehead, two small blue horns, white snout, small dark nose, sleepy half-closed black eyes, white chest ruff and belly, light-blue body with a few dark-blue triangle stripes, dark-blue spikes along back and tail, bushy blue tail with white tip, white toes dark-blue claws, low poly, few flat facets, matte` (size 5 x 9 x 8)
- C2: C with the hair clause replaced by `big fluffy shaggy light-blue hair mane covering forehead and cheeks`, and `flat facets` at the end.

## Winner (C), now at `Workspace > Silly secret dinos v3 > Foxosaurus`
- Asset id `112996440434481` (candidate C, published by the generator). Part meshes (fallback if Place 1 is lost): body 140224882951722, head 121501467451319, hair 70401230262509, left ear 93176586443959, right ear 78485891946918, left leg 121540493748395, right leg 90686375947030, tail 124051111330462.
- Position: centre x=65.12, z=150, minimum x = 63.2 (a 6-stud edge gap after Budgiesaurus, whose right edge is x=57.2), bottom on the baseplate (minY 0), turned 180 degrees so it faces -Z like the others. Size 3.8 x 8.4 x 8.0 studs. The v1 fox, A, B, C2 and the staging folder were deleted; Budgiesaurus and the birds were not touched.
- 8 parts, each a Model holding one `<name>_geom` MeshPart, all unanchored like the other split dinos. The generator returned clean names (the stray-character cleaning script was run, nothing to remove).
- Pictures: [front](v2-front.jpg), [side](v2-side.jpg), [three-quarter](v2-three-quarter.jpg); next to the reference: [front](v2-vs-reference-front.jpg), [side](v2-vs-reference-side.jpg), [three-quarter](v2-vs-reference-threequarter.jpg).

## Rating: 5 of 10 against the reference
It is clearly the same character idea (blue fox-dinosaur, big dark-tipped ears, sleepy lids, white muzzle and chest, stripes, spikes, white-tipped tail) in the flat-faceted v3 style, and it fits the other secret dinos. The picture's soft, shaggy fur and the crouching theropod pose are what the generator did not deliver.

Largest remaining differences (the generator cannot draw these; nothing was faked with extra geometry):
1. No shaggy hair: the picture's big light-blue hair mass over the forehead and cheeks is only a small tuft. Asking for a mane (C2) produced a square hair block, so the generator cannot do shaggy hair strands.
2. The pose is upright with arms hanging; the picture leans forward in a theropod crouch with the arms raised and bent, and a long horizontal tail. Here the tail curls up behind.
3. The horns are two small dark-blue bumps, barely readable from the front; the picture has two clear pale-blue horns beside the hair.
4. The stripes are small dark patches on the back and legs, not large triangle stripes; the spine spikes are a short row, the picture's tail spikes are bigger.
5. The ears are tall, narrow and flat-sided (a slab from the side), not the broad cupped ears of the picture; the eyes are black bars with no blue iris.
6. The body and neck are slim and the head small; the picture is chunkier with a large head.
7. No fluffy ruff texture (flat white chest only), no fur at all (flat facets, per the v3 style).

Texture control: the dark-blue ear tips, white ear insides, white muzzle, white tail tip and dark claws did come out as painted texture on the right parts, so the generator can place colour areas (stripes only roughly) but not fine detail.

Camera: Place 1 ended on `CameraType = Custom` (`shared.__camConn` armed). The Studio window was restored by the lead (an earlier task had minimised it); this task never touched the window.

UNSAVED in Place 1: the owner must press Ctrl+S in the Place1.rbxl window.
