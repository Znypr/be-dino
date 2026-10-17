# Water species by bulk (C-39, BD-537), 2026-10-17

Studio evidence from an own window (`dtmp/water.rbxlx`, `python tools/build.py --profile playtest` of branch `claude/water-bulk-c39`), Play, RenderStepped 60 frames/s before every capture, viewport 1140 x 785, FOV 70. Images are Studio `screen_capture` only; the CameraType was set back to Custom afterwards. Window closed and only its own Studio process ended.

Rule (owner BD-232, "fly/water scaled by bulk to the T-Rex"): bulk = cube root of width x height x length; T-Rex bulk 8.12 at tier 5, 10% less per tier below (5.55 / 6.10 / 6.71 / 7.38 / 8.12). Only three species are class Water (Ichthyosaurus, Plesiosaurus, Mosasaurus); Elasmosaurus stays Ground (docs/101).

## Sizes (Studio `GetBoundingBox` of `LowPolyDinos.clone(species)` at growth scale 1)

| Swimmer | Tier | Scale before to after | Box W x H x L before | Box W x H x L after (re-read in Studio) | Bulk after (target) |
|---|---:|---|---|---|---|
| Ichthyosaurus | 3 | 2.87 to 3.71 | 3.78 x 4.31 x 8.61 | 4.89 x 5.57 x 11.13 | 6.716 (6.71) |
| Plesiosaurus | 3 | 2.87 to 2.78 | 4.81 x 7.99 x 8.61 | 4.66 x 7.74 x 8.34 | 6.698 (6.71) |
| Mosasaurus | 5 | 3.47 to 5.64 | 3.37 x 3.55 x 10.41 | 5.48 x 5.77 x 16.92 | 8.116 (8.12) |

Compy 3.49 x 6.60 x 7.69 and T-Rex 5.31 x 9.67 x 10.41 read the same as before. The "after" boxes equal the computed ones (old box x new scale / old scale) to 2 decimals. Head parts re-read: Ichthyosaurus snout 5.57, head 5.11; Plesiosaurus 4.17, 3.92; Mosasaurus 8.46, 4.37 (`ScaleLadder` updated by 0.01 for Plesiosaurus head and Mosasaurus snout). Mosasaurus is now longer than the T-Rex (16.92 versus 10.41) but lower (5.77 versus 9.67).

## Images

- [before-lineup.jpg](before-lineup.jpg): left to right Compy, T-Rex, Ichthyosaurus, Plesiosaurus, Mosasaurus, before (the three swimmers are the same models scaled back to the old scales with `Model:ScaleTo`).
- [after-lineup.jpg](after-lineup.jpg): the same five on the same spots, after (the real current `LowPolyDinoAssets` scales).
- Default game camera at the minimum zoom, a real island run (`RunLifecycle.requestStart`, rain on), growth scale 1: [camera-ichthyosaurus-s1.jpg](camera-ichthyosaurus-s1.jpg), [camera-plesiosaurus-s1.jpg](camera-plesiosaurus-s1.jpg), [camera-mosasaurus-s1.jpg](camera-mosasaurus-s1.jpg); Mosasaurus at growth scale 4: [camera-mosasaurus-s4.jpg](camera-mosasaurus-s4.jpg).

## Camera sweep rows (the three rows of `tools/verify_camera_framing.py` STUDIO)

Same method as [camfit](../2026-10-17-camfit/README.md): species set on the server (`Dinosaur.setSpecies`), growth scale 1 / 2 / 4 by `GrowthScore` 0 / 150 / 750 + `Dinosaur.syncScale`, the camera pulled to its minimum zoom (`CameraMaxZoomDistance = CameraMinZoomDistance`), fill and top = the visible parts' real box corners projected with `WorldToViewportPoint` on the 785 px screen.

| Species | Scale 1 zoom / fill / top | Scale 2 | Scale 4 |
|---|---|---|---|
| ichthyosaurus | 13.44 / 39% / 345 | 26.89 / 36% / 267 | 53.78 / 37% / 235 |
| plesiosaurus | 13.92 / 44% / 294 | 27.84 / 42% / 230 | 55.68 / 41% / 207 |
| mosasaurus | 18.17 / 26% / 355 | 36.33 / 26% / 300 | 72.66 / 28% / 263 |

All in the 25% to 56% fill band, top 160 px or more, under the 90 stud cap (Mosasaurus BIG at scale 4.8 would be 87.2). The Mosasaurus is the smallest fill (26%): a long, low body is framed by its length, so it reads smaller on screen than the other swimmers. Before the change these were 12.0 / 40% / 367 (Ichthyosaurus), 14.4 / 46% / 264 (Plesiosaurus) and 12.0 / 39% / 402 (Mosasaurus).

Not covered: phone, published server, hit feel. The projection of the fill is a computed measure of the real model in the real camera, not a pixel count of the screenshot.
