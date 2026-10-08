# Main Integration Evidence

2026-10-08. Tested source snapshot `1799536`, Build 020, then UTF-8-corrected sync.
Target: BeDino-019-DisposableAcceptance.rbxlx,
`e3eb431e-61b3-4f56-a5d6-d8dcb40576af`, GameId=PlaceId=0.
The old filename does not represent its new synced Build 020 source.

ProfileState Loaded; ProfileMode Studio preview (not saved); 22 configured species.
Both paid flags false. No real charge, live profile change or experience publication.
Old scripts preserved in ServerStorage.BeDinoPreMainIntegrationBackup, with executable
scripts disabled. Runtime probes were temporary and Play was stopped after testing.

## Screenshots

- `final-outcomes.png`: actual GUI shop/odds/Details navigation, tier 0, 16% aggregate
  failure, 37,683,361 final outcomes, rounding notice and nonzero individual odds.
- `next-tier-outcomes.png`: actual condition-confirmation/odds/Details navigation,
  tier 1, 13.6% failure; the profile still has conditionLevel=0.
- `empty-queue-paid-gate.png`: empty queue after attempted purchase. A separate
  response observer recorded ok=false, random_items_unavailable. Not a paid hatch.
- `earned-egg-hatch.png`: actual automatic claim/reveal after a disposable server
  settlement fixture: 1x Compy, Normal, Cream/Blue 53/47, round-spots pattern,
  hatchSuccess=true, queue empty. It is not a complete real run/persistence result.

All screenshots are actual MCP widget captures at 583x784. Visible Details labels
reported TextFits=true. No desktop/phone emulator or physical-phone claim is made.

## Verification And Diagnostics

226 sources compiled; ten offline Luau checks passed; 37 Python tests pass on the
isolated committed tree including UTF-8 sync regression. This isolates the tested
integration from concurrent, uncommitted egg-nest work.

The first sync used the tool's Windows default decoding, producing mojibake in the
client. Explicit UTF-8 and line-ending normalization corrected it before capture.
One >200k source assignment exceeded Studio's setter limit; exact matching source
was retained and the remaining batches verified. All 226 source rows were covered.

Console had the normal redesign-020 readiness message. Diagnostics also recorded
an MCP-command call to a nonexistent repository getter, a no-visible-button command
after automatic hatching began, and self-destruction warnings from temporary probe
scripts. These are test-command/probe errors, not claimed gameplay errors or a
clean-console certification. Direct MCP require probes do not share the running
repository's module context; the actual settlement fixture ran as a server Script.

FocusLost helper page clamping passed. Keyboard text injection itself did not
update the page input; real typed page interaction remains unchecked.

See [the maintained integration checklist](../../44-main-integration-checklist.md).
