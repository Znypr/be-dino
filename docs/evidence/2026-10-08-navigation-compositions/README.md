# Shared navigation artwork verification

2026-10-08, continued from `91aac96` on `redesign/resources-and-core-fixes`.

Both connected instances report Config.Build `redesign-019`. Repository sources
were synced in Edit to published `newbuild` (place 111259822927673, experience
10769812255, Studio c91d2e6f-2da9-4457-afa0-4fe028f1a83f) and the separate local
`BeDino-019-DisposableAcceptance.rbxlx` (Studio
83a530b4-df1c-44ca-b216-3367e97119c0, PlaceId=0, GameId=0).
Only the unpublished copy was played. No persistent player data was accessed or
changed, no fixtures were added, and nothing was published to Roblox.

## Captures and observations

- [Desktop](desktop.png): MCP capture `019-shared-navigation-desktop`, viewport
  1263x772. Both shared compositions visible in the vertical rail, about 38.6px
  square after UIScale. No navigation label clipping or icon/label overlap.
- [Phone](phone.png): MCP capture `019-shared-navigation-phone`, iPhone 17 Pro
  landscape preset 874x402, runtime viewport 750x381, ScreenGui 750x323.
  Both compositions visible at 24x24 inside 82x44 buttons in the horizontal rail.
  Icons stay within their slots; labels remain readable and the rail does not
  overlap the joystick. Small detail is intentionally reduced at this size.

The game uses LandscapeSensor, CoreUISafeInsets and ClipToDeviceSafeArea=true.
Portrait is not a supported layout. Phone capture is emulator evidence, not a
real-device touch, physical safe-area or performance certification.

## Engine inspection

In both layouts, navigation `Artwork_aura_meadow` contains two independently
clipped `aura_meadow_ring` ImageLabels (rbxassetid://80049958683098) and one
`fossil_centerpiece` (rbxassetid://86663955990810). Every ImageLabel IsLoaded=true.
`Artwork_potion_speed` contains `potion_speed_base`
(rbxassetid://87695825543059, IsLoaded=true) and a separate `Art_speed` native Frame
with nine geometry children. No flattened image or duplicate upload was made.

Console output: `[Be Dino] redesign-019 ready. Resource redesign.` only.
The initial simulator orientation call while on default desktop returned a tool
error; selecting the phone before its orientation succeeded. This was not a game
runtime error. Play was stopped and simulation reset to default afterward.

## Repository checks and limits

44 Luau sources compile with pinned Luau 0.741; artwork assembly harness passes
shared navigation mapping, empty-binding native fallbacks, rear/front ring clips,
independent centerpiece and both bottle emblems. Both binding generators pass
`--check`; 21 Python tests pass, including deterministic build/source round-trip.
Build 019 is regenerated with the shared mapping module.

Leap and Clear, Rain, Thunderstorm and Blizzard remain native placeholders:
their illustrated PNGs are Todo, separately listed in the artwork guide.
Non-owner published image permissions, real-phone performance/touch and the
remaining release gates in the canonical checklist are not verified by this pass.
