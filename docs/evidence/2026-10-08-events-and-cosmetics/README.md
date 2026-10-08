# Weather, mutations, cosmetics and textured visuals

2026-10-08. Separate unpublished `BeDino-VisualUpgrade.rbxlx`, Studio instance
4aa9faee-9d45-4ff3-8780-e046093db182, Build redesign-019, PlaceId/GameId 0.
The other connected published `newbuild` instance was not modified. Local test
profiles are unsaved and their wallet replenishes; no persistent profiles used.

## Runtime evidence

- Actual UI purchases in the initial session: Meadow aura and Nova trail.
  Final phone UI session also purchased and equipped Royal Nova and Nova Ribbon
  through confirmations. Result attributes show both owned/equipped. Cosmetic
  card actions are 130.62x44.63 px; tabs 87.08x44.63 px in runtime GUI coordinates.
  Final fixtures use real repository purchase/equip actions for Royal/Nova;
  all four return purchased/equipped. These are disposable crystal transactions,
  not Robux purchases or published persistence proof.
- Desktop and phone aura/trail shops, tinted egg queue and all six model
  index previews archived. Wait for mesh content to load before inspection.
  A framing defect in early hatch captures was fixed; hatch screenshots 1-3
  were replaced with correctly framed final captures.
- HATCH NEXT EGG then NEXT EGG twice consumes Ember, Aurora, Blood Moon in
  order. Final rewards: 1x Triceratops Ember, 2x Compy Aurora, 1x Compy Blood
  Moon. Mutation perks appear on each reveal. Both desktop and phone captured.
  Metadata was seeded through the real settlement method in this unsaved
  profile; it is not evidence of natural random catch frequency.
- Clear + Royal + Blood Moon: growth 1.87x, speed 1.12x. Royal alone under
  volcano: growth 2.04x, speed 1x, loot 1.65x; aurora: 2.21x/1.10x/1.50x;
  quake: 1.87x/1x/1.40x; bloodmoon: 1.955x/1.15x/1.75x. Actual server clock
  transitions were forced with a disposable replacement of WeatherClock.step;
  normal server consumers applied lighting/attributes. No production debug
  remote or fixture source was added to the build. Aurora/Blood Moon set 19h,
  volcano 17h, quake 14h. Initial client-only screenshots were replaced by
  server-driven state captures; separate sky views demonstrate moon/aurora.
- Real FoodService pickup: fixture seeds 9 catches and .99 fractional carry,
  begins a run, relocates the rig onto a berry and temporarily forces the server
  mutation roll to zero. FoodService awards 10 catches and RunEggEvents becomes
  `[{"eventId":"volcano","mutationId":"ember"}]`. Production roll restored.
- Reduced-effects test executes in the real LocalScript context: zero enabled
  cosmetic beams/trails/particles/lights and zero enabled weather beams.
  A plugin-context require does not share the running scripts' module state;
  that initial diagnostic was not counted as a passing test.
- Moving Nova ribbon + aura + mutation glow captured. Visual collision stays
  disabled; server movement controller unchanged. FPS/triangle totals unmeasured.
- All six model creators and twelve selected material maps report creator
  target 7285577648, matching experience owner. Models load with 7/7/7/3/7/7
  BaseParts for Compy/Triceratops/T-Rex/Raptor/Stegosaurus/Ankylosaurus.
  Grass/Rock/Wood override names match BeDino_Meadow/Stone/Bark.
- Final console has the Build ready line and Studio assistant camera-reset
  messages, no game-script errors. Earlier protected BaseMaterial startup
  failure was fixed by authoring/packaging variants instead of creating them
  from server code. Earlier generation preview timeouts were tool warnings.
- Imported textures were removed from Gold/Diamond treated clones so they cannot
  mask metal/glass colors. Actual Fusion page previews show gold metal/cyan
  glass with zero retained SurfaceAppearances; screenshots archived. This is
  visual compatibility evidence, not a new successful fusion/persistence test.

## Limits

Desktop: Average Laptop preset, runtime viewport 1365x768. Phone: dynamically
selected iPhone 17 Pro, landscape, runtime 750x381; LandscapeSensor game.
Captures are Studio-scaled previews, not physical-phone measurements. Shop
action/tab targets were enlarged; other modal targets and physical readability
remain unverified. No non-owner permissions, multiplayer performance, persistent
migration or save/rejoin acceptance was attempted, per user deferral.

Native event icons, native trail thumbnails and built-in VFX textures are not
completed illustrated assets. New dinosaur shapes are draft art; original
environment mesh geometry remains because three generation jobs failed.
The requested 500-food/10-egg ratio was treated as an example, not approved
balance. Existing catch thresholds remain unchanged.

Automated verification: 51 Luau sources compile; logic/gameplay/progression,
native/imported preview framing and artwork harnesses pass. Python packaging,
resource/artwork and binding tests: 27 passed after final rebuild. This evidence does
not substitute for the explicitly deferred release checks.

Play stopped and Studio reset to its default viewport. Disposable fixtures and
unsaved profiles disappeared with the stopped sessions.
