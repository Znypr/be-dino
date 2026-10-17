# Water species by bulk (C-39, BD-537), 2026-10-17

**Status: Studio images PENDING.** The lead asked for no Studio use while another agent's Studio was open (two agent Studios at once froze every new window). The numbers below are computed from the earlier Studio boxes (BD-471 / BD-232) times new scale / old scale (a uniform clone scale, so exact). They are not a new Studio reading.

Rule (owner BD-232, "fly/water scaled by bulk to the T-Rex"): bulk = cube root of width x height x length; T-Rex bulk 8.12 at tier 5, 10% less per tier below (5.55 / 6.10 / 6.71 / 7.38 / 8.12). Elasmosaurus stays Ground (docs/101).

| Swimmer | Tier | Scale before to after | Box W x H x L before | Box W x H x L after | Bulk before to after (target) |
|---|---:|---|---|---|---|
| Ichthyosaurus | 3 | 2.87 to 3.71 | 3.78 x 4.31 x 8.61 | 4.89 x 5.57 x 11.13 | 5.20 to 6.72 (6.71) |
| Plesiosaurus | 3 | 2.87 to 2.78 | 4.81 x 7.99 x 8.61 | 4.66 x 7.74 x 8.34 | 6.92 to 6.70 (6.71) |
| Mosasaurus | 5 | 3.47 to 5.64 | 3.37 x 3.55 x 10.41 | 5.48 x 5.77 x 16.92 | 4.99 to 8.12 (8.12) |

Reference: Compy 3.49 x 6.60 x 7.69, T-Rex 5.31 x 9.67 x 10.41. Mosasaurus is now longer than the T-Rex (16.92 versus 10.41) but lower (5.77 versus 9.67), which is what bulk gives. Only 3 species are class Water (Elasmosaurus is Ground).

Ladder order checks (`tools/verify_scale_ladder.py`): the dino door versus the tallest hub dino and colossal trees versus the tallest BIG-max dino do not move, because the tallest dino is still the T-Rex. The BIG-max Plesiosaurus height goes 38.4 to 37.2 and the Mosasaurus 17.0 to 27.7, both under the T-Rex 46.4.

Camera: `Shared/CameraFraming` reads the box, so the Mosasaurus camera now backs off (min zoom 12 to 18 at growth scale 1), Ichthyosaurus 12 to 13.2, Plesiosaurus 14.4 to 13.7. The three old Studio sweep rows were removed from `tools/verify_camera_framing.py` (PENDING_SWEEP) until the sweep is redone.

To do when Studio is free: build the playtest, place the 3 swimmers next to a Compy and a T-Rex at growth scale 1, capture before (origin/main) and after, re-read the three boxes, set the rows in `ScaleLadder` to the real reading, redo the camera sweep for the three, add the images here.
