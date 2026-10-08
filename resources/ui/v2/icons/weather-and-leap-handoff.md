# Illustrated leap and weather integration

Generated sources, 2026-10-08. Integration follow-up: all five now have verified
owner uploads in `upload-bindings.json` and generated runtime bindings. Desktop,
phone-emulator and 48/64px evidence is archived in
`docs/evidence/2026-10-08-weather-and-leap/`. The original instructions below
describe the completed integration path; manifest draft statuses record generation
history. Empty bindings still use native symbols. Canonical status is in
`docs/07-kanban.md`; style rules are in `docs/32-artwork-guide-and-todo.md`.

| Master | Runtime icon key | Runtime state | Starting centered image scale |
|---|---|---|---|
| leap-v1.png | leap | Leap ready/cooldown | 0.80 |
| weather-clear-v1.png | weather | clear/default | 0.84 |
| weather-rain-v1.png | rain | rain | 0.84 |
| weather-thunder-v1.png | thunder | thunder | 0.84 |
| weather-blizzard-v1.png | blizzard | blizzard | 0.84 |

Each master has a sibling `.manifest.json` containing its exact generation prompt,
style reference, SHA-256, dimensions and review limitations. The PNGs preserve genuine
alpha. Generated safe margins are tighter than requested; the scales above are
starting layout values, not a Studio-verified acceptance result. Keep source masters
unchanged; use editable shared layout to inset the ImageLabel. Inspect transparent
edge fringe, silhouette and label spacing at the actual 48px HUD size and 64px.
The leap illustration depicts an ability, not an additional playable species.

## Local Codex with Studio MCP

1. Pull the current `redesign/resources-and-core-fixes` branch, preserving local work.
2. Read the canonical checklist, handoff and each manifest. Check the connected
   Studio instance and experience owner before uploading.
3. Upload the five PNGs through MCP under the verified experience owner. Record
   actual image IDs and owner/loading evidence in `icons/upload-bindings.json`.
4. Extend `tools/bind_ui_icons.py`: it currently enforces exactly the original
   seven keys. Accept the original keys plus `leap`, `weather`, `rain`, `thunder`,
   `blizzard`, retaining duplicate/invalid-key and image-ID validation. Regenerate
   `UIIconAssets.luau`; preserve existing seven uploads.
5. Keep these logical keys compatible with existing calls in `Bootstrap.client.luau`.
   Clear maps to `weather`. Do not add a competing `clear` icon key or new gameplay
   weather state. Apply configurable per-icon image inset in the shared renderer,
   leaving native fallbacks and utility symbols intact.
6. Verify each actual ImageLabel loads, and inspect all four weather states plus
   leap ready/cooldown on desktop and phone emulator. Use a separate unpublished
   disposable copy for fixtures; leave persistent data untouched. Keep timers,
   E key, text and effects as live UI, never baked into PNGs.
7. Archive screenshots/runtime evidence, run the existing binding/compilation and
   relevant verification checks, regenerate the current build and update status.
   Generated, uploaded, integrated and Studio verified are distinct stages.

Real-phone touch/performance, multiplayer, persistent rejoin and non-owner
published image loading remain separate acceptance gates. This artwork handoff
does not certify them or authorize publishing the experience.
