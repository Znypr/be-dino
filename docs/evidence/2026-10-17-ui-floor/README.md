# UI floor sweep (BD-501): before / after, desktop Studio play

Playtest build (`python tools/build.py --profile playtest`) opened in its own Studio window, game view 1156 x 841 (desktop, not compact).
Eggs and dinos came from the dev-only `DemoTrigger` hatch party in a private local copy of the build (the demo flag is off in every committed build and was not changed in the repo).
Screens are captured with Studio `screen_capture` only.

| Screen | Before | After | What changed |
| --- | --- | --- | --- |
| Potion Shop cards | before-01 | after-01 | Buy 30 to 44 px, card text re-stacked in the same 132 px card |
| Potion Shop, your potions | before-02 | after-02 | USE 40 to 44 px, 50 px row pitch |
| Shop, Crystals tab | before-03 | after-03 | pack Buy 38 to 44 px, price text min 12 to 14 |
| Goal line + Goals header | before-04 | (after-13) | header 30 to 44 px |
| Goals panel open | before-13 | after-13 | panel 14 px taller, rows kept |
| Goal line, longest copy | before-14 | after-14 | min 1 to 14, wraps to two 14 px lines |
| Eggs screen | before-05 | after-05 | chip min 10 to 14 (copy already larger) |
| Hatch: paint chips | before-06, before-09 | after-06, after-09 | chip names min 12 to 14, LEGENDARY badge 82 to 94 px |
| Hatch: result | before-07 | after-07 | tap hint min 12 to 14 |
| Hatch: ribbons | before-08 | after-08 | ribbon min 10 to 14 |
| My dinos (Compy) | before-10 | after-10 | pills 14 px, "No egg" 11 to 14 px |
| My dinos (SHINY + BIG) | before-11 | after-11 | ribbons no longer overlap the stage pill |
| My dinos (mutation) | before-12 | after-12 | same |

Not seen on screen: Fast travel perk button (flag off), legacy Fusion buttons (unreachable in the playtest profile), phone layouts.
