# BD-043 UI motion and responsiveness

Status: Review / test. The canonical tracker is docs/07-kanban.md.

This branch isolates presentation changes from concurrent shop/genetics changes.
Merge alongside those changes rather than replacing their client files.

Implemented: cancellable tweens, mouse/touch/controller feedback and highlights,
modal/content/toast transitions, meter fills, hatch rarity outline/pop, currency
counters/gain feedback, active tabs, processing/equip messages, startup stages
and fade after character/UI readiness, cached JSON/coalesced refreshes, mobile
crystal HUD scaling, 30Hz camera orbit and 20Hz glints with visibility gating.
Existing egg wobble/cracks/confetti and server transaction outcomes remain.
Runtime mesh geometry already uses cached templates; whole-view pooling is
deferred until measurements justify added lifecycle complexity.

Validation: all 57 current local Luau sources compile; six-species and imported
preview bounds pass four aspect ratios. Isolated branch files compile too.
Syntax/framing checks are not runtime, type-analysis or FPS evidence.

Acceptance still needed: choose Studio target; rapid modal interruption; mouse,
touch and controller input; reduced effects; hatch closure; load failures and
main-UI-ready transition; delayed/error purchases and repeated rewards; physical
phone safe areas and 44px target audit; frame time/memory and connection counts
after repeated panel navigation. No Studio deployment or persistent-data test
was performed in this pass.

## Studio acceptance, 2026-10-08

Selected BeDino-Latest.rbxlx (65d0a77a-6006-4d4c-80b3-4fa62fce67cc),
verified GameId/PlaceId 0. Backed up existing scripts locally, then synchronized
57 current scripts needed by the older file. Studio uses in-memory unsaved profiles.
Other agents' local shop/genetics source is present in that Studio test but excluded
from this UI-only PR. A concurrent GeneTextures module appeared later and was
not included in the tested snapshot. The window was left stopped in Edit mode.

Passed: startup Ready/character gate and loading dismissal; seven menus with
correct active marker and settled modal position/scale; 8 reduced-effects and
10 normal-effects close/reopen cycles; settings OFF zero blur / ON blur 8;
hidden preview camera pause/resume; tween replacement and immediate reduced
effects probe; real UI egg purchase and claim (1x raptor); rarity outline/pop
and confetti; wallet initial text and animated intermediate/exact final values.
Keyboard Return selection drove UI; an injected ButtonA did not activate.
Final console contains only the build-ready message.

Fixed during acceptance: wallet initially stayed at 0 because NumberValue was
initialized before the Changed listener; explicitly set initial text. Bounded
texture density reduced collection descendants 3752 -> 1974 in the same
750x323 touch-emulator layout. This is an instance reduction, not FPS evidence.

Evidence: docs/evidence/2026-10-08-ui-motion/runtime-observations.json and
phone-final.png. The counter fixture changed only a client attribute and restored
it; it was not a server currency grant. Purchased/claimed eggs used disposable
preview memory and vanished on restart. No published player data was accessed.

Still open: physical touch/controller activation, device safe areas, FPS/memory
and connection profiling, loading-failure/slow-server transitions, delayed/error
shop results, early-close hatch regression and integration of all concurrent work.

## Premium hatch correction after owner feedback

The former hatch used EggPreview sphere/spot primitives and three 2D rectangle
cracks. It did not use the premium Blender egg. The old navigation image was
103460376747474, independently bound from the hatch.

Now HatchPresentation uses matched 512px RGBA normal-shell and branching-crack
exports from Premium_Egg/Blank_Egg_Conditions, preserving the shared full camera
canvas. Uploaded shell 95856282289615 and cracks 126956807167774 both have verified
Creator.Id 7285577648. The navigation binding also uses this shell, sized to
compensate for its transparent margins. Source PNGs/checksums are retained in
resources/ui/v2/icons/premium-egg-bindings.json.

Cracks fade onto the shared egg layer, stay attached during shake/squash, and
two cropped shell halves separate/rotate/fade over 240ms during reveal. With
effects off, motion is removed and reveal resolves immediately. No reward
outcomes or server claim timing are changed. Hatch genes tint the image when
the concurrently developed genetics module is installed; baseline remains valid.

Actual Studio UI buy/claim yielded 2x raptor, emptied the queue, and rendered
the premium crack layers (premium-cracks.png). The new navigation ImageLabel
IsLoaded=true; console only build-ready. All 60 current sources compile and
generated icon bindings check passes. This is owner Studio evidence, not
published non-owner access or final owner art approval.

Integration: keep the existing local genes variable and pass it into
HatchPresentation.add when merging with shop/genetics changes. Do not restore
the former rectangle fracture loop.
