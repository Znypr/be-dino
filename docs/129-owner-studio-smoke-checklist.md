# 129 Owner Studio smoke checklist before friends session 1 (written 2026-10-16)

Label: **OWNER CHECK LIST**. Everything below passed offline checks only; nobody has looked at or listened to it in Studio. Source: [125 go / no-go](125-friends-playtest-go-no-go.md) (PR #254), [114 handbook](114-handbook.md) (vibe words, section 0), [07 kanban](07-kanban.md). Peaceful is excluded (being removed). Golden Drumstick (BD-207) is flag off: skip.

**How to use:** play the playtest build in Studio (desktop) top to bottom; tick each line. **BLOCKS** = fix or switch off before inviting friends (session 1). **NICE** = look when you have time; does not block.
**Vibe check for every line:** does it feel polished, satisfying, calm, bubbly, friendly, vibrant? (Overall feel, not a literal rule: a dim cave can still be colourful.)
**How to report a problem:** one line in chat: `<BD id> <place> <what you saw>` plus a screenshot if you can, for example `BD-292 cave sign: text blurry at the potion station`. Say "heard" or "unheard" for sounds. If the in-game Feedback button exists in your build (see 12), use it instead.

Cave items: the owner put the cave hub in session 1 (2026-10-16), so `CaveHub` is ON in the playtest profile (PR #254, docs/125) and the cave checks below BLOCK session 1. Items marked (open PR) are not on main yet; check them once merged.

## 1. Sanctuary / hub (first screen)
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-377, BD-365..368 | Welcome card, run-start hint, first-run copy | Short kid words, no "5m 0s", nothing clipped, first egg arrives in about 60 s | BLOCKS |
| BD-389 | Sanctuary dino after hatching a new species | Low-poly dino, not the old blocky one | BLOCKS |
| BD-390 | Any menu text and pickup numbers (+0.6) | Light fill with dark outline, readable on busy backgrounds | BLOCKS |
| BD-422 | Get eaten on purpose, check the egg count | You keep your eggs; copy says so | BLOCKS |

## 2. Cave (on in the playtest build; owner 2026-10-16)
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| #251 cave cosy pass (BD-293 family) | Show-off pedestal height | The dino stands ON the pedestal top, feet touching, not sunk or floating; camera sees the whole dino | BLOCKS |
| #251 | Lamp flicker | A slow, soft warm breathing glow; never strobing, never a hard on/off; Reduce Motion stops it | BLOCKS |
| BD-292 | Signs (stations, potions, fusion) | Text readable from 10 studs away in the dim light, self-lit, no blur | BLOCKS |
| BD-399, BD-383, BD-398 | Overall light, then wait for weather | Dim, lamp-lit, still colourful (amber crystals, warm props); no rain, snow or storm effects inside | BLOCKS |
| BD-382 | Open one station, tap another rail button | One tap travels; no two-click dead end | BLOCKS |
| BD-401, BD-400 | Crystals in shops and HUD | Amber / yellow, never blue-purple in a shop | NICE |

## 3. Run start
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-366 | Press play, start a run | Run begins fast, camera smooth, no panic copy | BLOCKS |
| BD-396 | "Follow the glow" guide | Soft green sparkle trail you notice in daylight, points to the station | NICE |

## 4. Food field
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-386 | Eat 10 food, watch size | Dino grows slowly (about 5x slower than before), size bar moves visibly | BLOCKS |
| BD-387, BD-167 | Food density and look | Plenty of food in each biome, readable, no floating food; frame rate steady | BLOCKS |
| BD-395, BD-416, BD-417 | Trees, rocks, bushes on slopes | Bottoms touch the ground; nothing sunk or floating | NICE |
| BD-388 | Low-poly dino walking | Eyes and nostrils stay fixed on the head; only legs, tail and a small head peck move | BLOCKS |
| BD-418 | Stopwatch a 5-minute run | About 15 eggs on the EGGS plate (write the number down) | BLOCKS |

## 5. Egg reveal party (after the run)
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-044, #260 hatch ladder (open PR) | Reveal ORDER of a 12 to 15 egg batch | One egg at a time, ordinary first and rarer later (rising excitement), 1 s each, Skip all works | BLOCKS |
| BD-397 hatch v2 | Hatch animation (flag off: skip unless you turn `HatchV2` on) | Paint-bucket coats, crack, burst; calm, no flash | NICE |
| BD-162 | Mutation hatch | Soft burst and calm loop, nothing harsh | NICE |
| BD-420 | Earn extra nests (long run) | Nests beyond five spots turn into crystals with a toast "Nests full!" | NICE |
| BD-365 | First two eggs | Never Cracked; Cracked later reads gentle and funny | BLOCKS |

## 6. Rare hatch
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-428 (merged #243) | Hatch a Legendary, Shiny or mutation (use the test grant in Studio) | Banner and confetti when the reveal lands, warm `shiny_bang` sound, another player sees one short banner; not spammy | BLOCKS for session 2, NICE for session 1 |
| BD-428 | Reduce Motion / Effects Off | Banner and sound, no confetti | NICE |

## 7. Shops
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-430 (PR #259 label) | Egg odds wording in Buy Egg and Conditions shop | Says "Cracked is X%" separately from "hatches Y%"; no jargon; numbers match the config | BLOCKS |
| BD-430 | Crystals tab packs | Each pack button shows its price ("R$ 45") when Roblox knows it, "Price soon" when it does not (packs off: "Coming soon!" above); never "..." or a cut-off label | BLOCKS |
| BD-393 | Aura and Trail shop headers | "For: <your dino>" shown | NICE |
| BD-394 | Conditions shop eggs | Large, readable condition eggs | NICE |
| BD-405, BD-391 | Fast travel perk in Crystal Shop (flag off) | Skip unless you turn `FastTravelPerk` on | NICE |

## 8. Settings
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-081 | Settings > Sound | Sliders work; volume never loud or sharp | BLOCKS |
| Effects / Reduce Motion | Toggle both | Goals and FX switch to calm static versions | NICE |

## 9. Goals panel
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-427 (merged #245; #248 species / colours / patterns / mutations) | Hub Goals panel | Three goal lines (collect, favourite to Diamond, play new dinos), progress counts that match what you own, short kid copy, fits on one screen | BLOCKS |

## 10. Class picker and dino page
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-423, #250 (open PR) | Dino page class line and picker | One short class line under the species name (Ground / Fly / Water / Armored) plus a feel hint; no overlap with stats or buttons; every owned dino can be equipped | NICE for session 1 (class movement is effectively off) |
| BD-246 | Fly glide, Water dash | Only if `ClassMovementEnabled` is on: smooth, not twitchy | NICE |

## 11. Sound Lab (Settings > Sound > SOUND LAB)
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| BD-081, BD-343 | Press PLAY on each cue, list is grouped by category | Soft, round, short, no harsh highs; hatch rarity sting is not doubled; mark each "keep" or "change" | NICE (sounds are all unheard, but any harsh one BLOCKS) |

## 12. Feedback button (#261, open PR)
| BD | Look at | Good looks like | Level |
| --- | --- | --- | --- |
| #261 / [128](128-playtest-feedback.md) | Small Feedback button in the hub | Easy to find, 44 px or bigger, opens a short friendly form, sends without lag; friends can use it | BLOCKS only if you want friends to report from inside the game |

## Result
Write the date, build, and tick count in the release record ([55](55-playtest-release-runbook.md)). Any BLOCKS line that fails: say so in chat and we switch the feature off or fix before the session. Anything you did not look at stays "not verified" in the kanban.
