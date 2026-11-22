# 248 ChatGPT art-director critique of every asset (2026-11-22)

The owner asked to have all current assets critiqued with ChatGPT and to get proposed changes. Input: three sheets from the uniform
captures:
- all 31 creatures (portrait tool);
- all 86 placed world models (`world_pairs.luau`), each scaled to the same size;
- the UI kit pieces: shop kit 2, the proposed hatch kit and the older Toybox kit.

The same pictures are in the Be Dino Desk (docs/247), where the owner rates each item. Owner taste and approved board designs win over
this critique. Where they clash, the clash is listed at the end.

## Scores

| Sheet | Score | Verdict |
|---|---|---|
| Creatures (31) | 6.5 / 10 | Good silhouettes, but eyes, facet density, anatomy and materials vary |
| World models (86) | 4.5 / 10 | Weakest: reads like assets from several games |
| UI kit | 5.5 / 10 | Three competing systems; kit 2 alone is about 8 / 10 |

Biggest problems:
1. Three 3D styles: sharp chunky creatures, soft airbrushed bubble trees, primitive or neon cave props.
2. No standard for faces, palette or material:
   - eyes differ (square on Raptor, glossy round on T-Rex, anime slits on Foxosaurus);
   - colours range from neon to muddy to pastel;
   - Brachiosaurus and Dimorphodon have dirty smudges.
3. Shapes repeat and the UI runs three systems:
   - near-duplicate silhouettes: Elasmosaurus and Plesiosaurus; Compy, Baryonyx and T-Rex;
   - the three UI kits use different corners, outlines, studs and gloss.

## Proposed style rules (every new or reworked asset)

1. **Shape:** chunky, rounded low-poly with large planes and bevelled edges. No thin realistic geometry; the silhouette must read at 120 px.
2. **Creature proportions:** the head is about 35-45 % of the height on small dinos, with short chunky limbs.
3. **Eyes:** a glossy black oval or circle with one small white highlight, 10-15 % of the head width. No square eyes or slits.
4. **Palette:**
   - one body colour, one lighter secondary and one accent;
   - core colours green #39C978, orange #F59A45, cyan #40C5EA, purple #A276EB, yellow #F7D56D, cream #FFF0CE.
5. **Contrast:** faces and interactive objects stay readable on grass. No large neon-green areas and no muddy darks.
6. **Texture:** flat colour or broad shading in 2-3 value groups. No photo texture, noise, scratches or random gradients.
7. **Outline:** dark keyline #24252B, about 3 px at 256 px, on character and icon renders.
8. **Material:**
   - creatures are satin (roughness 0.45-0.6);
   - the world is matte (0.6-0.8);
   - the UI is glossy with one highlight.
9. **World geometry:** trees have 3-7 big canopy clusters; rocks have 5-12 facets; grass has 4-7 thick blades. No hair-thin vines or needle grass.
10. **UI:** one kit (kit 2) with 5-7 px dark outlines at 256 px, small inset studs, 12-15 % card corners, pill buttons and one top-left gloss.

## Worst 12 (ranked) and the fix

| # | Asset | Problem | Fix |
|---|---|---|---|
| 1 | cave_lava_rim_rock | Reads as a blue padded seat | Rebuild: jagged basalt #4C4B60 with an orange lava fissure #FF7841 |
| 2 | dimorphodon | Purple fantasy dragon, dark head smudge | Repaint #9067E4 and rebuild the head; wings in 2-3 sections |
| 3 | pachycephalosaurus | Muddy olive, unclear dome | Rebuild the head with a big round dome #E9C75E; body #8EBC58 |
| 4 | veg2_grass_b | Blue/yellow shards read as crystals | Remove from grass, or remake as 5-7 broad green blades |
| 5 | foxosaurus | Electric blue, anime eyes | New face with round eyes, fewer spikes, blue #4D9CE3 |
| 6 | cave_stalagmite_l | Three plain blue cones | Rebuild: 3-5 irregular faceted slate columns #74849B |
| 7 | brachiosaurus | Dirty dark-purple back patch | Repaint: #9877DE, lighter side #BAA0EE, cream belly |
| 8 | cave_moss_hang | Hair-thin strands, visual noise | Rebuild: 5-7 thick moss ribbons #80C97A |
| 9 | eaglesaurus | Too naturalistic | Head +20 %, bigger eye, simpler talons and feathers |
| 10 | veg2_rock_spiral | Odd hollow rock with heavy moss | Simple rounded rock #88939F, moss on 20-25 % of the top |
| 11 | tree_burnt | Realistic dark stump | Matte warm grey-brown with 5-8 facets and one simple orange glow |
| 12 | toybox card-common | Competes with the kit 2 cards | Remove; use kit 2 card-common |

Also:
- **Elasmosaurus vs Plesiosaurus:** give Elasmosaurus a slimmer neck and 4 clear flippers so the two stop looking alike.
- **Baryonyx:** make the snout 20-25 % bigger with stronger claws.
- **Barrel, forge altar, lagoon arch:** tone down the candy pink/orange.

Picture: `docs/evidence/2026-11-22-asset-critique/world-worst6-proposal.jpg` (ChatGPT redesign of the 6 worst world models; direction only, final art goes through Blender).

## Best 8 (the target look)

| Asset | Why |
|---|---|
| t-rex | Head size and eye (the creature reference) |
| stegosaurus | Colour blocking, defining anatomy |
| triceratops | Shape first |
| pteranodon | Readable flying silhouette |
| veg2_tree_fruit | The world reference: friendly, readable harvestables |
| hub_crystal_l | Collectibles and resources |
| kit2 card-rare | The UI reference |
| kit2 card-art-aura-tidal | Quality bar for card illustrations |

## Missing (compared with top collecting games)

- **P0:**
  - 5 distinct egg families (Meadow, Forest, Beach, Volcano, Special);
  - a complete physical hatch stage (nest, platform, cracks, 3 shell pieces, reveal pedestal);
  - a portrait set for all creatures (the capture tool now gives this);
  - a ground and terrain kit (grass, dirt, sand, paths, shore and cliff edges, cave floor, volcanic ground).
- **P1:**
  - a spawn landmark (hatchery or giant egg);
  - one family of shop buildings;
  - mutation and shiny visuals;
  - zone gateway landmarks;
  - pickup and growth feedback effects.
- **P2:**
  - floating world markers;
  - ambient effects;
  - collection states (locked silhouette, new, duplicate counter).

## UI kit verdict

- **Kit 2 is the master kit.** Keep all its cards, buttons, headers, close button, effect strip and card art.
- **Hatch kit:**
  - keep the effects and egg-painting pieces (burst, rays, sparkle, egg layers, pail, can, stream, drops, pedestal, ribbons, NEW! burst, tick);
  - rework the plates, pills and chips to the kit 2 outline weight;
  - drop its own cards, buttons and header.
- **Toybox:** retire it; only its panel frame might serve as the dark window body.
- **To build from kit 2:**
  - a purple button (#AE35E6);
  - a dark window body (#292A35);
  - a selected card state;
  - a disabled button;
  - an icon tile;
  - a progress bar.

Its suggested order:
1. UI consolidation.
2. The worst cave, grass and rock models, plus one world palette.
3. Creature eyes, materials and duplicates.
4. Eggs, the hatch stage and portraits.
5. Landmarks, shops and feedback effects.

## Lead notes (clashes and what happens next)

- **Correction (same day):** the dark patches on Brachiosaurus and Dimorphodon were a capture artifact, not paint. The magenta background part-keyed saturated purple and turned it brown; the BD-1291 session found it. Re-shot on a green background, both are clean, and the desk shows the clean pictures. So item 7 (Brachiosaurus repaint) and the smudge in item 2 are void. Dimorphodon's head and wing notes still stand. Purple and pink subjects are now captured on green.

- **Clash:** the owner asked on 2026-11-22 for rounder buttons and cards, and the hatch mock now uses the new rounded hatch buttons and cards (`btn-green`, `btn-purple`, `card-blue`, `card-grey`). ChatGPT says to drop them for kit 2. The owner decides by rating both in the desk (Text and buttons > Buttons; UI kit tab). Until then the hatch mock keeps the rounded ones.
- The creature findings went to the dino upgrade session (BD-1291). Its owner-approved cut already covers Pachycephalosaurus and the 3 paint fixes; Dimorphodon, Foxosaurus, Brachiosaurus and Eaglesaurus are its extra input.
- Queued as rows:
  - BD-1293: world rebuild pass on the worst 6 world models;
  - BD-1294: UI kit consolidation, waiting on the owner's button/card rating;
  - BD-1295: the P0 gaps (egg families, hatch stage, terrain kit).
