# BD-513 BIG camera cap and BD-508 found-egg toast: evidence (2026-10-17)

Status: **Studio re-measure DONE 2026-10-17 (BD-513 PASS, BD-508 PASS)**; the offline proof below is kept, and "What blocked the Studio part" is history.

## Studio results (2026-10-17)

Build: `python tools/build.py --profile playtest --output C:/Users/znypr/dtmp/captures.rbxlx` (origin/main with PR #379, plus PR #383's branch), own Studio window, Play, real run on the island (`RunLifecycle.requestStart`), default gameplay camera (Custom) with `CameraMaxZoomDistance = CameraMinZoomDistance` (the camfit method, so the drawn distance is the minimum zoom the size rule asks for), view 1140 x 785 (60 frames/s). BIG = `GrowthScore` 750 and `BigDinosaur` true on the server, which `HubScaleRules` turns into scale 4 x 1.2 = **4.8**; species set with `Dinosaur.setSpecies`. Fill = the real model box (all visible parts, 8 corners each) projected with `WorldToViewportPoint`, height divided by the 785 px view height; the HUD line is 160 px.

| Species | Scale | Min zoom | Fill of screen height | Box top (px) | Box bottom (px) | Picture |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| spinosaurus | 4.8 | 86.6 | **56.3%** (before 72%) | 161 | 603 | [01](01-big-spinosaurus-4.8.jpg) |
| tyrannosaurus | 4.8 | 83.2 | **45.7%** (before 51%) | 180 | 539 | [02](02-big-trex-4.8.jpg) |
| ankylosaurus | 4.8 | 90.0 | **42.3%** (before 49%) | 217 | 549 | [03](03-big-ankylosaurus-4.8.jpg) |

The measured fills match the offline expectation (56 / 45 / 41). Only the Ankylosaurus sits at the cap (90.0, it asks for 89.2). **The Spinosaurus sail does not touch the banner:** the box top is 161 px (a box corner, 1 px under the 160 px line), the visible sail tip is at about 188 px and the hint line "Eat food to grow..." ends at about 178 px; the T-Rex head top is about 183 px, also just under the hint text (a few px of air). So no pitch-lift row was opened. The box bottom is below the visible feet because the box includes the far tail and legs in perspective.

BD-508: Admin panel remote (`AdminAction`): Food worth x10, Mutation chance x10, `startWeather volcano`; the dino walked to food. [04](04-multi-egg-toast-ember.jpg) shows the toast "You found 3 eggs!" over "2 Ember eggs! Hatch them at Home" (1140 x 785 view). [05](05-toast-7-eggs-phone-836x390.jpg) is the same at the 836 x 390 phone window: "You found 7 eggs!" over "An Ember egg! Hatch them at Home". Both fit inside the card. PASS.

## History: what blocked the Studio part earlier

Builds `bigcam0.rbxlx` (origin/main) and `bigcam.rbxlx` (this branch), `--profile playtest`, were opened in new Studio windows and placed on screen 3 as required. In every window on the PC, including other agents' (`phonefit.rbxlx`, checked read-only), the 3D viewport never rendered: `RunService.RenderStepped` fired 0 times in 2 s, `Camera.ViewportSize` was 1 x 1, the window repainted only partly (no ribbon, blank viewport), `screen_capture` timed out or the MCP connection closed, with the window maximised, restored, moved to screen 1 and re-launched (twice). Studio itself was healthy (autosave ran, `execute_luau` and Play worked, server side `RunLifecycle.requestStart` and `Dinosaur.render(character, 4.8, "spinosaurus")` worked), so the dinosaur could be placed but the camera and the picture could not be produced. No image was faked or taken from another source. Re-run the capture when a Studio window renders: BIG Spinosaurus, T-Rex and Ankylosaurus at growth scale 4.8, camfit method (`docs/evidence/2026-10-17-camfit/README.md` s1: 1140 x 785, FOV 70, camera pulled to its minimum zoom).

## Numbers (offline, from `CameraFraming` and the 22 measured boxes)
Minimum zoom the size rule asks for at growth scale 4.8, and what the old cap 75 gave:

| Species | Rule asks | Old cap 75 | New cap 90 | Screen share before (camfit, measured) | Expected after (scale 4 sweep, NOT measured at 4.8) |
| --- | ---: | ---: | ---: | ---: | ---: |
| ankylosaurus | 89.2 | 75.0 | 89.2 | 49% | about 41% |
| spinosaurus | 86.5 | 75.0 | 86.5 | 72% (sail behind the banner, top 64 px) | about 56%, top about 160 px |
| tyrannosaurus | 82.1 | 75.0 | 82.1 | 51% (head at the hint line, top 150 px) | about 45%, top about 180 px |
| elasmosaurus | 78.0 | 75.0 | 78.0 | not captured | about 46% |
| therizinosaurus | 76.6 | 75.0 | 76.6 | not captured | about 44% |

At scale 4 or less nobody needs more than 75.4 (Ankylosaurus), so only BIG dinos change. `CameraOcclusion.MaxRange` is 100 (cap + 10).
The Spinosaurus top is the open risk: the scale 1, 2, 4 tops were 255, 199, 165 px and the trend gives about 160 to 166 at 4.8, on the 160 px HUD line used by camfit. If the Studio shot shows the sail at the banner, add a small pitch lift for very large bodies (BC1 fallback).

## Checks run
`tools/verify_camera_framing.py` (cap 90, no species held by the cap at 4.8, range at least cap + 10), `tools/verify_camera_occlusion.py` (90 stud camera), `tools/verify_ftue_p1.py` (toast copy: 7 weather names x 7 egg counts x 4 weather counts x one kind / mixed, 224 cases within 30 / 44 characters), `tools/verify_egg_toast_count.py` (HudV2 counts every tagged egg).
