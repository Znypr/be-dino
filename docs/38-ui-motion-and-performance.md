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
