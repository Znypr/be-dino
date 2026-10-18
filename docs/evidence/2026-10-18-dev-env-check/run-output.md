# Evidence: first real run of tools/dev_env_check.py (BD-645, 2026-10-18)

Tool and rules: [docs/165](../../165-dev-env-check.md). Run once on the owner's PC with `python tools/dev_env_check.py --json docs/evidence/2026-10-18-dev-env-check/dev_env_check.json`. Read-only: no setting, window or process was changed. Only the Roblox Studio window title is shown; no other window title, file name or account name is in the output.

## Real output (copied, not edited)

```
[ ok ] Blender   installed                          C:/Program Files/Blender Foundation/Blender 5.1/blender.exe
[ ok ] Blender   running                            2 processes
[ ok ] Blender   MCP add-on file                    blender_mcp.py is installed
[ ok ] Blender   MCP port 9876                      add-on answered ping (pong)
[ ok ] Studio    running                            1 process
[FAIL] Studio    window                             Roblox Studio  MINIMISED (Studio draws 0 frames)
[ ok ] Studio    MCP plugin                         3 StudioMCP processes, port 13469 accepts a connection (connect only)
[info] Studio    keyboard/mouse idle                0 s
[ ok ] Studio    PC locked                          not locked
[ ok ] Studio    displays asleep                    Windows never turns the displays off (setting is 0)
[ ok ] Browsers  chrome installed                   yes
[info] Browsers  chrome running                     not running
[info] Browsers  chrome keep running in background  off: closing the last window quits the browser
[info] Browsers  chrome Claude extension            not installed
[ ok ] Browsers  edge installed                     yes
[ ok ] Browsers  edge running                       14 processes
[ ok ] Browsers  edge keep running in background    on
[ ok ] Browsers  edge Claude extension              installed (profile folder: Profile 1)
[ ok ] Tools     ffmpeg                             on PATH
[ ok ] Tools     git                                git version 2.46.1.windows.1
[ ok ] Tools     gh logged in                       yes
[ ok ] Tools     python                             3.14.0
[ ok ] Tools     luau runner                        ~/AppData/Local/Temp/bd057/luau/luau.exe
[warn] Repo      worktrees                          460 registered (many: ask the lead to clean up)
[warn] Repo      stale worktrees                    0 of 260 under .claude/worktrees had no git activity for 3+ days (nothing is deleted by this tool); 5 folders there are not registered
[ ok ] Repo      disk free                          29 GB free on the repo drive
[info] Power     power plan                         always on
[ ok ] Power     monitor-timeout-ac                 now never; docs/158 recommends never
[ ok ] Power     standby-timeout-ac                 now never; docs/158 recommends never
[ ok ] Power     hibernate-timeout-ac               now never; docs/158 recommends never
[warn] Power     disk-timeout-ac                    now 20 min 0 s; docs/158 recommends never (how to set: docs/158 section 3)

22 ok, 1 FAIL, 3 warn, 0 skipped. Nothing was changed on this PC.
```

The JSON of the same run is in [dev_env_check.json](dev_env_check.json).

## What it means, in plain words

- **Blender is up.** It runs, the add-on is installed and answered the `ping` on port 9876. (This run saw 2 Blender processes for a moment; a minute later only the owner's one was left.)
- **Studio is open but MINIMISED.** One Studio window, titled just "Roblox Studio" (no place name, so no place such as Place1 is loaded in it). A minimised Studio draws 0 frames ([158](../../158-virtual-display-and-phone-emulator.md) section 1). This tool did not touch it; the owner restores it, nobody else.
- **Studio MCP is up.** `StudioMCP` runs and its port 13469 accepts a connection (connect only; no request was sent).
- **Power is almost as docs/158 wants.** The plan is "always on"; monitor, standby and hibernate are "never" (plugged in). Only the disk timeout is 20 minutes (docs/158 says never). Owner action, not done here.
- **Claude extension lives in Edge, not Chrome.** It is in Edge (profile folder "Profile 1"), and Edge is running with "keep running in background" on. Chrome is installed, not running, and does not have the extension. If the lead expects "Claude in Chrome" to work, Edge is the browser that must be open.
- **Chrome's background setting is off.** Not a problem today (Chrome holds no Claude extension), so it is only an info line.
- **Worktrees: 460 registered** (260 under `.claude/worktrees`), none idle for 3+ days, 5 leftover folders in `.claude/worktrees` that git does not know about. The lead decides about cleanup; the tool deletes nothing.
- **Disk:** 29 GB free.

## Not tested / not claimed

- `--launch chrome|edge|blender` for real: Blender and Edge were running, so the tool correctly refused ("already running, nothing started"); `--launch chrome --dry-run` printed the command. Chrome was **not** started for real (it would open a window on the owner's screen). The Blender start script was tested headless (`blender -b --factory-startup --python tools/blender/enable_mcp_addon.py` printed "switched blender_mcp on for this session"; no scene or preference was saved).
- A green "displays asleep" line is a guess from the power setting and idle time, not a measurement of the monitors.
- No Studio MCP call and no Studio window change was made in this task.
