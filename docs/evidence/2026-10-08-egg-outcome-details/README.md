# Final Egg Outcome Details, 2026-10-08

## Scope

Build 019 adds a lazy, configurable final-outcome catalog and pre-purchase Details
view. It includes aggregate failure, species, copies, condition, color genes/share,
pattern, size and numerical unconditional probability. Purchased eggs have no
Shiny or event mutation. Next-tier condition confirmation links use next-tier odds.
Filters never renormalize probabilities. Both paid release flags remain false.

## Captured Studio Evidence

Unpublished owner copy `BeDino-VisualUpgrade.rbxlx`, instance
`4aa9faee-9d45-4ff3-8780-e046093db182`, GameId/PlaceId 0, redesign-019.
Disposable Studio profile; no persistent player data or real purchase used.

- `outcomes-owner-initial.png`: first functional iteration; small footer controls
  were subsequently enlarged.
- `outcomes-black-black.png`: updated actual owner-widget capture, 583x763 viewport.
  AURAS > EGGS > VIEW ODDS > FINAL OUTCOME DETAILS and both Black filters were
  activated through GUI selection/keyboard input. The filtered legacy catalog has
  18,180 entries; displayed examples show 0.000000000099802%, not rounded zero.
  Visible TextLabels reported TextFits=true. Final console contained the normal
  redesign-019 readiness message and no errors.

These are widget screenshots, not a new desktop/phone-emulator certification.
After context resumed the old Studio session was gone; the sole connected instance
reported "Place is not open". Final rounding notice, rounded-up touch heights and
variable-height factor rows were therefore not resynced or visually retested.

## Offline Verification

An isolated Git baseline plus only these outcome changes was built, avoiding
the concurrent uncommitted 22-creature/visual upgrade. Build019 contains 63 scripts.

- 63 Luau sources compiled successfully with Luau 0.741.
- All 33 Python tests passed after rebuilding the generated delivery.
- Gameplay, progression, egg genetics, preview and artwork execution checks passed.
- Product bindings check passed; receipt/payment/release gates unchanged.
- `verify_outcomes.py`: sums every final outcome to 100% before rounding; verifies
  actual generator share probabilities, all seven upgrade tiers, filtered sums,
  boundary indices, rare precision and legacy/explicit-uniform compatibility.
- The same outcome check also passed against the current uncommitted 22-species,
  eight-pattern configuration, including its clamped endpoint distribution. That
  integration is not included in this isolated Build019 or this Studio evidence.

## Still Open

- Retest final UI, page jumping/reset/bounds and next-tier confirmation in Studio.
- Desktop, phone emulator and physical-device layout/interaction acceptance.
- Full paid-random-policy review, restricted-player handling and real receipt tests
  in a controlled private experience before enabling either paid gate.
- Integration with separately developed catalog, pattern and visual changes.
