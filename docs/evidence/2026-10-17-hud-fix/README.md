# HUD leftovers (BD-502): before / after, desktop Studio play

Playtest build (`python tools/build.py --profile playtest`) of a private local copy with the dev-only DemoTrigger flag on (never committed), opened in its own Studio window; the "before" place is the BD-501 branch head, the "after" place is this branch. A Shiny + BIG Triceratops came from the DemoTrigger hatch party and was opened through the real EGGS screen. Studio `screen_capture` only. Game view 1140 x 785 (ScreenGui 1140 x 727).

| Item | Before | After | What changed |
| --- | --- | --- | --- |
| 1 Tell us! on the egg counter | before-01-tell-us-over-eggs.jpg | after-01-tell-us-above-eggs.jpg | the purple button no longer covers "EGGS 0", it sits straight above the egg plate (8 px gap); the Studio-only FOOD line moved above it |
| 2 My dinos card, SHINY and BIG | before-02-my-dinos-pills.jpg | after-02-my-dinos-pills.jpg | the 14 px pills sit in a row under the thumbnail, the dino is not covered |

Not seen on screen: phone and tablet layouts (offline layout checks only: tools/verify_movement_mobile.py, tools/verify_phone_scale.py), the GoalsPanel header on a real 0.6 goal-line scale, the hub beam cap on a phone (client rule, offline model). No phone measurement (BD-085).
