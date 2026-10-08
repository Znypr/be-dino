# BD-043 UI motion and responsiveness

> **HISTORICAL branch-specific BD-043 test snapshot.** This document's `Status: Review / test` below records its original branch review and may disagree with the **current canonical Kanban** (BD-043: In progress). Build 020 merged UI-motion work into main; consult [main integration](44-main-integration-checklist.md) and [Kanban](07-kanban.md) for active status. The tests below retain their original bounded evidence.

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

## Hatch v3: stronger breaking/reveal

Three crack regions grow from the impact point at 0.68/1.48/2.28 seconds,
with escalating damped shakes. A 2.75-3.12s still beat precedes release at
3.4s. Seven shared-edge jagged polygons crop the existing shell artwork; the
top cap moves first, then pieces rotate/fall/fade over 0.72s. CanvasGroup
flattening, zero image borders and source-pixel guard overlap remove phone
crop seams. At most 217 temporary crops are used; grouped alpha updates run
at 30Hz and cleanup disconnects flight. Reduced motion builds no fragments.

A rarity-colored halo/ring and eight rays accompany successful reveal; confetti
waits 180ms. Existing five-second total timing and server outcomes are unchanged.
Cracked failure uses break but suppresses success chime/rays/confetti. When merging
with local genetics code retain splitEgg(not failed), not baseline splitEgg(true).

Loaded sound assets: ProSoundEffects shell crunch 9120490790 (taps pitched up,
full crunch on release) and soft reveal chime 9116394545. Separate SOUND ON/OFF
setting tested in actual UI. Asset provenance is in premium-egg-bindings.json.
Auditory quality and published non-owner permission still need owner review.

Studio trace shows progressive crack heights, seven visible fragments at
3.56/3.86s and none by 4.31s; all sound instances loaded. Success and failed
Cracked claims were exercised on disposable preview profiles. Early-close and
reduced-motion helper probes pass. All 61 current sources compile; fragment
coverage/budget harness and six-species framing harness pass.

An imported mesh download failure left blank discoveries even after preloading.
DinosaurPreview now uses the uploaded model's actual asset thumbnail when those
mesh fetches fail. The Compy fallback IsLoaded=true and is visible in the real
claim screenshot. It is a static base-model thumbnail; it does not reproduce
genotype/fusion colors or orbit. Full 3D asset access remains an open issue.

Evidence: hatch-v3-observations.json, hatch-v3-fragments.png (visual-only helper
probe, no server claim) and hatch-v3-discovery.png (actual Compy purchase/claim).
This is implementation evidence, not a subjective 8/10 rating, physical-phone
FPS measurement, or blanket integration acceptance for concurrent work.
