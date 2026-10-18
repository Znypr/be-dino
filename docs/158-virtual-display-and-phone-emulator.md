# 158 A display that never sleeps for Studio, and a phone to test on (BD-635, 2026-10-18)

Label: **RESEARCH + PROPOSAL, nothing installed, nothing changed on any machine.** No driver, emulator, setting or window was touched while writing this. Every step marked **OWNER ACTION** changes the PC (a driver, a power setting, an account sign-in) and is for the owner to run, not an agent. Web sources were read on **2026-10-18**; anything I could not confirm from a source is marked **UNVERIFIED**. Related: phone budgets [107](107-offline-mobile-budget.md) section 5 and [146](146-phone-forecast-2026-10-17.md) (BD-085, BD-322), the Studio render failure in [145](145-session1-readiness-2026-10-17.md) section 9.

## 0. The short answer (read this first)

1. **Do the free fix first.** Tell Windows to never turn the displays off, never sleep and never lock (section 3). It costs nothing, installs nothing and is undone with three commands. It may already cure the "displays asleep, 0 frames" case.
2. **Primary: a software virtual monitor** (the open-source "Virtual Display Driver", section 2 option A). Windows sees a real extra monitor that is always plugged in and never goes dark. All agent Studio windows live there and nobody ever moves or minimises them. Install effort: about 15 minutes, one driver, owner only.
3. **Fallback: an HDMI/DisplayPort dummy plug** (about the price of a lunch, section 2 option B). Same idea in hardware, no software driver at all.
4. **Not recommended:** Remote Desktop to the same PC, a Hyper-V virtual machine, Parsec's virtual display (section 2 options C, D, E).
5. **Phone, in two steps.** Now: Studio's own **Device Simulator** (free, built in) for touch layout, screen shapes and the on-screen keyboard. Later: a **cheap real Android phone** for the numbers that matter (speed, heat, memory). An Android emulator on the PC adds little over those two and Roblox restricts emulators for players (section 5).
6. **A 10-minute test plus a 30-minute idle check** the lead runs after the owner install (section 4) decides pass or fail.

## 1. What went wrong, in plain words

| What we saw | Most likely reason | Source / status |
| --- | --- | --- |
| Studio draws nothing when its window is minimised | A minimised window has no drawing area. Our own 2026-10-17 run read `Camera.ViewportSize` = 1 x 1 and `RenderStepped` fired 0 times in 3 s while `Heartbeat` ran at 60 per second ([145](145-session1-readiness-2026-10-17.md) section 9). The game is fine; the drawing step has nothing to draw into. | MEASURED locally. That Roblox pauses drawing for a minimised Studio window is **UNVERIFIED** from any Roblox page (Roblox's player client briefly paused when minimised in Oct 2025 as a test and Roblox confirmed on 2025-12-10 it will not ship it, [DevForum](https://devforum.roblox.com/t/minimizing-the-roblox-client-window-pauses-the-entire-client/4025005), read 2026-10-18; the thread does not say anything about Studio). |
| 0 frames after hours of owner idle | The monitors went to sleep or the PC locked, so Windows stopped presenting frames to a screen. | Owner observation (memory "Studio idle displays"). The exact Windows mechanism is **UNVERIFIED**; the cure (never sleep, never lock) does not depend on it. |
| Windows refused an agent's window restore/placement call | Windows only lets the program that has the foreground, or that got the last input, take the foreground. Anyone else is refused and the taskbar button just flashes ([Microsoft SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow), read 2026-10-18). This is a rule of Windows, not a bug. | Documented. |
| Several agent Studios open at once froze | Not established. Each Studio holds a lot of memory and a graphics context, and windows that fight for the foreground make it worse. | **UNVERIFIED**; section 4 step 5 tests it. |

Design rule that follows from this: **nobody minimises, restores or fights for the foreground a Studio window.** Studio windows are put once on a screen that is always on, and agents only read them with `screen_capture` and `execute_luau`. Moving a window with `SetWindowPos` (no activation) was shown to work on 2026-10-17 ([145](145-session1-readiness-2026-10-17.md) section 9); only the foreground calls are blocked.

## 2. Options for a screen that is always on

All rows are my reading of the sources listed in section 6. "Studio renders" means: the drawing is done by the real graphics card and shown on that screen.

| | A. Software virtual monitor (Virtual Display Driver) | B. Dummy plug (hardware) | C. Remote Desktop to this PC | D. Hyper-V virtual machine | E. Parsec virtual display |
| --- | --- | --- | --- | --- | --- |
| What it is | A small Windows driver that makes Windows believe a new monitor is plugged in. Based on Microsoft's own Indirect Display Driver sample, MIT licence ([GitHub](https://github.com/VirtualDrivers/Virtual-Display-Driver)) | A cheap HDMI or DisplayPort plug that tells the graphics card "a monitor is here" | A second Windows login over the network to the same PC | A whole second Windows inside Windows | A virtual monitor that exists only during a paid Parsec session |
| Does Studio render on it? | Yes, expected. The real GPU does the drawing; the driver only receives the finished picture ([Microsoft IDD overview](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/indirect-display-driver-model-overview), 2025-11). Studio on the virtual monitor: **UNVERIFIED until the section 4 test** | Yes, it is a real output of the real card | Poor. A remote session gets its own display driver, and many GPU programs stop drawing or go black when the session is disconnected; the known workaround (`tscon`) needs admin and kicks the viewer ([Adobe note](https://experienceleague.adobe.com/de/docs/substance-3d-painter/using/pipeline-and-integration/configuration/remote-desktop), read 2026-10-18) | Hyper-V GPU sharing exposes DirectX 11 and OpenGL, not DirectX 12 or Vulkan, per one Microsoft Q&A answer ([link](https://learn.microsoft.com/en-us/answers/questions/5605686/is-it-possible-to-add-support-for-directx-12-in-hy)); which one Studio needs is **UNVERIFIED** | Yes, same IDD idea |
| Survives monitor sleep / PC idle? | The virtual monitor has no panel to switch off. Windows power timers still apply, so also do section 3. Test in section 4 | Same: no panel, but Windows still counts it as a monitor, so also do section 3 | A locked or disconnected remote session blanks | The VM can pause with the host | Parsec says it is not persistent: it exists only for a session ([Parsec](https://support.parsec.app/hc/en-us/articles/32381178803604), read via search 2026-10-18); extra displays are a Teams or Warp feature |
| Several Studio windows? | Yes. Make it large (2560 x 1440 or 3840 x 2160) and tile 2 to 4 windows. A 2 x 2 grid at 2560 x 1440 gives four 1280 x 720 windows | Same, limited by the plug's biggest mode (some are 1080p only; 4K60 listings are often 4:2:0) | One session, one desktop | Heavy: every VM needs its own Studio, RAM and GPU share | Same as A |
| Studio MCP and `screen_capture` | They run on the Windows that runs Studio, so the same machine works as today. `screen_capture` seems to ask Studio itself for a frame (`CaptureService`, per [145](145-session1-readiness-2026-10-17.md) section 9), so it should not care which monitor the window is on, if frames are drawn. **UNVERIFIED**, test in section 4 | Same as A | MCP would run in the other session: messy | MCP would have to live inside the VM or cross the VM wall | Same as A |
| Install effort | Medium: one driver, OWNER ACTION, about 15 min | Low: plug in (needs a free video port), nothing else | Low to start, high to keep working; Windows 11 Pro allows one interactive session, a remote login signs the local user out (forum reports, [example](https://learn.microsoft.com/en-us/answers/questions/2193660/why-do-i-have-to-sign-off-my-remote-pc-after-the-j)) | High: Hyper-V, a second Windows licence, GPU sharing scripts | Medium, needs a Parsec account (owner), paid tier |
| Risk | A driver on the PC. It is a user-mode driver, so a bug should not crash Windows ([Microsoft](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/indirect-display-driver-model-overview)). Known: big graphics-driver updates can give black screens or scramble display order; recovery is Win+P, or Safe Mode and uninstall ([README](https://github.com/VirtualDrivers/Virtual-Display-Driver)) | Cheap hardware can run hot; do not "reprogram" the plug | Locks the owner out of their own desktop | Fragile | Account and cost |
| Verdict | **Primary** | **Fallback** | Reject | Reject (last resort only) | Reject |

### Is the driver trustworthy? (read before installing)

- The project is the "Virtual Display Driver" led by MikeTheTech; homepage `vdd.mikethetech.com`; MIT licence; based on Microsoft's sample ([search listing and SignPath page](https://signpath.org/projects/virtual-display-driver), read 2026-10-18). The README says free code signing is provided by SignPath.io with a SignPath Foundation certificate ([README](https://github.com/VirtualDrivers/Virtual-Display-Driver)).
- **Many copies exist** (accounts `VirtualDrivers`, `VirtualDisplay`, `itsmikethetech`, `GitHangar`, `LizardByte`, `Scorpo999`, `goldli`, `peacepenguin` all showed up). Only use the copy you reach by clicking from the project homepage; the SignPath page names `github.com/VirtualDisplay/Virtual-Display-Driver`, the README I read was on `VirtualDrivers/...`. Whether these two are the same project under a renamed organisation is **UNVERIFIED**; the owner should open the homepage link and use the repository it points to.
- I could not confirm **which release is newest** or that each release file is signed (the release page I read showed two beta pre-releases dated 27 Oct and 16 Oct, year not shown). **UNVERIFIED.** The owner checks the Digital Signatures tab of the downloaded file (step A4 below).
- The README disclaimer: provided "as is", no warranty. It is an unsigned-by-Microsoft community driver, so treat it as software from a stranger: restore point first, physical monitor kept plugged in.
- Hardware option B has no software to trust at all. That is its main advantage.

## 3. Keep the PC awake (free, do first, OWNER ACTION)

Why: whichever option is used, Windows can still switch displays off, sleep, or lock. All values below mean "never". Run in a normal terminal as the owner; `powercfg` ([Microsoft reference](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options), read 2026-10-18) takes minutes, and 0 means never (standard Windows behaviour; the page's own example uses 0 as an index value, so check the result with the query line).

Save the old values first, so it can be undone:

```
powercfg /getactivescheme
powercfg /query > "%USERPROFILE%\power-before.txt"
```

Then (plugged-in values only, a desktop PC):

```
powercfg /change monitor-timeout-ac 0
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change disk-timeout-ac 0
powercfg /availablesleepstates
```

Also by hand in Windows Settings (these are settings, not commands):

1. Settings > Accounts > Sign-in options > "If you've been away, when should Windows require you to sign in again?" = **Never**; "Dynamic lock" = off.
2. Settings > Personalization > Lock screen > Screen saver = **(None)**.
3. Settings > System > Power > Screen and sleep: all four dropdowns = **Never**.
4. Do not use the Win+L lock key while agents are working. A locked PC is the likeliest silent cause of 0 frames (**UNVERIFIED**, but cheap to avoid).

Check what is still keeping Windows from sleeping or what might force it: `powercfg /requests` and `powercfg /lastwake` (read-only). Undo: `powercfg /change monitor-timeout-ac 15` and `powercfg /change standby-timeout-ac 30` (use the numbers in `power-before.txt`). A PC left on all day uses power; the owner decides whether that is fine.

## 4. Recommended path: step by step and the acceptance test

### Primary: virtual monitor (OWNER ACTION, all of A1 to A8)

- **A1.** Do section 3 first. Run the section 4 test (part T below, the 30-minute idle step) once with only that. If frames are lit after 30 minutes, the idle problem is solved; the driver is then only for window placement and can wait.
- **A2.** Make a restore point: Start > "Create a restore point" > Create. Keep one physical monitor plugged in the whole time.
- **A3.** Open `vdd.mikethetech.com`, follow its link to the GitHub repository, Releases, take the newest non-beta installer or the "Virtual Driver Control" app (the README recommends it). Alternative from the README: `winget install --id=VirtualDrivers.Virtual-Display-Driver -e` ([README](https://github.com/VirtualDrivers/Virtual-Display-Driver), id read 2026-10-18).
- **A4.** Before running: right-click the file > Properties > Digital Signatures. A signature from "SignPath Foundation" is expected (**UNVERIFIED**; if there is no signature tab, stop and use the fallback). Run Windows Security on the file.
- **A5.** Run the installer or VDC and press Install. Windows asks to install a device driver: accept only if the publisher is named.
- **A6.** Settings > System > Display: a new extra monitor appears. Set it to **Extend**, resolution **2560 x 1440 at 60 Hz** (the driver allows custom modes through its settings file, `vdd_settings.xml`; its folder is **UNVERIFIED**, VDC shows it). Put it at the far right of the arrangement so the mouse never wanders onto it. Do not make it the main display. Name it in your notes "BD virtual".
- **A7.** Move the Studio windows onto it once by hand (drag, or Win+Shift+Arrow) and leave them. Studio on the owner's physical screen 3 stays as the owner's own window ("never minimise or move", memory "Owner's Place1 window").
- **A8.** Rule for agents, copied into the lead notes: place with `SetWindowPos` (flags no-activate, no-z-order) only; never `ShowWindow` minimise or restore; never `SetForegroundWindow`; read pictures with `screen_capture`.
- **Undo:** the VDC app (Uninstall), or Device Manager > Display adapters > "Virtual Display Driver" > Uninstall device. If the screen goes black after a graphics-driver update: Win+P and cycle, or Safe Mode and uninstall ([README](https://github.com/VirtualDrivers/Virtual-Display-Driver)). Best practice from the README: uninstall before a big graphics-driver update, reinstall after.

### Fallback: dummy plug (OWNER ACTION)

Buy one plug that matches a **free** port on the graphics card (HDMI or DisplayPort; check a free port exists, with several monitors it may not) and lists full RGB or 4:4:4 at 2560 x 1440 or 3840 x 2160 if text sharpness matters ([listings and note](https://www.newegg.com/p/30U-00JU-00021), read 2026-10-18; spec claims in shop listings are unverified until the card lists the mode in Display settings). Plug it in, set it to Extend in Display settings, then continue at A7. No software, so nothing to uninstall.

### Acceptance test (the lead runs it after the owner has installed; about 10 minutes active plus a 30-minute wait)

All numbers are read with `execute_luau` and `screen_capture`; the lead never clicks or moves a window.

1. **Where is it.** Enumerate the monitors (Win32 `EnumDisplayMonitors`) and the Studio window rectangle; PASS if the Studio window lies fully inside the virtual monitor's rectangle.
2. **Is it drawing.** In Studio run, over 3 s, a counter of `RunService.RenderStepped` plus `workspace.CurrentCamera.ViewportSize`. PASS: RenderStepped at least 30 per second and viewport width above 100 (the 2026-10-17 failure was 0 and 1 x 1).
3. **Is the picture lit.** `screen_capture` once; measure with ffmpeg: `C:/ffmpeg/bin/ffmpeg -i frame.png -vf signalstats -f null -` and read `YAVG`. PASS: YAVG above 15 and `YMAX` above 100 (all-black is about 0). Save the image under `docs/evidence/` and show it to the owner.
4. **Idle.** Hands off keyboard and mouse for **30 minutes** with section 3 applied. Repeat steps 2 and 3. PASS: both still pass. FAIL: 0 frames again, then record `powercfg /requests`, whether the PC locked, and move to the fallback.
5. **Two at once (optional, tests the freeze).** Open a second Studio window on the same virtual monitor, tile them, run Play in one for 5 minutes. PASS: both keep RenderStepped above 30 per second and the PC stays responsive. If not, limit the lead to **two rendering Studios at a time** and write that as a rule (**UNVERIFIED** that this is the right number).
6. **Physical screens off (optional).** Owner switches the physical monitors off with their buttons for 5 minutes. Repeat step 3. PASS: lit frame from the virtual-display window.

Result goes in the kanban row BD-635 and in memory "Studio idle displays".

## 5. Phone test

What each tool can show. "GPU frame time" means how smoothly a real phone chip draws; the PC card is far stronger, so any PC number says nothing about a phone.

| Tool | Touch and layout | Safe areas / shapes | Real GPU speed, heat, memory | Cost / effort | Notes |
| --- | --- | --- | --- | --- | --- |
| **Studio Device Simulator** (built in, beta) | Yes, approximate: pinch and rotate by Alt + drag, two-finger pan by Alt + Shift + drag; on-screen keyboard; rotate; Android back button ([Roblox docs](https://create.roblox.com/docs/studio/device-simulator), read 2026-10-18) | Rescales to each device; the doc page does not mention a notch or safe-area overlay (**UNVERIFIED**; a 2022 DevForum post says notch devices existed as a beta, [link](https://devforum.roblox.com/t/notched-screen-support-full-release/2074324)) | **No.** Shows what it looks like, not how it runs ([Roblox docs](https://create.roblox.com/docs/studio/device-simulator)) | Free. File > Beta Features > New Device Simulator, restart Studio | It runs inside Studio, so it also needs a screen that is always on (this document). Roblox's own Studio emulator is explicitly not affected by the emulator policy ([DevForum](https://devforum.roblox.com/t/an-update-on-using-third-party-emulators/3867040)) |
| **Android Studio emulator** | Real Android touch path and the real Roblox app if it installs from Google Play (needs a Google sign-in, OWNER ACTION) | Real device shapes | **No.** It draws with the PC card (`-gpu host`) or in software, so speed and heat are meaningless ([Android docs](https://developer.android.com/studio/run/emulator-acceleration), read 2026-10-18). Memory only roughly (the RAM size can be capped) | Medium: Android Studio, a Windows feature (Windows Hypervisor Platform), a virtual phone image. The older AEHD driver ends **2026-12-31**, WHPX is the recommended one (same page) | Roblox policy, see below. Whether an x86 phone image can run Roblox, or needs Arm translation, is **UNVERIFIED** |
| **BlueStacks and similar** | Yes | Fake shapes | No | Third-party software with bundled extras | Third-party emulator: squarely in the Roblox restriction. Not recommended |
| **Windows Subsystem for Android** | n/a | n/a | n/a | Gone | Microsoft stopped offering WSA and the Amazon Appstore on 2025-03-05 ([Microsoft](https://learn.microsoft.com/en-us/windows/android/wsa/), read 2026-10-18). Do not use unofficial copies |
| **A real cheap Android phone** | Yes, real fingers, real thumb reach | Yes | **Yes**: frame rate, heat, memory, battery, loading time on the same class of device our players have | A used or new low-end phone; price **UNVERIFIED**, check shops. Owner action: buy, install Roblox from Play, sign in, test | The only way to close BD-085 and BD-322 |

**Roblox's emulator policy** (announced 2025-08-07, read 2026-10-18, [DevForum](https://devforum.roblox.com/t/an-update-on-using-third-party-emulators/3867040)): players on a third-party emulator are kicked and must use the official app. **Creators are exempt for testing:** they may join any experience where they have "edit" permission. A matching exemption for the "play" test role was promised "in coming weeks"; I did not find that it shipped (**UNVERIFIED**). Roblox does not list which emulators count; whether Android Studio's virtual phone counts is **UNVERIFIED** (forum replies only guess). The owner's account owns Be Dino, so testing our own game from an emulator should be inside the exemption; test nothing else on it, and expect that the policy can change.

**Recommendation**

1. **Now, free:** Studio Device Simulator for layout and touch (UI size, button reach, keyboard cover, aspect ratios). This is what we can do without the owner buying anything. It proves **layout and touch only**.
2. **Skip** BlueStacks and WSA. Add the Android Studio emulator **only if** the owner wants a real-Android touch check before a phone is bought; it cannot replace the phone, and it adds a Google sign-in, a Windows feature and a policy grey zone.
3. **Buy one cheap real Android phone** matching the docs/107 target class: low-end, about 3 GB RAM, 2019 to 2021 ([107](107-offline-mobile-budget.md) section 1). Then run the section 5 checklist of docs/107 once (BD-085 and BD-322): frame rate on the playtest build, memory in the in-game console, heat after 10 minutes, touch feel. That is the only evidence that clears the "biggest unmeasured risk" in [125](125-playtest-readiness.md) and checks the worst-case 250 k triangle, 3,000 part and 16 light guesses in [146](146-phone-forecast-2026-10-17.md).
4. A second cheap phone is not needed for the first friends test; one phone, one run.

## 6. Sources (all read 2026-10-18)

- Virtual Display Driver README (install, winget id, SignPath statement, known issues, MIT): https://github.com/VirtualDrivers/Virtual-Display-Driver
- SignPath listing (homepage, repository named): https://signpath.org/projects/virtual-display-driver
- Microsoft, Indirect Display Driver model (user-mode, Session 0, sample): https://learn.microsoft.com/en-us/windows-hardware/drivers/display/indirect-display-driver-model-overview
- Microsoft, powercfg options: https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options
- Microsoft, SetForegroundWindow rules: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow
- Roblox DevForum, emulator policy: https://devforum.roblox.com/t/an-update-on-using-third-party-emulators/3867040
- Roblox DevForum, minimise pauses the client (not about Studio): https://devforum.roblox.com/t/minimizing-the-roblox-client-window-pauses-the-entire-client/4025005
- Roblox docs, Device Simulator: https://create.roblox.com/docs/studio/device-simulator
- Android docs, emulator acceleration: https://developer.android.com/studio/run/emulator-acceleration
- Microsoft, WSA ended: https://learn.microsoft.com/en-us/windows/android/wsa/
- Hyper-V GPU-P API support (independent answer): https://learn.microsoft.com/en-us/answers/questions/5605686/is-it-possible-to-add-support-for-directx-12-in-hy
- Remote Desktop and GPU (Adobe note, `tscon`): https://experienceleague.adobe.com/de/docs/substance-3d-painter/using/pipeline-and-integration/configuration/remote-desktop
- Windows 11 remote session signs the local user out (forum example): https://learn.microsoft.com/en-us/answers/questions/2193660/why-do-i-have-to-sign-off-my-remote-pc-after-the-j
- Parsec virtual display limits: https://support.parsec.app/hc/en-us/articles/32381178803604
- Dummy plug example listing: https://www.newegg.com/p/30U-00JU-00021

## 7. Open points for the owner and lead

- **OWNER:** apply section 3 (3 minutes, no install). Then decide on A (driver) or B (plug).
- **OWNER:** the cheap Android phone and its Google sign-in (BD-085, BD-322).
- **LEAD:** run section 4 after the owner reports done; store the images in `docs/evidence/`.
- **UNVERIFIED and to settle by test:** Studio drawing on the virtual monitor; `screen_capture` on it; the newest driver release and its signature; how many Studio windows can render at once; whether the Android Studio emulator can run Roblox.

## Agent windows stay on the virtual monitor (BD-1059, owner 2026-10-18)
Owner request: Studio, Blender and the Edge window the browser tools drive always open on the virtual monitor, so the other screens stay free for the owner's own work (video editing, Roblox).
- Tool: `python tools/monitor4.py list | place | launch studio <file> | launch blender [file] | launch edge [url] | watch` (Windows only, `tests/test_monitor4.py`). The virtual monitor is found by its size 1280 x 720 (Windows lists it as monitor 3 in a code enumeration even though the Settings page calls it monitor 4; the tool never uses the number unless `--index` is given).
- Rules it keeps: never touches a window titled `Place1` (the owner's own Studio window), never minimises or closes, never makes a window topmost, never takes focus, skips the window the owner has focus on, keeps a window's size if it fits.
- Edge: the owner's own Edge windows are left alone. Only an Edge window whose title holds the marker `Claude` (or every Edge window with `--edge-title "*"`, only when the owner asks) or one started with `launch edge` is placed. On 2026-10-18 the only Edge window found was already on the virtual monitor.
- Rule for helpers: start Studio, Blender and Edge with `tools/monitor4.py launch ...` (or run `place` right after any launch); a window that opened elsewhere is a defect to fix at once.
