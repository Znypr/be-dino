# Cockatoosaurus, generated candidates v2 (BD-621), 2026-10-18

Owner decision 2026-10-18: the cockatoo must be GENERATED (not the script-built Blender study in [../2026-10-18-cockatoo-blender](../2026-10-18-cockatoo-blender/README.md)), and the owner said "the blender shape isnt the same, it should be more dino shapes, like curved natural". So the prompts were rewritten for a soft, rounded, naturally curved dino-bird. Status of everything here: **candidate** (not accepted art, not in the game, not in Place 1).

References: PRIMARY the owner draft [reference/cockatoo-owner-draft.webp](../../reference/cockatoo-owner-draft.webp) (a low crouching run, soft layered feathers, swept-back yellow crest, hooked dark beak, feathered arms with black claws, scaly grey legs with big black claws); the ChatGPT turnaround sheet [reference/cockatoo-turnaround-chatgpt-v1.png](../../reference/cockatoo-turnaround-chatgpt-v1.png) (reference only).

## Setup
- Scratch Studio window `cockatoo-scratch.rbxl` only. Place 1 and `playtest-build.rbxlx` were not touched. The scratch place was NOT saved.
- Tool: `generate_mesh`, text prompt only, `segmentation=explicit`, parts `body, head, crest, left wing, right wing, left leg, right leg, tail`, run async. 11 generations used (cap 11 after the lead raised it): rounds 1 and 2 three each, round 3 two, round 4 three (I, J, K). Every generation came back split into the 8 parts with clean names.
- Models were put in `Workspace > Cockatoo candidates v2` in a row at z = 300 (A x=0, B x=12, C x=24 as asked; D x=36, E x=48, F x=60, G x=72, H x=84 for the later rounds), all turned to face +x, bottom on y=0. For the pictures only one candidate was visible at a time (the others were parked in ServerStorage, then put back). The ground in the pictures is the scratch place terrain edge, so the grey wedge on the left is not part of the model.
- Pictures are `screen_capture` renders (516 x 481): front, side and 3/4 for every candidate, one camera change per picture. Studio lighting comes from behind the front view, so fronts look darker (candidate B and E fronts looked bluish-grey for that reason; the side views show the true cream colour).

## Prompts (exactly as sent, all under 490 characters)
Round 1 (the v2 variants A, B, C rewritten for "curved, natural, dino"):
- A upright raptor, size 5x8x8, asset `139180937591533`: `cute soft rounded cockatoo raptor dinosaur, graceful S-curved neck and back, leaning forward on two strong bent legs, cream-white fluffy feathered body, swept-back crest of long pale yellow feather blades, hooked dark grey beak, big round brown eye, small feathered arms bent forward with curved black claws, scaly grey legs with big black claws, long tail of cream feathers with yellow tips, smooth rounded low-poly, soft natural curves, kids game`
- B chubby, size 5x8x8, asset `116459292468442`: `chubby round friendly cockatoo dino with a soft curved body, plump cream-white feathered belly, curved neck, big head with swept-back pale yellow crest, hooked dark grey beak, big round brown eye, short bent scaly grey legs with big black claws, small feathered arms with curved black claws, rounded tail with yellow-tipped feathers, smooth organic shapes, cute rounded low-poly, kids game`
- C crouching run like the owner draft, size 5x8x8, asset `87731592907541`: `cockatoo dinosaur in a low crouching run, body leaning forward, body and tail forming a smooth horizontal curve, head raised on a curved neck, cream-white fluffy feathers, swept-back pale yellow crest, hooked dark grey beak, big round brown eye, feathered arms raised with curved black claws, bent scaly grey legs with big black claws, long tail with yellow-tipped feathers swept back, soft rounded low-poly, kids game`

Round 2 (round 1 problems: A a plain parrot, B a dodo, C hard facets and a tiny crest; so "low-poly, soft facets" was dropped for "smooth rounded organic shapes" and the crest and arms were stressed):
- D crouch soft, size 5x7x8, asset `114635952828217`: `soft rounded cockatoo raptor dinosaur crouching forward with a curved back, plump smooth cream-white feathered body, big head with a tall swept-back fan of long pale yellow crest feathers, hooked dark grey beak, big brown eye, fluffy feathered arms with big curved black claws held forward, thick bent grey scaly legs with big black claws, tail of cream feathers with yellow tips, smooth rounded organic shapes, kids game`
- E chubby raptor, size 5x8x8, asset `80376371850073`: `chubby cockatoo raptor dinosaur with a curved body, big hooked dark grey beak, tall swept-back crest of long pale yellow feather blades, big brown eye, cream-white fluffy feathered body, feathered arms with black curved claws held forward, thick grey scaly legs with big black claws, tail feathers with yellow tips, smooth soft rounded shapes, cute, kids game`
- F theropod tilted, size 5x7x9, asset `114240745449528`: `cockatoo theropod dinosaur, body tilted forward with a long horizontal feathered tail for balance, S-curved neck, cream-white fluffy feathers, swept-back pale yellow crest, hooked dark grey beak, big brown eye, small feathered arms with black curved claws, strong bent grey scaly legs with big black claws, yellow-tipped tail feathers, soft rounded smooth shapes, cute, kids game`

Round 3 (best parts of round 2: F's pose and D's crest and scalloped feathers):
- G theropod scalloped, size 5x7x9, asset `87704847003593`: `cockatoo theropod dinosaur, body tilted forward with a long horizontal feathered tail, S-curved neck, plump cream-white body of soft scalloped feathers, tall swept-back fan of long pale yellow crest feathers, big hooked dark grey beak, big brown eye, feathered arms with big curved black claws held forward, long strong grey scaly legs with big black claws, yellow-tipped tail feathers, smooth rounded organic shapes, cute, kids game`
- H crouch run scalloped, size 5x6x9, asset `133259808005218`: `cockatoo dinosaur running low in a crouch, back and long tail in a smooth horizontal curve, head raised on a curved neck, plump cream-white body of soft scalloped feathers, tall swept-back fan of long pale yellow crest feathers, big hooked dark grey beak, big brown eye, feathered arms with big curved black claws held forward, strong bent grey scaly legs with big black claws, yellow-tipped tail feathers, smooth rounded organic shapes, cute, kids game`

Round 4 (lead: H is the base; change ONE thing per generation; each prompt is H's text with only the named change):
- I H + long clawed legs, asset `138642212523860`: legs clause replaced by `long strong bent legs in grey scales with three huge curved black claws on each foot`.
- J H + crest as three long blades, asset `119185638622365`: crest clause replaced by `crest of three long pale yellow feather blades swept far back` (legs clause back to H's `strong bent grey scaly legs with big black claws`).
- K H + strongly hooked beak, asset `77920946493998`: beak clause replaced by `big strongly hooked dark grey beak curving down` (rest exactly H).

## Pictures (all in [review-2026-10-17](../review-2026-10-17/))
- [131 overview, owner draft + turnaround side + the side view of every candidate](../review-2026-10-17/131-cockatoo-generated-overview-side-views.jpg)
- [132 winner H: front, side and 3/4 under the owner draft and the turnaround](../review-2026-10-17/132-cockatoo-generated-H-vs-references.jpg)
- [133 round 1 A, B, C](../review-2026-10-17/133-cockatoo-generated-round1-ABC.jpg), [134 round 2 D, E, F](../review-2026-10-17/134-cockatoo-generated-round2-DEF.jpg), [135 round 3 G, H](../review-2026-10-17/135-cockatoo-generated-round3-GH.jpg) (each: front, side, 3/4); round 4: [136 I, J, K](../review-2026-10-17/136-cockatoo-generated-round4-IJK.jpg), [137 best K under the owner draft and turnaround](../review-2026-10-17/137-cockatoo-generated-K-vs-references.jpg), [138 side views H, I, J, K next to the draft](../review-2026-10-17/138-cockatoo-generated-H-to-K-side-views.jpg)

## Ratings against the owner draft (honest, 10 = same character and shape)
| | Rating | What is good | What is off |
| --- | ---: | --- | --- |
| A upright | 4 | Reads as a cockatoo, soft, yellow crest and tail | A parrot standing straight, not a curved dino: no feathered arms, no claws, no scaly legs; the crest is thin sticks with one orange blade |
| B chubby | 3 | Curved neck and back, cute dino shape, soft | A dodo, not a cockatoo: tiny crest, blunt beak, no arms with claws, grey-blue legs |
| C crouching run | 3.5 | The pose is the owner draft's low run, wings forward | Hard flat facets (not soft), tiny crest, wings are flat panels, yellow only as a thin stripe |
| D crouch soft | 5 | Best crest (fan of long blades), scalloped feathers, hooked grey beak, front view close to the turnaround sheet | Squat round parrot, not crouching, no visible arms or claws |
| E chubby raptor | 4 | Huge swept crest, hooked beak | A parrot again, brown stain marks on the wing, no arms or claws |
| F theropod tilted | 5 | Soft, curved, theropod stance with a horizontal tail and small clawed arms | Blunt dodo beak, small crest, short legs, grey-blue feet |
| G theropod scalloped | 4.5 | The most dino shape of all: S-curved neck, long legs, raised arm with claws, long tail | Thin and slim (not chubby), single banana crest, small beak, plain smooth skin, reads as an ostrich-raptor |
| **H crouch run scalloped** | **6** | Closest to the owner draft: low horizontal body and tail, head raised, big fan crest, soft rounded body, yellow-tipped tail, wings forward with black claws, cute face | Legs are short and hidden (no long scaly grey legs with big claws), the beak is less hooked, the feathers are smooth (no scalloped layers), the pose is squatter than the draft |
| I H + long clawed legs | 4.5 | Big yellow-orange crest, hooked beak | The leg change did NOT work: legs still short, and the whole pose flipped to an upright parrot with a brown wing stripe; the crouching run was lost |
| J H + three crest blades | 5 | Horizontal body, hooked dark beak, yellow-tipped fan tail, clean soft shapes | The crest is three banana-like blades that curl forward, plain smooth feathers, no arms or claws visible, legs short |
| **K H + hooked beak** | **6.5** | Low crouching run like the draft, arm held forward with big black claws, crest with horn-like tufts (front view close to the turnaround sheet), soft cream body, yellow tips on the tail, cute face | Legs still short and dark blue-grey, no scaly texture or big toe claws, the beak is only a little hooked, smooth feathers, crest more cream than yellow |

**Round 3 winner: H, 6 of 10.** Round 4 winner: K, 6.5 of 10 (see below).

**Superseded: round 3 text:** H, 6 of 10, a candidate, not accepted. It is the first one that is both curved and cockatoo-coloured. It is still a soft toy bird, not the draft. The two things the generator keeps missing are layered feather scales and long scaly legs with big claws.

## Numbers from Studio (no FBX export was possible: `generate_mesh` results live in the place)
Triangles measured with `EditableMesh` face counts over all 8 MeshParts: H 9,822 total (largest part 1,990), A 9,528, B 9,818, C 9,356, D 9,858, E 9,878, F 9,752, G 9,484. All about 10k, well under the 21k-per-mesh Roblox limit. Size of H as placed: 3.0 x 6.0 x 5.8 studs (body 2.3x2.9x3.3, head 2.0x2.0x2.4, crest 0.6x2.3x3.4, wings 1.3x1.3x2.2 and 1.3x1.3x3.0, legs 1.2x1.9x1.6 and 1.2x1.6x2.4, tail 1.5x1.4x1.8). `tools/check_model_for_roblox.py` is not on `origin/main` (PR #468 not merged) and the generated model cannot be exported from the sandbox, so that check was NOT run.

## Round 4 result and recommendation (cap of 11 generations reached, no candidate reached 7)
**Best: K, 6.5 of 10, asset `77920946493998`, 9,864 triangles (largest part not measured separately), 3.4 x 6.0 x 6.1 studs.** I 9,834, J 9,810 triangles. Prompt wording cannot fix the legs: asking for long clawed legs (I) made the generator drop the crouch and return a parrot. What prompts do deliver: pose, crest, colours and cute faces. What they do not: scaly legs with big toe claws and layered feather scales.

Recommendation (LEAD to decide): (1) accept K as a **placeholder at 6.5 of 10** for the playtest, or (2) keep K as the base and **hand-model the two legs and feet in Blender** (scaly grey legs, three big black claws per foot, bent like the draft), then upload through the pipeline in docs/169 and swap only the `left leg`/`right leg` parts. Option 2 is the realistic way to reach 8 and keeps to the rule 'generation plus Blender cleanup'. No more prompt rounds are recommended.

## Earlier note: next prompt to try after round 3 (done as I; it did not help)
H with G's legs and the claws stressed, one change at a time: `cockatoo dinosaur running low in a crouch, back and long tail in a smooth horizontal curve, head raised on a curved neck, plump cream-white body of soft scalloped feathers, tall swept-back fan of long pale yellow crest feathers, big hooked dark grey beak, big brown eye, feathered arms with big curved black claws held forward, long strong bent legs in grey scales with three huge curved black claws on each foot, yellow-tipped tail feathers, smooth rounded organic shapes, cute, kids game` (adds only the long clawed legs). If the legs still come out short, the realistic route is the legs and feet cleanup in Blender on the winner (the generated mesh is the base; the owner's rule allows generation plus Blender cleanup).

## NOT done
No Place 1 model, no game integration (no `LowPolyDinoAssets` entry, species config, drop weight, class). The scratch place was not saved, so the eight asset ids above (published by the generator, insertable with `insert_asset`) are the record.
