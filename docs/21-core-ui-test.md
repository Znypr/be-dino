# Build 011: core UI and first-session guidance

Build 011 validates BD-015 on desktop and Studio's phone landscape emulator. It removes the normal development test controls.

## Player-facing UI

- First-session tutorial appears once per join and explains food, PvP, run banking, collection and Gold.
- Compact HUD shows growth, catches, size and spawn/PvP status.
- Bottom touch-friendly navigation exposes Home, Dinos, Chests and End Run.
- Home gives a compact progression overview.
- Dinos shows exactly one row per species with grouped base/Gold counts, equip and Gold progress/action.
- Chests shows five active slots, countdown/ready state, overflow and one claim action.
- Run summary shows reason, growth, catches and committed reward, then the next run starts automatically.
- Loading/profile failures remain visible instead of silently showing writable blank data.
- All normal Build 008-010 debug grant/setup buttons are disabled.
- Chest timer returns to the planned 60-second private-alpha value.

## Test objectives

Use a private test experience with Studio API access enabled. Existing test save data is fine.

1. Start F5. A HOW TO PLAY card appears. Click GOT IT. It stays gone for the rest of that Play session.
2. HUD stays compact while moving and collecting food. Growth changes and SAFE becomes PVP after spawn protection.
3. Open DINOS. There are exactly three rows, regardless of copy counts. Each row shows grouped base/Gold numbers. Owned dinosaurs can be equipped; locked ones cannot.
4. Open CHESTS. It shows five queue slots, overflow count and a single claim action. Existing queued chests/countdowns must remain usable.
5. Open HOME. It shows equipped dinosaur, the main loop explanation and chest queue totals.
6. Click END RUN and stay still. A RUN COMPLETE summary appears with reason, growth, catches and reward, then the next run starts.
7. In Studio Device Emulator, switch to a phone in landscape orientation. The HUD, bottom buttons, tutorial/modal, DINOS and CHESTS must fit on screen without buttons being cut off. Click/tap each core button.
8. Back on desktop or while still emulated, verify there are no SET 49/50/51, test chest grants or test unlock buttons anywhere in the normal UI.

If all eight pass, BD-015 is Done for UI behavior. A real physical phone remains part of BD-019/device validation.
