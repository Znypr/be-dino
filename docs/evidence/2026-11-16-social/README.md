# 2026-11-16 social, retention and ambience (BD-1227, BD-1228, BD-1229, BD-1233, BD-1225)

Place: `build/BeDino-social2-playtest.rbxlx`, built with `python tools/build.py --profile playtest` from branch `claude/bd-social-retention-79df88`
(not committed: generated build). Opened in its own Studio window (never the owner's Place1). Solo Play in Studio: Roblox Studio cannot start a
second real Roblox account from the MCP, so the two-player parts (news seen by another player, the friend check) are proven offline only.
Label: **CURRENT BUILD BEHAVIOR of the playtest profile**; the default build is unchanged (all five flags false, pinned by `tools/release_profiles.py`).

## What was checked in Studio

| Row | Check | Result |
| --- | --- | --- |
| all | `Config` flags in the playtest build | RareHatchNews, FriendBonus, Badges, Codes, ZoneAmbience, WorldV3 all `true` |
| BD-1233 | real `CodeAction` remote from the client | wrong code -> "That code is not right."; ` be-dino ` -> "You got 50 crystals!" (+50 exactly); again -> "You used this code already."; group chest -> "No group yet." (GameGroupId 0); 60 x `<` -> wrong; `HATCH` with a forged `crystals = 99999` -> +25 only; two tries inside 1.5 s -> "Try again soon." |
| BD-1225 | five zone loops | every id `IsLoaded`, creator ProSoundEffects (GetProductInfo), lengths 70.8 / 56.0 / 40.2 / 33.1 / 76.8 s; all five on `BeDinoAmbience`; moving the dino from the plaza into the forest crossfaded volcano 0.10 -> forest 0.16 within 4 s. The plaza first read as "volcano" (sector border at the centre): fixed, the plaza is now the meadow (offline test) |
| BD-1227 | news banner and chat line | see the pictures below (drawn on the client from a real payload shape; a second player was not available) |
| BD-1228 | friend chip | look only (see below); the IsFriendsWith path needs two real accounts that are friends |
| BD-1229 | badges | every id 0 -> nothing awarded (by design until the owner creates them) |

Measured, not heard: nobody listened to the loops (docs/87: the owner judges by ear).

## Badges to create (OWNER, Creator Hub > Be Dino! > Associated Items > Badges)

Creating a badge is an account action, so no agent did it. After creating each one, paste its id into `src/shared/BadgeTable.luau` (`B.Ids`).
Icons: 512 x 512 round badge pictures, best made in Blender or by the owner (docs/72 art rule); suggestions below.

| Key | Name | Description | Icon idea |
| --- | --- | --- | --- |
| welcome | Welcome to Be Dino! | You joined the dino island. | the green Compy waving on the round island |
| first_hatch | First Hatch | You hatched your first dino! | a cracked spotted egg with a baby dino peeking out |
| first_rare | Rare Find | You hatched a Rare dino! | a blue-glow egg with one star |
| first_epic | Epic Find | You hatched an Epic dino! | a purple-glow egg with two stars |
| first_legendary | Legendary! | You hatched a Legendary dino! | a gold-glow egg with a crown |
| first_shiny | Shiny! | You hatched a Shiny dino! | a sparkling dino head with star glints |
| first_mutant | Mutant! | You hatched a dino with a weather mutation! | a dino head with a little frost or ember swirl |
| index_5 | Dino Spotter | 5 kinds of dino in your Index. | an open Index book with a "5" tab |
| index_10 | Dino Expert | 10 kinds of dino in your Index. | the Index book with a "10" tab and a magnifier |
| index_all | Dino Master | Every kind of dino in your Index! | the Index book with a gold trophy |

## Still needs the owner

1. **Create the 10 badges** above and send the ids (or paste them into `B.Ids`).
2. **The game's Roblox group id** for the group gift chest (`Config.GameGroupId`, 0 now: the chest stays hidden until it is set).
3. **Listen** to the five zone loops in the playtest (Weather slider controls them).

## Pictures (Studio, playtest build, 1914 x 793 viewport)

- `news-banner-friend-chip.jpg` (copy `review-2026-10-17/580-social-news-banner-friend-chip.jpg`): the news banner "RARE FIND! / Mia hatched a **Legendary** T-Rex!" drawn by `RareFindBanner.show(..., news = true)` from a payload of the server's shape, and the friend chip forced visible to show its look (solo test: no friend in the server). Known, not from this change: the banner sits over the size bar and goal line (BD-1121 position `Banner.Y = 118`); left as it is (the HUD belongs to the UI session), reported as a follow-up.
- `codes-panel.jpg` (copy `581-social-codes-panel.jpg`): the Codes button under the friend chip and the Gifts panel after a real `BEDINO` redeem through the remote ("You got 50 crystals!", crystals 1,000,000 -> 1,000,050 on the Studio test wallet). The button was forced visible for the picture (it shows between runs; the starter run was active). The empty space under the code box is gone after this picture: with no group id the panel is now 200 px tall.
