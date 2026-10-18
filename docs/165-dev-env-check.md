# 165 Morning check for the lead's tools (BD-645, 2026-10-18)

Owner request (tool 5 of 8): "a start-up script so the tools are available each morning". Label: **CURRENT BUILD of a dev tool** (`tools/dev_env_check.py`); it is not part of the game and changes nothing in `src/`. Real output from this PC: [report](evidence/2026-10-18-dev-env-check/run-output.md).

## 1. What it does, in plain words

One command looks at the PC and prints one line per question: **ok**, **warn** (works, but look at it), **FAIL** (a tool is down), **skip** (cannot be read here), **info** (just a number).

```
python tools/dev_env_check.py                  # the table
python tools/dev_env_check.py --json out.json  # the same, also as a file
python tools/dev_env_check.py --launch blender # start Blender (see section 3)
```

Exit code is 1 when any line is FAIL, else 0. It takes about 2 seconds.

## 2. What it checks (all read-only)

| Area | Questions |
| --- | --- |
| Blender | Is `blender.exe` installed? Running? Is the "MCP for Blender" add-on file installed? Does the add-on answer on port 9876? |
| Studio | Is `RobloxStudioBeta` running? Which Studio windows are open (titles only), and is any **minimised**? Is `StudioMCP` running and does its port accept a connection? Seconds since the last key or mouse move. Is the PC locked? Are the displays probably asleep? |
| Browsers | Chrome and Edge: installed, running, "keep running in background" setting, Claude extension installed (which profile folder). |
| Tools | `ffmpeg`, `git`, `gh` logged in, `python`, the Luau runner. |
| Repo | How many git worktrees, how many are idle for 3+ days, free disk space. |
| Power | Active power plan, and the plugged-in monitor, standby, hibernate and disk timeouts, compared with [158](158-virtual-display-and-phone-emulator.md) section 3 (all "never"). |

How each answer is found:

- **Blender port.** The add-on (`blender_mcp.py`, "MCP for Blender") starts its own server on `localhost:9876` when Blender opens (scene option "Auto-Start Server", on by default). The tool connects and sends one message, `{"type": "ping"}`. The add-on's own code answers `pong` and touches no scene data. Nothing else is ever sent. If you changed the port in the add-on panel, use `--blender-port`.
- **Studio.** Windows are listed with the Windows calls `EnumWindows` and `IsIconic`, which only read. The tool never moves, focuses, minimises or restores a window. It does not talk to Studio at all: for the Studio MCP plugin it only opens and closes a connection to the port that `StudioMCP.exe` listens on.
- **Displays asleep.** Windows has no simple "are the displays off" question. The tool says "probably asleep" only when you were idle for longer than the display timeout. With the timeout at "never" it says ok.
- **Browser setting.** Read from the browser's `Local State` file (`background_mode.enabled`). If the key is missing, the browser default (on) applies.
- **Power.** `powercfg /query` and `/getactivescheme` only.

The tool never: kills a process, changes a setting, uses `SetForegroundWindow`, takes an OS screenshot, or opens a file in Studio. A test (`tests/test_dev_env_check.py`, class `SafetyTests`) fails if such a Windows call appears in the source.

## 3. The launch option

`--launch blender`, `--launch chrome` or `--launch edge` **starts** that program, detached, and then ends. Add `--dry-run` to only see the command.

- It refuses when the program is already running ("nothing started"). It never starts a second copy and never stops anything.
- A new window opens in front. That is how Windows starts a program; the tool cannot prevent it, so do not use it while the owner is working.
- Blender starts with `tools/blender/enable_mcp_addon.py`. That script does one small thing: if the "MCP for Blender" add-on is installed but off, it switches it on **for this session** (it does not save preferences and does not touch the scene). On this PC the add-on is already on, so the script just says "already on". The add-on then starts its server by itself. Tested headless on 2026-10-18 (`blender -b --factory-startup --python ...` said "switched on for this session"). Wait about 20 seconds, then run the check again.
- **There is no option for Roblox Studio, on purpose.** Studio windows are the owner's, and the agent window rules say nobody opens, moves, minimises or focuses them ([160](160-agent-brief.md) section 6, [158](158-virtual-display-and-phone-emulator.md) section 1). The Studio lines only look.

## 4. Morning routine (5 lines)

1. `python tools/dev_env_check.py`
2. Blender FAIL: `python tools/dev_env_check.py --launch blender`, wait 20 s, check again.
3. Chrome or Edge not running (the one with the Claude extension is flagged): `--launch chrome` or `--launch edge`.
4. Studio window MINIMISED, or PC locked: tell the owner. Nobody restores the window ([160](160-agent-brief.md) section 6).
5. Power warn: show the owner the line; the fix is in [158](158-virtual-display-and-phone-emulator.md) section 3 and is the owner's action.

## 5. Limits (honest)

- It reads **what Windows says now**. A green line does not prove Studio is drawing frames; section 4 of [158](158-virtual-display-and-phone-emulator.md) (RenderStepped count, `screen_capture`) is still the real test.
- "Displays asleep" is a guess from idle time and the timeout (see section 2).
- The Studio MCP line proves the port opens, not that a tool call would work.
- "Idle worktree" means no git activity (HEAD or index change) for 3 days, not "no unsaved work". The tool deletes nothing; `git worktree list` and the lead decide.
- Windows only for most probes. On another system the lines say skip and the tool does not crash.
- Not checked on purpose: logins (only `gh auth status`, exit code), Roblox Creator Hub, anything that needs a password or sends data.

## 6. Where things are

`tools/dev_env_check.py`, `tools/blender/enable_mcp_addon.py`, `tests/test_dev_env_check.py`. The add-on code was read in place (user add-ons folder), not copied. Kanban: BD-645.
