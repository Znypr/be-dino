# Hatch and leaderboard acceptance evidence

2026-10-08, unpublished BeDino-VisualUpgrade.rbxlx, Build redesign-019,
Studio ID 4aa9faee-9d45-4ff3-8780-e046093db182, PlaceId=GameId=0.
Published newbuild instance was not modified. Profiles/leaderboards used memory.

## Recorded results

Desktop Average Laptop viewport 1365x768. Phone iPhone 17 Pro viewport 750x381,
LandscapeSensor. Captures are tool-scaled images; target sizes were measured in
the live client, not inferred from screenshot pixels.

- Desktop: Compy -> Triceratops -> T-Rex, 5.100 / 5.067 second claim spacing.
- Phone automatic post-run: Raptor -> Stegosaurus -> Ankylosaurus,
  5.059 / 5.066 second claim spacing after sanctuary respawn.
- Final phone X 45.715 square before hover; Next/Collection 174.154 x 44.627.
- BIG: scale 1 -> 1.3, collider 3.38 x 2.4 x 4.16; no world Shiny flag/effect.
- Shiny-only reveal visibly shows SHINY without BIG; stacked egg/dino badges and
  event perk labels also captured.
- Close during first reveal: two eggs remained after six seconds, no further claims.
- Boards: rarity Legendary and real local playtime populated; Robux remains 0 and
  board shows no ranked players. No fake spent totals were inserted into Studio.
- Final console: Build019 ready, no game script error. Earlier startup briefly
  emitted a WaitForChild warning during asset import; not reproduced on final runs.
  MCP camera-restoration diagnostics are tool messages, not game errors.

## Fixture boundaries

Disposable scripts temporarily replaced RewardMath's species roll and EggTraits'
trait roll, then restored both immediately after real settlement. Actual server
run lifecycle, profile transactions, remote claims, queue refill and client animation
ran normally. Fixtures deliberately guarantee rare/stacked outcomes; screenshots
do not measure natural odds. Offline exhaustive roll grids verify configured odds.
Extra LocalScripts held screenshot cameras only. Stop removed all fixtures.

Initial desktop-first-egg capture exposed the respawn timing bug and shows results,
not a passed automatic hatch. It is retained as diagnosis; final phone automatic
captures verify the fix. Early board captures show small type/refresh delay. Final
board captures verify enlarged titles/rows and actual populated preview rankings.

screenshots.json contains generated dimensions/SHA256. runtime-observations.json
contains measured tool results. Studio ended stopped with the default viewport;
latest source was synced, and the repository-generated rbxlx is the saved artifact.
Studio MCP exposes no save-place tool, so no claim of saving its local editor file.

Pending: real products/purchases, global OrderedDataStore ranking, persistent
migration/rejoin, physical devices, multiplayer/max-size BIG physics and final art.
