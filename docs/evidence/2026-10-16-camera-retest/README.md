# BD-255 camera rattle retest (2026-10-16)

Build: `python tools/build.py --profile playtest` (Build 020 playtest profile), temp copy opened in a private Studio window, Play (client+server), character walked by `Humanoid:MoveTo` (WalkSpeed 22, baby dino, no growth). The Studio logger scripts lived only in the temp copy.

## What went wrong with a naive retest, and what was measured

Studio only renders at 60 fps while its window is the foreground window. The other agent's Studio kept taking the foreground, so many legs fell back to **15 fps** (Studio's background throttle; Heartbeat/physics still ran at 60 Hz). A second difference of camera Y scales roughly with 1/fps^2, so a 15 fps log is about 16x too large against 60 fps. The earlier BD-255 number (0.144) was a 15 fps measurement.

So each 30 s walk (and one 12 s climb) was logged **once** per area at the 60 Hz Heartbeat (root Y and dt, from the real physics), and the real `BeDinoCameraSmooth` filter (`S += (y-S)*(1-exp(-dt/s))`, offset clamped +-2.5) was replayed offline in Studio Luau at each smoothing value, at 60 fps (recorded dt) and at 30 fps (every second sample). Same walk for every value, so the values are directly comparable. Camera Y = root Y + clamp(S - y); its second difference is the rattle metric (studs per frame^2, mean / p95 of |y[i]-2y[i-1]+y[i-2]|). Lag = |S - y| (how far the camera trails the root vertically, studs).

Areas: meadow (0,30), hills = conifer highlands (-232,-224), rocky = badlands (256,224), volcanic (232,-208); a 70 stud radius loop at each, 30 s. Climb 1 = straight uphill at the conifer peak from 100 studs out, 12 s, root rose 23.6 studs (BD-053 case). Climb 2 (volcanic peak) did not climb (rise 0) and is ignored.

## Live cross-check (real camera, real RenderStepped, smoothing 0.18)

| Area | Render fps | Camera Y d2 mean / p95 | Root Y d2 mean / p95 |
| --- | ---: | --- | --- |
| meadow | 53 | 0.0004 / 0.0016 | 0.0004 / 0.0015 |
| hills | 59 | 0.0008 / 0.0034 | 0.0022 / 0.0105 |
| rocky | 15 (focus lost) | 0.0058 / 0.0248 | 0.0145 / 0.0517 |
| volcanic | 15 (focus lost) | 0.0301 / 0.1123 | 0.0816 / 0.3120 |

The 59 fps hills leg matches the offline 60 fps replay (0.0008 live vs 0.0006 replay); the 15 fps legs show the 1/fps^2 inflation.

## Replay, 60 fps (camera Y d2 mean / p95; smoothing 0 = no filter = raw root)

| Smoothing | meadow | hills | rocky | volcanic | climb1 d2 mean / p95 | climb1 lag mean / p95 / max |
| --- | --- | --- | --- | --- | --- | --- |
| 0 (off) | .0004 / .0014 | .0022 / .0105 | .0016 / .0049 | .0093 / .0398 | .0068 / .0380 | 0 |
| .06 | .0003 / .0008 | .0010 / .0044 | .0010 / .0040 | .0048 / .0170 | .0044 / .0203 | .13 / .48 / .55 |
| .12 | .0002 / .0007 | .0007 / .0031 | .0008 / .0036 | .0031 / .0108 | .0038 / .0188 | .27 / 1.01 / 1.11 |
| **.18 (current)** | .0002 / .0006 | .0006 / .0025 | .0006 / .0034 | .0023 / .0078 | .0036 / .0177 | .42 / 1.53 / 1.64 |
| .25 | .0002 / .0006 | .0005 / .0021 | .0006 / .0031 | .0017 / .0059 | .0034 / .0173 | .59 / 2.13 / 2.23 |
| .35 | .0002 / .0005 | .0004 / .0017 | .0005 / .0029 | .0013 / .0046 | .0049 / .0326 | .84 / 2.95 / 3.08 |
| .50 | .0002 / .0005 | .0003 / .0014 | .0004 / .0026 | .0010 / .0034 | .0057 / .0351 | 1.20 / 4.14 / 4.30 |

## Replay, 30 fps (camera Y d2 mean / p95)

| Smoothing | meadow | hills | rocky | volcanic | climb1 |
| --- | --- | --- | --- | --- | --- |
| 0 (off) | .0009 / .0028 | .0056 / .0253 | .0052 / .0167 | .0283 / .1083 | .0104 / .0486 |
| .12 | .0006 / .0016 | .0023 / .0105 | .0021 / .0090 | .0114 / .0399 | .0059 / .0290 |
| **.18 (current)** | .0006 / .0014 | .0018 / .0080 | .0017 / .0081 | .0083 / .0283 | .0052 / .0275 |
| .25 | .0005 / .0012 | .0014 / .0062 | .0013 / .0066 | .0062 / .0207 | .0047 / .0259 |
| .35 | .0004 / .0010 | .0011 / .0046 | .0011 / .0054 | .0046 / .0152 | .0063 / .0313 |

## Findings and decision

- At 60 fps the rattle is tiny even with no filter (worst: volcanic 0.009 studs/frame^2 mean). The 0.144 from the first retest was a 15 fps artifact, not evidence of a defect.
- 0.18 cuts the second difference about 4x on volcanic, 3.5x on hills and 2.6x on rocky versus no filter, with modest tail lag. 0.12 gives away 35 percent more rattle on volcanic for 0.5 stud less p95 climb lag; 0.25 buys another 25 percent on volcanic but p95 climb lag reaches 2.1 studs, near the +-2.5 offset clamp. 0.35 and above hit the clamp on climbs (p95 2.95), so rattle on the climb gets worse again (0.0049 vs 0.0034). The knee is 0.18 to 0.25.
- **Decision: keep `CameraVerticalSmoothing = 0.18`. No code change.** BD-053 hill-climb lag at 0.18: mean 0.42, p95 1.5 studs (about climb rate x tau).
- Limits: baby dino only (no growth lift, no BIG); one 30 s loop per area; root Y logged from the local client's own simulation; live fps was not constant (see table), which is why the replay is the comparison; a real 30 fps phone check is still outstanding.
