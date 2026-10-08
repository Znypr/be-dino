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
