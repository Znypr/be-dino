# Eaglesaurus, generated candidates (BD-622), 2026-10-18

Owner wants models "more dino shapes, curved natural" (same note as the cockatoo, [../2026-10-18-cockatoo-generated](../2026-10-18-cockatoo-generated/README.md)). Status of everything here: **candidate** (not accepted art, not in the game, not in Place 1). Not Studio-play tested, not phone tested; looked at as pictures only.

## References
- PRIMARY: the owner draft [reference/eagle-owner-draft.webp](../../reference/eagle-owner-draft.webp) (a bald-eagle dino in a low forward-leaning stance on two strong legs, scalloped chestnut feathers with tan edges, white head with a feather tuft and a big white neck ruff, hooked yellow beak, big yellow scaly feet with huge dark claws, small feathered arms held forward with dark claws, a long white tail with tan tips).
- ChatGPT turnaround sheet (front, side right, back), made from the draft: [reference/eagle-turnaround-chatgpt-v1.png](../../reference/eagle-turnaround-chatgpt-v1.png), prompt in [reference/eagle-turnaround-chatgpt-v1.txt](../../reference/eagle-turnaround-chatgpt-v1.txt). Reference only, not final art.
- Real and stylised eagles (look-only notes below).

## What to copy (research in the owner's browser, 2026-10-18)
Looked at with Claude in Chrome, nothing downloaded except the ChatGPT sheet. Licences read from the Commons data of each picture.
Real bald-eagle photos (all on Wikipedia, licence from Commons):
1. [Bald eagle about to fly in Alaska (2016)](https://commons.wikimedia.org/wiki/File:Bald_eagle_about_to_fly_in_Alaska_(2016).jpg), CC BY 2.0, Andy Morffew. A perched eagle leaning forward with the wings half lifted. Copy: the body leans forward with the back running down to the tail (not an upright statue); big hooked beak; the legs show as thick feathered thighs that end in bare yellow lower legs and big feet.
2. [Bald Eagle Portrait](https://commons.wikimedia.org/wiki/File:Bald_Eagle_Portrait.jpg), CC BY-SA 3.0, Saffron Blaze. Head close-up. Copy: the beak is big, deep and strongly hooked with a yellow cere; the white head is a smooth cap that flows into a thick white neck that ends in a V; a heavy brow over a pale yellow eye gives the fierce look (the draft softens this to a big round brown eye).
3. [Bald eagle foot closeup](https://commons.wikimedia.org/wiki/File:Bald_eagle_foot_closeup.jpg), CC BY-SA 4.0, Bloopityboop. Copy: bare yellow scaly leg and toes (rows of small scales, rough pads), and a very long, smoothly curved black talon.
4. [Lady Baltimore](https://commons.wikimedia.org/wiki/File:Lady_Baltimore,_in_her_habitat.jpg), CC BY-SA 3.0, Michaelh2001. Front view. Copy: the white head sits on a wide dark chest, the wings are folded down the sides like arms, the white tail hangs behind, the legs are short and feathered down to the knee.
5. [Haliaeetus leucocephalus 38319](https://commons.wikimedia.org/wiki/File:Haliaeetus_leucocephalus_38319.JPG), CC BY 2.5, Walter Siegmund (young bird). Copy: the side profile of the perched body, the long tail that hangs below the line of the legs, the feather edges that look like tiles.
Stylised and cartoon eagles (Google image search, look only, licence unknown, nothing copied or saved): big head (about a third of the body), thick white neck ruff in a V, very big round eyes under a heavy brow, short rounded body, soft folded wings, chunky yellow feet, a big orange-yellow hooked beak, a short white tail fan.
What to copy for the model, in short: (a) a big white head with a small tuft and a thick white ruff; (b) a deep, clearly hooked yellow beak; (c) a forward-leaning back that runs in one smooth line into the tail; (d) feathered thighs then bare yellow scaly legs and large yellow feet with three huge curved black talons; (e) small clawed arms held forward; (f) a white tail with tan tips; (g) scalloped feathers with tan edges.

## ChatGPT sheet: what it got right and what it invented
ChatGPT (owner account, Instant model), 1 try, same workflow as the cockatoo (docs/167 section 4). Checklist from docs/167:
- [x] Input draft: [reference/eagle-owner-draft.webp](../../reference/eagle-owner-draft.webp), made by the owner.
- [x] Prompt saved: [reference/eagle-turnaround-chatgpt-v1.txt](../../reference/eagle-turnaround-chatgpt-v1.txt), 2026-10-18, 1 try.
- [x] Result 1774 x 887 px, 1.8 MB, reference only.
- [x] Differences from the draft: the front view stands much more upright than the side view (the front looks like a standing owl-eagle with arms down, the side is the crouch from the draft); the back view shows a spiky white tuft on the head and a small white feather patch on the rump (tail seen from behind); the beak looks a bit shorter and the face friendlier than the draft; the legs are a little longer and thinner than in the draft. The draft wins.
- [x] Proportions: head size, leg length and tail are the same in the three views; only the lean of the body differs.

## Setup
- Scratch Studio window `cockatoo-scratch.rbxl` only. Place 1 and `playtest-build2.rbxlx` were not touched. The scratch place was NOT saved.
- Tool: `generate_mesh`, text prompt only (no image input), `segmentation=explicit`, parts `body, head, beak, left wing, right wing, left leg, right leg, tail` (the small feathered arms are the "wings"; the separate beak is meant to get a clean yellow). Run async. **8 generations used (the cap)**: round 1 three (A, B, C), round 2 two (D, E), round 3 two (F, G), round 4 one (H). Every generation came back split into the 8 parts with clean names. A first attempt of F and G was refused with "Character limit exceeded" (527 and 516 characters, no mesh made, not counted); the limit is somewhere between 489 and 516 characters, so keep under 490.
- Models are in `Workspace > Eagle candidates` in a row at **z = 340** (not z = 300: the Cockatoo candidates v2 row already stands at z = 300, x 0 to 84): A x=0, B x=12, C x=24, D x=36, E x=48, F x=60, G x=72, H x=84, all turned to face +x, bottom on y=0. For the pictures one candidate was visible at a time and the Cockatoo row and other folders were parked in ServerStorage and put back afterwards. All eight stand in the folder now.
- Pictures are `screen_capture` renders (516 x 481): front, side and 3/4 for each candidate. A first picture right after inserting can be grey: the textures load a few seconds later (candidate B was grey, then red). Front views are darker because the light comes from behind.

## Prompts (exactly as sent)
Round 1 (A, B, C, all three rewritten from the prepared prompts in prompts.txt to the cockatoo lessons: smooth organic shapes, legs named early):
- A crouch like the draft, size 4x6x8, asset `78705238199400` (487 chars): `bald eagle dinosaur in a low forward-leaning crouch like a raptor, plump dark chestnut-brown body of layered scalloped feathers with tan edges, white head with a short white feather tuft and a thick white neck ruff, big hooked yellow beak, big round brown eye, small feathered arms held forward with big dark curved claws, long strong bent legs with bright yellow scaly feet and three huge curved black claws, long white tail with tan tips, smooth rounded organic shapes, cute, kids game`
- B upright dino stance, size 4x8x7, asset `98207620497063`: `bald eagle dinosaur standing upright on two long strong bent legs with bright yellow scaly feet and three huge curved black claws, plump dark chestnut-brown body of soft layered scalloped feathers with tan edges, white head with a short white feather tuft and a thick white neck ruff, big hooked yellow beak, big round brown eye, small feathered arms held forward with big dark curved claws, long white tail with tan tips held out behind, smooth rounded organic shapes, cute, kids game`
- C chubby, tilted, size 4x7x8, asset `77860434529141`: `chubby cute bald eagle dinosaur, tilted forward with a long horizontal tail for balance, big round white head with a short tuft and a thick white neck ruff, big hooked yellow beak, big round brown eye, plump chestnut-brown body of soft scalloped feathers with tan edges, small feathered arms with big dark curved claws held forward, long strong bent legs with bright yellow scaly feet and three huge curved black claws, white tail with tan tips, smooth rounded organic shapes, kids game`

Round 2 (A is the base; one change each; "short white feather tuft" cut to "short white tuft" and "big round brown eye" to "big brown eye" in D and later only to stay under the length limit):
- D = A with the tail clause `wide white feather-fan tail with tan tips`, asset `123690193296965`.
- E = A with the legs clause `feathered thighs, long bare yellow scaly shins, huge feet with three big black claws`, asset `129626619779173`.

Round 3 (E's text is the base, 472 chars: `bald eagle dinosaur in a low forward-leaning crouch like a raptor, plump dark chestnut-brown body of layered scalloped feathers with tan edges, white head with a short white tuft and a thick white neck ruff, big hooked yellow beak, big brown eye, small feathered arms held forward with big dark curved claws, feathered thighs, long bare yellow scaly shins, huge feet with three big black claws, long white tail with tan tips, smooth rounded organic shapes, cute, kids game`):
- F = E with the tail clause `broad flat white feather tail held out behind`, size 4x6x8, asset `116840996663024`.
- G = E with the opening `bald eagle dinosaur running low, back and tail in a horizontal line, head raised` (instead of the crouch), size 4x6x9, asset `97155339193950`.

Round 4 (the last generation, the cap):
- H = G with F's tail clause, plus `smooth rounded shapes, kids game` (cut "organic" and "cute" to stay at 489 chars), size 4x6x9, asset `116638992063695`.

## Pictures (all in [review-2026-10-17](../review-2026-10-17/))
- [139 overview: owner draft, turnaround sheet and the side view of all 8 candidates](../review-2026-10-17/139-eagle-generated-overview-side-views.jpg)
- [140 BEST F: front, side and 3/4 under the owner draft and the turnaround sheet](../review-2026-10-17/140-eagle-generated-F-vs-references.jpg)
- [141 round 1 A, B, C](../review-2026-10-17/141-eagle-generated-round1-ABC.jpg), [142 round 2 D, E, F](../review-2026-10-17/142-eagle-generated-round2-DEF.jpg), [143 round 3 G, H](../review-2026-10-17/143-eagle-generated-round3-GH.jpg) (each: front, side, 3/4)
- [144 the ChatGPT turnaround sheet](../review-2026-10-17/144-eagle-turnaround-sheet-chatgpt.png)

## Ratings against the owner draft (honest, 10 = same character and shape)
| | Rating | What is good | What is off |
| --- | ---: | --- | --- |
| A crouch | 6 | Clear bald eagle: white head, big hooked yellow beak, brown body with a little scallop pattern, yellow feet with black claws, crouched like the draft | Tail is a brown lizard tail with stripes (not white feathers), legs short and thin, the arms are tucked and barely show, body skin smooth with a swirl pattern |
| B upright | 3 | Nice curved dino stance, white feathers on the chest | A red raptor with a duck-like head and a flat yellow beak: not an eagle |
| C chubby | 3.5 | Very cute, white head, hooked yellow beak, scalloped face | A chicken: tiny legs, brown fan tail pointing up, no arms with claws |
| D tail fan | 5 | Cute, white tail fan, hooked beak, scalloped chest | Small and squat, the body shrank to a round bird, legs short, beak rounder |
| E bare legs | 6.5 | Best eagle FACE and feathers: white head, deep hooked beak, scalloped tan-edged feathers, big yellow feet with black claws, long white tail blade | Stands upright and hunched like a statue (not a dino crouch), no visible arms with claws, legs are still brown feathered, tail is one thin blade |
| **F flat tail** | **6.5** | **Most dino shape**: low crouch, back and brown tail in one horizontal line ending in a white feather fan, long legs with yellow scaly shins and big feet with black claws, one arm held forward with a claw, hooked yellow beak (the owner's "dino shapes, curved natural") | Head is small and a bit lizard-like (the beak is thin), body smooth (no layered scalloped feathers), tail is brown with white only at the tip, no white neck ruff to speak of |
| G running | 6 | Pose is the closest to the draft's low run: head up, wings along the back, white tail horizontal, big feet | The eye is an orange square patch, the body looks muscular and rough (not fluffy), dark wing stripe, beak small |
| H running + flat tail | 6 | Cute, white head with tuft and ruff, scalloped chest, both arms forward with black claws, feet with three black claws, white tail horizontal | Squat, short legs and a short body (much smaller than the draft), tail is only a short white stub |

**Best: F (asset 116840996663024), 6.5 of 10. Nothing reached 7 and the cap of 8 generations is used.** E has the nicest eagle face but not the dino shape; H is the cutest; F is the one that changes the shape the way the owner asked. Same two gaps as the cockatoo: the generator gives a smooth skin (no fluffy layered feathers) and keeps the legs shorter than the draft, and it ignores the "large white neck ruff and fluffy tail" words after about the third try. Prompt words changed colours and pose well and the tail clause worked (D, F, H), but the generator does not do arms with claws reliably (only A-F-H show them).

Recommendation (LEAD decides): accept F as a **placeholder at 6.5 of 10**, as was done for the cockatoo K, and keep E's head as the model for a later Blender cleanup of F's head (a bigger, deeper hooked beak and a white neck ruff). No more prompt rounds are recommended.

## Numbers from Studio (no FBX export was possible: generate_mesh results live in the place)
Triangles measured with `EditableMesh` face counts over all 8 mesh parts (largest part in brackets): A 9,822 (3,664), B 9,918 (4,232), C 9,836 (2,044), D 9,840 (2,358), E 9,882 (3,150), **F 9,652 (1,924)**, G 9,858 (3,454), H 9,886 (2,658). All about 10k, well under the 21k-per-mesh Roblox limit. Size as placed (width x height x length, studs): A 3.8 x 6.0 x 7.2, B 3.3 x 6.5 x 7.0, C 4.0 x 5.2 x 6.3, D 4.0 x 5.0 x 5.4, E 4.0 x 6.0 x 6.6, **F 4.0 x 5.5 x 7.7**, G 4.0 x 5.5 x 7.7, H 4.0 x 5.8 x 6.2. `tools/check_model_for_roblox.py` was not run (the model cannot be exported from the sandbox).

## NOT done
No Place 1 model, no game integration (no `LowPolyDinoAssets` entry, species config, drop weight, class). The scratch place was not saved, so the asset ids above (published by the generator, insertable with `insert_asset`) are the record.
