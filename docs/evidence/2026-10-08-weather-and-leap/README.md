# Illustrated leap and weather verification

2026-10-08, branch `redesign/resources-and-core-fixes`, continued from `6831ffd`.
Followed `resources/ui/v2/icons/weather-and-leap-handoff.md`.

## Scope and owner

Only connected Studio: `BeDino-019-DisposableAcceptance.rbxlx`, ID
`83a530b4-df1c-44ca-b216-3367e97119c0`. Config.Build=redesign-019,
PlaceId=0, GameId=0, ProfileMode="Studio preview (not saved)".
The original published instance was not connected. Published place 111259822927673
GetProductInfo reports User znyprs / 7285577648, matching recorded experience
10769812255 owner. All five new uploads report that same creator and AssetTypeId=1.

| Key | Master | Actual asset ID | Centered scale |
|---|---|---|---|
| leap | leap-v1.png | 137570028242707 | .80 |
| weather | weather-clear-v1.png | 115952370461269 | .84 |
| rain | weather-rain-v1.png | 72440937569305 | .84 |
| thunder | weather-thunder-v1.png | 135005203451565 | .84 |
| blizzard | weather-blizzard-v1.png | 83461127038303 | .84 |

The seven existing bindings remain unchanged. No source PNG was edited.

## Screenshot matrix

| State | Desktop | Phone |
|---|---|---|
| Clear/default | [Clear](desktop-clear.png) | [Clear](phone-clear.png) |
| Rain | [Rain](desktop-rain.png) | [Rain](phone-rain.png) |
| Thunderstorm | [Thunderstorm](desktop-thunder.png) | [Thunderstorm](phone-thunder.png) |
| Blizzard | [Blizzard](desktop-blizzard.png) | [Blizzard](phone-blizzard.png) |
| Leap ready | Visible in all desktop weather captures | [Ready after expiry](phone-leap-ready.png) |
| Leap cooldown | [Actual E leap](desktop-leap-cooldown.png) | Visible in all phone weather captures |

[48px and 64px inspection](desktop-48-64.png): top row uses 48px logical slots;
bottom uses 64px. Left-to-right: Leap, Clear, Rain, Thunderstorm, Blizzard.
This temporary engine-rendered probe was removed before stopping play.
MCP capture IDs use `019-weather-desktop-<state>` / `019-weather-phone-<state>`,
`019-desktop-leap-cooldown`, `019-phone-leap-ready` and `019-weather-leap-48-64`.

Desktop viewport 1263x772, GUI 1263x714. iPhone 17 Pro preset 874x402,
landscape viewport 750x381, GUI 750x323. Game is LandscapeSensor;
GUI uses CoreUISafeInsets and ClipToDeviceSafeArea=true. Portrait is unsupported.
PNG capture framing is Studio-scaled on phone, not a physical-device photograph.

## Observations and traces

All five ImageLabels report IsLoaded=true in their desktop and phone HUD states.
Desktop slots scale from logical 48px to 46.32px, with leap image 37.056px and
weather image 38.909px. Phone slots are 35.2px, leap 28.16px and weather 29.568px.
The insets leave visible space around tight master edges. No clipping, opaque
alpha rectangle, conspicuous edge fringe or overlap with labels was observed.
Sun, drops, bolt and snowflake remain distinguishable; the full-body leap is
readable, with tiny detail appropriately reduced on phone.

After normal EXPLORE ISLAND activation and E input, the server reported Active,
LastLeapStatus=leaping, cooldown approximately 59.17 seconds. Desktop showed
LEAP 1:00 and muted button color. Phone showed the decreasing cooldown, then
LEAP [E] / READY and blue after natural 60-second expiry, without clock edits.
This verifies ready/cooldown artwork and live timer behavior, not physical touch.

`runtime-traces.json` archives per-capture live IDs, loaded flags, dimensions,
weather attributes and timer labels. Toast labels may remain in hidden GUI
instances; screenshots show the actual visible HUD.

Weather states were set through server Workspace attributes only in the unpublished
session, with 180-second end/600-second next timestamps. Existing client particle
effects responded too. This does not certify random scheduling or weather bonuses.
No fixture scripts, profile grants or gameplay changes were added to source/Edit.

Empty-binding fallback probes used the actual UITheme renderer for all five keys,
temporarily clearing/restoring only the client in-memory mapping. Each produced
native Frames and zero ImageLabels: leap 8 children, weather 10, rain/thunder/
blizzard 11 each. Native utility symbols and layered navigation remain intact.

Console contains only `[Be Dino] redesign-019 ready. Resource redesign.`
Play stopped, default viewport restored, temporary runtime attributes/probe discarded.
Upload HTTP helper stopped. Persistent player data was untouched; nothing published.

## Validation and remaining gates

45 Luau sources compile with pinned 0.741; artwork assembly and both binding checks
pass. Build 019 rebuilt. 25 Python tests pass, covering strict missing/duplicate/
invalid keys and IDs, empty mappings, deterministic source round-trip and the five
unchanged masters' full RGBA decode/alpha/SHA-256. The prior seven-icon count
assertion was updated to twelve.

Non-owner published asset permissions/moderation, actual phone touch/performance,
multiplayer and persistent rejoin remain unverified. This local artwork pass does
not close those release gates or authorize publishing.
